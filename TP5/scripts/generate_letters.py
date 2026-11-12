#!/usr/bin/env python3
"""Genera letras nuevas con el decoder de una corrida (ejercicio 1.a.4).

Para cada par de letras toma sus códigos latentes y decodifica puntos equiespaciados sobre el segmento que los une.
Los extremos (t = 0 y t = 1) tienen que reproducir las letras originales; los intermedios son entradas que la red
nunca vio. Usa el binario de neuron/ en modo evaluación (epochs 0 + initial_weights) con --decode.

    .venv/bin/python scripts/generate_letters.py [--run neuron/results/<corrida>] [--steps 7] [par ...]

Cada par se escribe como "o,e" (letra de origen y de destino, tal como figuran en src/font.h). Sin pares usa
algunos por defecto. Escribe generated.png y generated.svg en la carpeta de la corrida.
"""
import argparse
import csv
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NEURON = ROOT / "neuron"
RESULTS = NEURON / "results"
FONT = ROOT / "src" / "font.h"
ROWS, COLS = 7, 5
DEFAULT_PAIRS = ["o,e", "u,w", "b,c", "a,q", "h,k"]


def latest_run():
    runs = sorted(p for p in RESULTS.glob("*") if (p / "latent.csv").exists())
    if not runs:
        sys.exit(f"no hay corridas con latent.csv en {RESULTS}")
    return runs[-1]


def read_labels():
    return re.findall(r"//\s*0x[0-9a-fA-F]+,\s*(\S+)", FONT.read_text())


def read_csv(path):
    with Path(path).open() as file:
        header, *rows = csv.reader(file)
    return header, [[float(v) for v in row] for row in rows]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pairs", nargs="*", default=DEFAULT_PAIRS)
    parser.add_argument("--run", type=Path, default=None)
    parser.add_argument("--steps", type=int, default=7, help="puntos por par, extremos incluidos (por defecto 7)")
    args = parser.parse_args()

    run = (args.run or latest_run()).resolve()
    labels = read_labels()
    _, codes = read_csv(run / "latent.csv")
    _, originals = read_csv(NEURON / "data" / "font.csv")
    originals = [row[: ROWS * COLS] for row in originals]
    if len(codes) != len(labels):
        sys.exit(f"{len(codes)} códigos y {len(labels)} letras en {FONT.name}: no coinciden")

    pairs = []
    for text in args.pairs:
        a, _, b = text.partition(",")
        for letter in (a, b):
            if letter not in labels:
                sys.exit(f'la letra "{letter}" no está en {FONT.name}: {" ".join(labels)}')
        pairs.append((labels.index(a), labels.index(b)))

    # puntos sobre cada segmento, par por par
    points = []
    for i, j in pairs:
        for k in range(args.steps):
            t = k / (args.steps - 1)
            points.append([(1 - t) * codes[i][d] + t * codes[j][d] for d in range(2)])

    with tempfile.TemporaryDirectory() as tmp:
        points_path = Path(tmp) / "points.csv"
        points_path.write_text("latent_0,latent_1\n" + "".join(f"{x:.10g},{y:.10g}\n" for x, y in points))
        config = json.loads((run / "config.json").read_text())
        config["epochs"] = 0
        config["initial_weights"] = str(run)
        config_path = Path(tmp) / "config.json"
        config_path.write_text(json.dumps(config))
        done = subprocess.run([str(NEURON / "build" / "neuron"), str(config_path), "--decode", str(points_path)],
                              cwd=NEURON, capture_output=True, text=True)
    if done.returncode != 0:
        sys.exit(f"falló neuron:\n{done.stderr}")
    eval_run = NEURON / done.stdout.strip().removeprefix("results -> ")
    _, generated = read_csv(eval_run / "generated.csv")
    images = [row[2:] for row in generated]

    # control: los extremos tienen que dar la letra original (a lo sumo 1 píxel de diferencia)
    print(f"corrida: {run.name}  (decodificación en {eval_run.name})")
    for n, (i, j) in enumerate(pairs):
        for k, letter in ((0, i), (args.steps - 1, j)):
            image = images[n * args.steps + k]
            wrong = sum((p > 0.5) != (q > 0.5) for p, q in zip(image, originals[letter]))
            print(f'  extremo "{labels[letter]}": {wrong} píxeles distintos de la letra original')

    fig, axes = plt.subplots(len(pairs), args.steps, figsize=(1.1 * args.steps + 1, 1.5 * len(pairs) + 0.6),
                             squeeze=False)
    for n, (i, j) in enumerate(pairs):
        for k in range(args.steps):
            ax = axes[n][k]
            ax.imshow([images[n * args.steps + k][r * COLS:(r + 1) * COLS] for r in range(ROWS)],
                      cmap="gray_r", vmin=0, vmax=1)
            ax.set_xticks([])
            ax.set_yticks([])
            for side in ax.spines.values():
                side.set_color("#2a78d6" if k in (0, args.steps - 1) else "#bbbbbb")
                side.set_linewidth(2 if k in (0, args.steps - 1) else 0.8)
            if n == 0:
                ax.set_title(f"t={k / (args.steps - 1):.2f}", fontsize=9)
        axes[n][0].set_ylabel(f'"{labels[i]}" → "{labels[j]}"', fontsize=11)
    fig.suptitle("Decodificación entre dos letras del espacio latente (bordes azules: las letras originales)",
                 fontsize=10)
    fig.tight_layout()

    for extension in ("png", "svg"):
        target = run / f"generated.{extension}"
        fig.savefig(target, dpi=150)
        print(target)


if __name__ == "__main__":
    main()
