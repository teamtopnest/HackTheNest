from __future__ import annotations

import asyncio
import queue
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from eeg_stream.device import DeviceConnectionError, EEGDevice


def create_app(device: EEGDevice | None = None) -> FastAPI:
    eeg_device = device if device is not None else EEGDevice()
    stream_lock = asyncio.Lock()
    app = FastAPI(title="Local EEG Stream", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/api/status")
    def get_status() -> dict[str, str | None]:
        return eeg_device.status

    @app.post("/api/device/connect")
    def connect_device() -> dict[str, str | None]:
        try:
            eeg_device.connect()
        except DeviceConnectionError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return eeg_device.status

    @app.post("/api/device/disconnect")
    def disconnect_device() -> dict[str, str | None]:
        eeg_device.disconnect()
        return eeg_device.status

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

                try:
                    await asyncio.to_thread(eeg_device.connect)
                except DeviceConnectionError as exc:
                    await websocket.send_json({"type": "error", "message": str(exc)})
                    await websocket.close(code=1011)
                    return

                stream_started = True
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
                    elif frame_task is not None:
                        frame_task.cancel()
                        frame_task = None
            except WebSocketDisconnect:
                pass
            finally:
                if receive_task is not None and not receive_task.done():
                    receive_task.cancel()
                if frame_task is not None and not frame_task.done():
                    frame_task.cancel()
                if stream_started:
                    await asyncio.to_thread(eeg_device.disconnect)

    return app


app = create_app()
