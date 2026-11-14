from datetime import datetime, timezone
from uuid import uuid4

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
