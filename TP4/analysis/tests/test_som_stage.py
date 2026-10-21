"""Tests of the guarded stage driver (SOM-03, D-10): run_stage on the 6-row fixture, the failure stop, the
stage-2 writer, the refusal when the rule changed and the guard over analysis/som_select.py."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest

import som_select
import som_stage

HEX40 = re.compile(r"[0-9a-f]{40}")
IDENTITY_KEYS = ("rule_commit", "rule_sha256", "select_commit", "select_sha256")
RULE_TEXT = "# Regla\n<!-- regla:inicio -->\nlas reglas\n<!-- regla:fin -->\n"


def write_series(tmp_path, name, variants, seeds=(1, 2)):
    """A series on the 6-row fixture: 5 epochs, eta 0.5 -> 0.01, radius_final 1."""
    base = {"model": "kohonen", "seed": 1, "input": "tests/fixtures/zscore_small.csv", "grid_k": 3,
            "neighborhood": "step", "radius0": 1.5, "radius_final": 1.0, "eta0": 0.5, "eta_final": 0.01,
            "epochs": 5}
    (tmp_path / "base.json").write_text(json.dumps(base))
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps({"base_config": "base.json", "seeds": list(seeds), "variants": variants}))
    return path


def stage1_variants():
    return [
        {"label": "k2-step", "set": {"grid_k": 2, "neighborhood": "step", "radius0": 1.0}},
        {"label": "k3-step", "set": {"grid_k": 3, "neighborhood": "step", "radius0": 1.5}},
        {"label": "k2-gaussian", "set": {"grid_k": 2, "neighborhood": "gaussian", "radius0": 1.0}},
    ]


def read_csv(path):
    with Path(path).open(newline="") as file:
        return list(csv.DictReader(file))


def git(repo, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
                           *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


def make_repo(path, first, second=None):
    """A fresh repo; `first` is committed together, `second` (if any) in a later commit. Returns the hashes."""
    path.mkdir(parents=True)
    git(path, "init", "-q")
    hashes = []
    for group in (first, second):
        if group is None:
            continue
        for rel, text in group.items():
            (path / rel).parent.mkdir(parents=True, exist_ok=True)
            (path / rel).write_text(text)
            git(path, "add", rel)
        git(path, "commit", "-q", "-m", "c")
        hashes.append(git(path, "rev-parse", "HEAD"))
    return hashes


def test_run_stage_fixture(tmp_path):
    series = write_series(tmp_path, "series_som_stage1", stage1_variants())
    root = tmp_path / "res"
    out = som_stage.run_stage(series, results_root=root, select=True, check_rule=False, workers=2)
    assert out == root / "som" / "series_som_stage1"

    aggregate = read_csv(out / "aggregate.csv")
    assert [row["label"] for row in aggregate] == ["k2-step", "k3-step", "k2-gaussian"]
    assert "medoid_seed" in aggregate[0] and aggregate[0]["medoid_seed"] in ("1", "2")
    assert len(read_csv(out / "loo.csv")) == 3 * 2 * 6
    assert len(read_csv(out / "loo_by_seed.csv")) == 6
    stability = read_csv(out / "stability.csv")
    assert list(stability[0]) == ["label", "seed_a", "seed_b", "spearman"] and len(stability) == 3
    assert {row["label"] for row in stability} == {"k2-step", "k3-step", "k2-gaussian"}

    selection = json.loads((out / "selection.json").read_text())
    for key in ("outcome", "chosen_k", "decided_by", "te_filter_dropped", "qe_train_argmin_k", "figure_seed",
                "figure_run", "sweep_dir", *IDENTITY_KEYS):
        assert key in selection, key
    assert all(selection[key] is None for key in IDENTITY_KEYS)
    assert selection["outcome"] in ("chosen", "no_eligible_grid")
    if selection["chosen_k"] is not None:
        run_dir = som_stage.TP_DIR / selection["figure_run"]
        assert run_dir.is_dir() and (run_dir / "assignments.csv").is_file()
        assert f"k{selection['chosen_k']}-step" in run_dir.name
        assert selection["figure_seed"] in (1, 2) and f"seed{selection['figure_seed']}" in run_dir.name
    else:
        assert selection["figure_seed"] is None and selection["figure_run"] is None
    assert (som_stage.TP_DIR / selection["sweep_dir"] / "summary.csv").is_file()
    stage = json.loads((out / "stage.json").read_text())
    assert stage["n_runs"] == 6 and stage["n_loo_trainings"] == 36

    # stage 2: the same driver without --select, reading the chosen k from the stage-1 selection
    selection.update({"outcome": "chosen", "chosen_k": 2, "te_filter_dropped": True})
    (out / "selection.json").write_text(json.dumps(selection))
    stage2 = write_series(tmp_path, "series_som_stage2", [
        {"label": "base", "set": {"grid_k": 2, "radius0": 1.0}},
        {"label": "epochs-10", "set": {"grid_k": 2, "radius0": 1.0, "epochs": 10}},
    ])
    out2 = som_stage.run_stage(stage2, results_root=root, select=False, check_rule=False, workers=2)
    assert not (out2 / "selection.json").exists()
    robustness = read_csv(out2 / "robustness.csv")
    assert [row["label"] for row in robustness] == ["base", "epochs-10"]
    for row in robustness:
        assert row["passes"] == str(row["passes_empty"] == "True" and row["passes_creators"] == "True")
    verdict = json.loads((out2 / "robustness.json").read_text())
    assert verdict["te_checked"] is False
    assert verdict["robust"] == (verdict["failing_variants"] == [])
    assert verdict["failing_variants"] == [row["label"] for row in robustness if row["passes"] != "True"]


def test_run_stage_failure_stops(tmp_path):
    variants = stage1_variants() + [{"label": "bad", "set": {"neighborhood": "hex"}}]
    series = write_series(tmp_path, "series_som_stage1", variants)
    root = tmp_path / "res"
    with pytest.raises(SystemExit) as caught:
        som_stage.run_stage(series, results_root=root, select=True, check_rule=False, workers=2)
    assert "failed" in str(caught.value)
    assert not list(root.rglob("aggregate.csv")) and not list(root.rglob("selection.json"))


def test_write_stage2(tmp_path):
    chosen = tmp_path / "selection.json"
    chosen.write_text(json.dumps({"outcome": "chosen", "chosen_k": 4}))
    out = som_stage.write_stage2(chosen, tmp_path / "series_som_stage2.json")
    assert json.loads(Path(out).read_text()) == som_select.stage2_series(4)
    assert Path(out).read_text().endswith("}\n")

    none = tmp_path / "none.json"
    none.write_text(json.dumps({"outcome": "no_eligible_grid", "chosen_k": None}))
    with pytest.raises(SystemExit):
        som_stage.write_stage2(none, tmp_path / "other.json")
    assert not (tmp_path / "other.json").exists()


def test_require_same_rule(tmp_path):
    rule = tmp_path / "rule.md"
    rule.write_text(RULE_TEXT)
    select = tmp_path / "select.py"
    select.write_text("TE_MAX = 0.05\n")
    rule_sha = som_select.rule_digest(rule)
    select_sha = hashlib.sha256(select.read_bytes()).hexdigest()
    selection = tmp_path / "selection.json"

    selection.write_text(json.dumps({"rule_sha256": "a" * 64, "select_sha256": select_sha}))
    with pytest.raises(SystemExit) as caught:
        som_stage.require_same_rule(selection, rule, select)
    assert "a" * 64 in str(caught.value) and rule_sha in str(caught.value)

    selection.write_text(json.dumps({"rule_sha256": rule_sha, "select_sha256": "b" * 64}))
    with pytest.raises(SystemExit) as caught:
        som_stage.require_same_rule(selection, rule, select)
    assert "b" * 64 in str(caught.value) and select_sha in str(caught.value)

    selection.write_text(json.dumps({"rule_sha256": rule_sha, "select_sha256": select_sha}))
    som_stage.require_same_rule(selection, rule, select)

    with pytest.raises(SystemExit):
        som_stage.require_same_rule(tmp_path / "missing.json", rule, select)


def test_rule_identity_guards_code(tmp_path):
    repo = tmp_path / "repo"
    select_text = "TE_MAX = 0.05\n"
    (c1,) = make_repo(repo, {som_select.RULE_FILE: RULE_TEXT, som_select.SELECT_FILE: select_text,
                             som_select.STAGE1_SERIES: "{}\n"})
    assert HEX40.fullmatch(c1)
    ident = som_stage.rule_identity(som_select.STAGE1_SERIES, repo_dir=repo)
    assert ident["rule_commit"] == c1 and ident["select_commit"] == c1
    assert ident["rule_sha256"] == som_select.rule_digest(repo / som_select.RULE_FILE)
    assert ident["select_sha256"] == hashlib.sha256((repo / som_select.SELECT_FILE).read_bytes()).hexdigest()

    # a later commit (section 3 after the end marker, the stage-2 series) never moves the rule commit
    with (repo / som_select.RULE_FILE).open("a") as file:
        file.write("## 3. Etapa 1\n")
    (repo / som_select.STAGE2_SERIES).write_text("{}\n")
    git(repo, "add", som_select.RULE_FILE, som_select.STAGE2_SERIES)
    git(repo, "commit", "-q", "-m", "c2")
    c2 = git(repo, "rev-parse", "HEAD")
    assert c2 != c1
    for series in (som_select.STAGE1_SERIES, som_select.STAGE2_SERIES):
        later = som_stage.rule_identity(series, repo_dir=repo)
        assert later["rule_commit"] == c1 and later["select_commit"] == c1
        assert later["rule_sha256"] == ident["rule_sha256"] and later["select_sha256"] == ident["select_sha256"]

    # an uncommitted change to the executable rule stops the stage
    (repo / som_select.SELECT_FILE).write_text(select_text.replace("0.05", "0.06"))
    with pytest.raises(SystemExit) as caught:
        som_stage.rule_identity(som_select.STAGE1_SERIES, repo_dir=repo)
    assert som_select.SELECT_FILE in str(caught.value)
    git(repo, "checkout", "--", som_select.SELECT_FILE)

    # untracked (removed from the index, file left in place) stops it too
    git(repo, "rm", "-q", "--cached", som_select.SELECT_FILE)
    git(repo, "commit", "-q", "-m", "c3")
    assert (repo / som_select.SELECT_FILE).is_file()
    with pytest.raises(SystemExit) as caught:
        som_stage.rule_identity(som_select.STAGE1_SERIES, repo_dir=repo)
    assert som_select.SELECT_FILE in str(caught.value)

    # the rule text and its code share their adding commit: a split add is refused, naming both commits
    split = tmp_path / "split"
    a, b = make_repo(split, {som_select.RULE_FILE: RULE_TEXT, som_select.STAGE1_SERIES: "{}\n"},
                     {som_select.SELECT_FILE: select_text})
    with pytest.raises(SystemExit) as caught:
        som_stage.rule_identity(som_select.STAGE1_SERIES, repo_dir=split)
    message = str(caught.value)
    assert som_select.SELECT_FILE in message and a in message and b in message
