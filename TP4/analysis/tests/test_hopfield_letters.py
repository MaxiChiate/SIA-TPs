"""Tests of the guarded Hopfield letters driver (HOP-02, HOP-03, D-04) on the six-pattern synthetic fixture.

The whole driver runs on neuron/tests/fixtures/patterns_mix.csv through an injected design with the rule guard off;
the guard is tested on its own. Nothing here reads datos/letters/ or the prepared alphabet.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path

import numpy as np
import pytest

import hopfield
import hopfield_letters
import hopfield_select
import sweep

FIXTURE = Path(__file__).resolve().parent.parent.parent / "neuron" / "tests" / "fixtures" / "patterns_mix.csv"
OUT = Path("hopfield") / "letters"


def fixture_design(**changes):
    values = dict(
        patterns_path=FIXTURE,
        meta_path=FIXTURE.with_suffix(".meta.json"),
        letters="ABCDEF",
        max_sweeps=100,
        recall_levels=(0.0, 0.24),
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
        spurious_seeds=(1, 2, 3),
        spurious_update="async",
    )
    values.update(changes)
    return hopfield_letters.Design(**values)


def read_csv(path):
    with Path(path).open(newline="") as file:
        return list(csv.DictReader(file))


def run_fixture(tmp_path, **changes):
    return hopfield_letters.run(results_dir=tmp_path, design=fixture_design(**changes), check_rule=False)


@pytest.fixture(scope="module", autouse=True)
def binary():
    sweep.build_binary()


@pytest.fixture(scope="module")
def patterns():
    return hopfield.load_patterns(FIXTURE)


@pytest.fixture(scope="module")
def full_run(tmp_path_factory):
    root = tmp_path_factory.mktemp("letters_full")
    return run_fixture(root)


# ---------- Task 1: guarded end-to-end path ----------

def test_driver_fixture_separated_async(full_run, patterns):
    assert full_run.name == "letters"
    selection = json.loads((full_run / "selection.json").read_text())
    chosen = hopfield_select.select_sets(patterns)
    assert selection["separated"]["indices"] == list(chosen["separated"])
    assert selection["correlated"]["indices"] == list(chosen["correlated"])
    assert selection["rule_commit"] is None

    rows = [r for r in read_csv(full_run / "recall.csv") if r["set"] == "separated" and r["update"] == "async"]
    assert [float(r["noise"]) for r in rows] == [0.0, 0.24]
    assert rows[0]["n_trials"] == str(4 * 3 * 2)
    assert float(rows[0]["recall_rate"]) == 1.0


def test_driver_refuses_without_rule_commit(tmp_path):
    empty = tmp_path / "norepo"
    empty.mkdir()
    with pytest.raises(SystemExit) as error:
        hopfield_letters.run(results_dir=tmp_path / "res", design=fixture_design(), repo_dir=empty, check_rule=True)
    assert str(error.value).endswith("(D-04)")
    assert not (tmp_path / "res" / OUT).exists()


def test_driver_refuses_stale_prepared_csv(tmp_path, monkeypatch):
    identity = {"rule_commit": "a" * 40, "rule_sha256": "1" * 64, "select_sha256": "2" * 64,
                "alphabet_sha256": "0" * 64, "letters_sha256": "3" * 64}
    monkeypatch.setattr(hopfield_select, "rule_identity", lambda repo_dir=None: identity)
    meta = tmp_path / "alphabet_pm1.meta.json"
    meta.write_text(json.dumps({"source_sha256": "f" * 64}))
    with pytest.raises(SystemExit) as error:
        hopfield_letters.run(results_dir=tmp_path / "res", design=fixture_design(meta_path=meta),
                             repo_dir=tmp_path, check_rule=True)
    assert "make letters" in str(error.value)
    assert not (tmp_path / "res" / OUT).exists()


# ---------- Task 2: both sets, both modes, orthogonality, capacity ----------

def test_recall_covers_both_sets_and_modes(full_run):
    rows = read_csv(full_run / "recall.csv")
    assert len(rows) == 2 * 2 * 2
    assert [(r["set"], r["update"]) for r in rows[::2]] == [("separated", "async"), ("separated", "sync"),
                                                            ("correlated", "async"), ("correlated", "sync")]
    by_pattern = read_csv(full_run / "recall_by_pattern.csv")
    assert len(by_pattern) == 2 * 2 * 4 * 2
    # With no noise the async query is the stored letter: recalled exactly when the letter is a fixed point
    report = json.loads((full_run / "orthogonality.json").read_text())
    for row in rows:
        if row["update"] == "async" and float(row["noise"]) == 0.0:
            assert float(row["recall_rate"]) == sum(report[row["set"]]["fixed"]) / 4
    first = rows[0]
    assert first["set"] == "separated" and float(first["recall_rate"]) == 1.0


def test_orthogonality_report(full_run, patterns):
    report = json.loads((full_run / "orthogonality.json").read_text())
    n = patterns.shape[1]
    chosen = hopfield_select.select_sets(patterns)
    for name in ("separated", "correlated"):
        entry = report[name]
        P = patterns[list(chosen[name])]
        p = P.shape[0]
        assert np.array_equal(np.array(entry["dots"]), P @ P.T)
        assert np.allclose(np.array(entry["overlaps"]), (P @ P.T) / n)
        margins = np.array(entry["margins"])
        assert np.array_equal(margins, n - p + np.array(entry["cross_terms"]))
        assert entry["fixed"] == [bool(row.min() >= 0) for row in margins]
        assert entry["min_margin"] == [int(row.min()) for row in margins]
        assert entry["wrong_pixels"] == [int((row < 0).sum()) for row in margins]


def test_capacity_p4_on_fixture(full_run):
    rows = read_csv(full_run / "capacity_p4.csv")
    assert [int(r["n_stable"]) for r in rows] == [4, 2, 4, 3, 4, 2, 4, 4, 3, 4, 4, 4, 4, 4, 4]
    assert [int(r["min_margin"]) for r in rows] == [2, -2, 4, -2, 6, -6, 4, 10, -2, 2, 6, 10, 6, 10, 10]
    assert all(0.0 <= float(r["recall_rate_mean"]) <= 1.0 for r in rows)
    assert list(rows[0]) == ["subset", "idx_0", "idx_1", "idx_2", "idx_3", "letters", "max_abs_overlap",
                             "mean_abs_overlap", "n_stable", "stable_fraction", "min_margin", "recall_rate_mean",
                             "recall_rate_sd"]
    assert rows[0]["letters"] == "ABCD"


def test_capacity_by_p_on_fixture(full_run, patterns):
    rows = read_csv(full_run / "capacity_by_p.csv")
    assert [int(r["p"]) for r in rows] == [1, 2, 3]
    assert [int(r["n_subsets"]) for r in rows] == [5, 5, 5]
    assert [r["exhaustive"] for r in rows] == ["0", "0", "0"]
    assert [r["extension"] for r in rows] == ["0", "0", "0"]
    assert all(r["n_seeds"] == "2" for r in rows)
    capacity = json.loads((full_run / "capacity.json").read_text())
    assert capacity["p_extension"]["extended"] is False and capacity["p_extension"]["p_last"] == 3
    n = patterns.shape[1]
    assert capacity["orders_of_magnitude"] == {"0.138N": 0.138 * n, "0.15N": 0.15 * n}
    assert capacity["n_pixels"] == n
    assert sum(capacity["p4_n_stable_counts"].values()) == 15


def test_capacity_exhaustive_when_every_subset_fits(tmp_path):
    out = run_fixture(tmp_path, capacity_samples=6)
    first = read_csv(out / "capacity_by_p.csv")[0]
    assert first["p"] == "1" and first["n_subsets"] == "6" and first["exhaustive"] == "1"


def test_capacity_extension_follows_rule(tmp_path):
    out = run_fixture(tmp_path, capacity_near_zero=0.0, capacity_p_limit=5)
    rows = read_csv(out / "capacity_by_p.csv")
    assert [int(r["p"]) for r in rows] == [1, 2, 3, 4, 5]
    assert [int(r["extension"]) for r in rows] == [0, 0, 0, 1, 1]
    assert (out / "sweeps" / "capacity_by_p_p4").is_dir() and (out / "sweeps" / "capacity_by_p_p5").is_dir()
    fractions = [float(r["mean_stable_fraction"]) for r in rows]
    for index in (2, 3):
        assert hopfield_select.capacity_needs_next_p(int(rows[index]["p"]), fractions[index], 0.0, 5)
    assert not hopfield_select.capacity_needs_next_p(5, fractions[4], 0.0, 5)
    extension = json.loads((out / "capacity.json").read_text())["p_extension"]
    assert extension["extended"] is True and extension["p_last"] == 5


# ---------- Task 3: spurious search, run.json, determinism ----------

def trial_rows(run_dir):
    return read_csv(Path(run_dir) / "trials.csv")


def test_spurious_search_follows_pre_registration(full_run):
    spurious = json.loads((full_run / "spurious.json").read_text())
    seeds = spurious["seeds_tried"]
    assert seeds == [1, 2, 3][:len(seeds)] and seeds[0] == 1
    merged = {}
    for position, seed in enumerate(seeds):
        run_dir = next((full_run / "sweeps" / f"spurious_seed{seed}" / "runs").iterdir())
        rows = trial_rows(run_dir)
        needs_next = hopfield_select.spurious_needs_next_seed(rows)
        assert set(spurious["counts_by_seed"][str(seed)]) == {"stored", "inverse", "mixture", "other"}
        for code, row in hopfield_select.pick_spurious(rows).items():
            merged.setdefault(hopfield_select.CLASS_NAMES[code], (seed, row))
        if position < len(seeds) - 1:
            assert needs_next  # a seed without a mixture or another state is followed by the next one
        else:
            assert not needs_next or seed == 3  # the search stops at the first seed with one, or after the last
    assert set(spurious["picks"]) == set(merged)
    assert spurious["found_target"] == any(name in merged for name in ("mixture", "other"))
    for name, pick in spurious["picks"].items():
        seed, row = merged[name]
        assert pick["seed"] == seed and pick["trial"] == int(row["trial"])
        assert len(pick["query"]) == 25 and len(pick["final"]) == 25
        assert pick["class"] == name
        assert pick["is_fixed"] is True
        assert pick["energy_trace"][0] == pick["e_start"] and pick["energy_trace"][-1] == pick["e_final"]
        assert len(pick["overlaps"]) == 4
        assert not Path(pick["run"]).is_absolute()
    assert len(spurious["stored_energies"]) == 4


def test_spurious_finding_without_target(tmp_path):
    out = run_fixture(tmp_path, spurious_levels=(0.0,))
    spurious = json.loads((out / "spurious.json").read_text())
    assert spurious["found_target"] is False
    assert spurious["picks"] == {}
    assert spurious["seeds_tried"] == [1, 2, 3]


def test_run_json_records_identity_and_totals(full_run):
    run = json.loads((full_run / "run.json").read_text())
    assert run["rule_commit"] is None and run["spurious_seeds_tried"][0] == 1
    assert run["cross_checked_trials"] > 0 and run["cross_checked_capacity_rows"] > 0
    assert "recall" in run["sweeps"] and not Path(run["design"]["patterns_path"]).is_absolute()


def test_run_json_records_code_identity(full_run):
    identity = json.loads((full_run / "run.json").read_text())["code_identity"]
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=hopfield_letters.TP_DIR, capture_output=True,
                          text=True).stdout.strip()
    assert identity["head"] == head
    assert isinstance(identity["dirty"], bool)
    assert list(identity["files"]) == list(hopfield_letters.CODE_FILES)
    for name, digest in identity["files"].items():
        assert digest == hashlib.sha256((hopfield_letters.TP_DIR / name).read_bytes()).hexdigest(), name
    assert identity["binary_sha256"] == hashlib.sha256(sweep.BINARY.read_bytes()).hexdigest()
    assert hopfield_letters.changed_code_files(identity) == []


def git_in(repo, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=repo, check=True,
                   capture_output=True)


def test_code_identity_dirty_flag_and_changed_files(tmp_path):
    repo = tmp_path / "repo"
    for name in hopfield_letters.CODE_FILES:
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text(f"// {name}\n")
    binary = tmp_path / "neuron"
    binary.write_bytes(b"binary")
    git_in(repo, "init", "-q")
    git_in(repo, "add", ".")
    git_in(repo, "commit", "-q", "-m", "code")
    clean = hopfield_letters.code_identity(repo, binary)
    assert clean["dirty"] is False and len(clean["head"]) == 40
    assert clean["binary_sha256"] == hashlib.sha256(b"binary").hexdigest()
    assert hopfield_letters.changed_code_files(clean, repo) == []

    edited = hopfield_letters.CODE_FILES[0]
    (repo / edited).write_text("// changed\n")
    assert hopfield_letters.code_identity(repo, binary)["dirty"] is True
    assert hopfield_letters.changed_code_files(clean, repo) == [edited]
    git_in(repo, "checkout", "--", edited)
    assert hopfield_letters.code_identity(repo, binary)["dirty"] is False

    (repo / "neuron" / "models" / "hopfield_core.c").unlink()
    with pytest.raises(SystemExit):
        hopfield_letters.code_identity(repo, binary)


def test_code_identity_outside_a_repository(tmp_path):
    for name in hopfield_letters.CODE_FILES:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("x")
    binary = tmp_path / "neuron.bin"
    binary.write_bytes(b"b")
    identity = hopfield_letters.code_identity(tmp_path, binary)
    assert identity["head"] is None and identity["dirty"] is None
    assert set(identity["files"]) == set(hopfield_letters.CODE_FILES)
    assert hopfield_letters.changed_code_files({}, tmp_path) == list(hopfield_letters.CODE_FILES)


def test_driver_is_deterministic(tmp_path):
    first = run_fixture(tmp_path / "a")
    second = run_fixture(tmp_path / "b")
    names = ["selection.json", "orthogonality.json", "recall.csv", "recall_by_pattern.csv", "capacity_p4.csv",
             "capacity_by_p.csv", "capacity.json", "spurious.json", "run.json"]
    for name in names:
        assert (first / name).read_bytes() == (second / name).read_bytes(), name

    def tree(root):
        return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(root.rglob("*")) if p.is_file()}
    assert tree(first) == tree(second)
