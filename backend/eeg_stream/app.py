from __future__ import annotations

import asyncio
import logging
import os
import queue
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from eeg_stream.device import DeviceConnectionError, EEGDevice, discover_devices
from eeg_stream.storage import MongoRecorder, StorageError

LOGGER = logging.getLogger(__name__)

class DeviceSelection(BaseModel):
    serial: str = Field(min_length=1, max_length=128, pattern=r"^\S+$")


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
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
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

    @app.post("/api/device/connect")
    @app.post("/api/acquisition/start")
    def connect_device(selection: DeviceSelection | None = None) -> dict[str, Any]:
        try:
            eeg_device.connect(serial=selection.serial if selection else None)
        except DeviceConnectionError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return get_status()

    @app.post("/api/device/disconnect")
    @app.post("/api/acquisition/stop")
    def disconnect_device() -> dict[str, Any]:
        try:
            eeg_device.disconnect()
        except StorageError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return get_status()

    @app.websocket("/ws/eeg")
    async def stream_eeg(websocket: WebSocket) -> None:
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
                    await asyncio.to_thread(eeg_device.connect)
                except DeviceConnectionError as exc:
                    await websocket.send_json({"type": "error", "message": str(exc)})
                    await websocket.close(code=1011)
                    return

                stream_started = owns_acquisition
                await websocket.send_json(
                    {
                        "type": "started",
                        "sampling_rate_hz": 250,
                        "channel_count": 8,
                        "channel_indices": list(range(8)),
                        "unit": "uV",
                        "filter_hz": [0.5, 30.0],
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
                if stream_started:
                    try:
                        await asyncio.to_thread(eeg_device.disconnect)
                    except StorageError as exc:
                        LOGGER.error("EEG recording finalization failed: %s", exc)

    return app


app = create_app()
