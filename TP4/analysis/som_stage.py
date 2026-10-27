#!/usr/bin/env python3
"""Guarded driver of the two Kohonen stages (SOM-03, D-06, D-10): sweep, leave-one-out, stability, aggregate.

    .venv/bin/python analysis/som_stage.py run analysis/series_som_stage1.json --select
    .venv/bin/python analysis/som_stage.py write-stage2
    .venv/bin/python analysis/som_stage.py run analysis/series_som_stage2.json

`run` refuses to start unless the pre-registered rule is committed and unchanged: deliverables/02-kohonen.md,
analysis/som_select.py (the rule as code) and analysis/series_som_stage1.json must be tracked and clean, and
must have been added in one single commit (the rule commit). The stage then runs the sweep of the series, the
QE leave-one-out of the same series and the seed stability of every variant, and writes under
analysis/results/som/<series name>/: aggregate.csv, loo.csv, loo_by_seed.csv, stability.csv, stage.json and,
with --select, selection.json (the outcome of som_select.select_grid with the identity of the rule that
produced it) or, without it, robustness.csv and robustness.json (stage 2: does the chosen k keep passing
the filters). Any failed run or training stops the stage before aggregate.csv exists. `write-stage2` derives
analysis/series_som_stage2.json from the chosen k and the committed ladders. numpy and the standard library
only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

TP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TP_DIR / "scripts"))
sys.path.insert(0, str(TP_DIR / "analysis"))

import som  # noqa: E402
import som_loo  # noqa: E402
import som_select  # noqa: E402
import sweep  # noqa: E402

RESULTS_DIR = TP_DIR / "analysis" / "results"
STAGE1_NAME = Path(som_select.STAGE1_SERIES).stem
HEX40 = re.compile(r"[0-9a-f]{40}")
IDENTITY_KEYS = ("rule_commit", "rule_sha256", "select_commit", "select_sha256")
STABILITY_COLUMNS = ["label", "seed_a", "seed_b", "spearman"]
ROBUSTNESS_COLUMNS = ["label", "radius0", "eta0", "epochs", "te_mean", "empty_fraction_mean",
                      "creators_per_occupied_mean", "passes_te", "passes_empty", "passes_creators", "passes",
                      "qe_loo_mean", "qe_loo_sd", "stability"]


# ---------- the rule that was committed before looking (D-10) ----------

def _git_stdout(args: list[str], repo_dir: Path) -> str:
    """Argument list, no shell, run in repo_dir (T-02-09)."""
    return subprocess.run(["git", *args], cwd=repo_dir, capture_output=True, text=True,
                          check=True).stdout.strip()


def _added_commit(path: str, repo_dir: Path) -> str:
    """The one commit that added `path` (git log --diff-filter=A). Never added, or added more than once, is
    refused: the rule commit must be unambiguous."""
    out = _git_stdout(["log", "--diff-filter=A", "--format=%H", "--", path], repo_dir)
    if not HEX40.fullmatch(out):
        raise SystemExit(f"{path}: expected exactly one commit that added it, git reports {out!r} (D-10)")
    return out


def rule_identity(series_path, repo_dir=TP_DIR) -> dict:
    """Refuse unless the rule text, analysis/som_select.py and the series are tracked and clean and the rule
    text, its code and the stage-1 series were added in one commit; return the identity to record.

    rule_commit is the commit that added the rule text, which no later commit changes: section 3 and the
    stage-2 series are committed afterwards, and rule_guard's own return value (the last commit touching any
    of the paths) moves with them, so it is used only as the clean-and-tracked check and never recorded."""
    repo_dir = Path(repo_dir).resolve()
    series = Path(series_path)
    series_rel = (os.path.relpath(series.resolve(), repo_dir) if series.is_absolute() else str(series))
    series_rel = Path(series_rel).as_posix()

    guarded = list(dict.fromkeys([som_select.RULE_FILE, som_select.SELECT_FILE, som_select.STAGE1_SERIES,
                                  series_rel]))
    som_select.rule_guard(guarded, repo_dir)

    rule_commit = _added_commit(som_select.RULE_FILE, repo_dir)
    for path in (som_select.SELECT_FILE, som_select.STAGE1_SERIES):
        added = _added_commit(path, repo_dir)
        if added != rule_commit:
            raise SystemExit(f"{path} was added in commit {added}, not in the rule commit {rule_commit} that "
                             f"added {som_select.RULE_FILE} (D-10)")
    select_commit = _git_stdout(["log", "-1", "--format=%H", "--", som_select.SELECT_FILE], repo_dir)
    return {
        "rule_commit": rule_commit,
        "rule_sha256": som_select.rule_digest(repo_dir / som_select.RULE_FILE),
        "select_commit": select_commit,
        "select_sha256": hashlib.sha256((repo_dir / som_select.SELECT_FILE).read_bytes()).hexdigest(),
    }


def require_same_rule(selection_path, rule_file, select_file=TP_DIR / som_select.SELECT_FILE) -> None:
    """Stage 2 (and the later plans) run only on the rule and the code that stage 1 recorded."""
    selection_path = Path(selection_path)
    try:
        recorded = json.loads(selection_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise SystemExit(f"{selection_path}: cannot read the stage-1 selection (run stage 1 first): {error}")
    current = som_select.rule_digest(rule_file)
    if recorded.get("rule_sha256") != current:
        raise SystemExit(f"rule changed since stage 1: {recorded.get('rule_sha256')} != {current}")
    current_code = hashlib.sha256(Path(select_file).read_bytes()).hexdigest()
    if recorded.get("select_sha256") != current_code:
        raise SystemExit(f"selection code changed since stage 1: {recorded.get('select_sha256')} != {current_code}")


# ---------- the stage ----------

def _create_sweep_dir(results_root: Path, name: str) -> Path:
    base = f"{name}_{time.strftime('%Y-%m-%d_%H-%M-%S')}"
    results_root.mkdir(parents=True, exist_ok=True)
    attempt = 1
    while True:
        sweep_dir = results_root / (base if attempt == 1 else f"{base}_{attempt}")
        try:
            sweep_dir.mkdir()
            return sweep_dir
        except FileExistsError:
            attempt += 1


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(columns)
        for row in rows:
            writer.writerow([repr(row[c]) if isinstance(row[c], float) else row[c] for c in columns])


def _relative(path: Path) -> str:
    return Path(os.path.relpath(Path(path).resolve(), TP_DIR)).as_posix()


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_stage(series_path, results_root=RESULTS_DIR, select=False, check_rule=True, workers=None) -> Path:
    series_file = Path(series_path)
    if not series_file.is_absolute():
        series_file = TP_DIR / series_file
    results_root = Path(results_root)

    ident = dict.fromkeys(IDENTITY_KEYS)
    if check_rule:
        ident = rule_identity(series_file)
        if not select:
            require_same_rule(results_root / "som" / STAGE1_NAME / "selection.json", TP_DIR / som_select.RULE_FILE)

    series = sweep.load_series(series_file)
    tasks = sweep.plan(series)
    labels = [variant.label for variant in series.variants]
    if len(set(labels)) != len(labels):
        raise SystemExit(f"{series_file}: variant labels must be unique")

    out = results_root / "som" / series.name
    if out.exists():  # a failed re-run must not leave the previous aggregate.csv or selection.json behind
        shutil.rmtree(out)

    sweep.build_binary()
    sweep_dir = _create_sweep_dir(results_root, series.name)
    shutil.copy(series.path, sweep_dir / "series.json")
    sweep.write_plan(series, sweep_dir / "plan.json")
    varied = sweep.varied_keys(series)
    rows = sweep.run_all(tasks, sweep_dir, workers or series.workers, varied)
    sweep.write_summary(rows, sweep_dir / "summary.csv", varied)
    failed = sum(1 for row in rows if row["status"] != "ok")
    if failed:
        raise SystemExit(f"{failed} of {len(rows)} runs failed; see {sweep_dir / 'summary.csv'}")

    out.mkdir(parents=True)
    _loo_rows, loo_by_seed = som_loo.run_loo(series_file, out, workers)

    stability_by_label, medoids, stability_rows = {}, {}, []
    for variant in series.variants:
        seeds = sorted(series.seeds)
        by_seed = {task.seed: task for task in tasks if task.label == variant.label}
        bmus = [som.read_run(sweep_dir / "runs" / by_seed[seed].name).bmu for seed in seeds]
        k = int(by_seed[seeds[0]].config["grid_k"])
        matrix = som.seed_spearman_matrix(bmus, k)
        stability_by_label[variant.label] = som.stability(bmus, k)
        medoids[variant.label] = som.medoid_seed(matrix, seeds)
        for a in range(len(seeds)):
            for b in range(a + 1, len(seeds)):
                stability_rows.append({"label": variant.label, "seed_a": seeds[a], "seed_b": seeds[b],
                                       "spearman": float(matrix[a, b])})
    _write_csv(out / "stability.csv", STABILITY_COLUMNS, stability_rows)

    with (sweep_dir / "summary.csv").open(newline="", encoding="utf-8") as file:
        summary_rows = list(csv.DictReader(file))
    aggregated = som_select.aggregate(summary_rows, loo_by_seed, stability_by_label)
    for row in aggregated:
        row["medoid_seed"] = medoids[row["label"]]
    _write_csv(out / "aggregate.csv", list(aggregated[0]), aggregated)
    _write_json(out / "stage.json", {
        "series": _relative(series_file), "sweep_dir": _relative(sweep_dir), **ident,
        "n_runs": len(tasks), "n_loo_trainings": len(_loo_rows),
    })

    if select:
        result = som_select.select_grid(aggregated)
        result.update(ident)
        result["series"] = _relative(series_file)
        result["sweep_dir"] = _relative(sweep_dir)
        result["figure_seed"] = None
        result["figure_run"] = None
        if result["chosen_k"] is not None:
            seed = medoids[result["chosen_label"]]
            task = next(t for t in tasks if t.label == result["chosen_label"] and t.seed == seed)
            result["figure_seed"] = seed
            result["figure_run"] = _relative(sweep_dir / "runs" / task.name)
        _write_json(out / "selection.json", result)
    else:
        _write_robustness(out, results_root, aggregated)

    print(f"som -> {out}")
    return out


def _write_robustness(out: Path, results_root: Path, aggregated: list[dict]) -> None:
    stage1_path = results_root / "som" / STAGE1_NAME / "selection.json"
    try:
        stage1 = json.loads(stage1_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise SystemExit(f"{stage1_path}: cannot read the stage-1 selection: {error}")
    if stage1.get("chosen_k") is None:
        raise SystemExit(f"{stage1_path}: stage 1 chose no grid; there is no k to check (D-14)")
    dropped = bool(stage1["te_filter_dropped"])

    rows, failing = [], []
    for row in aggregated:
        flags = som_select.passes_filters(row)
        passes = flags["empty"] and flags["creators"] and (dropped or flags["te"])
        rows.append({
            "label": row["label"], "radius0": row["radius0"], "eta0": row["eta0"], "epochs": row["epochs"],
            "te_mean": row["te_mean"], "empty_fraction_mean": row["empty_fraction_mean"],
            "creators_per_occupied_mean": row["creators_per_occupied_mean"],
            "passes_te": bool(flags["te"]), "passes_empty": bool(flags["empty"]),
            "passes_creators": bool(flags["creators"]), "passes": bool(passes),
            "qe_loo_mean": row["qe_loo_mean"], "qe_loo_sd": row["qe_loo_sd"], "stability": row["stability"],
        })
        if not passes:
            failing.append(row["label"])
    _write_csv(out / "robustness.csv", ROBUSTNESS_COLUMNS, rows)
    _write_json(out / "robustness.json", {"robust": not failing, "failing_variants": failing,
                                          "te_checked": not dropped})


def write_stage2(selection_path=RESULTS_DIR / "som" / STAGE1_NAME / "selection.json",
                 out_path=TP_DIR / som_select.STAGE2_SERIES) -> Path:
    """analysis/series_som_stage2.json from the stage-1 choice and the committed ladders, nothing else."""
    selection_path = Path(selection_path)
    try:
        selection = json.loads(selection_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise SystemExit(f"{selection_path}: cannot read the stage-1 selection: {error}")
    if selection.get("outcome") != "chosen" or selection.get("chosen_k") is None:
        raise SystemExit(f"{selection_path}: outcome is {selection.get('outcome')!r}; with no chosen grid there "
                         "is no k to vary (D-14)")
    out_path = Path(out_path)
    out_path.write_text(json.dumps(som_select.stage2_series(int(selection["chosen_k"])), indent=2) + "\n",
                        encoding="utf-8")
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="run one stage under the committed rule")
    run.add_argument("series", type=Path, help="series JSON, e.g. analysis/series_som_stage1.json")
    run.add_argument("--select", action="store_true", help="stage 1: also apply the selection rule")
    run.add_argument("--workers", type=int, help="parallel runs and trainings (default: every core)")
    commands.add_parser("write-stage2", help="generate analysis/series_som_stage2.json from the chosen k")
    args = parser.parse_args(argv)
    if args.command == "run":
        run_stage(args.series, select=args.select, check_rule=True, workers=args.workers)
    else:
        print(f"stage 2 series -> {write_stage2()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
