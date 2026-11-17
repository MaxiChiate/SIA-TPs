#!/usr/bin/env python3
"""Corre un mismo config con varias semillas y resume cuántas veces el autoencoder cumple el objetivo.

Por semilla mide, sobre predictions.csv (los pesos que el binario se queda): el MSE y los píxeles incorrectos por
letra (un píxel es incorrecto si la predicción binarizada en 0.5 difiere de la ζ). Cumple el objetivo del
enunciado si todas las letras tienen a lo sumo 1 píxel incorrecto. Las corridas son en serie: la carpeta de cada
una se nombra por segundo y en paralelo podrían pisarse. Al medir, borra la carpeta de la corrida que acaba de
crear (con --keep se queda), para no llenar results/ ni cambiar cuál es "la última corrida".

    python3 scripts/seed_sweep.py neuron/config.json.autoencoder.example [--seeds 10] [--first-seed 1] [--keep]

También se importa: sweep(config, seeds) devuelve una lista de dicts, uno por semilla.
"""
import argparse
import csv
import json
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

NEURON = Path(__file__).resolve().parent.parent / "neuron"
RESULTS = NEURON / "results"
MAX_WRONG = 1


def measure(run):
    with (run / "predictions.csv").open() as file:
        header, *rows = csv.reader(file)
    zetas = [i for i, name in enumerate(header) if name.startswith("zeta_")]
    predictions = [i for i, name in enumerate(header) if name.startswith("prediction_")]
    squared = [(float(row[z]) - float(row[p])) ** 2 for row in rows for z, p in zip(zetas, predictions)]
    wrong = [sum((float(row[p]) > 0.5) != (float(row[z]) > 0.5) for z, p in zip(zetas, predictions)) for row in rows]
    return sum(squared) / len(squared), wrong


def run_once(config, tmp):
    """Entrena con config (un dict) y devuelve la carpeta de la corrida."""
    path = Path(tmp) / "config.json"
    path.write_text(json.dumps(config))
    done = subprocess.run([str(NEURON / "build" / "neuron"), str(path)], cwd=NEURON, capture_output=True, text=True)
    if done.returncode != 0:
        sys.exit(f"falló con seed {config['seed']}:\n{done.stderr[-500:]}")
    return NEURON / done.stdout.strip().removeprefix("results -> ")


def sweep(config, seeds, keep=False, verbose=False):
    """Una corrida por semilla de seeds; devuelve [{seed, mse, worst, ok, n, goal, seconds}, ...]."""
    config = dict(config)
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        for seed in seeds:
            config["seed"] = seed
            run = run_once(config, tmp)
            mse, wrong = measure(run)
            with (run / "epochs.csv").open() as file:
                seconds = float(list(csv.DictReader(file))[-1]["elapsed_s"])
            if not keep:
                assert run.parent == RESULTS, run  # solo se borra lo que acaba de crear el binario
                shutil.rmtree(run)
            ok = sum(w <= MAX_WRONG for w in wrong)
            row = {"seed": seed, "mse": mse, "worst": max(wrong), "ok": ok, "n": len(wrong),
                   "goal": ok == len(wrong), "seconds": seconds}
            results.append(row)
            if verbose:
                print(f"{seed:>5} {mse:>9.5f} {row['worst']:>11} {ok:>7}/{len(wrong)}  {seconds:>6.1f}", flush=True)
    return results


def summarize(results):
    mses = [r["mse"] for r in results]
    return {"goal": sum(r["goal"] for r in results), "runs": len(results),
            "mse_mean": statistics.mean(mses), "mse_std": statistics.pstdev(mses),
            "mse_min": min(mses), "mse_max": max(mses), "worst": max(r["worst"] for r in results),
            "seconds": statistics.mean(r["seconds"] for r in results)}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("config", type=Path)
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--first-seed", type=int, default=1)
    parser.add_argument("--keep", action="store_true", help="no borrar las carpetas de las corridas")
    args = parser.parse_args()

    config = json.loads(args.config.read_text())
    print(f"{args.config.name}: activation={config['activation']}, optimizer={config['optimizer']}, "
          f"eta={config['eta']}, epochs={config['epochs']}")
    print(f"{'seed':>5} {'MSE':>9} {'peor letra':>11} {'letras ok':>10}  segundos")
    results = sweep(config, range(args.first_seed, args.first_seed + args.seeds), keep=args.keep, verbose=True)
    s = summarize(results)
    print(f"cumplen el objetivo (todas las letras con a lo sumo {MAX_WRONG} píxel mal): {s['goal']}/{s['runs']}")
    print(f"MSE: media {s['mse_mean']:.5f}, desvío {s['mse_std']:.5f}, mín {s['mse_min']:.5f}, máx {s['mse_max']:.5f}")


if __name__ == "__main__":
    main()
