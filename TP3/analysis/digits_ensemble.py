"""Accuracy of an ensemble of digit networks: the average of their 10 outputs (stdlib only).

Takes the predictions.csv of several runs on the same set (same sample order, so same dataset and the
runs differ in seed or in training). Prints each run's accuracy and the ensemble's.

    python3 analysis/digits_ensemble.py <run>/predictions.csv <run>/predictions.csv ...
"""

from __future__ import annotations

import argparse
import csv
import statistics
from pathlib import Path

N_CLASSES = 10


def load(path: Path) -> tuple[list[int], list[list[float]]]:
    with path.open(newline="") as file:
        rows = list(csv.DictReader(file))
    truth = [max(range(N_CLASSES), key=lambda k: float(row[f"zeta_{k}"])) for row in rows]
    outputs = [[float(row[f"prediction_{k}"]) for k in range(N_CLASSES)] for row in rows]
    return truth, outputs


def argmax(values: list[float]) -> int:
    return max(range(len(values)), key=values.__getitem__)


def accuracy(truth: list[int], outputs: list[list[float]]) -> float:
    return sum(argmax(o) == t for t, o in zip(truth, outputs)) / len(truth)


def average(all_outputs: list[list[list[float]]]) -> list[list[float]]:
    return [[statistics.fmean(run[i][k] for run in all_outputs) for k in range(N_CLASSES)] for i in range(len(all_outputs[0]))]


def write(path: Path, truth: list[int], outputs: list[list[float]]) -> None:
    with path.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([f"zeta_{k}" for k in range(N_CLASSES)] + [f"prediction_{k}" for k in range(N_CLASSES)])
        for label, output in zip(truth, outputs):
            writer.writerow([int(k == label) for k in range(N_CLASSES)] + [f"{value:.6f}" for value in output])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("predictions", type=Path, nargs="+")
    parser.add_argument("--write", type=Path, help="save the ensemble as a predictions.csv (zeta_k, prediction_k) to chart it like a run")
    args = parser.parse_args()
    loaded = [load(path) for path in args.predictions]
    truth = loaded[0][0]
    if any(t != truth for t, _ in loaded):
        raise SystemExit("the runs are not on the same samples")
    accuracies = [accuracy(truth, outputs) for _, outputs in loaded]
    print(f"{len(loaded)} redes: accuracy individual media {100 * statistics.fmean(accuracies):.2f} % "
          f"(mín {100 * min(accuracies):.2f}, máx {100 * max(accuracies):.2f})")
    ensemble = average([o for _, o in loaded])
    print(f"ensemble (promedio de las salidas): {100 * accuracy(truth, ensemble):.2f} %")
    if args.write:
        write(args.write, truth, ensemble)


if __name__ == "__main__":
    main()
