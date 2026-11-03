"""Tests of the post-hoc masked QR experiment (KD-9): mask, triple ranking, reconstruction and the guard refusal.

The helpers are checked on the 5x5 "staircase" fixture of test_hopfield_qr.py (row i and row i+1 differ in one
pixel), by hand. The C binary is never invoked here.
"""

from __future__ import annotations

import numpy as np
import pytest

import hopfield_qr_masked
import hopfield_qr_select
from test_hopfield_qr import STAIRCASE


def test_varying_mask_drops_the_common_pixels():
    mask = hopfield_qr_masked.varying_mask(STAIRCASE)
    assert mask.tolist() == [False, True, True, True, True]  # column 0 is 1 in every row


def test_rank_subsets_picks_the_least_correlated_triple():
    # The ranking is best first: smallest max |dot| / N, then the smallest mean among the ties.
    ranked = hopfield_qr_masked.rank_subsets(STAIRCASE, 3)
    assert len(ranked) == 10
    best = ranked[0]
    maxima = [item["max_abs_overlap"] for item in ranked]
    assert best["max_abs_overlap"] == min(maxima)
    assert maxima == sorted(maxima)
    ties = [item for item in ranked if item["max_abs_overlap"] == best["max_abs_overlap"]]
    assert best["mean_abs_overlap"] == min(item["mean_abs_overlap"] for item in ties)


def test_reconstruct_refills_the_common_pixels_from_the_template():
    mask = hopfield_qr_masked.varying_mask(STAIRCASE)
    for row in STAIRCASE:
        rebuilt = hopfield_qr_masked.reconstruct(row[mask], mask, STAIRCASE[0])
        assert np.array_equal(rebuilt, row)


def test_write_patterns_round_trips(tmp_path):
    import hopfield

    path = tmp_path / "masked.csv"
    hopfield_qr_masked.write_patterns(path, STAIRCASE[:, 1:])
    assert np.array_equal(hopfield.load_patterns(path), STAIRCASE[:, 1:])


def test_run_refuses_on_a_changed_protocol(tmp_path, monkeypatch):
    def refuse(_repo_dir):
        raise SystemExit("rule changed")

    monkeypatch.setattr(hopfield_qr_select, "rule_identity", refuse)
    with pytest.raises(SystemExit, match="rule changed"):
        hopfield_qr_masked.run(results_dir=tmp_path)
    assert not (tmp_path / hopfield_qr_masked.RESULTS_SUBDIR).exists()


def test_changed_code_files_without_a_record_is_every_file():
    assert hopfield_qr_masked.changed_code_files({}) == list(hopfield_qr_masked.MASKED_CODE_FILES)
