# Local EEG stream

This service runs on the computer paired with a g.tec Unicorn Hybrid Black. It uses g.Pype to acquire the eight EEG channels at 250 Hz, applies a causal Butterworth bandpass from 0.5 to 30 Hz, and exposes the filtered samples over a local WebSocket. The device's optional motion and status channels are disabled.

## Setup

Pair the headset with Windows Bluetooth settings, then from this folder install the service:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Run the API on loopback:

```powershell
python run.py
```

The HTTP API is available at `http://127.0.0.1:8000`:

- `GET /api/status` reports the device state.
- `POST /api/device/connect` opens the g.Pype pipeline and device.
- `POST /api/device/disconnect` stops acquisition and releases the device.
- `WS /ws/eeg` accepts `{"action":"start"}` as its first message, then sends one JSON frame per acquired block. Send `{"action":"stop"}` to stop acquisition.

The first WebSocket start request connects the device if it is not already connected. Only one WebSocket stream is allowed at a time. Frames include the host receive timestamp, sample index, sample rate, channel indices (0–7), channel count, microvolt units, and samples; sample indices make any dropped blocks visible. If the bounded WebSocket buffer fills, the oldest block is discarded and the cumulative dropped-block count is included in subsequent frames.

MongoDB storage and Nextflow/Seqera batch ingestion are not part of this service yet.

## Validation

Install test dependencies and run the hardware-independent tests:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
```
