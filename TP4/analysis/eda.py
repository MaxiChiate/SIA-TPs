"""EDA of datos/creadores.csv and the generated audit table (DATA-02).

Run from TP4/ with `make eda` (or `.venv/bin/python analysis/eda.py`). Everything is regenerated from
the raw CSV and written to analysis/results/eda/ (not versioned): distributions, the 31 x 31
correlation heatmap, summary statistics with skewness, the residuals of the 5 exact dependencies, the
strong-correlation pairs, the near-redundant variables and the audit table.

The audit decision comes from `creadores.audit_variables`, the same rule that produced
datos/prepared (D-08, D-09), so the table cannot disagree with the matrices the C core reads.
No dataframe library (D-06): `csv` and numpy do the work, matplotlib draws.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

TP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TP_DIR / "scripts"))
sys.path.insert(0, str(TP_DIR / "analysis"))

import plots_style  # noqa: E402
from creadores import (  # noqa: E402
    EXACT_TOLERANCE,
    Audit,
    Creadores,
    audit_variables,
    dependency_residuals,
    load_creadores,
)

DEFAULT_OUT_DIR = TP_DIR / "analysis" / "results" / "eda"

STRONG_THRESHOLD = 0.8
NEAR_THRESHOLD = 0.9
REFERENCE = "followers"
ESTIMATED = "estimated_argentina_reach"

VARIABLE_GROUPS: dict[str, str] = {
    "followers": "tamaño y alcance",
    "average_reach": "tamaño y alcance",
    "average_impressions": "tamaño y alcance",
    "average_video_views": "tamaño y alcance",
    "estimated_argentina_reach": "tamaño y alcance",
    "monthly_posts": "actividad",
    "argentina_audience_pct": "audiencia",
    "non_follower_reach_pct": "audiencia",
    "likes_per_1000": "engagement por 1000",
    "comments_per_1000": "engagement por 1000",
    "saves_per_1000": "engagement por 1000",
    "shares_per_1000": "engagement por 1000",
    "total_engagement_per_1000": "engagement por 1000",
    "profile_visits_per_1000": "engagement por 1000",
    "price_usd": "precio",
    "price_ars": "precio",
    "sponsored_posts_pct": "patrocinio",
    "organic_posts_pct": "patrocinio",
    "topic_football_pct": "temas (composición)",
    "topic_makeup_pct": "temas (composición)",
    "topic_dogs_pct": "temas (composición)",
    "topic_art_pct": "temas (composición)",
    "content_tutorial_pct": "tipo de contenido (composición)",
    "content_review_pct": "tipo de contenido (composición)",
    "content_entertainment_pct": "tipo de contenido (composición)",
    "content_showcase_pct": "tipo de contenido (composición)",
    "average_caption_words": "formato y estilo",
    "average_watch_time_seconds": "formato y estilo",
    "video_posts_pct": "formato y estilo",
    "short_form_posts_pct": "formato y estilo",
    "trend_posts_pct": "formato y estilo",
}

# Exact relation of every variable that takes part in one (D-08): variable -> relation text.
_ENGAGEMENT_PARTS = ("likes_per_1000", "comments_per_1000", "saves_per_1000", "shares_per_1000")
RELATIONS: dict[str, str] = {
    "price_ars": "price_ars = 1500 · price_usd",
    "organic_posts_pct": "organic_posts_pct = 100 − sponsored_posts_pct",
    "total_engagement_per_1000": "total_engagement_per_1000 = likes + comments + saves + shares (por 1000)",
    "topic_sum_100": "suma de topic_* = 100",
    "content_sum_100": "suma de content_* = 100",
}


def _column(data: Creadores, name: str) -> np.ndarray:
    return data.values[:, data.columns.index(name)]


def _relation_of(variable: str) -> str | None:
    """The exact relation a variable belongs to (as dependent or as base), or None."""
    if variable in ("price_ars", "price_usd"):
        return RELATIONS["price_ars"]
    if variable in ("organic_posts_pct", "sponsored_posts_pct"):
        return RELATIONS["organic_posts_pct"]
    if variable == "total_engagement_per_1000" or variable in _ENGAGEMENT_PARTS:
        return RELATIONS["total_engagement_per_1000"]
    if variable.startswith("topic_"):
        return RELATIONS["topic_sum_100"]
    if variable.startswith("content_"):
        return RELATIONS["content_sum_100"]
    return None


def _pretty(formula: str) -> str:
    """Typographic form of a reconstruction formula from creadores.py."""
    return formula.replace(" * ", " · ").replace(" - ", " − ")


def summary_statistics(data: Creadores) -> list[dict]:
    """Per column: mean, std (ddof = 1), min, median, max and Fisher-Pearson skewness g1.

    g1 = m3 / m2^(3/2) with population central moments m2 and m3.
    """
    rows = []
    for name in data.columns:
        x = _column(data, name)
        centred = x - x.mean()
        m2 = float(np.mean(centred**2))
        m3 = float(np.mean(centred**3))
        rows.append(
            {
                "variable": name,
                "mean": float(x.mean()),
                "std": float(x.std(ddof=1)),
                "min": float(x.min()),
                "median": float(np.median(x)),
                "max": float(x.max()),
                "skewness": m3 / m2**1.5 if m2 > 0 else 0.0,
            }
        )
    return rows


def correlation_matrix(data: Creadores) -> np.ndarray:
    return np.corrcoef(data.values, rowvar=False)


def strong_correlations(data: Creadores, threshold: float = STRONG_THRESHOLD) -> list[dict]:
    """Every pair with |r| >= threshold, sorted by |r| descending (ties by column order)."""
    corr = correlation_matrix(data)
    pairs = []
    n = len(data.columns)
    for i in range(n):
        for j in range(i + 1, n):
            r = float(corr[i, j])
            if abs(r) >= threshold:
                pairs.append({"a": data.columns[i], "b": data.columns[j], "r": r})
    pairs.sort(key=lambda p: -abs(p["r"]))
    return pairs


def near_redundant(data: Creadores) -> list[dict]:
    """The D-10 rows: variables with |r| > 0.9 with followers, and estimated_argentina_reach.

    estimated_argentina_reach is approximately average_reach · argentina_audience_pct / 100 (not
    exact, so it stays). Each row has the variable, r with followers and, for the estimate only,
    the max absolute error against that formula.
    """
    followers = _column(data, REFERENCE)
    rows: dict[str, dict] = {}
    for name in data.columns:
        if name == REFERENCE:
            continue
        r = float(np.corrcoef(followers, _column(data, name))[0, 1])
        if abs(r) > NEAR_THRESHOLD:
            rows[name] = {"variable": name, "r_followers": r, "max_abs_error": None}
    approx = _column(data, "average_reach") * _column(data, "argentina_audience_pct") / 100.0
    error = float(np.max(np.abs(_column(data, ESTIMATED) - approx)))
    if ESTIMATED not in rows:
        r = float(np.corrcoef(followers, _column(data, ESTIMATED))[0, 1])
        rows[ESTIMATED] = {"variable": ESTIMATED, "r_followers": r, "max_abs_error": None}
    rows[ESTIMATED]["max_abs_error"] = error
    ordered = [name for name in data.columns if name in rows]
    return [rows[name] for name in ordered]


def audit_rows(
    data: Creadores, audit: Audit, residuals: dict[str, float], near: list[dict]
) -> list[dict]:
    """One row per numeric variable, in file order: Variable, Grupo, Relación, Decisión, Motivo."""
    dropped = {d.name: d for d in audit.dropped}
    near_by_name = {row["variable"]: row for row in near}
    inexact = [name for name, value in residuals.items() if value > EXACT_TOLERANCE]
    if inexact:
        raise ValueError(f"relations no longer exact, the audit table would be wrong: {inexact}")

    rows = []
    for name in data.columns:
        relation = _relation_of(name) or ""
        near_row = near_by_name.get(name)
        if name in dropped:
            decision = "sale (reconstruible)"
            reason = f"{dropped[name].reason}; {_pretty(dropped[name].reconstruct)}"
        elif relation:
            decision = "entra"
            reason = f"base de la relación {relation}"
        else:
            decision = "entra"
            reason = "variable original"

        if near_row is not None:
            notes = []
            if near_row["max_abs_error"] is not None:
                notes.append(
                    "aproximación no exacta, error máx "
                    f"{near_row['max_abs_error']:.3g} frente a "
                    "average_reach · argentina_audience_pct / 100"
                )
            if abs(near_row["r_followers"]) > NEAR_THRESHOLD:
                notes.append(f"casi redundante: r = {near_row['r_followers']:.3f} con {REFERENCE}")
            if not relation:
                relation = "casi redundante (se documenta, no se elimina)"
            reason = "; ".join(notes)
        rows.append(
            {
                "Variable": name,
                "Grupo": VARIABLE_GROUPS[name],
                "Relación": relation,
                "Decisión": decision,
                "Motivo": reason,
            }
        )
    return rows


def audit_table_markdown(rows: list[dict]) -> str:
    header = ["Variable", "Grupo", "Relación", "Decisión", "Motivo"]
    lines = [
        "| " + " | ".join(header) + " |",
        "|" + "|".join(["---"] * len(header)) + "|",
    ]
    for row in rows:
        cells = [f"`{row['Variable']}`"] + [row[h] for h in header[1:]]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def _write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def _num(value: float | None) -> str:
    return "" if value is None else repr(float(value))


def plot_distributions(data: Creadores, stats: list[dict], out_dir: Path) -> None:
    plt = plots_style.apply_style()
    fig, axes = plt.subplots(6, 6, figsize=(21, 17))
    flat = axes.ravel()
    skew = {row["variable"]: row["skewness"] for row in stats}
    for ax, name in zip(flat, data.columns):
        ax.hist(_column(data, name), bins=12, color=plots_style.palette_for(["x"])["x"],
                edgecolor=plots_style.SURFACE, linewidth=0.5)
        ax.set_title(f"{name}\nasimetría = {skew[name]:.2f}", fontsize=8)
        ax.tick_params(labelsize=7)
    for ax in flat[len(data.columns):]:
        ax.set_visible(False)
    fig.suptitle("Distribuciones de las 31 variables (n = 50)", fontsize=16)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    plots_style.save_figure(fig, out_dir / "distributions")


# Variables whose histogram the slide variant shows next to the correlations: the size block, price, the most
# skewed variable and the one that runs against size (fixed by name, not picked by how they look).
SLIDE_HISTOGRAMS = ("followers", "price_usd", "estimated_argentina_reach", "average_caption_words")


def plot_correlation_slide(data: Creadores, stats: list[dict], dropped: list[str], out_dir: Path) -> None:
    """Slide variant of the EDA: the 31 x 31 correlations ordered by variable group (the variables that leave the
    audited set marked with ×) and four histograms with their skewness."""
    from matplotlib.gridspec import GridSpec

    plt = plots_style.apply_style()
    order = list(VARIABLE_GROUPS)
    index = [data.columns.index(name) for name in order]
    corr = correlation_matrix(data)[np.ix_(index, index)]
    fig = plt.figure(figsize=plots_style.figsize((12.8, 4.85)))
    grid = GridSpec(2, 3, figure=fig, width_ratios=[1.55, 1.0, 1.0], wspace=0.35, hspace=0.75,
                    left=0.17, right=0.99, top=0.87, bottom=0.08)
    ax = fig.add_subplot(grid[:, 0])
    image = ax.imshow(corr, cmap=plots_style.DIVERGING, vmin=-1, vmax=1)
    labels = [f"× {name}" if name in dropped else name for name in order]
    ax.set_xticks(range(len(order)))
    ax.set_yticks(range(len(order)))
    ax.set_xticklabels([])
    ax.set_yticklabels(labels, fontsize=6.2)
    for tick, name in zip(ax.get_yticklabels(), order):
        if name in dropped:
            tick.set_color(plots_style._SERIES[7])
    ax.tick_params(length=0)
    groups = [VARIABLE_GROUPS[name] for name in order]
    for position in range(1, len(order)):
        if groups[position] != groups[position - 1]:
            ax.axhline(position - 0.5, color=plots_style.SURFACE, linewidth=1.2)
            ax.axvline(position - 0.5, color=plots_style.SURFACE, linewidth=1.2)
    for spine in ax.spines.values():
        spine.set_visible(False)
    colorbar = fig.colorbar(image, ax=ax, fraction=0.045, pad=0.02)
    colorbar.ax.tick_params(labelsize=8)
    ax.set_title("correlación de Pearson (× sale del conjunto)", fontsize=9.5)
    skew = {row["variable"]: row["skewness"] for row in stats}
    color = plots_style.palette_for(["x"])["x"]
    for slot, name in enumerate(SLIDE_HISTOGRAMS):
        hist_ax = fig.add_subplot(grid[slot // 2, 1 + slot % 2])
        hist_ax.hist(_column(data, name), bins=12, color=color, edgecolor=plots_style.SURFACE, linewidth=0.5)
        hist_ax.set_title(f"{name}\nasimetría {skew[name]:.2f}".replace(".", ","), fontsize=9.5)
        hist_ax.tick_params(labelsize=8)
        hist_ax.ticklabel_format(axis="x", style="plain")
        hist_ax.xaxis.set_major_locator(plt.MaxNLocator(3))
        hist_ax.set_ylabel("creadores", fontsize=8.5)
    plots_style.save_figure(fig, out_dir / "correlation")


def plot_correlation(data: Creadores, out_dir: Path, stats: list[dict] | None = None,
                     dropped: list[str] | None = None) -> None:
    if plots_style.variant() == "slide":
        plot_correlation_slide(data, stats or summary_statistics(data), dropped or [], out_dir)
        return
    plt = plots_style.apply_style()
    corr = correlation_matrix(data)
    n = len(data.columns)
    fig, ax = plt.subplots(figsize=(14, 12))
    image = ax.imshow(corr, cmap=plots_style.DIVERGING, vmin=-1, vmax=1)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(data.columns, rotation=90, fontsize=8)
    ax.set_yticklabels(data.columns, fontsize=8)
    for spine in ax.spines.values():
        spine.set_visible(False)
    colorbar = fig.colorbar(image, ax=ax, fraction=0.04, pad=0.02)
    colorbar.set_label("correlación de Pearson")
    ax.set_title("Correlaciones entre las 31 variables", fontsize=14)
    fig.tight_layout()
    plots_style.save_figure(fig, out_dir / "correlation")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EDA of datos/creadores.csv and audit table.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR,
                        help="output folder (default: analysis/results/eda)")
    args = parser.parse_args(argv)
    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    data = load_creadores()
    if set(VARIABLE_GROUPS) != set(data.columns) or len(VARIABLE_GROUPS) != len(data.columns):
        missing = sorted(set(data.columns) - set(VARIABLE_GROUPS))
        extra = sorted(set(VARIABLE_GROUPS) - set(data.columns))
        raise SystemExit(
            f"VARIABLE_GROUPS does not match the loaded columns: missing {missing}, extra {extra}"
        )
    if data.values.shape != (50, 31):
        raise SystemExit(f"expected a 50 x 31 numeric matrix, got {data.values.shape}")

    residuals = dependency_residuals(data)
    audit = audit_variables(data)
    stats = summary_statistics(data)
    strong = strong_correlations(data)
    near = near_redundant(data)
    rows = audit_rows(data, audit, residuals, near)

    _write_csv(
        out_dir / "summary_stats.csv",
        ["variable", "mean", "std", "min", "median", "max", "skewness"],
        [[r["variable"], *(_num(r[k]) for k in ("mean", "std", "min", "median", "max", "skewness"))]
         for r in stats],
    )
    _write_csv(
        out_dir / "exact_dependencies.csv",
        ["relation", "max_abs_residual", "exact"],
        [[name, _num(value), str(value <= EXACT_TOLERANCE)] for name, value in residuals.items()],
    )
    _write_csv(
        out_dir / "strong_correlations.csv",
        ["variable_a", "variable_b", "r"],
        [[p["a"], p["b"], _num(p["r"])] for p in strong],
    )
    _write_csv(
        out_dir / "near_redundant.csv",
        ["variable", "r_followers", "max_abs_error"],
        [[r["variable"], _num(r["r_followers"]), _num(r["max_abs_error"])] for r in near],
    )
    (out_dir / "audit_table.md").write_text(audit_table_markdown(rows), encoding="utf-8")

    plot_distributions(data, stats, out_dir)
    for _ in plots_style.iter_variants():  # report, then the slide variant of the EDA slide
        plot_correlation(data, out_dir, stats, [item.name for item in audit.dropped])

    print("Residuos máximos de las 5 dependencias exactas:")
    for name, value in residuals.items():
        print(f"  {name}: {value:.3g}")
    print(f"Variables que salen: {len(audit.dropped)}; que entran: {len(audit.kept)}")
    for path in sorted(out_dir.iterdir()):
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
