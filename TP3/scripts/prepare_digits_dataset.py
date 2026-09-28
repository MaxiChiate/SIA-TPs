"""Turns the raw digits datasets into the CSV layout the C network reads.

The raw files have one row per image: `label,"[p0, p1, ..., p783]"`, a 28x28 grayscale image
flattened row by row, already in [0, 1]. Each one is written as:

  x1,...,x784,zeta_0,...,zeta_9

the pixels as they come, and the label one-hot encoded in the last 10 columns (zeta_k = 1 when the
digit is k, 0 otherwise), one per output neuron.

Pixels aren't normalized: they already share the same [0, 1] scale, and z-scoring would give the
always-black borders a zero std.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "neuron" / "data"

RAW_DATASETS = ("digits", "digits_test", "more_digits")

IMAGE_SIZE = 28 * 28
N_CLASSES = 10


@dataclass(frozen=True)
class DigitSample:
    label: int
    pixels: list[float]


def parse_sample(row: dict[str, str], line_number: int) -> DigitSample:
    label = int(row["label"])
    pixels = [float(value) for value in json.loads(row["image"])]
    if not 0 <= label < N_CLASSES:
        raise ValueError(f"line {line_number}: label {label} out of range")
    if len(pixels) != IMAGE_SIZE:
        raise ValueError(f"line {line_number}: expected {IMAGE_SIZE} pixels, got {len(pixels)}")
    return DigitSample(label, pixels)


def load_raw_dataset(path: Path) -> list[DigitSample]:
    csv.field_size_limit(1 << 24)  # each image is a single ~4 KB field
    with path.open(newline="") as file:
        return [parse_sample(row, line_number) for line_number, row in enumerate(csv.DictReader(file), start=2)]


def one_hot(label: int) -> list[int]:
    return [1 if k == label else 0 for k in range(N_CLASSES)]


def header() -> list[str]:
    pixels = [f"x{i}" for i in range(1, IMAGE_SIZE + 1)]
    zetas = [f"zeta_{k}" for k in range(N_CLASSES)]
    return pixels + zetas


def format_pixel(value: float) -> str:
    return f"{value:.6g}"  # most pixels are 0; "0" instead of "0.000000" keeps the files small


def write_prepared(path: Path, samples: list[DigitSample]) -> None:
    with path.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(header())
        for sample in samples:
            writer.writerow([format_pixel(value) for value in sample.pixels] + one_hot(sample.label))


def class_counts(samples: list[DigitSample]) -> str:
    counts = Counter(sample.label for sample in samples)
    return " ".join(f"{k}:{counts[k]}" for k in range(N_CLASSES))


def prepared_path(raw_path: Path) -> Path:
    return raw_path.with_name(f"{raw_path.stem}_prepared.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inputs", type=Path, nargs="*",
                        default=[DATA_DIR / f"{name}.csv" for name in RAW_DATASETS],
                        help="raw digits CSVs (default: digits, digits_test and more_digits in data/); "
                             "each one is written next to it as <name>_prepared.csv")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    for raw_path in args.inputs:
        samples = load_raw_dataset(raw_path)
        output = prepared_path(raw_path)
        write_prepared(output, samples)
        print(f"{raw_path.name}: {len(samples)} samples [{class_counts(samples)}] -> {output}")


if __name__ == "__main__":
    main()
