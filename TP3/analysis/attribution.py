"""Attribution: which inputs a trained model leaned on for a prediction (stdlib only).

Forward and backward in Python on the weights of model.py: the same backprop as network.c, one layer further down
to the inputs (δ_input = Wᵀ · δ_first_hidden; weight 0 is the bias, input fixed at 1). For an ensemble the gradient
of the average is the average of the gradients. The target is the class the model predicts (its highest output O_k).

    saliency     ∂O_k/∂x_i
    grad_input   x_i · ∂O_k/∂x_i (zero wherever the input is zero)
    integrated   integrated gradients from an all-zero baseline: (x_i − 0) · mean of ∂O_k/∂x_i along the straight path
    occlusion    how much O_k drops when a group of inputs is set to zero: 4×4 patches with --input-shape, else one input

Knows nothing about images: the output is a vector per sample, attributions.csv
(model, sample, true, predicted, method, a1..a<n_inputs>); --input-shape is only used to group the occlusion.

    python3 analysis/attribution.py --models ex3_ensemble --dataset data/digits_test_prepared.csv --self-check
    python3 analysis/attribution.py --models ex2_single ex3_ensemble --dataset data/digits_test_prepared.csv \\
        --samples per-class:1 --methods saliency grad_input integrated occlusion --input-shape 28x28

--samples: indices ("0 5 17"), per-class:N (the first N samples of each true class) or errors:N (the first N the
model gets wrong; per model). --self-check compares the Python forward with the C and the analytic gradient with
finite differences, and checks that integrated gradients add up to O_k(x) − O_k(0); run it before reading any map.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

ANALYSIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ANALYSIS_DIR))
from model import ACTIVATIONS, Model, Run, argmax, evaluate_runs, forward, load_dataset, load_model, resolve_dataset  # noqa: E402

MODELS_DIR = ANALYSIS_DIR / "models"
RESULTS_DIR = ANALYSIS_DIR / "results"
METHODS = ["saliency", "grad_input", "integrated", "occlusion"]
CHECK_SEED = 1  # which pixels the finite-difference check probes


# ---------- one network, fast on sparse inputs ----------

class Network:
    """A run's weights laid out for attribution: the first layer by input (a column per input), so the forward only
    touches the inputs that aren't zero and the gradient can be asked for only some inputs."""

    def __init__(self, run: Run) -> None:
        self.theta, self.theta_prime = ACTIVATIONS[run.activation]
        first = run.layers[0]
        self.n_inputs = run.n_inputs
        self.first_bias = [weights[0] for weights in first]
        self.columns = [[weights[i + 1] for weights in first] for i in range(self.n_inputs)]
        self.rest = run.layers[1:]

    def forward(self, x: list[float]) -> tuple[list[list[float]], list[list[float]]]:
        """h and V of every layer from the first hidden one on (V[-1] is the output)."""
        h = list(self.first_bias)
        for value, column in zip(x, self.columns):
            if value:
                h = [a + value * w for a, w in zip(h, column)]
        hs, vs = [h], [[self.theta(a) for a in h]]
        for layer in self.rest:
            h = [weights[0] + sum(w * v for w, v in zip(weights[1:], vs[-1])) for weights in layer]
            hs.append(h)
            vs.append([self.theta(a) for a in h])
        return hs, vs

    def output(self, x: list[float]) -> list[float]:
        return self.forward(x)[1][-1]

    def gradient(self, x: list[float], k: int, inputs: list[int]) -> tuple[float, dict[int, float]]:
        """O_k and ∂O_k/∂x_i for the given inputs. δ as in network.c, with ∂O_k/∂h instead of the error."""
        hs, vs = self.forward(x)
        delta = [self.theta_prime(h) if j == k else 0.0 for j, h in enumerate(hs[-1])]
        for layer, h in zip(reversed(self.rest), reversed(hs[:-1])):
            back = [sum(weights[i + 1] * d for weights, d in zip(layer, delta)) for i in range(len(h))]
            delta = [b * self.theta_prime(a) for b, a in zip(back, h)]
        return vs[-1][k], {i: sum(w * d for w, d in zip(self.columns[i], delta)) for i in inputs}


# ---------- the model: the average of its networks ----------

@dataclass(frozen=True)
class Explainer:
    networks: list[Network]

    @property
    def n_inputs(self) -> int:
        return self.networks[0].n_inputs

    def output(self, x: list[float]) -> list[float]:
        outputs = [network.output(x) for network in self.networks]
        return [statistics.fmean(values) for values in zip(*outputs)]

    def gradient(self, x: list[float], k: int, inputs: list[int]) -> tuple[float, dict[int, float]]:
        results = [network.gradient(x, k, inputs) for network in self.networks]
        return (statistics.fmean(o for o, _ in results),
                {i: statistics.fmean(g[i] for _, g in results) for i in inputs})


def nonzero(x: list[float]) -> list[int]:
    return [i for i, value in enumerate(x) if value]


def saliency(explainer: Explainer, x: list[float], k: int, _: argparse.Namespace) -> list[float]:
    _, grad = explainer.gradient(x, k, list(range(len(x))))
    return [grad[i] for i in range(len(x))]


def grad_input(explainer: Explainer, x: list[float], k: int, _: argparse.Namespace) -> list[float]:
    _, grad = explainer.gradient(x, k, nonzero(x))
    return [x[i] * grad.get(i, 0.0) for i in range(len(x))]


def integrated(explainer: Explainer, x: list[float], k: int, args: argparse.Namespace) -> list[float]:
    """Midpoint rule over `steps` points of the path α·x, α in (0, 1); the baseline is all zeros."""
    active = nonzero(x)
    total = dict.fromkeys(active, 0.0)
    for step in range(args.steps):
        alpha = (step + 0.5) / args.steps
        _, grad = explainer.gradient([alpha * value for value in x], k, active)
        for i in active:
            total[i] += grad[i]
    return [x[i] * total.get(i, 0.0) / args.steps for i in range(len(x))]


def groups(n_inputs: int, shape: tuple[int, int] | None, patch: int) -> list[list[int]]:
    if shape is None:
        return [[i] for i in range(n_inputs)]
    rows, cols = shape
    return [[r * cols + c for r in range(top, min(top + patch, rows)) for c in range(left, min(left + patch, cols))]
            for top in range(0, rows, patch) for left in range(0, cols, patch)]


def occlusion(explainer: Explainer, x: list[float], k: int, args: argparse.Namespace) -> list[float]:
    """O_k(x) − O_k(x with the group at zero), the same value on every input of the group. A group that is
    already zero changes nothing, so it isn't evaluated."""
    base = explainer.output(x)[k]
    out = [0.0] * len(x)
    for group in groups(len(x), args.shape, args.patch):
        if not any(x[i] for i in group):
            continue
        occluded = list(x)
        for i in group:
            occluded[i] = 0.0
        drop = base - explainer.output(occluded)[k]
        for i in group:
            out[i] = drop
    return out


ATTRIBUTIONS: dict[str, Callable[[Explainer, list[float], int, argparse.Namespace], list[float]]] = {
    "saliency": saliency, "grad_input": grad_input, "integrated": integrated, "occlusion": occlusion}


# ---------- samples ----------

def select(spec: list[str], zetas: list[list[float]], predicted: list[int]) -> list[int]:
    if len(spec) == 1 and spec[0].startswith("per-class:"):
        n = int(spec[0].removeprefix("per-class:"))
        chosen: dict[int, list[int]] = {}
        for index, zeta in enumerate(zetas):
            bucket = chosen.setdefault(argmax(zeta), [])
            if len(bucket) < n:
                bucket.append(index)
        return sorted(i for bucket in chosen.values() for i in bucket)
    if len(spec) == 1 and spec[0].startswith("errors:"):
        n = int(spec[0].removeprefix("errors:"))
        return [i for i, zeta in enumerate(zetas) if argmax(zeta) != predicted[i]][:n]
    return [int(value) for value in spec]


def c_predictions(model: Model, dataset: Path) -> list[list[float]]:
    runs = evaluate_runs(model, dataset)
    return [[statistics.fmean(values) for values in zip(*rows)] for rows in zip(*(r.outputs for r in runs))]


# ---------- self-check ----------

def self_check(name: str, model: Model, explainer: Explainer, inputs: list[list[float]], c_outputs: list[list[float]],
               samples: list[int], args: argparse.Namespace) -> bool:
    ok = True
    # (1) the fast forward against model.forward and against the C (predictions.csv keeps 10 significant digits)
    worst_c = max(abs(a - b) for i in samples for a, b in zip(explainer.output(inputs[i]), c_outputs[i]))
    worst_py = max(abs(a - b) for i in samples[:2] for run, network in zip(model.runs, explainer.networks)
                   for a, b in zip(network.output(inputs[i]), forward(run, inputs[i])[1][-1]))
    print(f"{name}: forward contra el C max |Δ| {worst_c:.2g}, contra model.forward {worst_py:.2g}")
    ok &= worst_c < 1e-8 and worst_py < 1e-12

    # (2) the analytic gradient against central differences, on a few inputs of each sample (some zero, some not)
    rng = random.Random(CHECK_SEED)
    worst = 0.0
    for i in samples[:3]:
        x = inputs[i]
        k = argmax(explainer.output(x))
        probe = rng.sample(nonzero(x), 3) + rng.sample([j for j in range(len(x)) if not x[j]], 2)
        _, grad = explainer.gradient(x, k, probe)
        for j in probe:
            eps = 1e-5
            up, down = list(x), list(x)
            up[j] += eps
            down[j] -= eps
            numeric = (explainer.output(up)[k] - explainer.output(down)[k]) / (2 * eps)
            worst = max(worst, abs(numeric - grad[j]) / max(1e-6, abs(numeric) + abs(grad[j])))
    print(f"{name}: gradiente analítico contra diferencias finitas, error relativo máx {worst:.2g}")
    ok &= worst < 1e-4

    # (3) completeness of integrated gradients: Σ attributions = O_k(x) − O_k(0), up to the quadrature error
    for i in samples[:2]:
        x = inputs[i]
        k = argmax(explainer.output(x))
        total = sum(integrated(explainer, x, k, args))
        expected = explainer.output(x)[k] - explainer.output([0.0] * len(x))[k]
        print(f"{name}: muestra {i}, Σ integrated gradients {total:.4f} contra O_k(x) − O_k(0) {expected:.4f}")
        ok &= abs(total - expected) < 0.05 * max(abs(expected), 0.05)
    return ok


# ---------- main ----------

def model_path(name: str) -> Path:
    path = Path(name)
    return path if path.suffix == ".json" else MODELS_DIR / f"{name}.json"


def parse_shape(text: str | None) -> tuple[int, int] | None:
    if text is None:
        return None
    rows, cols = text.lower().split("x")
    return int(rows), int(cols)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", nargs="+", required=True, help="names in analysis/models/ or paths to model JSONs")
    parser.add_argument("--dataset", required=True, help="prepared CSV; relative paths also resolve from neuron/")
    parser.add_argument("--samples", nargs="+", default=["per-class:1"], help='indices, "per-class:N" or "errors:N" (default per-class:1)')
    parser.add_argument("--methods", nargs="+", choices=METHODS, default=METHODS)
    parser.add_argument("--input-shape", help='e.g. "28x28": occlusion by patches; without it, one input at a time')
    parser.add_argument("--patch", type=int, default=4, help="occlusion patch side (default 4)")
    parser.add_argument("--steps", type=int, default=50, help="integrated gradients steps (default 50)")
    parser.add_argument("--self-check", action="store_true", help="only run the checks; exit 1 if one fails")
    parser.add_argument("--name", help="what this set of maps is for, in the output directory: attribution_<name>_<date>_<time>")
    parser.add_argument("--out", type=Path, help="output directory (default: analysis/results/attribution[_<name>]_<date>_<time>/)")
    args = parser.parse_args()
    args.shape = parse_shape(args.input_shape)

    dataset = resolve_dataset(args.dataset)
    inputs, zetas = load_dataset(dataset)
    models = {model_path(name).stem: load_model(model_path(name)) for name in args.models}

    if args.self_check:
        ok = True
        for name, model in models.items():
            outputs = c_predictions(model, dataset)
            samples = select(args.samples, zetas, [argmax(o) for o in outputs])[:5]
            ok &= self_check(name, model, Explainer([Network(run) for run in model.runs]), inputs, outputs, samples, args)
        print("self-check: " + ("ok" if ok else "FALLÓ"))
        raise SystemExit(0 if ok else 1)

    prefix = f"attribution_{args.name}" if args.name else "attribution"
    out = args.out or RESULTS_DIR / f"{prefix}_{time.strftime('%Y-%m-%d_%H-%M-%S')}"
    out.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with (out / "attributions.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["model", "sample", "true", "predicted", "method"] + [f"a{i + 1}" for i in range(len(inputs[0]))])
        for name, model in models.items():
            explainer = Explainer([Network(run) for run in model.runs])
            predicted = [argmax(o) for o in c_predictions(model, dataset)]
            samples = select(args.samples, zetas, predicted)
            for done, i in enumerate(samples, start=1):
                k = argmax(explainer.output(inputs[i]))
                for method in args.methods:
                    values = ATTRIBUTIONS[method](explainer, inputs[i], k, args)
                    writer.writerow([name, i, argmax(zetas[i]), k, method] + [f"{v:.6g}" for v in values])
                print(f"{name}: {done}/{len(samples)} muestras, {time.monotonic() - started:.0f}s", file=sys.stderr)
    (out / "run.json").write_text(json.dumps({"models": list(models), "dataset": str(dataset), "samples": args.samples,
                                              "methods": args.methods, "input_shape": args.input_shape, "patch": args.patch,
                                              "steps": args.steps}, indent=2) + "\n")
    print(f"attribution -> {out}")


if __name__ == "__main__":
    main()
