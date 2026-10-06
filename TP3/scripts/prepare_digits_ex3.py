"""Builds the Exercise 3 datasets: a held-out validation set and the training sets (stdlib only).

The validation set is a seeded random fraction of the union of digits.csv and more_digits.csv (identical
images counted once). Training sets never contain a validation image. digits_test.csv is only converted,
never used to choose anything. Writes into data/ (prefix = --name):

  <name>_validation.csv, <name>_test.csv        same preprocessing as the training sets
  <name>_train_more.csv                         more_digits.csv minus the validation images
  <name>_train_union.csv                        digits.csv + more_digits.csv minus the validation images

Preprocessing, applied to every set: --center moves each image so its center of mass sits in the middle.
Augmentation, applied to the training sets only: --augment K adds K random copies of every image, each
shifted up to --max-shift pixels and rotated up to --max-rotation degrees.
"""

from __future__ import annotations

import argparse
import math
import random
from pathlib import Path

from prepare_digits_dataset import DATA_DIR, DigitSample, class_counts, load_raw_dataset, write_prepared

SIDE = 28
Image = list[float]


def center_of_mass(pixels: Image) -> tuple[float, float]:
    total = sum(pixels)
    if total == 0:
        return (SIDE - 1) / 2, (SIDE - 1) / 2
    rows = sum(value * (i // SIDE) for i, value in enumerate(pixels)) / total
    cols = sum(value * (i % SIDE) for i, value in enumerate(pixels)) / total
    return rows, cols


def shift(pixels: Image, dy: int, dx: int) -> Image:
    out = [0.0] * (SIDE * SIDE)
    for row in range(SIDE):
        source_row = row - dy
        if not 0 <= source_row < SIDE:
            continue
        for col in range(SIDE):
            source_col = col - dx
            if 0 <= source_col < SIDE:
                out[row * SIDE + col] = pixels[source_row * SIDE + source_col]
    return out


def recenter(pixels: Image) -> Image:
    rows, cols = center_of_mass(pixels)
    return shift(pixels, round((SIDE - 1) / 2 - rows), round((SIDE - 1) / 2 - cols))


def rotate(pixels: Image, degrees: float) -> Image:
    """Bilinear rotation around the center of the image."""
    angle, c = math.radians(degrees), (SIDE - 1) / 2
    cos, sin = math.cos(angle), math.sin(angle)
    out = [0.0] * (SIDE * SIDE)
    for row in range(SIDE):
        for col in range(SIDE):
            y, x = row - c, col - c
            source_y, source_x = cos * y + sin * x + c, -sin * y + cos * x + c
            y0, x0 = math.floor(source_y), math.floor(source_x)
            fy, fx = source_y - y0, source_x - x0
            value = 0.0
            for yy, wy in ((y0, 1 - fy), (y0 + 1, fy)):
                for xx, wx in ((x0, 1 - fx), (x0 + 1, fx)):
                    if 0 <= yy < SIDE and 0 <= xx < SIDE:
                        value += wy * wx * pixels[yy * SIDE + xx]
            out[row * SIDE + col] = value
    return out


def augmented(sample: DigitSample, copies: int, max_shift: int, max_rotation: float, rng: random.Random) -> list[DigitSample]:
    result = []
    for _ in range(copies):
        pixels = rotate(sample.pixels, rng.uniform(-max_rotation, max_rotation)) if max_rotation else sample.pixels
        pixels = shift(pixels, rng.randint(-max_shift, max_shift), rng.randint(-max_shift, max_shift))
        result.append(DigitSample(sample.label, pixels))
    return result


def unique(samples: list[DigitSample]) -> list[DigitSample]:
    seen: set[tuple[float, ...]] = set()
    result = []
    for sample in samples:
        key = tuple(sample.pixels)
        if key not in seen:
            seen.add(key)
            result.append(sample)
    return result


def split_validation(samples: list[DigitSample], fraction: float, rng: random.Random) -> tuple[set[tuple[float, ...]], list[DigitSample]]:
    indices = list(range(len(samples)))
    rng.shuffle(indices)
    chosen = sorted(indices[:round(fraction * len(samples))])
    validation = [samples[i] for i in chosen]
    return {tuple(s.pixels) for s in validation}, validation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--validation-fraction", type=float, default=0.2)
    parser.add_argument("--center", action="store_true")
    parser.add_argument("--augment", type=int, default=0, help="random augmented copies per training image")
    parser.add_argument("--max-shift", type=int, default=2)
    parser.add_argument("--max-rotation", type=float, default=10.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)
    digits = load_raw_dataset(DATA_DIR / "digits.csv")
    more = load_raw_dataset(DATA_DIR / "more_digits.csv")
    test = load_raw_dataset(DATA_DIR / "digits_test.csv")
    prep = (lambda sample: DigitSample(sample.label, recenter(sample.pixels))) if args.center else (lambda sample: sample)
    union = unique(digits + more)
    held_out, validation = split_validation(union, args.validation_fraction, rng)
    trains = {"more": [s for s in more if tuple(s.pixels) not in held_out],
              "union": [s for s in union if tuple(s.pixels) not in held_out]}
    write_prepared(DATA_DIR / f"{args.name}_validation.csv", [prep(s) for s in validation])
    write_prepared(DATA_DIR / f"{args.name}_test.csv", [prep(s) for s in test])
    print(f"validation: {len(validation)} [{class_counts(validation)}]")
    for key, samples in trains.items():
        prepared = [prep(s) for s in samples]
        extra = [copy for s in prepared for copy in augmented(s, args.augment, args.max_shift, args.max_rotation, rng)]
        write_prepared(DATA_DIR / f"{args.name}_train_{key}.csv", prepared + extra)
        print(f"train_{key}: {len(samples)} images + {len(extra)} augmented [{class_counts(samples)}]")


if __name__ == "__main__":
    main()
