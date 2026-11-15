"""Headset input. Raw chunks only. The decoder owns the bandpass.

The BCI Core is not opened here. Construct DeviceSource(stream) with an
iterator of Frame objects once acquisition exists. Channel order has to
match the recordings the LDA was trained on.

eeg_stream publishes frames that are already bandpassed at 0.5–30 Hz
with a second-order filter. Do not feed those into this decoder. It
applies its own fourth-order causal filter, and a second pass would
not match the model trained on the raw MAT files.
"""

from ..config import CHANNELS, FS
from .frames import Frame


class DeviceSource:
    def __init__(self, stream=None):
        self.stream = stream

    @property
    def channels(self):
        return CHANNELS

    @property
    def fs(self):
        return FS

    def frames(self):
        if self.stream is None:
            raise RuntimeError(
                "BCI Core is not connected. Replay a .mat file with "
                "load_recording, or pass a stream of raw Frame objects. "
                f"Expect {FS} Hz and channels {', '.join(CHANNELS)}, unfiltered."
            )
        for frame in self.stream:
            if not isinstance(frame, Frame):
                raise TypeError("device stream must yield Frame objects")
            if frame.data.ndim != 2 or frame.data.shape[1] != len(CHANNELS):
                raise ValueError(
                    f"device chunk must be samples x {len(CHANNELS)}, "
                    f"got {frame.data.shape}"
                )
            yield frame
