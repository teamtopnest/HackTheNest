"""Score flashes as EEG arrives. The same class runs on a file and on a headset."""

import numpy as np

from ..config import FS, POST, PRE
from ..filtering.bandpass import CausalBandpass
from .features import epoch_features


class OnlineDecoder:
    """Feed EEG chunks and flash markers.

    mark_flash(tile) when a stimulus turns on.
    push(chunk) with samples x channels. Returns the winning tile id once
    every tile has been seen `rounds` times, otherwise None.
    score_chunk(chunk) returns (tile, score) for epochs that just completed
    and leaves the winner to the caller. The row/column speller uses that.
    """

    def __init__(self, model, n_ch=8, n_tiles=4, rounds=5, fs=FS):
        self.model = model
        self.fs = fs
        self.n_tiles = n_tiles
        self.rounds = rounds
        self.filt = CausalBandpass(n_ch, fs)
        self.buf = np.zeros((0, n_ch))
        self.offset = 0
        self.n_samples = 0
        self.pending = []
        self.reset_scores()

    def reset_scores(self):
        self.scores = np.zeros(self.n_tiles)
        self.counts = np.zeros(self.n_tiles, int)

    def mark_flash(self, tile, sample_index=None):
        """sample_index is the absolute EEG sample of the flash.

        Pass the headset clock when there is one. The default is the
        newest sample already received.
        """
        if sample_index is None:
            sample_index = self.n_samples
        self.pending.append((sample_index, tile))

    def score_chunk(self, chunk):
        """Filter this chunk and score every flash whose window has arrived."""
        filtered = self.filt.process(chunk)
        self.buf = np.vstack([self.buf, filtered])
        self.n_samples += len(chunk)
        pre = int(round(PRE * self.fs))
        post = int(round(POST * self.fs))
        scored = []
        still = []
        for sample_index, tile in self.pending:
            if sample_index + post > self.n_samples:
                still.append((sample_index, tile))
                continue
            local = sample_index - self.offset
            if local - pre < 0:
                continue
            features = epoch_features(self.buf, local, self.fs)
            score = float(self.model.decision_function(features[None])[0])
            scored.append((tile, score))
        self.pending = still
        self._trim(pre + post)
        return scored

    def push(self, chunk):
        for tile, score in self.score_chunk(chunk):
            self.scores[tile] += score
            self.counts[tile] += 1
        if self.counts.min() >= self.rounds:
            choice = int(np.argmax(self.scores))
            self.reset_scores()
            return choice
        return None

    def _trim(self, window):
        keep = 2 * window
        if len(self.buf) > keep * 4:
            drop = len(self.buf) - keep * 2
            self.buf = self.buf[drop:]
            self.offset += drop
