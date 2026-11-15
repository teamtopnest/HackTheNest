"""6x6 row/column board.

The LDA scores a flash. This board adds that score to the row or the
column that flashed. The character is the best row plus the best column
once every line has been flashed `rounds` times.

`_` is the space cell. The g.tec .mat files do not name rows or columns,
so this board is for the speller UI and for calibration you run yourself.
"""

import numpy as np

from ..decode.online import OnlineDecoder

MATRIX = (
    "ABCDEF",
    "GHIJKL",
    "MNOPQR",
    "STUVWX",
    "YZ1234",
    "56789_",
)


def stimulus_ids_for(letter):
    """Row and column ids that contain this character. Space is '_'."""
    glyph = "_" if letter == " " else letter.upper()
    for row_index, row in enumerate(MATRIX):
        col_index = row.find(glyph)
        if col_index >= 0:
            return f"row-{row_index}", f"col-{col_index}"
    raise ValueError(f"{letter!r} is not on the 6x6 board")


def stimulus_index(stimulus_id):
    kind, index = _parse(stimulus_id)
    return index if kind == "row" else 6 + index


def stimulus_name(index):
    if 0 <= index < 6:
        return f"row-{index}"
    if 6 <= index < 12:
        return f"col-{index - 6}"
    raise ValueError(f"stimulus index {index} is outside 0..11")


def _parse(stimulus_id):
    kind, sep, raw = str(stimulus_id).partition("-")
    if sep != "-" or kind not in ("row", "col"):
        raise ValueError(f"stimulus id must look like 'row-2' or 'col-4', got {stimulus_id!r}")
    index = int(raw)
    if not 0 <= index < 6:
        raise ValueError(f"{stimulus_id!r} is outside row-0..5 / col-0..5")
    return kind, index


class RowColumnBoard:
    def __init__(self, rounds=5):
        if rounds < 1:
            raise ValueError("rounds must be at least 1")
        self.rounds = rounds
        self.reset()

    def reset(self):
        self.row_scores = np.zeros(6)
        self.col_scores = np.zeros(6)
        self.row_counts = np.zeros(6, dtype=int)
        self.col_counts = np.zeros(6, dtype=int)

    def add(self, stimulus_id, score):
        """Add one flash score. Returns the chosen character, or None."""
        kind, index = _parse(stimulus_id)
        if kind == "row":
            self.row_scores[index] += score
            self.row_counts[index] += 1
        else:
            self.col_scores[index] += score
            self.col_counts[index] += 1
        if self.row_counts.min() < self.rounds or self.col_counts.min() < self.rounds:
            return None
        letter = MATRIX[int(np.argmax(self.row_scores))][int(np.argmax(self.col_scores))]
        self.reset()
        return letter


class SpellerSession:
    """OnlineDecoder plus the board. push(chunk) appends a character when one wins."""

    def __init__(self, model, n_ch=8, rounds=5, fs=250):
        # The board decides the character. The decoder only scores flashes,
        # so its own winner threshold stays out of reach.
        self.decoder = OnlineDecoder(
            model, n_ch=n_ch, n_tiles=12, rounds=10**9, fs=fs
        )
        self.board = RowColumnBoard(rounds)
        self.text = ""

    def mark_flash(self, stimulus_id, sample_index=None):
        self.decoder.mark_flash(stimulus_index(stimulus_id), sample_index)

    def push(self, chunk):
        emitted = None
        for tile, score in self.decoder.score_chunk(chunk):
            letter = self.board.add(stimulus_name(tile), score)
            if letter is not None:
                self.text += letter
                emitted = letter
        return emitted
