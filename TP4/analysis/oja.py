"""Oja's neuron against PC1: comparison, seed dispersion and convergence evidence (OJA-01, OJA-02, D-01..D-06).

Run from TP4/ with `make oja` (or `.venv/bin/python analysis/oja.py`). It runs analysis/series_oja.json (the
example config of neuron/, seeds 1 to 10) through the C binary with sweep.py, reads every run as C wrote it,
and writes under analysis/results/oja/ (not versioned) the comparison of the figure seed with the first
principal component of `make pca`: abs(cos) between the vectors, Pearson and tie-aware Spearman between the
Oja index and the PC1 score, and the overlap of the top 5 and the top 10.

The comparison with PC1 happens here and never in C (D-05): the neuron only learns, orients (D-02) and
projects. Python never re-orients a run: a seed whose w disagrees in sign with the PCA orientation is
reported as it is and fails the gates.

numpy, matplotlib through plots_style and the standard library are the only dependencies (Phase 1 D-06).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

TP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TP_DIR / "scripts"))
sys.path.insert(0, str(TP_DIR / "analysis"))

import plots_style  # noqa: E402,F401
import som  # noqa: E402
import sweep  # noqa: E402
from creadores import load_creadores  # noqa: E402
from pca import _pearson, dominant_topics  # noqa: E402

SERIES = TP_DIR / "analysis" / "series_oja.json"
DEFAULT_OUT = TP_DIR / "analysis" / "results" / "oja"
PCA_DIR = TP_DIR / "analysis" / "results" / "pca" / "audited"
FIGURE_SEED = 1
COS_MIN = 0.99
TOP_KS = (5, 10)
TRACE_FIXED = ["epoch", "eta", "w_norm", "delta_w"]
METRICS_KEYS = ("seed", "n_samples", "n_features", "epochs", "eta0", "eta_final", "pivot")
INDEX_COLUMNS = ["creator_id", "name", "oja_index", "pc1_score", "rank_oja", "rank_pc1", "dominant_topic",
                 "followers"]
SEEDS_COLUMNS = ["seed", "abs_cos", "cos", "pivot", "sign_flipped", "w_norm_final", "delta_w_final"]


@dataclass(frozen=True)
class OjaRun:
    run_dir: Path
    metrics: dict
    features: list[str]
    w: np.ndarray  # (p,) unit weight vector, with the D-02 sign applied by C
    index: np.ndarray  # (n,) projection of the creators on w
    trace: np.ndarray  # (epochs + 1, 4 + p): TRACE_FIXED then the weights before renormalizing


@dataclass(frozen=True)
class PcaRef:
    features: list[str]
    v1: np.ndarray  # (p,) PC1 eigenvector, oriented by pca.orient
    pc1: np.ndarray  # (n,) PC1 score of every creator
    creator_ids: list[str]
    names: list[str]


# ----------------------------------------------------------------------------------------------
# Readers
# ----------------------------------------------------------------------------------------------


def _read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    if not path.is_file():
        raise ValueError(f"{path}: file not found")
    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.reader(file))
    if not rows:
        raise ValueError(f"{path}: empty file")
    return rows[0], rows[1:]


def _floats(path: Path, rows: list[list[str]], width: int) -> np.ndarray:
    for number, row in enumerate(rows, start=2):
        if len(row) != width:
            raise ValueError(f"{path}: line {number} has {len(row)} cells, expected {width}")
    try:
        return np.array([[float(cell) for cell in row] for row in rows], dtype=np.float64).reshape(
            len(rows), width)
    except ValueError as error:
        raise ValueError(f"{path}: {error}") from error


def read_oja_run(run_dir) -> OjaRun:
    """Parse a run folder of the Oja model; any contract mismatch raises ValueError naming the file (T-03-07)."""
    run_dir = Path(run_dir)
    metrics_path = run_dir / "metrics.json"
    try:
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"{metrics_path}: cannot read the metrics: {error}") from error
    if not isinstance(metrics, dict):
        raise ValueError(f"{metrics_path}: not a JSON object")
    missing = [key for key in METRICS_KEYS if key not in metrics]
    if missing:
        raise ValueError(f"{metrics_path}: missing keys {missing}")
    n, p, epochs = int(metrics["n_samples"]), int(metrics["n_features"]), int(metrics["epochs"])

    weights_path = run_dir / "weights.csv"
    features, rows = _read_csv(weights_path)
    if len(features) != p or len(rows) != 1:
        raise ValueError(f"{weights_path}: expected a header of {p} features and one row, found "
                         f"{len(features)} columns and {len(rows)} rows")
    w = _floats(weights_path, rows, p)[0]

    index_path = run_dir / "index.csv"
    header, rows = _read_csv(index_path)
    if header != ["sample", "index"]:
        raise ValueError(f"{index_path}: header must be sample,index, found {header}")
    if len(rows) != n:
        raise ValueError(f"{index_path}: {len(rows)} rows but metrics.json says n_samples = {n}")
    table = _floats(index_path, rows, 2)
    if not np.array_equal(table[:, 0], np.arange(n, dtype=np.float64)):
        raise ValueError(f"{index_path}: the sample column must be 0..{n - 1} in order")

    trace_path = run_dir / "trace.csv"
    header, rows = _read_csv(trace_path)
    if header != TRACE_FIXED + features:
        raise ValueError(f"{trace_path}: header must be {TRACE_FIXED} followed by the weights.csv features")
    if len(rows) != epochs + 1:
        raise ValueError(f"{trace_path}: {len(rows)} rows but epochs + 1 = {epochs + 1}")
    trace = _floats(trace_path, rows, len(header))
    return OjaRun(run_dir, metrics, features, w, table[:, 1], trace)


def _read_pca_table(path: Path) -> tuple[list[str], list[list[str]]]:
    if not path.is_file():
        raise SystemExit(f"{path} not found; run `make pca`")
    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.reader(file))
    return rows[0], rows[1:]


def read_pca(pca_dir=PCA_DIR) -> PcaRef:
    """The PC1 eigenvector (already oriented) and the PC1 scores written by `make pca` for the audited set."""
    pca_dir = Path(pca_dir)
    vectors_path, scores_path = pca_dir / "eigenvectors.csv", pca_dir / "scores.csv"
    header, rows = _read_pca_table(vectors_path)
    if len(header) < 2 or header[0] != "variable" or header[1] != "PC1":
        raise ValueError(f"{vectors_path}: header must start with variable,PC1, found {header[:2]}")
    features = [row[0] for row in rows]
    v1 = np.array([float(row[1]) for row in rows], dtype=np.float64)

    header, rows = _read_pca_table(scores_path)
    if header[:3] != ["creator_id", "name", "PC1"]:
        raise ValueError(f"{scores_path}: header must start with creator_id,name,PC1, found {header[:3]}")
    return PcaRef(features, v1, np.array([float(row[2]) for row in rows], dtype=np.float64),
                  [row[0] for row in rows], [row[1] for row in rows])


# ----------------------------------------------------------------------------------------------
# Comparison with PC1 (OJA-02)
# ----------------------------------------------------------------------------------------------


def abs_cos(a, b) -> float:
    """abs(a . b) / (|a| |b|): the sign-free alignment of two directions."""
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denominator == 0.0:
        raise ValueError("abs_cos of a zero vector")
    return abs(float(a @ b)) / denominator


def _signed_cos(a, b) -> float:
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    return float(a @ b) / float(np.linalg.norm(a) * np.linalg.norm(b))


def top_k(values, k: int) -> np.ndarray:
    """Indices of the k largest values; ties keep the row order (stable)."""
    return np.argsort(-np.asarray(values, dtype=np.float64), kind="stable")[:k]


def overlap(a, b) -> int:
    """Number of indices two top-k lists share."""
    return len(set(int(i) for i in a) & set(int(i) for i in b))


def compare(w, index, v1, pc1) -> dict:
    """Oja against PC1: both vectors carry the D-02 sign, so cos is signed and a flip shows as -1."""
    index, pc1 = np.asarray(index, dtype=np.float64), np.asarray(pc1, dtype=np.float64)
    result = {
        "abs_cos": abs_cos(w, v1),
        "cos": _signed_cos(w, v1),
        "pearson": _pearson(index, pc1),
        "spearman": som.spearman_ties(index, pc1),
    }
    for k in TOP_KS:
        result[f"overlap_at_{k}"] = overlap(top_k(index, k), top_k(pc1, k))
    result["max_abs_diff"] = float(np.max(np.abs(index - pc1)))
    return result


def seeds_table(runs: dict, v1) -> list[dict]:
    """One row per seed, in seed order: alignment with PC1 and the training indicators of metrics.json."""
    rows = []
    for seed in sorted(runs):
        run = runs[seed]
        rows.append({
            "seed": int(seed),
            "abs_cos": abs_cos(run.w, v1),
            "cos": _signed_cos(run.w, v1),
            "pivot": run.metrics["pivot"],
            "sign_flipped": int(run.metrics.get("sign_flipped", 0)),
            "w_norm_final": float(run.metrics.get("w_norm_final", float("nan"))),
            "delta_w_final": float(run.metrics.get("delta_w_final", float("nan"))),
        })
    return rows


# ----------------------------------------------------------------------------------------------
# The series
# ----------------------------------------------------------------------------------------------


def run_series(series_path=SERIES, workers=None) -> tuple[Path, dict]:
    """The same calls as som_stage.run_stage: plan, build, run every seed, summary.csv. Returns the sweep folder
    and {seed: run folder}; a run that did not end ok stops everything."""
    series_file = Path(series_path).resolve()
    series = sweep.load_series(series_file)
    tasks = sweep.plan(series)
    sweep.build_binary()
    sweep_dir = sweep.create_sweep_dir(series)
    shutil.copy(series.path, sweep_dir / "series.json")
    sweep.write_plan(series, sweep_dir / "plan.json")
    varied = sweep.varied_keys(series)
    rows = sweep.run_all(tasks, sweep_dir, workers or series.workers, varied)
    sweep.write_summary(rows, sweep_dir / "summary.csv", varied)
    failed = sum(1 for row in rows if row["status"] != "ok")
    if failed:
        raise SystemExit(f"{failed} of {len(rows)} runs failed; see {sweep_dir / 'summary.csv'}")
    return sweep_dir, {task.seed: sweep_dir / "runs" / task.name for task in tasks}


# ----------------------------------------------------------------------------------------------
# Writers (byte-stable: repr floats, "\n" line ends)
# ----------------------------------------------------------------------------------------------


def _fmt(value) -> str:
    return repr(float(value))


def _write_table(path: Path, header: list[str], rows: list[list]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _relative(path: Path) -> str:
    return Path(os.path.relpath(Path(path).resolve(), TP_DIR)).as_posix()


def _decimal(value: float, digits: int) -> str:
    """Spanish decimals for the report lines: comma instead of point (the deliverable is in Spanish)."""
    return f"{value:.{digits}f}".replace(".", ",")


def _scientific(value: float) -> str:
    return f"{value:.1e}".replace(".", ",")


def _rank_desc(values) -> np.ndarray:
    """1 = largest value; ties by row order."""
    order = np.argsort(-np.asarray(values, dtype=np.float64), kind="stable")
    ranks = np.empty(len(order), dtype=np.int64)
    ranks[order] = np.arange(1, len(order) + 1)
    return ranks


def _followers(creator_ids: list[str]) -> list[str]:
    data = load_creadores()
    if list(data.ids) != list(creator_ids):
        raise SystemExit("the creator order of datos/creadores.csv differs from analysis/results/pca/ (T-03-07)")
    column = data.values[:, data.columns.index("followers")]
    return [str(int(x)) if float(x).is_integer() else repr(float(x)) for x in column]


def index_table(run: OjaRun, pca_ref: PcaRef) -> list[list]:
    rank_oja, rank_pc1 = _rank_desc(run.index), _rank_desc(pca_ref.pc1)
    topics = dominant_topics(pca_ref.creator_ids)
    followers = _followers(pca_ref.creator_ids)
    return [[pca_ref.creator_ids[i], pca_ref.names[i], _fmt(run.index[i]), _fmt(pca_ref.pc1[i]),
             int(rank_oja[i]), int(rank_pc1[i]), topics[i], followers[i]] for i in range(len(run.index))]


def comparison_table(comp: dict) -> list[str]:
    """Report lines of the comparison: a two-column table, comma decimals, nothing else."""
    return [
        f"| Medida (seed {FIGURE_SEED}) | Valor |",
        "|---|---|",
        f"| abs(cos(w, v1)) | {_decimal(comp['abs_cos'], 6)} |",
        f"| cos(w, v1) con la convención de signo | {_decimal(comp['cos'], 6)} |",
        f"| Pearson índice vs score de PC1 | {_decimal(comp['pearson'], 4)} |",
        f"| Spearman índice vs score de PC1 | {_decimal(comp['spearman'], 4)} |",
        f"| overlap@5 | {comp['overlap_at_5']} de 5 |",
        f"| overlap@10 | {comp['overlap_at_10']} de 10 |",
        f"| mayor abs(índice − score PC1) | {_scientific(comp['max_abs_diff'])} |",
    ]


def _write_lines(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ----------------------------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Oja's neuron against PC1: comparison, dispersion, convergence.")
    parser.add_argument("--series", type=Path, default=SERIES, help="series JSON (default: analysis/series_oja.json)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output folder (default: analysis/results/oja)")
    parser.add_argument("--workers", type=int, help="parallel runs (default: every core)")
    args = parser.parse_args(argv)
    out: Path = args.out

    pca_ref = read_pca()  # refuse before running anything when `make pca` has not been run
    sweep_dir, run_dirs = run_series(args.series, args.workers)

    runs = {seed: read_oja_run(path) for seed, path in sorted(run_dirs.items())}
    for seed, run in runs.items():
        if run.features != pca_ref.features:
            raise SystemExit(f"seed {seed}: the features of {run.run_dir / 'weights.csv'} differ from "
                             "analysis/results/pca/audited/eigenvectors.csv (T-03-07)")
        if len(run.index) != len(pca_ref.creator_ids):
            raise SystemExit(f"seed {seed}: {len(run.index)} samples but PCA has {len(pca_ref.creator_ids)} creators")
    if FIGURE_SEED not in runs:
        raise SystemExit(f"the series has no seed {FIGURE_SEED}, the figure seed")
    figure = runs[FIGURE_SEED]

    out.mkdir(parents=True, exist_ok=True)
    _write_json(out / "runs.json", {
        "sweep_dir": _relative(sweep_dir),
        "runs": {str(seed): _relative(path) for seed, path in sorted(run_dirs.items())},
    })
    comp = compare(figure.w, figure.index, pca_ref.v1, pca_ref.pc1)
    _write_json(out / "comparison.json", {
        **comp,
        "figure_seed": FIGURE_SEED,
        "n_seeds": len(runs),
        "eta0": float(figure.metrics["eta0"]),
        "eta_final": float(figure.metrics["eta_final"]),
        "epochs": int(figure.metrics["epochs"]),
    })
    table = seeds_table(runs, pca_ref.v1)
    _write_table(out / "seeds.csv", SEEDS_COLUMNS,
                 [[row["seed"], _fmt(row["abs_cos"]), _fmt(row["cos"]), row["pivot"], row["sign_flipped"],
                   _fmt(row["w_norm_final"]), _fmt(row["delta_w_final"])] for row in table])
    _write_table(out / "index.csv", INDEX_COLUMNS, index_table(figure, pca_ref))
    _write_table(out / "weights.csv", ["variable", "w", "v1"],
                 [[name, _fmt(figure.w[i]), _fmt(pca_ref.v1[i])] for i, name in enumerate(figure.features)])
    _write_lines(out / "report_pc1.md", comparison_table(comp))
    print(f"oja -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
