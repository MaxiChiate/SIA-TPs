"""Calibration of the fraud TinyModel's probabilities against flagged_fraud (stdlib only).

The TinyModel imitates BigModel's probability, not the chance that a transaction is a fraud. This checks how
far its output is from P(fraud | output) and tries two ways of fixing it, both fit on validation and scored on
test: Platt scaling (a sigmoid of the output) and isotonic regression (a non-decreasing step function).

    python3 analysis/fraud_calibration.py --validation <run>/predictions.csv --validation-labels data/x_validation_labels.csv \\
        --test <run>/predictions.csv --test-labels data/x_test_labels.csv
"""

from __future__ import annotations

import argparse
import bisect
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from fraud_threshold import Scored, load

EPSILON = 1e-6
BINS = 10


@dataclass(frozen=True)
class Quality:
    brier: float
    log_loss: float
    ece: float


def clip(probability: float) -> float:
    return min(max(probability, EPSILON), 1 - EPSILON)


def brier(probabilities: list[float], labels: list[int]) -> float:
    return sum((p - y) ** 2 for p, y in zip(probabilities, labels)) / len(labels)


def log_loss(probabilities: list[float], labels: list[int]) -> float:
    return -sum(math.log(clip(p)) if y else math.log(1 - clip(p)) for p, y in zip(probabilities, labels)) / len(labels)


def reliability(probabilities: list[float], labels: list[int]) -> list[tuple[float, float, int]]:
    """(mean prediction, observed fraud rate, count) for each of BINS equal-width bins that has samples."""
    groups: dict[int, list[int]] = {}
    for index, p in enumerate(probabilities):
        groups.setdefault(min(int(p * BINS), BINS - 1), []).append(index)
    table = []
    for key in sorted(groups):
        members = groups[key]
        table.append((sum(probabilities[i] for i in members) / len(members), sum(labels[i] for i in members) / len(members), len(members)))
    return table


def expected_calibration_error(probabilities: list[float], labels: list[int]) -> float:
    return sum(count * abs(mean - rate) for mean, rate, count in reliability(probabilities, labels)) / len(labels)


def quality(probabilities: list[float], labels: list[int]) -> Quality:
    return Quality(brier(probabilities, labels), log_loss(probabilities, labels), expected_calibration_error(probabilities, labels))


def sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x)) if x >= 0 else math.exp(x) / (1 + math.exp(x))


def fit_platt(scores: list[float], labels: list[int], iterations: int = 50) -> tuple[float, float]:
    """Newton's method on the log loss of sigmoid(a * score + b)."""
    a, b = 1.0, 0.0
    for _ in range(iterations):
        ps = [sigmoid(a * s + b) for s in scores]
        g_a = sum((p - y) * s for p, y, s in zip(ps, labels, scores))
        g_b = sum(p - y for p, y in zip(ps, labels))
        h_aa = sum(p * (1 - p) * s * s for p, s in zip(ps, scores)) + 1e-9
        h_ab = sum(p * (1 - p) * s for p, s in zip(ps, scores))
        h_bb = sum(p * (1 - p) for p in ps) + 1e-9
        det = h_aa * h_bb - h_ab * h_ab
        if abs(det) < 1e-12:
            break
        step_a, step_b = (h_bb * g_a - h_ab * g_b) / det, (h_aa * g_b - h_ab * g_a) / det
        a, b = a - step_a, b - step_b
        if abs(step_a) + abs(step_b) < 1e-10:
            break
    return a, b


def fit_isotonic(scores: list[float], labels: list[int]) -> Callable[[float], float]:
    """Pool adjacent violators: blocks of increasing fraud rate; a score gets the rate of the block it falls in."""
    order = sorted(range(len(scores)), key=scores.__getitem__)
    blocks: list[list[float]] = []  # [sum of labels, count, largest score]
    for i in order:
        blocks.append([float(labels[i]), 1.0, scores[i]])
        while len(blocks) > 1 and blocks[-2][0] / blocks[-2][1] >= blocks[-1][0] / blocks[-1][1]:
            top = blocks.pop()
            blocks[-1] = [blocks[-1][0] + top[0], blocks[-1][1] + top[1], top[2]]
    upper = [block[2] for block in blocks]
    value = [block[0] / block[1] for block in blocks]
    return lambda score: value[min(bisect.bisect_left(upper, score), len(value) - 1)]


def print_table(name: str, probabilities: list[float], labels: list[int]) -> None:
    q = quality(probabilities, labels)
    print(f"\n{name}: Brier {q.brier:.4f}  log loss {q.log_loss:.4f}  ECE {q.ece:.4f}")


def print_reliability(probabilities: list[float], labels: list[int]) -> None:
    print("  predicción media -> tasa de fraude observada (n)")
    for mean, rate, count in reliability(probabilities, labels):
        print(f"    {mean:.2f} -> {rate:.2f}  ({count})")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ("validation", "validation-labels", "test", "test-labels"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validation, test = load(args.validation, args.validation_labels), load(args.test, args.test_labels)
    a, b = fit_platt(validation.prediction, validation.label)
    isotonic = fit_isotonic(validation.prediction, validation.label)
    print(f"Platt: sigmoid({a:.2f} * salida + {b:.2f}), ajustado en validación ({len(validation.label)} muestras)")
    versions: list[tuple[str, Callable[[Scored], list[float]]]] = [
        ("probabilidad de BigModel (referencia)", lambda s: s.truth),
        ("TinyModel sin calibrar", lambda s: s.prediction),
        ("TinyModel + Platt", lambda s: [sigmoid(a * p + b) for p in s.prediction]),
        ("TinyModel + isotónica", lambda s: [isotonic(p) for p in s.prediction]),
    ]
    for part, scored in (("test", test),):
        print(f"\n== {part}")
        for name, transform in versions:
            probabilities = transform(scored)
            print_table(name, probabilities, scored.label)
            if name in ("TinyModel sin calibrar", "TinyModel + Platt"):
                print_reliability(probabilities, scored.label)


if __name__ == "__main__":
    main()
