#!/usr/bin/env python3
"""Arma un dataset de denoising: cada letra de neuron/data/font.csv con ruido en la entrada y limpia como ζ.

Ruido: cada píxel se invierte (0 <-> 1) con probabilidad p, de forma independiente. Para cada nivel de --levels se
generan --copies copias ruidosas de cada letra. El mismo formato de siempre (x1..x35, zeta_1..zeta_35), así que
el binario lo entrena sin cambios.

    python3 scripts/noisy_font.py --levels 0.1 --copies 100 --seed 1 neuron/data/font_noisy_train.csv
"""
import argparse
import csv
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONT = ROOT / "neuron" / "data" / "font.csv"
PIXELS = 35


def read_font():
    with FONT.open() as file:
        _, *rows = csv.reader(file)
    return [[int(float(v)) for v in row[:PIXELS]] for row in rows]


def flip(letter, p, rng):
    return [1 - v if rng.random() < p else v for v in letter]


def write(path, levels, copies, seed):
    rng = random.Random(seed)
    letters = read_font()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as file:
        file.write(",".join([f"x{i + 1}" for i in range(PIXELS)] + [f"zeta_{i + 1}" for i in range(PIXELS)]) + "\n")
        for p in levels:
            for letter in letters:
                for _ in range(copies):
                    file.write(",".join(map(str, flip(letter, p, rng) + letter)) + "\n")
    return len(letters) * copies * len(levels)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("out", type=Path)
    parser.add_argument("--levels", default="0.1", help="probabilidades de invertir un píxel, separadas por coma")
    parser.add_argument("--copies", type=int, default=100, help="copias ruidosas por letra y por nivel")
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    levels = [float(v) for v in args.levels.split(",")]
    if any(not 0 <= p <= 1 for p in levels):
        sys.exit("los niveles tienen que estar entre 0 y 1")
    n = write(args.out, levels, args.copies, args.seed)
    print(f"{args.out}: {n} filas")


if __name__ == "__main__":
    main()
