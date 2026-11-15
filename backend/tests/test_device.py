import sys
import types
from queue import Empty

import numpy as np
import pytest

from eeg_stream.device import DeviceConnectionError, EEGDevice, discover_devices


class FakePipeline:
    def __init__(self) -> None:
        self.connections = []
        self.started = False
        self.stopped = False
        self.closed = False

    def connect(self, source, target) -> None:
        self.connections.append((source, target))

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def close(self) -> None:
        self.closed = True


def install_fake_gpype(monkeypatch, pipeline):
    class FakeINode:
        def __init__(self) -> None:
            pass

    class FakeHybridBlack:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

    class FakeBandpass:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

    class FakePipelineFactory:
        def __new__(cls):
            return pipeline

    fake_gpype = types.SimpleNamespace(
        Constants=types.SimpleNamespace(
            Defaults=types.SimpleNamespace(PORT_IN="in")
        ),
        INode=FakeINode,
        HybridBlack=FakeHybridBlack,
        Bandpass=FakeBandpass,
        Pipeline=FakePipelineFactory,
    )
    monkeypatch.setitem(sys.modules, "gpype", fake_gpype)
    monkeypatch.setitem(
        sys.modules, "gtec_unicorn",
        types.SimpleNamespace(
            Amplifier=types.SimpleNamespace(get_connected_devices=lambda: ["UN-1234"])
        ),
    )


def test_pipeline_uses_eight_channel_source_and_bandpass(monkeypatch):
    pipeline = FakePipeline()
    install_fake_gpype(monkeypatch, pipeline)
    device = EEGDevice(serial="UN-1234", frame_queue_size=2)

    device.connect()

    assert device.status == {"state": "connected", "error": None}
    assert pipeline.started
    source, bandpass = pipeline.connections[0]
    assert source.kwargs == {
        "serial": "UN-1234",
        "frame_size": 25,
        "include_accel": False,
        "include_gyro": False,
        "include_aux": False,
    }
    assert bandpass.kwargs == {
        "f_lo": 0.5,
        "f_hi": 30.0,
        "order": 2,
        "phase": "causal",
    }
    sink = pipeline.connections[1][1]
    samples = np.arange(24, dtype=float).reshape((3, 8))
    sink.step({"in": samples})

    frame = device.read_frame(timeout=0.1)
    assert frame is not None
    assert frame["sampling_rate_hz"] == 250
    assert frame["channel_count"] == 8
    assert frame["channel_indices"] == list(range(8))
    assert frame["unit"] == "uV"
    assert frame["sample_index_start"] == 0
    assert frame["sample_count"] == 3
    assert frame["samples"] == samples.tolist()
    assert frame["block_received_at_utc"]

    device.disconnect()
    assert pipeline.stopped
    assert pipeline.closed
    assert device.status == {"state": "disconnected", "error": None}


def test_full_frame_queue_drops_oldest_and_reports_loss(monkeypatch):
    pipeline = FakePipeline()
    install_fake_gpype(monkeypatch, pipeline)
    device = EEGDevice(frame_queue_size=1)
    device.connect()
    sink = pipeline.connections[1][1]

    sink.step({"in": np.zeros((1, 8))})
    sink.step({"in": np.ones((1, 8))})

    frame = device.read_frame(timeout=0.1)
    assert frame is not None
    assert frame["sample_index_start"] == 1
    assert frame["dropped_blocks_total"] == 1
    assert frame["samples"] == np.ones((1, 8)).tolist()

    device.disconnect()


def test_failed_pipeline_start_is_reported_and_closed():
    class FailedPipeline(FakePipeline):
        def start(self) -> None:
            raise OSError("Bluetooth device not found")

    pipeline = FailedPipeline()
    device = EEGDevice(pipeline_factory=lambda _: pipeline)

    with pytest.raises(DeviceConnectionError, match="Bluetooth device not found"):
        device.connect()

    assert device.status == {
        "state": "error",
        "error": "Bluetooth device not found",
    }
    assert pipeline.closed


def test_invalid_eeg_block_is_rejected(monkeypatch):
    pipeline = FakePipeline()
    install_fake_gpype(monkeypatch, pipeline)
    device = EEGDevice()
    device.connect()
    sink = pipeline.connections[1][1]

    with pytest.raises(ValueError, match="samples-by-8"):
        sink.step({"in": np.zeros((2, 7))})

    assert device.status["state"] == "error"
    device.disconnect()


def test_read_frame_times_out_when_no_samples_are_available():
    device = EEGDevice()

    with pytest.raises(Empty):
        device.read_frame(timeout=0.01)


def test_discovery_does_not_hide_sdk_errors(monkeypatch):
    def fail():
        raise OSError("Bluetooth adapter failure")

    monkeypatch.setitem(
        sys.modules, "gtec_unicorn",
        types.SimpleNamespace(Amplifier=types.SimpleNamespace(get_connected_devices=fail)),
    )
    with pytest.raises(DeviceConnectionError, match="discovery failed"):
        discover_devices()


def test_automatic_selection_rejects_multiple_paired_devices(monkeypatch):
    pipeline = FakePipeline()
    install_fake_gpype(monkeypatch, pipeline)
    sys.modules["gtec_unicorn"].Amplifier.get_connected_devices = lambda: ["UN-1", "UN-2"]
    device = EEGDevice()
    with pytest.raises(DeviceConnectionError, match="select a serial"):
        device.connect()
    assert not pipeline.started
    device.connect(serial="UN-2")
    assert pipeline.connections[0][0].kwargs["serial"] == "UN-2"
    with pytest.raises(DeviceConnectionError, match="Disconnect"):
        device.connect(serial="UN-1")
    device.disconnect()


def test_missing_data_changes_acquisition_status(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr("eeg_stream.device.time.monotonic", lambda: clock[0])
    device = EEGDevice(pipeline_factory=lambda _: FakePipeline())
    device.connect()
    clock[0] += 11
    assert device.status["state"] == "error"
    assert "No EEG data" in device.status["error"]
    device.disconnect()
