from __future__ import annotations

from typing import Any


MODELS = {
    "hybrid-black": {"name": "Unicorn Hybrid Black", "family": "hybrid", "channels": 8},
    "core-4": {"name": "Unicorn BCI Core-4", "family": "core", "channels": 4},
    "core-8": {"name": "Unicorn BCI Core-8", "family": "core", "channels": 8},
    "nautilus-pro": {"name": "g.Nautilus PRO Flexible", "family": "nautilus", "channels": None},
    "nautilus-research": {"name": "g.Nautilus RESEARCH", "family": "nautilus", "channels": None},
}


class HeadsetError(RuntimeError):
    """The selected headset could not be found or checked."""


def _initialize_driver() -> None:
    from gpype.common._private import driver_usage

    driver_usage.register()


def discover(model: str) -> list[dict[str, Any]]:
    info = MODELS[model]
    family = info["family"]
    try:
        if family == "hybrid":
            from gtec_unicorn import Amplifier

            serials = Amplifier.get_connected_devices()
        elif family == "core":
            from gtec_ble import Amplifier
            from gpype.backend.sources import bci_core

            _initialize_driver()
            bci_core._load()
            bci_core._ble_acquire()
            prefix = "U4-" if model == "core-4" else "U8-"
            serials = [
                serial for serial in Amplifier.get_connected_devices(rescan=True)
                if str(serial).startswith(prefix)
            ]
        else:
            from gtec_gds.lib.constants import Constants
            from gtec_gds.lib.gtec_gds_wrapper import ConnectedDevices, GDS

            _initialize_driver()
            GDS._check_key()
            serials = [
                name for name, kind, in_use in ConnectedDevices()
                if kind == Constants.DEVICE_TYPE_GNAUTILUS and not in_use
            ]
    except Exception as exc:
        raise HeadsetError(f"Device discovery failed: {exc}") from exc
    return [{"serial": str(serial), "model": info["name"]} for serial in serials]


def check(model: str, serial: str, sampling_rate: int) -> dict[str, Any]:
    info = MODELS[model]
    family = info["family"]
    if family != "nautilus" and sampling_rate != 250:
        raise HeadsetError("This Unicorn model uses 250 Hz")
    if family == "nautilus" and sampling_rate not in (250, 500):
        raise HeadsetError("g.Nautilus sampling rate must be 250 or 500 Hz")
    devices = discover(model)
    if serial not in {device["serial"] for device in devices}:
        raise HeadsetError("Selected headset was not found; scan again")
    try:
        if family == "hybrid":
            from gtec_unicorn import Amplifier

            device = Amplifier(serial)
        elif family == "core":
            from gtec_ble import Amplifier

            device = Amplifier(serial)
        else:
            from gtec_gds import GNautilus

            device = GNautilus(serial=serial, sampling_rate=sampling_rate)
        try:
            if family == "nautilus":
                channel_indices = list(device.channel_selection)
                actual_rate = int(device.sampling_rate)
            elif family == "core":
                actual_rate = int(device.sampling_rate)
                count = int(device.eeg_channel_count)
                if count != info["channels"]:
                    raise HeadsetError(
                        f"Expected {info['channels']} EEG channels, device reports {count}"
                    )
                channel_indices = list(range(count))
            else:
                actual_rate = 250
                channel_indices = list(range(8))
            if actual_rate != sampling_rate:
                raise HeadsetError(
                    f"Device reports {actual_rate} Hz instead of {sampling_rate} Hz"
                )
            if not channel_indices:
                raise HeadsetError("Device reported no EEG channels")
        finally:
            device.close()
    except HeadsetError:
        raise
    except Exception as exc:
        raise HeadsetError(f"Device connection check failed: {exc}") from exc
    return {
        "model_id": model,
        "model": info["name"],
        "serial": serial,
        "sampling_rate_hz": actual_rate,
        "channel_count": len(channel_indices),
        "channel_indices": channel_indices,
        "unit": "uV",
        "filter_hz": [0.5, 30.0],
        "model_identity": "user_selected" if family == "nautilus" else "serial_family",
        "decoding": {"status": "disabled", "reason": "Calibration and stimulus timing are not validated"},
    }
