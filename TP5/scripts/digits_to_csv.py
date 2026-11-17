#!/usr/bin/env python3
"""Convierte los dígitos de TP3 (28x28, escala de grises) al CSV que entrena el autoencoder: x1..x784 y los mismos
784 valores como zeta_1..zeta_784 (la salida esperada de un autoencoder es su entrada).

Fuentes: por defecto digits.csv y more_digits.csv de TP3/neuron/data, juntas y sin imágenes repetidas (comparten 3689).
digits.csv sola no tiene ningún 8 y casi no tiene 5; la unión tiene de todo, aunque el 8 (585) y el 5 (785) siguen
siendo pocos contra ~2800 de cada uno de los demás.

  --val-n N --val-out ruta   aparta N imágenes al azar de la unión como validación; no entran en el train. Así la
                             validación sale del mismo pozo que el train y digits_test.csv queda sin tocar.
  --balanced                 train con la misma cantidad de cada dígito (la del dígito más escaso)
  --n N                      train de N imágenes al azar (sin --balanced); sin esto, todas las que quedan

Además del CSV escribe <salida>_labels.csv con el dígito de cada fila, en el mismo orden: el entrenamiento no lo usa,
sirve para colorear el espacio latente.

    python3 scripts/digits_to_csv.py --val-n 500 --val-out neuron/data/digits_val.csv --balanced [salida.csv]
"""
import argparse
import ast
import csv
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TP3_DATA = ROOT.parent / "TP3" / "neuron" / "data"
PIXELS = 28 * 28


def fmt(value):
    return "0" if value == 0 else f"{value:.3f}".rstrip("0").rstrip(".")


def read_sources(names):
    """Imágenes únicas de todas las fuentes, como [(dígito, píxeles)], en el orden en que aparecen."""
    csv.field_size_limit(10 ** 9)
    seen, rows = set(), []
    for name in names:
        with (TP3_DATA / name).open() as file:
            reader = csv.reader(file)
            next(reader)
            for label, image in reader:
                if image in seen:
                    continue
                seen.add(image)
                pixels = ast.literal_eval(image)
                if len(pixels) != PIXELS:
                    sys.exit(f"{name}: se esperaban imágenes de {PIXELS} píxeles")
                rows.append((label, pixels))
    return rows


def write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as file:
        file.write(",".join([f"x{i + 1}" for i in range(PIXELS)] + [f"zeta_{i + 1}" for i in range(PIXELS)]) + "\n")
        for _, pixels in rows:
            values = [fmt(v) for v in pixels]
            file.write(",".join(values + values) + "\n")
    labels = path.with_name(path.stem + "_labels.csv")
    labels.write_text("label\n" + "".join(f"{label}\n" for label, _ in rows))
    counts = defaultdict(int)
    for label, _ in rows:
        counts[label] += 1
    print(f"{path}: {len(rows)} imágenes ({path.stat().st_size / 1e6:.1f} MB), por dígito: "
          f"{dict(sorted(counts.items()))}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("out", nargs="?", type=Path, default=ROOT / "neuron" / "data" / "digits.csv")
    parser.add_argument("--source", default="digits.csv,more_digits.csv", help="archivos de TP3/neuron/data, separados por coma")
    parser.add_argument("--val-n", type=int, default=0)
    parser.add_argument("--val-out", type=Path, default=None)
    parser.add_argument("--balanced", action="store_true")
    parser.add_argument("--n", type=int, default=None)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()
    if bool(args.val_n) != bool(args.val_out):
        sys.exit("--val-n y --val-out van juntos")
    if args.balanced and args.n:
        sys.exit("--balanced y --n no van juntos")

    rng = random.Random(args.seed)
    pool = read_sources(args.source.split(","))
    rng.shuffle(pool)
    print(f"{len(pool)} imágenes únicas en {args.source}")

    if args.val_n:
        write(args.val_out, pool[:args.val_n])
        pool = pool[args.val_n:]
    if args.balanced:
        by_label = defaultdict(list)
        for row in pool:
            by_label[row[0]].append(row)
        each = min(len(rows) for rows in by_label.values())
        pool = [row for rows in by_label.values() for row in rows[:each]]
        rng.shuffle(pool)
    elif args.n is not None:
        pool = pool[:args.n]
    write(args.out, pool)


if __name__ == "__main__":
    main()
