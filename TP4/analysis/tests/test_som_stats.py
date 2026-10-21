"""Tests of seed stability (D-13, tie-aware Spearman) and of the QE leave-one-out driver (D-09)."""

from __future__ import annotations

import math

import numpy as np

import som


def rotate90(bmu, k):
    """(r, c) -> (c, k - 1 - r) on neuron indices r * k + c."""
    r, c = bmu // k, bmu % k
    return c * k + (k - 1 - r)


def reflect(bmu, k):
    """(r, c) -> (r, k - 1 - c)."""
    r, c = bmu // k, bmu % k
    return r * k + (k - 1 - c)


def test_average_ranks_ties():
    assert np.array_equal(som.average_ranks(np.array([1, 1, 1, 2, 2, 3])), [2, 2, 2, 4.5, 4.5, 6])
    assert np.array_equal(som.average_ranks(np.array([3, 1, 2])), [3, 1, 2])


def test_spearman_ties_known_values():
    a = np.array([0.3, 1.2, -0.7, 2.0])
    assert abs(som.spearman_ties(a, a) - 1.0) < 1e-15
    assert abs(som.spearman_ties(a, -a) + 1.0) < 1e-15
    assert abs(som.spearman_ties([1, 2, 2, 3], [1, 3, 2, 4]) - math.sqrt(0.9)) < 1e-15
    assert math.isnan(som.spearman_ties([5, 5, 5], [1, 2, 3]))
    assert math.isnan(som.spearman_ties([1, 2, 3], [4, 4, 4]))


def test_grid_distance_vector():
    got = som.grid_distance_vector(np.array([0, 1, 3]), 2)
    assert np.allclose(got, [1.0, math.sqrt(2.0), 1.0], atol=1e-15, rtol=0)


def test_stability_rotation_reflection():
    k = 3
    seed1 = np.array([0, 1, 4, 8, 5, 2])
    seeds = [seed1, rotate90(seed1, k), reflect(seed1, k)]
    value, nan_pairs = som.stability(seeds, k)
    assert abs(value - 1.0) < 1e-12 and nan_pairs == 0


def test_stability_creator_permutation():
    k = 3
    rng = np.random.default_rng(7)
    seeds = [rng.integers(0, k * k, size=6) for _ in range(3)]
    base, base_nan = som.stability(seeds, k)
    assert 0.0 < abs(base) < 1.0 - 1e-6  # a non-trivial example: not the degenerate 1.0
    perm = rng.permutation(6)
    permuted, permuted_nan = som.stability([s[perm] for s in seeds], k)
    assert abs(base - permuted) < 1e-12 and base_nan == permuted_nan


def test_stability_all_nan():
    seeds = [np.zeros(6, dtype=int) for _ in range(3)]
    assert som.stability(seeds, 3) == (0.0, 3)
    # one NaN pair is dropped and counted, the rest still averages
    seeds = [np.zeros(6, dtype=int), np.array([0, 1, 4, 8, 5, 2]), np.array([0, 1, 4, 8, 5, 2])]
    value, nan_pairs = som.stability(seeds, 3)
    assert nan_pairs == 2 and abs(value - 1.0) < 1e-12


def test_medoid_seed():
    nan = float("nan")
    matrix = np.array([[nan, 0.9, 0.5], [0.9, nan, 0.7], [0.5, 0.7, nan]])
    assert som.medoid_seed(matrix, [4, 5, 6]) == 5
    tied = np.array([[nan, 0.5, 0.5], [0.5, nan, 0.5], [0.5, 0.5, nan]])
    assert som.medoid_seed(tied, [9, 3, 6]) == 3
    # a row with no finite entry never wins
    lone = np.array([[nan, nan, nan], [nan, nan, 0.1], [nan, 0.1, nan]])
    assert som.medoid_seed(lone, [1, 2, 3]) == 2
