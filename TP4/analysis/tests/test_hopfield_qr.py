"""Tests of the guarded Hopfield-on-QR driver's pure numpy helpers and its guard refusal (HOP-04, HOP-05, HOP-06,
D-01, D-08).

The helpers are checked against hand-computed expectations on a tiny synthetic 5-by-5 pm-one "staircase" fixture
(row i and row i+1 differ in exactly one pixel), independent of any network run. The guard refusal is checked by
monkeypatching hopfield_qr_select.rule_identity to raise: the driver must propagate the SystemExit and leave no
output directory, without ever reaching the C binary. Plan 04 adds: pinv's exact-fixed-point stability on a small
correlated-but-linearly-independent fixture (and Hebb's lack of it on the SAME fixture, D-06/D-07), and the
Hamming 1-NN helper's correctness and tie-break (D-08). numpy and the standard library only; the C binary is never
invoked here.
"""

from __future__ import annotations

import numpy as np
import pytest

import hopfield
import hopfield_qr
import hopfield_qr_limits
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


# ---------- Task 3 (Plan 04): pinv stability vs Hebb's lack of it (D-06, D-07) ----------

# A small pm-one fixture, linearly independent (rank 4 = p) but heavily correlated: the first three columns are
# identical across all four patterns, so only the last three columns distinguish them - correlated enough that
# Hebb leaves three of the four patterns NOT fixed points, while pinv (which only needs linear independence) makes
# every one of them an exact fixed point.
CORRELATED = np.array(
    [
        [1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, -1],
        [1, 1, 1, 1, -1, 1],
        [1, 1, 1, -1, 1, 1],
    ],
    dtype=np.int64,
)


def test_correlated_fixture_is_linearly_independent_and_correlated():
    # Sanity on the fixture itself: rank = p (so pinv's Gram inverts) and it is NOT orthogonal (so Hebb is
    # expected to struggle) - both preconditions the two tests below rely on.
    assert np.linalg.matrix_rank(CORRELATED.astype(np.float64)) == CORRELATED.shape[0]
    assert hopfield_qr.min_pair_hamming(CORRELATED) < CORRELATED.shape[1]


def test_pinv_makes_every_pattern_of_the_correlated_fixture_a_fixed_point():
    W = hopfield.pinv(CORRELATED)
    assert all(hopfield.is_fixed(W, CORRELATED[a]) for a in range(CORRELATED.shape[0]))


def test_hebb_leaves_at_least_one_pattern_of_the_correlated_fixture_not_fixed():
    W = hopfield.hebb(CORRELATED)
    fixed = [hopfield.is_fixed(W, CORRELATED[a]) for a in range(CORRELATED.shape[0])]
    assert not all(fixed)
    assert any(fixed)  # the fixture is not so pathological that Hebb fails on every pattern either


# ---------- Task 3 (Plan 04): the Hamming 1-NN baseline (D-08) ----------

# Three patterns, N = 8, with minimum pairwise Hamming distance 4 (every pair, computed by hand): a query with
# fewer than half that (< 2 flips) is unambiguously closer to its own source pattern than to any other.
HAMMING_FIXTURE = np.array(
    [
        [1, 1, 1, 1, 1, 1, 1, 1],
        [-1, -1, -1, -1, 1, 1, 1, 1],
        [1, 1, -1, -1, -1, -1, 1, 1],
    ],
    dtype=np.int64,
)


def test_hamming_fixture_min_pair_distance_is_four():
    assert hopfield_qr.min_pair_hamming(HAMMING_FIXTURE) == 4


def test_hamming_classify_returns_the_true_pattern_under_low_noise():
    rng = np.random.default_rng(0)
    for a in range(HAMMING_FIXTURE.shape[0]):
        query = HAMMING_FIXTURE[a].copy()
        flip = rng.choice(HAMMING_FIXTURE.shape[1], size=1, replace=False)  # 1 flip, well under half of 4
        query[flip] *= -1
        assert hopfield_qr.hamming_classify(HAMMING_FIXTURE, query) == a


def test_hamming_classify_breaks_an_exact_tie_by_the_lowest_index():
    # Flip 2 of the 4 differing pixels between pattern 0 and pattern 1: the query lands exactly halfway between
    # them (Hamming distance 2 to each), and much farther from pattern 2.
    query = HAMMING_FIXTURE[0].copy()
    query[0] *= -1
    query[1] *= -1
    distances = [int((HAMMING_FIXTURE[a] != query).sum()) for a in range(HAMMING_FIXTURE.shape[0])]
    assert distances[0] == distances[1] and distances[0] < distances[2]  # confirms the tie is real, not assumed
    assert hopfield_qr.hamming_classify(HAMMING_FIXTURE, query) == 0  # HAMMING_TIE_BREAK: the lowest index


# ---------- Task 1 (Plan 05): the majority attractor differs from every target (D-11a) ----------

# 5 patterns, N = 5: at every pixel j, exactly two of the five rows ({j, (j-1) mod 5}) hold -1 and the other
# three hold +1, so every column sums to +1 (majority = all +1) while every row itself has exactly two -1
# pixels - hand-verified below to differ from the all-+1 majority by Hamming distance 2 on every row, unlike
# STAIRCASE or CORRELATED (both of which happen to coincide with one of their own rows exactly).
MAJORITY_FIXTURE = np.array(
    [
        [-1, 1, 1, 1, -1],
        [-1, -1, 1, 1, 1],
        [1, -1, -1, 1, 1],
        [1, 1, -1, -1, 1],
        [1, 1, 1, -1, -1],
    ],
    dtype=np.int64,
)
EXPECTED_MAJORITY = np.array([1, 1, 1, 1, 1], dtype=np.int64)
EXPECTED_HAMMING_TO_TARGETS = [2, 2, 2, 2, 2]


def test_majority_fixture_column_sums_are_hand_verified():
    # Sanity on the fixture itself: every column sums to +1 (3 rows at +1, 2 at -1).
    assert np.array_equal(MAJORITY_FIXTURE.sum(axis=0), np.full(5, 1))


def test_majority_attractor_differs_from_every_target():
    majority = hopfield_qr_limits.majority_attractor(MAJORITY_FIXTURE)
    assert np.array_equal(majority, EXPECTED_MAJORITY)
    for a in range(MAJORITY_FIXTURE.shape[0]):
        assert int((majority != MAJORITY_FIXTURE[a]).sum()) == EXPECTED_HAMMING_TO_TARGETS[a] > 0


def test_majority_json_reports_hamming_and_overlap_to_every_target():
    report = hopfield_qr_limits.majority_json(MAJORITY_FIXTURE)
    assert report["n_pixels"] == 5
    assert report["n_patterns"] == 5
    assert report["majority"] == EXPECTED_MAJORITY.tolist()
    assert report["hamming_to_targets"] == EXPECTED_HAMMING_TO_TARGETS
    assert all(d >= 1 for d in report["hamming_to_targets"])  # differs from every target (D-11a)
    n = report["n_pixels"]
    for a, h in enumerate(report["hamming_to_targets"]):
        assert report["overlap_to_targets"][a] == pytest.approx((n - 2 * h) / n)


# ---------- Task 1 (Plan 05): the by-hand async runner's fixed-point sanity (D-11b) ----------

def test_by_hand_async_run_keeps_an_unshifted_fixed_point_fixed():
    # Reuses CORRELATED (05-04): every one of its 4 patterns is an exact fixed point under pinv (D-06/D-07).
    # The by-hand runner (our own implementation, not hopfield.py's trace-replay) must report zero flips.
    W = hopfield.pinv(CORRELATED)
    for a in range(CORRELATED.shape[0]):
        final, sweeps, flips = hopfield_qr_limits.by_hand_async_run(W, CORRELATED[a], seed=1)
        assert flips == 0
        assert sweeps == 1  # one sweep to confirm no neuron wants to flip
        assert np.array_equal(final, CORRELATED[a])


def test_by_hand_async_run_actually_moves_an_unstable_pattern():
    # The flip side of the sanity check: hebb leaves at least one CORRELATED pattern unstable (already shown
    # above), and the by-hand runner must actually flip something when started from one of those, so the
    # "zero flips" result above is a real fixed-point finding and not the runner silently doing nothing.
    W = hopfield.hebb(CORRELATED)
    unstable = next(a for a in range(CORRELATED.shape[0]) if not hopfield.is_fixed(W, CORRELATED[a]))
    _final, _sweeps, flips = hopfield_qr_limits.by_hand_async_run(W, CORRELATED[unstable], seed=1)
    assert flips > 0


# ---------- Task 1 (Plan 05): the shift builder's documented edge convention (D-11b) ----------

def test_shift_pattern_zero_pads_with_light_and_preserves_the_rest():
    side = 3
    base = np.array([[1, -1, 1], [-1, 1, -1], [1, 1, -1]], dtype=np.int64)
    shifted = hopfield_qr_limits.shift_pattern(base, 1)
    assert np.array_equal(shifted[0, :], np.full(side, -1))  # vacated top row: light = -1
    assert np.array_equal(shifted[:, 0], np.full(side, -1))  # vacated left column: light = -1
    assert np.array_equal(shifted[1:, 1:], base[: side - 1, : side - 1])  # the rest carries over unchanged


# ---------- Task 2 (Plan 05): shift.json carries the full pixel vectors the figures need (D-11b) ----------

# N = 9 (3x3), p = 3, linearly independent (so pinv's Gram inverts): the three patterns differ only in
# their last two pixels, mirroring CORRELATED's "mostly identical" shape at a size small enough to reshape.
SHIFT_FIXTURE = np.array(
    [
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, -1],
        [1, 1, 1, 1, 1, 1, 1, -1, 1],
    ],
    dtype=np.int64,
)


def test_shift_json_includes_the_full_pixel_vectors_for_the_figures():
    report = hopfield_qr_limits.shift_json(SHIFT_FIXTURE, source=0, pixels=(1,), seed=1)
    n = SHIFT_FIXTURE.shape[1]
    assert len(report["source_pattern"]) == n
    assert report["source_pattern"] == SHIFT_FIXTURE[0].tolist()
    entry = report["shifts"][0]
    assert len(entry["query"]) == n
    assert len(entry["recovered"]) == n
    assert entry["query_hamming"] == int((np.array(entry["query"]) != SHIFT_FIXTURE[0]).sum())
    assert entry["recovered_hamming"] == int((np.array(entry["recovered"]) != SHIFT_FIXTURE[0]).sum())
