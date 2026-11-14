from datetime import datetime, timedelta

import numpy as np
import pytest
from scipy.io import savemat

from backend.importer import chunks_from_mat, read_mat, recording_from_manifest
from backend.schemas import Chunk, Recording, Sample, normalize_chunk, offset_ns
from backend.storage import Conflict, reconcile
from backend.schemas import Completion
from backend.tests.conftest import make_sample


def test_time_origin_and_submillisecond_clock(recording):
    chunk = normalize_chunk(recording, Chunk(
        chunkIndex=1, finalWindow=True, samples=[make_sample(recording, 250)]))
    assert chunk["samples"][0]["timestamp"] == recording.recordingStartedAt + timedelta(seconds=1)
    assert chunk["missingSampleRanges"] == []
    fields = recording.model_dump()
    fields["sampleRateHz"] = 256
    faster = Recording(**fields)
    sample = make_sample(faster, 1)
    assert sample.offsetNs == 3_906_250
    assert sample.timestamp == faster.recordingStartedAt + timedelta(milliseconds=3)
    assert offset_ns(256 * 60 * 60, 256) == 3_600_000_000_000
    normalize_chunk(faster, Chunk(chunkIndex=0, samples=[sample]))


@pytest.mark.parametrize("start", [datetime(2024, 1, 1), "2024-01-01T00:00:00.000001Z"])
def test_unusable_absolute_start_rejected(recording, start):
    with pytest.raises(ValueError, match="timezone|millisecond"):
        Recording(**{**recording.model_dump(), "recordingStartedAt": start})


@pytest.mark.parametrize("changes", [
    {"values": [0.0] * 7}, {"values": [0.0] * 9},
    {"values": [float("nan")] * 8}, {"values": [float("inf")] * 8},
    {"values": [True] * 8}, {"values": ["1"] * 8},
    {"trigger": 2}, {"trigger": True}, {"sampleIndex": 0.5},
])
def test_invalid_sample_rejected(recording, changes):
    with pytest.raises(ValueError):
        Sample(**{**make_sample(recording, 0).model_dump(), **changes})


def test_offset_order_timestamp_and_window_rejected(recording):
    sample = make_sample(recording, 1)
    with pytest.raises(ValueError, match="strictly ordered"):
        normalize_chunk(recording, Chunk(chunkIndex=0, samples=[sample, sample]))
    with pytest.raises(ValueError, match="window"):
        normalize_chunk(recording, Chunk(chunkIndex=0, samples=[make_sample(recording, 250)]))
    wrong = sample.model_copy(update={"timestamp": sample.timestamp + timedelta(milliseconds=1)})
    with pytest.raises(ValueError, match="timestamp"):
        normalize_chunk(recording, Chunk(chunkIndex=0, samples=[wrong]))
    wrong = sample.model_copy(update={"offsetNs": sample.offsetNs + 1})
    with pytest.raises(ValueError, match="clock"):
        normalize_chunk(recording, Chunk(chunkIndex=0, samples=[wrong]))


def test_gaps_and_completion(recording):
    chunk = normalize_chunk(recording, Chunk(chunkIndex=0, finalWindow=True,
                                            samples=[make_sample(recording, 0, 1),
                                                     make_sample(recording, 2, -1)]))
    assert chunk["missingSampleRanges"] == [[1, 1]]
    expected = Completion(expectedSampleCount=2, expectedLastSampleIndex=2)
    with pytest.raises(Conflict, match="missing samples"):
        reconcile([chunk], expected, 250)
    result = reconcile([chunk], expected.model_copy(update={"allowGaps": True}), 250)
    assert result["targetCount"] == result["nonTargetCount"] == 1
    with pytest.raises(Conflict, match="count"):
        reconcile([chunk], Completion(expectedSampleCount=3, expectedLastSampleIndex=2), 250)


def test_mat_roundtrip_preserves_values_triggers_and_tail(tmp_path, recording):
    values = np.arange(251 * 8, dtype=float).reshape(251, 8) / 7
    triggers = np.zeros((251, 1), dtype=float)
    triggers[1] = -1
    triggers[250] = 1
    path = tmp_path / "S1.mat"
    savemat(path, {"fs": 250, "y": values, "trig": triggers})
    rate, loaded, labels = read_mat(path)
    assert rate == 250
    chunks = list(chunks_from_mat(recording, loaded, labels))
    assert [len(chunk.samples) for chunk in chunks] == [250, 1]
    assert [chunk.finalWindow for chunk in chunks] == [False, True]
    recovered = np.asarray([sample.values for chunk in chunks for sample in chunk.samples])
    assert np.array_equal(recovered, values)
    assert [sample.trigger for chunk in chunks for sample in chunk.samples] == labels.tolist()
    assert chunks[-1].samples[-1].timestamp == recording.recordingStartedAt + timedelta(seconds=1)


def test_missing_dates_block_manifest_and_identity_is_repeatable(tmp_path, recording):
    path = tmp_path / "S1.mat"
    path.write_bytes(b"test-source")
    with pytest.raises(ValueError, match="verified"):
        recording_from_manifest(path, {}, 250)
    entry = recording.model_dump(mode="json", exclude={
        "recordingId", "source", "sampleRateHz", "schemaVersion"})
    first = recording_from_manifest(path, entry, 250)
    assert first.recordingId == recording_from_manifest(path, entry, 250).recordingId
    path.write_bytes(b"changed-source")
    assert first.recordingId != recording_from_manifest(path, entry, 250).recordingId


@pytest.mark.parametrize("fields", [
    {"fs": 250, "y": np.zeros((2, 7)), "trig": np.zeros((2, 1))},
    {"fs": 250, "y": np.zeros((2, 8)), "trig": np.zeros((1, 1))},
    {"fs": 0, "y": np.zeros((2, 8)), "trig": np.zeros((2, 1))},
    {"fs": 250, "y": np.zeros((2, 8)), "trig": np.full((2, 1), 2)},
])
def test_malformed_mat_is_rejected(tmp_path, fields):
    path = tmp_path / "bad.mat"
    savemat(path, fields)
    with pytest.raises(ValueError):
        read_mat(path)
