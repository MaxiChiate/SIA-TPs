"""Tests of the region rule, the raw-unit profiles and the pre-declared PC1/PC2 contrast statistics (SOM-05)."""

from __future__ import annotations

import numpy as np

import som
import som_profiles


def test_regions_synthetic():
    # k = 3, one feature: columns 0 and 1 are 1 apart, column 2 is 10 further. Of the 12 adjacent pairs, 6 vertical
    # ones have distance 0, 3 have distance 1 and 3 have distance 10: the linear 75th percentile is 3.25.
    k = 3
    protos = np.array([[0.0], [1.0], [11.0]] * 3)
    hits = np.array([5, 5, 1, 5, 5, 0, 5, 5, 0])
    result = som_profiles.regions(protos, hits, k)
    distances = som.edge_distances(protos, k)
    assert np.isclose(result.threshold, np.percentile(distances, 75.0))
    assert np.isclose(result.threshold, 3.25)
    assert int(result.cut.sum()) == 3
    assert list(result.cut) == [bool(d > result.threshold) for d in distances]
    assert list(result.labels) == [0, 0, 1, 0, 0, -1, 0, 0, -1]
    assert list(result.sizes) == [30, 1]
    assert list(result.interpretable) == [True, False]


def test_profiles_raw_means():
    raw = np.array([[1.0, 10.0], [3.0, 20.0], [5.0, 40.0], [100.0, 1000.0]])
    rows = som_profiles.profiles(np.array([0, 0, 1, -1]), raw, ["a", "b"])
    assert [row["group"] for row in rows] == [0, 1]
    assert [row["n"] for row in rows] == [2, 1]
    assert rows[0]["a"] == 2.0 and rows[0]["b"] == 15.0
    assert rows[1]["a"] == 5.0 and rows[1]["b"] == 40.0


def test_grid_r2_rotation_reflection():
    rng = np.random.default_rng(7)
    k = 4
    rows = rng.integers(0, k, size=30)
    cols = rng.integers(0, k, size=30)
    y = rng.normal(size=30) + 0.5 * rows
    base = som_profiles.grid_r2(y, rows, cols)
    assert 0.0 < base < 1.0
    rotated = som_profiles.grid_r2(y, cols, k - 1 - rows)
    reflected = som_profiles.grid_r2(y, rows, k - 1 - cols)
    assert abs(base - rotated) < 1e-12
    assert abs(base - reflected) < 1e-12
    # a perfect plane gives R^2 = 1
    assert abs(som_profiles.grid_r2(2.0 + 3.0 * rows - cols, rows, cols) - 1.0) < 1e-12


def test_permutation_deterministic():
    rng = np.random.default_rng(1)
    k, n = 4, 20
    bmu = rng.integers(0, k * k, size=n)
    rows, cols = bmu // k, bmu % k
    y = rng.normal(size=n)
    plane = rng.normal(size=(n, 2))
    a = som_profiles.r2_null(y, rows, cols, np.random.default_rng(2026), n=50)
    b = som_profiles.r2_null(y, rows, cols, np.random.default_rng(2026), n=50)
    assert a.shape == (50,) and np.array_equal(a, b)
    c = som_profiles.mantel_null(bmu, k, plane, np.random.default_rng(2026), n=50)
    d = som_profiles.mantel_null(bmu, k, plane, np.random.default_rng(2026), n=50)
    assert c.shape == (50,) and np.array_equal(c, d)
    null = np.array([0.1, 0.5, 0.5, 0.9])
    assert som_profiles.permutation_pvalue(0.5, null) == (1 + 3) / (1 + 4)
    assert som_profiles.permutation_pvalue(2.0, null) == 1 / 5
    p = som_profiles.permutation_pvalue(-1.0, null)
    assert 0.0 < p <= 1.0 and p == 1.0


def test_edge_contrast_synthetic():
    # k = 3, one creator in each of neurons 0..7, neuron 8 empty. The prototype is the PC1 value of its creator,
    # so every edge distance equals the gap in neuron-mean PC1.
    k = 3
    pc1 = np.array([0.0, 1.0, 3.0, 7.0, 12.0, 20.0, 33.0, 54.0])
    pc2 = np.array([5.0, 1.0, 4.0, 2.0, 9.0, 3.0, 8.0, 6.0])
    pc = np.column_stack([pc1, pc2])
    bmu = np.arange(8)
    hits = np.array([1, 1, 1, 1, 1, 1, 1, 1, 0])
    protos = np.append(pc1, 100.0).reshape(-1, 1)
    result = som_profiles.edge_contrast(protos, hits, bmu, k, pc)
    assert abs(result["rho_pc1"] - 1.0) < 1e-12
    assert result["n_edges"] == 10 and result["n_excluded"] == 2
    assert result["rho_pc2"] < 0.999


def test_high_u_edges_units():
    protos = np.array([[0.0, 0.0, 0.0], [3.0, 4.0, 0.0], [0.0, 1.0, 0.0], [6.0, 8.0, 0.0]])
    std = np.array([1.0, 2.0, 10.0])
    features = ["f0", "f1", "f2"]
    edges = som_profiles.high_u_edges(protos, np.array([1, 1, 1, 1]), 2, features, std, top_edges=2, top_vars=3)
    assert [(e["neuron_a"], e["neuron_b"]) for e in edges] == [(2, 3), (0, 1)]
    assert np.isclose(edges[0]["distance"], np.sqrt(85.0))
    first = edges[0]["variables"]
    assert [v["variable"] for v in first] == ["f1", "f0", "f2"]
    assert first[0]["delta_z"] == 7.0 and first[0]["delta_raw"] == 14.0
    assert first[1]["delta_z"] == 6.0 and first[1]["delta_raw"] == 6.0
    # an empty neuron never carries an edge
    only = som_profiles.high_u_edges(protos, np.array([1, 1, 1, 0]), 2, features, std, top_edges=5, top_vars=1)
    assert all(3 not in (e["neuron_a"], e["neuron_b"]) for e in only)
    assert len(only) == 2 and (only[0]["neuron_a"], only[0]["neuron_b"]) == (0, 1)
    # disagreement pairs: creators 0 and 1 are far apart in the grid yet identical in the plane; 2 and 3 share a neuron
    # yet are far apart in the plane
    bmu = np.array([0, 15, 5, 5, 0, 15])
    plane = np.array([[0.0, 0.0], [0.1, 0.0], [10.0, 0.0], [-10.0, 0.0], [0.0, 0.2], [0.1, 0.3]])
    found = som_profiles.disagreements(bmu, 4, plane, top=1)
    close = [d for d in found if d["kind"] == "plano_cerca_grilla_lejos"]
    far = [d for d in found if d["kind"] == "plano_lejos_grilla_cerca"]
    assert len(close) == 1 and len(far) == 1
    assert (far[0]["creator_a"], far[0]["creator_b"]) == (2, 3)
    assert np.isclose(close[0]["grid_distance"], np.hypot(3, 3))
