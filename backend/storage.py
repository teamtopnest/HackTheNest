from datetime import datetime, timezone
from collections.abc import Iterable
from typing import Any

from bson import BSON, Int64
from pymongo import MongoClient
from pymongo.errors import CollectionInvalid, DuplicateKeyError
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from backend.schemas import Completion, MAX_BODY_BYTES, Recording, Chunk, content_hash, normalize_chunk


class Conflict(Exception):
    pass


class NotFound(Exception):
    pass


def reconcile(chunks: Iterable[dict], expected: Completion, window_size: int) -> dict:
    count = targets = non_targets = 0
    previous_offset = -1
    previous_end = -1
    gaps = []
    chunk_count = 0
    expected_windows = expected.expectedLastSampleIndex // window_size + 1
    for index, chunk in enumerate(chunks):
        if chunk["chunkIndex"] != index or chunk["firstSampleIndex"] != previous_end + 1:
            raise Conflict("Missing chunk windows; recording cannot be completed")
        if chunk["firstSampleIndex"] != index * window_size:
            raise Conflict("Invalid chunk coverage")
        if chunk["finalWindow"] != (index == expected_windows - 1):
            raise Conflict("Exactly the last window must be final")
        for sample in chunk["samples"]:
            if sample["offsetNs"] <= previous_offset:
                raise Conflict("Offsets move backwards across chunk boundaries")
            previous_offset = sample["offsetNs"]
            targets += sample["trigger"] == 1
            non_targets += sample["trigger"] == -1
        count += chunk["sampleCount"]
        gaps.extend(chunk["missingSampleRanges"])
        previous_end = chunk["lastSampleIndex"]
        chunk_count += 1
    if previous_end != expected.expectedLastSampleIndex or count != expected.expectedSampleCount:
        raise Conflict("Stored sample count or last index disagrees with completion request")
    if gaps and not expected.allowGaps:
        raise Conflict("Recording has missing samples; explicit allowGaps is required")
    return {
        "sampleCount": count,
        "lastSampleIndex": previous_end,
        "chunkCount": chunk_count,
        "targetCount": targets,
        "nonTargetCount": non_targets,
        "missingSampleRanges": gaps,
    }


def validators():
    integer = {"bsonType": ["int", "long"], "minimum": 0}
    nullable_date = {"bsonType": ["date", "null"]}
    sample = {
        "bsonType": "object",
        "additionalProperties": False,
        "required": ["sampleIndex", "timestamp", "offsetNs", "values", "trigger"],
        "properties": {
            "sampleIndex": integer,
            "timestamp": {"bsonType": "date"},
            "offsetNs": {"bsonType": "long", "minimum": 0},
            "values": {"bsonType": "array", "minItems": 8, "maxItems": 8,
                       "items": {"bsonType": "double",
                                 "minimum": -1.7976931348623157e308,
                                 "maximum": 1.7976931348623157e308}},
            "trigger": {"bsonType": ["int", "long", "null"], "enum": [-1, 0, 1, None]},
        },
    }
    recording = {
        "bsonType": "object",
        "required": ["_id", "schemaVersion", "ownerId", "subjectId", "source", "channels",
                     "sampleRateHz", "signalUnit", "recordingStartedAt", "timeBase",
                     "chunkSampleCount", "status", "createdAt", "updatedAt", "metadataHash"],
        "properties": {
            "_id": {"bsonType": "string"},
            "schemaVersion": {"enum": [1]},
            "ownerId": {"bsonType": "string"},
            "subjectId": {"bsonType": "string"},
            "source": {"bsonType": "object"},
            "channels": {"bsonType": "array", "minItems": 8, "maxItems": 8,
                         "uniqueItems": True, "items": {"bsonType": "string"}},
            "sampleRateHz": {"bsonType": "double", "minimum": 0, "exclusiveMinimum": True},
            "signalUnit": {"enum": ["unknown", "uV", "V", "adc_count"]},
            "recordingStartedAt": {"bsonType": "date"},
            "timeBase": {"bsonType": "object"},
            "chunkSampleCount": integer,
            "status": {"enum": ["importing", "streaming", "complete", "failed"]},
            "createdAt": {"bsonType": "date"},
            "updatedAt": {"bsonType": "date"},
            "metadataHash": {"bsonType": "string"},
        },
    }
    properties = {
        "_id": {"bsonType": "string"},
        "schemaVersion": {"enum": [1]},
        "recordingId": {"bsonType": "string"},
        "chunkIndex": integer,
        "firstSampleIndex": integer,
        "lastSampleIndex": integer,
        "sampleCount": integer,
        "finalWindow": {"bsonType": "bool"},
        "startedAt": nullable_date,
        "endedAt": nullable_date,
        "receivedAt": {"bsonType": "date"},
        "firstOffsetNs": {"bsonType": ["long", "null"]},
        "lastOffsetNs": {"bsonType": ["long", "null"]},
        "samples": {"bsonType": "array", "maxItems": 2000, "items": sample},
        "missingSampleRanges": {"bsonType": "array", "items": {
            "bsonType": "array", "minItems": 2, "maxItems": 2, "items": integer}},
        "contentHash": {"bsonType": "string"},
    }
    chunk = {"bsonType": "object", "additionalProperties": False,
             "required": list(properties), "properties": properties}
    return {"eeg_recordings": {"$jsonSchema": recording},
            "eeg_chunks": {"$jsonSchema": chunk}}


class MongoStore:
    def __init__(self, uri: str, database: str):
        self.client = MongoClient(
            uri, tz_aware=True, serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000, socketTimeoutMS=20000, retryWrites=True,
        )
        self.db = self.client.get_database(database, write_concern=WriteConcern("majority"))

    def start(self):
        hello = self.client.admin.command("hello")
        if not hello.get("setName") and hello.get("msg") != "isdbgrid":
            raise RuntimeError("EEG ingestion requires transaction-capable Atlas or a replica set")
        for name, validator in validators().items():
            try:
                self.db.create_collection(name, validator=validator, validationAction="error")
            except CollectionInvalid:
                self.db.command("collMod", name, validator=validator,
                                validationLevel="strict", validationAction="error")
        self.db.eeg_recordings.create_index(
            [("ownerId", 1), ("subjectId", 1), ("recordingStartedAt", 1)])
        self.db.eeg_recordings.create_index([("ownerId", 1), ("_id", 1)])
        self.db.eeg_chunks.create_index([("recordingId", 1), ("chunkIndex", 1)], unique=True)
        self.db.eeg_chunks.create_index([("recordingId", 1), ("firstSampleIndex", 1)])

    def close(self):
        self.client.close()

    def _recording(self, recording_id: str, owner: str, session=None):
        doc = self.db.eeg_recordings.find_one(
            {"_id": recording_id, "ownerId": owner}, session=session)
        if doc is None:
            raise NotFound("Recording not found")
        return doc

    @staticmethod
    def _model(doc: dict) -> Recording:
        fields = {key: doc[key] for key in Recording.model_fields if key != "recordingId"}
        return Recording(recordingId=doc["_id"], **fields)

    def create(self, recording: Recording, owner: str):
        request = recording.model_dump(mode="json")
        identity = content_hash(request)
        now = datetime.now(timezone.utc)
        document = recording.model_dump(exclude={"recordingId"})
        document.update(
            _id=str(recording.recordingId), ownerId=owner, metadataHash=identity,
            chunkSampleCount=recording.chunk_sample_count,
            status="importing" if recording.source.kind == "mat" else "streaming",
            createdAt=now, updatedAt=now, revision=0,
        )
        try:
            self.db.eeg_recordings.insert_one(document)
        except DuplicateKeyError:
            existing = self._recording(str(recording.recordingId), owner)
            if existing["metadataHash"] != identity:
                raise Conflict("Recording ID already has different metadata")
            return {"recordingId": existing["_id"], "duplicate": True}
        return {"recordingId": document["_id"], "duplicate": False}

    def append(self, recording_id: str, owner: str, chunk: Chunk):
        def write(session):
            recording_doc = self._recording(recording_id, owner, session)
            doc = normalize_chunk(self._model(recording_doc), chunk)
            existing = self.db.eeg_chunks.find_one({"_id": doc["_id"]}, session=session)
            if existing:
                if existing["contentHash"] != doc["contentHash"]:
                    raise Conflict("Chunk retry has different content")
                return {"chunkIndex": chunk.chunkIndex, "duplicate": True}
            if recording_doc["status"] not in ("importing", "streaming"):
                raise Conflict("Recording is not open for new chunks")
            terminal = recording_doc.get("terminalChunkIndex")
            if terminal is not None and chunk.chunkIndex > terminal:
                raise Conflict("Chunk follows the final window")
            if chunk.finalWindow:
                if terminal is not None and terminal != chunk.chunkIndex:
                    raise Conflict("Recording already has a different final window")
                if self.db.eeg_chunks.find_one(
                    {"recordingId": recording_id, "chunkIndex": {"$gt": chunk.chunkIndex}},
                    session=session,
                ):
                    raise Conflict("Final window precedes stored data")
            if doc["samples"]:
                for direction, sort, boundary in (
                    ("$lt", -1, "lastOffsetNs"), ("$gt", 1, "firstOffsetNs")
                ):
                    neighbor = self.db.eeg_chunks.find_one(
                        {"recordingId": recording_id,
                         "chunkIndex": {direction: chunk.chunkIndex},
                         boundary: {"$ne": None}},
                        sort=[("chunkIndex", sort)], session=session,
                    )
                    if neighbor and (
                        (direction == "$lt" and neighbor[boundary] >= doc["firstOffsetNs"])
                        or (direction == "$gt" and neighbor[boundary] <= doc["lastOffsetNs"])
                    ):
                        raise Conflict("Offsets move backwards across chunk boundaries")
            doc["receivedAt"] = datetime.now(timezone.utc)
            for sample in doc["samples"]:
                sample["offsetNs"] = Int64(sample["offsetNs"])
            for key in ("firstOffsetNs", "lastOffsetNs"):
                if doc[key] is not None:
                    doc[key] = Int64(doc[key])
            if len(BSON.encode(doc)) > MAX_BODY_BYTES:
                raise ValueError("Serialized chunk exceeds the 1 MiB storage limit")
            self.db.eeg_chunks.insert_one(doc, session=session)
            update: dict[str, Any] = {"updatedAt": doc["receivedAt"]}
            if chunk.finalWindow:
                update["terminalChunkIndex"] = chunk.chunkIndex
            self.db.eeg_recordings.update_one(
                {"_id": recording_id}, {"$inc": {"revision": 1}, "$set": update},
                session=session,
            )
            return {"chunkIndex": chunk.chunkIndex, "duplicate": False}
        return self._transaction(write)

    def complete(self, recording_id: str, owner: str, expected: Completion):
        def finish(session):
            recording = self._recording(recording_id, owner, session)
            if recording["status"] == "failed":
                raise Conflict("Failed recording cannot be finalized")
            chunks = self.db.eeg_chunks.find(
                {"recordingId": recording_id},
                {"chunkIndex": 1, "firstSampleIndex": 1, "lastSampleIndex": 1,
                 "sampleCount": 1, "finalWindow": 1, "missingSampleRanges": 1,
                 "samples.offsetNs": 1, "samples.trigger": 1},
                session=session).sort("chunkIndex", 1)
            summary = reconcile(chunks, expected, recording["chunkSampleCount"])
            if len(BSON.encode(summary)) > MAX_BODY_BYTES:
                raise Conflict("Completion gap summary exceeds the 1 MiB limit")
            self.db.eeg_recordings.update_one(
                {"_id": recording_id},
                {"$set": {"status": "complete", "summary": summary,
                          "updatedAt": datetime.now(timezone.utc)},
                 "$inc": {"revision": 1}}, session=session)
            return summary
        return self._transaction(finish)

    def _transaction(self, callback):
        with self.client.start_session() as session:
            return session.with_transaction(
                callback, read_concern=ReadConcern("snapshot"),
                write_concern=WriteConcern("majority", wtimeout=10000))

    def recordings(self, owner: str, after: str, limit: int):
        documents = list(self.db.eeg_recordings.find(
            {"ownerId": owner, "_id": {"$gt": after}},
            {"metadataHash": 0, "revision": 0}).sort("_id", 1).limit(limit))
        return {"recordings": documents,
                "nextAfter": documents[-1]["_id"] if len(documents) == limit else None}

    def samples(self, recording_id: str, owner: str, after: int, limit: int,
                start: datetime | None = None, end: datetime | None = None):
        self._recording(recording_id, owner)
        sample_filter: dict[str, Any] = {"samples.sampleIndex": {"$gt": after}}
        if start is not None or end is not None:
            sample_filter["samples.timestamp"] = {}
            if start is not None:
                sample_filter["samples.timestamp"]["$gte"] = start
            if end is not None:
                sample_filter["samples.timestamp"]["$lt"] = end
        pipeline = [
            {"$match": {"recordingId": recording_id, "lastSampleIndex": {"$gt": after}}},
            {"$sort": {"firstSampleIndex": 1}},
            {"$unwind": "$samples"}, {"$match": sample_filter},
            {"$limit": limit}, {"$replaceRoot": {"newRoot": "$samples"}},
        ]
        result = list(self.db.eeg_chunks.aggregate(pipeline))
        return {"samples": result,
                "nextAfter": result[-1]["sampleIndex"] if len(result) == limit else None}
