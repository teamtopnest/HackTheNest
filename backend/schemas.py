from datetime import datetime, timedelta, timezone
from fractions import Fraction
from hashlib import sha256
import json
import math
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


MAX_BODY_BYTES = 1_048_576
MAX_CHUNK_SAMPLES = 2_000
Index = Annotated[int, Field(strict=True, ge=0, le=2**53 - 1)]
Value = Annotated[float, Field(allow_inf_nan=False)]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Source(Model):
    kind: Literal["mat", "live"]
    identifier: str = Field(min_length=1, max_length=200)
    filename: str | None = Field(default=None, max_length=200)
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    format: str = Field(min_length=1, max_length=100)
    importerVersion: str = Field(default="1", max_length=50)

    @model_validator(mode="after")
    def require_mat_identity(self):
        if self.kind == "mat" and (not self.filename or not self.sha256):
            raise ValueError("MAT sources require filename and SHA-256")
        return self


class TimeBase(Model):
    originalTimezone: str = Field(min_length=1, max_length=100)
    evidence: str = Field(min_length=1, max_length=500)
    derivation: Literal["uniform_sample_clock", "source_offsets"]
    precisionMs: float = Field(gt=0, allow_inf_nan=False)

    @field_validator("originalTimezone", "evidence")
    @classmethod
    def reject_placeholders(cls, value):
        if value.startswith("REPLACE_") or not value.strip():
            raise ValueError("Provide verified timezone/evidence, not a placeholder")
        return value


class Recording(Model):
    recordingId: UUID
    schemaVersion: Literal[1] = 1
    subjectId: str = Field(min_length=1, max_length=200)
    source: Source
    device: dict[str, str] = Field(default_factory=dict, max_length=20)
    channels: list[str] = Field(min_length=8, max_length=8)
    sampleRateHz: float = Field(gt=0, le=MAX_CHUNK_SAMPLES, allow_inf_nan=False)
    signalUnit: Literal["unknown", "uV", "V", "adc_count"] = "unknown"
    unitEvidence: str | None = Field(default=None, max_length=500)
    recordingStartedAt: datetime
    timeBase: TimeBase

    @field_validator("channels")
    @classmethod
    def validate_channels(cls, labels):
        if any(not label.strip() or len(label) > 32 for label in labels):
            raise ValueError("Each electrode requires a nonempty label of at most 32 characters")
        if len(set(labels)) != 8:
            raise ValueError("Electrode labels must be unique")
        return labels

    @field_validator("recordingStartedAt")
    @classmethod
    def verified_utc(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Verified recording start must include a timezone")
        value = value.astimezone(timezone.utc)
        if value.microsecond % 1000:
            raise ValueError("Recording start must be millisecond-aligned for BSON Date")
        return value

    @model_validator(mode="after")
    def verified_units(self):
        if self.signalUnit != "unknown" and not self.unitEvidence:
            raise ValueError("Verified units require unitEvidence")
        return self

    @property
    def chunk_sample_count(self):
        return math.ceil(self.sampleRateHz)


class Sample(Model):
    sampleIndex: Index
    timestamp: datetime
    offsetNs: Annotated[int, Field(strict=True, ge=0, le=2**63 - 1)]
    values: list[Value] = Field(min_length=8, max_length=8)
    trigger: Annotated[int, Field(strict=True, ge=-1, le=1)] | None = None

    @field_validator("timestamp")
    @classmethod
    def utc_timestamp(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Sample timestamp must include a timezone")
        return value.astimezone(timezone.utc)

    @field_validator("values", mode="before")
    @classmethod
    def numeric_values(cls, values):
        if not isinstance(values, (list, tuple)) or any(
            isinstance(v, (bool, str)) for v in values
        ):
            raise ValueError("Signal values must be numbers, not strings or booleans")
        return values


class Chunk(Model):
    chunkIndex: Index
    finalWindow: bool = False
    samples: list[Sample] = Field(max_length=MAX_CHUNK_SAMPLES)


class Completion(Model):
    expectedSampleCount: Annotated[int, Field(strict=True, gt=0)]
    expectedLastSampleIndex: Index
    allowGaps: bool = False


def offset_ns(index: int, rate: float) -> int:
    fraction = Fraction(str(rate))
    numerator = index * 1_000_000_000 * fraction.denominator
    return (2 * numerator + fraction.numerator) // (2 * fraction.numerator)


def sample_timestamp(start: datetime, offset: int) -> datetime:
    return start + timedelta(milliseconds=offset // 1_000_000)


def content_hash(value: dict) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(encoded.encode("utf-8")).hexdigest()


def normalize_chunk(recording: Recording, chunk: Chunk) -> dict:
    size = recording.chunk_sample_count
    start = chunk.chunkIndex * size
    if chunk.finalWindow and not chunk.samples:
        raise ValueError("Final window must contain at least one sample")
    end = chunk.samples[-1].sampleIndex if chunk.finalWindow else start + size - 1
    if not start <= end < start + size:
        raise ValueError("Final window lies outside its source-index window")
    previous_index = start - 1
    previous_offset = -1
    missing = []
    for sample in chunk.samples:
        if not previous_index < sample.sampleIndex <= end:
            raise ValueError("Samples must be strictly ordered within the chunk window")
        if sample.offsetNs <= previous_offset:
            raise ValueError("Sample offsets must strictly increase")
        if sample.sampleIndex == 0 and sample.offsetNs != 0:
            raise ValueError("Source sample zero must align with the recording time origin")
        if recording.timeBase.derivation == "uniform_sample_clock":
            if sample.offsetNs != offset_ns(sample.sampleIndex, recording.sampleRateHz):
                raise ValueError("Sample offset disagrees with the recording clock")
        if sample.timestamp != sample_timestamp(recording.recordingStartedAt, sample.offsetNs):
            raise ValueError("Sample timestamp disagrees with its offset and recording start")
        if sample.sampleIndex > previous_index + 1:
            missing.append([previous_index + 1, sample.sampleIndex - 1])
        previous_index, previous_offset = sample.sampleIndex, sample.offsetNs
    if previous_index < end:
        missing.append([previous_index + 1, end])
    payload = chunk.model_dump(mode="json")
    return {
        "_id": f"{recording.recordingId}:{chunk.chunkIndex}",
        "schemaVersion": 1,
        "recordingId": str(recording.recordingId),
        "chunkIndex": chunk.chunkIndex,
        "firstSampleIndex": start,
        "lastSampleIndex": end,
        "sampleCount": len(chunk.samples),
        "finalWindow": chunk.finalWindow,
        "startedAt": chunk.samples[0].timestamp if chunk.samples else None,
        "endedAt": chunk.samples[-1].timestamp if chunk.samples else None,
        "firstOffsetNs": chunk.samples[0].offsetNs if chunk.samples else None,
        "lastOffsetNs": chunk.samples[-1].offsetNs if chunk.samples else None,
        "samples": [sample.model_dump() for sample in chunk.samples],
        "missingSampleRanges": missing,
        "contentHash": content_hash(payload),
    }
