"""Tests of the number formatters and the facts loader of the informe (D-11), on synthetic result trees."""

from __future__ import annotations

import json

import pytest

import facts
import informe


def write_results(root, *, robust=False):
    """A results tree with only the keys facts.load_facts reads."""
    files = {
        "som/profiles/pca_contrast.json": {
            "r2_pc1": 0.9613, "p_r2_pc1": 0.000999, "r2_pc2": 0.0552, "p_r2_pc2": 0.2667,
            "n_regions": 1, "n_permutations": 1000,
        },
        "som/series_som_stage1/selection.json": {"outcome": "chosen", "chosen_k": 5},
        "som/series_som_stage2/robustness.json": {"robust": robust, "te_checked": True},
    }
    for relative, payload in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
    return root


def test_dec_uses_decimal_comma():
    assert facts.dec(0.9613, 3) == "0,961"


def test_dec_writes_nan_as_nd():
    assert facts.dec(float("nan"), 2) == "n/d"


def test_pct_is_number_space_percent_sign():
    assert facts.pct(0.973, 1) == "97,3 %"
    assert facts.pct(0.5) == "50 %"


def test_integer_drops_the_decimal_part():
    assert facts.integer(5.0) == "5"
    assert facts.integer(1000) == "1000"


def test_load_facts_returns_display_strings(tmp_path):
    values = facts.load_facts(write_results(tmp_path))
    assert values["som.r2_pc1"] == "0,961"
    assert values["som.p_r2_pc1"] == "0,001"
    assert values["som.r2_pc2"] == "0,055"
    assert values["som.p_r2_pc2"] == "0,267"
    assert values["som.chosen_k"] == "5"
    assert values["som.n_regions"] == "1"
    assert values["som.n_permutations"] == "1000"
    assert values["som.robust"] == "no"


def test_load_facts_robust_true_is_si(tmp_path):
    assert facts.load_facts(write_results(tmp_path, robust=True))["som.robust"] == "sí"


def test_load_facts_missing_file_names_the_make_command(tmp_path):
    write_results(tmp_path)
    (tmp_path / "som" / "profiles" / "pca_contrast.json").unlink()
    with pytest.raises(SystemExit) as stop:
        facts.load_facts(tmp_path)
    assert "make results" in str(stop.value)
    assert "som-profiles" in str(stop.value)


def test_fill_substitutes_known_keys():
    assert facts.fill("R² {som.r2_pc1}", {"som.r2_pc1": "0,961"}) == "R² 0,961"


def test_fill_unknown_key_names_it():
    with pytest.raises(SystemExit) as stop:
        facts.fill("{som.nothing}", {"som.r2_pc1": "0,961"})
    assert "som.nothing" in str(stop.value)


def test_fill_wrap_emits_data_fact_span_and_escapes_the_value():
    out = facts.fill("x {som.r2_pc1} y", {"som.r2_pc1": "<b>"}, wrap=informe.fact_span)
    assert out == 'x <span class="fact" data-fact="som.r2_pc1">&lt;b&gt;</span> y'


def test_dump_prints_sorted_json(tmp_path, capsys):
    write_results(tmp_path)
    assert facts.main(["dump", "--results", str(tmp_path)]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["som.chosen_k"] == "5"
    assert list(printed) == sorted(printed)
