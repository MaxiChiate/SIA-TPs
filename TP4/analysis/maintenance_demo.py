#!/usr/bin/env python3
"""Maintenance demo with one SYNTHETIC creator: saved scaler, Phase 2 map, saved Oja weights and drift check (CAMP-03).

    .venv/bin/python analysis/maintenance_demo.py [--out DIR]

D-19: the creator is synthetic (creator_id SYN001, name @sintetico_demo, `synthetic: true` in demo.json and the word
sintético in every report line about it). It is built from the column medians of datos/creadores.csv with the five
exact relations restored, it is written only under analysis/results/maintenance/ and it never enters
datos/creadores.csv or any campaign list. It is mapped into the z-score space with scripts/map_creator.py and the
saved datos/prepared/creadores_zscore.meta.json, placed on the best-matching neuron of the Phase 2 figure run of the
chosen grid (k5-step), given its Oja index with the saved w of analysis/results/oja/weights.csv (D-02 sign), and
D-18: the drift check flags retraining only when its BMU distance is above the largest training BMU distance.
numpy and the standard library only (Phase 1 D-06).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

TP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TP_DIR / "scripts"))
sys.path.insert(0, str(TP_DIR / "analysis"))

import pca  # noqa: E402
import som  # noqa: E402
import som_stage  # noqa: E402
from creadores import load_creadores, load_meta, transform_new_creator  # noqa: E402

SYNTHETIC_ID = "SYN001"
SYNTHETIC_NAME = "@sintetico_demo"
DEFAULT_OUT = TP_DIR / "analysis" / "results" / "maintenance"
META = TP_DIR / "datos" / "prepared" / "creadores_zscore.meta.json"
OJA_WEIGHTS = TP_DIR / "analysis" / "results" / "oja" / "weights.csv"
OJA_INDEX = TP_DIR / "analysis" / "results" / "oja" / "index.csv"
STAGE1 = TP_DIR / "analysis" / "results" / "som" / "series_som_stage1"
PHASE2_RULE_FILE = "deliverables/02-kohonen.md"
MAP_CREATOR = TP_DIR / "scripts" / "map_creator.py"

ENGAGEMENT_KINDS = ("likes", "comments", "saves", "shares")


# ----------------------------------------------------------------------------------------------
# The synthetic creator (D-19)
# ----------------------------------------------------------------------------------------------


def _rescale_to_100(row: dict, prefix: str) -> None:
    names = [name for name in row if name.startswith(prefix)]
    total = sum(row[name] for name in names)
    for name in names:
        row[name] = row[name] * 100.0 / total


def synthetic_creator(data) -> dict:
    """The synthetic creator as a dict over creator_id, name and the 31 raw columns of `data`: the median of every
    column over the creators, then the five exact relations restored (price_ars, organic_posts_pct,
    total_engagement_per_1000, the four topic shares and the four content shares each summing 100) and the
    Argentine reach recomputed from the audience share (D-19)."""
    row = {"creator_id": SYNTHETIC_ID, "name": SYNTHETIC_NAME}
    for j, column in enumerate(data.columns):
        row[column] = float(np.median(data.values[:, j]))
    row["estimated_argentina_reach"] = float(round(row["average_reach"] * row["argentina_audience_pct"] / 100.0))
    row["total_engagement_per_1000"] = float(sum(row[f"{kind}_per_1000"] for kind in ENGAGEMENT_KINDS))
    row["price_ars"] = 1500.0 * row["price_usd"]
    row["organic_posts_pct"] = 100.0 - row["sponsored_posts_pct"]
    _rescale_to_100(row, "topic_")
    _rescale_to_100(row, "content_")
    return row


def write_raw_csv(row: dict, path: Path) -> None:
    """One-row CSV in the layout of datos/creadores.csv: creator_id, name, then the 31 columns in their order."""
    columns = [name for name in row if name not in ("creator_id", "name")]
    with Path(path).open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(["creator_id", "name", *columns])
        writer.writerow([row["creator_id"], row["name"], *(repr(float(row[c])) for c in columns)])


def map_with_cli(raw_csv, meta_path, out_csv) -> np.ndarray:
    """Map the one-row CSV with scripts/map_creator.py and the saved .meta.json and return its z row (D-19). An
    argument list with sys.executable, no shell, check=True (T-03-14)."""
    subprocess.run([sys.executable, str(MAP_CREATOR), "--meta", str(meta_path), "--input", str(raw_csv),
                    "--out", str(out_csv)], check=True)
    with Path(out_csv).open(newline="", encoding="utf-8") as file:
        rows = list(csv.reader(file))
    if len(rows) != 2:
        raise SystemExit(f"{out_csv}: expected a header and one z row, found {len(rows)} lines")
    return np.array([float(cell) for cell in rows[1]], dtype=np.float64)


# ----------------------------------------------------------------------------------------------
# Placing the creator
# ----------------------------------------------------------------------------------------------


def bmu(z, prototypes, k) -> tuple[int, int, int, float]:
    """(neuron, row, col, distance) of the best-matching neuron, lowest index on ties."""
    neuron, distance = som.nearest_distance(z, prototypes)
    return neuron, neuron // k, neuron % k, distance


def drift_check(distance, training_distances) -> dict:
    """D-18: the training QE (mean BMU distance), the maximum, the 95th percentile and the fraction of training
    distances at or below the new one; `drift` (retrain) only when the distance is strictly above the maximum."""
    training = np.asarray(training_distances, dtype=np.float64)
    return {
        "qe": float(training.mean()),
        "max": float(training.max()),
        "p95": float(np.percentile(training, 95)),
        "percentile": float(np.mean(training <= distance)),
        "drift": bool(distance > training.max()),
    }


def index_rank(value, indices) -> int:
    """Place the value would take among the training indices: 1 + the number of them that are larger (D-02 sign,
    1 = the largest). The value is not added to the indices."""
    return 1 + int(sum(1 for v in indices if v > value))


# ----------------------------------------------------------------------------------------------
# Inputs and writers
# ----------------------------------------------------------------------------------------------


def _require(path: Path, target: str) -> Path:
    if not Path(path).is_file():
        raise SystemExit(f"{path} not found; run `make {target}`")
    return Path(path)


def read_weights(path, features) -> np.ndarray:
    """w of analysis/results/oja/weights.csv in the order of the saved scaler's features (D-02 sign)."""
    with _require(path, "oja").open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    if [row["variable"] for row in rows] != list(features):
        raise SystemExit(f"{path}: the variables are not the features of the saved scaler, in the same order")
    return np.array([float(row["w"]) for row in rows], dtype=np.float64)


def read_training_indices(path) -> list[float]:
    with _require(path, "oja").open(newline="", encoding="utf-8") as file:
        return [float(row["oja_index"]) for row in csv.DictReader(file)]


def _decimal(value: float, digits: int) -> str:
    return "n/d" if math.isnan(value) else f"{value:.{digits}f}".replace(".", ",")


def report_lines(result: dict) -> list[str]:
    b, d = result["bmu"], result["drift"]
    verdict = "re-entrenar" if d["drift"] else "no hace falta re-entrenar"
    reason = "supera" if d["drift"] else "no supera"
    return [
        f"- El creador sintético ({result['creator_id']}, {result['name']}) se arma con las medianas de las 31 "
        "columnas de datos/creadores.csv; no es un creador real y no está en ninguna lista.",
        f"- Su neurona ganadora en el mapa {result['som_label']} (seed {result['figure_seed']}) es "
        f"(fila {b['row']}, col {b['col']}) a distancia {_decimal(b['distance'], 3)} de su vector.",
        f"- Distancias de entrenamiento al BMU: QE media {_decimal(d['qe'], 3)}, máximo {_decimal(d['max'], 3)}, "
        f"percentil 95 {_decimal(d['p95'], 3)}; el {_decimal(d['percentile'] * 100, 1)} % de esas distancias es "
        "menor o igual que la del creador sintético.",
        f"- Veredicto de deriva: {verdict} (la distancia del creador sintético {reason} el máximo de "
        "entrenamiento).",
        f"- El creador sintético tiene índice de Oja {_decimal(result['oja_index'], 3)} con el w guardado y ocuparía "
        f"el lugar {result['oja_rank']} entre los 50 creadores (1 = índice más alto, 51 = más bajo que los 50).",
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Maintenance demo with one synthetic creator (D-18, D-19).")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help="output folder (default: analysis/results/maintenance)")
    args = parser.parse_args(argv)
    out: Path = args.out

    selection_path = STAGE1 / "selection.json"
    if not selection_path.is_file():
        raise SystemExit(f"{selection_path} not found; run `make som-stage1`")
    _require(OJA_WEIGHTS, "oja")
    _require(OJA_INDEX, "oja")
    if not META.is_file():
        raise SystemExit(f"{META} not found; run `make prepare`")
    som_stage.require_same_rule(selection_path, TP_DIR / PHASE2_RULE_FILE)
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    if selection.get("chosen_k") is None or selection.get("outcome") != "chosen":
        raise SystemExit(f"selection.json has no chosen grid (outcome {selection.get('outcome')!r})")
    k = int(selection["chosen_k"])
    run = som.read_run(TP_DIR / selection["figure_run"])
    if run.k != k:
        raise SystemExit(f"figure run has grid_k {run.k}, selection.json chose k = {k}")
    meta = load_meta(META)
    features = list(meta["features"])
    if list(run.features) != features:
        raise SystemExit("figure run features differ from the saved scaler's features")

    data = load_creadores()
    row = synthetic_creator(data)
    out.mkdir(parents=True, exist_ok=True)
    raw_csv, z_csv = out / "synthetic_creator.csv", out / "synthetic_z.csv"
    write_raw_csv(row, raw_csv)
    z = map_with_cli(raw_csv, META, z_csv)
    if not np.allclose(z, transform_new_creator(meta, row), rtol=0.0, atol=1e-12):
        raise SystemExit("the CLI mapping differs from creadores.transform_new_creator")

    neuron, r, c, distance = bmu(z, run.prototypes, k)
    check = drift_check(distance, run.distance)
    training_indices = read_training_indices(OJA_INDEX)
    oja_value = float(z @ read_weights(OJA_WEIGHTS, features))
    result = {
        "synthetic": True,
        "creator_id": SYNTHETIC_ID,
        "name": SYNTHETIC_NAME,
        "raw": {key: value for key, value in row.items()},
        "z": {feature: float(v) for feature, v in zip(features, z)},
        "som_label": str(selection["chosen_label"]),
        "figure_seed": int(selection["figure_seed"]),
        "bmu": {"neuron": neuron, "row": r, "col": c, "distance": distance},
        "drift": check,
        "oja_index": oja_value,
        "oja_rank": index_rank(oja_value, training_indices),
    }
    (out / "demo.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "report_demo.md").write_text("\n".join(report_lines(result)) + "\n", encoding="utf-8")
    print(f"maintenance -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
