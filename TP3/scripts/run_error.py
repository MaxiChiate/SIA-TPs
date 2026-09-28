#!/usr/bin/env python3
"""Computes the error of one neuron run from its predictions.csv.

Takes a run directory (results/<date>_<time>_<activation>/); without one, uses the latest run.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent.parent / "neuron" / "results"

@dataclass(frozen=True)
class RunError:
    n_samples: int  # zeta values: samples x outputs
    energy: float  # E = 1/2 * sum((zeta - O)^2), the error the neuron minimizes
    mse: float
    mae: float
    max_abs_error: float


def latest_run(results_dir: Path) -> Path:
    runs = sorted(path for path in results_dir.iterdir() if path.is_dir())
    if not runs:
        raise SystemExit(f"no runs in {results_dir}")
    return runs[-1]


def output_columns(names: list[str], prefix: str) -> list[tuple[str, int | None]]:
    """(column, output) pairs: `prefix` alone with a single output, `prefix_0`, `prefix_1`, ... with several."""
    if prefix in names:
        return [(prefix, None)]
    columns = [name for name in names if name.startswith(f"{prefix}_")]
    return [(name, int(name.removeprefix(f"{prefix}_"))) for name in columns]


def load_predictions(run_dir: Path) -> list[tuple[float, float]]:
    """One (zeta, prediction) pair per sample and output."""
    with (run_dir / "predictions.csv").open(newline="") as file:
        reader = csv.DictReader(file)
        names = list(reader.fieldnames or [])
        pairs = list(zip(output_columns(names, "zeta"), output_columns(names, "prediction")))
        return [(float(row[zeta]), float(row[prediction])) for row in reader for (zeta, _), (prediction, _) in pairs]


def run_error(pairs: list[tuple[float, float]]) -> RunError:
    errors = [zeta - prediction for zeta, prediction in pairs]
    squared_sum = sum(error ** 2 for error in errors)
    abs_errors = [abs(error) for error in errors]
    return RunError(
        n_samples=len(errors),
        energy=squared_sum / 2,
        mse=squared_sum / len(errors),
        mae=sum(abs_errors) / len(errors),
        max_abs_error=max(abs_errors),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path, nargs="?", help="run directory (default: latest)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dir = args.run_dir or latest_run(RESULTS_DIR)
    error = run_error(load_predictions(run_dir))
    print(f"run:         {run_dir}")
    print(f"samples:     {error.n_samples}")
    print(f"E (½·SSE):   {error.energy:.6g}")
    print(f"MSE:         {error.mse:.6g}")
    print(f"MAE:         {error.mae:.6g}")
    print(f"max |e|:     {error.max_abs_error:.6g}")


if __name__ == "__main__":
    main()
