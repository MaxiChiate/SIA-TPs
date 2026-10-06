"""Robustness to noise: accuracy of trained models as Gaussian noise is added to a dataset's inputs (stdlib only).

For every σ and noise seed, perturbs the dataset once (scripts/perturb_dataset.py) and evaluates every model on it
with the binary in evaluation mode (model.py; a network shared by two models runs once). Knows nothing about digits
or exercises: the models (analysis/models/*.json) and the dataset say what is measured.

    python3 analysis/robustness.py --models ex2_single ex2_ensemble ex3_single ex3_ensemble \\
        --dataset data/digits_test_prepared.csv --gaussian 0 0.05 0.1 0.2 0.3 0.5 --noise-seeds 1-10 --clip 0 1

Writes analysis/results/robustness_<date>_<time>/ (gitignored): robustness.csv, one row per model × σ × noise seed
with the accuracy and the accuracy per class (the share of each class's samples classified right), and run.json
with the arguments. σ 0 has no noise to draw, so it is evaluated once, as noise seed 0. Prints the mean ± standard
deviation over the noise seeds and, per σ, each pair of models compared with the paired permutation test (paired by
noise seed: both models saw the same noisy images).

The dataset is only measured here, never used to choose anything.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import statistics
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

ANALYSIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ANALYSIS_DIR))
sys.path.insert(0, str(ANALYSIS_DIR.parent / "scripts"))
from model import Model, Predictions, accuracy, argmax, evaluate_models, load_model, resolve_dataset  # noqa: E402
from paired_stats import permutation_p_value  # noqa: E402
from perturb_dataset import load as load_table, perturb  # noqa: E402

MODELS_DIR = ANALYSIS_DIR / "models"
RESULTS_DIR = ANALYSIS_DIR / "results"


@dataclass(frozen=True)
class Row:
    model: str
    label: str
    sigma: float
    noise_seed: int
    accuracy: float
    by_class: list[float]


def class_accuracies(predictions: Predictions) -> list[float]:
    """Per class (the highest zeta), the share of its samples whose highest output is that class."""
    n_classes = len(predictions.zetas[0])
    hits, totals = [0] * n_classes, [0] * n_classes
    for zeta, output in zip(predictions.zetas, predictions.outputs):
        label = argmax(zeta)
        totals[label] += 1
        hits[label] += argmax(output) == label
    return [hit / total if total else float("nan") for hit, total in zip(hits, totals)]


def parse_seeds(values: list[str]) -> list[int]:
    """"1-10" or "1 2 5"."""
    seeds: list[int] = []
    for value in values:
        first, _, last = value.partition("-")
        seeds += list(range(int(first), int(last or first) + 1))
    return seeds


def model_path(name: str) -> Path:
    path = Path(name)
    return path if path.suffix == ".json" else MODELS_DIR / f"{name}.json"


def conditions(sigmas: list[float], seeds: list[int]) -> list[tuple[float, int]]:
    """σ 0 once (nothing random), every other σ once per noise seed."""
    return [(sigma, 0) for sigma in sigmas if sigma == 0] + [(sigma, seed) for sigma in sigmas if sigma > 0 for seed in seeds]


def measure(models: dict[str, Model], dataset: Path, sigmas: list[float], seeds: list[int], clip: tuple[float, float] | None) -> list[Row]:
    table = load_table(dataset)
    todo = conditions(sigmas, seeds)
    rows: list[Row] = []
    started = time.monotonic()
    with tempfile.TemporaryDirectory() as workdir:
        noisy = Path(workdir) / "noisy.csv"
        for done, (sigma, seed) in enumerate(todo, start=1):
            perturb(table, noisy, seed, sigma, clip)
            for (name, model), predictions in zip(models.items(), evaluate_models(list(models.values()), noisy)):
                rows.append(Row(name, model.label, sigma, seed, accuracy(predictions), class_accuracies(predictions)))
            print(f"σ {sigma:g}, seed {seed}: {done}/{len(todo)}, {time.monotonic() - started:.0f}s", file=sys.stderr)
    return rows


def write(path: Path, rows: list[Row]) -> None:
    n_classes = len(rows[0].by_class)
    with path.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["model", "label", "sigma", "noise_seed", "accuracy"] + [f"accuracy_{k}" for k in range(n_classes)])
        for row in rows:
            writer.writerow([row.model, row.label, row.sigma, row.noise_seed, f"{row.accuracy:.6f}"] + [f"{value:.6f}" for value in row.by_class])


def summarize(rows: list[Row]) -> None:
    models = list(dict.fromkeys(row.model for row in rows))
    sigmas = sorted({row.sigma for row in rows})
    by = {(row.model, row.sigma, row.noise_seed): row.accuracy for row in rows}
    print("accuracy (%), media ± desvío entre seeds de ruido")
    print(f"{'σ':>6}  " + "  ".join(f"{name:>18}" for name in models))
    for sigma in sigmas:
        cells = []
        for name in models:
            values = [100 * value for (m, s, _), value in by.items() if m == name and s == sigma]
            spread = statistics.stdev(values) if len(values) > 1 else 0.0
            cells.append(f"{statistics.fmean(values):>9.2f} ± {spread:<6.2f}")
        print(f"{sigma:>6g}  " + "  ".join(cells))

    print("\ndiferencia pareada por seed de ruido (puntos de accuracy, primero − segundo) y p del test de permutación")
    for sigma in sigmas:
        seeds = sorted({seed for (_, s, seed) in by if s == sigma})
        if len(seeds) < 2:
            continue
        for first, second in itertools.combinations(models, 2):
            differences = [100 * (by[first, sigma, seed] - by[second, sigma, seed]) for seed in seeds]
            p_value, _ = permutation_p_value(differences)
            print(f"σ {sigma:<5g} {first} − {second}: {statistics.fmean(differences):+.2f} (p = {p_value:.3g})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", nargs="+", required=True, help="names in analysis/models/ or paths to model JSONs")
    parser.add_argument("--dataset", required=True, help="prepared CSV; relative paths also resolve from neuron/")
    parser.add_argument("--gaussian", type=float, nargs="+", required=True, metavar="SIGMA")
    parser.add_argument("--noise-seeds", nargs="+", required=True, help='e.g. "1-10" or "1 2 3"')
    parser.add_argument("--clip", type=float, nargs=2, metavar=("MIN", "MAX"), help="clamp the noisy inputs (pixels: 0 1)")
    parser.add_argument("--out", type=Path, help="output directory (default: analysis/results/robustness_<date>_<time>/)")
    args = parser.parse_args()
    if any(sigma < 0 for sigma in args.gaussian):
        parser.error("σ can't be negative")

    models = {model_path(name).stem: load_model(model_path(name)) for name in args.models}
    dataset = resolve_dataset(args.dataset)
    seeds = parse_seeds(args.noise_seeds)
    clip = tuple(args.clip) if args.clip else None
    rows = measure(models, dataset, sorted(set(args.gaussian)), seeds, clip)

    out = args.out or RESULTS_DIR / f"robustness_{time.strftime('%Y-%m-%d_%H-%M-%S')}"
    out.mkdir(parents=True, exist_ok=True)
    write(out / "robustness.csv", rows)
    (out / "run.json").write_text(json.dumps({"models": {name: [str(run.path) for run in model.runs] for name, model in models.items()},
                                              "dataset": str(dataset), "gaussian": args.gaussian, "noise_seeds": seeds,
                                              "clip": args.clip}, ensure_ascii=False, indent=2) + "\n")
    summarize(rows)
    print(f"\nrobustness -> {out}")


if __name__ == "__main__":
    main()
