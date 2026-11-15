"""Play a .mat recording as headset-sized chunks."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.io import loadmat

from ..config import CHANNELS, CHARACTER_GAP_S, CHUNK_SAMPLES, FS
from .frames import Flash, Frame


def character_ids(flash_index, fs=FS):
    """A new character starts where the gap between flashes exceeds 0.4 s."""
    flash_index = np.asarray(flash_index)
    if flash_index.size == 0:
        return np.zeros(0, dtype=int)
    gap = np.diff(flash_index) > int(CHARACTER_GAP_S * fs)
    return np.cumsum(np.r_[0, gap])


@dataclass
class Recording:
    path: Path
    fs: int
    eeg: np.ndarray
    flash_index: np.ndarray
    is_target: np.ndarray

    def blocks(self):
        return character_ids(self.flash_index, self.fs)

    def frames(self, chunk=CHUNK_SAMPLES):
        by_sample: dict[int, list[int]] = {}
        for i, sample in enumerate(self.flash_index):
            by_sample.setdefault(int(sample), []).append(i)
        n = len(self.eeg)
        for start in range(0, n, chunk):
            stop = min(start + chunk, n)
            flashes = []
            for sample, owners in by_sample.items():
                if start <= sample < stop:
                    for i in owners:
                        flashes.append(
                            Flash(
                                sample_index=sample,
                                stimulus_id=None,
                                is_target=bool(self.is_target[i]),
                            )
                        )
            flashes.sort(key=lambda flash: flash.sample_index)
            yield Frame(self.eeg[start:stop], flashes)


def load_recording(path) -> Recording:
    path = Path(path)
    raw = loadmat(path)
    fs = int(np.asarray(raw["fs"]).ravel()[0])
    eeg = np.asarray(raw["y"], float)
    trig = np.asarray(raw["trig"]).ravel()
    if fs != FS:
        raise ValueError(f"{path.name}: expected {FS} Hz, file says {fs}")
    if eeg.ndim != 2 or eeg.shape[1] != len(CHANNELS):
        raise ValueError(
            f"{path.name}: expected {len(CHANNELS)} channels "
            f"({', '.join(CHANNELS)}), got shape {eeg.shape}"
        )
    flash_index = np.flatnonzero(trig != 0)
    is_target = (trig[flash_index] == 1).astype(int)
    return Recording(path, fs, eeg, flash_index, is_target)
