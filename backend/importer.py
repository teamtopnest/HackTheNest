import argparse
from collections import Counter
from hashlib import sha256
import json
import logging
import os
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from dotenv import load_dotenv
import httpx
import numpy as np
from pydantic import ValidationError
from scipy.io import loadmat

from backend.schemas import Chunk, Recording, Sample, content_hash, offset_ns, sample_timestamp
from backend.sender import ApiClient


MONTAGE = ["Fz", "Cz", "P3", "Pz", "P4", "PO7", "PO8", "Oz"]
logger = logging.getLogger(__name__)


def read_mat(path: Path):
    data = loadmat(path)
    if not all(name in data for name in ("fs", "y", "trig")):
        raise ValueError(f"{path.name}: expected fs, y, and trig")
    fs = np.asarray(data["fs"])
    if fs.size != 1 or not np.issubdtype(fs.dtype, np.number):
        raise ValueError(f"{path.name}: fs must be a numeric scalar")
    rate = float(fs.item())
    if not np.isfinite(rate) or not 0 < rate <= 2000:
        raise ValueError(f"{path.name}: sample rate must be positive and at most 2000 Hz")
    values = np.asarray(data["y"])
    triggers = np.asarray(data["trig"])
    if values.ndim != 2 or values.shape[1] != 8 or values.shape[0] == 0:
        raise ValueError(f"{path.name}: y must be a nonempty samples x 8 matrix")
    if not np.issubdtype(values.dtype, np.floating) or not np.isfinite(values).all():
        raise ValueError(f"{path.name}: EEG values must be finite floating-point numbers")
    if triggers.shape not in ((len(values), 1), (1, len(values))):
        raise ValueError(f"{path.name}: trig must be a vector aligned with y")
    triggers = triggers.reshape(-1)
    if not np.isin(triggers, [-1, 0, 1]).all():
        raise ValueError(f"{path.name}: trig contains an unsupported code")
    return rate, values, triggers


def recording_from_manifest(path: Path, entry: dict, rate: float) -> Recording:
    if not isinstance(entry, dict):
        raise ValueError(f"{path.name}: manifest entry must be an object")
    if not entry.get("recordingStartedAt"):
        raise ValueError(
            f"{path.name}: provide its verified first-sample recordingStartedAt with timezone; "
            "export and import dates are not acquisition times"
        )
    allowed = {"subjectId", "recordingStartedAt", "timeBase", "channels", "signalUnit",
               "unitEvidence", "device"}
    unknown = set(entry) - allowed
    if unknown:
        raise ValueError(f"{path.name}: unknown manifest fields {sorted(unknown)}")
    fields = {
        **entry,
        "sampleRateHz": rate,
        "source": {"kind": "mat", "identifier": "p300-speller",
                   "filename": path.name, "sha256": sha256(path.read_bytes()).hexdigest(),
                   "format": "MATLAB v5"},
    }
    identity = uuid5(NAMESPACE_URL, "eeg-import:" + content_hash(fields))
    return Recording(recordingId=identity, **fields)


def chunks_from_mat(recording: Recording, values, triggers):
    size = recording.chunk_sample_count
    for start in range(0, len(values), size):
        stop = min(start + size, len(values))
        samples = []
        for index in range(start, stop):
            offset = offset_ns(index, recording.sampleRateHz)
            samples.append(Sample(
                sampleIndex=index, offsetNs=offset,
                timestamp=sample_timestamp(recording.recordingStartedAt, offset),
                values=values[index].tolist(), trigger=int(triggers[index]),
            ))
        yield Chunk(chunkIndex=start // size, finalWindow=stop == len(values), samples=samples)


def verify_roundtrip(api: ApiClient, recording: Recording, values, triggers):
    after, checked = -1, 0
    while True:
        result = api.request("GET", f"v1/recordings/{recording.recordingId}/samples",
                             params={"after": after, "limit": 2000})
        samples = result["samples"]
        for raw in samples:
            sample = Sample.model_validate(raw)
            if sample.sampleIndex != checked or checked >= len(values):
                raise ValueError("Round-trip source indices are missing or duplicated")
            offset = offset_ns(checked, recording.sampleRateHz)
            if (
                sample.offsetNs != offset
                or sample.timestamp != sample_timestamp(recording.recordingStartedAt, offset)
                or sample.trigger != int(triggers[checked])
                or not np.array_equal(np.asarray(sample.values), values[checked])
            ):
                raise ValueError(f"Round-trip mismatch at sample {checked}")
            checked += 1
        if result["nextAfter"] is None:
            break
        if not samples or result["nextAfter"] <= after:
            raise ValueError("API pagination did not advance")
        after = result["nextAfter"]
    if checked != len(values):
        raise ValueError(f"Round-trip count mismatch: expected {len(values)}, got {checked}")
    return checked


def import_recording(api, recording, values, triggers):
    api.create(recording)
    persisted = skipped = 0
    for chunk in chunks_from_mat(recording, values, triggers):
        result = api.send(str(recording.recordingId), chunk)
        if result["duplicate"]:
            skipped += 1
        else:
            persisted += 1
    verified = verify_roundtrip(api, recording, values, triggers)
    summary = api.request("POST", f"v1/recordings/{recording.recordingId}/complete", json={
        "expectedSampleCount": len(values), "expectedLastSampleIndex": len(values) - 1,
    })
    return {"persistedChunks": persisted, "skippedChunks": skipped,
            "verifiedSamples": verified, "summary": summary}


def main():
    parser = argparse.ArgumentParser(description="Inspect or import eight-channel P300 MAT files")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--import-data", action="store_true",
                        help="Write via the configured API; otherwise inspection only")
    args = parser.parse_args()
    load_dotenv(Path(__file__).with_name(".env"))
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8")) if args.manifest else {}
        if not isinstance(manifest, dict):
            raise ValueError("Manifest must be an object keyed by exact MAT filename")
        prepared = []
        for path in args.files:
            rate, values, triggers = read_mat(path)
            counts = Counter(int(code) for code in triggers)
            entry = manifest.get(path.name)
            recording = recording_from_manifest(path, entry, rate) if entry is not None else None
            if args.import_data and recording is None:
                raise ValueError(f"{path.name}: a verified recording manifest is required before writes")
            print(json.dumps({
                "file": path.name, "samples": len(values), "channels": 8, "sampleRateHz": rate,
                "durationSeconds": len(values) / rate,
                "lastSampleOffsetSeconds": (len(values) - 1) / rate,
                "triggerCounts": counts, "verifiedTimeManifest": recording is not None,
            }))
            prepared.append((path, recording, values, triggers))
        if args.import_data:
            api = ApiClient(os.environ.get("EEG_API_URL", ""), os.environ.get("EEG_API_TOKEN", ""))
            try:
                for path, recording, values, triggers in prepared:
                    print(json.dumps({"file": path.name,
                                      **import_recording(api, recording, values, triggers)}))
            finally:
                api.close()
    except (ValueError, OSError, ValidationError, RuntimeError, httpx.HTTPStatusError) as exc:
        if isinstance(exc, (ValidationError, httpx.HTTPStatusError)):
            logger.error("Import failed (%s); check manifest/API validation and authorization",
                         type(exc).__name__)
        else:
            logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
