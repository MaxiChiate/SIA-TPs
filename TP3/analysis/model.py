"""A trained model: one network or an ensemble of them, read from the runs of a series (stdlib only).

A model is a small JSON in analysis/models/ (the only piece that depends on the exercise):

    {"label": "Ej. 3 — ensemble de 9", "runs": ["series_ex3_final/000_a2-512_seed1", ...]}

Each run is <series>/<run>: the run directory inside the latest results/<series>_<date>_<time>/ that has it, so the
JSON keeps working when a series is run again. A path to a run directory also works. One network is an ensemble of
one: the model's output is the average of its networks' outputs. Nothing here knows about digits: inputs are the x*
columns of a prepared CSV, outputs its zeta* columns.

    predict(model, inputs)      forward in Python (few samples: attribution)
    evaluate(model, dataset)    the C binary with epochs 0, once per run (whole datasets: robustness)

As a script, checks a model against the C on a dataset (the same check the attribution relies on):

    python3 analysis/model.py analysis/models/ex3_ensemble.json --dataset data/ex3_base_test.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics
import subprocess
import tempfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

ANALYSIS_DIR = Path(__file__).resolve().parent
TP_DIR = ANALYSIS_DIR.parent
NEURON_DIR = TP_DIR / "neuron"
BINARY = NEURON_DIR / "build" / "neuron"
RESULTS_DIR = ANALYSIS_DIR / "results"


def _logistic(h: float) -> float:
    # Same split as activation.c, so a very negative h doesn't overflow exp
    if h >= 0:
        return 1.0 / (1.0 + math.exp(-h))
    e = math.exp(h)
    return e / (1.0 + e)


# theta and theta' of each activation, as in neuron/activation/activation.c
ACTIVATIONS: dict[str, tuple[Callable[[float], float], Callable[[float], float]]] = {
    "sign": (lambda h: 1.0 if h >= 0 else -1.0, lambda h: 1.0),
    "lineal": (lambda h: h, lambda h: 1.0),
    "tanh": (math.tanh, lambda h: 1.0 - math.tanh(h) ** 2),
    "logistic": (_logistic, lambda h: _logistic(h) * (1.0 - _logistic(h))),
    "relu": (lambda h: h if h > 0 else 0.0, lambda h: 1.0 if h > 0 else 0.0),
}


@dataclass(frozen=True)
class Run:
    path: Path
    activation: str
    hidden_layers: list[int]
    layers: list[list[list[float]]]  # layer -> neuron -> weights; weight 0 is the bias (input fixed at 1)

    @property
    def n_inputs(self) -> int:
        return len(self.layers[0][0]) - 1


@dataclass(frozen=True)
class Model:
    label: str
    runs: list[Run]


@dataclass(frozen=True)
class Predictions:
    zetas: list[list[float]]    # sample -> expected outputs
    outputs: list[list[float]]  # sample -> network outputs


# ---------- loading ----------

def resolve_run(name: str) -> Path:
    """<series>/<run> -> that run in the latest results/<series>_<date>_<time>/ that has its weights."""
    direct = Path(name) if Path(name).is_absolute() else ANALYSIS_DIR / name
    if (direct / "weights.csv").exists():
        return direct
    series, run = name.split("/", 1)
    candidates = sorted(RESULTS_DIR.glob(f"{series}_????-??-??_??-??-??/runs/{run}/weights.csv"), reverse=True)
    if not candidates:
        raise SystemExit(f"run {name}: no results/{series}_<date>/runs/{run}/weights.csv; run the series again")
    return candidates[0].parent


def load_weights(path: Path) -> list[list[list[float]]]:
    layers: list[list[list[float]]] = []
    with (path / "weights.csv").open(newline="") as file:
        for row in csv.DictReader(file):
            layer, neuron = int(row["layer"]), int(row["neuron"])
            if layer > len(layers):
                layers.append([])
            if neuron > len(layers[-1]):
                layers[-1].append([])
            layers[-1][-1].append(float(row["final"]))
    return layers


def load_run(name: str) -> Run:
    path = resolve_run(name)
    config = json.loads((path / "config.json").read_text())
    layers = load_weights(path)
    if [len(layer) for layer in layers[:-1]] != list(config["hidden_layers"]):
        raise SystemExit(f"{path}: weights.csv doesn't match hidden_layers {config['hidden_layers']}")
    return Run(path, config["activation"], list(config["hidden_layers"]), layers)


def load_model(path: Path) -> Model:
    spec = json.loads(path.read_text())
    runs = [load_run(name) for name in spec["runs"]]
    if len({(run.n_inputs, len(run.layers[-1])) for run in runs}) != 1:
        raise SystemExit(f"{path}: the runs don't share inputs and outputs, so they can't be averaged")
    return Model(spec.get("label", path.stem), runs)


def resolve_dataset(name: str) -> Path:
    """As given if it exists, else relative to neuron/ (where data/ lives)."""
    path = Path(name)
    return path.resolve() if path.exists() else NEURON_DIR / name


def output_columns(header: list[str]) -> list[int]:
    """The zeta* columns at the end of the header, as io/dataset.c reads them (none: just the last one)."""
    n = 0
    while n < len(header) and header[len(header) - 1 - n].startswith("zeta"):
        n += 1
    return list(range(len(header) - max(n, 1), len(header)))


def load_dataset(path: Path) -> tuple[list[list[float]], list[list[float]]]:
    """A prepared CSV -> (inputs, zetas)."""
    with path.open(newline="") as file:
        reader = csv.reader(file)
        outputs = output_columns(next(reader))
        first = outputs[0]
        rows = [[float(value) for value in row] for row in reader]
    return [row[:first] for row in rows], [row[first:] for row in rows]


def load_predictions(path: Path) -> Predictions:
    """A run's predictions.csv: zeta*/prediction* columns (or zeta/prediction with one output)."""
    with path.open(newline="") as file:
        reader = csv.reader(file)
        header = next(reader)
        zetas = [i for i, name in enumerate(header) if name == "zeta" or name.startswith("zeta_")]
        outputs = [i for i, name in enumerate(header) if name == "prediction" or name.startswith("prediction_")]
        rows = list(reader)
    return Predictions([[float(row[i]) for i in zetas] for row in rows], [[float(row[i]) for i in outputs] for row in rows])


# ---------- the ensemble ----------

def argmax(values: list[float]) -> int:
    return max(range(len(values)), key=values.__getitem__)


def accuracy(predictions: Predictions) -> float:
    """Classes by argmax: the highest output against the highest zeta."""
    hits = sum(argmax(o) == argmax(z) for z, o in zip(predictions.zetas, predictions.outputs))
    return hits / len(predictions.zetas)


def average(all_predictions: list[Predictions]) -> Predictions:
    """The ensemble: the mean of each output over the networks. They must be on the same samples."""
    zetas = all_predictions[0].zetas
    if any(p.zetas != zetas for p in all_predictions):
        raise SystemExit("the runs are not on the same samples")
    runs = [p.outputs for p in all_predictions]
    n_outputs = len(runs[0][0])
    return Predictions(zetas, [[statistics.fmean(run[i][k] for run in runs) for k in range(n_outputs)] for i in range(len(zetas))])


# ---------- forward in Python ----------

def forward(run: Run, inputs: list[float]) -> tuple[list[list[float]], list[list[float]]]:
    """Every layer's h and V (V[0] = inputs), as network.c computes them."""
    theta = ACTIVATIONS[run.activation][0]
    hs: list[list[float]] = [[]]
    vs: list[list[float]] = [inputs]
    for layer in run.layers:
        previous = vs[-1]
        h = [weights[0] + sum(w * v for w, v in zip(weights[1:], previous)) for weights in layer]
        hs.append(h)
        vs.append([theta(value) for value in h])
    return hs, vs


def predict(model: Model, inputs: list[float]) -> list[float]:
    outputs = [forward(run, inputs)[1][-1] for run in model.runs]
    return [statistics.fmean(run[k] for run in outputs) for k in range(len(outputs[0]))]


# ---------- evaluation in C (epochs 0) ----------

def evaluate_run(run: Run, dataset: Path) -> Predictions:
    """The binary in evaluation mode, in a temporary directory: its results/ goes away with it."""
    with tempfile.TemporaryDirectory() as workdir:
        config = {"train_dataset": str(dataset), "validation_dataset": str(dataset), "activation": run.activation,
                  "eta": 1, "epochs": 0, "batch_size": 1, "hidden_layers": run.hidden_layers, "seed": 1,
                  "initial_weights": str(run.path)}
        config_path = Path(workdir) / "config.json"
        config_path.write_text(json.dumps(config))
        out = subprocess.run([str(BINARY), str(config_path)], cwd=workdir, check=True, capture_output=True, text=True).stdout
        run_dir = Path(workdir) / out.strip().splitlines()[-1].removeprefix("results -> ")
        return load_predictions(run_dir / "predictions.csv")


def evaluate_runs(model: Model, dataset: Path) -> list[Predictions]:
    """Each network on the whole dataset, in parallel."""
    if not BINARY.exists():
        raise SystemExit(f"{BINARY} doesn't exist: cd neuron && make")
    with ThreadPoolExecutor(max_workers=os.cpu_count()) as pool:
        return list(pool.map(lambda run: evaluate_run(run, dataset), model.runs))


def evaluate(model: Model, dataset: Path) -> Predictions:
    return average(evaluate_runs(model, dataset))


def evaluate_models(models: list[Model], dataset: Path) -> list[Predictions]:
    """Several models on one dataset, each network evaluated once even if several models share it
    (a single network is usually one of an ensemble's)."""
    unique = list({run.path: run for model in models for run in model.runs}.values())
    by_path = dict(zip((run.path for run in unique), evaluate_runs(Model("", unique), dataset)))
    return [average([by_path[run.path] for run in model.runs]) for model in models]


# ---------- check ----------

def max_difference(a: list[list[float]], b: list[list[float]]) -> float:
    return max(abs(x - y) for row_a, row_b in zip(a, b) for x, y in zip(row_a, row_b))


def same_dataset(run: Run, dataset: Path) -> bool:
    config = json.loads((run.path / "config.json").read_text())
    validation = config.get("validation_dataset", "")
    return validation != "" and resolve_dataset(validation).resolve() == dataset.resolve()


def check(model: Model, dataset: Path, n_python: int) -> None:
    """(1) the C in evaluation mode against each run's own predictions.csv, when it was on this dataset;
    (2) the forward in Python against the C on the first n_python samples."""
    evaluated = evaluate_runs(model, dataset)
    for run, predictions in zip(model.runs, evaluated):
        line = f"{run.path.name}: accuracy {100 * accuracy(predictions):.2f} %"
        if same_dataset(run, dataset):
            line += f", against its predictions.csv max |Δ| {max_difference(predictions.outputs, load_predictions(run.path / 'predictions.csv').outputs):.3g}"
        print(line)
    ensemble = average(evaluated)
    print(f"{model.label}: {len(model.runs)} redes, accuracy {100 * accuracy(ensemble):.2f} %")

    inputs, _ = load_dataset(dataset)
    python = [predict(model, x) for x in inputs[:n_python]]
    print(f"forward en Python contra el C ({n_python} muestras): max |Δ| {max_difference(python, ensemble.outputs[:n_python]):.3g}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("model", type=Path, help="analysis/models/<name>.json")
    parser.add_argument("--dataset", required=True, help="prepared CSV; relative paths also resolve from neuron/")
    parser.add_argument("--python-samples", type=int, default=5, help="samples for the Python forward check (default 5)")
    args = parser.parse_args()
    check(load_model(args.model), resolve_dataset(args.dataset), args.python_samples)


if __name__ == "__main__":
    main()
