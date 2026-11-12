#!/usr/bin/env python3
"""Grafica el espacio latente de 2 dimensiones de una corrida: una letra por punto (ejercicio 1.a.3).

Lee latent.csv de la corrida y los nombres de las letras de los comentarios de src/font.h (mismo orden que el
dataset). Escribe latent.png y latent.svg en la carpeta de la corrida.

    .venv/bin/python scripts/latent_plot.py [neuron/results/<corrida>]    # sin argumento, la última corrida
"""
import csv
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "neuron" / "results"
FONT = ROOT / "src" / "font.h"


def latest_run():
    runs = sorted(p for p in RESULTS.glob("*") if (p / "latent.csv").exists())
    if not runs:
        sys.exit(f"no hay corridas con latent.csv en {RESULTS}")
    return runs[-1]


def read_labels():
    # cada fila de datos termina con "// 0x61, a": el carácter es lo que sigue a la coma
    return re.findall(r"//\s*0x[0-9a-fA-F]+,\s*(\S+)", FONT.read_text())


def read_codes(run):
    with (run / "latent.csv").open() as file:
        header, *rows = csv.reader(file)
    if len(header) != 2:
        sys.exit(f"el latente tiene {len(header)} dimensiones, el gráfico es de 2")
    return [(float(a), float(b)) for a, b in rows]


def main():
    run = Path(sys.argv[1]) if len(sys.argv) > 1 else latest_run()
    codes = read_codes(run)
    labels = read_labels()
    if len(labels) != len(codes):
        sys.exit(f"{len(codes)} códigos y {len(labels)} letras en {FONT.name}: no coinciden")

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.scatter([c[0] for c in codes], [c[1] for c in codes], s=18, color="#2a78d6", zorder=3)
    for (x, y), label in zip(codes, labels):
        ax.annotate(label, (x, y), textcoords="offset points", xytext=(5, 5), fontsize=12, fontweight="bold")
    ax.set_xlabel("código latente, dimensión 1")
    ax.set_ylabel("código latente, dimensión 2")
    ax.set_title("Espacio latente de las letras")
    ax.grid(True, color="#eeeeee", zorder=0)
    ax.margins(0.08)
    fig.tight_layout()

    for extension in ("png", "svg"):
        target = run / f"latent.{extension}"
        fig.savefig(target, dpi=150)
        print(target)


if __name__ == "__main__":
    main()
