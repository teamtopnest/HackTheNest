import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

# Ingestion imports `backend` from the repo root. The headset stream imports
# `eeg_stream` with the backend directory on the path. One pytest run needs both.
_backend_dir = Path(__file__).resolve().parent.parent
_repo_root = _backend_dir.parent
for _entry in (str(_repo_root), str(_backend_dir)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

import pytest

from backend.schemas import Recording, Sample, offset_ns, sample_timestamp


@pytest.fixture
def recording():
    return Recording(
        recordingId=uuid4(), subjectId="test:subject",
        source={"kind": "live", "identifier": "test-device", "format": "test"},
        channels=["Fz", "Cz", "P3", "Pz", "P4", "PO7", "PO8", "Oz"],
        sampleRateHz=250, recordingStartedAt=datetime(2024, 1, 1, tzinfo=timezone.utc),
        timeBase={"originalTimezone": "UTC", "evidence": "synthetic test clock",
                  "derivation": "uniform_sample_clock", "precisionMs": 1},
    )


def make_sample(recording, index, trigger=None):
    offset = offset_ns(index, recording.sampleRateHz)
    return Sample(sampleIndex=index, offsetNs=offset,
                  timestamp=sample_timestamp(recording.recordingStartedAt, offset),
                  values=[float(index + i) for i in range(8)], trigger=trigger)
