# Backend

Three pieces share this folder. They are not one process. History is in [CHANGELOG.md](CHANGELOG.md).

| Piece | What it does | Local script |
| --- | --- | --- |
| `decoder/` | Causal 0.5–30 Hz filter and shrunk LDA on the S1–S5 MAT files. | `.\backend\scripts\score.ps1` |
| `eeg_stream/` | g.Pype acquisition from a Unicorn Hybrid Black. Frames are already bandpassed. WebSocket on port 8000. | `.\backend\scripts\stream.ps1` |
| Ingestion, below | Stores raw MAT samples and triggers in MongoDB. No filtering. | `.\backend\scripts\ingest.ps1` |

The decoder trains on raw samples and applies its own fourth-order filter. `eeg_stream` already filters with a second-order g.Pype bandpass, so those WebSocket frames must not be passed into the decoder. The headset service and the ingestion API cannot both bind port 8000.

Channel order for the recordings and the decoder is Fz, Cz, P3, Pz, P4, PO7, PO8, Oz. The frontend topology section shows a different eight-name set and is not the montage of these files.

## Local commands

From the repo root in PowerShell. If script execution is disabled for the current window:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

Scripts use `HackTheNest\.venv` when it exists, otherwise `backend\.venv`.

```powershell
# Install once. The repo-root venv is the one the scripts find first.
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

# Score every S*.mat under ..\sources\p300-speller. Prints one AUC per file.
.\backend\scripts\score.ps1

# Same scorer, one file.
.\backend\scripts\score.ps1 ..\sources\p300-speller\S1.mat

# Fit an LDA on those files and write backend\model.joblib. That file is gitignored.
.\backend\scripts\train.ps1

# Headset WebSocket. Pair the Unicorn in Windows Bluetooth first.
.\backend\scripts\stream.ps1

# MongoDB API. Copy backend\.env.example to backend\.env and fill it in first.
.\backend\scripts\ingest.ps1

# Decoder unit tests, then the headset tests. Add -Mongo to include ingestion tests.
.\backend\scripts\test.ps1
```

What each service then exposes:

- Decoder score: no server. The script prints `live-replay AUC` and exits.
- Headset: `http://127.0.0.1:8000`. `GET /api/status`, `POST /api/device/connect`, `POST /api/device/disconnect`, `WS /ws/eeg`. The first WebSocket message must be `{"action":"start"}`.
- Ingestion: `http://127.0.0.1:8000`. Routes are under `/v1/recordings` and require `Authorization: Bearer <EEG_API_TOKEN>`. Schema docs are at `/docs`.

Direct module commands, if you are not using the scripts:

```powershell
python -m backend.decoder.live_decoder ..\sources\p300-speller\S1.mat
python -m backend.decoder.live_decoder --train ..\sources\p300-speller\S1.mat --output backend\model.joblib
python backend\run.py
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

# EEG ingestion

Python 3.10+ backend for historical P300 MAT imports and future eight-electrode batches. The Unicorn WebSocket above is the hardware acquisition path. This service stores samples. Frontend login is not wired to it.

## Setup

The scripts in `scripts/` use the repo-root `.venv` when it exists, and `backend\.venv` otherwise. Create the second venv only when you want ingestion isolated from the decoder.

From the repository root in PowerShell:

```powershell
python -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
```

Edit the ignored `backend\.env` locally. Never paste passwords into chat or commit them. Set `MONGODB_URI` to your Atlas SRV URI, substituting a **URL-encoded** password, and select `MONGODB_DATABASE`. Set a random `EEG_API_TOKEN` of at least 32 characters and an opaque `EEG_OWNER_ID`. The token authenticates the sender to this API; it is not the database password.

Atlas/replica-set transactions are required. Allowlist the backend's network address in Atlas. Startup provisions strict validators/indexes, so provisioning permissions are needed; use a dedicated database account and restrict access to this database. Run only one sender process per SQLite queue. Deploy behind HTTPS with request/header timeouts; plain HTTP is allowed by the sender only on loopback.

```powershell
backend\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Set `EEG_API_URL=http://127.0.0.1:8000` locally, or your deployed HTTPS API URL. The frontend never connects directly to MongoDB.

## What the supplied files contain

Each S1-S5 file contains `fs=250`, `y` (samples x 8), and aligned `trig` (-1 non-target, 0 no trigger, +1 target). Together: **304,269 samples**, **2,434,152 values**, **1,220 chunks**, **750 target** and **5,250 non-target** markers. All source amplitudes are preserved without filtering or unit conversion.

The supplied montage defines `[Fz, Cz, P3, Pz, P4, PO7, PO8, Oz]`. This is source configuration, not embedded MAT metadata. Do not substitute the frontend's different channel labels. The TVLDA abstract describes the matching eight-channel, 250 Hz Unicorn experiment; the older P300 paper's 256 Hz g.USBamp settings are not applied. The dataset information sheet mentions four subjects, but the overview and files include S5.

**No verified acquisition dates exist in these files.** MATLAB export dates, file modification dates, and import dates must not become recording dates. Units remain `unknown` until supported by evidence.

## Inspect/import

Inspection requires neither dates nor database credentials:

```powershell
$files = Get-ChildItem 'C:\PATH\TO\p300-speller\S*.mat'
backend\.venv\Scripts\python.exe -m backend.importer @($files.FullName)
```

Copy `manifest.example.json` to an ignored `manifest.local.json`. Add entries for every selected file, keyed by exact filename, with a distinct pseudonymous subject ID. Replace each null `recordingStartedAt` with the **verified first-sample timestamp**, including UTC offset; set the original timezone/offset, evidence, and honest clock precision. Starts must align to milliseconds because BSON Date has millisecond precision. Do not leave placeholder timezone/evidence. The example intentionally cannot be imported.

```powershell
backend\.venv\Scripts\python.exe -m backend.importer @($files.FullName) --manifest backend\manifest.local.json --import-data
```

Every selected file is preflighted before any write. The importer registers metadata, sends fixed windows (250 samples here, final short tail preserved), reads all samples back to compare every value/trigger/time, and then finalizes. Re-running unchanged files/configuration resumes through duplicate-safe acknowledgments. An error exits nonzero; already acknowledged chunks remain available for retry.

## Standard document contract

`eeg_recordings`: immutable source configuration and time origin, UUID ID, server-authorized owner, pseudonymous subject, source SHA-256, ordered eight labels, rate, units/evidence, device metadata, start time/evidence, ingestion times, lifecycle status, and finalized counts.

`eeg_chunks`: one immutable source-index window, unique `(recordingId, chunkIndex)`, index coverage, actual count, final-window flag, first/last acquisition timestamps, receipt timestamp, missing index ranges, canonical content hash, and samples:

```json
{
  "sampleIndex": 1,
  "timestamp": "2024-01-01T00:00:00.004Z",
  "offsetNs": 4000000,
  "values": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
  "trigger": 0
}
```

This timestamp/data is **synthetic illustration only**, not an acquisition date for S1-S5. Value position i maps to recording channel i. Trigger null means the source does not supply triggers; zero means it supplied a no-trigger value.

For a uniform clock, offset is rounded directly from `index * 1e9 / fs`, never accumulated from rounded intervals. `timestamp` is the recording UTC start plus the offset, floored to BSON milliseconds. `offsetNs` is stored as BSON Int64 for precise relative timing; it does not imply an equally precise absolute clock. At 250 Hz, timestamps are exactly 4 ms apart.

For `source_offsets`, acquisition software supplies increasing source indices and elapsed offsets from a verified UTC anchor. Timing is not inferred from network arrival. Missing samples become explicit ranges, including fully missing windows; no zero-filling. Completion requires consistent counts/coverage and explicit permission for gaps.

Rate is bounded to **2000 Hz**, payload/BSON size to **1 MiB**, and each sample to exactly eight finite floating values. Larger configurations are rejected explicitly. Existing recordings cannot change channel order, rate, time origin, or units; use a new recording revision.

MongoDB enforces BSON types and required document structure. Cross-document ownership, clock relationships, window coverage and completion are validated in Python. Transactions update recording revision alongside inserts/finalization, serializing concurrent writes. Exact retries succeed; different content under the same recording/chunk key returns 409. Recording completion does not permit new chunks, but acknowledges existing identical retries. No TTL deletion is configured.

## API

All routes require `Authorization: Bearer <EEG_API_TOKEN>`. Owner comes only from server configuration; clients provide a pseudonymous subject, not an arbitrary owner.

- `POST /v1/recordings`: `Recording` schema, including retry-stable UUID.
- `POST /v1/recordings/{id}/chunks`: `{"chunkIndex": 0, "finalWindow": false, "samples": [...]}`.
- `POST /v1/recordings/{id}/complete`: `expectedSampleCount`, `expectedLastSampleIndex`, optional `allowGaps` (false by default).
- `GET /v1/recordings?after=<id>&limit=20`: ID-ordered pagination.
- `GET /v1/recordings/{id}/samples?after=-1&limit=500`: source-index pagination; optional timezone-aware `start` inclusive / `end` exclusive.

Sample responses include `nextAfter`; pass it as `after` until it is null. Maximum page size is 2000 samples (100 recordings). Validation: 422; oversized body: 413; unauthorized: 401; missing/cross-owner recording: 404; conflicting retry/closed recording: 409; Mongo failure: 503. API validation errors do not echo raw signal inputs. Interactive schema docs are at `/docs`.

## Live sender

Existing acquisition software constructs a validated `Recording` with source kind `live`, actual rate/channels/units, verified first-sample UTC time, and timestamp derivation. Construct `Sample` objects with real source indices and offsets; do not supply server receipt timestamps.

```python
from pathlib import Path
from backend.sender import ApiClient, LiveSender

# recording and samples come from your acquisition adapter; secrets come from env.
sender = LiveSender(api, recording, Path("backend") / "live.sqlite3")
try:
    sender.feed(samples)
    sender.drain()
    # At the actual end of acquisition:
    sender.finish()
finally:
    sender.close()
```

Feed continuously and call `drain()` regularly. A window is sealed when the next window begins; `finish()` seals the last one. SQLite persists both the partial buffer and unacknowledged windows, including across restarts. Reopen the same queue with identical recording metadata to resume. Feed is incremental: samples before a raised error may already be durably accepted; resume after its saved last source index, never blindly replay the whole feed iterable.

The default pending-data capacity is 16 MiB. Exhaustion raises `BufferError`, requiring acquisition backpressure or a surfaced failure, never silent dropping. Protect the queue file and its directory with local access permissions: it contains sensitive raw EEG, but never tokens/passwords. Delete only the specific recording's queue after confirmed completion according to your retention policy.

## Tests

`.\backend\scripts\test.ps1` runs the decoder unit tests and the headset-stream tests. `.\backend\scripts\test.ps1 -Mongo` also runs the ingestion tests. The MongoDB integration test still needs `EEG_TEST_MONGODB_URI`.

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q
```

Unit/API/sender tests use synthetic times, not fabricated historical metadata. For real BSON/index/transaction tests, configure `EEG_TEST_MONGODB_URI` locally to a **test** Atlas/replica-set deployment. The integration fixture creates and deletes only its uniquely named `eeg_test_<uuid>` database. Integration tests skip explicitly when this variable is absent.

Historical production imports require verified recording dates and a reachable configured API/database; passing unit tests is not evidence that an Atlas import succeeded.
