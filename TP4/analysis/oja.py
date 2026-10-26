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

import plots_style  # noqa: E402
import som  # noqa: E402
import sweep  # noqa: E402
from creadores import load_creadores  # noqa: E402
from pca import TOPICS, _pearson, dominant_topics  # noqa: E402

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
# Dispersion across seeds, convergence per epoch and the pivot margin (D-01, D-02, D-03)
# ----------------------------------------------------------------------------------------------


def dispersion(runs: dict, v1) -> dict:
    """How much the 10 seeds disagree (D-03): alignment with PC1, orientation, pivots, pairwise alignment of
    the weight vectors and the per-creator spread of the index across seeds."""
    seeds = sorted(runs)
    if len(seeds) < 2:
        raise ValueError("dispersion needs at least two seeds")
    weights = np.array([runs[seed].w for seed in seeds])
    unit = weights / np.linalg.norm(weights, axis=1, keepdims=True)
    pairs = (unit @ unit.T)[np.triu_indices(len(seeds), 1)]
    aligned = np.array([abs_cos(runs[seed].w, v1) for seed in seeds])
    same_side = np.array([float(runs[seed].w @ np.asarray(v1, dtype=np.float64)) > 0 for seed in seeds])
    spread = np.array([runs[seed].index for seed in seeds])
    spread = spread.max(axis=0) - spread.min(axis=0)
    worst = int(np.argmin(aligned))
    return {
        "n_seeds": len(seeds),
        "n_abs_cos_above": int(np.sum(aligned > COS_MIN)),
        "n_same_orientation": int(np.sum(same_side)),
        "pivots": sorted({str(runs[seed].metrics["pivot"]) for seed in seeds}),
        "min_pairwise_abs_cos": float(np.min(np.abs(pairs))),
        "mean_pairwise_abs_cos": float(np.mean(np.abs(pairs))),
        "min_pairwise_cos": float(np.min(pairs)),
        "max_index_range": float(np.max(spread)),
        "mean_index_range": float(np.mean(spread)),
        "worst_one_minus_abs_cos": float(1.0 - aligned[worst]),
        "worst_seed": int(seeds[worst]),
    }


def convergence_rows(seed: int, trace, v1) -> list[dict]:
    """Per epoch: eta, w_norm and delta_w as C wrote them, and abs(cos(w_e, v1)) computed here (D-01) on the
    trace weights normalized to length 1 (the trace holds w before renormalizing)."""
    trace = np.asarray(trace, dtype=np.float64)
    v1 = np.asarray(v1, dtype=np.float64)
    weights = trace[:, len(TRACE_FIXED):]
    norms = np.linalg.norm(weights, axis=1)
    if np.any(norms == 0.0):
        raise ValueError(f"seed {seed}: the trace has a zero weight vector")
    cosines = np.abs((weights / norms[:, None]) @ (v1 / np.linalg.norm(v1)))
    return [{"seed": int(seed), "epoch": int(trace[i, 0]), "eta": float(trace[i, 1]),
             "w_norm": float(trace[i, 2]), "delta_w": float(trace[i, 3]), "abs_cos": float(cosines[i])}
            for i in range(trace.shape[0])]


def pivot_margin(v1, features: list[str]) -> dict:
    """The two largest |coefficients| of PC1: the D-02 sign convention rests on the gap between them, and on
    these data it is small (average_caption_words +0.2521 against average_impressions -0.2493)."""
    v1 = np.asarray(v1, dtype=np.float64)
    order = np.argsort(-np.abs(v1), kind="stable")
    first, second = int(order[0]), int(order[1])
    return {
        "first": features[first], "first_coef": float(v1[first]),
        "second": features[second], "second_coef": float(v1[second]),
        "margin": float(abs(v1[first]) - abs(v1[second])),
    }


CONVERGENCE_COLUMNS = ["seed", "epoch", "eta", "w_norm", "delta_w", "abs_cos"]
FLOOR = 1e-16  # 1 - abs(cos) is drawn on a log axis; a perfect alignment is floored here


def plot_convergence(rows: list[dict], params: dict, out_stem) -> None:
    """Three panels on the epoch axis: 1 - abs(cos(w_e, v1)), abs(w) before renormalizing and ||delta w||. The
    10 seeds are thin lines in one neutral colour (the palette has 8 slots), the figure seed is the first slot."""
    plt = plots_style.apply_style()
    by_seed: dict[int, list[dict]] = {}
    for row in rows:
        by_seed.setdefault(row["seed"], []).append(row)
    highlight = plots_style.palette_for(["seed"])["seed"]

    fig, axes = plt.subplots(3, 1, figsize=(9, 9.5), sharex=True)
    panels = (
        (axes[0], lambda r: max(1.0 - r["abs_cos"], FLOOR), "1 − |cos(w_e, v1)|", True, 0),
        (axes[1], lambda r: r["w_norm"], "|w| antes de renormalizar", False, 0),
        (axes[2], lambda r: r["delta_w"], "‖Δw‖ de la época", True, 1),
    )
    for ax, value, label, log, first_epoch in panels:
        for seed in sorted(by_seed):
            if seed == FIGURE_SEED:
                continue
            series = [r for r in by_seed[seed] if r["epoch"] >= first_epoch]
            ax.plot([r["epoch"] for r in series], [value(r) for r in series], color=plots_style.TEXT_SECONDARY,
                    linewidth=0.7, alpha=0.8)
        if FIGURE_SEED in by_seed:
            series = [r for r in by_seed[FIGURE_SEED] if r["epoch"] >= first_epoch]
            ax.plot([r["epoch"] for r in series], [value(r) for r in series], color=highlight, linewidth=1.8,
                    zorder=3)
        if log:
            ax.set_yscale("log")
        ax.set_ylabel(label)
    axes[1].axhline(1.0, color=plots_style.GRID, linewidth=1, zorder=0)
    axes[2].set_xlabel("época")
    handles = [plt.Line2D([], [], color=highlight, linewidth=1.8),
               plt.Line2D([], [], color=plots_style.TEXT_SECONDARY, linewidth=0.7)]
    axes[0].legend(handles, [f"seed {FIGURE_SEED}", f"las otras {len(by_seed) - 1} seeds"], frameon=False,
                   fontsize=9, loc="upper right")
    axes[0].set_title(
        f"Convergencia de la neurona de Oja a PC1 ({len(by_seed)} seeds): η0 = {_compact(params['eta0'])}, "
        f"ηf = {_compact(params['eta_final'])}, {params['epochs']} épocas",
        fontsize=11, loc="left")
    fig.tight_layout()
    plots_style.save_figure(fig, out_stem)


def plot_oja_vs_pc1(index, pc1, topic_labels, comparison, out_stem) -> None:
    """Scatter of the PC1 score (x) against the Oja index (y) for the figure seed: one point per creator, coloured
    by dominant topic, with the identity line and the agreement statistics of `comparison` (OJA-02)."""
    plt = plots_style.apply_style()
    index, pc1 = np.asarray(index, dtype=np.float64), np.asarray(pc1, dtype=np.float64)
    order = [label for _, label in TOPICS]
    colors = plots_style.palette_for(order)

    slide = plots_style.variant() == "slide"
    fig, ax = plt.subplots(figsize=plots_style.figsize((8, 7)))
    low, high = float(min(index.min(), pc1.min())), float(max(index.max(), pc1.max()))
    pad = 0.05 * (high - low)
    ax.plot([low - pad, high + pad], [low - pad, high + pad], color=plots_style.GRID, linewidth=1.2, zorder=1,
            label="identidad (y = x)")
    for label in order:
        mask = np.array([t == label for t in topic_labels])
        ax.scatter(pc1[mask], index[mask], s=60, color=colors[label], edgecolor=plots_style.SURFACE, linewidth=1.2,
                   label=f"{label} (n = {int(mask.sum())})", zorder=3)
    ax.set_xlim(low - pad, high + pad)
    ax.set_ylim(low - pad, high + pad)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("score de PC1")
    ax.set_ylabel(f"índice de Oja (seed {FIGURE_SEED})")
    if not slide:  # the slide has its own title
        ax.set_title(f"Índice de Oja contra la proyección sobre PC1 ({len(index)} creadores)", fontsize=11,
                     loc="left")
    stats = (f"|cos(w, v1)| = {_decimal(comparison['abs_cos'], 7)}\nPearson = {_decimal(comparison['pearson'], 4)}\n"
             f"Spearman = {_decimal(comparison['spearman'], 4)}")
    box = {"facecolor": plots_style.SURFACE, "edgecolor": plots_style.GRID, "boxstyle": "round,pad=0.4"}
    if slide:  # square plot on the left; legend and agreement statistics in the free space on its right
        ax.text(1.04, 0.0, stats, transform=ax.transAxes, ha="left", va="bottom",
                fontsize=plots_style.fontsize(9), color=plots_style.TEXT_PRIMARY, bbox=box)
        ax.legend(title="tema dominante", loc="upper left", bbox_to_anchor=(1.04, 1.0), frameon=True,
                  facecolor=plots_style.SURFACE, edgecolor=plots_style.GRID, fontsize=plots_style.fontsize(9))
    else:
        ax.text(0.97, 0.05, stats, transform=ax.transAxes, ha="right", va="bottom", fontsize=9,
                color=plots_style.TEXT_PRIMARY, bbox=box)
        ax.legend(title="tema dominante", loc="upper left", frameon=True, facecolor=plots_style.SURFACE,
                  edgecolor=plots_style.GRID, fontsize=9)
    fig.tight_layout()
    plots_style.save_figure(fig, out_stem)


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


def _signed(value: float, digits: int) -> str:
    return f"{value:+.{digits}f}".replace(".", ",")


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


def _compact(value: float) -> str:
    return f"{value:g}".replace(".", ",")


def pc1_bullets(disp: dict) -> list[str]:
    """The four seed bullets that follow the comparison table (D-03)."""
    n = disp["n_seeds"]
    pivots = disp["pivots"]
    pivot = f"pivote de todas: {pivots[0]}" if len(pivots) == 1 else f"pivotes distintos: {', '.join(pivots)}"
    return [
        f"- Seeds con abs(cos(w, v1)) > {_compact(COS_MIN)}: {disp['n_abs_cos_above']} de {n}.",
        f"- Seeds con la orientación de PCA (w · v1 > 0): {disp['n_same_orientation']} de {n}; {pivot}.",
        f"- abs(cos) entre pares de seeds: mínimo {_decimal(disp['min_pairwise_abs_cos'], 7)}, "
        f"media {_decimal(disp['mean_pairwise_abs_cos'], 7)}.",
        f"- Rango del índice por creador entre seeds: máximo {_scientific(disp['max_index_range'])}, "
        f"media {_scientific(disp['mean_index_range'])}.",
    ]


def first_epoch_below(rows: list[dict], threshold: float) -> int | None:
    for row in rows:
        if 1.0 - row["abs_cos"] < threshold:
            return row["epoch"]
    return None


def convergence_bullets(figure: OjaRun, figure_rows: list[dict], disp: dict, margin: dict) -> list[str]:
    """Bullets of report_convergence.md: the training parameters, where seed 1 ended and the pivot margin."""
    m = figure.metrics
    epochs, n = int(m["epochs"]), int(m["n_samples"])
    reached = first_epoch_below(figure_rows, 1e-3)
    reached_text = f"época {reached}" if reached is not None else "ninguna época"
    return [
        f"- Parámetros: η0 = {_compact(float(m['eta0']))}, ηf = {_compact(float(m['eta_final']))}, "
        f"{epochs} épocas ({epochs * n} actualizaciones: {epochs} × {n} creadores).",
        f"- Cota de estabilidad: η0 · máx ‖x‖² = {_decimal(float(m['eta0_max_x2']), 4)} (debe ser menor que 1).",
        f"- Seed {FIGURE_SEED} al final del entrenamiento: |w| = {_decimal(float(m['w_norm_final']), 5)} antes de "
        f"renormalizar y ‖Δw‖ = {_scientific(float(m['delta_w_final']))} en la última época.",
        f"- Peor seed ({disp['worst_seed']}): 1 − |cos(w, v1)| = {_scientific(disp['worst_one_minus_abs_cos'])}.",
        f"- Seed {FIGURE_SEED}: primera época con 1 − |cos(w_e, v1)| < 1e-3: {reached_text}.",
        f"- Margen del pivote: los dos mayores coeficientes de PC1 son {margin['first']} "
        f"({_signed(margin['first_coef'], 4)}) y {margin['second']} ({_signed(margin['second_coef'], 4)}), "
        f"con un margen de {_decimal(margin['margin'], 5)} en valor absoluto: es el límite de la convención "
        "de signo, que con otros datos podría elegir la otra variable e invertir w y el índice.",
    ]


# ----------------------------------------------------------------------------------------------
# Evidence of the maximum under both signs (OJA-03, D-06)
# ----------------------------------------------------------------------------------------------

EVIDENCE_TOP = 10
EVIDENCE_TARGETS = ("followers", *(name for name, _ in TOPICS))
SIGNS = (1, -1)  # +1 is the D-02 convention, -1 the opposite one
SIGN_LABELS = {1: "de D-02", -1: "opuesto"}
EVIDENCE_WEIGHT_COLUMNS = ["variable", "w"]
EVIDENCE_CORR_COLUMNS = ["target", "sign", "pearson", "spearman"]
EVIDENCE_TOP_COLUMNS = ["sign", "topic", "overlap_top10_by_share", "dominant_in_index_top10"]


def evidence(w, features, index, data, ids) -> dict:
    """The evidence behind "is the creator with the highest index the right choice for any campaign?" under both
    signs (D-06). `index` is in the order of `ids`; the raw followers and topic shares come from `data` (the
    Creadores of datos/creadores.csv) matched by creator id. Ties in a top-k keep the row order."""
    w, index = np.asarray(w, dtype=np.float64), np.asarray(index, dtype=np.float64)
    position = {cid: i for i, cid in enumerate(data.ids)}
    missing = [cid for cid in ids if cid not in position]
    if missing:
        raise ValueError(f"creators not found in the raw data: {missing[:3]}")
    rows = [position[cid] for cid in ids]
    raw = {name: data.values[rows, data.columns.index(name)] for name in EVIDENCE_TARGETS}
    shares = np.column_stack([raw[name] for name, _ in TOPICS])
    dominant = [TOPICS[int(np.argmax(shares[i]))][1] for i in range(len(ids))]

    order = np.argsort(-np.abs(w), kind="stable")
    weights = [{"variable": features[int(i)], "w": float(w[int(i)])} for i in order]

    correlations, top10, maximum = [], [], {}
    for target in EVIDENCE_TARGETS:
        for sign in SIGNS:
            signed = sign * index
            correlations.append({"target": target, "sign": sign, "pearson": _pearson(signed, raw[target]),
                                 "spearman": som.spearman_ties(signed, raw[target])})
    for sign in SIGNS:
        signed = sign * index
        top_index = top_k(signed, EVIDENCE_TOP)
        for name, label in TOPICS:
            top_share = top_k(raw[name], EVIDENCE_TOP)
            top10.append({"sign": sign, "topic": label, "overlap_top10_by_share": overlap(top_index, top_share),
                          "dominant_in_index_top10": sum(1 for i in top_index if dominant[int(i)] == label)})
        best = int(top_k(signed, 1)[0])
        maximum[f"{sign:+d}"] = {
            "creator_id": ids[best], "name": data.names[rows[best]], "dominant_topic": dominant[best],
            "followers": int(raw["followers"][best]), "index": float(signed[best]),
        }
    return {"weights": weights, "correlations": correlations, "top10": top10, "maximum": maximum}


def evidence_lines(ev: dict) -> list[str]:
    """Report lines of report_evidence.md: three tables and two bullets, comma decimals, nothing else."""
    lines = ["| Variable | w (convención D-02) |", "|---|---|"]
    lines += [f"| {row['variable']} | {_signed(row['w'], 4)} |" for row in ev["weights"]]
    corr = {(row["target"], row["sign"]): row for row in ev["correlations"]}
    lines += ["| Variable cruda | Pearson (D-02) | Spearman (D-02) | Pearson (signo opuesto) | "
              "Spearman (signo opuesto) |",
              "|---|---|---|---|---|"]
    for target in EVIDENCE_TARGETS:
        cells = [_signed(corr[(target, sign)][kind], 3) for sign in SIGNS for kind in ("pearson", "spearman")]
        lines.append(f"| {target} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} |")
    top = {(row["sign"], row["topic"]): row for row in ev["top10"]}
    lines += ["| Tema | Top 10 por porcentaje en común con el top 10 del índice (D-02) | "
              "Top 10 por porcentaje en común con el top 10 del índice (signo opuesto) | "
              "Creadores del top 10 del índice con ese tema dominante (D-02) | "
              "Creadores del top 10 del índice con ese tema dominante (signo opuesto) |",
              "|---|---|---|---|---|"]
    for _, label in TOPICS:
        lines.append(f"| {label} | {top[(1, label)]['overlap_top10_by_share']} de {EVIDENCE_TOP} | "
                     f"{top[(-1, label)]['overlap_top10_by_share']} de {EVIDENCE_TOP} | "
                     f"{top[(1, label)]['dominant_in_index_top10']} de {EVIDENCE_TOP} | "
                     f"{top[(-1, label)]['dominant_in_index_top10']} de {EVIDENCE_TOP} |")
    for sign in SIGNS:
        best = ev["maximum"][f"{sign:+d}"]
        lines.append(f"- Máximo con el signo {SIGN_LABELS[sign]}: {best['creator_id']} ({best['name']}), "
                     f"tema dominante {best['dominant_topic']}, {best['followers']} followers, "
                     f"índice {_signed(best['index'], 2)}.")
    return lines


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

    disp = dispersion(runs, pca_ref.v1)
    margin = pivot_margin(pca_ref.v1, pca_ref.features)
    _write_json(out / "dispersion.json", {**disp, "pivot_margin": margin})
    conv = [row for seed in sorted(runs) for row in convergence_rows(seed, runs[seed].trace, pca_ref.v1)]
    _write_table(out / "convergence.csv", CONVERGENCE_COLUMNS,
                 [[row["seed"], row["epoch"], _fmt(row["eta"]), _fmt(row["w_norm"]), _fmt(row["delta_w"]),
                   _fmt(row["abs_cos"])] for row in conv])
    _write_lines(out / "report_pc1.md", comparison_table(comp) + pc1_bullets(disp))
    figure_rows = [row for row in conv if row["seed"] == FIGURE_SEED]
    _write_lines(out / "report_convergence.md", convergence_bullets(figure, figure_rows, disp, margin))
    plot_convergence(conv, {"eta0": float(figure.metrics["eta0"]), "eta_final": float(figure.metrics["eta_final"]),
                            "epochs": int(figure.metrics["epochs"])}, out / "convergence")

    data = load_creadores()
    if list(data.ids) != list(pca_ref.creator_ids):
        raise SystemExit("the creator order of datos/creadores.csv differs from analysis/results/pca/ (T-03-07)")
    ev = evidence(figure.w, figure.features, figure.index, data, pca_ref.creator_ids)
    _write_table(out / "evidence_weights.csv", EVIDENCE_WEIGHT_COLUMNS,
                 [[row["variable"], _fmt(row["w"])] for row in ev["weights"]])
    _write_table(out / "evidence_correlations.csv", EVIDENCE_CORR_COLUMNS,
                 [[row["target"], f"{row['sign']:+d}", _fmt(row["pearson"]), _fmt(row["spearman"])]
                  for row in ev["correlations"]])
    _write_table(out / "evidence_top10.csv", EVIDENCE_TOP_COLUMNS,
                 [[f"{row['sign']:+d}", row["topic"], row["overlap_top10_by_share"], row["dominant_in_index_top10"]]
                  for row in ev["top10"]])
    _write_json(out / "evidence.json", {"figure_seed": FIGURE_SEED, "maximum": ev["maximum"]})
    _write_lines(out / "report_evidence.md", evidence_lines(ev))
    for _ in plots_style.iter_variants():  # report, then slide (D-08)
        plot_oja_vs_pc1(figure.index, pca_ref.pc1, dominant_topics(pca_ref.creator_ids), comp, out / "oja_vs_pc1")
    print(f"oja -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
