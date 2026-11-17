#!/usr/bin/env python3
"""Estudio del ejercicio 2: el VAE sobre los dígitos de TP3, variando β (peso del término KL) y las épocas.

Parte de neuron/config.json.vae.example y cambia lo que se le pide. Por corrida mide, en validación y con z = media:
  - mse: error de reconstrucción (el mismo MSE que imprime el binario), y mse_vs_media: ese MSE dividido por el de
    predecir siempre la imagen media del train (1 = no aprendió nada, 0 = reconstruye perfecto).
  - kl: KL promedio por imagen entre N(media, exp(log-varianza)) y N(0, 1), sumado sobre las 2 dimensiones.
  - std_media_0/1: desvío de las medias en validación (cerca de 0 = esa dimensión no se usa, colapso).
Agrega una fila por corrida a docs/estudio_vae.csv.

    python3 scripts/study_vae.py --betas 0,0.01,0.1,1 --epochs 30 [--seed 1] [--keep]
"""
import argparse
import csv
import json
import math
import shutil
import statistics
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seed_sweep  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NEURON = ROOT / "neuron"
BASE = NEURON / "config.json.vae.example"
OUT = ROOT / "docs" / "estudio_vae.csv"
FIELDS = ["beta", "epochs", "seed", "encoder_layers", "latent_dim", "mse", "mse_vs_media", "kl", "std_media_0",
          "std_media_1", "seconds"]


def read(path):
    with Path(path).open() as file:
        header, *rows = csv.reader(file)
    return header, [[float(v) for v in row] for row in rows]


def mean_image_mse(config):
    _, train = read(NEURON / config["train_dataset"])
    _, validation = read(NEURON / config["validation_dataset"])
    n = len(train[0]) // 2
    mean = [sum(row[i] for row in train) / len(train) for i in range(n)]
    squared = sum((row[i] - mean[i]) ** 2 for row in validation for i in range(n))
    return squared / (len(validation) * n)


def measure(run, baseline):
    with (run / "epochs.csv").open() as file:
        last = list(csv.DictReader(file))[-1]
    header, codes = read(run / "latent.csv")
    half = len(header) // 2
    kl = statistics.mean(sum(-0.5 * (1 + row[half + j] - row[j] ** 2 - math.exp(row[half + j])) for j in range(half))
                         for row in codes)
    stds = [statistics.pstdev(row[j] for row in codes) for j in range(half)]
    mse = float(last["validation_mse"])
    return {"mse": mse, "mse_vs_media": mse / baseline, "kl": kl, "std_media_0": stds[0], "std_media_1": stds[1],
            "seconds": float(last["elapsed_s"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--betas", default="0,0.01,0.1,1")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--encoder", default=None, help="capas del encoder, p. ej. 256,64 (por defecto las del ejemplo)")
    parser.add_argument("--keep", action="store_true", help="no borrar las carpetas de las corridas")
    args = parser.parse_args()

    base = json.loads(BASE.read_text())
    baseline = mean_image_mse(base)
    print(f"MSE de predecir la imagen media (validación): {baseline:.5f}")
    OUT.parent.mkdir(exist_ok=True)
    new_file = not OUT.exists()
    with OUT.open("a", newline="") as file, tempfile.TemporaryDirectory() as tmp:
        writer = csv.DictWriter(file, FIELDS)
        if new_file:
            writer.writeheader()
        print(f"{'beta':>6} {'épocas':>6} {'MSE':>8} {'MSE/media':>9} {'KL':>7} {'std μ0':>7} {'std μ1':>7} {'s':>6}")
        for beta in (float(v) for v in args.betas.split(",")):
            config = dict(base, variational_beta=beta, epochs=args.epochs, seed=args.seed)
            if args.encoder:
                config["encoder_layers"] = [int(v) for v in args.encoder.split(",")]
            run = seed_sweep.run_once(config, tmp)
            row = measure(run, baseline)
            if not args.keep:
                assert run.parent == seed_sweep.RESULTS, run
                shutil.rmtree(run)
            writer.writerow({"beta": beta, "epochs": args.epochs, "seed": args.seed,
                             "encoder_layers": json.dumps(config["encoder_layers"]),
                             "latent_dim": config["latent_dim"], **{k: f"{v:.6g}" for k, v in row.items()}})
            file.flush()
            print(f"{beta:>6g} {args.epochs:>6} {row['mse']:>8.5f} {row['mse_vs_media']:>9.3f} {row['kl']:>7.2f} "
                  f"{row['std_media_0']:>7.3f} {row['std_media_1']:>7.3f} {row['seconds']:>6.1f}", flush=True)


if __name__ == "__main__":
    main()
