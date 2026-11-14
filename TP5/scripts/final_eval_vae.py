#!/usr/bin/env python3
"""Evaluación final del VAE sobre digits_test.csv. Se corre una sola vez; el protocolo está en el README, sección
"Evaluación final del VAE sobre digits_test.csv (protocolo fijado antes de correr)".

Entrena VAE (β = 0.1) y el mismo modelo sin KL (β = 0), con latente 2 y 10, semillas 1 a 3 (100 épocas, encoder 784-128,
tanh, Adam, η = 0.001, train balanceado), y mide sobre digits_test.csv el MSE de reconstrucción con z = media (total y por
dígito) y el KL por imagen. La referencia es predecir siempre la imagen media del train. Escribe una fila por modelo,
semilla y dígito en docs/evaluacion_final_vae.csv.

    python3 scripts/final_eval_vae.py
"""
import csv
import json
import math
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vae_figures as vf  # noqa: E402

ROOT = vf.ROOT
NEURON = vf.NEURON
OUT = ROOT / "docs" / "evaluacion_final_vae.csv"
TEST = "data/digits_test.csv"
SEEDS = (1, 2, 3)
EPOCHS = 100
PIXELS = 784


def mean_image():
    _, train = vf.read(NEURON / vf.TRAIN)
    return [sum(row[i] for row in train) / len(train) for i in range(PIXELS)]


def per_digit(values, labels):
    """MSE por dígito y total, dado el MSE de cada imagen."""
    groups = {d: [v for v, l in zip(values, labels) if l == d] for d in range(10)}
    return {**{d: sum(v) / len(v) for d, v in groups.items()}, "all": sum(values) / len(values)}


def main():
    if OUT.exists():
        sys.exit(f"{OUT} ya existe: la evaluación final se corre una sola vez")
    _, labels = vf.read(NEURON / "data" / "digits_test_labels.csv")
    labels = [int(r[0]) for r in labels]
    _, test = vf.read(NEURON / TEST)
    n_images = len(test)
    print(f"{n_images} imágenes de {TEST}", flush=True)

    mean = mean_image()
    baseline = per_digit([sum((row[i] - mean[i]) ** 2 for i in range(PIXELS)) / PIXELS for row in test], labels)
    rows = [("referencia: imagen media", 0, 0.0, 0, baseline, None)]

    with tempfile.TemporaryDirectory() as tmp:
        for name, latent, beta in vf.MODELS:
            for seed in SEEDS:
                config = json.loads(vf.BASE.read_text())
                config.update(epochs=EPOCHS, encoder_layers=[128], latent_dim=latent, variational_beta=beta, seed=seed)
                run = vf.run_binary(config, tmp)
                try:
                    eval_run = vf.evaluate(config, run, TEST, tmp)
                    header, predictions = vf.read(eval_run / "predictions.csv")
                    _, codes = vf.read(eval_run / "latent.csv")
                    shutil.rmtree(eval_run)
                finally:
                    shutil.rmtree(run)
                x = [i for i, h in enumerate(header) if h.startswith("x")]
                p = [i for i, h in enumerate(header) if h.startswith("prediction_")]
                squared = [sum((row[a] - row[b]) ** 2 for a, b in zip(x, p)) / PIXELS for row in predictions]
                kl = sum(-0.5 * sum(1 + c[latent + j] - c[j] ** 2 - math.exp(c[latent + j]) for j in range(latent))
                         for c in codes) / len(codes)
                result = per_digit(squared, labels)
                rows.append((name, latent, beta, seed, result, kl))
                print(f"{name:<22} semilla {seed}: MSE test {result['all']:.5f}, KL {kl:.2f}", flush=True)

    with OUT.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["model", "latent", "beta", "seed", "kl"] + [f"mse_digit_{d}" for d in range(10)] + ["mse_all"])
        for name, latent, beta, seed, result, kl in rows:
            writer.writerow([name, latent, beta, seed, "" if kl is None else f"{kl:.4g}"]
                            + [f"{result[d]:.6g}" for d in range(10)] + [f"{result['all']:.6g}"])
    print(OUT)


if __name__ == "__main__":
    main()
