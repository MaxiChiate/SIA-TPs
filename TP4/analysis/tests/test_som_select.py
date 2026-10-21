"""Tests of the pre-registered grid-selection rule (D-10..D-15): every branch on synthetic tables."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import numpy as np
import pytest

import som_select

TP_DIR = Path(__file__).resolve().parent.parent.parent


def make_row(k, neighborhood="step", te=0.0, empty=0.0, cpo=3.0, qe=1.0, qe_loo=2.0, qe_loo_sd=0.01,
             stability=0.5):
    """One aggregated configuration, with the fields aggregate() produces."""
    return {
        "label": f"k{k}-{neighborhood}",
        "grid_k": k,
        "neighborhood": neighborhood,
        "te_mean": te,
        "empty_fraction_mean": empty,
        "creators_per_occupied_mean": cpo,
        "qe_mean": qe,
        "qe_loo_mean": qe_loo,
        "qe_loo_sd": qe_loo_sd,
        "stability": stability,
        "nan_pairs": 0,
    }


def test_select_filters_boundaries():
    rows = [
        make_row(2, te=0.05, qe_loo=2.0),
        make_row(3, te=0.06, qe_loo=1.0),
        make_row(4, empty=0.21, qe_loo=1.0),
        make_row(5, cpo=1.99, qe_loo=1.0),
    ]
    result = som_select.select_grid(rows)
    assert result["outcome"] == "chosen"
    assert result["chosen_k"] == 2
    assert result["te_filter_dropped"] is False
    flags = {entry["k"]: entry for entry in result["per_k"]}
    assert flags[2]["passes_te"] and flags[2]["passes_empty"] and flags[2]["passes_creators"]
    assert not flags[3]["passes_te"] and flags[3]["passes_empty"] and flags[3]["passes_creators"]
    assert not flags[4]["passes_empty"]
    assert not flags[5]["passes_creators"]
    # equality passes at the three thresholds
    assert som_select.passes_filters(make_row(2, te=0.05, empty=0.20, cpo=2.0)) == {
        "te": True, "empty": True, "creators": True}
    # one row per k: a duplicate is an input error, not a silent choice
    with pytest.raises(ValueError):
        som_select.select_grid([make_row(2), make_row(2)])


def test_select_lowest_qe_loo():
    rows = [make_row(2, qe_loo=2.0), make_row(3, qe_loo=1.8), make_row(4, qe_loo=1.9)]
    result = som_select.select_grid(rows)
    assert result["chosen_k"] == 3
    assert result["chosen_label"] == "k3-step"
    assert result["decided_by"] == "qe_loo"
    assert result["tie_band"] == [3]
    assert result["winner_by_qe_loo"] == 3


def test_select_tie_band_stability():
    # binary-friendly numbers: the band is [2.0, 2.5) because the winner's SD is 0.5 and the test is strict
    rows = [
        make_row(2, qe_loo=2.0, qe_loo_sd=0.5, stability=0.5),
        make_row(3, qe_loo=2.25, qe_loo_sd=0.5, stability=0.9),
        make_row(4, qe_loo=2.5, qe_loo_sd=0.5, stability=0.99),
    ]
    result = som_select.select_grid(rows)
    assert result["winner_by_qe_loo"] == 2
    assert result["tie_band"] == [2, 3]
    assert result["chosen_k"] == 3
    assert result["decided_by"] == "stability"


def test_select_equal_stability_smaller_k():
    rows = [
        make_row(2, qe_loo=2.0, qe_loo_sd=0.5, stability=0.7),
        make_row(3, qe_loo=2.25, qe_loo_sd=0.5, stability=0.7),
    ]
    result = som_select.select_grid(rows)
    assert result["tie_band"] == [2, 3]
    assert result["chosen_k"] == 2
    assert result["decided_by"] == "smallest_k"

    # exact QE-LOO equality: the smaller k is the winner (and a zero SD leaves the band at one member)
    equal = [make_row(4, qe_loo=1.5, qe_loo_sd=0.0), make_row(3, qe_loo=1.5, qe_loo_sd=0.0)]
    result = som_select.select_grid(equal)
    assert result["winner_by_qe_loo"] == 3
    assert result["chosen_k"] == 3
    assert result["tie_band"] == [3]
    assert result["decided_by"] == "qe_loo"


def test_select_ignores_gaussian():
    rows = [
        make_row(2, qe_loo=2.0),
        make_row(3, qe_loo=2.5),
        make_row(4, "gaussian", qe_loo=0.5, qe=0.1),
    ]
    result = som_select.select_grid(rows)
    assert result["chosen_k"] == 2
    assert [entry["k"] for entry in result["per_k"]] == [2, 3]
    assert [entry["k"] for entry in result["gaussian"]] == [4]
    assert result["gaussian"][0]["qe_loo_mean"] == 0.5


def test_select_drop_te_only():
    rows = [
        make_row(2, te=0.30, empty=0.5, qe_loo=1.0),
        make_row(3, te=0.30, qe_loo=2.0),
        make_row(4, te=0.20, cpo=1.0, qe_loo=1.5),
    ]
    result = som_select.select_grid(rows)
    assert result["outcome"] == "chosen"
    assert result["te_filter_dropped"] is True
    assert result["chosen_k"] == 3


def test_select_no_eligible():
    rows = [
        make_row(2, empty=0.5, te=0.0),
        make_row(3, cpo=1.0, te=0.4),
        make_row(4, empty=0.3, cpo=1.0),
    ]
    result = som_select.select_grid(rows)
    assert result["outcome"] == "no_eligible_grid"
    for key in ("chosen_k", "chosen_label", "winner_by_qe_loo", "decided_by"):
        assert result[key] is None
    assert result["tie_band"] == []
    assert result["te_filter_dropped"] is True
    flags = {entry["k"]: entry for entry in result["per_k"]}
    assert not flags[2]["passes_empty"]
    assert not flags[3]["passes_creators"]
    assert not flags[4]["passes_empty"] and not flags[4]["passes_creators"]


def test_select_reports_qe_argmin():
    rows = [
        make_row(2, qe=3.0, qe_loo=2.0),
        make_row(3, qe=2.0, qe_loo=2.5),
        make_row(4, qe=1.0, qe_loo=1.0, empty=0.9),  # lowest training QE, filtered out
    ]
    result = som_select.select_grid(rows)
    assert result["qe_train_argmin_k"] == 4
    assert result["chosen_k"] == 2
    assert result["chosen_k"] != result["qe_train_argmin_k"]
    assert result["thresholds"] == {"te_max": 0.05, "empty_max": 0.20, "creators_min": 2.0}


def summary_row(label, seed, occupied, status="ok", qe=1.0, te=0.0, k=3):
    return {
        "run": f"000_{label}_seed{seed}", "variant": "0", "label": label, "seed": str(seed), "status": status,
        "grid_k": str(k), "neighborhood": "step", "radius0": "1.5", "radius_final": "1.0", "eta0": "0.5",
        "eta_final": "0.01", "epochs": "260", "n_samples": "50", "qe": str(qe), "te": str(te),
        "occupied_neurons": str(occupied), "empty_fraction": str(1 - occupied / (k * k)),
    }


def test_aggregate_per_seed_ratio():
    summary = [summary_row("k3-step", 1, 10, qe=1.0, k=7), summary_row("k3-step", 2, 40, qe=3.0, k=7)]
    loo = [{"label": "k3-step", "seed": "1", "qe_loo": "2.0"}, {"label": "k3-step", "seed": "2", "qe_loo": "4.0"}]
    rows = som_select.aggregate(summary, loo, {"k3-step": (0.75, 2)})
    assert len(rows) == 1
    row = rows[0]
    assert row["creators_per_occupied_mean"] == pytest.approx((5 + 1.25) / 2)
    assert row["creators_per_occupied_mean"] != pytest.approx(50 / 25)
    assert row["qe_mean"] == pytest.approx(2.0)
    assert row["qe_sd"] == pytest.approx(np.std([1.0, 3.0], ddof=1))
    assert row["qe_loo_mean"] == pytest.approx(3.0)
    assert row["qe_loo_sd"] == pytest.approx(np.std([2.0, 4.0], ddof=1))
    assert row["grid_k"] == 7 and row["neighborhood"] == "step" and row["n_seeds"] == 2
    assert row["stability"] == 0.75 and row["nan_pairs"] == 2

    failed = [summary_row("k3-step", 1, 10), summary_row("k3-step", 2, 40, status="error: boom")]
    with pytest.raises(ValueError):
        som_select.aggregate(failed, loo, {"k3-step": (0.75, 0)})
    with pytest.raises(ValueError):
        som_select.aggregate(summary, loo[:1], {"k3-step": (0.75, 0)})
    with pytest.raises(ValueError):
        som_select.aggregate(summary[:1], loo[:1], {"k3-step": (0.75, 0)})  # one seed has no SD (ddof 1)


def test_rule_digest_markers(tmp_path):
    path = tmp_path / "doc.md"
    body = "\nlínea uno\n**Filtros.** TE <= 0,05\n"
    path.write_bytes(f"antes\n{som_select.RULE_START}{body}{som_select.RULE_END}\ndespués\n".encode("utf-8"))
    assert som_select.rule_digest(path) == hashlib.sha256(body.encode("utf-8")).hexdigest()

    path.write_text("sin marcadores\n", encoding="utf-8")
    with pytest.raises(ValueError):
        som_select.rule_digest(path)
    path.write_text(f"{som_select.RULE_START}\na\n{som_select.RULE_START}\nb\n{som_select.RULE_END}\n",
                    encoding="utf-8")
    with pytest.raises(ValueError):
        som_select.rule_digest(path)
    path.write_text(f"{som_select.RULE_END}\na\n{som_select.RULE_START}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        som_select.rule_digest(path)


def git(repo, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
                           *args], cwd=repo, check=True, capture_output=True, text=True)


def test_guard_untracked_modified_clean(tmp_path):
    git(tmp_path, "init", "-q")
    (tmp_path / "rule.md").write_text("regla\n", encoding="utf-8")
    with pytest.raises(SystemExit) as untracked:
        som_select.rule_guard(["rule.md"], tmp_path)
    assert "rule.md" in str(untracked.value)

    git(tmp_path, "add", "rule.md")
    git(tmp_path, "commit", "-q", "-m", "rule")
    commit = som_select.rule_guard(["rule.md"], tmp_path)
    assert len(commit) == 40 and int(commit, 16) >= 0
    assert commit == git(tmp_path, "rev-parse", "HEAD").stdout.strip()

    (tmp_path / "rule.md").write_text("regla cambiada\n", encoding="utf-8")
    with pytest.raises(SystemExit) as modified:
        som_select.rule_guard(["rule.md"], tmp_path)
    assert "rule.md" in str(modified.value)


def test_stage2_series_one_at_a_time():
    series = som_select.stage2_series(4)
    base = series["set"]
    assert base["grid_k"] == 4 and base["radius0"] == 2.0 and base["neighborhood"] == "step"
    assert base["epochs"] == 260 and base["eta0"] == 0.5
    assert series["seeds"] == list(range(1, 11))
    labels = [variant["label"] for variant in series["variants"]]
    assert labels == ["base", "radius0-1", "radius0-4", "eta0-0.1", "eta0-0.25", "eta0-0.9",
                      "epochs-50", "epochs-130", "epochs-520", "epochs-1040"]
    assert len(labels) == 10
    for variant in series["variants"][1:]:
        assert len(variant["set"]) == 1
        (key, value), = variant["set"].items()
        assert value != base[key]
    assert series["variants"][0]["set"] == {}

    small = som_select.stage2_series(2)
    radius_values = [v["set"]["radius0"] for v in small["variants"] if "radius0" in v["set"]]
    assert radius_values == [2.0]  # max(1, 2/4) = 1 equals the baseline max(1, 2/2) = 1 and is dropped
