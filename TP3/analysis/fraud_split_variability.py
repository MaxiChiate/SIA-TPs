"""How much does the fraud threshold depend on the train/validation/test split? (stdlib only)

For each split seed: writes a stratified 70/15/15 split (scripts/prepare_fraud_split.py), trains the final
TinyModel (logistic, 6 inputs), picks the threshold on validation for --min-recall, and scores it on test.
The network's own seed stays fixed, so the only thing that moves is the split.

    python3 analysis/fraud_split_variability.py --seeds 1 2 3 4 5 6 7 8 9 10
"""

from __future__ import annotations

import argparse
import json
import shutil
import statistics
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ANALYSIS_DIR = Path(__file__).resolve().parent
TP_DIR = ANALYSIS_DIR.parent
NEURON_DIR = TP_DIR / "neuron"
BINARY = NEURON_DIR / "build" / "neuron"
DROPPED = ["timestamp", "device_screen_resolution", "time_since_last_login_s"]

sys.path.insert(0, str(ANALYSIS_DIR))
from fraud_threshold import choose_threshold, counts_at, load  # noqa: E402


@dataclass(frozen=True)
class SplitResult:
    seed: int
    threshold: float
    validation_precision: float
    validation_recall: float
    test_precision: float
    test_recall: float
    test_frauds: int
    test_by_threshold: dict[float, tuple[float, float]]  # fixed thresholds -> (precision, recall) on test


def prepare_split(split_seed: int, name: str) -> None:
    command = [sys.executable, str(TP_DIR / "scripts" / "prepare_fraud_split.py"), "--seed", str(split_seed), "--name", name, "--drop", *DROPPED]
    subprocess.run(command, check=True, capture_output=True, text=True)


def predictions_of(name: str, part: str, workdir: Path, seed: int, eta: float, epochs: int) -> Path:
    config = {"train_dataset": f"data/{name}_train.csv", "validation_dataset": f"data/{name}_{part}.csv", "activation": "logistic",
              "eta": eta, "epochs": epochs, "batch_size": 1, "shuffle": True, "hidden_layers": [], "seed": seed}
    config_path = workdir / f"{name}_{part}.json"
    config_path.write_text(json.dumps(config))
    out = subprocess.run([str(BINARY), str(config_path)], cwd=NEURON_DIR, check=True, capture_output=True, text=True).stdout
    run_dir = NEURON_DIR / out.strip().splitlines()[-1].removeprefix("results -> ")
    kept = workdir / f"{name}_{part}_predictions.csv"
    shutil.copy(run_dir / "predictions.csv", kept)
    shutil.rmtree(run_dir)
    return kept


def evaluate(split_seed: int, workdir: Path, min_recall: float, seed: int, eta: float, epochs: int, fixed: list[float]) -> SplitResult:
    name = f"fraud_split{split_seed}"
    prepare_split(split_seed, name)
    labels = lambda part: NEURON_DIR / "data" / f"{name}_{part}_labels.csv"
    validation = load(predictions_of(name, "validation", workdir, seed, eta, epochs), labels("validation"))
    test = load(predictions_of(name, "test", workdir, seed, eta, epochs), labels("test"))
    threshold = choose_threshold(validation, min_recall)
    on_validation, on_test = counts_at(validation, threshold), counts_at(test, threshold)
    by_threshold = {t: (counts_at(test, t).precision, counts_at(test, t).recall) for t in fixed}
    return SplitResult(split_seed, threshold, on_validation.precision, on_validation.recall, on_test.precision, on_test.recall,
                       on_test.tp + on_test.fn, by_threshold)


def summary(label: str, values: list[float]) -> str:
    return f"{label}: media {statistics.fmean(values):.3f}  desvío {statistics.pstdev(values):.3f}  rango [{min(values):.3f}, {max(values):.3f}]"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seeds", type=int, nargs="+", required=True, help="split seeds")
    parser.add_argument("--fixed", type=float, nargs="*", default=[], help="fixed thresholds to score on every split's test")
    parser.add_argument("--min-recall", type=float, default=0.95)
    parser.add_argument("--seed", type=int, default=1, help="the network's seed")
    parser.add_argument("--eta", type=float, default=0.01)
    parser.add_argument("--epochs", type=int, default=200)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with tempfile.TemporaryDirectory() as directory:
        results = [evaluate(s, Path(directory), args.min_recall, args.seed, args.eta, args.epochs, args.fixed) for s in args.seeds]
    print("split  umbral  val P / R        test P / R       fraudes en test")
    for r in results:
        print(f"{r.seed:5d}  {r.threshold:.2f}    {r.validation_precision:.3f} / {r.validation_recall:.3f}  {r.test_precision:.3f} / {r.test_recall:.3f}   {r.test_frauds}")
    print()
    print(summary("umbral", [r.threshold for r in results]))
    print(summary("precisión en test", [r.test_precision for r in results]))
    print(summary("recall en test", [r.test_recall for r in results]))
    for threshold in args.fixed:
        precisions = [r.test_by_threshold[threshold][0] for r in results]
        recalls = [r.test_by_threshold[threshold][1] for r in results]
        under = sum(recall < args.min_recall for recall in recalls)
        print(f"umbral fijo {threshold:.2f}: precisión {statistics.fmean(precisions):.3f}, recall {statistics.fmean(recalls):.3f} (mínimo {min(recalls):.3f}), "
              f"recall bajo {args.min_recall} en {under} de {len(results)}")
    below = sum(r.test_recall < args.min_recall for r in results)
    print(f"splits donde el recall en test queda por debajo de {args.min_recall}: {below} de {len(results)}")


if __name__ == "__main__":
    main()
