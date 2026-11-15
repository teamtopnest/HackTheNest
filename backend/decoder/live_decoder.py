"""P300 decoder command.

Score the recordings shipped in backend/resources/unicorn-bi:

    python -m backend.decoder.live_decoder

Fit an LDA on those files and save it:

    python -m backend.decoder.live_decoder --train --output model.joblib
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    _package_dir = Path(__file__).resolve().parent
    _repo_root = _package_dir.parent.parent
    # Drop the script directory so a local package cannot hide a stdlib module.
    sys.path = [entry for entry in sys.path if Path(entry).resolve() != _package_dir]
    sys.path.insert(0, str(_repo_root))
    __package__ = "backend.decoder"

from .config import bundled_recordings
from .decode.features import extract_epochs
from .decode.model import load_model, save_model, train_lda, train_recordings
from .decode.online import OnlineDecoder
from .eval.replay import report
from .filtering.bandpass import CausalBandpass
from .sources.replay import load_recording

__all__ = [
    "CausalBandpass",
    "OnlineDecoder",
    "extract_epochs",
    "load_model",
    "save_model",
    "train_lda",
    "train_recordings",
]


def main(argv=None):
    parser = argparse.ArgumentParser(description="P300 decoder offline tools")
    parser.add_argument(
        "recordings",
        nargs="*",
        help="MAT paths. Defaults to backend/resources/unicorn-bi/S*.mat",
    )
    parser.add_argument(
        "--train",
        action="store_true",
        help="fit an LDA on every flash in these files and save it",
    )
    parser.add_argument("--output", default="model.joblib", help="path for --train")
    args = parser.parse_args(argv)
    recordings = args.recordings or [str(path) for path in bundled_recordings()]
    if args.train:
        recordings = [load_recording(path) for path in recordings]
        model = train_recordings(recordings)
        saved = save_model(model, args.output)
        print(f"saved {saved}")
        return
    print(
        "Causal filter, leave-one-character-out, scored by streaming replay"
    )
    for path in recordings:
        report(path)


if __name__ == "__main__":
    main()
