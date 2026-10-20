"""Accuracy of an ensemble of digit networks: the average of their 10 outputs (stdlib only).

Takes the predictions.csv of several runs on the same set (same sample order, so same dataset and the
runs differ in seed or in training), or a model of analysis/models/ evaluated on a dataset. Prints each
run's accuracy and the ensemble's. The averaging lives in model.py.

    python3 analysis/digits_ensemble.py <run>/predictions.csv <run>/predictions.csv ...
    python3 analysis/digits_ensemble.py --model analysis/models/ex3_ensemble.json --dataset data/ex3_base_test.csv
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from model import Predictions, accuracy, average, argmax, evaluate_runs, load_model, load_predictions, resolve_dataset  # noqa: E402


def write(path: Path, predictions: Predictions) -> None:
    n_outputs = len(predictions.zetas[0])
    with path.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([f"zeta_{k}" for k in range(n_outputs)] + [f"prediction_{k}" for k in range(n_outputs)])
        for zeta, output in zip(predictions.zetas, predictions.outputs):
            label = argmax(zeta)
            writer.writerow([int(k == label) for k in range(n_outputs)] + [f"{value:.6f}" for value in output])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("predictions", type=Path, nargs="*")
    parser.add_argument("--model", type=Path, help="a model of analysis/models/, evaluated with the binary (epochs 0)")
    parser.add_argument("--dataset", help="with --model: the prepared CSV to evaluate on")
    parser.add_argument("--write", type=Path, help="save the ensemble as a predictions.csv (zeta_k, prediction_k) to chart it like a run")
    args = parser.parse_args()
    if bool(args.model) == bool(args.predictions) or bool(args.model) != bool(args.dataset):
        parser.error("either predictions.csv files, or --model with --dataset")

    if args.model:
        loaded = evaluate_runs(load_model(args.model), resolve_dataset(args.dataset))
    else:
        loaded = [load_predictions(path) for path in args.predictions]
    accuracies = [accuracy(predictions) for predictions in loaded]
    print(f"{len(loaded)} redes: accuracy individual media {100 * statistics.fmean(accuracies):.2f} % "
          f"(mín {100 * min(accuracies):.2f}, máx {100 * max(accuracies):.2f})")
    ensemble = average(loaded)
    print(f"ensemble (promedio de las salidas): {100 * accuracy(ensemble):.2f} %")
    if args.write:
        write(args.write, ensemble)


if __name__ == "__main__":
    main()
