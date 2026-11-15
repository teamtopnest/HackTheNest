from __future__ import annotations

import logging
import queue
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable

import numpy as np

from eeg_stream.storage import MongoRecorder, StorageError

LOGGER = logging.getLogger(__name__)

SAMPLE_RATE_HZ = 250
EEG_CHANNEL_COUNT = 8
FILTER_LOW_HZ = 0.5
FILTER_HIGH_HZ = 30.0
FRAME_QUEUE_SIZE = 32
ACQUISITION_TIMEOUT_SECONDS = 10


class DeviceConnectionError(RuntimeError):
    """Raised when the g.Pype pipeline cannot open the EEG device."""


def discover_devices() -> list[dict[str, str]]:
    try:
        from gtec_unicorn import Amplifier

        serials = Amplifier.get_connected_devices()
    except Exception as exc:
        LOGGER.error("Unicorn discovery failed")
        raise DeviceConnectionError(
            "Unicorn discovery failed; check the gtec-unicorn installation and "
            f"Bluetooth adapter: {exc}"
        ) from exc
    return [{"serial": str(serial), "model": "Unicorn Hybrid Black"} for serial in serials]


class EEGDevice:
    def __init__(
        self,
        serial: str | None = None,
        frame_queue_size: int = FRAME_QUEUE_SIZE,
        pipeline_factory: Callable[[Callable[[Any], None]], Any] | None = None,
        recorder: MongoRecorder | None = None,
    ) -> None:
        if frame_queue_size < 1:
            raise ValueError("frame_queue_size must be greater than zero")

        self._serial = serial
        self._recorder = recorder
        self._pipeline_factory = pipeline_factory or self._create_gpype_pipeline
        self._frames: queue.Queue[dict[str, Any] | None] = queue.Queue(
            maxsize=frame_queue_size
        )
        self._lifecycle_lock = threading.RLock()
        self._frame_lock = threading.Lock()
        self._pipeline: Any | None = None
        self._state = "disconnected"
        self._last_error: str | None = None
        self._next_sample_index = 0
        self._dropped_blocks = 0
        self._last_frame_time = 0.0

    @property
    def status(self) -> dict[str, str | None]:
        with self._lifecycle_lock:
            if self._state == "connected":
                storage_error = self._recorder.status["error"] if self._recorder else None
                if storage_error:
                    self._state = "error"
                    self._last_error = storage_error
                elif time.monotonic() - self._last_frame_time > ACQUISITION_TIMEOUT_SECONDS:
                    self._state = "error"
                    self._last_error = "No EEG data received for 10 seconds; check headset power and Bluetooth"
            return {"state": self._state, "error": self._last_error}

    @property
    def metadata(self) -> dict[str, Any]:
        return {
            "serial": self._serial,
            "model": "Unicorn Hybrid Black",
            "sampling_rate_hz": SAMPLE_RATE_HZ,
            "channel_count": EEG_CHANNEL_COUNT,
            "channel_indices": list(range(EEG_CHANNEL_COUNT)),
            "unit": "uV",
            "filter_hz": [FILTER_LOW_HZ, FILTER_HIGH_HZ],
        }

    def connect(self, serial: str | None = None) -> None:
        with self._lifecycle_lock:
            if self._pipeline is not None:
                if self.status["state"] == "error":
                    raise DeviceConnectionError("Acquisition failed; disconnect before restarting")
                if serial is not None and serial != self._serial:
                    raise DeviceConnectionError("Disconnect before selecting another device")
                return
            if serial is not None:
                self._serial = serial

            self._state = "connecting"
            self._last_error = None
            pipeline = None
            self._clear_frames()
            with self._frame_lock:
                self._next_sample_index = 0
                self._dropped_blocks = 0
                self._last_frame_time = time.monotonic()
            try:
                if self._pipeline_factory == self._create_gpype_pipeline and self._serial is None:
                    devices = discover_devices()
                    if len(devices) != 1:
                        raise DeviceConnectionError(
                            "Pair and power on one Hybrid Black, or select a serial from /api/devices"
                        )
                    self._serial = devices[0]["serial"]
                pipeline = self._pipeline_factory(self._publish_frame)
                if self._recorder is not None:
                    self._recorder.start(self.metadata)
                pipeline.start()
            except Exception as exc:
                self._state = "error"
                self._last_error = str(exc)
                if pipeline is not None:
                    try:
                        pipeline.close()
                    except Exception:
                        LOGGER.exception("Failed to close an EEG pipeline after startup failed")
                if self._recorder is not None:
                    try:
                        self._recorder.stop(error="Device acquisition startup failed")
                    except StorageError:
                        LOGGER.error("Failed to finalize recording after device startup failed")
                raise DeviceConnectionError(
                    f"Could not connect to the Unicorn Hybrid Black: {exc}"
                ) from exc

            self._pipeline = pipeline
            self._state = "connected"

    def disconnect(self) -> None:
        with self._lifecycle_lock:
            pipeline = self._pipeline
            self._pipeline = None
            if pipeline is None:
                self._state = "disconnected"
                self._clear_frames()
                return

            try:
                pipeline.stop()
            finally:
                try:
                    pipeline.close()
                finally:
                    self._state = "disconnected"
                    self._clear_frames()
                    self._enqueue_stop()
                    if self._recorder is not None:
                        self._recorder.stop(error=self._last_error)

    def read_frame(self, timeout: float = 0.5) -> dict[str, Any] | None:
        return self._frames.get(timeout=timeout)

    def _publish_frame(self, data: Any) -> None:
        if self._state == "error":
            raise DeviceConnectionError(self._last_error or "EEG acquisition failed")
        frame = np.asarray(data, dtype=float)
        if frame.ndim != 2 or frame.shape[1] != EEG_CHANNEL_COUNT:
            message = (
                f"Expected a samples-by-{EEG_CHANNEL_COUNT} EEG block, "
                f"received shape {frame.shape}"
            )
            self._state = "error"
            self._last_error = message
            raise ValueError(message)
        if not np.isfinite(frame).all():
            message = "EEG block contains non-finite sample values"
            self._state = "error"
            self._last_error = message
            raise ValueError(message)

        with self._frame_lock:
            self._last_frame_time = time.monotonic()
            sample_index_start = self._next_sample_index
            self._next_sample_index += frame.shape[0]
            payload = {
                "type": "eeg",
                "sampling_rate_hz": SAMPLE_RATE_HZ,
                "channel_count": EEG_CHANNEL_COUNT,
                "channel_indices": list(range(EEG_CHANNEL_COUNT)),
                "unit": "uV",
                "sample_index_start": sample_index_start,
                "sample_count": int(frame.shape[0]),
                "block_received_at_utc": datetime.now(timezone.utc).isoformat(),
                "dropped_blocks_total": self._dropped_blocks,
                "samples": frame.tolist(),
            }
            if self._recorder is not None:
                try:
                    self._recorder.submit(payload)
                except StorageError as exc:
                    self._state = "error"
                    self._last_error = str(exc)
                    raise
            try:
                self._frames.put_nowait(payload)
            except queue.Full:
                self._frames.get_nowait()
                self._dropped_blocks += 1
                payload["dropped_blocks_total"] = self._dropped_blocks
                self._frames.put_nowait(payload)
                LOGGER.warning(
                    "EEG WebSocket buffer is full; dropped %d block(s)",
                    self._dropped_blocks,
                )

    def _clear_frames(self) -> None:
        while True:
            try:
                self._frames.get_nowait()
            except queue.Empty:
                return

    def _enqueue_stop(self) -> None:
        try:
            self._frames.put_nowait(None)
        except queue.Full:
            self._clear_frames()
            self._frames.put_nowait(None)

    def _create_gpype_pipeline(self, on_frame: Callable[[Any], None]) -> Any:
        try:
            import gpype as gp
        except ImportError as exc:
            raise RuntimeError(
                'g.Pype is missing; install backend requirements with '
                '`python -m pip install -r requirements.txt` from the backend folder'
            ) from exc

        input_port = gp.Constants.Defaults.PORT_IN

        class AcquisitionSink(gp.INode):
            def __init__(self) -> None:
                super().__init__()

            def step(self, data: dict[str, Any]) -> None:
                on_frame(data[input_port])

        source = gp.HybridBlack(
            serial=self._serial,
            frame_size=25,
            include_accel=False,
            include_gyro=False,
            include_aux=False,
        )
        bandpass = gp.Bandpass(
            f_lo=FILTER_LOW_HZ,
            f_hi=FILTER_HIGH_HZ,
            order=2,
            phase="causal",
        )
        sink = AcquisitionSink()
        pipeline = gp.Pipeline()
        pipeline.connect(source, bandpass)
        pipeline.connect(bandpass, sink)
        return pipeline
