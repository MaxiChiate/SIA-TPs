#!/usr/bin/env python3
"""Estudio del ejercicio 1.a.2: qué arquitecturas y optimizadores permiten aprender las 32 letras en 2 dimensiones.

Parte del config de neuron/config.json.autoencoder_tanh.example (tanh, Adam, η = 0.001, 30000 épocas, encoder
35-20-10, latente de 2) y cambia una cosa por vez, con varias semillas cada una. El objetivo del enunciado: todas
las letras con a lo sumo 1 píxel incorrecto. Agrega filas a docs/estudio_1a2.csv (una por configuración).

    python3 scripts/study_1a2.py optimizers [--seeds 5]
    python3 scripts/study_1a2.py architectures [--seeds 10]
"""
import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seed_sweep  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "neuron" / "config.json.autoencoder_tanh.example"
OUT = ROOT / "docs" / "estudio_1a2.csv"
FIELDS = ["experiment", "name", "activation", "optimizer", "eta", "encoder_layers", "epochs", "seeds", "goal",
          "mse_mean", "mse_std", "mse_min", "mse_max", "worst_pixels", "seconds"]

# optimizador: hiperparámetros propios (el resto del config es el de BASE)
OPTIMIZERS = {
    "gd": {},
    "momentum": {"momentum": 0.9},
    "rmsprop": {"rmsprop_decay": 0.9, "optimizer_epsilon": 1e-8},
    "adam": {"adam_beta1": 0.9, "adam_beta2": 0.999, "optimizer_epsilon": 1e-8},
}
OWN_KEYS = {"momentum", "rmsprop_decay", "adam_beta1", "adam_beta2", "optimizer_epsilon"}
ETAS = {
    "gd": [0.001, 0.01, 0.1],
    "momentum": [0.0003, 0.001, 0.01],
    "rmsprop": [0.0001, 0.001, 0.01],
    "adam": [0.0003, 0.001, 0.003],
}
ARCHITECTURES = [[], [10], [35], [20, 10], [35, 20, 10], [35, 35, 20, 10]]


def with_optimizer(base, name, eta):
    config = {k: v for k, v in base.items() if k not in OWN_KEYS}
    config.update(optimizer=name, eta=eta, **OPTIMIZERS[name])
    return config


def experiments(kind):
    base = json.loads(BASE.read_text())
    if kind == "optimizers":
        for name in OPTIMIZERS:
            for eta in ETAS[name]:
                yield f"{name} eta={eta}", with_optimizer(base, name, eta)
    else:
        for layers in ARCHITECTURES:
            config = dict(base, encoder_layers=layers)
            yield "35-" + "".join(f"{n}-" for n in layers) + "2 (encoder)" if layers else "35-2 (sin ocultas)", config


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("kind", choices=["optimizers", "architectures"])
    parser.add_argument("--seeds", type=int, default=5)
    args = parser.parse_args()

    OUT.parent.mkdir(exist_ok=True)
    new_file = not OUT.exists()
    with OUT.open("a", newline="") as file:
        writer = csv.DictWriter(file, FIELDS)
        if new_file:
            writer.writeheader()
        print(f"{'configuración':<28} {'cumplen':>8} {'MSE medio':>10} {'mín':>9} {'máx':>9} {'peor':>5} {'s/corr':>7}")
        for name, config in experiments(args.kind):
            results = seed_sweep.sweep(config, range(1, args.seeds + 1))
            s = seed_sweep.summarize(results)
            writer.writerow({"experiment": args.kind, "name": name, "activation": config["activation"],
                             "optimizer": config["optimizer"], "eta": config["eta"],
                             "encoder_layers": json.dumps(config["encoder_layers"]), "epochs": config["epochs"],
                             "seeds": args.seeds, "goal": f"{s['goal']}/{s['runs']}",
                             "mse_mean": f"{s['mse_mean']:.6g}", "mse_std": f"{s['mse_std']:.6g}",
                             "mse_min": f"{s['mse_min']:.6g}", "mse_max": f"{s['mse_max']:.6g}",
                             "worst_pixels": s["worst"], "seconds": f"{s['seconds']:.1f}"})
            file.flush()
            print(f"{name:<28} {s['goal']:>5}/{s['runs']:<2} {s['mse_mean']:>10.5f} {s['mse_min']:>9.5f} "
                  f"{s['mse_max']:>9.5f} {s['worst']:>5} {s['seconds']:>7.1f}", flush=True)


if __name__ == "__main__":
    main()
