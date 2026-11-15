# Local Hybrid Black EEG backend

This Windows-local FastAPI service acquires **Unicorn Hybrid Black** EEG using
`gp.HybridBlack`: eight channels at 250 Hz, in microvolts. It applies a stateful,
causal order-2 Butterworth **0.5-30 Hz bandpass**, records filtered blocks to
MongoDB when configured, and optionally streams them over a WebSocket.
Motion and auxiliary channels are disabled.

## Hardware prerequisite

1. Power on the headset and pair it in Windows Bluetooth settings.
2. Use a supported Bluetooth adapter (preferably the vendor-supplied dongle) and
   install the applicable g.tec drivers. Close any other recorder using the headset.
3. Discovery lists **paired** Hybrid Black serials on Windows. It does not pair
   devices, prove they are powered on, or list arbitrary Bluetooth peripherals.
   Successful acquisition is the live connectivity check.

The `Unicorn-BCI-Core-Recorder` folder contains the **BCI Core** recorder manual and
C# LSL/UDP receiver examples, not the recorder executable or Hybrid Black server.
Its recorder is installed through g.tec Suite. BCI Core and Hybrid Black are
different devices: the supplied `gp.BCICore(...)` example is not the source to use
for a Hybrid Black. This backend talks directly to the headset; do not run a
vendor recorder against the same headset simultaneously.

If discovery reports `BLUETOOTH_SOCKET_FAILED` / code 3 ("Couldn't initialize
Bluetooth lookup service"), the API is running but the native SDK cannot initialize
Bluetooth. Check the adapter in Device Manager, Bluetooth drivers and pairing;
verify `Get-Service bthserv` reports Running. A running service alone does not
guarantee a compatible adapter.

## Install and start

Use 64-bit Python 3.12 (the validated interpreter), from this folder:

```powershell
python -m venv .venv
<<<<<<< Updated upstream
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
=======
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

# Score every S*.mat in backend\resources\unicorn-bi. Prints one AUC per file.
.\backend\scripts\score.ps1

# Same scorer, one file.
.\backend\scripts\score.ps1 backend\resources\unicorn-bi\S1.mat

# Fit an LDA on those files and write backend\model.joblib. That file is gitignored.
.\backend\scripts\train.ps1

# Headset WebSocket. Pair the Unicorn in Windows Bluetooth first.
.\backend\scripts\stream.ps1

# MongoDB API. Copy backend\.env.example to backend\.env and fill it in first.
.\backend\scripts\ingest.ps1

# Decoder unit tests, then the headset tests. Add -Mongo to include ingestion tests.
.\backend\scripts\test.ps1
>>>>>>> Stashed changes
```

Edit `.env` locally; it is gitignored. For Atlas, set:

<<<<<<< Updated upstream
```dotenv
MONGODB_URI=mongodb+srv://<username>:<URL-encoded-password>@<cluster-host>/?retryWrites=true&w=majority
MONGODB_DATABASE=hackthenest
UNICORN_SERIAL=
=======
Direct module commands, if you are not using the scripts:

```powershell
python -m backend.decoder.live_decoder
python -m backend.decoder.live_decoder --train --output backend\model.joblib
python backend\run.py
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
>>>>>>> Stashed changes
```

Use your Atlas hostname, database user and password, not the angle-bracket
placeholders. Percent-encode reserved characters in username/password (for example
`@` becomes `%40`). Give the database user read/write permissions for this
database and allow **your current public IP** in Atlas Network Access. Do not
commit credentials or paste them into chat. Environment variables override `.env`.

Leave `MONGODB_URI` empty for **streaming only**. When a URI is configured, MongoDB
must be reachable before acquisition starts; a storage failure does not silently
fall back to streaming-only mode. Device registration also requires MongoDB.

Start the server:

```powershell
.\.venv\Scripts\python.exe run.py
```

Open `http://127.0.0.1:8000/docs` for the interactive API. Keep a **single server
process**, bound to loopback (no reload or multiple workers). These local control
endpoints have no authentication; do not expose the server publicly.

## Discover, register, collect

<<<<<<< Updated upstream
In another PowerShell terminal:

```powershell
$api = "http://127.0.0.1:8000"
Invoke-RestMethod "$api/api/devices"
=======
Each S1-S5 file in `backend/resources/unicorn-bi` contains `fs=250`, `y` (samples x 8), and aligned `trig` (-1 non-target, 0 no trigger, +1 target). Together: **304,269 samples**, **2,434,152 values**, **1,220 chunks**, **750 target** and **5,250 non-target** markers. All source amplitudes are preserved without filtering or unit conversion.

The supplied montage defines `[Fz, Cz, P3, Pz, P4, PO7, PO8, Oz]`. This is source configuration, not embedded MAT metadata. Do not substitute the frontend's different channel labels. The TVLDA abstract describes the matching eight-channel, 250 Hz Unicorn experiment; the older P300 paper's 256 Hz g.USBamp settings are not applied. The dataset information sheet mentions four subjects, but the overview and files include S5.

**No verified acquisition dates exist in these files.** MATLAB export dates, file modification dates, and import dates must not become recording dates. Units remain `unknown` until supported by evidence.

## Inspect/import

Inspection requires neither dates nor database credentials:

```powershell
$files = Get-ChildItem backend\resources\unicorn-bi\S*.mat
backend\.venv\Scripts\python.exe -m backend.importer @($files.FullName)
```
>>>>>>> Stashed changes

# Replace this with a serial returned above.
$device = @{ serial = "UN-1234" } | ConvertTo-Json
Invoke-RestMethod "$api/api/device/register" -Method Post -ContentType "application/json" -Body $device
Invoke-RestMethod "$api/api/acquisition/start" -Method Post -ContentType "application/json" -Body $device
Invoke-RestMethod "$api/api/status"

# Stop acquisition, flush queued database writes and finalize the session.
Invoke-RestMethod "$api/api/acquisition/stop" -Method Post
```

Registration upserts the paired serial into MongoDB's `devices` collection; it
does not perform Windows Bluetooth pairing and is optional for acquisition.
Starting with no JSON body selects `UNICORN_SERIAL` if set, otherwise the only
paired device. Multiple paired devices require explicit selection.

- `POST /api/acquisition/start` starts acquisition and database collection
  **without any WebSocket client**.
- `POST /api/acquisition/stop` stops/releases the device and flushes recording.
- `POST /api/device/connect` and `/api/device/disconnect` are compatibility
  aliases for start/stop, not separate idle connection states.
- `GET /api/status` reports device state and storage configuration, current/last
  session ID, confirmed persisted block/sample counts and errors.
- `WS /ws/eeg`: send `{"action":"start"}` first, then `{"action":"stop"}` to end
  viewing. Only one viewer is allowed. If HTTP already started collection, viewer
  stop/disconnect **does not stop collection**; use the HTTP stop endpoint.
  If the WebSocket starts acquisition itself, viewer stop/disconnect stops it,
  preserving the original streaming workflow.

If status reports an acquisition or storage error, stop the session, resolve the
cause and start a new one. No samples for ten seconds is reported as a device
error rather than remaining apparently connected. Errors are not auto-recovered.
Ctrl+C performs normal device shutdown and flushes recording.

## Stored data and backpressure

`sessions` contains session UUID, selected serial, channel/rate/unit/filter
metadata, start/stop UTC times, completion/error state and persisted counts.
`eeg_blocks` stores one document per filtered 25-sample block, with session ID,
sample index, sample count, host receive UTC timestamp and a samples-by-8 array.
A unique `(session_id, sample_index_start)` index separates/order-checks blocks.
Indices restart at zero for each session. These are **filtered EEG only**, not raw
EEG, hardware timestamps, battery telemetry or hardware packet-loss measurements.
`devices` is the serial-keyed device registry.

The 32-block viewer buffer can discard the oldest block; frames report
`dropped_blocks_total` for **viewer-buffer** loss only. MongoDB receives blocks
independently, before that buffer, so slow or absent viewers do not lose database
data. Its separate 64-block recording queue never silently drops on overflow:
write failure/overflow reports an error and marks the session incomplete when
finalized. Stop flushes accepted blocks on a healthy database; after a writer
error, pending unsaved blocks are discarded and the error is retained. No offline
disk spool or retry/replay is implemented. A forced process kill cannot flush or
finalize sessions; an interrupted session can remain marked `recording`.

## Why 0.5-30 Hz?

This is a reasonable band for general EEG rhythm work: delta, theta, alpha and
most beta, with slow drift and higher-frequency muscle/line noise attenuated.
It excludes gamma/high beta above 30 Hz; choose a different band if the experiment
requires those. Filtering does not remove all eye/motion/muscle artifacts.

Cutoffs are not brick walls: the amplitude at 0.5 and 30 Hz is about -3 dB, and an
order-2 filter leaves some 50/60 Hz energy. Separate mains notches are usually
unnecessary for a 30 Hz upper cutoff, but can be warranted by measured residual
line noise; neither 50 nor 60 Hz notch is applied by default. The causal filter
preserves state across blocks but introduces phase delay and startup transients;
allow several seconds to settle. A Qt `MainApp`/scope is not needed by this
headless backend.

## Validation

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Tests cover device selection/discovery errors, lifecycle, standalone collection,
MongoDB document writes/session finalization and explicit failure/backpressure
(with an injected client), plus the actual g.Pype filter's cutoff response, drift
rejection and continuity across blocks. Real Bluetooth acquisition and Atlas
connectivity still require the paired hardware and valid local credentials.
