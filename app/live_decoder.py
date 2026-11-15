"""NeuroVoice real-time P300 decoder.

Pieces:
  CausalBandpass  - filter that works on live chunks (no future samples)
  extract_epochs  - same epoching used for training AND live
  train_lda       - train on a calibration recording, filtered causally
  OnlineDecoder   - feed it EEG chunks + flash markers; it returns the chosen tile

Self-test (replays S1..S5 chunk by chunk, as if live):
  python live_decoder.py S1.mat S2.mat S3.mat S4.mat S5.mat
"""
import sys
import numpy as np
from scipy.io import loadmat
from scipy.signal import butter, sosfilt, sosfilt_zi, resample_poly
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.metrics import roc_auc_score

FS = 250
BAND = (0.5, 30)
PRE, POST = 0.1, 0.7          # seconds before / after each flash
DOWN = 10                     # 250 Hz -> 25 Hz


class CausalBandpass:
    """Streaming band-pass. Call .process(chunk) with chunk = samples x channels."""
    def __init__(self, n_ch, fs=FS, band=BAND, order=4):
        self.sos = butter(order, band, btype="bandpass", fs=fs, output="sos")
        self.zi = None
        self.n_ch = n_ch

    def process(self, chunk):
        chunk = np.asarray(chunk, float)
        if self.zi is None:  # start the filter at the first sample's level (avoids a big jump)
            self.zi = sosfilt_zi(self.sos)[:, :, None] * chunk[0][None, None, :]
        out, self.zi = sosfilt(self.sos, chunk, axis=0, zi=self.zi)
        return out


def epoch_features(filtered, idx, fs=FS):
    pre, post = int(round(PRE * fs)), int(round(POST * fs))
    ep = filtered[idx - pre: idx + post].copy()
    ep -= ep[:pre].mean(axis=0)
    return resample_poly(ep, 1, DOWN, axis=0).T.ravel()


def extract_epochs(eeg, flash_idx, fs=FS):
    """eeg = samples x channels (raw). Filters causally, returns features for each flash."""
    filtered = CausalBandpass(eeg.shape[1], fs).process(eeg)
    pre, post = int(round(PRE * fs)), int(round(POST * fs))
    ok = (flash_idx >= pre) & (flash_idx + post <= len(eeg))
    return np.stack([epoch_features(filtered, i, fs) for i in flash_idx[ok]]), ok


def make_model():
    return make_pipeline(StandardScaler(),
                         LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"))


def train_lda(eeg, flash_idx, is_target, fs=FS):
    """Calibration: raw EEG, flash sample indices, 1/0 target labels."""
    X, ok = extract_epochs(eeg, flash_idx, fs)
    return make_model().fit(X, np.asarray(is_target)[ok])


class OnlineDecoder:
    """Live use:
        dec = OnlineDecoder(model, n_ch=8, n_tiles=4, rounds=5)
        every time the app flashes a tile:   dec.mark_flash(tile_id)
        every time EEG samples arrive:       choice = dec.push(chunk)
        choice is None until a tile wins, then the tile id.
    """
    def __init__(self, model, n_ch=8, n_tiles=4, rounds=5, fs=FS):
        self.model, self.fs, self.n_tiles, self.rounds = model, fs, n_tiles, rounds
        self.filt = CausalBandpass(n_ch, fs)
        self.buf = np.zeros((0, n_ch))
        self.offset = 0                   # absolute sample index of buf[0]
        self.n_samples = 0                # total samples received
        self.pending = []                 # (absolute sample index, tile)
        self.reset_scores()

    def reset_scores(self):
        self.scores = np.zeros(self.n_tiles)
        self.counts = np.zeros(self.n_tiles, int)

    def mark_flash(self, tile, sample_index=None):
        """Call at flash time. sample_index = absolute EEG sample of the flash
        (best: from the headset's own trigger/marker). Default = latest sample."""
        self.pending.append((self.n_samples if sample_index is None else sample_index, tile))

    def push(self, chunk):
        f = self.filt.process(chunk)
        self.buf = np.vstack([self.buf, f])
        self.n_samples += len(chunk)
        pre, post = int(round(PRE * self.fs)), int(round(POST * self.fs))
        still = []
        for idx, tile in self.pending:
            if idx + post <= self.n_samples:          # epoch complete
                x = epoch_features(self.buf, idx - self.offset, self.fs)
                self.scores[tile] += self.model.decision_function(x[None])[0]
                self.counts[tile] += 1
            else:
                still.append((idx, tile))
        self.pending = still
        keep = 2 * (pre + post)                       # trim old samples
        if len(self.buf) > keep * 4:
            drop = len(self.buf) - keep * 2
            self.buf, self.offset = self.buf[drop:], self.offset + drop
        if self.counts.min() >= self.rounds:
            choice = int(np.argmax(self.scores))
            self.reset_scores()
            return choice
        return None


# ---------------- self-test on the g.tec dataset ----------------
def _load(path):
    d = loadmat(path)
    eeg = np.asarray(d["y"], float)
    trig = np.asarray(d["trig"]).ravel()
    idx = np.flatnonzero(trig != 0)
    return eeg, idx, (trig[idx] == 1).astype(int)


if __name__ == "__main__":
    print("Causal (real-time) filter, leave-one-character-block-out, scored by streaming replay")
    for p in sys.argv[1:]:
        eeg, idx, lab = _load(p)
        block = np.cumsum(np.r_[0, np.diff(idx) > int(0.4 * FS)])
        scores = np.full(len(idx), np.nan)
        for b in np.unique(block):
            tr = block != b
            model = train_lda(eeg, idx[tr], lab[tr])
            # replay the whole recording live in 32-sample chunks (~128 ms, like a headset)
            dec = OnlineDecoder(model, n_ch=eeg.shape[1], n_tiles=1, rounds=10**9)
            test_ids = set(np.flatnonzero(~tr))
            got, k = {}, 0
            order = np.argsort(idx)
            for start in range(0, len(eeg), 32):
                while k < len(idx) and idx[order[k]] < start + 32:
                    j = order[k]
                    if j in test_ids:
                        dec.pending.append((idx[j], j))  # tile slot used as flash id here
                    k += 1
                # score manually so we keep per-flash values
                f = dec.filt.process(eeg[start:start + 32])
                dec.buf = np.vstack([dec.buf, f]); dec.n_samples += len(f)
                post = int(round(POST * FS)); still = []
                for i0, j in dec.pending:
                    if i0 + post <= dec.n_samples and i0 - int(PRE * FS) - dec.offset >= 0:
                        x = epoch_features(dec.buf, i0 - dec.offset)
                        got[j] = model.decision_function(x[None])[0]
                    elif i0 + post <= dec.n_samples:
                        pass
                    else:
                        still.append((i0, j))
                dec.pending = still
            for j, v in got.items():
                scores[j] = v
        m = ~np.isnan(scores)
        print(f"{p.split('/')[-1]:>8}: live-replay AUC = {roc_auc_score(lab[m], scores[m]):.3f}  "
              f"({m.sum()} flashes scored)")
