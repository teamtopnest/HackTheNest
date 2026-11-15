"""Leave-one-character-out AUC, scored by streaming the file in headset chunks.

The causal filter replays each recording from the first sample, so a held-out
character sees the same filter history a live session would.
"""

from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

from ..config import CHUNK_SAMPLES, FS, POST, PRE
from ..decode.features import epoch_features
from ..decode.model import train_lda
from ..decode.online import OnlineDecoder
from ..sources.replay import load_recording


def leave_one_character_scores(recording):
    """Return (attended labels, decision scores) for every flash that was scored."""
    flash_index = recording.flash_index
    labels = recording.is_target
    blocks = recording.blocks()
    scores = np.full(len(flash_index), np.nan)
    for block in np.unique(blocks):
        train = blocks != block
        model = train_lda(
            recording.eeg, flash_index[train], labels[train], recording.fs
        )
        held_out = set(np.flatnonzero(~train))
        for flash_id, score in _replay_scores(
            recording.eeg, flash_index, held_out, model
        ).items():
            scores[flash_id] = score
    scored = ~np.isnan(scores)
    return labels[scored], scores[scored]


def replay_auc(recording):
    labels, scores = leave_one_character_scores(recording)
    return float(roc_auc_score(labels, scores)), int(len(scores))


def _replay_scores(eeg, flash_index, held_out, model):
    """Stream the whole file. Score only the held-out flashes."""
    decoder = OnlineDecoder(
        model, n_ch=eeg.shape[1], n_tiles=1, rounds=10**9
    )
    got = {}
    order = np.argsort(flash_index)
    cursor = 0
    post = int(round(POST * FS))
    pre = int(round(PRE * FS))
    for start in range(0, len(eeg), CHUNK_SAMPLES):
        while cursor < len(flash_index) and flash_index[order[cursor]] < start + CHUNK_SAMPLES:
            flash_id = order[cursor]
            if flash_id in held_out:
                decoder.pending.append((int(flash_index[flash_id]), flash_id))
            cursor += 1
        filtered = decoder.filt.process(eeg[start : start + CHUNK_SAMPLES])
        decoder.buf = np.vstack([decoder.buf, filtered])
        decoder.n_samples += len(filtered)
        still = []
        for sample_index, flash_id in decoder.pending:
            ready = sample_index + post <= decoder.n_samples
            in_buffer = sample_index - pre - decoder.offset >= 0
            if ready and in_buffer:
                features = epoch_features(decoder.buf, sample_index - decoder.offset)
                got[flash_id] = float(model.decision_function(features[None])[0])
            elif not ready:
                still.append((sample_index, flash_id))
        decoder.pending = still
    return got


def report(path):
    recording = load_recording(path)
    auc, n_scored = replay_auc(recording)
    print(
        f"{Path(path).name:>8}: live-replay AUC = {auc:.3f}  "
        f"({n_scored} flashes scored)"
    )
    return auc
