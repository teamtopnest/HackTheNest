import io
import json
from email.message import Message
from urllib.error import HTTPError, URLError

from fastapi.testclient import TestClient

from eeg_stream.app import create_app
from eeg_stream.speech import demo_phrase


def test_demo_phrases_use_the_full_menu_path():
    assert demo_phrase([0]) == "I want food."
    assert demo_phrase([0, 0]) == "I want fast food."
    assert demo_phrase([0, 0, 0]) == "I want pizza."
    assert demo_phrase([0, 4, 0]) == "I want chicken noodle soup."
    assert demo_phrase([2]) == "I want to move."
    assert demo_phrase([2, 0, 1]) == "I want to go home."
    assert demo_phrase([2, 2, 4]) == "I want to raise my legs."
    assert demo_phrase([3, 0, 2]) == "I have pain in the back of my head."
    assert demo_phrase([4, 0, 0]) == "I need to pee."
    assert demo_phrase([4, 5, 1]) == "Please call a nurse."
    assert demo_phrase([5, 0, 0]) == "I want to contact my mother."
    assert demo_phrase([6, 3]) == "I want to do something with my friends."
    assert demo_phrase([6, 3, 1]) == "I want to watch a movie with my friends."
    assert demo_phrase([0, 0, 4]) == "I would like another food option."


def test_speech_endpoint_sends_only_a_demo_phrase(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "test-voice")
    seen = []

    class FakeResponse(io.BytesIO):
        def __init__(self):
            super().__init__(b"fake mp3")
            self.headers = Message()
            self.headers["Content-Type"] = "audio/mpeg"

    def fake_open(request, timeout):
        seen.append((request, timeout))
        return FakeResponse()

    monkeypatch.setattr("eeg_stream.speech.urlopen", fake_open)
    client = TestClient(create_app())
    response = client.post("/api/demo/speech", json={"path": [0, 0, 0]})
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.headers["cache-control"] == "no-store"
    assert response.content == b"fake mp3"
    request, timeout = seen[0]
    assert timeout == 20
    assert request.full_url == "https://api.elevenlabs.io/v1/text-to-speech/test-voice"
    assert request.get_header("Xi-api-key") == "test-key"
    assert json.loads(request.data) == {"text": "I want pizza.", "model_id": "eleven_multilingual_v2"}


def test_speech_rejects_invalid_paths_and_unconfigured_service(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.delenv("ELEVENLABS_VOICE_ID", raising=False)
    client = TestClient(create_app())
    for path in ([], [-1], [99], [0, 0, 0, 0], [0, 0, "0"]):
        assert client.post("/api/demo/speech", json={"path": path}).status_code == 422
    response = client.post("/api/demo/speech", json={"path": [0]})
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_speech_provider_failures_are_reported_without_secrets(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-secret")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "test-voice")
    client = TestClient(create_app())

    def fail_http(request, timeout):
        raise HTTPError(request.full_url, 401, "unauthorized", None, None)

    monkeypatch.setattr("eeg_stream.speech.urlopen", fail_http)
    response = client.post("/api/demo/speech", json={"path": [0]})
    assert response.status_code == 502
    assert "HTTP 401" in response.json()["detail"]
    assert "test-secret" not in response.text

    def fail_payment(request, timeout):
        raise HTTPError(request.full_url, 402, "payment required", None, None)

    monkeypatch.setattr("eeg_stream.speech.urlopen", fail_payment)
    response = client.post("/api/demo/speech", json={"path": [0]})
    assert response.status_code == 502
    assert "credits and billing" in response.json()["detail"]

    def fail_network(request, timeout):
        raise URLError("unavailable")

    monkeypatch.setattr("eeg_stream.speech.urlopen", fail_network)
    assert client.post("/api/demo/speech", json={"path": [0]}).status_code == 502
