"""Tests of the U-matrix, the grid adjacency and the figure functions of the chosen map (SOM-04, D-04)."""

from __future__ import annotations

import math
import os

import numpy as np

import som
import som_figures
import sweep
from creadores import TP_DIR

FIXTURE = TP_DIR / "neuron" / "tests" / "fixtures" / "zscore_small.csv"


def test_umatrix_2x2():
    # neuron order (0,0), (0,1), (1,0), (1,1) = rows (0,0), (3,4), (0,1), (6,8)
    protos = np.array([[0.0, 0.0], [3.0, 4.0], [0.0, 1.0], [6.0, 8.0]])
    got = som.umatrix(protos, 2)
    root = math.sqrt(85.0)
    expected = np.array([[3.0, 5.0], [(1.0 + root) / 2.0, (5.0 + root) / 2.0]])
    # (0,0) neighbours (3,4) at 5 and (0,1) at 1 -> 3; (0,1) neighbours (0,0) at 5 and (6,8) at 5 -> 5
    expected[0, 0], expected[0, 1] = 3.0, 5.0
    assert got.shape == (2, 2)
    assert np.allclose(got, expected, atol=1e-12, rtol=0)


def test_adjacent_pairs():
    k = 3
    pairs = som.adjacent_pairs(k)
    assert len(pairs) == 2 * k * (k - 1) == 12
    assert len(set(pairs)) == 12
    for a, b in pairs:
        assert a < b
        assert abs(a // k - b // k) + abs(a % k - b % k) == 1
    protos = np.arange(k * k, dtype=float).reshape(-1, 1) ** 2
    distances = som.edge_distances(protos, k)
    assert distances.shape == (12,)
    for (a, b), d in zip(pairs, distances):
        assert d == abs(protos[a, 0] - protos[b, 0])


def test_main_planes_rule():
    features = ["a", "b", "c", "d", "e", "f"]
    loads = np.zeros((6, 2))
    loads[:, 0] = [0.1, -0.9, 0.5, 0.3, -0.7, 0.2]  # |PC1|: b, e, c, d, f, a
    loads[:, 1] = [0.2, 0.95, -0.1, 0.8, 0.6, -0.9]  # |PC2|: b, f, d, e, a, c
    # n = 2: PC1 gives b, e; PC2 skips b and picks f, d
    assert som_figures.main_planes(loads, features, n=2) == ["b", "e", "f", "d"]
    # n = 4: PC1 gives b, e, c, d; only f and a remain for PC2 (b, d, e already taken)
    names = som_figures.main_planes(loads, features, n=4)
    assert names == ["b", "e", "c", "d", "f", "a"]
    assert len(set(names)) == len(names)


def train_fixture(tmp_path, seed=3):
    config = {"model": "kohonen", "seed": seed, "input": os.path.relpath(FIXTURE, tmp_path), "grid_k": 3,
              "neighborhood": "step", "radius0": 1.5, "radius_final": 1.0, "eta0": 0.5, "eta_final": 0.01,
              "epochs": 8}
    sweep.build_binary()
    return som.read_run(som.run_binary(config, tmp_path))


def synthetic_stage1():
    rows = []
    for neighborhood in ("step", "gaussian"):
        for k in (2, 3):
            row = {"label": f"k{k}-{neighborhood}", "grid_k": str(k), "neighborhood": neighborhood}
            for measure, base in (("qe", 3.0), ("qe_loo", 3.4), ("te", 0.04), ("empty_fraction", 0.1),
                                  ("creators_per_occupied", 2.5)):
                row[f"{measure}_mean"] = str(base - 0.1 * k)
                row[f"{measure}_sd"] = "0.02"
            row["stability"] = "0.7"
            rows.append(row)
    selection = {"chosen_k": 3, "qe_train_argmin_k": 3,
                 "thresholds": {"te_max": 0.05, "empty_max": 0.2, "creators_min": 2.0}}
    return rows, selection


def read_bytes(path):
    return path.read_bytes()


def test_figures_deterministic(tmp_path):
    work = tmp_path / "run"
    work.mkdir()
    run = train_fixture(work)
    k = run.k
    U = som.umatrix(run.prototypes, k)
    cell = np.full((k, k), np.nan)
    cell.flat[0] = 1.0
    planes = [som_figures.Plane(f"v{i}", run.prototypes[:, i].reshape(k, k), "z", "z") for i in range(3)]
    planes.append(som_figures.Plane("raw", cell, "raw", "%"))
    rows, selection = synthetic_stage1()

    def draw(out):
        out.mkdir()
        som_figures.plot_map(run.hits, U, k, "t", "caption; orientacion arbitraria", out / "map")
        som_figures.plot_planes(planes, k, run.hits, "t", "caption", out / "planes", ncols=2)
        som_figures.plot_trace(run.trace, "t", out / "trace")
        som_figures.plot_stage1_curves(rows, selection, out / "curves")
        return out

    first, second = draw(tmp_path / "a"), draw(tmp_path / "b")
    for stem in ("map", "planes", "trace", "curves"):
        for suffix in (".svg", ".png"):
            assert (first / f"{stem}{suffix}").stat().st_size > 0
        assert read_bytes(first / f"{stem}.svg") == read_bytes(second / f"{stem}.svg")
