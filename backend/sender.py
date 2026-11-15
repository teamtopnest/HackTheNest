import json
import sqlite3
import time
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import httpx

from backend.schemas import Chunk, MAX_BODY_BYTES, Recording, Sample, content_hash, normalize_chunk


class ApiClient:
    def __init__(self, url: str, token: str, transport=None):
        parsed = urlparse(url)
        if parsed.username or parsed.password:
            raise ValueError("Do not put credentials in the API URL")
        if parsed.scheme != "https" and not (
            parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "localhost", "::1")
        ):
            raise ValueError("Use HTTPS except for loopback development")
        if not token:
            raise ValueError("EEG_API_TOKEN is required")
        self.client = httpx.Client(
            base_url=url.rstrip("/") + "/", headers={"Authorization": f"Bearer {token}"},
            timeout=30, transport=transport,
        )

    def close(self):
        self.client.close()

    def request(self, method: str, path: str, **kwargs):
        for attempt in range(4):
            try:
                response = self.client.request(method, path, **kwargs)
            except httpx.TransportError as exc:
                if attempt == 3:
                    raise RuntimeError(
                        f"EEG API transport failed ({type(exc).__name__}); pending data retained"
                    ) from None
            else:
                if response.status_code not in (429, 502, 503, 504):
                    response.raise_for_status()
                    return response.json()
                if attempt == 3:
                    raise RuntimeError(
                        f"EEG API unavailable (HTTP {response.status_code}); pending data retained"
                    )
            time.sleep(2**attempt)
        raise RuntimeError("EEG API retry budget exhausted")

    def create(self, recording: Recording):
        return self.request("POST", "v1/recordings", json=recording.model_dump(mode="json"))

    def send(self, recording_id: str, chunk: Chunk):
        return self.request("POST", f"v1/recordings/{recording_id}/chunks",
                            json=chunk.model_dump(mode="json"))


class LiveSender:
    """Durable one-producer buffer; acquisition supplies verified Sample objects."""

    def __init__(self, api: ApiClient, recording: Recording, queue_path: Path,
                 capacity_bytes: int = 16 * MAX_BODY_BYTES):
        if recording.source.kind != "live":
            raise ValueError("LiveSender requires a live recording")
        if capacity_bytes < MAX_BODY_BYTES:
            raise ValueError("Queue capacity must be at least 1 MiB")
        self.api, self.recording, self.capacity = api, recording, capacity_bytes
        self.db = sqlite3.connect(queue_path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS buffer (
                sample_index INTEGER PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS pending (
                chunk_index INTEGER PRIMARY KEY, payload TEXT NOT NULL);
        """)
        identity = content_hash(recording.model_dump(mode="json"))
        existing = self._state("identity")
        if existing is not None and existing != identity:
            self.db.close()
            raise ValueError("Queue belongs to a different recording or metadata revision")
        if existing is None:
            with self.db:
                self._set("identity", identity)
                self._set("nextWindow", "0")
                self._set("sampleCount", "0")
                self._set("lastIndex", "-1")
                self._set("lastOffset", "-1")

    def close(self):
        self.db.close()

    def _state(self, key):
        row = self.db.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
        return row[0] if row is not None else None

    def _set(self, key, value):
        self.db.execute("INSERT OR REPLACE INTO state (key,value) VALUES (?,?)", (key, value))

    def _check_capacity(self, extra: int = 0):
        size = sum(self.db.execute(
            f"SELECT COALESCE(SUM(length(CAST(payload AS BLOB))),0) FROM {table}"
        ).fetchone()[0] for table in ("buffer", "pending"))
        if size + extra > self.capacity:
            raise BufferError("EEG queue capacity exhausted; pause acquisition or retry after draining")

    def _enqueue(self, final: bool):
        window = int(self._state("nextWindow"))
        samples = [Sample.model_validate_json(row[0]) for row in self.db.execute(
            "SELECT payload FROM buffer ORDER BY sample_index")]
        chunk = Chunk(chunkIndex=window, finalWindow=final, samples=samples)
        normalize_chunk(self.recording, chunk)
        payload = chunk.model_dump_json()
        if len(payload.encode("utf-8")) > MAX_BODY_BYTES:
            raise BufferError("EEG window exceeds the 1 MiB request limit")
        self.db.execute("DELETE FROM buffer")
        self._check_capacity(len(payload.encode("utf-8")))
        self.db.execute("INSERT INTO pending VALUES (?,?)", (window, payload))
        self._set("nextWindow", str(window + 1))

    def feed(self, samples: Iterable[Sample]):
        if self._state("finished") is not None:
            raise ValueError("Recording has already ended")
        for sample in samples:
            with self.db:
                last_index, last_offset = int(self._state("lastIndex")), int(self._state("lastOffset"))
                if sample.sampleIndex <= last_index or sample.offsetNs <= last_offset:
                    raise ValueError("Live source indices and offsets must strictly increase")
                target_window = sample.sampleIndex // self.recording.chunk_sample_count
                while int(self._state("nextWindow")) < target_window:
                    self._enqueue(final=False)
                normalize_chunk(self.recording, Chunk(chunkIndex=target_window, samples=[sample]))
                payload = sample.model_dump_json()
                self._check_capacity(len(payload.encode("utf-8")))
                self.db.execute("INSERT INTO buffer VALUES (?,?)", (sample.sampleIndex, payload))
                self._set("sampleCount", str(int(self._state("sampleCount")) + 1))
                self._set("lastIndex", str(sample.sampleIndex))
                self._set("lastOffset", str(sample.offsetNs))

    def drain(self):
        self.api.create(self.recording)
        while True:
            row = self.db.execute(
                "SELECT chunk_index,payload FROM pending ORDER BY chunk_index LIMIT 1"
            ).fetchone()
            if row is None:
                return
            self.api.send(str(self.recording.recordingId), Chunk.model_validate_json(row[1]))
            with self.db:
                self.db.execute("DELETE FROM pending WHERE chunk_index=?", (row[0],))

    def finish(self, allow_gaps: bool = False):
        if int(self._state("sampleCount")) == 0:
            raise ValueError("Cannot finish an empty recording")
        if self._state("finished") is None:
            with self.db:
                self._enqueue(final=True)
                self._set("finished", "true")
        self.drain()
        return self.api.request("POST", f"v1/recordings/{self.recording.recordingId}/complete", json={
            "expectedSampleCount": int(self._state("sampleCount")),
            "expectedLastSampleIndex": int(self._state("lastIndex")),
            "allowGaps": allow_gaps,
        })
