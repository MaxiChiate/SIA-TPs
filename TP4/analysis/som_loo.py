#!/usr/bin/env python3
"""QE leave-one-out of a Kohonen series: one map per held-out creator, per (variant, seed) (D-09).

    .venv/bin/python analysis/som_loo.py analysis/series_som_stage1.json
    .venv/bin/python analysis/som_loo.py analysis/series_som_stage1.json --out DIR --workers 4

For every (variant, seed) of the series and every row i of the input, the binary trains a map on the other
n - 1 rows with that run's own config and seed; Python then measures the distance from row i to its nearest
prototype (the binary gains no LOO mode). Each training runs in its own temporary working directory under
<out>/tmp, so the binary's run directories never collide. Outputs in <out>: loo.csv (label, variant, seed,
fold, bmu, distance), loo_by_seed.csv (label, variant, seed, n_folds, qe_loo: the mean over the folds of one
seed) and folds/fold_NN.csv. Averaging seeds into a config happens in som_select.aggregate, never here
(RESEARCH Pitfall 7). A failed training stops the driver before any CSV is written.

numpy and the standard library only.
"""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

TP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TP_DIR / "scripts"))
sys.path.insert(0, str(TP_DIR / "analysis"))

import som  # noqa: E402
import sweep  # noqa: E402

LOO_COLUMNS = ["label", "variant", "seed", "fold", "bmu", "distance"]
BY_SEED_COLUMNS = ["label", "variant", "seed", "n_folds", "qe_loo"]


def write_folds(input_csv: Path, folds_dir: Path) -> list[Path]:
    """folds_dir/fold_NN.csv = the header line plus every data line except data line NN, copied verbatim so
    the C side reads the exact same doubles."""
    lines = Path(input_csv).read_text(encoding="utf-8").splitlines()
    header, data = lines[0], lines[1:]
    folds_dir = Path(folds_dir)
    folds_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(len(data)):
        path = folds_dir / f"fold_{i:02d}.csv"
        path.write_text("".join(line + "\n" for line in [header] + data[:i] + data[i + 1:]), encoding="utf-8")
        paths.append(path)
    return paths


def read_matrix(input_csv: Path) -> np.ndarray:
    with Path(input_csv).open(newline="", encoding="utf-8") as file:
        rows = list(csv.reader(file))
    return np.array([[float(cell) for cell in row] for row in rows[1:]], dtype=np.float64)


def train_fold(task: sweep.Task, fold: int, fold_path: Path, x: np.ndarray, tmp_root: Path) -> dict:
    """One training in its own temporary directory; returns the held-out creator's BMU and distance."""
    with tempfile.TemporaryDirectory(dir=tmp_root) as work:
        work_dir = Path(work)
        config = dict(task.config)
        config["input"] = os.path.relpath(fold_path, work_dir)
        run_dir = som.run_binary(config, work_dir)
        run = som.read_run(run_dir)
        bmu, distance = som.nearest_distance(x[fold], run.prototypes)
    return {"label": task.label, "variant": task.variant, "seed": task.seed, "fold": fold, "bmu": bmu,
            "distance": distance}


def run_loo(series_path: Path, out_dir: Path, workers: int | None = None) -> tuple[list[dict], list[dict]]:
    sweep.build_binary()
    series = sweep.load_series(Path(series_path))
    tasks = sweep.plan(series)
    inputs = {str((sweep.NEURON_DIR / task.config["input"]).resolve()) for task in tasks}
    if len(inputs) != 1:
        raise SystemExit(f"{series_path}: every run of a LOO series must share one input, found {sorted(inputs)}")
    input_csv = Path(inputs.pop())

    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in ("loo.csv", "loo_by_seed.csv"):
        (out_dir / stale).unlink(missing_ok=True)
    x = read_matrix(input_csv)
    fold_paths = write_folds(input_csv, out_dir / "folds")
    tmp_root = out_dir / "tmp"
    tmp_root.mkdir(exist_ok=True)

    jobs = [(task, fold) for task in tasks for fold in range(len(fold_paths))]
    rows: list[dict] = []
    failures: list[tuple[int, int, int, str, str]] = []

    def work(job):
        task, fold = job
        try:
            return train_fold(task, fold, fold_paths[fold], x, tmp_root), None
        except Exception as error:  # a broken training must stop the driver, not vanish
            return None, (task.variant, task.seed, fold, task.label, str(error))

    with ThreadPoolExecutor(max_workers=workers or series.workers or os.cpu_count() or 1) as pool:
        for row, failure in pool.map(work, jobs):
            if failure is None:
                rows.append(row)
            else:
                failures.append(failure)

    if failures:
        shutil.rmtree(tmp_root, ignore_errors=True)
        _v, seed, fold, label, reason = min(failures, key=lambda f: f[:3])
        raise SystemExit(f"{len(failures)} LOO trainings failed; first: {label} seed {seed} fold {fold}: {reason}")

    rows.sort(key=lambda row: (row["variant"], row["seed"], row["fold"]))
    by_seed = []
    for task in tasks:
        distances = [row["distance"] for row in rows if row["variant"] == task.variant and row["seed"] == task.seed]
        by_seed.append({"label": task.label, "variant": task.variant, "seed": task.seed,
                        "n_folds": len(distances), "qe_loo": float(np.mean(distances))})
    by_seed.sort(key=lambda row: (row["variant"], row["seed"]))

    write_csv(out_dir / "loo.csv", LOO_COLUMNS, rows)
    write_csv(out_dir / "loo_by_seed.csv", BY_SEED_COLUMNS, by_seed)
    shutil.rmtree(tmp_root, ignore_errors=True)
    return rows, by_seed


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(columns)
        for row in rows:
            writer.writerow([repr(row[c]) if isinstance(row[c], float) else row[c] for c in columns])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("series", type=Path, help="series JSON, e.g. analysis/series_som_stage1.json")
    parser.add_argument("--out", type=Path, help="output folder (default analysis/results/som/<series>/loo)")
    parser.add_argument("--workers", type=int, help="parallel trainings (default: every core)")
    args = parser.parse_args(argv)
    out = args.out or TP_DIR / "analysis" / "results" / "som" / args.series.stem / "loo"
    run_loo(args.series, out, args.workers)
    print(f"loo -> {Path(out).resolve() / 'loo.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
