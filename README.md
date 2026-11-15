Welcome to TopNest Group - HackTheNest 2026

`app/` is the frontend. Python lives in `backend/`:

- `backend/decoder/` scores the P300 recordings locally.
- `backend/eeg_stream/` streams a paired Unicorn Hybrid Black over a WebSocket.
- [EEG ingestion](backend/README.md) imports the MAT files into MongoDB and accepts live batches.
s
Local PowerShell commands and the backend history are in [backend/README.md](backend/README.md) and [backend/CHANGELOG.md](backend/CHANGELOG.md). From the repo root, `.\backend\scripts\score.ps1` scores the MAT files.

The ingestion API and the headset WebSocket both listen on port 8000. Run one at a time.