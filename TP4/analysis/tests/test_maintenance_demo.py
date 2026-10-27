"""Tests of the maintenance demo (CAMP-03, D-18, D-19): the synthetic creator, the drift threshold, the mapping through
scripts/map_creator.py and the BMU and rank helpers. The creator is synthetic; no real creator is added to anything."""

from __future__ import annotations

import math

import numpy as np
import pytest

import creadores
import maintenance_demo as md
from creadores import PREPARED_DIR, RAW_PATH, load_creadores, load_meta, transform_new_creator

META = PREPARED_DIR / "creadores_zscore.meta.json"


@pytest.fixture(scope="module")
def prepared():
    if not META.exists():
        creadores.prepare(RAW_PATH, PREPARED_DIR)
    return PREPARED_DIR


def test_synthetic_creator_relations():
    data = load_creadores()
    row = md.synthetic_creator(data)
    assert row["creator_id"] == "SYN001" and row["name"] == "@sintetico_demo"
    assert set(data.columns) <= set(row)
    assert abs(row["price_ars"] - 1500.0 * row["price_usd"]) < 1e-9
    assert abs(row["organic_posts_pct"] - (100.0 - row["sponsored_posts_pct"])) < 1e-9
    engagement = sum(row[f"{kind}_per_1000"] for kind in ("likes", "comments", "saves", "shares"))
    assert abs(row["total_engagement_per_1000"] - engagement) < 1e-9
    for prefix in ("topic_", "content_"):
        assert abs(sum(v for name, v in row.items() if name.startswith(prefix)) - 100.0) < 1e-9
    assert abs(row["estimated_argentina_reach"] - row["average_reach"] * row["argentina_audience_pct"] / 100.0) <= 0.5
    # the five relations hold for the row as a one-creator dataset (the same audit the prepared data passes)
    one = creadores.Creadores(ids=[row["creator_id"]], names=[row["name"]], columns=list(data.columns),
                              values=np.array([[row[c] for c in data.columns]], dtype=np.float64))
    assert max(creadores.dependency_residuals(one).values()) < 1e-6


def test_drift_check_threshold():
    training = [1.0, 2.0, 3.0]
    assert md.drift_check(2.5, training)["drift"] is False
    assert md.drift_check(3.0, training)["drift"] is False  # equal to the maximum: no drift
    assert md.drift_check(3.1, training)["drift"] is True
    check = md.drift_check(2.5, training)
    assert math.isclose(check["percentile"], 2 / 3)
    assert check["max"] == 3.0 and math.isclose(check["qe"], 2.0)
    assert math.isclose(check["p95"], float(np.percentile(training, 95)))


def test_map_creator_cli_matches_transform(prepared, tmp_path):
    data = load_creadores()
    row = md.synthetic_creator(data)
    raw_csv = tmp_path / "synthetic_creator.csv"
    md.write_raw_csv(row, raw_csv)
    z = md.map_with_cli(raw_csv, META, tmp_path / "synthetic_z.csv")
    expected = transform_new_creator(load_meta(META), row)
    assert z.shape == (26,)
    assert np.max(np.abs(z - expected)) < 1e-12


def test_bmu_and_index_rank():
    prototypes = np.array([[0.0, 0.0], [1.0, 1.0], [5.0, 5.0]])
    neuron, r, c, distance = md.bmu(np.array([0.9, 1.2]), prototypes, 2)
    assert (neuron, r, c) == (1, 0, 1)
    assert math.isclose(distance, math.sqrt(0.1 ** 2 + 0.2 ** 2))
    assert md.index_rank(2.5, [1, 2, 3, 4]) == 3
    assert md.index_rank(10.0, [1, 2, 3, 4]) == 1
    assert md.index_rank(0.0, [1, 2, 3, 4]) == 5
