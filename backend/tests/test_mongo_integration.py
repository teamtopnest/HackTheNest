import os
from uuid import uuid4

from bson import Int64
from pymongo.errors import WriteError
import pytest

from backend.schemas import Chunk, Completion
from backend.storage import Conflict, MongoStore, NotFound
from backend.tests.conftest import make_sample


@pytest.fixture
def mongo():
    uri = os.environ.get("EEG_TEST_MONGODB_URI")
    if not uri:
        pytest.skip("Set EEG_TEST_MONGODB_URI to a transaction-capable test deployment")
    store = MongoStore(uri, "eeg_test_" + uuid4().hex)
    store.start()
    try:
        yield store
    finally:
        store.client.drop_database(store.db.name)
        store.close()


def test_mongo_roundtrip_idempotency_ownership_and_completion(mongo, recording):
    assert not mongo.create(recording, "owner")["duplicate"]
    assert mongo.create(recording, "owner")["duplicate"]
    chunk = Chunk(chunkIndex=0, finalWindow=True,
                  samples=[make_sample(recording, 0, 1), make_sample(recording, 1, -1)])
    assert not mongo.append(str(recording.recordingId), "owner", chunk)["duplicate"]
    assert mongo.append(str(recording.recordingId), "owner", chunk)["duplicate"]
    with pytest.raises(Conflict):
        mongo.append(str(recording.recordingId), "owner", Chunk(
            chunkIndex=0, finalWindow=True, samples=[make_sample(recording, 0)]))
    with pytest.raises(NotFound):
        mongo.samples(str(recording.recordingId), "other-owner", -1, 500)
    samples = mongo.samples(str(recording.recordingId), "owner", -1, 500)["samples"]
    assert samples == [sample.model_dump() for sample in chunk.samples]
    raw = mongo.db.eeg_chunks.find_one({"recordingId": str(recording.recordingId)})
    assert isinstance(raw["samples"][0]["offsetNs"], Int64)
    expected = Completion(expectedSampleCount=2, expectedLastSampleIndex=1)
    summary = mongo.complete(str(recording.recordingId), "owner", expected)
    assert summary["sampleCount"] == 2
    assert mongo.complete(str(recording.recordingId), "owner", expected) == summary
    with pytest.raises(Conflict):
        mongo.append(str(recording.recordingId), "owner", Chunk(
            chunkIndex=1, samples=[make_sample(recording, 250)]))
    assert mongo.append(str(recording.recordingId), "owner", chunk)["duplicate"]
    malformed = {**raw, "_id": "invalid"}
    malformed["samples"] = [{"values": [1.0] * 7}]
    with pytest.raises(WriteError):
        mongo.db.eeg_chunks.insert_one(malformed)
