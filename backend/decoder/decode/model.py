"""Shrunk LDA. Fit on recordings, save the pipeline, load it for a session."""

from pathlib import Path

import joblib
import numpy as np
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ..config import BAND, CHANNELS, DOWN, FS, POST, PRE
from .features import extract_epochs


def make_model():
    return make_pipeline(
        StandardScaler(),
        LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"),
    )


def train_lda(eeg, flash_idx, is_target, fs=FS):
    """Fit on one continuous recording. is_target is 1 for an attended flash."""
    features, ok = extract_epochs(eeg, flash_idx, fs)
    labels = np.asarray(is_target)[ok]
    return make_model().fit(features, labels)


def train_recordings(recordings):
    """Fit on several files. Each file is filtered on its own, then the epochs are pooled."""
    pooled_x = []
    pooled_y = []
    for recording in recordings:
        features, ok = extract_epochs(
            recording.eeg, recording.flash_index, recording.fs
        )
        pooled_x.append(features)
        pooled_y.append(np.asarray(recording.is_target)[ok])
    features = np.vstack(pooled_x)
    labels = np.concatenate(pooled_y)
    if len(np.unique(labels)) < 2:
        raise ValueError("calibration needs both attended and ignored flashes")
    return make_model().fit(features, labels)


def save_model(model, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": model,
            "fs": FS,
            "band": BAND,
            "pre": PRE,
            "post": POST,
            "down": DOWN,
            "channels": CHANNELS,
        },
        path,
    )
    return path


def load_model(path):
    payload = joblib.load(path)
    return payload["model"]
