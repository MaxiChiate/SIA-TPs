"""Tests of the Oja neuron against PCA (OJA-01, OJA-02, D-01..D-05): the C run on the real z-scored data is
compared with the oriented first principal component computed in numpy."""

from __future__ import annotations

import json
import os

import numpy as np
import pytest

import creadores
import oja
import som
import sweep
from creadores import PREPARED_DIR, RAW_PATH, TP_DIR
from pca import pca_eigh, read_prepared

STEM = "creadores_zscore"
EXAMPLE = TP_DIR / "neuron" / "config.json.oja.example"


def prepared():
    if not (PREPARED_DIR / f"{STEM}.csv").exists():
        creadores.prepare(RAW_PATH, PREPARED_DIR)
    return read_prepared(STEM)


def train(tmp_path):
    """neuron/config.json.oja.example on the real data, run through the binary in tmp_path (D-05)."""
    prepared()
    sweep.build_binary()
    config = json.loads(EXAMPLE.read_text())
    config["input"] = os.path.relpath(PREPARED_DIR / f"{STEM}.csv", tmp_path)
    return som.run_binary(config, tmp_path)


def write_run(run_dir, features, w, index, trace_rows, epochs):
    """A hand-made run folder with the file contract of neuron/models/oja.c."""
    run_dir.mkdir(parents=True, exist_ok=True)
    n, p = len(index), len(features)
    (run_dir / "metrics.json").write_text(json.dumps({
        "model": "oja", "seed": 1, "n_samples": n, "n_features": p, "epochs": epochs,
        "eta0": 0.001, "eta_final": 0.0001, "pivot": features[int(np.argmax(np.abs(w)))],
    }))
    (run_dir / "weights.csv").write_text(",".join(features) + "\n" + ",".join(repr(float(x)) for x in w) + "\n")
    (run_dir / "index.csv").write_text(
        "sample,index\n" + "".join(f"{i},{float(index[i])!r}\n" for i in range(n)))
    header = ["epoch", "eta", "w_norm", "delta_w", *features]
    (run_dir / "trace.csv").write_text(
        ",".join(header) + "\n" + "".join(",".join(repr(float(x)) for x in row) + "\n" for row in trace_rows))


def test_input_is_centered():
    features, z, _meta = prepared()
    assert z.shape == (50, len(features))
    assert np.abs(z.mean(axis=0)).max() < 1e-12
    assert np.abs(z.std(axis=0, ddof=1) - 1.0).max() < 1e-12


def test_smoke_run_matches_pc1(tmp_path):
    features, z, _meta = prepared()
    v1 = pca_eigh(z, features).eigenvectors[:, 0]
    run = oja.read_oja_run(train(tmp_path))

    assert run.features == features
    assert oja.abs_cos(run.w, v1) > 0.99
    assert float(run.w @ v1) > 0, "Oja must carry the PCA orientation (D-02)"
    assert abs(float(np.linalg.norm(run.w)) - 1.0) < 1e-12
    assert np.allclose(run.index, z @ run.w, atol=1e-9, rtol=0)
    assert run.trace.shape == (int(run.metrics["epochs"]) + 1, 4 + len(features))
    assert run.metrics["pivot"] == features[int(np.argmax(np.abs(v1)))]


def test_compare_identity_and_flip():
    rng = np.random.default_rng(7)
    z = rng.normal(size=(50, 26))
    v1 = rng.normal(size=26)
    v1 /= np.linalg.norm(v1)
    pc1 = z @ v1

    same = oja.compare(v1, z @ v1, v1, pc1)
    assert same["abs_cos"] == pytest.approx(1.0, abs=1e-12)
    assert same["cos"] == pytest.approx(1.0, abs=1e-12)
    assert same["pearson"] == pytest.approx(1.0, abs=1e-12)
    assert same["spearman"] == pytest.approx(1.0, abs=1e-12)
    assert same["overlap_at_5"] == 5 and same["overlap_at_10"] == 10
    assert same["max_abs_diff"] == pytest.approx(0.0, abs=1e-12)

    flipped = oja.compare(-v1, -(z @ v1), v1, pc1)
    assert flipped["abs_cos"] == pytest.approx(1.0, abs=1e-12)
    assert flipped["cos"] == pytest.approx(-1.0, abs=1e-12)
    assert flipped["spearman"] == pytest.approx(-1.0, abs=1e-12)


def test_top_k_and_overlap_stable():
    assert oja.top_k(np.array([3.0, 1.0, 3.0, 2.0]), 2).tolist() == [0, 2]
    assert oja.overlap([0, 2], [2, 3]) == 1


def test_read_oja_run_rejects_bad_header(tmp_path):
    features = ["a", "b", "c"]
    w = np.array([0.6, 0.0, 0.8])
    index = np.array([1.0, -1.0, 0.5, -0.5])
    trace = [[0, 0.001, 1.0, 0.0, *w], [1, 0.0009, 1.0, 0.1, *w], [2, 0.0008, 1.0, 0.05, *w]]
    run_dir = tmp_path / "run"
    write_run(run_dir, features, w, index, trace, epochs=2)

    run = oja.read_oja_run(run_dir)
    assert run.features == features and run.trace.shape == (3, 7)

    path = run_dir / "trace.csv"
    path.write_text(path.read_text().replace("epoch,eta,w_norm,delta_w", "epoch,eta,delta_w", 1))
    with pytest.raises(ValueError, match="trace.csv"):
        oja.read_oja_run(run_dir)


def test_convergence_abs_cos_normalizes():
    v = np.array([0.6, 0.0, 0.8])
    noisy = v + np.array([0.0, 0.1, 0.0])
    trace = np.array([
        [0, 0.001, 1.5, 0.0, *(2.0 * v)],
        [1, 0.0009, 2.5, 0.25, *(-3.0 * v)],
        [2, 0.0008, 1.0, 0.125, *noisy],
    ])
    rows = oja.convergence_rows(4, trace, v)

    assert [row["epoch"] for row in rows] == [0, 1, 2] and all(row["seed"] == 4 for row in rows)
    assert rows[0]["abs_cos"] == pytest.approx(1.0, abs=1e-12)
    assert rows[1]["abs_cos"] == pytest.approx(1.0, abs=1e-12)
    assert rows[2]["abs_cos"] == pytest.approx(float(noisy @ v / np.linalg.norm(noisy)), abs=1e-12)
    assert [row["w_norm"] for row in rows] == [1.5, 2.5, 1.0]
    assert [row["delta_w"] for row in rows] == [0.0, 0.25, 0.125]
    assert [row["eta"] for row in rows] == [0.001, 0.0009, 0.0008]


def test_evidence_both_signs():
    """D-06 on a synthetic table whose index is topic_dogs_pct: the correlation and the overlaps flip with the sign."""
    n = 12
    rng = np.random.default_rng(3)
    dogs = np.arange(1.0, n + 1.0) * 5.0  # distinct, increasing
    rest = rng.uniform(0.0, 1.0, size=(n, 3))
    columns = ["followers", "topic_football_pct", "topic_makeup_pct", "topic_dogs_pct", "topic_art_pct"]
    values = np.column_stack([rng.uniform(1e3, 1e5, size=n), rest[:, 0], rest[:, 1], dogs, rest[:, 2]])
    ids = [f"C{i:02d}" for i in range(n)]
    data = creadores.Creadores(ids=ids, names=[f"@c{i}" for i in range(n)], columns=columns, values=values)
    features = ["a", "b", "c"]
    w = np.array([0.1, -0.8, 0.3])
    index = dogs.copy()

    ev = oja.evidence(w, features, index, data, ids)

    assert [row["variable"] for row in ev["weights"]] == ["b", "c", "a"]
    assert [row["w"] for row in ev["weights"]] == [-0.8, 0.3, 0.1]

    corr = {(row["target"], row["sign"]): row for row in ev["correlations"]}
    assert len(corr) == 10
    assert corr[("topic_dogs_pct", 1)]["pearson"] == pytest.approx(1.0, abs=1e-12)
    assert corr[("topic_dogs_pct", -1)]["pearson"] == pytest.approx(-1.0, abs=1e-12)
    assert corr[("topic_dogs_pct", 1)]["spearman"] == pytest.approx(1.0, abs=1e-12)
    assert corr[("topic_dogs_pct", -1)]["spearman"] == pytest.approx(-1.0, abs=1e-12)

    top = {(row["sign"], row["topic"]): row for row in ev["top10"]}
    assert len(top) == 8
    assert top[(1, "perros")]["overlap_top10_by_share"] == 10
    assert top[(-1, "perros")]["overlap_top10_by_share"] == 8
    assert top[(1, "perros")]["dominant_in_index_top10"] == 10  # dogs is the dominant topic of the 10 largest

    assert ev["maximum"]["+1"]["creator_id"] == ids[int(np.argmax(index))]
    assert ev["maximum"]["-1"]["creator_id"] == ids[int(np.argmin(index))]
