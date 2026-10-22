"""Tests of the guarded campaign run (CAMP-01, CAMP-02, D-07..D-17): the metrics on synthetic creators and the
refusal when the rule identity fails. No real creator is read here."""

from __future__ import annotations

import math

import numpy as np
import pytest

import campaigns
import campaigns_select as cs
from creadores import Creadores

TOPIC_COLUMNS = [name for name, _ in cs.TOPICS]


def build(n, **columns):
    """Synthetic Creadores: ids INF001.., only the columns given (each a list of n numbers)."""
    names = list(columns)
    values = np.empty((n, len(names)), dtype=np.float64)
    for j, name in enumerate(names):
        if len(columns[name]) != n:
            raise ValueError(f"{name}: {len(columns[name])} values for {n} rows")
        values[:, j] = columns[name]
    ids = [f"INF{i + 1:03d}" for i in range(n)]
    return Creadores(ids=ids, names=[f"@c{i + 1}" for i in range(n)], columns=names, values=values)


def topic_columns(labels):
    """The four raw topic shares for creators whose dominant topic is the given label (80 for it, 20/3 else)."""
    columns = {name: [] for name in TOPIC_COLUMNS}
    for label in labels:
        for name, topic in cs.TOPICS:
            columns[name].append(80.0 if topic == label else 20.0 / 3)
    return columns


def test_overlap_counts_shared_ids_once():
    assert campaigns.overlap([1, 2, 3], [3, 2, 9]) == 2
    assert campaigns.overlap([4], [4]) == 1
    assert campaigns.overlap([1, 2], [3, 4]) == 0
    assert campaigns.overlap([], [1]) == 0


def test_list_metrics_ratio_of_sums():
    data = build(2, **topic_columns(["fútbol", "fútbol"]), price_usd=[100, 300],
                 estimated_argentina_reach=[10000, 10000])
    metrics = campaigns.list_metrics([0, 1], data, "fútbol", "alcance")
    assert metrics["n"] == 2
    assert metrics["cost_total"] == pytest.approx(400.0)
    assert metrics["reach_total"] == pytest.approx(20000.0)
    # the ratio of sums (400 / 20000 x 1000), not the mean of the ratios 10 and 30
    assert metrics["cost_per_thousand"] == pytest.approx(20.0)
    assert metrics["criterion_mean"] == pytest.approx(10000.0)


def test_list_metrics_short_and_empty_list():
    data = build(5, **topic_columns(["fútbol"] * 5), price_usd=[10, 20, 30, 40, 50],
                 estimated_argentina_reach=[1000, 2000, 3000, 4000, 5000])
    short = campaigns.list_metrics([0, 1, 2], data, "fútbol", "alcance")
    assert short["n"] == 3
    assert short["reach_total"] == pytest.approx(6000.0)
    assert short["cost_total"] == pytest.approx(60.0)
    assert short["cost_per_thousand"] == pytest.approx(10.0)
    empty = campaigns.list_metrics([], data, "fútbol", "alcance")
    assert empty["n"] == 0
    assert empty["reach_total"] == 0.0 and empty["cost_total"] == 0.0
    for key in ("cost_per_thousand", "topic_dominant_share", "topic_mean_pct", "criterion_mean"):
        assert math.isnan(empty[key]), key


def test_topic_share_counts_dominant():
    data = build(5, **topic_columns(["fútbol", "arte", "fútbol", "perros", "fútbol"]), price_usd=[1] * 5,
                 estimated_argentina_reach=[1000] * 5)
    metrics = campaigns.list_metrics([0, 1, 2, 3, 4], data, "fútbol", "alcance")
    assert metrics["topic_dominant_share"] == pytest.approx(0.6)
    football = data.values[:, data.columns.index("topic_football_pct")]
    assert metrics["topic_mean_pct"] == pytest.approx(float(football.mean()))


def test_main_refuses_without_rule(monkeypatch, tmp_path):
    def refuse(*args, **kwargs):
        raise SystemExit("rule changed (D-07)")

    monkeypatch.setattr(cs, "rule_identity", refuse)
    out = tmp_path / "out"
    with pytest.raises(SystemExit):
        campaigns.main(["--out", str(out)])
    assert not out.exists()
