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


# ---------- QE leave-one-out (D-09) ----------

import csv  # noqa: E402
import json  # noqa: E402

import pytest  # noqa: E402

import som_loo  # noqa: E402
from sweep import NEURON_DIR  # noqa: E402

FIXTURE = NEURON_DIR / "tests" / "fixtures" / "zscore_small.csv"


def fixture_series(tmp_path, **overrides):
    base = {
        "model": "kohonen", "seed": 1, "input": "tests/fixtures/zscore_small.csv", "grid_k": 3,
        "neighborhood": "step", "radius0": 1.5, "radius_final": 1.0, "eta0": 0.5, "eta_final": 0.01, "epochs": 5,
    }
    base.update(overrides)
    (tmp_path / "base.json").write_text(json.dumps(base))
    series = tmp_path / "series.json"
    series.write_text(json.dumps({"base_config": "base.json", "seeds": [1, 2]}))
    return series


def test_loo_fixture(tmp_path):
    series = fixture_series(tmp_path)
    out = tmp_path / "out1"
    rows, by_seed = som_loo.run_loo(series, out, workers=2)
    assert len(rows) == 12
    for row in rows:
        assert np.isfinite(row["distance"]) and row["distance"] > 0
        assert 0 <= row["bmu"] <= 8
    assert [(r["seed"], r["fold"]) for r in rows] == [(s, f) for s in (1, 2) for f in range(6)]
    assert len(by_seed) == 2
    for entry in by_seed:
        distances = [r["distance"] for r in rows if r["seed"] == entry["seed"]]
        assert entry["n_folds"] == 6 and abs(entry["qe_loo"] - np.mean(distances)) < 1e-12
    assert not (out / "tmp").exists() and not (out / "results").exists()
    assert (out / "loo.csv").is_file() and (out / "loo_by_seed.csv").is_file()
    with (out / "loo.csv").open() as file:
        assert next(csv.reader(file)) == ["label", "variant", "seed", "fold", "bmu", "distance"]

    som_loo.run_loo(series, tmp_path / "out2", workers=3)
    assert (out / "loo.csv").read_bytes() == (tmp_path / "out2" / "loo.csv").read_bytes()
    assert (out / "loo_by_seed.csv").read_bytes() == (tmp_path / "out2" / "loo_by_seed.csv").read_bytes()


def test_loo_folds_bytes(tmp_path):
    paths = som_loo.write_folds(FIXTURE, tmp_path / "folds")
    assert len(paths) == 6
    lines = FIXTURE.read_text().splitlines()
    header, data = lines[0], lines[1:]
    for i, path in enumerate(paths):
        assert path.name == f"fold_{i:02d}.csv"
        expected = "".join(line + "\n" for line in [header] + data[:i] + data[i + 1:])
        assert path.read_bytes() == expected.encode()


def test_loo_failure_stops(tmp_path):
    series = fixture_series(tmp_path, neighborhood="hex")
    out = tmp_path / "out"
    with pytest.raises(SystemExit) as caught:
        som_loo.run_loo(series, out, workers=2)
    message = str(caught.value)
    assert "base" in message and "seed 1" in message and "fold 0" in message
    assert not (out / "loo.csv").exists() and not (out / "loo_by_seed.csv").exists()
    assert not (out / "tmp").exists()
