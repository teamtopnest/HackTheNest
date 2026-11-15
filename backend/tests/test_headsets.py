import asyncio
import sys
import threading
import types

import numpy as np
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from eeg_stream import headsets
from eeg_stream.app import create_app
from eeg_stream.device import EEGDevice
from eeg_stream.headsets import HeadsetError


@pytest.mark.parametrize(
    ("model", "serial", "count", "rate"),
    [
        ("hybrid-black", "UN-1", 8, 250),
        ("core-4", "U4-1", 4, 250),
        ("core-8", "U8-1", 8, 250),
        ("nautilus-pro", "NA-1", 16, 250),
        ("nautilus-research", "NA-1", 32, 500),
    ],
)
def test_check_opens_and_closes_without_starting_acquisition(
    monkeypatch, model, serial, count, rate
):
    instances = []

    class Amplifier:
        def __init__(self, serial, **kwargs):
            self.sampling_rate = rate
            self.eeg_channel_count = count
            self.channel_selection = list(range(count))
            self.closed = False
            instances.append(self)

        def close(self):
            self.closed = True

    monkeypatch.setattr(headsets, "discover", lambda _: [{"serial": serial}])
    monkeypatch.setitem(sys.modules, "gtec_unicorn", types.SimpleNamespace(Amplifier=Amplifier))
    monkeypatch.setitem(sys.modules, "gtec_ble", types.SimpleNamespace(Amplifier=Amplifier))
    monkeypatch.setitem(sys.modules, "gtec_gds", types.SimpleNamespace(GNautilus=Amplifier))

    result = headsets.check(model, serial, rate)
    assert result["channel_count"] == count
    assert result["sampling_rate_hz"] == rate
    assert result["channel_indices"] == list(range(count))
    assert instances[0].closed


def test_core_mismatched_channel_count_closes_device(monkeypatch):
    class Amplifier:
        sampling_rate = 250
        eeg_channel_count = 8
        closed = False

        def __init__(self, serial):
            pass

        def close(self):
            Amplifier.closed = True

    monkeypatch.setattr(headsets, "discover", lambda _: [{"serial": "U4-1"}])
    monkeypatch.setitem(sys.modules, "gtec_ble", types.SimpleNamespace(Amplifier=Amplifier))
    with pytest.raises(HeadsetError, match="Expected 4 EEG channels"):
        headsets.check("core-4", "U4-1", 250)
    assert Amplifier.closed


def test_core_discovery_filters_model_and_surfaces_failures(monkeypatch):
    class Amplifier:
        @staticmethod
        def get_connected_devices(rescan):
            assert rescan
            return ["U4-123", "U8-123", "UN-123"]

    monkeypatch.setattr(headsets, "_initialize_driver", lambda: None)
    monkeypatch.setitem(
        sys.modules, "gpype.backend.sources.bci_core",
        types.SimpleNamespace(_load=lambda: None, _ble_acquire=lambda: None),
    )
    import gpype.backend.sources as sources
    monkeypatch.setattr(
        sources, "bci_core", types.SimpleNamespace(_load=lambda: None, _ble_acquire=lambda: None),
        raising=False,
    )
    monkeypatch.setitem(sys.modules, "gtec_ble", types.SimpleNamespace(Amplifier=Amplifier))
    assert headsets.discover("core-4") == [
        {"serial": "U4-123", "model": "Unicorn BCI Core-4"}
    ]
    assert headsets.discover("core-8") == [
        {"serial": "U8-123", "model": "Unicorn BCI Core-8"}
    ]

    def fail(rescan):
        raise RuntimeError("Bluetooth unavailable")

    Amplifier.get_connected_devices = fail
    with pytest.raises(HeadsetError, match="Bluetooth unavailable"):
        headsets.discover("core-8")


def test_setup_check_is_separate_and_collection_carries_checked_metadata(monkeypatch):
    class Recorder:
        def __init__(self):
            self.started = []
            self.frames = []

        @property
        def status(self):
            return {"configured": True, "recording": bool(self.started), "error": None}

        def start(self, metadata):
            self.started.append(metadata)

        def submit(self, frame):
            self.frames.append(frame)

        def stop(self, error=None):
            pass

        def close(self):
            pass

    class Pipeline:
        def start(self):
            pass

        def stop(self):
            pass

        def close(self):
            pass

    recorder = Recorder()
    callbacks = []
    def factory(callback):
        callbacks.append(callback)
        return Pipeline()

    device = EEGDevice(pipeline_factory=factory, recorder=recorder)
    metadata = {
        "model_id": "core-4", "model": "Unicorn BCI Core-4", "serial": "U4-1",
        "sampling_rate_hz": 250, "channel_count": 4,
        "channel_indices": [0, 1, 2, 3], "unit": "uV", "filter_hz": [0.5, 30.0],
        "model_identity": "serial_family",
    }
    monkeypatch.setattr("eeg_stream.app.check", lambda model, serial, sampling_rate: metadata)
    selection = {"model": "core-4", "serial": "U4-1", "sampling_rate_hz": 250}
    with TestClient(create_app(device, recorder)) as api:
        assert api.post("/api/headsets/start", json=selection).status_code == 409
        assert api.post("/api/headsets/check", json=selection).json()["checked"]
        assert not recorder.started
        assert api.post("/api/headsets/start", json={**selection, "serial": "U4-2"}).status_code == 409
        response = api.post("/api/headsets/start", json=selection)
        assert response.status_code == 200
        assert recorder.started == [metadata]
        callbacks[0](np.ones((25, 4)))
        assert recorder.frames[0]["channel_count"] == 4
        assert recorder.frames[0]["sampling_rate_hz"] == 250
        with api.websocket_connect("/ws/eeg") as websocket:
            websocket.send_json({"action": "start"})
            started = websocket.receive_json()
            assert started["channel_count"] == 4
            assert websocket.receive_json()["channel_count"] == 4
            websocket.send_json({"action": "stop"})
            assert websocket.receive_json()["type"] == "stopped"
        assert device.status["state"] == "connected"
        assert api.post("/api/acquisition/stop").status_code == 200


def test_websocket_setup_starts_and_stops_its_own_collection(monkeypatch):
    class Recorder:
        status = {"configured": True, "error": None}

        def start(self, metadata):
            pass

        def submit(self, frame):
            pass

        def stop(self, error=None):
            pass

        def close(self):
            pass

    class Pipeline:
        def start(self):
            pass

        def stop(self):
            pass

        def close(self):
            pass

    device = EEGDevice(pipeline_factory=lambda _: Pipeline(), recorder=Recorder())
    metadata = {
        "model_id": "core-8", "serial": "U8-1", "sampling_rate_hz": 250,
        "channel_count": 8, "channel_indices": list(range(8)),
        "model": "Unicorn BCI Core-8", "unit": "uV", "filter_hz": [0.5, 30.0],
    }
    monkeypatch.setattr("eeg_stream.app.check", lambda *args: metadata)
    selection = {"model": "core-8", "serial": "U8-1", "sampling_rate_hz": 250}
    with TestClient(create_app(device, Recorder())) as api:
        assert api.post("/api/headsets/check", json=selection).status_code == 200
        with api.websocket_connect("/ws/eeg") as websocket:
            websocket.send_json({"action": "start", **selection})
            assert websocket.receive_json()["model_id"] == "core-8"
            assert device.status["state"] == "connected"
            websocket.send_json({"action": "stop"})
            assert websocket.receive_json() == {"type": "stopped"}
        assert device.status["state"] == "disconnected"


def test_cancelled_websocket_start_waits_for_and_stops_device(monkeypatch):
    entered = threading.Event()
    release = threading.Event()

    class Recorder:
        status = {"configured": True, "error": None}

        def start(self, metadata):
            pass

        def stop(self, error=None):
            pass

        def close(self):
            pass

    class Pipeline:
        def start(self):
            entered.set()
            if not release.wait(5):
                raise RuntimeError("Timed out waiting for test")

        def stop(self):
            pass

        def close(self):
            pass

    class Socket:
        headers = {}

        async def accept(self):
            pass

        async def receive_json(self):
            return {"action": "start", **selection}

    recorder = Recorder()
    device = EEGDevice(pipeline_factory=lambda _: Pipeline(), recorder=recorder)
    metadata = {
        "model_id": "core-4", "serial": "U4-1", "sampling_rate_hz": 250,
        "channel_count": 4, "channel_indices": list(range(4)),
        "model": "Unicorn BCI Core-4", "unit": "uV", "filter_hz": [0.5, 30.0],
    }
    monkeypatch.setattr("eeg_stream.app.check", lambda *args: metadata)
    selection = {"model": "core-4", "serial": "U4-1", "sampling_rate_hz": 250}
    app = create_app(device, recorder)
    with TestClient(app) as api:
        assert api.post("/api/headsets/check", json=selection).status_code == 200
        handler = next(route.endpoint for route in app.routes if route.path == "/ws/eeg")

        async def exercise():
            task = asyncio.create_task(handler(Socket()))
            try:
                assert await asyncio.to_thread(entered.wait, 2)
                task.cancel()
            finally:
                release.set()
            with pytest.raises(asyncio.CancelledError):
                await task

        asyncio.run(exercise())
        assert device.status["state"] == "disconnected"


@pytest.mark.parametrize(
    ("model", "rate", "count", "expected_source"),
    [("core-4", 250, 4, "core"), ("core-8", 250, 8, "core"),
     ("nautilus-pro", 250, 16, "nautilus"),
     ("nautilus-research", 500, 32, "nautilus")],
)
def test_pipeline_uses_device_specific_shape_and_rate(
    monkeypatch, model, rate, count, expected_source
):
    class Node:
        def __init__(self, kind, **kwargs):
            self.kind = kind
            self.kwargs = kwargs

    class Pipeline:
        def __init__(self):
            self.connections = []

        def connect(self, source, target):
            self.connections.append((source, target))

    fake_gp = types.SimpleNamespace(
        Constants=types.SimpleNamespace(
            Defaults=types.SimpleNamespace(PORT_IN="in"),
            ChannelRoles=types.SimpleNamespace(SIGNAL="signal"),
        ),
        INode=type("INode", (), {"__init__": lambda self: None}),
        BCICore=lambda **kwargs: Node("core", **kwargs),
        GNautilus=lambda **kwargs: Node("nautilus", **kwargs),
        ChannelSelector=lambda **kwargs: Node("selector", **kwargs),
        Framer=lambda **kwargs: Node("framer", **kwargs),
        Bandpass=lambda **kwargs: Node("bandpass", **kwargs),
        Pipeline=Pipeline,
    )
    monkeypatch.setitem(sys.modules, "gpype", fake_gp)
    device = EEGDevice()
    configuration = {
        "model_id": model, "serial": "test", "sampling_rate_hz": rate,
        "channel_count": count, "channel_indices": list(range(count)),
    }
    device.configure(configuration)
    pipeline = device._create_gpype_pipeline(lambda _: None)
    source, next_node = pipeline.connections[0]
    assert source.kind == expected_source
    assert source.kwargs["channel_selection"] == list(range(count))
    assert source.kwargs["sampling_rate"] == rate
    if expected_source == "nautilus":
        assert source.kwargs["frame_size"] == 1
        assert next_node.kind == "framer"
        assert next_node.kwargs["frame_size"] == rate // 10
    else:
        assert next_node.kind == "selector"
        assert next_node.kwargs["roles"] == "signal"
        assert pipeline.connections[1][0] is next_node
        assert pipeline.connections[1][1].kind == "bandpass"


def test_real_gpype_selector_excludes_core_quality_channel():
    import gpype as gp

    selector = gp.ChannelSelector(roles=gp.Constants.ChannelRoles.SIGNAL)
    keys = gp.Constants.Keys
    roles = gp.Constants.ChannelRoles
    context = {
        keys.CHANNEL_COUNT: 5,
        keys.CHANNEL_ROLES: [roles.SIGNAL] * 4 + [roles.QUALITY],
    }
    assert selector._resolve(context) == [0, 1, 2, 3]


def test_websocket_rejects_untrusted_browser_origin():
    with TestClient(create_app()) as api:
        with pytest.raises(WebSocketDisconnect) as error:
            with api.websocket_connect(
                "/ws/eeg", headers={"origin": "https://untrusted.example"}
            ):
                pass
        assert error.value.code == 1008
