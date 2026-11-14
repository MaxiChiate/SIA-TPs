#!/usr/bin/env python3
"""Figuras del ejercicio 2: VAE sobre los dígitos de TP3, con latente de 2 y de 10 dimensiones, contra el mismo modelo sin KL.

Entrena cuatro modelos con el mismo encoder (784-128), tanh y Adam: VAE (β = 0.1) y sin término KL (β = 0, que sigue
inyectando el ruido ε), cada uno con latente 2 y 10. Un autoencoder no variacional con tanh en el latente no sirve de
control: con 784 entradas satura la capa latente (todos los códigos en ±1) y no entrena (MSE de la imagen media). Mide el error en validación y escribe tres figuras en docs/:
  vae_latent.png          latente de 2 dimensiones: códigos de las imágenes de train por dígito y decodificación de una
                          grilla del plano (β > 0: [-3, 3]², el rango de la normal; β = 0: el rango de sus códigos)
  vae_samples.png         imágenes nuevas: z ~ N(0, I) decodificado, en los cuatro modelos
  vae_reconstructions.png un ejemplo de cada dígito de validación y su reconstrucción en los cuatro modelos
y docs/estudio_vae_figuras.csv con el MSE y el KL de cada modelo.

Entrena en dos etapas: primero calcula todo y lo guarda en --cache (JSON), después dibuja desde ahí. Con --from-cache
solo dibuja.

    .venv/bin/python scripts/vae_figures.py [--epochs 100] [--cache /ruta/cache.json] [--from-cache]
"""
import argparse
import csv
import json
import math
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NEURON = ROOT / "neuron"
DOCS = ROOT / "docs"
BASE = NEURON / "config.json.vae.example"
TRAIN, VALIDATION = "data/digits.csv", "data/digits_val.csv"
SIDE, GRID, SAMPLES = 28, 15, 15
BETA = 0.1
MODELS = [("VAE, latente 2", 2, BETA), ("VAE, latente 10", 10, BETA),
          ("Sin KL, latente 2", 2, 0.0), ("Sin KL, latente 10", 10, 0.0)]


def run_binary(config, tmp, extra=()):
    path = Path(tmp) / "config.json"
    path.write_text(json.dumps(config))
    done = subprocess.run([str(NEURON / "build" / "neuron"), str(path), *extra], cwd=NEURON, capture_output=True,
                          text=True)
    if done.returncode != 0:
        sys.exit(f"falló neuron:\n{done.stderr[-600:]}")
    return NEURON / done.stdout.strip().removeprefix("results -> ")


def read(path):
    with Path(path).open() as file:
        header, *rows = csv.reader(file)
    return header, [[float(v) for v in row] for row in rows]


def evaluate(config, run, dataset, tmp, extra=()):
    """Corre la red de run (modo evaluación) sobre dataset; devuelve la carpeta de esa corrida de evaluación."""
    config = dict(config, epochs=0, initial_weights=str(run), train_dataset=dataset, validation_dataset=dataset)
    return run_binary(config, tmp, extra)


def decode(config, run, points, tmp):
    points_path = Path(tmp) / "points.csv"
    dim = len(points[0])
    points_path.write_text(",".join(f"latent_{i}" for i in range(dim)) + "\n"
                           + "".join(",".join(f"{v:.8g}" for v in p) + "\n" for p in points))
    eval_run = evaluate(config, run, VALIDATION, tmp, ("--decode", str(points_path)))
    _, rows = read(eval_run / "generated.csv")
    shutil.rmtree(eval_run)
    return [row[dim:] for row in rows]


def model_data(name, latent, beta, epochs, tmp, picks, rng):
    config = json.loads(BASE.read_text())
    config.update(epochs=epochs, encoder_layers=[128], latent_dim=latent, variational_beta=beta, seed=1)
    run = run_binary(config, tmp)
    try:
        with (run / "epochs.csv").open() as file:
            last = list(csv.DictReader(file))[-1]
        data = {"name": name, "latent": latent, "beta": beta, "train_mse": float(last["train_mse"]),
                "validation_mse": float(last["validation_mse"])}

        eval_run = evaluate(config, run, VALIDATION, tmp)  # predicciones sobre validación
        header, rows = read(eval_run / "predictions.csv")
        shutil.rmtree(eval_run)
        prediction = [i for i, n in enumerate(header) if n.startswith("prediction_")]
        data["reconstructions"] = [[rows[i][j] for j in prediction] for i in picks]

        eval_run = evaluate(config, run, TRAIN, tmp)  # códigos de las imágenes de train
        _, codes = read(eval_run / "latent.csv")
        shutil.rmtree(eval_run)
        means = [row[:latent] for row in codes]
        data["kl"] = sum(-0.5 * sum(1 + row[latent + j] - row[j] ** 2 - math.exp(row[latent + j])
                                    for j in range(latent)) for row in codes) / len(codes)
        data["train_codes"] = means if latent == 2 else None

        data["samples"] = decode(config, run, [[rng.gauss(0, 1) for _ in range(latent)] for _ in range(SAMPLES)], tmp)
        if latent == 2:
            if beta > 0:
                lo = [-3.0, -3.0]
                hi = [3.0, 3.0]
            else:
                lo = [min(c[j] for c in means) for j in range(2)]
                hi = [max(c[j] for c in means) for j in range(2)]
            data["grid_range"] = [lo, hi]
            xs = [lo[0] + (hi[0] - lo[0]) * k / (GRID - 1) for k in range(GRID)]
            ys = [hi[1] - (hi[1] - lo[1]) * k / (GRID - 1) for k in range(GRID)]  # de arriba hacia abajo
            data["grid"] = decode(config, run, [[x, y] for y in ys for x in xs], tmp)
        return data
    finally:
        shutil.rmtree(run)


def compute(epochs, cached):
    _, labels = read(NEURON / "data" / "digits_val_labels.csv")
    labels = [int(r[0]) for r in labels]
    picks = [labels.index(d) for d in range(10)]
    _, val = read(NEURON / VALIDATION)
    _, train_labels = read(NEURON / "data" / "digits_labels.csv")
    result = {"inputs": [val[i][:SIDE * SIDE] for i in picks], "train_labels": [int(r[0]) for r in train_labels],
              "models": []}
    with tempfile.TemporaryDirectory() as tmp:
        for name, latent, beta in MODELS:
            if name in cached and cached[name].get("beta") == beta:
                print(f"{name}: ya calculado en el cache", flush=True)
                result["models"].append(cached[name])
                continue
            print(f"entrenando {name} ({epochs} épocas)...", flush=True)
            result["models"].append(model_data(name, latent, beta, epochs, tmp, picks, random.Random(3000)))
            m = result["models"][-1]
            print(f"  MSE train {m['train_mse']:.5f}, validación {m['validation_mse']:.5f}, KL {m['kl']:.2f}", flush=True)
    return result


def tile(ax, pixels):
    ax.imshow([[float(pixels[r * SIDE + c]) for c in range(SIDE)] for r in range(SIDE)], cmap="gray_r", vmin=0, vmax=1)
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ax.spines.values():
        side.set_visible(False)


def draw(result):
    models = result["models"]
    labels = result["train_labels"]

    # espacio latente de 2 dimensiones: códigos por dígito y grilla decodificada
    fig, axes = plt.subplots(2, 2, figsize=(11, 10.5))
    for row, model in enumerate(m for m in models if m["latent"] == 2):
        ax = axes[row][0]
        codes = model["train_codes"]
        for digit in range(10):
            points = [c for c, l in zip(codes, labels) if l == digit]
            ax.scatter([p[0] for p in points], [p[1] for p in points], s=3, label=str(digit))
        ax.legend(markerscale=4, fontsize=7, ncol=5, loc="upper center")
        ax.set_title(f"{model['name']}: códigos de train (media)", fontsize=10)
        ax.set_xlabel("dimensión 1")
        ax.set_ylabel("dimensión 2")
        lo, hi = model["grid_range"]
        ax = axes[row][1]
        big = [[0.0] * (SIDE * GRID) for _ in range(SIDE * GRID)]
        for g, pixels in enumerate(model["grid"]):
            gi, gj = divmod(g, GRID)
            for r in range(SIDE):
                for c in range(SIDE):
                    big[gi * SIDE + r][gj * SIDE + c] = float(pixels[r * SIDE + c])
        ax.imshow(big, cmap="gray_r", vmin=0, vmax=1, extent=[lo[0], hi[0], lo[1], hi[1]], aspect="auto")
        ax.set_title(f"{model['name']}: decodificación de la grilla", fontsize=10)
        ax.set_xlabel("dimensión 1")
    fig.tight_layout()
    fig.savefig(DOCS / "vae_latent.png", dpi=130)
    plt.close(fig)

    # imágenes nuevas: z ~ N(0, I)
    fig, axes = plt.subplots(len(models), SAMPLES, figsize=(SAMPLES * 0.8, len(models) * 0.95 + 0.6))
    for row, model in enumerate(models):
        for col in range(SAMPLES):
            tile(axes[row][col], model["samples"][col])
        axes[row][0].set_ylabel(model["name"].replace(", ", "\n"), fontsize=8, rotation=0, labelpad=34, va="center")
    fig.suptitle("Imágenes nuevas: z ~ N(0, I) decodificado", fontsize=10)
    fig.tight_layout()
    fig.savefig(DOCS / "vae_samples.png", dpi=130)
    plt.close(fig)

    # reconstrucciones de un ejemplo de cada dígito de validación
    fig, axes = plt.subplots(1 + len(models), 10, figsize=(10 * 0.95, (1 + len(models)) * 1.0 + 0.5))
    for col in range(10):
        tile(axes[0][col], result["inputs"][col])
        for row, model in enumerate(models, start=1):
            tile(axes[row][col], model["reconstructions"][col])
    axes[0][0].set_ylabel("entrada", fontsize=8, rotation=0, labelpad=30, va="center")
    for row, model in enumerate(models, start=1):
        axes[row][0].set_ylabel(model["name"].replace(", ", "\n"), fontsize=8, rotation=0, labelpad=34, va="center")
    fig.suptitle("Reconstrucción de imágenes de validación", fontsize=10)
    fig.tight_layout()
    fig.savefig(DOCS / "vae_reconstructions.png", dpi=130)
    plt.close(fig)

    with (DOCS / "estudio_vae_figuras.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["model", "latent", "beta", "train_mse", "validation_mse", "kl"])
        for m in models:
            writer.writerow([m["name"], m["latent"], m["beta"], f"{m['train_mse']:.6g}", f"{m['validation_mse']:.6g}",
                             f"{m['kl']:.4g}"])
    print("docs/vae_latent.png, docs/vae_samples.png, docs/vae_reconstructions.png, docs/estudio_vae_figuras.csv")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--cache", type=Path, default=None)
    parser.add_argument("--from-cache", action="store_true")
    args = parser.parse_args()
    if args.from_cache:
        result = json.loads(args.cache.read_text())
    else:
        cached = {}
        if args.cache and args.cache.exists():
            cached = {m["name"]: m for m in json.loads(args.cache.read_text())["models"]}
        result = compute(args.epochs, cached)
        if args.cache:
            args.cache.write_text(json.dumps(result))
    draw(result)


if __name__ == "__main__":
    main()
