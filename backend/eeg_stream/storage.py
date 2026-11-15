from __future__ import annotations

import logging
import queue
import threading
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from pymongo import MongoClient
from pymongo.errors import PyMongoError

LOGGER = logging.getLogger(__name__)


class StorageError(RuntimeError):
    """Recording could not be persisted."""


class MongoRecorder:
    def __init__(
        self,
        uri: str | None,
        database: str = "hackthenest",
        client_factory: Callable[..., Any] = MongoClient,
        queue_size: int = 64,
    ) -> None:
        if queue_size < 1:
            raise ValueError("queue_size must be greater than zero")
        self._uri = uri
        self._database_name = database
        self._client_factory = client_factory
        self._client: Any | None = None
        self._queue: queue.Queue[dict[str, Any] | None] = queue.Queue(queue_size)
        self._lock = threading.Lock()
        self._worker: threading.Thread | None = None
        self._session_id: str | None = None
        self._error: str | None = None
        self._persisted_blocks = 0
        self._persisted_samples = 0

    @property
    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "configured": bool(self._uri),
                "recording": self._worker is not None and self._error is None,
                "session_id": self._session_id,
                "error": self._error,
                "persisted_blocks": self._persisted_blocks,
                "persisted_samples": self._persisted_samples,
            }

    def _database(self) -> Any:
        if not self._uri:
            raise StorageError("Set MONGODB_URI in backend .env to enable storage")
        if self._client is None:
            try:
                self._client = self._client_factory(
                    self._uri,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000,
                    socketTimeoutMS=5000,
                    timeoutMS=5000,
                )
            except (PyMongoError, ValueError):
                raise StorageError("MongoDB configuration is invalid") from None
        return self._client[self._database_name]

    def register(self, serial: str) -> dict[str, str]:
        try:
            db = self._database()
            self._client.admin.command("ping")
            db.devices.update_one(
                {"_id": serial},
                {"$set": {
                    "model": "Unicorn Hybrid Black",
                    "registered_at_utc": datetime.now(timezone.utc),
                }},
                upsert=True,
            )
        except PyMongoError:
            raise StorageError(
                "MongoDB device registration failed; check credentials and Atlas IP access"
            ) from None
        return {"serial": serial, "model": "Unicorn Hybrid Black"}

    def start(self, metadata: dict[str, Any]) -> None:
        if not self._uri:
            return
        if self._worker is not None:
            raise StorageError("A recording session is already active")
        session_id = str(uuid4())
        try:
            db = self._database()
            self._client.admin.command("ping")
            db.eeg_blocks.create_index(
                [("session_id", 1), ("sample_index_start", 1)], unique=True
            )
            db.sessions.insert_one({
                "_id": session_id,
                **metadata,
                "started_at_utc": datetime.now(timezone.utc),
                "state": "recording",
            })
        except (PyMongoError, StorageError):
            self._error = "MongoDB recording startup failed; check configuration, credentials and Atlas IP access"
            raise StorageError(self._error) from None
        with self._lock:
            self._session_id = session_id
            self._error = None
            self._persisted_blocks = 0
            self._persisted_samples = 0
        self._worker = threading.Thread(target=self._write_blocks, daemon=True)
        self._worker.start()

    def submit(self, frame: dict[str, Any]) -> None:
        if not self._uri:
            return
        with self._lock:
            if self._error:
                raise StorageError(self._error)
            if self._worker is None:
                raise StorageError("MongoDB recording has not started")
            try:
                self._queue.put_nowait(dict(frame))
            except queue.Full as exc:
                self._error = "MongoDB recording buffer is full; recording is incomplete"
                LOGGER.error(self._error)
                raise StorageError(self._error) from exc

    def _write_blocks(self) -> None:
        db = self._database()
        while True:
            frame = self._queue.get()
            try:
                if frame is None:
                    return
                if self._error:
                    continue
                db.eeg_blocks.insert_one({
                    **frame,
                    "session_id": self._session_id,
                    "filter_hz": [0.5, 30.0],
                    "block_received_at_utc": datetime.fromisoformat(
                        frame["block_received_at_utc"]
                    ),
                })
                with self._lock:
                    self._persisted_blocks += 1
                    self._persisted_samples += frame["sample_count"]
            except PyMongoError:
                with self._lock:
                    self._error = "MongoDB block write failed; recording is incomplete"
                # Driver exceptions may contain connection details; never log them.
                LOGGER.error(self._error)
            finally:
                self._queue.task_done()

    def stop(self, error: str | None = None) -> None:
        if self._worker is None:
            return
        self._queue.put(None)
        self._worker.join()
        self._worker = None
        status = self.status
        recording_error = status["error"] or error
        try:
            self._database().sessions.update_one(
                {"_id": self._session_id},
                {"$set": {
                    "stopped_at_utc": datetime.now(timezone.utc),
                    "state": "error" if recording_error else "completed",
                    "error": recording_error,
                    "persisted_blocks": status["persisted_blocks"],
                    "persisted_samples": status["persisted_samples"],
                }},
            )
        except PyMongoError:
            self._error = "MongoDB session finalization failed; recording is incomplete"
            raise StorageError(self._error) from None
        if status["error"]:
            raise StorageError(status["error"])

    def close(self) -> None:
        try:
            self.stop()
        finally:
            if self._client is not None:
                self._client.close()
