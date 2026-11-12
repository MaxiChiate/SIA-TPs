#!/usr/bin/env python3
"""Estudio del ejercicio 1.b: Denoising Autoencoder sobre las 32 letras.

Entrada ruidosa (cada píxel se invierte con probabilidad p), salida esperada la letra limpia. Se mide, por muestra, cuántos
píxeles de la salida (binarizada en 0.5) difieren de la letra limpia, contra los que ya difería la entrada ruidosa.
Los datos de entrenamiento (semilla 1), validación (semilla 1000) y test (semilla 2000) son realizaciones de ruido
distintas. Se elige con validación y el test se corre una sola vez, al final.

    python3 scripts/study_1b.py latent  [--seeds 3]                       # tamaño del latente, ruido de train 0.1
    python3 scripts/study_1b.py noise   --latent L [--seeds 3]            # nivel de ruido de entrenamiento
    python3 scripts/study_1b.py test    --latent L --train-levels 0.1,0.2 [--seeds 5]   # una vez, sobre test

Agrega filas a docs/estudio_1b.csv.
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import noisy_font  # noqa: E402
import seed_sweep  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NEURON = ROOT / "neuron"
DATA = NEURON / "data"
BASE = NEURON / "config.json.autoencoder_tanh.example"
OUT = ROOT / "docs" / "estudio_1b.csv"
FIELDS = ["experiment", "name", "train_levels", "encoder_layers", "latent_dim", "epochs", "seeds", "eval_level",
          "input_wrong", "output_wrong", "output_wrong_std", "perfect", "at_most_1_wrong"]

EPOCHS = 300
COPIES_TOTAL = 100  # copias ruidosas por letra en train, repartidas entre los niveles de entrenamiento
TRAIN_SEED, VAL_SEED, TEST_SEED = 1, 1000, 2000
VAL_COPIES, TEST_COPIES = 20, 20
EVAL_LEVELS = [0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4]


def dataset(kind, levels, copies, seed):
    name = f"font_noisy_{kind}_{'_'.join(str(p) for p in levels)}_{seed}.csv"
    path = DATA / name
    if not path.exists():
        noisy_font.write(path, levels, copies, seed)
    return f"data/{name}"


def training_config(train_levels, encoder_layers, latent_dim, seed):
    config = json.loads(BASE.read_text())
    config.update(train_dataset=dataset("train", train_levels, COPIES_TOTAL // len(train_levels), TRAIN_SEED),
                  validation_dataset=dataset("val", [0.1], VAL_COPIES, VAL_SEED),
                  encoder_layers=encoder_layers, latent_dim=latent_dim, epochs=EPOCHS, batch_size=32,
                  shuffle=True, seed=seed)
    return config


def evaluate(config, run, csv_path):
    """Pasa csv_path por la red de la corrida run (modo evaluación) y cuenta píxeles mal contra la letra limpia."""
    config = dict(config, epochs=0, initial_weights=str(run), train_dataset=csv_path, validation_dataset=csv_path)
    with tempfile.TemporaryDirectory() as tmp:
        eval_run = seed_sweep.run_once(config, tmp)
    with (eval_run / "predictions.csv").open() as file:
        header, *rows = csv.reader(file)
    shutil.rmtree(eval_run)
    xs = [i for i, name in enumerate(header) if name.startswith("x")]
    zs = [i for i, name in enumerate(header) if name.startswith("zeta_")]
    ps = [i for i, name in enumerate(header) if name.startswith("prediction_")]
    wrong_in, wrong_out = [], []
    for row in rows:
        wrong_in.append(sum((float(row[a]) > 0.5) != (float(row[b]) > 0.5) for a, b in zip(xs, zs)))
        wrong_out.append(sum((float(row[a]) > 0.5) != (float(row[b]) > 0.5) for a, b in zip(ps, zs)))
    n = len(rows)
    return {"input_wrong": sum(wrong_in) / n, "output_wrong": sum(wrong_out) / n,
            "perfect": sum(w == 0 for w in wrong_out) / n, "at_most_1_wrong": sum(w <= 1 for w in wrong_out) / n}


def train_and_evaluate(config, eval_sets, keep_nothing=True):
    """Entrena con config y devuelve {nivel: métricas} sobre cada (nivel, csv) de eval_sets."""
    with tempfile.TemporaryDirectory() as tmp:
        run = seed_sweep.run_once(config, tmp)
    try:
        return {level: evaluate(config, run, csv_path) for level, csv_path in eval_sets}
    finally:
        shutil.rmtree(run)


def row_for(experiment, name, train_levels, config, seeds, level, per_seed):
    def mean(key):
        return statistics.mean(r[key] for r in per_seed)
    return {"experiment": experiment, "name": name, "train_levels": "/".join(map(str, train_levels)),
            "encoder_layers": json.dumps(config["encoder_layers"]), "latent_dim": config["latent_dim"],
            "epochs": config["epochs"], "seeds": seeds, "eval_level": level,
            "input_wrong": f"{mean('input_wrong'):.3f}", "output_wrong": f"{mean('output_wrong'):.3f}",
            "output_wrong_std": f"{statistics.pstdev(r['output_wrong'] for r in per_seed):.3f}",
            "perfect": f"{mean('perfect'):.3f}", "at_most_1_wrong": f"{mean('at_most_1_wrong'):.3f}"}


def run_group(experiment, name, train_levels, encoder_layers, latent_dim, seeds, eval_levels, eval_seed, copies,
              writer, file, clean_targets=False):
    eval_sets = [(p, dataset("eval", [p], copies, eval_seed + i)) for i, p in enumerate(eval_levels)]
    per_level = {p: [] for p in eval_levels}
    config = None
    for seed in range(1, seeds + 1):
        config = training_config(train_levels, encoder_layers, latent_dim, seed)
        if clean_targets:  # control: la misma red entrenada solo con las letras limpias, 30000 épocas
            config.update(train_dataset="data/font.csv", validation_dataset="data/font.csv", epochs=30000)
            config.pop("shuffle")
        for level, metrics in train_and_evaluate(config, eval_sets).items():
            per_level[level].append(metrics)
    for level in eval_levels:
        row = row_for(experiment, name, train_levels, config, seeds, level, per_level[level])
        writer.writerow(row)
        file.flush()
        print(f"{name:<34} p_eval={level:<5} entrada {float(row['input_wrong']):5.2f} -> salida "
              f"{float(row['output_wrong']):5.2f} px  perfectas {float(row['perfect']):6.1%}  "
              f"a lo sumo 1 mal {float(row['at_most_1_wrong']):6.1%}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("kind", choices=["latent", "noise", "test"])
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--latent", type=int, default=10)
    parser.add_argument("--train-levels", default="0.1")
    args = parser.parse_args()

    OUT.parent.mkdir(exist_ok=True)
    new_file = not OUT.exists()
    with OUT.open("a", newline="") as file:
        writer = csv.DictWriter(file, FIELDS)
        if new_file:
            writer.writeheader()
        if args.kind == "latent":
            for latent in (2, 5, 10, 20, 35):
                run_group("latent", f"encoder [35, 20], latente {latent}", [0.1], [35, 20], latent, args.seeds,
                          [0.1], VAL_SEED, VAL_COPIES, writer, file)
        elif args.kind == "noise":
            for levels in ([0.05], [0.1], [0.2], [0.05, 0.1, 0.2]):
                run_group("noise", f"train p={'/'.join(map(str, levels))}", levels, [35, 20], args.latent,
                          args.seeds, [0.05, 0.1, 0.2, 0.3], VAL_SEED, VAL_COPIES, writer, file)
        else:
            levels = [float(v) for v in args.train_levels.split(",")]
            for name, clean in ((f"denoising (train p={args.train_levels})", False),
                                ("control: entrenado con letras limpias", True)):
                run_group("test", name, levels, [35, 20], args.latent, args.seeds, EVAL_LEVELS, TEST_SEED,
                          TEST_COPIES, writer, file, clean_targets=clean)


if __name__ == "__main__":
    main()
