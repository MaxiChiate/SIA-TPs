#!/usr/bin/env python3
"""Cuenta cuántos píxeles reconstruye mal el autoencoder en cada letra de una corrida.

Un píxel es incorrecto si la predicción, binarizada en 0.5, difiere de la ζ. El enunciado pide a lo sumo 1
píxel incorrecto por letra.

    python3 scripts/wrong_pixels.py [neuron/results/<corrida>]    # sin argumento, la última corrida
"""
import csv
import sys
from pathlib import Path

RESULTS = Path(__file__).resolve().parent.parent / "neuron" / "results"
MAX_WRONG = 1


def latest_run():
    runs = sorted(p for p in RESULTS.glob("*") if (p / "predictions.csv").exists())
    if not runs:
        sys.exit(f"no hay corridas en {RESULTS}")
    return runs[-1]


def main():
    run = Path(sys.argv[1]) if len(sys.argv) > 1 else latest_run()
    with (run / "predictions.csv").open() as file:
        header, *rows = csv.reader(file)
    zetas = [i for i, name in enumerate(header) if name.startswith("zeta_")]
    predictions = [i for i, name in enumerate(header) if name.startswith("prediction_")]
    wrong = [sum((float(row[p]) > 0.5) != (float(row[z]) > 0.5) for z, p in zip(zetas, predictions)) for row in rows]

    ok = sum(w <= MAX_WRONG for w in wrong)
    print(run)
    print("píxeles incorrectos por letra:", wrong)
    print(f"letras con a lo sumo {MAX_WRONG} píxel incorrecto: {ok}/{len(wrong)}")


if __name__ == "__main__":
    main()
