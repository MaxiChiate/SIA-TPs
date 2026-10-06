"""Splits the raw fraud dataset into train / validation / test and writes the CSVs the C network reads.

The split is stratified by flagged_fraud (every part keeps the ~11.6 % of frauds) and seeded. The z-score
mean and std come from the train part only, so nothing about validation or test leaks into the inputs.
flagged_fraud goes to a labels file next to each part: ground truth for evaluation and the threshold, never
an input. Rows keep the order of the raw file inside each part.

Input variants (so the same split can be trained with different columns):
  --drop COL ...        leave columns out
  --log-amount          replace amount_usd by log(amount_usd)
  --train-fraction F    keep only a stratified fraction F of the train part (the z-score uses what is kept)

Writes <name>_{train,validation,test}.csv and <name>_{train,validation,test}_labels.csv in data/.
"""

from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass
from pathlib import Path

from prepare_fraud_dataset import (
    DATA_DIR,
    LABEL_COLUMN,
    TARGET_COLUMN,
    ColumnStats,
    RawDataset,
    column_stats,
    input_columns,
    load_raw_dataset,
    write_csv,
)

AMOUNT = "amount_usd"


@dataclass(frozen=True)
class Split:
    train: list[int]
    validation: list[int]
    test: list[int]


def stratified_split(labels: list[float], validation_fraction: float, test_fraction: float, rng: random.Random) -> Split:
    train: list[int] = []
    validation: list[int] = []
    test: list[int] = []
    for value in sorted(set(labels)):
        indices = [i for i, label in enumerate(labels) if label == value]
        rng.shuffle(indices)
        n_validation = round(validation_fraction * len(indices))
        n_test = round(test_fraction * len(indices))
        validation += indices[:n_validation]
        test += indices[n_validation:n_validation + n_test]
        train += indices[n_validation + n_test:]
    return Split(sorted(train), sorted(validation), sorted(test))


def subsample(indices: list[int], labels: list[float], fraction: float, rng: random.Random) -> list[int]:
    if fraction >= 1.0:
        return indices
    kept: list[int] = []
    for value in sorted(set(labels)):
        group = [i for i in indices if labels[i] == value]
        rng.shuffle(group)
        kept += group[:max(1, round(fraction * len(group)))]
    return sorted(kept)


def feature_columns(dataset: RawDataset, dropped: list[str]) -> list[str]:
    unknown = [name for name in dropped if name not in dataset.header]
    if unknown:
        raise ValueError(f"unknown columns to drop: {unknown}")
    return [name for name in input_columns(dataset) if name not in dropped]


def feature_values(dataset: RawDataset, name: str, log_amount: bool) -> list[float]:
    values = dataset.column(name)
    return [math.log(value) for value in values] if log_amount and name == AMOUNT else values


def write_part(prefix: str, part: str, indices: list[int], columns: list[str], values: dict[str, list[float]],
               stats: dict[str, ColumnStats], targets: list[float], labels: list[float]) -> None:
    rows = [[stats[name].normalize(values[name][row]) for name in columns] + [targets[row]] for row in indices]
    write_csv(DATA_DIR / f"{prefix}_{part}.csv", columns + [TARGET_COLUMN], rows)
    write_csv(DATA_DIR / f"{prefix}_{part}_labels.csv", [LABEL_COLUMN], [[labels[row]] for row in indices])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--name", required=True, help="prefix of the files written")
    parser.add_argument("--input", type=Path, default=DATA_DIR / "fraud_dataset.csv")
    parser.add_argument("--validation-fraction", type=float, default=0.15)
    parser.add_argument("--test-fraction", type=float, default=0.15)
    parser.add_argument("--drop", nargs="*", default=[])
    parser.add_argument("--log-amount", action="store_true")
    parser.add_argument("--train-fraction", type=float, default=1.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)
    dataset = load_raw_dataset(args.input)
    labels = dataset.column(LABEL_COLUMN)
    split = stratified_split(labels, args.validation_fraction, args.test_fraction, rng)
    train = subsample(split.train, labels, args.train_fraction, rng)
    columns = feature_columns(dataset, args.drop)
    values = {name: feature_values(dataset, name, args.log_amount) for name in columns}
    stats = {name: column_stats([values[name][i] for i in train]) for name in columns}
    targets = dataset.column(TARGET_COLUMN)
    for part, indices in (("train", train), ("validation", split.validation), ("test", split.test)):
        write_part(args.name, part, indices, columns, values, stats, targets, labels)
        frauds = int(sum(labels[i] for i in indices))
        print(f"{args.name}_{part}: {len(indices)} samples, {frauds} frauds ({100 * frauds / len(indices):.1f} %)")
    print(f"inputs ({len(columns)}): {', '.join(columns)}")


if __name__ == "__main__":
    main()
