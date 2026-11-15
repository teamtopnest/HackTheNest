import threading
from datetime import datetime, timezone
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient
from pymongo.errors import PyMongoError

from eeg_stream.app import create_app
from eeg_stream.device import DeviceConnectionError, EEGDevice
from eeg_stream.storage import MongoRecorder, StorageError


class FakeCollection:
    def __init__(self):
        self.documents = []
        self.updates = []

    def create_index(self, *args, **kwargs):
        pass

    def insert_one(self, document):
        self.documents.append(document)

    def update_one(self, query, update, **kwargs):
        self.updates.append((query, update, kwargs))


class FakeClient:
    def __init__(self):
        self.db = SimpleNamespace(
            devices=FakeCollection(), sessions=FakeCollection(), eeg_blocks=FakeCollection()
        )
        self.admin = SimpleNamespace(command=lambda _: None)
        self.closed = False

    def __getitem__(self, name):
        return self.db

    def close(self):
        self.closed = True


def make_recorder(client, queue_size=64):
    return MongoRecorder(
        "mongodb://localhost", client_factory=lambda *args, **kwargs: client,
        queue_size=queue_size,
    )


def block():
    return {
        "type": "eeg",
        "sample_index_start": 0,
        "sample_count": 1,
        "samples": [[1.0] * 8],
        "block_received_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def test_http_collection_persists_without_websocket_and_flushes_on_stop():
    client = FakeClient()
    recorder = make_recorder(client)
    callbacks = []

    class Pipeline:
        def start(self):
            pass

        def stop(self):
            pass

        def close(self):
            pass

    def factory(callback):
        callbacks.append(callback)
        return Pipeline()

    device = EEGDevice(frame_queue_size=1, pipeline_factory=factory, recorder=recorder)
    with TestClient(create_app(device, recorder)) as api:
        response = api.post("/api/acquisition/start", json={"serial": "UN-1234"})
        assert response.status_code == 200
        session_id = response.json()["storage"]["session_id"]
        for i in range(4):
            callbacks[0](np.full((25, 8), i, dtype=float))
        response = api.post("/api/acquisition/stop")
        assert response.status_code == 200
        assert response.json()["storage"]["persisted_samples"] == 100
        assert response.json()["storage"]["persisted_blocks"] == 4
        documents = client.db.eeg_blocks.documents
        assert [doc["sample_index_start"] for doc in documents] == [0, 25, 50, 75]
        assert all(doc["session_id"] == session_id for doc in documents)
        assert isinstance(documents[0]["block_received_at_utc"], datetime)
        assert client.db.sessions.documents[0]["serial"] == "UN-1234"
        assert client.db.sessions.updates[-1][1]["$set"]["state"] == "completed"
        # A new session gets its own indices and no queued blocks from the previous one.
        assert api.post("/api/acquisition/start").status_code == 200
        callbacks[-1](np.zeros((25, 8)))
        assert api.post("/api/acquisition/stop").status_code == 200
        assert client.db.eeg_blocks.documents[-1]["sample_index_start"] == 0
        assert client.db.eeg_blocks.documents[-1]["session_id"] != session_id
    assert client.closed


def test_storage_start_failure_prevents_device_acquisition():
    client = FakeClient()

    def fail(_):
        raise PyMongoError("private connection details")

    client.admin.command = fail
    recorder = make_recorder(client)
    pipeline = SimpleNamespace(start=lambda: pytest.fail("Acquisition must not start"), close=lambda: None)
    device = EEGDevice(pipeline_factory=lambda _: pipeline, recorder=recorder)
    with pytest.raises(DeviceConnectionError, match="MongoDB recording startup failed"):
        device.connect()
    assert "private" not in device.status["error"]
    assert not recorder.status["recording"]
    recorder.close()


def test_block_write_failure_is_reported_and_marks_session_incomplete():
    client = FakeClient()

    def fail(_):
        raise PyMongoError("private connection details")

    client.db.eeg_blocks.insert_one = fail
    recorder = make_recorder(client)
    recorder.start({})
    recorder.submit(block())
    with pytest.raises(StorageError, match="block write failed"):
        recorder.stop()
    assert recorder.status["persisted_blocks"] == 0
    assert client.db.sessions.updates[-1][1]["$set"]["state"] == "error"
    assert "private" not in recorder.status["error"]
    recorder.close()


def test_full_storage_queue_is_explicit_failure_not_silent_loss():
    client = FakeClient()
    entered = threading.Event()
    release = threading.Event()

    def delayed_insert(document):
        entered.set()
        assert release.wait(timeout=5)
        client.db.eeg_blocks.documents.append(document)

    client.db.eeg_blocks.insert_one = delayed_insert
    recorder = make_recorder(client, queue_size=1)
    recorder.start({})
    try:
        recorder.submit(block())
        assert entered.wait(timeout=2)
        recorder.submit(block())
        with pytest.raises(StorageError, match="buffer is full"):
            recorder.submit(block())
    finally:
        release.set()
        with pytest.raises(StorageError, match="buffer is full"):
            recorder.stop()
        recorder.close()
    assert client.db.sessions.updates[-1][1]["$set"]["state"] == "error"


def test_registration_upserts_paired_device_and_rejects_unknown_serial(monkeypatch):
    monkeypatch.setattr(
        "eeg_stream.app.discover_devices",
        lambda: [{"serial": "UN-1234", "model": "Unicorn Hybrid Black"}],
    )
    client = FakeClient()
    recorder = make_recorder(client)
    with TestClient(create_app(recorder=recorder)) as api:
        assert api.get("/api/devices").json()["devices"][0]["serial"] == "UN-1234"
        assert api.post("/api/device/register", json={"serial": "unknown"}).status_code == 404
        assert api.post("/api/device/register", json={"serial": "UN-1234"}).status_code == 200
        query, _, options = client.db.devices.updates[0]
        assert query == {"_id": "UN-1234"}
        assert options["upsert"]
