#!/usr/bin/env python3
"""Ejercicio 2.c: muestras nuevas del VAE con un criterio fijado de antemano (ver README, "Muestras nuevas del VAE").

Genera 300 muestras z ~ N(0, I) con el VAE de latente 2 y con el de latente 10 (β = 0.1, 100 épocas, semilla 1) y mide
dos cosas de cada una:
  - pertenece a la clase d: un clasificador 784-64-10 (logistic, entrenado con el mismo train) da salida máxima >= 0.8
    para d y la segunda mayor <= 0.2.
  - es nueva: su distancia euclídea al píxel más cercano del train es al menos la del percentil 5 de las distancias al
    train de las 500 imágenes de validación (reales y no vistas).
Referencia: qué fracción de las imágenes de validación pasa "pertenece" con la clase correcta. Escribe
docs/muestras_2c.csv y docs/vae_muestras_2c.png. Se corre una sola vez: si docs/muestras_2c.csv existe, se niega.

    .venv/bin/python scripts/new_samples.py
"""
import csv
import json
import random
import shutil
import sys
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vae_figures as vf  # noqa: E402

NEURON, DOCS = vf.NEURON, vf.DOCS
OUT_CSV = DOCS / "muestras_2c.csv"
SAMPLES, SAMPLE_SEED = 300, 4000
TOP, RUNNER_UP = 0.8, 0.2
NEW_PERCENTILE = 5
EPOCHS = 100
SIDE = vf.SIDE
PIXELS = SIDE * SIDE
MODELS = [("VAE, latente 2", 2), ("VAE, latente 10", 10)]
CLASSIFIER = {"activation": "logistic", "optimizer": "adam", "adam_beta1": 0.9, "adam_beta2": 0.999,
              "optimizer_epsilon": 1e-8, "eta": 0.001, "epochs": 30, "batch_size": 32, "shuffle": True,
              "hidden_layers": [64], "seed": 1}


def write_classifier_csv(name, images, labels):
    """x1..x784 y zeta_0..zeta_9 (one-hot); labels None = ceros (solo para clasificar)."""
    path = NEURON / "data" / name
    with path.open("w") as file:
        file.write(",".join([f"x{i + 1}" for i in range(PIXELS)] + [f"zeta_{i}" for i in range(10)]) + "\n")
        for i, image in enumerate(images):
            onehot = [1 if labels is not None and labels[i] == d else 0 for d in range(10)]
            file.write(",".join(f"{v:.4g}" for v in image) + "," + ",".join(map(str, onehot)) + "\n")
    return f"data/{name}"


def read_images(name):
    _, rows = vf.read(NEURON / "data" / name)
    return np.array([r[:PIXELS] for r in rows])


def read_labels(name):
    _, rows = vf.read(NEURON / "data" / name)
    return [int(r[0]) for r in rows]


def classify(config, run, images, tmp):
    path = write_classifier_csv("cls_tmp.csv", images, None)
    eval_run = vf.evaluate(config, run, path, tmp)
    header, rows = vf.read(eval_run / "predictions.csv")
    shutil.rmtree(eval_run)
    cols = [i for i, h in enumerate(header) if h.startswith("prediction_")]
    return np.array([[r[c] for c in cols] for r in rows])


def verdict(outputs):
    """(clase, margen) si cumple el criterio de pertenecer; clase None si no."""
    order = np.argsort(-outputs, axis=1)
    top = outputs[np.arange(len(outputs)), order[:, 0]]
    second = outputs[np.arange(len(outputs)), order[:, 1]]
    belongs = (top >= TOP) & (second <= RUNNER_UP)
    return [int(order[i, 0]) if belongs[i] else None for i in range(len(outputs))], top - second


def nearest(images, train):
    """Distancia y posición del píxel más cercano del train de cada imagen."""
    d2 = (images ** 2).sum(1)[:, None] + (train ** 2).sum(1)[None, :] - 2 * images @ train.T
    index = d2.argmin(1)
    return np.sqrt(np.maximum(d2[np.arange(len(images)), index], 0)), index


def main():
    if OUT_CSV.exists():
        sys.exit(f"{OUT_CSV} ya existe: el 2.c se corre una sola vez")
    train, val = read_images("digits.csv"), read_images("digits_val.csv")
    train_labels, val_labels = read_labels("digits_labels.csv"), read_labels("digits_val_labels.csv")

    with tempfile.TemporaryDirectory() as tmp:
        classifier = dict(CLASSIFIER, train_dataset=write_classifier_csv("cls_train.csv", train, train_labels),
                          validation_dataset=write_classifier_csv("cls_val.csv", val, val_labels))
        print("entrenando el clasificador...", flush=True)
        run = vf.run_binary(classifier, tmp)
        try:
            val_outputs = classify(classifier, run, val, tmp)
            val_class, _ = verdict(val_outputs)
            accuracy = float(np.mean(val_outputs.argmax(1) == np.array(val_labels)))
            passes = float(np.mean([c is not None and c == l for c, l in zip(val_class, val_labels)]))
            print(f"clasificador, validación: acierto {accuracy:.1%}; pasa el criterio con la clase correcta "
                  f"{passes:.1%}", flush=True)
            val_distance, _ = nearest(val, train)
            threshold = float(np.percentile(val_distance, NEW_PERCENTILE))
            print(f"umbral de 'nueva': distancia al train >= {threshold:.2f} (percentil {NEW_PERCENTILE} de la "
                  f"validación; mediana {np.median(val_distance):.2f})", flush=True)

            results, rows = [], []
            for name, latent in MODELS:
                print(f"entrenando {name}...", flush=True)
                config = json.loads(vf.BASE.read_text())
                config.update(epochs=EPOCHS, encoder_layers=[128], latent_dim=latent, variational_beta=vf.BETA, seed=1)
                vae = vf.run_binary(config, tmp)
                try:
                    rng = random.Random(SAMPLE_SEED + latent)
                    generated = np.array(vf.decode(config, vae, [[rng.gauss(0, 1) for _ in range(latent)]
                                                                 for _ in range(SAMPLES)], tmp), dtype=float)
                finally:
                    shutil.rmtree(vae)
                classes, margins = verdict(classify(classifier, run, generated, tmp))
                distance, index = nearest(generated, train)
                new = distance >= threshold
                ok = [classes[i] is not None and bool(new[i]) for i in range(SAMPLES)]
                best = {}
                for i in range(SAMPLES):
                    if ok[i] and (classes[i] not in best or margins[i] > margins[best[classes[i]]]):
                        best[classes[i]] = i
                print(f"  {name}: pertenecen {sum(c is not None for c in classes)}/{SAMPLES}, nuevas "
                      f"{int(new.sum())}/{SAMPLES}, ambas {sum(ok)}/{SAMPLES}; clases con muestra elegida: "
                      f"{sorted(best)}", flush=True)
                results.append((name, generated, classes, margins, distance, index, ok, best))
                for d in range(10):
                    rows.append([name, d, sum(1 for i in range(SAMPLES) if ok[i] and classes[i] == d),
                                 sum(1 for i in range(SAMPLES) if classes[i] == d)])
        finally:
            shutil.rmtree(run)

    with OUT_CSV.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["model", "digit", "belongs_and_new", "belongs"])
        writer.writerows(rows)
        writer.writerow(["referencia: validación real, clase correcta", "", f"{passes:.4f}", f"{accuracy:.4f}"])

    fig, axes = plt.subplots(2 * len(results), 10, figsize=(10 * 0.95, len(results) * 2.2 + 0.8), squeeze=False)
    for m, (name, generated, classes, margins, distance, index, ok, best) in enumerate(results):
        for d in range(10):
            top, bottom = axes[2 * m][d], axes[2 * m + 1][d]
            for ax in (top, bottom):
                ax.set_xticks([])
                ax.set_yticks([])
                for side in ax.spines.values():
                    side.set_visible(False)
            if d in best:
                i = best[d]
                top.imshow(generated[i].reshape(SIDE, SIDE), cmap="gray_r", vmin=0, vmax=1)
                bottom.imshow(train[index[i]].reshape(SIDE, SIDE), cmap="gray_r", vmin=0, vmax=1)
                top.set_title(f"{d}  (margen {margins[i]:.2f})", fontsize=7)
            else:
                top.text(0.5, 0.5, f"{d}\nninguna", ha="center", va="center", fontsize=7, transform=top.transAxes)
        axes[2 * m][0].set_ylabel(f"{name}\ngenerada", fontsize=8, rotation=0, labelpad=36, va="center")
        axes[2 * m + 1][0].set_ylabel("train más\ncercano", fontsize=8, rotation=0, labelpad=36, va="center")
    fig.suptitle("Muestra nueva elegida por clase (cumple pertenecer y ser nueva, mayor margen)", fontsize=10)
    fig.tight_layout()
    fig.savefig(DOCS / "vae_muestras_2c.png", dpi=130)
    print(OUT_CSV, DOCS / "vae_muestras_2c.png")


if __name__ == "__main__":
    main()
