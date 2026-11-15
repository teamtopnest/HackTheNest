"""One feature vector per flash, shared by training and live scoring."""

import numpy as np
from scipy.signal import resample_poly

from ..config import DOWN, FS, POST, PRE
from ..filtering.bandpass import CausalBandpass


def epoch_features(filtered, idx, fs=FS):
    """Flatten one flash: baseline the pre-window, then downsample."""
    pre, post = int(round(PRE * fs)), int(round(POST * fs))
    ep = filtered[idx - pre : idx + post].copy()
    ep -= ep[:pre].mean(axis=0)
    return resample_poly(ep, 1, DOWN, axis=0).T.ravel()


def extract_epochs(eeg, flash_idx, fs=FS):
    """eeg is samples x channels, raw. Returns features and a keep-mask."""
    filtered = CausalBandpass(eeg.shape[1], fs).process(eeg)
    pre, post = int(round(PRE * fs)), int(round(POST * fs))
    ok = (flash_idx >= pre) & (flash_idx + post <= len(eeg))
    features = np.stack(
        [epoch_features(filtered, i, fs) for i in flash_idx[ok]]
    )
    return features, ok
