#!/usr/bin/env python3
"""Convierte los dígitos de TP3 (28x28, escala de grises) al CSV que entrena el autoencoder: x1..x784 y los mismos
784 valores como zeta_1..zeta_784 (la salida esperada de un autoencoder es su entrada).

Con --n toma una muestra al azar de n imágenes (semilla --seed), para iterar rápido. Además del CSV escribe
<salida>_labels.csv con el dígito de cada fila, en el mismo orden: el entrenamiento no lo usa, sirve para colorear el
espacio latente.

    python3 scripts/digits_to_csv.py [--n 3000] [--seed 1] [--source digits.csv|digits_test.csv] [salida.csv]
"""
import argparse
import ast
import csv
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TP3_DATA = ROOT.parent / "TP3" / "neuron" / "data"
PIXELS = 28 * 28


def fmt(value):
    return "0" if value == 0 else f"{value:.3f}".rstrip("0").rstrip(".")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("out", nargs="?", type=Path, default=ROOT / "neuron" / "data" / "digits.csv")
    parser.add_argument("--source", default="digits.csv", help="archivo de TP3/neuron/data")
    parser.add_argument("--n", type=int, default=None, help="imágenes al azar; sin esto, todas")
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()

    csv.field_size_limit(10 ** 9)
    with (TP3_DATA / args.source).open() as file:
        reader = csv.reader(file)
        next(reader)
        rows = [(label, ast.literal_eval(image)) for label, image in reader]
    if any(len(image) != PIXELS for _, image in rows):
        sys.exit(f"{args.source}: se esperaban imágenes de {PIXELS} píxeles")
    if args.n is not None:
        rows = random.Random(args.seed).sample(rows, args.n)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w") as file:
        file.write(",".join([f"x{i + 1}" for i in range(PIXELS)] + [f"zeta_{i + 1}" for i in range(PIXELS)]) + "\n")
        for _, image in rows:
            values = [fmt(v) for v in image]
            file.write(",".join(values + values) + "\n")
    labels = args.out.with_name(args.out.stem + "_labels.csv")
    labels.write_text("label\n" + "".join(f"{label}\n" for label, _ in rows))
    print(f"{args.out}: {len(rows)} imágenes ({args.out.stat().st_size / 1e6:.1f} MB); etiquetas en {labels.name}")


if __name__ == "__main__":
    main()
