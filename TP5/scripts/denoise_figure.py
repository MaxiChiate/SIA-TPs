#!/usr/bin/env python3
"""Figura de 1.b: letra limpia, entrada ruidosa y salida del denoising autoencoder, a varios niveles de ruido.

Entrena el modelo elegido en scripts/study_1b.py (encoder [35, 20], latente 10, ruido de entrenamiento mezclado
0.05/0.1/0.2, semilla 1) y lo evalúa sobre una realización de ruido nueva (semilla 3000) por nivel. Escribe
denoising.png y denoising.svg en docs/. La salida se muestra tal cual (en grises), sin binarizar.

    .venv/bin/python scripts/denoise_figure.py [--letters a,e,g,k,s,w] [--levels 0.1,0.2,0.3]
"""
import argparse
import csv
import shutil
import sys
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import noisy_font  # noqa: E402
import seed_sweep  # noqa: E402
import study_1b  # noqa: E402
from generate_letters import read_labels  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ROWS, COLS, FIGURE_SEED = 7, 5, 3000
TRAIN_LEVELS = [0.05, 0.1, 0.2]


def image(pixels):
    return [pixels[r * COLS:(r + 1) * COLS] for r in range(ROWS)]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--letters", default="a,e,g,k,s,w")
    parser.add_argument("--levels", default="0.1,0.2,0.3")
    args = parser.parse_args()
    labels = read_labels()
    letters = [labels.index(l) for l in args.letters.split(",")]
    levels = [float(v) for v in args.levels.split(",")]

    config = study_1b.training_config(TRAIN_LEVELS, [35, 20], 10, 1)
    shown = {}  # nivel -> (entradas ruidosas, salidas) de las 32 letras
    with tempfile.TemporaryDirectory() as tmp:
        run = seed_sweep.run_once(config, tmp)
        try:
            for i, level in enumerate(levels):
                name = f"data/font_noisy_figure_{level}_{FIGURE_SEED + i}.csv"
                noisy_font.write(ROOT / "neuron" / name, [level], 1, FIGURE_SEED + i)
                eval_config = dict(config, epochs=0, initial_weights=str(run), train_dataset=name,
                                   validation_dataset=name)
                eval_run = seed_sweep.run_once(eval_config, tmp)
                with (eval_run / "predictions.csv").open() as file:
                    header, *rows = csv.reader(file)
                shutil.rmtree(eval_run)
                x = [j for j, n in enumerate(header) if n.startswith("x")]
                p = [j for j, n in enumerate(header) if n.startswith("prediction_")]
                shown[level] = ([[float(r[j]) for j in x] for r in rows], [[float(r[j]) for j in p] for r in rows])
        finally:
            shutil.rmtree(run)

    clean = noisy_font.read_font()
    fig, axes = plt.subplots(len(letters), 1 + 2 * len(levels), figsize=(1.0 * (1 + 2 * len(levels)) + 0.6,
                                                                       1.45 * len(letters) + 0.8), squeeze=False)
    for row, letter in enumerate(letters):
        panels = [(clean[letter], "limpia" if row == 0 else None)]
        for level in levels:
            panels.append((shown[level][0][letter], f"p={level}\nentrada" if row == 0 else None))
            panels.append((shown[level][1][letter], f"p={level}\nsalida" if row == 0 else None))
        for col, (pixels, title) in enumerate(panels):
            ax = axes[row][col]
            ax.imshow(image(pixels), cmap="gray_r", vmin=0, vmax=1)
            ax.set_xticks([])
            ax.set_yticks([])
            if title:
                ax.set_title(title, fontsize=8)
        axes[row][0].set_ylabel(labels[letter], fontsize=12, rotation=0, labelpad=12)
    fig.suptitle("Denoising autoencoder: letra limpia, entrada ruidosa y salida", fontsize=10)
    fig.tight_layout()
    for extension in ("png", "svg"):
        target = ROOT / "docs" / f"denoising.{extension}"
        fig.savefig(target, dpi=150)
        print(target)


if __name__ == "__main__":
    main()
