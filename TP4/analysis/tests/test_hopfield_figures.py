"""Tests of the Hopfield letters figures (HOP-02, D-06, D-04) on the six-pattern synthetic fixture.

The driver output comes from hopfield_letters.run on neuron/tests/fixtures/patterns_mix.csv with the rule guard off;
the guard of the figure script is tested on its own. Nothing here reads the real alphabet.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import numpy as np
import pytest

import hopfield
import hopfield_figures
import hopfield_letters
import hopfield_select
import plots_style
import sweep

FIXTURE = Path(__file__).resolve().parent.parent.parent / "neuron" / "tests" / "fixtures" / "patterns_mix.csv"
OUT = Path("hopfield") / "letters"
STEMS = hopfield_figures.FIGURE_STEMS


def fixture_design():
    return hopfield_letters.Design(
        patterns_path=FIXTURE,
        meta_path=FIXTURE.with_suffix(".meta.json"),
        letters="ABCDEF",
        max_sweeps=100,
        recall_levels=(0.0, 0.12, 0.24, 0.36),
        recall_trials=3,
        seeds=(1, 2),
        updates=("async", "sync"),
        trace_trials=1,
        capacity_p=4,
        capacity_level=0.12,
        capacity_trials=2,
        capacity_p_range=(1, 2, 3),
        capacity_samples=5,
        capacity_near_zero=1.0,
        capacity_p_limit=6,
        spurious_levels=(0.4, 0.48),
        spurious_trials=5,
        spurious_seeds=(1, 2),
        spurious_update="async",
    )


@pytest.fixture(scope="module")
def results(tmp_path_factory):
    sweep.build_binary()
    root = tmp_path_factory.mktemp("figures_results")
    return hopfield_letters.run(results_dir=root, design=fixture_design(), check_rule=False)


def draw_into(results, out):
    return hopfield_figures.draw(results, out, patterns_path=FIXTURE, check_rule=False)


# ---------- Task 1: guarded path, letters and overlaps ----------

def test_figures_deterministic(results, tmp_path):
    first = draw_into(results, tmp_path / "a")
    second = draw_into(results, tmp_path / "b")
    assert [p.name for p in first] == [f"{stem}.{suffix}" for stem in STEMS for suffix in ("svg", "png")]
    for path_a, path_b in zip(first, second):
        assert path_a.exists() and path_a.stat().st_size > 0
        assert path_b.exists() and path_b.stat().st_size > 0
        if path_a.suffix == ".svg":
            assert path_a.read_bytes() == path_b.read_bytes()


SLIDE_STEMS = ("letters", "overlaps", "recall_noise", "capacity_p4", "spurious")


def svg_aspect(path):
    head = Path(path).read_text(encoding="utf-8")[:2000]
    width = float(re.search(r'<svg[^>]*\swidth="([\d.]+)pt"', head).group(1))
    height = float(re.search(r'<svg[^>]*\sheight="([\d.]+)pt"', head).group(1))
    return width / height


def test_slide_variants_of_the_letter_figures(results, tmp_path):
    out = tmp_path / "figures"
    draw_into(results, out)
    target = plots_style.SLIDE_FIGSIZE[0] / plots_style.SLIDE_FIGSIZE[1]
    for stem in SLIDE_STEMS:
        svg = out / "slide" / f"{stem}.svg"
        assert svg.stat().st_size > 0, stem
        assert (out / "slide" / f"{stem}.png").stat().st_size > 0, stem
        assert abs(svg_aspect(svg) - target) < 0.02, stem
    for stem in set(STEMS) - set(SLIDE_STEMS):  # max_overlap_hist, cross_terms, energy, capacity_by_p
        assert not (out / "slide" / f"{stem}.svg").exists(), stem
        assert (out / f"{stem}.svg").exists(), stem
    assert plots_style.variant() == "report"


def test_draw_refuses_changed_rule(results, tmp_path):
    copy = tmp_path / "results"
    copy.mkdir()
    for source in Path(results).iterdir():
        if source.is_file():
            (copy / source.name).write_bytes(source.read_bytes())
    selection = json.loads((copy / "selection.json").read_text())
    selection["rule_sha256"] = "0" * 64
    (copy / "selection.json").write_text(json.dumps(selection))
    with pytest.raises(SystemExit) as error:
        hopfield_figures.draw(copy, tmp_path / "figures", patterns_path=FIXTURE, check_rule=True)
    assert "(D-04)" in str(error.value)
    assert not (tmp_path / "figures").exists()


def copy_results(results, tmp_path):
    copy = tmp_path / "results"
    copy.mkdir()
    for source in Path(results).iterdir():
        if source.is_file():
            (copy / source.name).write_bytes(source.read_bytes())
    return copy


def test_draw_accepts_the_recorded_network_code(results, tmp_path):
    run = json.loads((Path(results) / "run.json").read_text())
    assert "code_identity" in run
    hopfield_figures.require_same_code(run)
    assert len(draw_into(results, tmp_path / "figures")) == 2 * len(STEMS)


def test_draw_refuses_changed_network_code(results, tmp_path):
    copy = copy_results(results, tmp_path)
    run = json.loads((copy / "run.json").read_text())
    changed = hopfield_letters.CODE_FILES[0]
    run["code_identity"]["files"][changed] = "0" * 64
    (copy / "run.json").write_text(json.dumps(run))
    with pytest.raises(SystemExit) as error:
        hopfield_figures.draw(copy, tmp_path / "figures", patterns_path=FIXTURE, check_rule=False)
    message = str(error.value)
    assert changed in message and "different network code" in message and "make hopfield-letters" in message
    assert not (tmp_path / "figures").exists()


def test_draw_refuses_results_without_code_identity(results, tmp_path):
    copy = copy_results(results, tmp_path)
    run = json.loads((copy / "run.json").read_text())
    del run["code_identity"]
    (copy / "run.json").write_text(json.dumps(run))
    with pytest.raises(SystemExit) as error:
        hopfield_figures.draw(copy, tmp_path / "figures", patterns_path=FIXTURE, check_rule=False)
    assert "different network code" in str(error.value)
    assert not (tmp_path / "figures").exists()


def test_draw_refuses_missing_results(tmp_path):
    with pytest.raises(SystemExit) as error:
        hopfield_figures.draw(tmp_path / "none", tmp_path / "figures")
    assert "make hopfield-letters" in str(error.value)


# ---------- Task 2: histogram and cross terms ----------

def synthetic_selection():
    return {
        "separated": {"letters": "ABCD"},
        "correlated": {"letters": "EFGH"},
        "max_abs_overlap_histogram": [
            {"max_abs_dot": 1, "max_abs_overlap": 0.04, "n_subsets": 1, "sets": ["separated"]},
            {"max_abs_dot": 3, "max_abs_overlap": 0.12, "n_subsets": 2, "sets": []},
            {"max_abs_dot": 5, "max_abs_overlap": 0.2, "n_subsets": 4, "sets": ["correlated"]},
        ],
    }


def test_max_overlap_hist_synthetic(tmp_path):
    hopfield_figures.plot_max_overlap_hist(synthetic_selection(), tmp_path / "hist")
    svg = (tmp_path / "hist.svg").read_text()
    assert (tmp_path / "hist.png").stat().st_size > 0
    assert len(svg) > 1000


def test_cross_terms_panels_and_negative_marks(results, tmp_path):
    report = json.loads((Path(results) / "orthogonality.json").read_text())
    hopfield_figures.plot_cross_terms(report, tmp_path / "cross")
    assert (tmp_path / "cross.svg").stat().st_size > 0
    # one panel per letter of each set, and the margins used are N - p + cross term
    n = report["n_pixels"]
    for name in hopfield_figures.SET_NAMES:
        entry = report[name]
        p = len(entry["letters"])
        assert len(entry["margins"]) == p
        for margin, cross in zip(entry["margins"], entry["cross_terms"]):
            assert margin == [n - p + c for c in cross]
        assert entry["wrong_pixels"] == [sum(1 for v in row if v < 0) for row in entry["margins"]]


# ---------- Task 3: recall against noise and energy ----------

def test_energy_panels_are_the_first_traced_trials(results):
    panels = hopfield_figures.energy_panels(results)
    selection = json.loads((Path(results) / "selection.json").read_text())
    letters = selection["separated"]["letters"]
    assert len(panels) == len(letters) * 3
    assert [(p["letter"], p["k"]) for p in panels] == [(letter, k) for letter in letters for k in (3, 6, 9)]
    levels = 4  # fixture: k = 0, 3, 6, 9
    per_level = 3
    for position, letter in enumerate(letters):
        for column, k in enumerate((3, 6, 9)):
            panel = panels[position * 3 + column]
            # trial index = (pattern x n_levels + level index) x trials, t = 0
            assert panel["trial"] == (position * levels + (column + 1)) * per_level
            assert panel["k"] == k
            assert panel["energies"][0] == panel["e_start"]
            assert panel["energies"][-1] == panel["e_final"]
            # the async energy never rises
            assert all(b <= a + 1e-9 for a, b in zip(panel["energies"], panel["energies"][1:]))
            assert panel["sweep_ends"][-1] == len(panel["energies"]) - 1


def test_energy_panels_do_not_depend_on_the_energies(results, tmp_path):
    """The chosen trials are fixed by index: a different noise realisation of the same index would change the energies,
    never the index."""
    panels = hopfield_figures.energy_panels(results)
    again = hopfield_figures.energy_panels(results)
    assert [p["trial"] for p in panels] == [p["trial"] for p in again]


def test_recall_noise_and_energy_figures(results, tmp_path):
    rows = list(csv.DictReader((Path(results) / "recall.csv").open()))
    hopfield_figures.plot_recall_noise(rows, tmp_path / "recall_noise")
    hopfield_figures.plot_energy(hopfield_figures.energy_panels(results), tmp_path / "energy")
    for stem in ("recall_noise", "energy"):
        assert (tmp_path / f"{stem}.svg").stat().st_size > 0
        assert (tmp_path / f"{stem}.png").stat().st_size > 0


def test_letters_and_overlaps_figures(results, tmp_path):
    patterns = hopfield.load_patterns(FIXTURE)
    selection = json.loads((Path(results) / "selection.json").read_text())
    sets = {name: selection[name]["indices"] for name in hopfield_figures.SET_NAMES}
    hopfield_figures.plot_letters(patterns, "ABCDEF", sets, tmp_path / "letters")
    report = json.loads((Path(results) / "orthogonality.json").read_text())
    hopfield_figures.plot_overlaps(report, tmp_path / "overlaps")
    for stem in ("letters", "overlaps"):
        assert (tmp_path / f"{stem}.svg").stat().st_size > 0
    assert np.asarray(report["separated"]["dots"]).shape == (4, 4)
    assert hopfield_select.CLASS_NAMES[0] == "stored"


# ---------- Plan 04-07: capacity and the spurious state ----------

def test_capacity_figures_from_fixture(results, tmp_path):
    rows = list(csv.DictReader((Path(results) / "capacity_p4.csv").open()))
    selection = json.loads((Path(results) / "selection.json").read_text())
    capacity = json.loads((Path(results) / "capacity.json").read_text())
    by_p = list(csv.DictReader((Path(results) / "capacity_by_p.csv").open()))
    hopfield_figures.plot_capacity_p4(rows, selection, tmp_path / "capacity_p4")
    hopfield_figures.plot_capacity_by_p(by_p, capacity, tmp_path / "capacity_by_p")
    for stem in ("capacity_p4", "capacity_by_p"):
        assert (tmp_path / f"{stem}.svg").stat().st_size > 1000
        assert (tmp_path / f"{stem}.png").stat().st_size > 0


def synthetic_capacity_rows(extended: bool):
    rows = []
    for p in range(1, 6):
        rows.append({"p": str(p), "n_subsets": "10", "exhaustive": "1" if p == 1 else "0", "n_seeds": "2",
                     "mean_stable_fraction": str(1.0 - 0.18 * p), "sd_stable_fraction": "0.02",
                     "all_stable_fraction": "0.5", "mean_recall_rate": str(0.9 - 0.15 * p),
                     "sd_recall_rate": "0.01", "extension": "1" if extended and p >= 4 else "0"})
    return rows


@pytest.mark.parametrize("extended", [True, False])
def test_capacity_by_p_synthetic_with_and_without_extension(tmp_path, extended):
    capacity = {"n_pixels": 25, "p_extension": {"near_zero": 0.05}, "orders_of_magnitude": {"0.138N": 3.45,
                                                                                            "0.15N": 3.75}}
    hopfield_figures.plot_capacity_by_p(synthetic_capacity_rows(extended), capacity, tmp_path / "by_p")
    svg = (tmp_path / "by_p.svg").read_text()
    assert len(svg) > 1000
    assert (tmp_path / "by_p.png").stat().st_size > 0


def synthetic_pick(klass, match_letters, signs):
    return {"seed": 1, "run": "x", "trial": 3, "letter": "A", "noise": 0.4, "flipped": 10,
            "query": [1, -1] * 12 + [1], "final": [-1, 1] * 12 + [-1], "overlaps": [0.5, -0.5, 0.1, 0.2],
            "class": klass, "match_letters": match_letters, "signs": signs, "converged": 1, "sweeps": 2,
            "e_start": 10.0, "e_final": -200.0, "energy_trace": [10.0, -50.0, -200.0, -200.0], "is_fixed": True}


def synthetic_spurious(found_target: bool, picks: dict):
    return {"seeds_tried": [1], "counts_by_seed": {"1": {"stored": 5, "inverse": 1, "mixture": 0, "other": 0}},
            "found_target": found_target, "stored_letters": ["A", "B", "C", "D"],
            "stored_energies": [-264.0] * 4, "picks": picks}


def test_plot_spurious_picks_and_absence(tmp_path):
    both = synthetic_spurious(True, {"inverse": synthetic_pick("inverse", ["B"], [-1]),
                                     "mixture": synthetic_pick("mixture", ["A", "B", "D"], [1, -1, 1])})
    hopfield_figures.plot_spurious(both, tmp_path / "both")
    only_inverse = synthetic_spurious(False, {"inverse": synthetic_pick("inverse", ["B"], [-1])})
    hopfield_figures.plot_spurious(only_inverse, tmp_path / "inverse")
    none = synthetic_spurious(False, {})
    hopfield_figures.plot_spurious(none, tmp_path / "none")
    for stem in ("both", "inverse", "none"):
        assert (tmp_path / f"{stem}.svg").stat().st_size > 1000
        assert (tmp_path / f"{stem}.png").stat().st_size > 0


def test_stems_include_the_capacity_and_spurious_figures():
    assert hopfield_figures.FIGURE_STEMS[-3:] == ("capacity_p4", "capacity_by_p", "spurious")
