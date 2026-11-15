# Changelog

Newest entries are at the top.

## 1.0.4

- Decoder scripts and tests read `S1.mat`–`S5.mat` from `backend/resources/unicorn-bi`. They no longer look outside the repo.
- `python -m backend.decoder.live_decoder` with no paths scores that folder.

## 1.0.3 
- Inteegrated P300 decoder, the Unicorn WebSocket, and the MongoDB importer now live together under `backend/`. `app/` is only the frontend.

### Added

- `decoder/`: causal 0.5–30 Hz filter, shrunk LDA, MAT replay, and the 6×6 row/column board. The single file that was `app/live_decoder.py` is this package.
- `scripts/`: PowerShell commands for scoring recordings, training a model, starting the headset stream, starting ingestion, and running the local tests.
- `CHANGELOG.md`.

### Changed

- `requirements.txt` installs the ingestion stack, `gpype[devices]`, and `scikit-learn` together. `scipy` is no longer pinned to 1.15.3, so it does not downgrade the SciPy that g.Pype installed.
- `tests/conftest.py` puts the repo root and `backend/` on `sys.path`, so one pytest run can import both `backend` and `eeg_stream`.
- `run.py` adds `backend/` to `sys.path` before starting Uvicorn, so `python backend\run.py` works from the repo root.
- `*.joblib` is ignored. A trained decoder saved by `scripts\train.ps1` stays local.

### Kept separate

- The decoder trains on raw MAT samples and applies its own fourth-order filter. `eeg_stream` already bandpasses with a second-order g.Pype filter. Do not score those WebSocket frames with the decoder.
- The headset WebSocket and the ingestion API both bind port 8000.
- Recording channel order is Fz, Cz, P3, Pz, P4, PO7, PO8, Oz. The frontend topology section uses a different eight names.

## 1.0.2 
- MAT ingestion and MongoDB
- create a recording, append chunks, complete it, and page samples back.
- `importer.py` reads `S1.mat`–`S5.mat` (`fs`, `y`, `trig`) without filtering or inventing a recording date.
- `sender.py` queues live batches in SQLite and retries them against the API.
- Tests cover normalization, the API, and the sender. MongoDB integration runs only when `EEG_TEST_MONGODB_URI` is set.

## 1.0.1
- Unicorn WebSocket
- `eeg_stream/` opens a Unicorn Hybrid Black through g.Pype, keeps eight EEG channels at 250 Hz, and applies a causal 0.5–30 Hz bandpass.
- `GET /api/status`, `POST /api/device/connect`, `POST /api/device/disconnect`, and `WS /ws/eeg` on `127.0.0.1:8000`.
- Hardware-free tests cover the device, the filter, and the WebSocket.

## 1.0.0
- Implemente decoder with a causal bandpass, flash epochs from 100 ms before a trigger to 700 ms after, and a shrunk LDA.
- Self-test replayed `S1.mat`–`S5.mat` in 32-sample chunks and printed a leave-one-character AUC.
