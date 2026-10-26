"""PCA of the correlation matrix by eigenvalues, with scree, loadings, biplot and sensitivity (DATA-04, DATA-05).

Run from TP4/ with `make pca` (or `.venv/bin/python analysis/pca.py`). It reads the prepared z-scored
matrices of datos/prepared/ (the same files the C models read) and writes, for the audited 26-variable
set and for the labelled 31-column sensitivity run, the eigenvalues, eigenvectors, loadings, scores,
three figures and decision.json under analysis/results/pca/ (not versioned), plus the comparison
sensitivity.json and sensitivity.md.

The method is the one written in section 5 of deliverables/01-datos-pca.md before this module existed
(D-12): PCA of the correlation matrix by `np.linalg.eigh`, k = smallest number of components whose
cumulative variance reaches 80 %, Kaiser (eigenvalue > 1) as a control, and each eigenvector oriented so
its largest-magnitude coefficient is positive. Phase 3 (Oja) reuses that orientation.

numpy and matplotlib only (D-06): no scikit-learn, no scipy, no dataframe library.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

TP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TP_DIR / "scripts"))
sys.path.insert(0, str(TP_DIR / "analysis"))

import plots_style  # noqa: E402
from creadores import PREPARED_DIR, load_creadores, load_meta  # noqa: E402

DEFAULT_OUT_DIR = TP_DIR / "analysis" / "results" / "pca"

VARIANCE_THRESHOLD = 0.80
NULL_EIGENVALUE = 1e-10
BIPLOT_LABELS = 8
ARROW_FILL = 0.9  # the longest arrow reaches this fraction of the largest score
TOP_LOADINGS = 6

# (prepared stem, output folder, human label of the figure titles)
VARIANTS = (
    ("creadores_zscore", "audited", "Conjunto auditado (26 variables)"),
    (
        "creadores_zscore_all31",
        "all31_sensitivity",
        "SENSIBILIDAD (31 columnas, no es el conjunto auditado)",
    ),
)

# Raw topic shares that colour the biplot (all four, including the dropped topic_art_pct).
TOPICS = (
    ("topic_football_pct", "fútbol"),
    ("topic_makeup_pct", "maquillaje"),
    ("topic_dogs_pct", "perros"),
    ("topic_art_pct", "arte"),
)


@dataclass(frozen=True)
class PcaResult:
    features: list[str]
    eigenvalues: np.ndarray  # (p,) descending
    eigenvectors: np.ndarray  # (p, p), one eigenvector per column
    explained: np.ndarray  # eigenvalues / sum
    cumulative: np.ndarray  # cumsum(explained)


def correlation_matrix(z: np.ndarray) -> np.ndarray:
    """z.T @ z / (n - 1): the prepared matrix is z-scored with ddof = 1, so this is the correlation."""
    z = np.asarray(z, dtype=np.float64)
    return z.T @ z / (z.shape[0] - 1)


def orient(vectors: np.ndarray) -> np.ndarray:
    """Flip each column so its largest-magnitude coefficient is positive (section 5 convention)."""
    vectors = np.array(vectors, dtype=np.float64, copy=True)
    pivot = np.argmax(np.abs(vectors), axis=0)
    signs = np.sign(vectors[pivot, np.arange(vectors.shape[1])])
    signs[signs == 0] = 1.0
    return vectors * signs


def pca_eigh(z: np.ndarray, features: list[str]) -> PcaResult:
    """Eigenvalues and eigenvectors of the correlation matrix, descending, oriented."""
    corr = correlation_matrix(z)
    if corr.shape[0] != len(features):
        raise ValueError(f"{corr.shape[0]} columns but {len(features)} feature names")
    values, vectors = np.linalg.eigh(corr)
    order = np.argsort(values, kind="stable")[::-1]
    values = values[order]
    vectors = orient(vectors[:, order])
    explained = values / values.sum()
    return PcaResult(
        features=list(features),
        eigenvalues=values,
        eigenvectors=vectors,
        explained=explained,
        cumulative=np.cumsum(explained),
    )


def k_by_variance(result: PcaResult, threshold: float = VARIANCE_THRESHOLD) -> int:
    """Smallest k whose cumulative explained variance reaches the threshold."""
    return int(np.argmax(result.cumulative >= threshold)) + 1


def kaiser_count(result: PcaResult) -> int:
    """Number of eigenvalues greater than 1 (control criterion, D-12)."""
    return int(np.sum(result.eigenvalues > 1.0))


def scores(result: PcaResult, z: np.ndarray) -> np.ndarray:
    """Coordinates of each creator on the components: z @ V."""
    return np.asarray(z, dtype=np.float64) @ result.eigenvectors


def loadings(result: PcaResult) -> np.ndarray:
    """Correlation of each variable with each component: V * sqrt(eigenvalue)."""
    return result.eigenvectors * np.sqrt(np.maximum(result.eigenvalues, 0.0))


def reconstruct(result: PcaResult, component_scores: np.ndarray) -> np.ndarray:
    """Back to the z-scored space: scores @ V.T (exact when all components are kept)."""
    return np.asarray(component_scores, dtype=np.float64) @ result.eigenvectors.T


def read_prepared(stem: str, prepared_dir: Path = PREPARED_DIR):
    """Read datos/prepared/{stem}.csv and its meta file; return (features, Z, meta).

    The header must equal meta['features'] and the row count meta['n_rows'] (T-01-17): a mismatch is an
    error, never a silent reordering.
    """
    csv_path = Path(prepared_dir) / f"{stem}.csv"
    meta_path = Path(prepared_dir) / f"{stem}.meta.json"
    for path in (csv_path, meta_path):
        if not path.exists():
            raise FileNotFoundError(f"{path} not found; run `make prepare`")
    meta = load_meta(meta_path)
    with csv_path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.reader(file))
    header, body = rows[0], rows[1:]
    if header != list(meta["features"]):
        raise ValueError(f"{csv_path}: header differs from the features in {meta_path.name}")
    if len(body) != int(meta["n_rows"]):
        raise ValueError(
            f"{csv_path}: {len(body)} rows but {meta_path.name} says n_rows = {meta['n_rows']}"
        )
    if len(meta["creator_id"]) != len(body) or len(meta["name"]) != len(body):
        raise ValueError(f"{meta_path.name}: creator_id/name lengths differ from the row count")
    z = np.array([[float(cell) for cell in row] for row in body], dtype=np.float64)
    return list(header), z, meta


def _ranks(values: np.ndarray) -> np.ndarray:
    return np.argsort(np.argsort(values)).astype(np.float64)


def _pearson(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean()
    b = b - b.mean()
    return float(a @ b / np.sqrt((a @ a) * (b @ b)))


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    """Pearson correlation of the ranks (argsort of argsort; no ties expected)."""
    return _pearson(_ranks(np.asarray(a, dtype=np.float64)), _ranks(np.asarray(b, dtype=np.float64)))


# ----------------------------------------------------------------------------------------------
# Tables
# ----------------------------------------------------------------------------------------------


def _fmt(value: float) -> str:
    return repr(float(value))


def _write_table(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def _component_names(p: int) -> list[str]:
    return [f"PC{i + 1}" for i in range(p)]


def write_tables(out: Path, result: PcaResult, z: np.ndarray, meta: dict) -> None:
    p = len(result.features)
    names = _component_names(p)
    _write_table(
        out / "eigenvalues.csv",
        ["component", "eigenvalue", "explained", "cumulative"],
        [
            [names[i], _fmt(result.eigenvalues[i]), _fmt(result.explained[i]), _fmt(result.cumulative[i])]
            for i in range(p)
        ],
    )
    _write_table(
        out / "eigenvectors.csv",
        ["variable", *names],
        [[f, *(_fmt(v) for v in result.eigenvectors[i])] for i, f in enumerate(result.features)],
    )
    _write_table(
        out / "loadings.csv",
        ["variable", *names],
        [[f, *(_fmt(v) for v in loadings(result)[i])] for i, f in enumerate(result.features)],
    )
    s = scores(result, z)
    _write_table(
        out / "scores.csv",
        ["creator_id", "name", *names],
        [[meta["creator_id"][i], meta["name"][i], *(_fmt(v) for v in s[i])] for i in range(s.shape[0])],
    )


def decision(result: PcaResult, variant: str) -> dict:
    """The decision.json payload: the section-5 rule applied as written."""
    k80 = k_by_variance(result)
    kaiser = kaiser_count(result)
    load = loadings(result)
    top = {}
    for c in range(3):
        order = np.argsort(-np.abs(load[:, c]), kind="stable")[:TOP_LOADINGS]
        top[f"PC{c + 1}"] = [[result.features[i], float(load[i, c])] for i in order]
    return {
        "variant": variant,
        "n_variables": len(result.features),
        "eigenvalue_sum": float(result.eigenvalues.sum()),
        "k_80": k80,
        "kaiser": kaiser,
        "rule_agrees": bool(k80 == kaiser),
        "explained_pc1": float(result.explained[0]),
        "explained_pc2": float(result.explained[1]),
        "cumulative_pc2": float(result.cumulative[1]),
        "null_eigenvalues": int(np.sum(np.abs(result.eigenvalues) < NULL_EIGENVALUE)),
        "min_eigenvalue": float(result.eigenvalues.min()),
        "top_loadings": top,
    }


# ----------------------------------------------------------------------------------------------
# Figures
# ----------------------------------------------------------------------------------------------


def plot_scree(result: PcaResult, dec: dict, title: str, out: Path) -> None:
    """Eigenvalues (top) and cumulative variance (bottom) on a shared component axis.

    Two panels instead of a twin y-axis: each has one scale, and the Kaiser line (eigenvalue 1) and the
    80 % line each sit on the panel whose unit they use.
    """
    plt = plots_style.apply_style()
    p = len(result.eigenvalues)
    k80 = dec["k_80"]
    x = np.arange(1, p + 1)
    blue = plots_style.palette_for(["a"])["a"]
    orange = plots_style._SERIES[1]
    slide = plots_style.variant() == "slide"
    if slide:  # side by side: two stacked panels would be too flat in the 2.6:1 slide box
        fig, (top, bottom) = plt.subplots(1, 2, figsize=plots_style.figsize((11, 7.5)), sharex=True)
    else:
        fig, (top, bottom) = plt.subplots(
            2, 1, figsize=plots_style.figsize((11, 7.5)), sharex=True, gridspec_kw={"height_ratios": [3, 2]}
        )

    colors = [orange if i + 1 == k80 else blue for i in range(p)]
    top.bar(x, result.eigenvalues, color=colors, width=0.7, edgecolor=plots_style.SURFACE, linewidth=1)
    top.axhline(1.0, color=plots_style.TEXT_SECONDARY, linewidth=1, linestyle="--")
    top.annotate("Kaiser (autovalor = 1)", (p + 0.4, 1.0), xytext=(0, 4), textcoords="offset points",
                 va="bottom", ha="right", color=plots_style.TEXT_SECONDARY, fontsize=plots_style.fontsize(9))
    top.set_ylabel("autovalor")
    agree = "coinciden" if dec["rule_agrees"] else "NO coinciden"
    if slide:  # the slide has its own title: panel titles only, the reading note in two short lines
        top.set_title("Autovalores", fontsize=plots_style.fontsize(12), loc="left")
        top.text(0.99, 0.93, f"k para 80 % = {k80} (barra naranja)\nKaiser: {dec['kaiser']} ({agree})",
                 transform=top.transAxes, ha="right", va="top", fontsize=plots_style.fontsize(9),
                 color=plots_style.TEXT_PRIMARY)
    else:
        top.set_title(f"{title}\nScree: autovalores y varianza acumulada", fontsize=12, loc="left")
        top.text(0.99, 0.93,
                 f"k para 80 % = {k80} (barra naranja)   |   Kaiser: {dec['kaiser']}   |   {agree}",
                 transform=top.transAxes, ha="right", va="top", fontsize=9, color=plots_style.TEXT_PRIMARY)

    bottom.plot(x, result.cumulative * 100, color=blue, linewidth=2, marker="o", markersize=5,
                markeredgecolor=plots_style.SURFACE)
    bottom.axhline(VARIANCE_THRESHOLD * 100, color=plots_style.TEXT_SECONDARY, linewidth=1, linestyle="--")
    bottom.annotate("80 %", (p + 0.4, VARIANCE_THRESHOLD * 100), xytext=(0, 4),
                    textcoords="offset points", va="bottom", ha="right",
                    color=plots_style.TEXT_SECONDARY, fontsize=plots_style.fontsize(9))
    bottom.plot([k80], [result.cumulative[k80 - 1] * 100], marker="o", markersize=9, color=orange,
                markeredgecolor=plots_style.SURFACE, markeredgewidth=2, linestyle="none")
    bottom.annotate(f"k = {k80}: {result.cumulative[k80 - 1] * 100:.1f} %",
                    (k80, result.cumulative[k80 - 1] * 100), xytext=(14, -48) if slide else (8, -16),
                    textcoords="offset points", fontsize=plots_style.fontsize(9),
                    color=plots_style.TEXT_PRIMARY)
    if slide:
        bottom.set_title("Varianza acumulada", fontsize=plots_style.fontsize(12), loc="left")
    bottom.set_ylim(0, 105)
    bottom.set_ylabel("varianza acumulada (%)")
    bottom.set_xlabel("componente principal")
    bottom.set_xticks(x)
    bottom.set_xticklabels([str(i) for i in x], fontsize=plots_style.fontsize(8))
    if slide:  # 15 pt tick labels collide past 9: label every other component
        top.set_xlabel("componente principal")
        for ax in (top, bottom):
            ax.set_xticks(x)
            ax.set_xticklabels([str(i) if i % 2 == 1 else "" for i in x], fontsize=plots_style.fontsize(8))
    fig.tight_layout()
    plots_style.save_figure(fig, out / "scree")


def plot_loadings(result: PcaResult, dec: dict, title: str, out: Path) -> None:
    plt = plots_style.apply_style()
    shown = max(dec["k_80"], 2)
    load = loadings(result)[:, :shown]
    p = len(result.features)
    fig, ax = plt.subplots(figsize=(max(7.0, 1.1 * shown + 5.5), 0.34 * p + 2.4))
    image = ax.imshow(load, cmap=plots_style.DIVERGING, vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(shown))
    ax.set_xticklabels(
        [f"PC{i + 1}\n{result.explained[i] * 100:.1f} %" for i in range(shown)], fontsize=9
    )
    ax.set_yticks(range(p))
    ax.set_yticklabels(result.features, fontsize=8)
    for i in range(p):
        for j in range(shown):
            value = load[i, j]
            ax.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=7,
                    color="white" if abs(value) > 0.6 else plots_style.TEXT_PRIMARY)
    for spine in ax.spines.values():
        spine.set_visible(False)
    colorbar = fig.colorbar(image, ax=ax, fraction=0.04, pad=0.02)
    colorbar.set_label("correlación variable-componente")
    ax.set_title(f"{title}\nCargas de PC1 a PC{shown} (componentes hasta k para 80 %)",
                 fontsize=11, loc="left")
    fig.tight_layout()
    plots_style.save_figure(fig, out / "loadings")


def dominant_topics(ids: list[str]) -> list[str]:
    """Label of the largest raw topic share of each creator, in the order of `ids`."""
    data = load_creadores()
    position = {cid: i for i, cid in enumerate(data.ids)}
    missing = [cid for cid in ids if cid not in position]
    if missing:
        raise ValueError(f"creators not found in datos/creadores.csv: {missing[:3]}")
    columns = [data.columns.index(name) for name, _ in TOPICS]
    labels = []
    for cid in ids:
        shares = data.values[position[cid], columns]
        labels.append(TOPICS[int(np.argmax(shares))][1])
    return labels


def plot_biplot(result: PcaResult, z: np.ndarray, meta: dict, title: str, out: Path) -> float:
    plt = plots_style.apply_style()
    s = scores(result, z)[:, :2]
    load = loadings(result)[:, :2]
    scale = ARROW_FILL * float(np.abs(s).max()) / float(np.abs(load).max())

    topic_labels = dominant_topics(meta["creator_id"])
    order = [label for _, label in TOPICS]
    colors = plots_style.palette_for(order)

    slide = plots_style.variant() == "slide"
    fig, ax = plt.subplots(figsize=plots_style.figsize((11, 8.5)))
    ax.axhline(0, color=plots_style.GRID, linewidth=1, zorder=0)
    ax.axvline(0, color=plots_style.GRID, linewidth=1, zorder=0)

    norms = np.hypot(load[:, 0], load[:, 1])
    labelled = set(np.argsort(-norms, kind="stable")[:BIPLOT_LABELS].tolist())
    for i, feature in enumerate(result.features):
        tip = load[i] * scale
        if i in labelled:
            ax.annotate("", xy=tip, xytext=(0, 0),
                        arrowprops={"arrowstyle": "-|>", "color": plots_style.TEXT_PRIMARY,
                                    "linewidth": 1.4, "shrinkA": 0, "shrinkB": 0}, zorder=3)
        else:
            ax.annotate("", xy=tip, xytext=(0, 0),
                        arrowprops={"arrowstyle": "-", "color": plots_style.TEXT_SECONDARY,
                                    "linewidth": 0.6, "alpha": 0.45, "shrinkA": 0, "shrinkB": 0},
                        zorder=2)

    for label in order:
        mask = np.array([t == label for t in topic_labels])
        ax.scatter(s[mask, 0], s[mask, 1], s=70, color=colors[label], edgecolor=plots_style.SURFACE,
                   linewidth=1.5, label=f"{label} (n = {int(mask.sum())})", zorder=4)

    # Room on both sides for the labels, then stack them so near-collinear arrows do not overprint.
    x0, x1 = ax.get_xlim()
    ax.set_xlim(x0 - 0.28 * (x1 - x0), x1 + 0.28 * (x1 - x0))
    y0, y1 = ax.get_ylim()
    gap = (0.075 if slide else 0.04) * (y1 - y0)  # slide type is larger in a lower figure
    for side in (-1, 1):
        members = sorted((i for i in labelled if (load[i, 0] >= 0) == (side > 0)),
                         key=lambda i: load[i, 1])
        placed: list[float] = []
        for i in members:
            tip = load[i] * scale
            y = tip[1]
            while any(abs(y - other) < gap for other in placed):
                y += gap
            placed.append(y)
            if y != tip[1]:  # displaced label: thin leader back to the arrow tip
                ax.plot([tip[0], tip[0] + side * 0.12], [tip[1], y], color=plots_style.TEXT_SECONDARY,
                        linewidth=0.5, zorder=4)
            ax.text(tip[0] + side * 0.12, y, result.features[i], ha="left" if side > 0 else "right",
                    va="center", fontsize=plots_style.fontsize(8.5), color=plots_style.TEXT_PRIMARY, zorder=5)

    ax.set_xlabel(f"PC1 ({result.explained[0] * 100:.1f} %)")
    ax.set_ylabel(f"PC2 ({result.explained[1] * 100:.1f} %)")
    if not slide:  # the slide has its own title
        ax.set_title(
            f"{title}\nBiplot PC1-PC2. Flechas: correlación de cada variable con PC1 y PC2 "
            f"(factor de escala s = {scale:.2f}); {BIPLOT_LABELS} con mayor norma etiquetadas",
            fontsize=10.5, loc="left")
    legend = {"loc": "center left", "bbox_to_anchor": (1.01, 0.5)} if slide else {"loc": "best"}
    ax.legend(title="tema dominante", frameon=True, facecolor=plots_style.SURFACE,
              edgecolor=plots_style.GRID, fontsize=plots_style.fontsize(9), **legend)
    fig.tight_layout()
    plots_style.save_figure(fig, out / "biplot")
    return scale


# ----------------------------------------------------------------------------------------------
# Sensitivity comparison (DATA-05)
# ----------------------------------------------------------------------------------------------


def sensitivity(audited: PcaResult, a_scores: np.ndarray, all31: PcaResult, s_scores: np.ndarray,
                dec_a: dict, dec_s: dict) -> dict:
    """Compare the 31-column run against the audited set on the 26 common variables."""
    common = [f for f in audited.features if f in all31.features]
    if len(common) != len(audited.features):
        raise ValueError("the audited features are not a subset of the 31 columns")
    rows = [all31.features.index(f) for f in common]
    out = {}
    for c in (0, 1):
        sub = all31.eigenvectors[rows, c]
        sub = sub / np.linalg.norm(sub)
        out[f"abs_cos_pc{c + 1}"] = float(abs(audited.eigenvectors[:, c] @ sub))
    for c in (0, 1):
        out[f"pearson_pc{c + 1}"] = _pearson(a_scores[:, c], s_scores[:, c])
        out[f"spearman_pc{c + 1}"] = spearman(a_scores[:, c], s_scores[:, c])

    def summary(dec: dict) -> dict:
        return {key: dec[key] for key in
                ("n_variables", "k_80", "kaiser", "explained_pc1", "explained_pc2", "null_eigenvalues")}

    return {"common_variables": len(common), "audited": summary(dec_a),
            "all31_sensitivity": summary(dec_s), **out}


def sensitivity_markdown(comp: dict) -> str:
    a, s = comp["audited"], comp["all31_sensitivity"]
    lines = [
        "# SENSIBILIDAD: 31 columnas frente al conjunto auditado",
        "",
        "Corrida de sensibilidad (DATA-05): las 31 columnas no son el conjunto auditado.",
        "",
        "| Medida | Auditado | 31 columnas |",
        "|---|---|---|",
        f"| Variables | {a['n_variables']} | {s['n_variables']} |",
        f"| Autovalores nulos (abs < {NULL_EIGENVALUE:g}) | {a['null_eigenvalues']} | {s['null_eigenvalues']} |",
        f"| Componentes para el 80 % | {a['k_80']} | {s['k_80']} |",
        f"| Componentes con autovalor > 1 (Kaiser) | {a['kaiser']} | {s['kaiser']} |",
        f"| % de varianza de PC1 | {a['explained_pc1'] * 100:.2f} | {s['explained_pc1'] * 100:.2f} |",
        f"| % de varianza de PC2 | {a['explained_pc2'] * 100:.2f} | {s['explained_pc2'] * 100:.2f} |",
        "",
        f"Comparación sobre las {comp['common_variables']} variables comunes "
        "(autovectores de 31 columnas restringidos y renormalizados):",
        "",
        "| Componente | abs(cos) entre autovectores | Pearson de scores | Spearman de scores |",
        "|---|---|---|---|",
    ]
    for c in (1, 2):
        lines.append(
            f"| PC{c} | {comp[f'abs_cos_pc{c}']:.6f} | {comp[f'pearson_pc{c}']:.6f} | "
            f"{comp[f'spearman_pc{c}']:.6f} |"
        )
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------------------------


def _figure_variants(folder: str):
    """The figure variants to draw for a data set (D-08): report then slide for the audited set, report only
    for the all-31 sensitivity set. Not this module's VARIANTS, which are the data sets."""
    return plots_style.iter_variants() if folder == "audited" else ["report"]


def run_variant(stem: str, folder: str, title: str, out_dir: Path):
    features, z, meta = read_prepared(stem)
    result = pca_eigh(z, features)
    out = out_dir / folder
    out.mkdir(parents=True, exist_ok=True)
    dec = decision(result, str(meta["variant"]))
    write_tables(out, result, z, meta)
    for _ in _figure_variants(folder):
        plot_scree(result, dec, title, out)
    plot_loadings(result, dec, title, out)
    for _ in _figure_variants(folder):
        plot_biplot(result, z, meta, title, out)
    (out / "decision.json").write_text(json.dumps(dec, indent=2, ensure_ascii=False) + "\n",
                                       encoding="utf-8")
    return result, z, dec, out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Correlation PCA by eigenvalues and 31-column sensitivity.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR,
                        help="output folder (default: analysis/results/pca)")
    args = parser.parse_args(argv)
    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    runs = {}
    for stem, folder, title in VARIANTS:
        result, z, dec, out = run_variant(stem, folder, title, out_dir)
        runs[folder] = (result, z, dec)
        print(f"{folder}: k_80 = {dec['k_80']}, Kaiser = {dec['kaiser']}, "
              f"agree = {dec['rule_agrees']}, null eigenvalues = {dec['null_eigenvalues']} -> {out}")

    a_result, a_z, a_dec = runs["audited"]
    s_result, s_z, s_dec = runs["all31_sensitivity"]
    comp = sensitivity(a_result, scores(a_result, a_z), s_result, scores(s_result, s_z), a_dec, s_dec)
    (out_dir / "sensitivity.json").write_text(json.dumps(comp, indent=2, ensure_ascii=False) + "\n",
                                              encoding="utf-8")
    (out_dir / "sensitivity.md").write_text(sensitivity_markdown(comp), encoding="utf-8")
    print(f"sensitivity -> {out_dir / 'sensitivity.json'}, {out_dir / 'sensitivity.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
