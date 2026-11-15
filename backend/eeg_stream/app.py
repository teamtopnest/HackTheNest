from __future__ import annotations

import asyncio
import logging
import os
import queue
import threading
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.responses import Response

from eeg_stream.device import DeviceConnectionError, EEGDevice, discover_devices
from eeg_stream.headsets import HeadsetError, check, discover
from eeg_stream.storage import MongoRecorder, StorageError
from eeg_stream.speech import DemoSpeechSelection, synthesize_demo_speech

LOGGER = logging.getLogger(__name__)
ALLOWED_ORIGINS = {"http://localhost:5173", "http://127.0.0.1:5173"}

class DeviceSelection(BaseModel):
    serial: str = Field(min_length=1, max_length=128, pattern=r"^\S+$")


class HeadsetSelection(DeviceSelection):
    model: Literal["hybrid-black", "core-4", "core-8", "nautilus-pro", "nautilus-research"]
    sampling_rate_hz: Literal[250, 500] = 250


def create_app(
    device: EEGDevice | None = None,
    recorder: MongoRecorder | None = None,
) -> FastAPI:
    storage = recorder if recorder is not None else MongoRecorder(
        os.getenv("MONGODB_URI"), os.getenv("MONGODB_DATABASE", "hackthenest")
    )
    eeg_device = device if device is not None else EEGDevice(
        serial=os.getenv("UNICORN_SERIAL") or None, recorder=storage
    )
    stream_lock = asyncio.Lock()
    setup_lock = threading.RLock()
    prepared: dict[str, Any] | None = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            yield
        finally:
            try:
                await asyncio.to_thread(eeg_device.disconnect)
            finally:
                await asyncio.to_thread(storage.close)

    app = FastAPI(title="Local EEG Stream", version="0.2.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(ALLOWED_ORIGINS),
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.post("/api/demo/speech")
    def demo_speech(selection: DemoSpeechSelection) -> Response:
        return Response(
            content=synthesize_demo_speech(selection.path),
            media_type="audio/mpeg",
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/api/status")
    def get_status() -> dict[str, Any]:
        return {**eeg_device.status, "storage": storage.status}

    @app.get("/api/devices")
    def get_devices() -> dict[str, Any]:
        try:
            return {"devices": discover_devices()}
        except DeviceConnectionError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/api/device/register")
    def register_device(selection: DeviceSelection) -> dict[str, str]:
        try:
            devices = discover_devices()
            if selection.serial not in {device["serial"] for device in devices}:
                raise HTTPException(status_code=404, detail="Device is not paired with this computer")
            return storage.register(selection.serial)
        except (DeviceConnectionError, StorageError) as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/api/headsets/{model}/devices")
    def find_headsets(
        model: Literal["hybrid-black", "core-4", "core-8", "nautilus-pro", "nautilus-research"],
    ) -> dict[str, Any]:
        try:
            with setup_lock:
                if eeg_device.status["state"] == "connected":
                    raise HTTPException(status_code=409, detail="Stop acquisition before scanning")
                return {"devices": discover(model)}
        except HeadsetError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/api/headsets/check")
    def check_headset(selection: HeadsetSelection) -> dict[str, Any]:
        nonlocal prepared
        with setup_lock:
            if eeg_device.status["state"] == "connected":
                raise HTTPException(status_code=409, detail="Stop acquisition before checking a headset")
            prepared = None
            try:
                prepared = check(selection.model, selection.serial, selection.sampling_rate_hz)
                eeg_device.configure(prepared)
            except (HeadsetError, DeviceConnectionError) as exc:
                prepared = None
                raise HTTPException(status_code=503, detail=str(exc)) from exc
            return {"checked": True, "device": prepared}

    @app.post("/api/headsets/start")
    def start_headset(selection: HeadsetSelection) -> dict[str, Any]:
        with setup_lock:
            if (
                prepared is None
                or prepared["model_id"] != selection.model
                or prepared["serial"] != selection.serial
                or prepared["sampling_rate_hz"] != selection.sampling_rate_hz
            ):
                raise HTTPException(status_code=409, detail="Check the selected headset before collecting")
            if not storage.status["configured"]:
                raise HTTPException(status_code=503, detail="Configure MongoDB before collecting data")
            try:
                if eeg_device.status["state"] == "connected":
                    raise HTTPException(status_code=409, detail="An acquisition is already active")
                eeg_device.configure(prepared)
                eeg_device.connect(serial=selection.serial)
            except DeviceConnectionError as exc:
                raise HTTPException(status_code=503, detail=str(exc)) from exc
            return {**get_status(), "device": eeg_device.metadata}

    @app.post("/api/device/connect")
    @app.post("/api/acquisition/start")
    def connect_device(selection: DeviceSelection | None = None) -> dict[str, Any]:
        try:
            with setup_lock:
                eeg_device.connect(serial=selection.serial if selection else None)
        except DeviceConnectionError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return get_status()

    @app.post("/api/device/disconnect")
    @app.post("/api/acquisition/stop")
    def disconnect_device() -> dict[str, Any]:
        try:
            with setup_lock:
                eeg_device.disconnect()
        except StorageError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return get_status()

    @app.websocket("/ws/eeg")
    async def stream_eeg(websocket: WebSocket) -> None:
        origin = websocket.headers.get("origin")
        if origin is not None and origin not in ALLOWED_ORIGINS:
            await websocket.close(code=1008, reason="Origin is not allowed")
            return
        await websocket.accept()
        if stream_lock.locked():
            await websocket.send_json(
                {"type": "error", "message": "An EEG WebSocket stream is already active"}
            )
            await websocket.close(code=1013)
            return

        async with stream_lock:
            receive_task: asyncio.Task[Any] | None = None
            frame_task: asyncio.Task[dict[str, Any] | None] | None = None
            start_task: asyncio.Task[Any] | None = None
            stream_started = False
            try:
                try:
                    command = await websocket.receive_json()
                except ValueError:
                    await websocket.send_json(
                        {"type": "error", "message": "WebSocket messages must be valid JSON"}
                    )
                    await websocket.close(code=1003)
                    return
                if not isinstance(command, dict) or command.get("action") != "start":
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": 'The first message must be {"action":"start"}',
                        }
                    )
                    await websocket.close(code=1008)
                    return

                owns_acquisition = eeg_device.status["state"] != "connected"
                try:
                    if "model" in command:
                        try:
                            selection = HeadsetSelection.model_validate(command)
                        except ValueError:
                            raise HTTPException(status_code=422, detail="Invalid headset selection")
                        start_task = asyncio.create_task(
                            asyncio.to_thread(start_headset, selection)
                        )
                        await asyncio.shield(start_task)
                        owns_acquisition = True
                    else:
                        await asyncio.to_thread(eeg_device.connect)
                except (DeviceConnectionError, HTTPException) as exc:
                    message = exc.detail if isinstance(exc, HTTPException) else str(exc)
                    await websocket.send_json({"type": "error", "message": message})
                    await websocket.close(code=1011)
                    return

                stream_started = owns_acquisition
                metadata = getattr(eeg_device, "metadata", {
                    "sampling_rate_hz": 250,
                    "channel_count": 8,
                    "channel_indices": list(range(8)),
                    "unit": "uV",
                    "filter_hz": [0.5, 30.0],
                })
                await websocket.send_json(
                    {
                        "type": "started",
                        **metadata,
                    }
                )
                receive_task = asyncio.create_task(websocket.receive_json())

                while True:
                    if frame_task is None:
                        frame_task = asyncio.create_task(
                            asyncio.to_thread(eeg_device.read_frame, 0.25)
                        )
                    done, _ = await asyncio.wait(
                        {receive_task, frame_task},
                        return_when=asyncio.FIRST_COMPLETED,
                    )

                    if receive_task in done:
                        try:
                            command = receive_task.result()
                        except ValueError:
                            await websocket.send_json(
                                {
                                    "type": "error",
                                    "message": "WebSocket messages must be valid JSON",
                                }
                            )
                            receive_task = asyncio.create_task(
                                websocket.receive_json()
                            )
                        else:
                            if (
                                isinstance(command, dict)
                                and command.get("action") == "stop"
                            ):
                                if owns_acquisition:
                                    await asyncio.to_thread(eeg_device.disconnect)
                                await websocket.send_json({"type": "stopped"})
                                break
                            await websocket.send_json(
                                {
                                    "type": "error",
                                    "message": 'Only {"action":"stop"} is accepted while streaming',
                                }
                            )
                            receive_task = asyncio.create_task(
                                websocket.receive_json()
                            )

                    if frame_task in done:
                        try:
                            frame = frame_task.result()
                        except queue.Empty:
                            frame = None
                            timed_out = True
                        else:
                            timed_out = False
                        if frame is None and not timed_out:
                            await websocket.send_json({"type": "stopped"})
                            break
                        if timed_out:
                            status = eeg_device.status
                            if status["state"] == "error":
                                await websocket.send_json(
                                    {
                                        "type": "error",
                                        "message": status["error"]
                                        or "EEG acquisition failed",
                                    }
                                )
                                break
                            if status["state"] == "disconnected":
                                await websocket.send_json({"type": "stopped"})
                                break
                        else:
                            await websocket.send_json(frame)
                        frame_task = None
            except StorageError as exc:
                await websocket.send_json({"type": "error", "message": str(exc)})
            except WebSocketDisconnect:
                pass
            finally:
                if receive_task is not None and not receive_task.done():
                    receive_task.cancel()
                if frame_task is not None and not frame_task.done():
                    frame_task.cancel()
                if start_task is not None and not stream_started:
                    try:
                        await asyncio.shield(start_task)
                    except (DeviceConnectionError, HTTPException) as exc:
                        LOGGER.warning("EEG acquisition startup did not complete: %s", exc)
                    else:
                        stream_started = True
                if stream_started:
                    try:
                        await asyncio.to_thread(eeg_device.disconnect)
                    except StorageError as exc:
                        LOGGER.error("EEG recording finalization failed: %s", exc)

    return app


app = create_app()
