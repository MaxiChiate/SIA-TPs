"""Generalization metrics and detection threshold for the fraud TinyModel (stdlib only).

Reads the predictions.csv of runs on the validation and test parts (zeta = BigModel probability,
prediction = TinyModel probability) and the matching flagged_fraud labels. The threshold is chosen on
validation: the highest one (rounded down to 0.01) that still reaches --min-recall, so the most precision at that recall. Test is
read only to report that threshold, never to choose it.

    python3 analysis/fraud_threshold.py --validation <run>/predictions.csv --validation-labels data/x_validation_labels.csv \\
        --test <run>/predictions.csv --test-labels data/x_test_labels.csv
"""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path

BIG_MODEL_THRESHOLD = 0.85  # where flagged_fraud and BigModel's probability separate exactly


@dataclass(frozen=True)
class Scored:
    truth: list[float]  # BigModel probability
    prediction: list[float]  # TinyModel probability
    label: list[int]  # flagged_fraud


@dataclass(frozen=True)
class Counts:
    tp: int
    fp: int
    fn: int
    tn: int

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else 1.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else 1.0

    @property
    def f1(self) -> float:
        total = self.precision + self.recall
        return 2 * self.precision * self.recall / total if total else 0.0


def load(predictions: Path, labels: Path) -> Scored:
    with predictions.open(newline="") as file:
        rows = list(csv.DictReader(file))
    with labels.open(newline="") as file:
        flags = [int(float(row["flagged_fraud"])) for row in csv.DictReader(file)]
    if len(rows) != len(flags):
        raise ValueError(f"{predictions} has {len(rows)} rows but {labels} has {len(flags)}")
    return Scored([float(r["zeta"]) for r in rows], [float(r["prediction"]) for r in rows], flags)


def counts_at(scored: Scored, threshold: float) -> Counts:
    tp = fp = fn = tn = 0
    for prediction, label in zip(scored.prediction, scored.label):
        flagged = prediction >= threshold
        tp += flagged and label == 1
        fp += flagged and label == 0
        fn += (not flagged) and label == 1
        tn += (not flagged) and label == 0
    return Counts(tp, fp, fn, tn)


def average_precision(scored: Scored) -> float:
    """Area under the precision-recall curve (step-wise), highest scores first."""
    order = sorted(range(len(scored.label)), key=lambda i: -scored.prediction[i])
    positives = sum(scored.label)
    hits = area = 0.0
    for rank, i in enumerate(order, start=1):
        if scored.label[i] == 1:
            hits += 1
            area += hits / rank
    return area / positives


def regression_errors(scored: Scored) -> tuple[float, float]:
    errors = [p - t for p, t in zip(scored.prediction, scored.truth)]
    return sum(e * e for e in errors) / len(errors), sum(abs(e) for e in errors) / len(errors)


def choose_threshold(scored: Scored, min_recall: float, step: float = 0.01) -> float:
    """The highest threshold that reaches min_recall, rounded down to a multiple of step.

    Rounding down only adds flagged samples, so recall can't drop below min_recall."""
    candidates = sorted(set(scored.prediction), reverse=True)
    best = candidates[-1]
    for threshold in candidates:
        if counts_at(scored, threshold).recall >= min_recall:
            best = threshold
            break
    return math.floor(best / step + 1e-9) * step


def report(name: str, scored: Scored, threshold: float) -> None:
    mse, mae = regression_errors(scored)
    counts = counts_at(scored, threshold)
    print(f"\n{name}: n={len(scored.label)}  MSE={mse:.5f}  MAE={mae:.4f}  PR-AUC={average_precision(scored):.4f}")
    print(f"  umbral {threshold:.4f}: precisión {counts.precision:.3f}  recall {counts.recall:.3f}  F1 {counts.f1:.3f}"
          f"  (TP {counts.tp}, FP {counts.fp}, FN {counts.fn}, TN {counts.tn})")


def sweep(scored: Scored) -> None:
    print("\numbral   precisión  recall   F1      FP    FN")
    for threshold in (0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9):
        c = counts_at(scored, threshold)
        print(f"{threshold:.2f}     {c.precision:.3f}      {c.recall:.3f}    {c.f1:.3f}   {c.fp:4d}  {c.fn:4d}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--validation-labels", type=Path, required=True)
    parser.add_argument("--test", type=Path)
    parser.add_argument("--test-labels", type=Path)
    parser.add_argument("--min-recall", type=float, default=0.95)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validation = load(args.validation, args.validation_labels)
    threshold = choose_threshold(validation, args.min_recall)
    print(f"umbral elegido en validación (recall mínimo {args.min_recall}): {threshold:.4f}")
    report("validación", validation, threshold)
    sweep(validation)
    if args.test and args.test_labels:
        test = load(args.test, args.test_labels)
        report("test", test, threshold)
        print("\nreferencia: BigModel en el umbral 0.85 separa exacto a flagged_fraud (precisión 1, recall 1)")


if __name__ == "__main__":
    main()
