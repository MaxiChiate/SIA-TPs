"""Cross-check of the C Kohonen measures against an independent numpy recomputation (SOM-02, D-04)."""

from __future__ import annotations

import csv
import json
import os

import numpy as np
import pytest

import creadores
import som
import sweep
from creadores import PREPARED_DIR, RAW_PATH
from pca import read_prepared

STEM = "creadores_zscore"

CASES = {
    "step-8": {"grid_k": 8, "neighborhood": "step", "radius0": 4.0, "radius_final": 1.0},
    "gaussian-4": {"grid_k": 4, "neighborhood": "gaussian", "radius0": 2.0, "radius_final": 0.5},
}


def train(tmp_path, case):
    if not (PREPARED_DIR / f"{STEM}.csv").exists():
        creadores.prepare(RAW_PATH, PREPARED_DIR)
    sweep.build_binary()
    config = {
        "model": "kohonen",
        "seed": 3,
        "input": os.path.relpath(PREPARED_DIR / f"{STEM}.csv", tmp_path),
        "eta0": 0.5,
        "eta_final": 0.01,
        "epochs": 30,
        **case,
    }
    return som.run_binary(config, tmp_path)


@pytest.mark.parametrize("name", list(CASES))
def test_recompute_metrics_from_run(tmp_path, name):
    run_dir = train(tmp_path, CASES[name])
    _features, z, _meta = read_prepared(STEM)
    run = som.read_run(run_dir)
    k = CASES[name]["grid_k"]
    assert run.k == k and run.prototypes.shape == (k * k, z.shape[1])

    got = som.metrics_from_prototypes(z, run.prototypes, k)
    m = run.metrics

    assert abs(got["qe"] - m["qe"]) < 1e-12
    assert abs(got["te"] - m["te"]) < 1e-12
    assert np.array_equal(got["hits"], run.hits) and int(got["hits"].sum()) == z.shape[0]
    assert np.array_equal(got["bmu"], run.bmu)
    assert np.array_equal(got["bmu2"], run.bmu2)
    assert np.allclose(got["distances"], run.distance, atol=1e-12, rtol=0)
    assert got["occupied_neurons"] == m["occupied_neurons"]
    assert abs(got["empty_fraction"] - m["empty_fraction"]) < 1e-12
    assert abs(got["mean_hits_occupied"] - m["mean_hits_occupied"]) < 1e-12
    assert got["max_hits"] == m["max_hits"]
    assert got["singleton_neurons"] == m["singleton_neurons"]
    assert run.trace.shape == (CASES[name].get("epochs", 30) + 1, 5)
    assert abs(run.trace[-1, 3] - m["qe"]) < 1e-12
    assert abs(run.trace[-1, 4] - m["te"]) < 1e-12


def test_read_run_rejects_broken_contract(tmp_path):
    run_dir = train(tmp_path, CASES["gaussian-4"])
    som.read_run(run_dir)

    path = run_dir / "occupancy.csv"
    original = path.read_text()
    path.write_text(original.replace("neuron,row,col,hits", "neuron,col,row,hits", 1))
    with pytest.raises(ValueError, match="occupancy.csv"):
        som.read_run(run_dir)
    path.write_text(original)

    path = run_dir / "prototypes.csv"
    original = path.read_text()
    lines = original.splitlines()
    lines[2], lines[3] = lines[3], lines[2]
    path.write_text("\n".join(lines) + "\n")
    with pytest.raises(ValueError, match="prototypes.csv"):
        som.read_run(run_dir)


def test_nearest_distance_lowest_index_on_ties():
    protos = np.array([[1.0, 0.0], [0.0, 1.0], [3.0, 3.0]])
    index, distance = som.nearest_distance(np.array([0.0, 0.0]), protos)
    assert index == 0 and distance == 1.0
