"""Replay contract, the 6x6 board, and a synthetic pass through the live scorer."""

import tempfile
import unittest
from pathlib import Path

import numpy as np

from backend.decoder.config import CHANNELS, CHUNK_SAMPLES, FS, POST, PRE
from backend.decoder.decode.model import load_model, save_model, train_lda
from backend.decoder.decode.online import OnlineDecoder
from backend.decoder.sources.device import DeviceSource
from backend.decoder.sources.frames import Frame
from backend.decoder.sources.replay import load_recording
from backend.decoder.spell.grid import (
    MATRIX,
    RowColumnBoard,
    stimulus_ids_for,
    stimulus_index,
    stimulus_name,
)

DATA = (
    Path(__file__).resolve().parents[2]
    / "sources"
    / "p300-speller"
    / "S1.mat"
)


class ConstantModel:
    def decision_function(self, features):
        return np.ones(len(features))


class SequenceModel:
    def __init__(self, scores):
        self.scores = list(scores)

    def decision_function(self, features):
        return np.array([self.scores.pop(0)])


class ReplayTests(unittest.TestCase):
    def test_s1_matches_the_recording_contract(self):
        recording = load_recording(DATA)
        self.assertEqual(recording.fs, FS)
        self.assertEqual(recording.eeg.shape[1], len(CHANNELS))
        self.assertEqual(len(recording.flash_index), 1200)
        self.assertEqual(int(recording.is_target.sum()), 150)

        blocks = recording.blocks()
        self.assertEqual(len(np.unique(blocks)), 5)
        for block in np.unique(blocks):
            in_block = blocks == block
            self.assertEqual(int(in_block.sum()), 240)
            self.assertEqual(int(recording.is_target[in_block].sum()), 30)

        covered = 0
        flash_count = 0
        target_count = 0
        for frame in recording.frames():
            self.assertLessEqual(len(frame.data), CHUNK_SAMPLES)
            self.assertEqual(frame.data.shape[1], 8)
            stop = covered + len(frame.data)
            for flash in frame.flashes:
                self.assertGreaterEqual(flash.sample_index, covered)
                self.assertLess(flash.sample_index, stop)
                self.assertIsNone(flash.stimulus_id)
                flash_count += 1
                target_count += int(flash.is_target)
            covered = stop
        self.assertEqual(covered, len(recording.eeg))
        self.assertEqual(flash_count, 1200)
        self.assertEqual(target_count, 150)


class BoardTests(unittest.TestCase):
    def test_high_scores_pick_the_cell(self):
        board = RowColumnBoard(rounds=1)
        letter = None
        for row in range(6):
            letter = board.add(f"row-{row}", 5.0 if row == 2 else 0.0)
            self.assertIsNone(letter)
        for col in range(6):
            letter = board.add(f"col-{col}", 5.0 if col == 4 else 0.0)
        self.assertEqual(letter, MATRIX[2][4])
        self.assertEqual(letter, "Q")
        self.assertEqual(stimulus_ids_for("W"), ("row-3", "col-4"))

    def test_letter_lookup_and_index_roundtrip(self):
        self.assertEqual(stimulus_ids_for("A"), ("row-0", "col-0"))
        self.assertEqual(stimulus_ids_for(" "), stimulus_ids_for("_"))
        for index in range(12):
            self.assertEqual(stimulus_index(stimulus_name(index)), index)

    def test_a_second_character_starts_from_zero(self):
        board = RowColumnBoard(rounds=1)
        for row in range(6):
            board.add(f"row-{row}", 1.0 if row == 0 else 0.0)
        first = None
        for col in range(6):
            first = board.add(f"col-{col}", 1.0 if col == 0 else 0.0)
        self.assertEqual(first, "A")
        for row in range(6):
            board.add(f"row-{row}", 1.0 if row == 1 else 0.0)
        second = None
        for col in range(6):
            second = board.add(f"col-{col}", 1.0 if col == 0 else 0.0)
        self.assertEqual(second, "G")


class DecoderTests(unittest.TestCase):
    def test_score_chunk_returns_one_score_per_flash(self):
        pre = int(round(PRE * FS))
        post = int(round(POST * FS))
        flashes = [pre + 10, 800, 1400]
        n = flashes[-1] + post + 5
        eeg = np.zeros((n, 1))
        decoder = OnlineDecoder(ConstantModel(), n_ch=1, n_tiles=1, rounds=10**9)
        scored = []
        cursor = 0
        for start in range(0, n, CHUNK_SAMPLES):
            stop = min(start + CHUNK_SAMPLES, n)
            while cursor < len(flashes) and flashes[cursor] < stop:
                decoder.mark_flash(0, flashes[cursor])
                cursor += 1
            scored.extend(decoder.score_chunk(eeg[start:stop]))
        self.assertEqual(len(scored), len(flashes))
        self.assertTrue(all(score == 1.0 for _, score in scored))

    def test_push_returns_the_winning_tile(self):
        pre = int(round(PRE * FS))
        post = int(round(POST * FS))
        eeg = np.zeros((pre + post + 80 + CHUNK_SAMPLES, 1))
        decoder = OnlineDecoder(SequenceModel([0.0, 5.0]), n_ch=1, n_tiles=2, rounds=1)
        decoder.mark_flash(0, pre)
        decoder.mark_flash(1, pre + 40)
        choice = None
        for start in range(0, len(eeg), CHUNK_SAMPLES):
            got = decoder.push(eeg[start : start + CHUNK_SAMPLES])
            if got is not None:
                choice = got
        self.assertEqual(choice, 1)

    def test_train_save_and_load(self):
        rng = np.random.default_rng(0)
        n = FS * 8
        eeg = rng.normal(scale=5.0, size=(n, 8))
        flash_index = np.arange(100, n - 200, 80)
        is_target = np.zeros(len(flash_index), dtype=int)
        is_target[::2] = 1
        # Attended flashes carry a bump on Pz so the two classes differ.
        for sample, label in zip(flash_index, is_target):
            if label:
                eeg[sample + 70 : sample + 90, 3] += 20.0
        model = train_lda(eeg, flash_index, is_target)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.joblib"
            save_model(model, path)
            loaded = load_model(path)
        features = rng.normal(size=(2, 160))
        np.testing.assert_allclose(
            model.decision_function(features),
            loaded.decision_function(features),
        )


class DeviceTests(unittest.TestCase):
    def test_unconnected_source_explains_itself(self):
        with self.assertRaises(RuntimeError) as caught:
            list(DeviceSource().frames())
        self.assertIn("BCI Core", str(caught.exception))

    def test_injected_stream_is_returned_raw(self):
        data = np.arange(32 * 8, dtype=float).reshape(32, 8)
        source = DeviceSource([Frame(data)])
        frames = list(source.frames())
        self.assertEqual(len(frames), 1)
        np.testing.assert_array_equal(frames[0].data, data)


if __name__ == "__main__":
    unittest.main()
