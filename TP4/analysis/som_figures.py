#!/usr/bin/env python3
"""Figures of the chosen Kohonen map (SOM-04): hit map with U-matrix, component planes, stage-1 curves, trace.

    .venv/bin/python analysis/som_figures.py [--stage1 DIR] [--out DIR]

Only the grid chosen by the pre-registered rule is drawn: the run is the one selection.json names as
`figure_run` (the stability medoid of the chosen k, D-13), and the script refuses to start when the rule
sha256 differs from the one recorded in selection.json or when no grid was chosen (D-14). The main component
planes are the 4 variables with the largest |loading| on PC1 and the next 4 distinct ones on PC2 (Phase 1
orientation), never picked by how the map looks. Every figure is written through plots_style.save_figure, so a
rerun gives byte-identical SVG files. numpy and matplotlib (through plots_style) only (Phase 1 D-06).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

TP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TP_DIR / "scripts"))
sys.path.insert(0, str(TP_DIR / "analysis"))

import pca  # noqa: E402
import plots_style  # noqa: E402
import som  # noqa: E402
import som_stage  # noqa: E402
from creadores import load_creadores  # noqa: E402

DEFAULT_STAGE1 = TP_DIR / "analysis" / "results" / "som" / "series_som_stage1"
DEFAULT_STAGE2 = TP_DIR / "analysis" / "results" / "som" / "series_som_stage2"
DEFAULT_OUT = TP_DIR / "analysis" / "results" / "som" / "figures"
RULE_FILE = TP_DIR / "deliverables" / "02-kohonen.md"
HATCH_COLOR = "#8a8984"
NEIGHBORHOOD_NAMES = {"step": "escalón", "gaussian": "gaussiana"}
EXTRA_RAW = ("topic_art_pct", "content_showcase_pct")


@dataclass(frozen=True)
class Plane:
    name: str
    values: np.ndarray  # k x k
    kind: str  # "z" (prototype value in z units), "pc" (prototype weight on a component, own scale centred on 0)
    #           or "raw" (mean of the creators of each neuron)
    unit: str


# ---------- small helpers ----------

def main_planes(loadings: np.ndarray, features: list[str], n: int = 4) -> list[str]:
    """The n features with the largest |PC1 loading| (descending), then the next n distinct features by
    |PC2 loading| (stable sorts), skipping those already taken."""
    loadings = np.asarray(loadings)
    first = np.argsort(-np.abs(loadings[:, 0]), kind="stable")[:n]
    names = [features[i] for i in first]
    second: list[str] = []
    for i in np.argsort(-np.abs(loadings[:, 1]), kind="stable"):
        if features[i] not in names:
            second.append(features[i])
            if len(second) == n:
                break
    return names + second


def neuron_raw_means(bmu, k: int, raw_column) -> np.ndarray:
    """k x k mean of raw_column over the creators whose BMU is each neuron; NaN where the neuron is empty."""
    bmu = np.asarray(bmu)
    raw_column = np.asarray(raw_column, dtype=np.float64)
    out = np.full(k * k, np.nan)
    for neuron in range(k * k):
        members = raw_column[bmu == neuron]
        if len(members):
            out[neuron] = float(members.mean())
    return out.reshape(k, k)


def _hatch(ax, mask: np.ndarray) -> None:
    """Hatch the cells where mask is True (empty neurons) without hiding the colour below."""
    from matplotlib.patches import Rectangle

    for row, col in zip(*np.nonzero(mask)):
        ax.add_patch(Rectangle((col - 0.5, row - 0.5), 1, 1, fill=False, hatch="////", linewidth=0,
                               edgecolor=HATCH_COLOR))


def _grid_axes(ax, k: int, fontsize: int = 8) -> None:
    fontsize = plots_style.fontsize(fontsize)
    ax.set_xticks(range(k))
    ax.set_yticks(range(k))
    ax.set_xticklabels([str(i) for i in range(k)], fontsize=fontsize)
    ax.set_yticklabels([str(i) for i in range(k)], fontsize=fontsize)
    ax.set_xlim(-0.5, k - 0.5)
    ax.set_ylim(k - 0.5, -0.5)  # row 0 at the top
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0)


def _caption(fig, text: str, width: int = 125, y: float = 0.01) -> None:
    """Kept for campaigns.py; the caption itself lives in plots_style (nothing is drawn in the slide variant)."""
    plots_style.caption(fig, text, width=width, y=y)


def _fmt(value: float) -> str:
    return f"{value:.2f}".replace(".", ",")


# ---------- hit map + U-matrix ----------

def plot_map(hits, U, k: int, title: str, caption: str, out_stem) -> None:
    plt = plots_style.apply_style()
    hits = np.asarray(hits).reshape(k, k)
    U = np.asarray(U, dtype=np.float64)
    empty = hits == 0
    fig, (left, right) = plt.subplots(1, 2, figsize=plots_style.figsize((11.5, 6.4)))

    shown = np.ma.masked_where(empty, hits)
    cmap = plt.get_cmap("Blues").with_extremes(bad=plots_style.SURFACE)
    image = left.imshow(shown, cmap=cmap, vmin=0, vmax=max(int(hits.max()), 1), aspect="equal")
    for row in range(k):
        for col in range(k):
            if hits[row, col] > 0:
                dark = hits[row, col] > 0.6 * max(int(hits.max()), 1)
                left.text(col, row, str(int(hits[row, col])), ha="center", va="center",
                          fontsize=plots_style.fontsize(11), color="white" if dark else plots_style.TEXT_PRIMARY)
    _hatch(left, empty)
    _grid_axes(left, k)
    left.set_title("Creadores por neurona (celdas rayadas: vacías)", fontsize=plots_style.fontsize(10), loc="left")
    bar = fig.colorbar(image, ax=left, fraction=0.046, pad=0.03)
    bar.set_label("creadores")

    image = right.imshow(U, cmap="viridis", vmin=float(U.min()), vmax=float(U.max()), aspect="equal")
    for row in range(k):
        for col in range(k):
            frac = (U[row, col] - U.min()) / (U.max() - U.min()) if U.max() > U.min() else 0.5
            right.text(col, row, _fmt(U[row, col]), ha="center", va="center",
                       fontsize=plots_style.fontsize(8), color="white" if frac < 0.55 else plots_style.TEXT_PRIMARY)
    _hatch(right, empty)
    _grid_axes(right, k)
    right.set_title("Matriz U (celdas rayadas: neuronas vacías)", fontsize=plots_style.fontsize(10), loc="left")
    bar = fig.colorbar(image, ax=right, fraction=0.046, pad=0.03)
    bar.set_label("distancia media a los 4 vecinos (z)")

    plots_style.suptitle(fig, title, fontsize=12, x=0.01, ha="left")
    fig.tight_layout(rect=plots_style.rect((0, 0.13, 1, 0.96)))
    plots_style.caption(fig, caption)
    plots_style.save_figure(fig, out_stem)


# ---------- component planes ----------

def plot_planes(planes: list[Plane], k: int, hits, title: str, caption: str, out_stem, ncols: int = 4) -> None:
    from matplotlib.gridspec import GridSpec
    from matplotlib.ticker import FuncFormatter

    plt = plots_style.apply_style()
    hits = np.asarray(hits).reshape(k, k)
    empty = hits == 0
    n = len(planes)
    nrows = math.ceil(n / ncols)
    cell = 2.5 if ncols >= 5 else 3.1
    fig = plt.figure(figsize=plots_style.figsize((cell * ncols * 0.85 + 1.8, cell * nrows * 0.85 + 1.7)))
    grid = GridSpec(nrows, ncols + 1, figure=fig, width_ratios=[1.0] * ncols + [0.07], wspace=0.5 if ncols < 5 else 0.85, hspace=0.45)

    z_values = [p.values for p in planes if p.kind == "z"]
    limit = max((float(np.nanmax(np.abs(v))) for v in z_values), default=1.0) or 1.0
    z_image = None
    for index, plane in enumerate(planes):
        ax = fig.add_subplot(grid[index // ncols, index % ncols])
        values = np.ma.masked_invalid(plane.values)
        if plane.kind == "z":
            cmap = plt.get_cmap(plots_style.DIVERGING).with_extremes(bad=plots_style.SURFACE)
            z_image = ax.imshow(values, cmap=cmap, vmin=-limit, vmax=limit, aspect="equal")
        elif plane.kind == "pc":
            own_limit = float(np.nanmax(np.abs(plane.values))) or 1.0
            cmap = plt.get_cmap(plots_style.DIVERGING).with_extremes(bad=plots_style.SURFACE)
            image = ax.imshow(values, cmap=cmap, vmin=-own_limit, vmax=own_limit, aspect="equal")
            inset = ax.inset_axes([1.05, 0.0, 0.06, 1.0])
            bar = fig.colorbar(image, cax=inset)
            bar.ax.tick_params(labelsize=plots_style.fontsize(6))
        else:
            cmap = plt.get_cmap("YlGnBu").with_extremes(bad=plots_style.SURFACE)
            image = ax.imshow(values, cmap=cmap, aspect="equal")
            inset = ax.inset_axes([1.05, 0.0, 0.06, 1.0])
            bar = fig.colorbar(image, cax=inset)
            bar.ax.tick_params(labelsize=plots_style.fontsize(6))
            bar.formatter = FuncFormatter(lambda v, _pos: f"{v:,.0f}" if abs(v) >= 1000 else f"{v:g}")
            bar.update_ticks()
        _hatch(ax, empty | np.isnan(plane.values))
        _grid_axes(ax, k, fontsize=7)
        if plane.kind == "z":
            ax.set_title(plane.name, fontsize=plots_style.fontsize(8), loc="left")
        elif plane.kind == "pc":
            ax.set_title(f"{plane.name}\n(peso del prototipo)", fontsize=plots_style.fontsize(8), loc="left")
        else:
            unit = f", {plane.unit}" if plane.unit else ""
            ax.set_title(f"{plane.name}\n(media cruda{unit})", fontsize=plots_style.fontsize(8), loc="left")
    if z_image is not None:
        cax = fig.add_subplot(grid[:, ncols])
        bar = fig.colorbar(z_image, cax=cax)
        bar.set_label("valor del prototipo (z)", fontsize=plots_style.fontsize(8))
        bar.ax.tick_params(labelsize=plots_style.fontsize(7))
    plots_style.suptitle(fig, title, fontsize=12, x=0.01, ha="left", y=0.995)
    height = cell * nrows * 0.85 + 1.7
    if plots_style.variant() == "slide":
        fig.subplots_adjust(left=0.04, right=0.92, top=0.9, bottom=0.08)
    else:
        fig.subplots_adjust(left=0.04, right=0.92, top=1 - 0.55 / height, bottom=1.1 / height)
    plots_style.caption(fig, caption, width=int(22 * ncols + 30))
    plots_style.save_figure(fig, out_stem)


# ---------- stage-1 curves ----------

CURVE_PANELS = (
    ("qe", "QE de entrenamiento", 1.0),
    ("qe_loo", "QE-LOO", 1.0),
    ("te", "Error topográfico (TE)", 1.0),
    ("empty_fraction", "% de neuronas vacías", 100.0),
    ("creators_per_occupied", "Creadores por neurona ocupada", 1.0),
    ("stability", "Estabilidad entre seeds (correlación)", 1.0),
)


def plot_stage1_curves(rows: list[dict], selection: dict, out_stem) -> None:
    plt = plots_style.apply_style()
    colors = plots_style.palette_for(["escalón", "gaussiana"])
    thresholds = selection["thresholds"]
    limits = {"te": thresholds["te_max"], "empty_fraction": thresholds["empty_max"] * 100.0,
              "creators_per_occupied": thresholds["creators_min"]}
    chosen = selection.get("chosen_k")
    fig, axes = plt.subplots(2, 3, figsize=plots_style.figsize((13.0, 7.6)))
    for ax, (measure, label, scale) in zip(axes.flat, CURVE_PANELS):
        for neighborhood, name in (("step", "escalón"), ("gaussian", "gaussiana")):
            subset = sorted((r for r in rows if r["neighborhood"] == neighborhood), key=lambda r: int(r["grid_k"]))
            ks = [int(r["grid_k"]) for r in subset]
            mean = [float(r[f"{measure}_mean" if measure != "stability" else "stability"]) * scale
                    for r in subset]
            sd_key = f"{measure}_sd"
            sd = [float(r[sd_key]) * scale if r.get(sd_key) not in (None, "") else 0.0 for r in subset]
            ax.errorbar(ks, mean, yerr=sd, color=colors[name], marker="o", markersize=4, linewidth=1.5,
                        capsize=3, label=name)
        if measure in limits:
            ax.axhline(limits[measure], color=plots_style.TEXT_SECONDARY, linestyle="--", linewidth=1)
            ax.annotate(f"umbral {_fmt(limits[measure]).rstrip('0').rstrip(',')}", (0.99, limits[measure]),
                        xycoords=("axes fraction", "data"), xytext=(0, 3), textcoords="offset points",
                        ha="right", va="bottom", fontsize=plots_style.fontsize(8),
                        color=plots_style.TEXT_SECONDARY)
        if chosen is not None:
            ax.axvline(chosen, color=plots_style.TEXT_PRIMARY, linewidth=1, alpha=0.5)
            if measure == "qe_loo":
                ax.annotate(f"k elegida = {chosen}", (chosen, 1.0), xycoords=("data", "axes fraction"),
                            xytext=(4, -12), textcoords="offset points", fontsize=plots_style.fontsize(8),
                            color=plots_style.TEXT_PRIMARY)
        if measure == "qe":
            argmin = selection.get("qe_train_argmin_k")
            if argmin is not None:
                value = next(float(r["qe_mean"]) for r in rows
                             if r["neighborhood"] == "step" and int(r["grid_k"]) == int(argmin))
                # the slide type is larger: the note sits in the empty top right of the panel (the legend
                # moves to another panel), instead of an offset that lands on the curves
                slide = plots_style.variant() == "slide"
                ax.annotate(f"menor QE: k = {argmin}", (argmin, value),
                            xytext=(0.74, 0.86) if slide else (-70, 40),
                            textcoords="axes fraction" if slide else "offset points",
                            ha="center" if slide else "right", fontsize=plots_style.fontsize(8),
                            color=plots_style.TEXT_PRIMARY,
                            arrowprops={"arrowstyle": "-", "color": plots_style.TEXT_SECONDARY})
        ax.set_title(label, fontsize=plots_style.fontsize(10), loc="left")
        ax.set_xlabel("k (lado de la grilla)")
        ks_all = sorted({int(r["grid_k"]) for r in rows})
        ax.set_xticks(ks_all)
        ax.grid(True, axis="y")
    slide = plots_style.variant() == "slide"
    # slide: the legend moves to the empty top right of the "Creadores por neurona ocupada" panel
    axes.flat[4 if slide else 0].legend(frameon=False, fontsize=plots_style.fontsize(9), loc="upper right")
    plots_style.suptitle(fig, "Etapa 1: medidas contra k (media ± desvío entre las 10 seeds; línea vertical: k elegida; "
                         "los umbrales de la regla valen para el escalón)", fontsize=11, x=0.01, ha="left")
    fig.tight_layout(rect=plots_style.rect((0, 0, 1, 0.95)))
    plots_style.save_figure(fig, out_stem)


# ---------- effect of one hyperparameter ----------

# The three measures of the rule: the topographic error (do neighbouring neurons stay neighbours on the grid), how many
# neurons are empty and how many creators share an occupied one.
EFFECT_PANELS = (
    ("te", "Error topográfico", "límite: 0,05", 1.0),
    ("empty_fraction", "% de neuronas vacías", "límite: 20 %", 100.0),
    ("creators_per_occupied", "Creadores por neurona ocupada", "mínimo: 2", 1.0),
)
# The same y range in the three figures, so a change of eta0 or R0 is read on the scale of the change of k.
EFFECT_YLIM = {"te": (-0.01, 0.22), "empty_fraction": (-2.0, 50.0), "creators_per_occupied": (0.0, 13.0)}


def effect_rows(stage2_rows: list[dict], vary: str) -> list[dict]:
    """The stage-2 rows that move `vary` (radius0 or eta0) plus the base one, sorted by that value."""
    prefix = {"radius0": "radius0-", "eta0": "eta0-"}[vary]
    chosen = [r for r in stage2_rows if r["label"] == "base" or r["label"].startswith(prefix)]
    return sorted(chosen, key=lambda r: float(r[vary]))


def plot_effect(rows: list[dict], x_key: str, x_label: str, base_x: float, thresholds: dict, out_stem) -> None:
    """Three panels (topographic error, empty neurons, creators per neuron) against one hyperparameter, escalón only;
    mean +/- sd over the 10 seeds, the dashed line is the limit of the rule, the vertical one the value we use."""
    plt = plots_style.apply_style()
    color = plots_style.palette_for(["escalón"])["escalón"]
    limits = {"te": thresholds["te_max"], "empty_fraction": thresholds["empty_max"] * 100.0,
              "creators_per_occupied": thresholds["creators_min"]}
    fig, axes = plt.subplots(1, 3, figsize=plots_style.figsize((11.5, 3.9), (12.8, 5.0)))
    xs = [float(r[x_key]) for r in rows]
    for ax, (measure, label, hint, scale) in zip(axes, EFFECT_PANELS):
        mean = [float(r[f"{measure}_mean"]) * scale for r in rows]
        sd = [float(r[f"{measure}_sd"]) * scale for r in rows]
        ax.errorbar(xs, mean, yerr=sd, color=color, marker="o", markersize=5, linewidth=1.8, capsize=3)
        if measure in limits:
            ax.axhline(limits[measure], color=plots_style.TEXT_SECONDARY, linestyle="--", linewidth=1)
        ax.axvline(base_x, color=plots_style.TEXT_PRIMARY, linewidth=1, alpha=0.5)
        ax.set_ylim(*EFFECT_YLIM[measure])
        # the slide carries the title only; the report keeps the hint (what is better, the limit of the rule)
        title = label if plots_style.variant() == "slide" else f"{label}\n({hint})"
        ax.set_title(title, fontsize=plots_style.fontsize(9), loc="left")
        ax.set_xlabel(x_label)
        ax.set_xticks(xs)
        ax.set_xticklabels([_fmt_tick(x) for x in xs])
        ax.grid(True, axis="y")
    fig.tight_layout(rect=plots_style.rect((0, 0, 1, 1)))
    plots_style.save_figure(fig, out_stem)


def _fmt_tick(value: float) -> str:
    return f"{value:g}".replace(".", ",")


# ---------- training trace ----------

def plot_trace(trace, title: str, out_stem) -> None:
    plt = plots_style.apply_style()
    trace = np.asarray(trace)
    colors = plots_style.palette_for(["QE", "TE"])
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    ax.plot(trace[:, 0], trace[:, 3], color=colors["QE"], linewidth=1.6, label="QE (eje izquierdo)")
    ax.set_xlabel("época")
    ax.set_ylabel("error de cuantización (z)", color=colors["QE"])
    twin = ax.twinx()
    twin.spines["right"].set_visible(True)
    twin.plot(trace[:, 0], trace[:, 4], color=colors["TE"], linewidth=1.6, label="TE (eje derecho)")
    twin.set_ylabel("error topográfico", color=colors["TE"])
    twin.set_ylim(bottom=0)
    handles = ax.get_lines() + twin.get_lines()
    ax.legend(handles, [h.get_label() for h in handles], frameon=False, fontsize=9, loc="upper right")
    ax.set_title(title, fontsize=11, loc="left")
    fig.tight_layout()
    plots_style.save_figure(fig, out_stem)


# ---------- the chosen grid ----------

def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def _stability_sd(stage1: Path) -> dict[str, float]:
    """SD (ddof 1) of the pairwise correlation values of every configuration (stability.csv)."""
    values: dict[str, list[float]] = {}
    for row in _read_csv(stage1 / "stability.csv"):
        if row["correlation"] not in ("", "nan", "NaN"):
            values.setdefault(row["label"], []).append(float(row["correlation"]))
    return {label: float(np.std(v, ddof=1)) if len(v) > 1 else 0.0 for label, v in values.items()}


def _unit(name: str) -> str:
    if name.endswith("_pct"):
        return "%"
    if name == "price_ars":
        return "ARS"
    if name.endswith("_per_1000"):
        return "por 1000"
    return ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Figures of the Kohonen grid chosen by the pre-registered rule.")
    parser.add_argument("--stage1", type=Path, default=DEFAULT_STAGE1,
                        help="stage-1 results folder (default: analysis/results/som/series_som_stage1)")
    parser.add_argument("--stage2", type=Path, default=DEFAULT_STAGE2,
                        help="stage-2 results folder (default: analysis/results/som/series_som_stage2)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help="output folder (default: analysis/results/som/figures)")
    args = parser.parse_args(argv)
    stage1: Path = args.stage1
    out: Path = args.out

    selection_path = stage1 / "selection.json"
    if not selection_path.is_file():
        raise SystemExit(f"{selection_path} not found; run `make som-stage1` first")
    som_stage.require_same_rule(selection_path, RULE_FILE)
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    if selection.get("chosen_k") is None or selection.get("outcome") != "chosen":
        raise SystemExit("selection.json has no chosen grid (outcome "
                         f"{selection.get('outcome')!r}): no map is drawn (D-14)")

    k = int(selection["chosen_k"])
    seed = int(selection["figure_seed"])
    run = som.read_run(TP_DIR / selection["figure_run"])
    if run.k != k:
        raise SystemExit(f"figure run has grid_k {run.k}, selection.json chose k = {k}")
    data = pca.som_input()
    features, meta = list(data["names"]), data["meta"]
    if list(run.features) != features:
        raise SystemExit("figure run features differ from the PCA score columns the map is trained on (run `make pca`)")
    loads = pca.loadings(data["result"])
    raw = load_creadores()
    column = {name: i for i, name in enumerate(raw.columns)}

    metrics = run.metrics
    out.mkdir(parents=True, exist_ok=True)
    neighborhood = NEIGHBORHOOD_NAMES.get(metrics["neighborhood"], metrics["neighborhood"])
    schedule = (f"vecindad {neighborhood}, R0 {_fmt(float(metrics['radius0']))} -> "
                f"{_fmt(float(metrics['radius_final']))}, eta {_fmt(float(metrics['eta0']))} -> "
                f"{_fmt(float(metrics['eta_final']))}, {metrics['epochs']} épocas")
    label = selection["chosen_label"]
    ident = f"k = {k} ({label}), {schedule}, seed {seed} (medoide de estabilidad entre las 10 seeds)"

    # hit map + U-matrix
    U = som.umatrix(run.prototypes, k)
    for _ in plots_style.iter_variants():  # report, then slide (D-08)
        plot_map(run.hits, U, k, f"SOM {k} x {k} ({label})",
                 f"{ident}. La orientación del mapa es arbitraria (rotarlo o reflejarlo no cambia nada de lo "
                 "medido). Celdas rayadas: neuronas sin creadores; la escala de la matriz U cubre todo el rango de "
                 "sus valores.", out / "map")

    # component planes
    prototypes = run.prototypes.reshape(k, k, -1)

    def pc_plane(name: str) -> Plane:
        return Plane(name, prototypes[:, :, features.index(name)], "pc", "peso")

    def raw_plane(name: str, unit: str) -> Plane:
        return Plane(name, neuron_raw_means(run.bmu, k, raw.values[:, column[name]]), "raw", unit)

    names = main_planes(loads, data["variables"])
    main_set = [raw_plane(name, _unit(name)) for name in names] + [raw_plane(name, "%") for name in EXTRA_RAW]
    plot_planes(main_set, k, run.hits,
                f"Planos de SOM {k} x {k}: variables principales de PC1 y PC2 (media cruda de cada neurona)",
                f"{ident}. Primeras 4 variables: mayor |carga| en PC1 de la PCA de las {len(data['variables'])} variables; "
                "las siguientes 4: mayor |carga| en PC2 (orientación de la Fase 1). El mapa se entrena con los scores "
                "de las componentes, no con las variables: cada plano es la media cruda de los creadores asignados a "
                "cada neurona y queda en blanco si la neurona está vacía. Las dos últimas son las variables que "
                "salieron por ser combinación exacta de otras. La orientación del mapa es arbitraria.",
                out / "planes_main", ncols=4)
    appendix = [pc_plane(name) for name in features] + [raw_plane(name, _unit(name)) for name in raw.columns]
    plot_planes(appendix, k, run.hits,
                f"Planos de SOM {k} x {k}: las {len(features)} componentes entrenadas y las {len(raw.columns)} "
                "variables originales",
                f"{ident}. Las componentes se muestran como el peso del prototipo (cada una con su escala centrada en "
                "0); las variables originales, como media cruda de los creadores de cada neurona. Celdas rayadas: "
                "neuronas vacías. La orientación del mapa es arbitraria.",
                out / "planes_appendix", ncols=6)

    # stage-1 curves and trace
    rows = _read_csv(stage1 / "aggregate.csv")
    sd = _stability_sd(stage1)
    for row in rows:
        row["stability_sd"] = str(sd.get(row["label"], 0.0))
    for _ in plots_style.iter_variants():
        plot_stage1_curves(rows, selection, out / "stage1_curves")
    stage2_rows = _read_csv(args.stage2 / "aggregate.csv")
    base = next(r for r in stage2_rows if r["label"] == "base")
    step_rows = sorted((r for r in rows if r["neighborhood"] == "step"), key=lambda r: int(r["grid_k"]))
    for _ in plots_style.iter_variants():
        plot_effect(step_rows, "grid_k", "k" if plots_style.variant() == "slide" else "k (lado de la grilla)", k, selection["thresholds"], out / "effect_k")
        plot_effect(effect_rows(stage2_rows, "eta0"), "eta0", "tasa de aprendizaje inicial η0", float(base["eta0"]),
                    selection["thresholds"], out / "effect_eta0")
        plot_effect(effect_rows(stage2_rows, "radius0"), "radius0", "radio inicial R0", float(base["radius0"]),
                    selection["thresholds"], out / "effect_radius0")
    plot_trace(run.trace, f"Traza del entrenamiento de la corrida dibujada: k = {k}, seed {seed}", out / "trace")

    # who is in each neuron
    with (out / "hits_members.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(["neuron", "row", "col", "hits", "creators"])
        for neuron in range(k * k):
            members = [meta["name"][i] for i in range(len(run.bmu)) if run.bmu[i] == neuron]
            writer.writerow([neuron, neuron // k, neuron % k, int(run.hits[neuron]), "; ".join(members)])
    print(f"figures -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
