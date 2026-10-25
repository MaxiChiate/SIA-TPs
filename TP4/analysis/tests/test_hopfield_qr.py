"""Tests of the guarded Hopfield-on-QR driver's pure numpy helpers and its guard refusal (HOP-04, HOP-05, D-01).

The helpers are checked against hand-computed expectations on a tiny synthetic 5-by-5 pm-one "staircase" fixture
(row i and row i+1 differ in exactly one pixel), independent of any network run. The guard refusal is checked by
monkeypatching hopfield_qr_select.rule_identity to raise: the driver must propagate the SystemExit and leave no
output directory, without ever reaching the C binary. numpy and the standard library only; the C binary is never
invoked here.
"""

from __future__ import annotations

import numpy as np
import pytest

import hopfield_qr
import hopfield_qr_select

# A 5x5 "staircase" pm-one fixture: row i and row i+1 differ in exactly one pixel (column i), so
# hamming(row_a, row_b) = |a - b| and dot(row_a, row_b) = N - 2 * |a - b| = 5 - 2 * |a - b|.
STAIRCASE = np.array(
    [
        [1, 1, 1, 1, 1],
        [1, 1, 1, 1, -1],
        [1, 1, 1, -1, -1],
        [1, 1, -1, -1, -1],
        [1, -1, -1, -1, -1],
    ],
    dtype=np.int64,
)
# Hand-computed: dot(a, b) = 5 - 2 * |a - b|.
EXPECTED_DOTS = np.array(
    [
        [5, 3, 1, -1, -3],
        [3, 5, 3, 1, -1],
        [1, 3, 5, 3, 1],
        [-1, 1, 3, 5, 3],
        [-3, -1, 1, 3, 5],
    ],
    dtype=np.int64,
)
# Only column 0 (all rows = 1) is constant across all five rows: 1 of 5 columns.
EXPECTED_IDENTICAL_FRACTION = 1 / 5
# Every adjacent pair (|a - b| = 1) has Hamming distance 1; no pair is closer.
EXPECTED_MIN_PAIR_HAMMING = 1


# ---------- Task 1: the pure numpy helpers, hand-computed ----------

def test_overlap_matrix_equals_p_pt():
    dots = hopfield_qr.overlap_matrix(STAIRCASE)
    assert dots.dtype == np.int64
    assert np.array_equal(dots, EXPECTED_DOTS)
    assert np.array_equal(dots, STAIRCASE @ STAIRCASE.T)


def test_overlaps_json_normalizes_by_n():
    report = hopfield_qr.overlaps_json(STAIRCASE)
    n = STAIRCASE.shape[1]
    assert report["n_pixels"] == n
    assert np.allclose(np.array(report["overlaps"]), EXPECTED_DOTS / n)
    assert np.array_equal(np.array(report["dots"]), EXPECTED_DOTS)
    pairs = [abs(EXPECTED_DOTS[a, b] / n) for a in range(5) for b in range(a + 1, 5)]
    assert report["max_abs_overlap"] == pytest.approx(max(pairs))
    assert report["mean_abs_overlap"] == pytest.approx(sum(pairs) / len(pairs))


def test_identical_fraction_is_the_fraction_of_constant_columns():
    assert hopfield_qr.identical_fraction(STAIRCASE) == pytest.approx(EXPECTED_IDENTICAL_FRACTION)
    # Direct from the definition: a column constant across all five rows.
    by_hand = np.mean([len({int(v) for v in STAIRCASE[:, c]}) == 1 for c in range(STAIRCASE.shape[1])])
    assert hopfield_qr.identical_fraction(STAIRCASE) == pytest.approx(float(by_hand))


def test_min_pair_hamming_matches_the_known_minimum():
    assert hopfield_qr.min_pair_hamming(STAIRCASE) == EXPECTED_MIN_PAIR_HAMMING
    # Brute force over every pair, independent of the implementation.
    p = STAIRCASE.shape[0]
    brute = min(int((STAIRCASE[a] != STAIRCASE[b]).sum()) for a in range(p) for b in range(a + 1, p))
    assert hopfield_qr.min_pair_hamming(STAIRCASE) == brute


def test_qr_facts_json_reports_both():
    facts = hopfield_qr.qr_facts_json(STAIRCASE)
    assert facts["identical_fraction"] == pytest.approx(EXPECTED_IDENTICAL_FRACTION)
    assert facts["min_pair_hamming"] == EXPECTED_MIN_PAIR_HAMMING
    assert facts["n_pixels"] == STAIRCASE.shape[1]
    assert len(facts["pair_hamming"]) == 10  # C(5, 2) pairs


# ---------- Task 1: the guard refusal ----------

def test_driver_refuses_when_rule_identity_raises(tmp_path, monkeypatch):
    def boom(repo_dir=None):
        raise SystemExit("the protocol must be committed and unchanged (D-01)")

    monkeypatch.setattr(hopfield_qr_select, "rule_identity", boom)
    out_dir = tmp_path / "res"
    with pytest.raises(SystemExit) as error:
        hopfield_qr.run(results_dir=out_dir, check_rule=True)
    assert str(error.value).endswith("(D-01)")
    assert not (out_dir / hopfield_qr.RESULTS_SUBDIR).exists()
    assert not out_dir.exists()  # the driver never even created the results directory
