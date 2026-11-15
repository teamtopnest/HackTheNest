"""Causal bandpass. A live chunk never looks at samples that have not arrived."""

import numpy as np
from scipy.signal import butter, sosfilt, sosfilt_zi

from ..config import BAND, FS


class CausalBandpass:
    """Streaming band-pass. process(chunk) takes samples x channels."""

    def __init__(self, n_ch, fs=FS, band=BAND, order=4):
        self.sos = butter(order, band, btype="bandpass", fs=fs, output="sos")
        self.zi = None
        self.n_ch = n_ch

    def process(self, chunk):
        chunk = np.asarray(chunk, float)
        if self.zi is None:
            # Start the filter at the first sample so the stream does not jump.
            self.zi = sosfilt_zi(self.sos)[:, :, None] * chunk[0][None, None, :]
        out, self.zi = sosfilt(self.sos, chunk, axis=0, zi=self.zi)
        return out
