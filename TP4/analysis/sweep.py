#!/usr/bin/env python3
"""Runs a series of neuron runs (variants x seeds) and writes one summary.csv.

    python3 analysis/sweep.py analysis/series_smoke_oja.json
    python3 analysis/sweep.py analysis/series_smoke_oja.json --workers 4
    python3 analysis/sweep.py analysis/series_smoke_oja.json --dry-run   # plan only

Every (variant, seed) is one run of neuron/build/neuron. Everything goes to
analysis/results/<series>_<date>_<time>/: series.json (copy of the series file), plan.json (the series
resolved), configs/ (one config per run), runs/<run>/ (the usual run files) and summary.csv (one row per
run). The paths inside the configs are relative to the sweep directory, never absolute. Model-agnostic:
the summary columns come from the series and from each run's metrics.json. Standard library only.
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ANALYSIS_DIR = Path(__file__).resolve().parent
TP_DIR = ANALYSIS_DIR.parent
NEURON_DIR = TP_DIR / "neuron"
BINARY = NEURON_DIR / "build" / "neuron"
RESULTS_DIR = ANALYSIS_DIR / "results"

PATH_KEYS = ("input",)  # relative to neuron/ in the base configs, like with make run
SERIES_KEYS = ("base_config", "set", "vary", "values", "variants", "seeds", "workers")
FIXED_COLUMNS = ["run", "variant", "label", "seed", "status"]
RESULT_PREFIX = "results -> "


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
    varied: str | None  # the key that "values" sweeps; None with explicit "variants" or no variation
    variants: list[Variant]
    seeds: list[int]
    workers: int


@dataclass(frozen=True)
class Task:
    index: int  # position in the plan, also the run directory prefix
    variant: int
    label: str
    seed: int
    config: dict[str, Any]  # paths still relative to neuron/; relative_paths() rewrites them per sweep

    @property
    def name(self) -> str:
        slug = re.sub(r"[^A-Za-z0-9.]+", "-", self.label).strip("-") or "variant"
        return f"{self.index:03d}_{slug}_seed{self.seed}"


# ---------- series ----------

def load_series(path: Path) -> Series:
    try:
        spec = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise SystemExit(f"{path}: cannot read the series: {error}")
    if not isinstance(spec, dict):
        raise SystemExit(f"{path}: the series must be a JSON object")
    for key in spec:
        if not key.startswith("_") and key not in SERIES_KEYS:
            raise SystemExit(f'{path}: unknown series key "{key}" (allowed: {", ".join(SERIES_KEYS)})')
    if "base_config" not in spec:
        raise SystemExit(f'{path}: missing key "base_config"')

    base_path = (path.parent / spec["base_config"]).resolve()
    try:
        base_config = json.loads(base_path.read_text())
    except (OSError, ValueError) as error:
        raise SystemExit(f"{path}: cannot read base_config {spec['base_config']}: {error}")
    if not isinstance(base_config, dict):
        raise SystemExit(f"{base_path}: the config must be a JSON object")

    shared = spec.get("set", {})
    if not isinstance(shared, dict):
        raise SystemExit(f'{path}: "set" must be an object')
    variants = series_variants(spec, path)
    if "seeds" in spec:
        seeds = spec["seeds"]
    elif "seed" in base_config:
        seeds = [base_config["seed"]]
    else:
        raise SystemExit(f'{path}: the series has no "seeds" and the base config has no "seed"')
    if not isinstance(seeds, list) or not seeds or not all(isinstance(seed, int) and not isinstance(seed, bool)
                                                           for seed in seeds):
        raise SystemExit(f'{path}: "seeds" must be a non-empty list of integers')
    workers = spec.get("workers", os.cpu_count() or 1)
    if not isinstance(workers, int) or isinstance(workers, bool) or workers < 1:
        raise SystemExit(f'{path}: "workers" must be an integer >= 1')
    return Series(path.stem, path, base_config, shared, spec.get("vary"), variants, seeds, workers)


def series_variants(spec: dict[str, Any], path: Path) -> list[Variant]:
    """"vary" + "values" (one key, one variant per value), "variants" (label + several keys each), or
    neither: a single variant "base" with no overrides."""
    if "variants" in spec:
        if "vary" in spec or "values" in spec:
            raise SystemExit(f'{path}: use "variants" or "vary" + "values", not both')
        if not isinstance(spec["variants"], list) or not spec["variants"]:
            raise SystemExit(f'{path}: "variants" must be a non-empty list')
        for variant in spec["variants"]:
            if not isinstance(variant, dict) or "label" not in variant or not isinstance(variant.get("set"), dict):
                raise SystemExit(f'{path}: every variant needs "label" and an object "set"')
        return [Variant(str(variant["label"]), variant["set"]) for variant in spec["variants"]]
    if "vary" in spec or "values" in spec:
        if "vary" not in spec or "values" not in spec:
            raise SystemExit(f'{path}: "vary" and "values" go together')
        if not isinstance(spec["values"], list) or not spec["values"]:
            raise SystemExit(f'{path}: "values" must be a non-empty list')
        return [Variant(value_label(value), {spec["vary"]: value}) for value in spec["values"]]
    return [Variant("base", {})]


def value_label(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value)


def set_dotted(config: dict[str, Any], key: str, value: Any) -> None:
    """config["a.b"] = value means config["a"]["b"] = value; intermediate objects are created as needed."""
    parts = key.split(".")
    node = config
    for part in parts[:-1]:
        child = node.setdefault(part, {})
        if not isinstance(child, dict):
            raise SystemExit(f'cannot set "{key}": "{part}" is not an object in the config')
        node = child
    node[parts[-1]] = value


def get_dotted(config: dict[str, Any], key: str) -> Any:
    node: Any = config
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return ""
        node = node[part]
    return node


def relative_paths(config: dict[str, Any], sweep_dir: Path) -> dict[str, Any]:
    """The base configs point at paths relative to neuron/; the binary runs from sweep_dir, so each path key
    is resolved against neuron/ and rewritten relative to sweep_dir (never absolute: D-04)."""
    return {key: os.path.relpath(os.path.join(NEURON_DIR, value), sweep_dir)
            if key in PATH_KEYS and isinstance(value, str) and value else value
            for key, value in config.items()}


def plan(series: Series) -> list[Task]:
    tasks = []
    for v, variant in enumerate(series.variants):
        for seed in series.seeds:
            config = copy.deepcopy(series.base_config)
            for key, value in {**series.shared, **variant.overrides}.items():
                set_dotted(config, key, copy.deepcopy(value))
            config["seed"] = seed
            tasks.append(Task(len(tasks), v, variant.label, seed, config))
    return tasks


def varied_keys(series: Series) -> list[str]:
    """Every key in any variant's overrides, in first-appearance order: these become summary columns."""
    keys: list[str] = []
    for variant in series.variants:
        keys.extend(key for key in variant.overrides if key not in keys)
    return keys


# ---------- running ----------

def build_binary() -> None:
    try:
        subprocess.run(["make", "-s", "-C", str(NEURON_DIR)], check=True)
    except (OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"cannot build neuron/build/neuron: {error}")


def cell(value: Any) -> Any:
    return json.dumps(value) if isinstance(value, (list, dict)) else value


def run_task(task: Task, sweep_dir: Path, varied: list[str]) -> dict[str, Any]:
    config = relative_paths(task.config, sweep_dir)
    config_path = sweep_dir / "configs" / f"{task.name}.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    row: dict[str, Any] = {"run": task.name, "variant": task.variant, "label": task.label, "seed": task.seed,
                           "status": "ok"}
    for key in varied:
        row[key] = cell(get_dotted(task.config, key))

    # Run from sweep_dir with the config path relative to it: the binary makes results/<run>/ under its working
    # directory and its error messages name configs/<run>.json instead of an absolute path. Argument list,
    # never a shell string.
    process = subprocess.run([str(BINARY), os.path.relpath(config_path, sweep_dir)], cwd=sweep_dir,
                             capture_output=True, text=True)
    if process.returncode != 0:
        reason = process.stderr.strip().splitlines()[-1:] or [f"exit code {process.returncode}"]
        return {**row, "status": f"error: {reason[0]}"}

    printed = [line for line in process.stdout.splitlines() if line.startswith(RESULT_PREFIX)]
    if not printed:
        return {**row, "status": "error: the binary printed no results directory"}
    run_dir = sweep_dir / "runs" / task.name
    shutil.move(str(sweep_dir / printed[-1][len(RESULT_PREFIX):].strip()), str(run_dir))
    metrics_path = run_dir / "metrics.json"
    if not metrics_path.is_file():  # a run that failed after creating its directory leaves no metrics
        return {**row, "status": "error: metrics.json missing"}
    try:
        metrics = json.loads(metrics_path.read_text())
    except ValueError as error:
        return {**row, "status": f"error: metrics.json: {error}"}
    if not isinstance(metrics, dict):
        return {**row, "status": "error: metrics.json is not an object"}
    for key, value in metrics.items():
        if key not in row:
            row[key] = cell(value)
    return row


def run_all(tasks: list[Task], sweep_dir: Path, workers: int, varied: list[str]) -> list[dict[str, Any]]:
    """In parallel, one process per run; failures are recorded and the rest keeps going."""
    for directory in ("configs", "runs"):
        (sweep_dir / directory).mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(run_task, task, sweep_dir, varied): task for task in tasks}
        for future in as_completed(futures):
            task = futures[future]
            try:
                row = future.result()
            except Exception as error:  # a broken run shouldn't take the series down
                row = {"run": task.name, "variant": task.variant, "label": task.label, "seed": task.seed,
                       "status": f"error: {error}"}
            rows.append(row)
            print_progress(row, len(rows), len(tasks), time.monotonic() - started)
    clean_leftovers(sweep_dir / "results")
    return sorted(rows, key=lambda row: row["run"])


def clean_leftovers(leftovers: Path) -> None:
    """Every successful run was moved to runs/; what stays in results/ are the partial directories of the failed
    ones (only a config copy, already in configs/). The reason of each failure is in summary.csv."""
    if not leftovers.is_dir():
        return
    for entry in leftovers.iterdir():
        if entry.is_dir() and not (entry / "metrics.json").exists():
            shutil.rmtree(entry)
    if not any(leftovers.iterdir()):
        leftovers.rmdir()


def print_progress(row: dict[str, Any], done: int, total: int, elapsed: float) -> None:
    print(f"[{done}/{total}] {row['label']} seed {row['seed']}: {row['status']}  ({elapsed:.1f}s)", file=sys.stderr)


# ---------- summary.csv ----------

def summary_columns(rows: list[dict[str, Any]], varied: list[str]) -> list[str]:
    """run, variant, label, seed, status; then the varied keys; then the metrics keys in the order of the
    lowest-named ok run, followed by the keys that only other ok runs have, sorted."""
    columns = list(FIXED_COLUMNS)
    columns.extend(key for key in varied if key not in columns)
    known = set(columns)
    ok_rows = sorted((row for row in rows if row["status"] == "ok"), key=lambda row: row["run"])
    if ok_rows:
        first = [key for key in ok_rows[0] if key not in known]
        columns.extend(first)
        known.update(first)
    extra = sorted({key for row in ok_rows for key in row if key not in known})
    columns.extend(extra)
    return columns


def write_summary(rows: list[dict[str, Any]], path: Path, varied: list[str] | tuple[str, ...] = ()) -> None:
    columns = summary_columns(rows, list(varied))
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns, restval="", lineterminator="\n")
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda row: row["run"]))


# plan.json: the series resolved (base config, overrides, variants), so it doesn't depend on where the series
# file was
def write_plan(series: Series, path: Path) -> None:
    path.write_text(json.dumps({
        "name": series.name,
        "base_config": series.base_config,
        "set": series.shared,
        "vary": series.varied,
        "variants": [asdict(variant) for variant in series.variants],
        "seeds": series.seeds,
    }, indent=2) + "\n")


# ---------- cli ----------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("series", type=Path, help="series JSON, e.g. analysis/series_smoke_oja.json")
    parser.add_argument("--workers", type=int, help='parallel runs (default: the series\' "workers", else every core)')
    parser.add_argument("--dry-run", action="store_true", help="print the plan without building or running anything")
    return parser.parse_args()


def print_plan(series: Series, tasks: list[Task]) -> None:
    print(f"series {series.name}: {len(series.variants)} variants x {len(series.seeds)} seeds = {len(tasks)} runs")
    for variant in series.variants:
        print(f"  {variant.label}: {json.dumps(variant.overrides)}")
    print(f"  seeds: {json.dumps(series.seeds)}")
    if series.shared:
        print(f"  every run: {json.dumps(series.shared)}")


def create_sweep_dir(series: Series) -> Path:
    base = f"{series.name}_{time.strftime('%Y-%m-%d_%H-%M-%S')}"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    attempt = 1
    while True:
        sweep_dir = RESULTS_DIR / (base if attempt == 1 else f"{base}_{attempt}")
        try:
            sweep_dir.mkdir()
            return sweep_dir
        except FileExistsError:
            attempt += 1


def main() -> None:
    args = parse_args()
    series = load_series(args.series)
    tasks = plan(series)
    print_plan(series, tasks)
    if args.dry_run:
        return

    build_binary()
    sweep_dir = create_sweep_dir(series)
    shutil.copy(series.path, sweep_dir / "series.json")
    write_plan(series, sweep_dir / "plan.json")
    varied = varied_keys(series)
    rows = run_all(tasks, sweep_dir, args.workers or series.workers, varied)
    write_summary(rows, sweep_dir / "summary.csv", varied)
    failed = sum(1 for row in rows if row["status"] != "ok")
    if failed:
        print(f"{failed} of {len(rows)} runs failed", file=sys.stderr)
    print(f"summary -> {sweep_dir / 'summary.csv'}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
