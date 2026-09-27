"""Turns the raw fraud dataset into the CSV layout the C neuron reads.

Writes two files, aligned row by row:
  - features: the normalized inputs, with big_model_fraud_probability as the last column (zeta).
  - labels: flagged_fraud alone. Ground truth for evaluation and threshold selection only;
    it must never reach training.

Inputs are z-score normalized so no column saturates the activation because of its scale.
"""

from __future__ import annotations

import argparse
import csv
import statistics
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "neuron" / "data"

TARGET_COLUMN = "big_model_fraud_probability"
LABEL_COLUMN = "flagged_fraud"


@dataclass(frozen=True)
class RawDataset:
    header: list[str]
    rows: list[list[float]]

    def column(self, name: str) -> list[float]:
        index = self.header.index(name)
        return [row[index] for row in self.rows]


@dataclass(frozen=True)
class ColumnStats:
    mean: float
    std: float

    def normalize(self, value: float) -> float:
        return (value - self.mean) / self.std


def load_raw_dataset(path: Path) -> RawDataset:
    with path.open(newline="") as file:
        reader = csv.reader(file)
        header = next(reader)
        rows = [[float(value) for value in row] for row in reader]
    return RawDataset(header, rows)


def input_columns(dataset: RawDataset) -> list[str]:
    return [name for name in dataset.header if name not in (TARGET_COLUMN, LABEL_COLUMN)]


def column_stats(values: list[float]) -> ColumnStats:
    std = statistics.pstdev(values)
    if std == 0:
        raise ValueError("constant column can't be normalized")
    return ColumnStats(statistics.fmean(values), std)


def normalized_inputs(dataset: RawDataset, columns: list[str]) -> list[list[float]]:
    normalized_columns = []
    for name in columns:
        values = dataset.column(name)
        stats = column_stats(values)
        normalized_columns.append([stats.normalize(value) for value in values])
    return [list(row) for row in zip(*normalized_columns)]


def write_csv(path: Path, header: list[str], rows: list[list[float]]) -> None:
    with path.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows([[f"{value:.6f}" for value in row] for row in rows])


def write_features(path: Path, dataset: RawDataset) -> None:
    columns = input_columns(dataset)
    inputs = normalized_inputs(dataset, columns)
    zetas = dataset.column(TARGET_COLUMN)
    rows = [row + [zeta] for row, zeta in zip(inputs, zetas)]
    write_csv(path, columns + [TARGET_COLUMN], rows)


def write_labels(path: Path, dataset: RawDataset) -> None:
    labels = dataset.column(LABEL_COLUMN)
    with path.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([LABEL_COLUMN])
        writer.writerows([[int(label)] for label in labels])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=DATA_DIR / "fraud_dataset.csv")
    parser.add_argument("--features", type=Path, default=DATA_DIR / "fraud_features.csv")
    parser.add_argument("--labels", type=Path, default=DATA_DIR / "fraud_labels.csv")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset = load_raw_dataset(args.input)
    write_features(args.features, dataset)
    write_labels(args.labels, dataset)
    print(f"{len(dataset.rows)} samples, {len(input_columns(dataset))} inputs")
    print(f"features -> {args.features}")
    print(f"labels   -> {args.labels}")


if __name__ == "__main__":
    main()
