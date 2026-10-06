#!/usr/bin/env python3
"""Runs a series of neuron trainings that vary one parameter, and writes a comparison report.

    python3 analysis/sweep.py analysis/series_eta.json
    python3 analysis/sweep.py analysis/series_eta.json --workers 4
    python3 analysis/sweep.py analysis/series_eta.json --dry-run   # plan only
    python3 analysis/sweep.py analysis/series_eta.json --no-run-reports

Every (variant, seed) is one run of build/neuron. Everything goes to
analysis/results/<series>_<date>_<time>/: runs/<run>/ (the usual run files plus its report.html, unless --no-run-reports),
summary.csv (one row per run) and report.html (the comparison). Standard library only.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

ANALYSIS_DIR = Path(__file__).resolve().parent
TP_DIR = ANALYSIS_DIR.parent
NEURON_DIR = TP_DIR / "neuron"
BINARY = NEURON_DIR / "build" / "neuron"
RESULTS_DIR = ANALYSIS_DIR / "results"

sys.path.insert(0, str(TP_DIR / "scripts"))
from run_error import run_error  # noqa: E402
from run_report import Run, argmax_hits, classification_hits, load_run, render  # noqa: E402

MAX_VARIANTS = 8  # one categorical color each
PATH_KEYS = ("train_dataset", "validation_dataset", "initial_weights")  # relative to neuron/ in the configs


@dataclass(frozen=True)
class Variant:
    label: str
    overrides: dict[str, Any]


@dataclass(frozen=True)
class Series:
    name: str
    path: Path
    base_config: dict[str, Any]
    shared: dict[str, Any]  # overrides applied to every variant
    varied: str | None  # the key that "values" sweeps; None with explicit "variants"
    variants: list[Variant]
    seeds: list[int]
    workers: int


@dataclass(frozen=True)
class Task:
    index: int  # position in the plan, also the run directory prefix
    variant: int
    label: str
    seed: int
    config: dict[str, Any]

    @property
    def name(self) -> str:
        slug = re.sub(r"[^A-Za-z0-9.]+", "-", self.label).strip("-") or "variant"
        return f"{self.index:03d}_{slug}_seed{self.seed}"


# summary.csv: one row per run. Validation metrics are on the final weights (the best train epoch).
@dataclass(frozen=True)
class RunSummary:
    run: str
    variant: int
    label: str
    seed: int
    status: str  # "ok" or the error
    epochs_run: int | None = None
    best_epoch: int | None = None
    converged: bool | None = None  # None when the config has no stop criterion
    train_mse: float | None = None  # best train MSE, the epoch whose weights the run keeps
    validation_mse: float | None = None
    validation_mae: float | None = None
    validation_max_error: float | None = None
    accuracy: float | None = None  # argmax with several outputs, closer class with two zetas; else None
    elapsed_s: float | None = None


# ---------- series ----------

def load_series(path: Path) -> Series:
    spec = json.loads(path.read_text())
    base_path = (path.parent / spec["base_config"]).resolve()
    base_config = json.loads(base_path.read_text())
    variants = series_variants(spec)
    if not 1 <= len(variants) <= MAX_VARIANTS:
        raise SystemExit(f"{path}: between 1 and {MAX_VARIANTS} variants per series, got {len(variants)}")
    seeds = spec.get("seeds", [base_config["seed"]])
    return Series(path.stem, path, base_config, spec.get("set", {}), spec.get("vary"), variants, seeds,
                  spec.get("workers", os.cpu_count() or 1))


def series_variants(spec: dict[str, Any]) -> list[Variant]:
    """Either "vary" + "values" (one key, one variant per value) or "variants" (label + several keys each)."""
    if "variants" in spec:
        return [Variant(variant["label"], variant["set"]) for variant in spec["variants"]]
    if "vary" not in spec or "values" not in spec:
        raise SystemExit('a series needs "vary" + "values" or "variants"')
    return [Variant(value_label(value), {spec["vary"]: value}) for value in spec["values"]]


def value_label(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value)


def absolute_paths(config: dict[str, Any]) -> dict[str, Any]:
    """The configs point at neuron/data/...; the runs execute elsewhere, so the paths become absolute."""
    return {key: str((NEURON_DIR / value).resolve()) if key in PATH_KEYS and value else value
            for key, value in config.items()}


def plan(series: Series) -> list[Task]:
    tasks = []
    for v, variant in enumerate(series.variants):
        for seed in series.seeds:
            config = absolute_paths({**series.base_config, **series.shared, **variant.overrides, "seed": seed})
            tasks.append(Task(len(tasks), v, variant.label, seed, config))
    return tasks


# ---------- running ----------

def build_binary() -> None:
    subprocess.run(["make", "-s", "-C", str(NEURON_DIR)], check=True)


def run_task(task: Task, sweep_dir: Path, run_reports: bool) -> RunSummary:
    config_path = sweep_dir / "configs" / f"{task.name}.json"
    config_path.write_text(json.dumps(task.config, indent=2))
    # Run from sweep_dir: the binary makes results/<timestamp>_<activation>/ under its working directory
    process = subprocess.run([str(BINARY), str(config_path)], cwd=sweep_dir, capture_output=True, text=True)
    if process.returncode != 0:
        reason = process.stderr.strip().splitlines()[-1:] or [f"exit code {process.returncode}"]
        return RunSummary(task.name, task.variant, task.label, task.seed, f"error: {reason[0]}")

    run_dir = sweep_dir / "runs" / task.name
    shutil.move(sweep_dir / process.stdout.strip().removeprefix("results -> "), run_dir)
    run = load_run(run_dir)
    if run_reports:
        (run_dir / "report.html").write_text(render(run))
    return summarize(task, run)


def summarize(task: Task, run: Run) -> RunSummary:
    error = run_error([(sample.zeta, sample.prediction) for sample in run.samples])
    train_mse = [record.train["mse"] for record in run.epochs]
    best_epoch = train_mse.index(min(train_mse))  # the first minimum, like keep_if_best in main.c
    epochs_run = run.epochs[-1].epoch
    return RunSummary(
        task.name, task.variant, task.label, task.seed, "ok",
        epochs_run=epochs_run,
        best_epoch=best_epoch,
        converged=converged(run.config, epochs_run, min(train_mse)),
        train_mse=min(train_mse),
        validation_mse=error.mse,
        validation_mae=error.mae,
        validation_max_error=error.max_abs_error,
        accuracy=accuracy(run),
        elapsed_s=run.epochs[-1].elapsed,
    )


def converged(config: dict[str, Any], epochs_run: int, best_train_mse: float) -> bool | None:
    """Stopping before the planned epochs means it converged; a sign run converging exactly at the
    last epoch isn't told apart from one that didn't (epochs.csv doesn't count misclassified samples)."""
    tolerance = config.get("tolerance", 0)
    if config["activation"] != "sign" and not tolerance:
        return None
    return epochs_run < config["epochs"] or (tolerance > 0 and best_train_mse < tolerance)


def accuracy(run: Run) -> float | None:
    if run.n_outputs > 1:
        return argmax_hits(run) / run.n_samples
    hits = classification_hits(run.samples)
    return None if hits is None else hits[0] / run.n_samples


def run_all(tasks: list[Task], sweep_dir: Path, workers: int, run_reports: bool) -> list[RunSummary]:
    """In parallel, one process per run; failures are recorded and the rest keeps going."""
    for directory in ("configs", "runs"):
        (sweep_dir / directory).mkdir(parents=True, exist_ok=True)
    summaries: list[RunSummary] = []
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(run_task, task, sweep_dir, run_reports): task for task in tasks}
        for future in as_completed(futures):
            task = futures[future]
            try:
                summary = future.result()
            except Exception as error:  # a broken run shouldn't take the series down
                summary = RunSummary(task.name, task.variant, task.label, task.seed, f"error: {error}")
            summaries.append(summary)
            print_progress(summary, len(summaries), len(tasks), time.monotonic() - started)
    leftovers = sweep_dir / "results"  # empty once every run was moved to runs/
    if leftovers.exists() and not any(leftovers.iterdir()):
        leftovers.rmdir()
    return sorted(summaries, key=lambda summary: summary.run)


def print_progress(summary: RunSummary, done: int, total: int, elapsed: float) -> None:
    result = summary.status if summary.status != "ok" else f"validation MSE {summary.validation_mse:.4g}"
    print(f"[{done}/{total}] {summary.label} seed {summary.seed}: {result}  ({elapsed:.1f}s)", file=sys.stderr)


# ---------- summary.csv ----------

def write_summary(summaries: list[RunSummary], path: Path) -> None:
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=[field.name for field in fields(RunSummary)])
        writer.writeheader()
        writer.writerows(asdict(summary) for summary in summaries)


def parse_field(name: str, value: str) -> Any:
    if name in ("run", "label", "status"):
        return value
    if value == "":
        return None
    if name == "converged":
        return value == "True"
    return int(value) if name in ("variant", "seed", "epochs_run", "best_epoch") else float(value)


def read_summary(path: Path) -> list[RunSummary]:
    with path.open(newline="") as file:
        return [RunSummary(**{name: parse_field(name, value) for name, value in row.items()})
                for row in csv.DictReader(file)]


# plan.json: the series resolved (base config, overrides, variants), so the report doesn't depend on
# where the series file was
def write_plan(series: Series, path: Path) -> None:
    path.write_text(json.dumps({
        "name": series.name,
        "base_config": series.base_config,
        "set": series.shared,
        "vary": series.varied,
        "variants": [asdict(variant) for variant in series.variants],
        "seeds": series.seeds,
    }, indent=2))


# ---------- cli ----------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("series", type=Path, help="series JSON, e.g. analysis/series_eta.json")
    parser.add_argument("--workers", type=int, help='parallel runs (default: the series\' "workers", else every core)')
    parser.add_argument("--no-run-reports", action="store_true",
                        help="skip each run's report.html (~6 MB with digits); run_report.py can make it later")
    parser.add_argument("--dry-run", action="store_true", help="print the plan without running anything")
    return parser.parse_args()


def print_plan(series: Series, tasks: list[Task]) -> None:
    print(f"series {series.name}: {len(series.variants)} variants x {len(series.seeds)} seeds = {len(tasks)} runs")
    for variant in series.variants:
        print(f"  {variant.label}: {json.dumps(variant.overrides)}")
    if series.shared:
        print(f"  every run: {json.dumps(series.shared)}")


def main() -> None:
    from sweep_report import write_report  # imports sweep, so not at the top

    args = parse_args()
    series = load_series(args.series)
    tasks = plan(series)
    print_plan(series, tasks)
    if args.dry_run:
        return

    build_binary()
    sweep_dir = RESULTS_DIR / f"{series.name}_{time.strftime('%Y-%m-%d_%H-%M-%S')}"
    sweep_dir.mkdir(parents=True)
    shutil.copy(series.path, sweep_dir / "series.json")
    write_plan(series, sweep_dir / "plan.json")
    summaries = run_all(tasks, sweep_dir, args.workers or series.workers, not args.no_run_reports)
    write_summary(summaries, sweep_dir / "summary.csv")
    print(f"summary -> {sweep_dir / 'summary.csv'}")
    print(f"report  -> {write_report(sweep_dir)}")


if __name__ == "__main__":
    main()
