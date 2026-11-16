from unittest.mock import Mock

from fastapi.testclient import TestClient
import httpx
from pymongo.errors import AutoReconnect
import pytest

from backend.app import create_app
from backend.schemas import Chunk, MAX_BODY_BYTES
from backend.sender import ApiClient, LiveSender
from backend.storage import MongoStore, NotFound
from backend.tests.conftest import make_sample


TOKEN = "test-token-not-a-secret-" + "x" * 32


def test_api_auth_validation_error_redaction_and_database_failure(recording):
    store = Mock(spec=MongoStore)
    store.create.return_value = {"duplicate": False}
    app = create_app(store=store, token=TOKEN, owner="test-owner")
    with TestClient(app) as client:
        payload = recording.model_dump(mode="json")
        assert client.post("/v1/recordings", json=payload).status_code == 401
        headers = {"Authorization": f"Bearer {TOKEN}"}
        response = client.post("/v1/recordings", json=payload, headers=headers)
        assert response.status_code == 200
        assert store.create.call_args.args[1] == "test-owner"
        payload["ownerId"] = "another-owner"
        response = client.post("/v1/recordings", json=payload, headers=headers)
        assert response.status_code == 422
        assert "another-owner" not in response.text
        del payload["ownerId"]
        store.create.side_effect = AutoReconnect("private database details")
        response = client.post("/v1/recordings", json=payload, headers=headers)
        assert response.status_code == 503
        assert "private database" not in response.text
        store.samples.side_effect = NotFound("Recording not found")
        response = client.get(f"/v1/recordings/{recording.recordingId}/samples", headers=headers)
        assert response.status_code == 404
        response = client.post("/v1/recordings", content=b"x" * (MAX_BODY_BYTES + 1), headers=headers)
        assert response.status_code == 413
        assert client.get("/v1/recordings?limit=1000", headers=headers).status_code == 422
    store.close.assert_called_once()


def test_public_demo_speech_supports_frontend_origin_and_keeps_ingestion_private(monkeypatch):
    monkeypatch.setenv("EEG_DEMO_TOKEN", "")
    monkeypatch.setenv("EEG_ALLOWED_ORIGINS", "https://neuronvision.us")
    speech = Mock(return_value=b"demo audio")
    monkeypatch.setattr("backend.app.synthesize_demo_speech", speech)
    app = create_app(store=Mock(spec=MongoStore), token=TOKEN, owner="test-owner")
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        response = client.post(
            "/api/demo/speech", json={"path": [0, 0, 0]},
            headers={"Origin": "https://neuronvision.us"},
        )
        assert response.status_code == 200
        assert response.content == b"demo audio"
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["access-control-allow-origin"] == "https://neuronvision.us"
        speech.assert_called_once_with([0, 0, 0])
        assert client.get("/v1/recordings").status_code == 401
        preflight = client.options("/api/demo/speech", headers={
            "Origin": "https://neuronvision.us",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        })
        assert preflight.status_code == 200
        assert client.options("/api/demo/speech", headers={
            "Origin": "https://untrusted.test", "Access-Control-Request-Method": "POST",
        }).status_code == 400
        assert client.post("/api/demo/speech", json={"path": []}).status_code == 422


def test_public_demo_speech_rejects_arbitrary_text(monkeypatch):
    speech = Mock()
    monkeypatch.setattr("backend.app.synthesize_demo_speech", speech)
    with TestClient(create_app(store=Mock(spec=MongoStore), token=TOKEN, owner="test-owner")) as client:
        assert client.post("/api/demo/speech", json={"text": "Arbitrary text"}).status_code == 422
    speech.assert_not_called()


def test_sender_retry_and_https(monkeypatch, recording):
    monkeypatch.setattr("backend.sender.time.sleep", lambda seconds: None)
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(503 if len(calls) < 3 else 200, json={"duplicate": False})

    api = ApiClient("https://example.test", TOKEN, httpx.MockTransport(respond))
    api.send(str(recording.recordingId), Chunk(chunkIndex=0, samples=[]))
    assert len(calls) == 3
    api.close()
    with pytest.raises(ValueError, match="HTTPS"):
        ApiClient("http://remote.test", TOKEN)


def test_live_outbox_restart_failures_and_gaps(tmp_path, recording):
    api = Mock(spec=ApiClient)
    api.send.side_effect = RuntimeError("network unavailable")
    path = tmp_path / "queue.sqlite3"
    sender = LiveSender(api, recording, path)
    sender.feed([make_sample(recording, 0), make_sample(recording, 250)])
    with pytest.raises(RuntimeError, match="network"):
        sender.drain()
    assert sender.db.execute("SELECT COUNT(*) FROM pending").fetchone()[0] == 1
    sender.close()
    resumed = LiveSender(api, recording, path)
    api.send.side_effect = None
    resumed.finish(allow_gaps=True)
    chunks = [call.args[1] for call in api.send.call_args_list]
    assert chunks[-2].chunkIndex == 0
    assert chunks[-1].chunkIndex == 1 and chunks[-1].finalWindow
    assert api.request.call_args.kwargs["json"] == {
        "expectedSampleCount": 2, "expectedLastSampleIndex": 250, "allowGaps": True,
    }
    assert resumed.db.execute("SELECT COUNT(*) FROM pending").fetchone()[0] == 0
    with pytest.raises(ValueError, match="ended"):
        resumed.feed([make_sample(recording, 251)])
    resumed.close()


def test_queue_exhaustion_is_explicit_and_rolls_back(tmp_path, recording):
    api = Mock(spec=ApiClient)
    sender = LiveSender(api, recording, tmp_path / "queue.sqlite3")
    sender.capacity = 1
    with pytest.raises(BufferError, match="capacity"):
        sender.feed([make_sample(recording, 0)])
    assert sender.db.execute("SELECT COUNT(*) FROM buffer").fetchone()[0] == 0
    assert sender._state("lastIndex") == "-1"
    sender.close()
