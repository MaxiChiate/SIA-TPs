"""Reader of the Kohonen run files and independent numpy recomputation of every SOM measure (SOM-02, SOM-03).

The C binary (neuron/models/kohonen.c) writes qe, te and the occupancy summary. Nothing downstream trusts
those numbers until this module reproduces them from prototypes.csv and the input matrix: `read_run` parses
a run directory, `metrics_from_prototypes` recomputes the measures, and the tests compare both within 1e-12.
Seed stability (D-13, tie-aware Spearman of grid-distance vectors) and the stability medoid live here too,
and `run_binary` is the one place that launches the binary from Python (analysis/som_loo.py uses it).

numpy and the standard library only (Phase 1 D-06, REQUIREMENTS Out of Scope): no SOM or machine-learning
library searches a BMU or computes any of these measures.
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

TP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TP_DIR / "scripts"))
sys.path.insert(0, str(TP_DIR / "analysis"))

from sweep import BINARY, RESULT_PREFIX, build_binary  # noqa: E402,F401

ASSIGNMENTS_HEADER = ["sample", "bmu", "row", "col", "distance", "bmu2"]
OCCUPANCY_HEADER = ["neuron", "row", "col", "hits"]
TRACE_HEADER = ["epoch", "eta", "radius", "qe", "te"]
PROTOTYPES_PREFIX = ["neuron", "row", "col"]


@dataclass(frozen=True)
class SomRun:
    run_dir: Path
    metrics: dict
    k: int
    features: list[str]
    prototypes: np.ndarray  # k^2 x p, row index = neuron = row * k + col
    bmu: np.ndarray
    bmu2: np.ndarray
    distance: np.ndarray
    hits: np.ndarray
    trace: np.ndarray  # epochs + 1 rows x (epoch, eta, radius, qe, te)


# ---------- reading a run directory ----------

def _read_table(path: Path, expected: list[str] | None = None) -> tuple[list[str], list[list[str]]]:
    try:
        with path.open(newline="", encoding="utf-8") as file:
            rows = list(csv.reader(file))
    except OSError as error:
        raise ValueError(f"{path}: cannot read the file: {error}") from error
    if not rows:
        raise ValueError(f"{path}: empty file")
    header, body = rows[0], rows[1:]
    if expected is not None and header != expected:
        raise ValueError(f"{path}: header {header} differs from the expected {expected}")
    for number, row in enumerate(body, start=2):
        if len(row) != len(header):
            raise ValueError(f"{path}: line {number} has {len(row)} cells, the header has {len(header)}")
    return header, body


def read_run(run_dir: Path) -> SomRun:
    """Parse one run directory of plan 02-01. A header or neuron-numbering mismatch raises ValueError naming
    the file (T-02-04): columns are never silently misaligned."""
    run_dir = Path(run_dir)
    metrics_path = run_dir / "metrics.json"
    try:
        metrics = json.loads(metrics_path.read_text())
    except (OSError, ValueError) as error:
        raise ValueError(f"{metrics_path}: cannot read the metrics: {error}") from error
    if not isinstance(metrics, dict) or "grid_k" not in metrics:
        raise ValueError(f"{metrics_path}: not a Kohonen metrics object (no grid_k)")
    k = int(metrics["grid_k"])
    neurons = k * k

    proto_path = run_dir / "prototypes.csv"
    header, body = _read_table(proto_path)
    if header[:3] != PROTOTYPES_PREFIX or len(header) <= 3:
        raise ValueError(f"{proto_path}: header must start with {PROTOTYPES_PREFIX} followed by the features")
    if len(body) != neurons:
        raise ValueError(f"{proto_path}: {len(body)} neurons, grid_k {k} needs {neurons}")
    for line, row in enumerate(body):
        neuron, r, c = int(row[0]), int(row[1]), int(row[2])
        if neuron != r * k + c or neuron != line:
            raise ValueError(f"{proto_path}: line {line + 2}: neuron {neuron} is not row {r} * {k} + col {c}")
    features = header[3:]
    prototypes = np.array([[float(cell) for cell in row[3:]] for row in body], dtype=np.float64)

    assign_path = run_dir / "assignments.csv"
    _h, body = _read_table(assign_path, ASSIGNMENTS_HEADER)
    bmu = np.array([int(row[1]) for row in body], dtype=np.int64)
    distance = np.array([float(row[4]) for row in body], dtype=np.float64)
    bmu2 = np.array([int(row[5]) for row in body], dtype=np.int64)
    for line, row in enumerate(body):
        if int(row[0]) != line or int(row[1]) != int(row[2]) * k + int(row[3]):
            raise ValueError(f"{assign_path}: line {line + 2}: sample or neuron = row * {k} + col numbering broken")

    occ_path = run_dir / "occupancy.csv"
    _h, body = _read_table(occ_path, OCCUPANCY_HEADER)
    if len(body) != neurons:
        raise ValueError(f"{occ_path}: {len(body)} neurons, grid_k {k} needs {neurons}")
    for line, row in enumerate(body):
        if int(row[0]) != line or int(row[0]) != int(row[1]) * k + int(row[2]):
            raise ValueError(f"{occ_path}: line {line + 2}: neuron = row * {k} + col numbering broken")
    hits = np.array([int(row[3]) for row in body], dtype=np.int64)

    trace_path = run_dir / "trace.csv"
    _h, body = _read_table(trace_path, TRACE_HEADER)
    trace = np.array([[float(cell) for cell in row] for row in body], dtype=np.float64).reshape(-1, 5)

    return SomRun(run_dir, metrics, k, features, prototypes, bmu, bmu2, distance, hits, trace)


# ---------- independent recomputation ----------

def distances(X: np.ndarray, protos: np.ndarray) -> np.ndarray:
    """n x k^2 Euclidean distances: the square root of the sum of squared differences."""
    diff = X[:, None, :] - protos[None, :, :]
    return np.sqrt(np.sum(diff * diff, axis=2))


def metrics_from_prototypes(X: np.ndarray, protos: np.ndarray, k: int) -> dict:
    """qe, te, hits, both BMU arrays and the occupancy summary, from the prototypes alone. The stable argsort
    gives the lowest index on ties, as nearest() does in C; te counts a winner/runner-up pair as an error
    when |dr| + |dc| != 1, so diagonal neighbours are errors (D-04)."""
    X = np.asarray(X, dtype=np.float64)
    dist = distances(X, protos)
    order = np.argsort(dist, axis=1, kind="stable")
    bmu, bmu2 = order[:, 0], order[:, 1]
    best = dist[np.arange(len(X)), bmu]
    adjacent = np.abs(bmu // k - bmu2 // k) + np.abs(bmu % k - bmu2 % k) == 1
    hits = np.bincount(bmu, minlength=k * k)
    occupied = int(np.count_nonzero(hits))
    return {
        "qe": float(best.mean()),
        "te": float(np.mean(~adjacent)),
        "hits": hits,
        "bmu": bmu,
        "bmu2": bmu2,
        "distances": best,
        "occupied_neurons": occupied,
        "empty_fraction": float((k * k - occupied) / (k * k)),
        "mean_hits_occupied": float(len(X) / occupied),
        "max_hits": int(hits.max()),
        "singleton_neurons": int(np.count_nonzero(hits == 1)),
    }


def nearest_distance(x: np.ndarray, protos: np.ndarray) -> tuple[int, float]:
    """(index, distance) of the prototype nearest to one row; the lowest index wins ties."""
    diff = protos - np.asarray(x, dtype=np.float64)[None, :]
    dist = np.sqrt(np.sum(diff * diff, axis=1))
    index = int(np.argmin(dist))
    return index, float(dist[index])


# ---------- running the binary ----------

def run_binary(config: dict, cwd: Path) -> Path:
    """Write cwd/config.json, run the binary from cwd with an argument list (no shell) and return the run
    directory it printed. A non-zero exit raises RuntimeError with the last stderr line (T-02-05)."""
    cwd = Path(cwd)
    (cwd / "config.json").write_text(json.dumps(config, indent=2) + "\n")
    process = subprocess.run([str(BINARY), "config.json"], cwd=cwd, capture_output=True, text=True)
    if process.returncode != 0:
        reason = process.stderr.strip().splitlines()[-1:] or [f"exit code {process.returncode}"]
        raise RuntimeError(reason[0])
    printed = [line for line in process.stdout.splitlines() if line.startswith(RESULT_PREFIX)]
    if not printed:
        raise RuntimeError("the binary printed no results directory")
    return cwd / printed[-1][len(RESULT_PREFIX):].strip()
