from queue import Empty, Queue

from fastapi.testclient import TestClient

from eeg_stream.app import create_app
from eeg_stream.device import DeviceConnectionError


class FakeDevice:
    def __init__(self) -> None:
        self.frames = Queue()
        self.connected = False

    @property
    def status(self):
        return {
            "state": "connected" if self.connected else "disconnected",
            "error": None,
        }

    def connect(self) -> None:
        self.connected = True
        self.frames.put(
            {
                "type": "eeg",
                "sampling_rate_hz": 250,
                "channel_count": 8,
                "sample_index_start": 0,
                "sample_count": 1,
                "samples": [[0.0] * 8],
            }
        )

    def disconnect(self) -> None:
        self.connected = False

    def read_frame(self, timeout: float = 0.5):
        return self.frames.get(timeout=timeout)


def test_websocket_start_stream_and_stop_lifecycle():
    device = FakeDevice()
    client = TestClient(create_app(device))

    with client.websocket_connect("/ws/eeg") as websocket:
        websocket.send_json({"action": "start"})
        assert websocket.receive_json()["type"] == "started"
        frame = websocket.receive_json()
        assert frame["type"] == "eeg"
        assert frame["channel_count"] == 8
        websocket.send_json({"action": "stop"})
        assert websocket.receive_json() == {"type": "stopped"}

    assert not device.connected


def test_device_connection_status_endpoint():
    device = FakeDevice()
    client = TestClient(create_app(device))

    assert client.get("/api/status").json()["state"] == "disconnected"
    assert client.post("/api/device/connect").json()["state"] == "connected"
    assert client.post("/api/device/disconnect").json()["state"] == "disconnected"


def test_websocket_disconnect_stops_acquisition():
    device = FakeDevice()
    client = TestClient(create_app(device))

    with client.websocket_connect("/ws/eeg") as websocket:
        websocket.send_json({"action": "start"})
        assert websocket.receive_json()["type"] == "started"
        websocket.close()

    assert not device.connected


def test_websocket_reports_device_connection_failure():
    class FailedDevice(FakeDevice):
        def connect(self) -> None:
            raise DeviceConnectionError("Bluetooth device not found")

    client = TestClient(create_app(FailedDevice()))

    with client.websocket_connect("/ws/eeg") as websocket:
        websocket.send_json({"action": "start"})
        error = websocket.receive_json()
        assert error == {
            "type": "error",
            "message": "Bluetooth device not found",
        }


def test_websocket_rejects_malformed_json():
    device = FakeDevice()
    client = TestClient(create_app(device))

    with client.websocket_connect("/ws/eeg") as websocket:
        websocket.send_text("{")
        assert websocket.receive_json() == {
            "type": "error",
            "message": "WebSocket messages must be valid JSON",
        }

    assert not device.connected
