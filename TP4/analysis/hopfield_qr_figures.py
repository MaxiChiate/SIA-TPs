#!/usr/bin/env python3
"""Figures of the Hopfield-on-QR comparison (HOP-04, HOP-05, HOP-06, HOP-07): glyphs, overlaps, the
three-rule recovery/overlap/cost comparison (hebb, pinv, hamming), the per-step energy trace for the
two dynamical rules (hebb, pinv), and the two limitation figures of Plan 05 (the shift triptych and
the Hebb majority attractor).

    .venv/bin/python analysis/hopfield_qr_figures.py [--results DIR] [--out DIR] [--limits-results DIR]

Reads the files `make hopfield-qr` wrote (overlaps.json, qr_facts.json, recall.csv, energy_trace.csv, run.json)
and refuses to draw (SystemExit) if `hopfield_qr_select.require_same_rule` rejects run.json - the protocol text,
the guard code, scripts/qr.py or one of the five PNGs changed since the run - or if the network code (the C core,
the driver, the config reader and the numpy control) differs from the sha256 run.json recorded as code_identity:
that identity is not pinned by the pre-registration guard, but the figures must come from the code that produced
the results (mirrors Phase 4's WR-02). The two limitation figures additionally read what
`make hopfield-qr-limits` wrote (majority.json, shift.json, run.json under qr_limits/, a directory sibling to
the qr/ this module otherwise reads) and refuse the same way if LIMITS_CODE_FILES's sha256 (hopfield_qr_limits.py,
hopfield.py) differs from what that run.json recorded. Every figure goes through plots_style.save_figure, so a
rerun gives byte-identical SVG files. numpy and matplotlib (through plots_style) only.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

TP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TP_DIR / "scripts"))
sys.path.insert(0, str(TP_DIR / "analysis"))

import hopfield  # noqa: E402
import hopfield_qr  # noqa: E402
import hopfield_qr_limits  # noqa: E402
import hopfield_qr_select  # noqa: E402
import plots_style  # noqa: E402
import qr  # noqa: E402

DEFAULT_RESULTS = TP_DIR / "analysis" / "results" / "hopfield" / "qr"
DEFAULT_OUT = DEFAULT_RESULTS / "figures"
# qr_limits/ is a SIBLING of qr/ (both under analysis/results/hopfield/), never the recall driver's own
# output directory - mirrors hopfield_qr_limits.RESULTS_SUBDIR's layout (D-01: make hopfield-qr never
# rmtrees qr_limits/).
DEFAULT_LIMITS_RESULTS = DEFAULT_RESULTS.parent / "qr_limits"
UPDATES = ("async", "sync")
UPDATE_LABELS = {"async": "asincrono (referencia)", "sync": "sincrono"}
# The three rules compared on the recovery figure, and the two with dynamics (the per-step energy panel and the
# cost/iterations panel are hebb-vs-pinv only: the Hamming baseline has no sweeps or energy, D-09).
RULES = ("hebb", "pinv", "hamming")
DYNAMICAL_RULES = ("hebb", "pinv")
RULE_LABELS = {"hebb": "Hebb", "pinv": "pseudo-inversa", "hamming": "Hamming 1-NN (lookup)"}
# Representative noise levels for the per-step energy panel, fixed by index before looking at any curve: the
# start, the middle and the top of the frozen 0..0.5 grid (D-05), not chosen for how their curves turned out.
ENERGY_LEVELS = (0.0, 0.25, 0.5)
FIGURE_STEMS = ("qr", "overlaps", "recovery", "energy_trace", "shift", "majority")
NEUTRAL_BAR = "#b9b8b3"
GLYPH_ON = "#1f1f1f"
GLYPH_OFF = "#ecebe6"


# ---------- small helpers ----------

def _caption(fig, text: str, width: int = 125, y: float = 0.01) -> None:
    plots_style.caption(fig, text, width, y)


def _fmt(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def _read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _read_rows(path: Path) -> list[dict]:
    with Path(path).open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def _clean_glyph_axes(ax) -> None:
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


def _qr_labels() -> list[str]:
    """Short display names in scripts/qr.py SOURCES order (beverages, dessert, food, specials, wine)."""
    return [name.removesuffix("_menu_qr.png") for name in qr.SOURCES]


# ---------- the five QR glyphs ----------

def plot_qr(patterns, out_stem) -> None:
    """The five 37x37 QR, display polarity dark = +1 (HOP-04)."""
    from matplotlib.colors import ListedColormap

    plt = plots_style.apply_style()
    patterns = np.asarray(patterns)
    p, n_pixels = patterns.shape
    side = int(round(n_pixels ** 0.5))
    labels = _qr_labels()
    cmap = ListedColormap([GLYPH_OFF, GLYPH_ON])
    fig, axes = plt.subplots(1, p, figsize=plots_style.figsize((2.6 * p + 0.6, 3.2)))
    for index, ax in enumerate(axes):
        ax.imshow(patterns[index].reshape(side, side), cmap=cmap, vmin=-1, vmax=1, interpolation="nearest")
        ax.set_title(labels[index], fontsize=plots_style.fontsize(10))
        _clean_glyph_axes(ax)
    plots_style.suptitle(fig, "Los 5 QR almacenados (37x37, pixel oscuro = +1)", fontsize=12, x=0.01, ha="left")
    fig.tight_layout(rect=plots_style.rect((0, 0.08, 1, 0.92)))
    _caption(fig, "Cada glifo es el patron +-1 del QR, fila por fila, en el orden fijo de scripts/qr.py SOURCES "
                  "(el que indexa el subconjunto [0, 1, 2, 3, 4]).")
    plots_style.save_figure(fig, out_stem)


# ---------- 5x5 overlap matrix ----------

def plot_overlaps(overlaps: dict, out_stem) -> None:
    """The 5x5 overlap matrix as a divergent heatmap, annotated with the integer dot and the /N overlap (HOP-04)."""
    plt = plots_style.apply_style()
    n = int(overlaps["n_pixels"])
    labels = _qr_labels()
    dots = np.asarray(overlaps["dots"])
    matrix = np.asarray(overlaps["overlaps"], dtype=np.float64)
    p = matrix.shape[0]
    slide = plots_style.variant() == "slide"
    fig, ax = plt.subplots(figsize=plots_style.figsize((6.4, 6.0)))
    image = ax.imshow(matrix, cmap=plots_style.DIVERGING, vmin=-1, vmax=1, aspect="equal")
    for row in range(p):
        for col in range(p):
            strong = abs(matrix[row, col]) > 0.6
            ax.text(col, row, f"{int(dots[row, col])}\n{_fmt(matrix[row, col])}", ha="center", va="center",
                    fontsize=plots_style.fontsize(10), color="white" if strong else plots_style.TEXT_PRIMARY)
    ax.set_xticks(range(p))
    ax.set_yticks(range(p))
    ax.set_xticklabels(labels, fontsize=plots_style.fontsize(10), rotation=20, ha="right")
    ax.set_yticklabels(labels, fontsize=plots_style.fontsize(10))
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    if slide:  # square matrix at the left, its numbers read off at the right
        fig.subplots_adjust(left=0.25, right=0.5344, top=0.95, bottom=0.2)
        bar = fig.colorbar(image, cax=fig.add_axes([0.56, 0.2, 0.015, 0.75]))
        fig.text(0.68, 0.58, f"max |solapamiento| = {_fmt(overlaps['max_abs_overlap'])}\n"
                             f"media = {_fmt(overlaps['mean_abs_overlap'])}", ha="left", va="center",
                 fontsize=plots_style.fontsize(10), color=plots_style.TEXT_PRIMARY)
    else:
        bar = fig.colorbar(image, ax=ax, fraction=0.045, pad=0.03)
    bar.set_label("solapamiento d / N")
    plots_style.suptitle(fig, "Solapamientos entre los 5 QR almacenados", fontsize=12, x=0.01, ha="left")
    if not slide:
        fig.subplots_adjust(left=0.18, right=0.86, top=0.88, bottom=0.2)
    _caption(fig, f"En cada celda, el producto escalar entero d y el solapamiento d / {n}. max|solapamiento| = "
                  f"{_fmt(overlaps['max_abs_overlap'])}, media = {_fmt(overlaps['mean_abs_overlap'])}: los 5 QR "
                  "estan lejos de ser ortogonales entre si, la causa raiz del fallo de Hebb (HOP-04, D-11a).")
    plots_style.save_figure(fig, out_stem)


# ---------- the three-rule recovery curve, continuous overlap, sweeps and energy (HOP-06, D-03, D-09) ----------

def plot_recovery(rows: list[dict], out_stem) -> None:
    """Three panels: exact recovery (hebb, pinv, hamming - async as the reference line, sync a labelled
    companion for the two dynamical rules, hamming a single no-update line) with +-seed-SD bands; the continuous
    mean |final overlap| for the same three; and the dynamical cost (sweeps, final energy) for hebb vs pinv only
    (the Hamming lookup has no dynamics, annotated as instantaneous, D-09). Colour is by rule (stable across
    panels), linestyle by update (solid async, dashed sync)."""
    plt = plots_style.apply_style()
    colors = plots_style.palette_for(list(RULES))
    slide = plots_style.variant() == "slide"
    short = {"hebb": "Hebb", "pinv": "pinv", "hamming": "Hamming"}
    fig, axes = plt.subplots(1, 3, figsize=plots_style.figsize((16.5, 5.4)))
    recall_ax, overlap_ax, cost_ax = axes
    energy_ax = cost_ax.twinx()

    for rule in RULES:
        mine_rule = [r for r in rows if r["rule"] == rule]
        updates = (hopfield_qr.HAMMING_UPDATE,) if rule == "hamming" else UPDATES
        for update in updates:
            mine = sorted((r for r in mine_rule if r["update"] == update), key=lambda r: float(r["noise"]))
            if not mine:
                continue
            noise = np.array([float(r["noise"]) for r in mine])
            rate = np.array([float(r["recall_rate"]) for r in mine])
            sd = np.array([float(r["recall_sd_seeds"]) for r in mine])
            overlap = np.array([float(r["mean_final_overlap"]) for r in mine])
            style = "-" if (rule == "hamming" or update == "async") else "--"
            label = RULE_LABELS[rule] if rule == "hamming" else f"{RULE_LABELS[rule]} ({UPDATE_LABELS[update]})"
            if slide:  # short names; one legend under the three panels
                label = "Hamming (lookup)" if rule == "hamming" else f"{short[rule]} ({update})"
            recall_ax.plot(noise, rate, style, marker="o", markersize=4, color=colors[rule], label=label)
            recall_ax.fill_between(noise, np.clip(rate - sd, 0, 1), np.clip(rate + sd, 0, 1), color=colors[rule],
                                   alpha=0.12, linewidth=0)
            overlap_ax.plot(noise, overlap, style, marker="o", markersize=4, color=colors[rule], label=label)

    for rule in DYNAMICAL_RULES:
        mine_rule = [r for r in rows if r["rule"] == rule]
        for update in UPDATES:
            mine = sorted((r for r in mine_rule if r["update"] == update), key=lambda r: float(r["noise"]))
            if not mine:
                continue
            noise = np.array([float(r["noise"]) for r in mine])
            sweeps = np.array([float(r["mean_sweeps"]) for r in mine])
            energy = np.array([float(r["mean_final_energy"]) for r in mine])
            style = "-" if update == "async" else "--"
            label = f"{RULE_LABELS[rule]} ({UPDATE_LABELS[update]})"
            cost_ax.plot(noise, sweeps, style, marker="s", markersize=4, color=colors[rule],
                        label=f"{label}: barridos")
            energy_ax.plot(noise, energy, style, marker="^", markersize=4, color=colors[rule], alpha=0.55,
                           label=f"{label}: energia")

    recall_ax.set_ylim(0, 1.05 if slide else 1.18)
    recall_ax.set_xlabel("nivel de ruido" if slide else "nivel de ruido (fraccion de pixeles invertidos)")
    recall_ax.set_ylabel("tasa de recuperacion exacta")
    if slide:
        slide_handles, slide_labels = recall_ax.get_legend_handles_labels()
        fig.legend(slide_handles, slide_labels, fontsize=plots_style.fontsize(8), frameon=False, ncol=5,
                   loc="lower center")
    else:
        recall_ax.legend(fontsize=6.5, frameon=False, ncol=1, loc="upper left", bbox_to_anchor=(0.0, 1.02))
    recall_ax.set_title("Recuperacion exacta" if slide else "Exito exacto, 3 reglas (D-03, D-08)",
                        fontsize=plots_style.fontsize(10), loc="left")

    pinv_zero = next((r for r in rows if r["rule"] == "pinv" and r["update"] == "async"
                      and abs(float(r["noise"])) < 1e-9), None)
    if pinv_zero is not None:
        rate0 = float(pinv_zero["recall_rate"])
        note = (f"pinv a ruido 0: {_fmt(rate0 * 100, 0)}% exacto" if slide else
                f"pinv a ruido 0: {_fmt(rate0 * 100, 0)}% exacto\n({'los 5 QR son' if rate0 == 1.0 else 'no todos los QR son'} "
                "puntos fijos)")
        recall_ax.annotate(
            note, xy=(0.9, 0.12) if slide else (0.98, 0.04), xycoords="axes fraction", ha="right", va="bottom",
            fontsize=plots_style.fontsize(7.5), color=plots_style.TEXT_SECONDARY, style="italic")

    overlap_ax.set_ylim(0, 1.02)
    overlap_ax.set_xlabel("nivel de ruido")
    overlap_ax.set_ylabel("|solapamiento final| medio" if slide else "|solapamiento final| medio con el objetivo")
    if not slide:
        overlap_ax.legend(fontsize=6.5, frameon=False, loc="lower left")
    overlap_ax.set_title("Cercania continua" if slide else "Cercania continua, 3 reglas (|m|, D-03)",
                         fontsize=plots_style.fontsize(10), loc="left")

    cost_ax.set_xlabel("nivel de ruido")
    cost_ax.set_ylabel("barridos (cuadrado)" if slide else "barridos medios (marcador cuadrado)")
    energy_ax.set_ylabel("energia final (triangulo)" if slide else "energia final media (marcador triangulo)")
    if not slide:  # in the slide the colour and line style are those of the legend under the panels
        handles = cost_ax.get_legend_handles_labels()[0] + energy_ax.get_legend_handles_labels()[0]
        labels_all = cost_ax.get_legend_handles_labels()[1] + energy_ax.get_legend_handles_labels()[1]
        cost_ax.legend(handles, labels_all, fontsize=6, frameon=False, loc="lower right", bbox_to_anchor=(0.72, 0.0))
    cost_ax.set_title("Costo: hebb vs pinv" if slide else "Costo dinamico: hebb vs pinv (D-09)",
                      fontsize=plots_style.fontsize(10), loc="left")
    cost_ax.annotate("Hamming: lookup\ninstantaneo, sin\nbarridos ni energia" if not slide else
                     "Hamming: lookup,\nsin barridos", xy=(0.02, 0.8) if slide else (0.99, 0.5),
                     xycoords="axes fraction", ha="left" if slide else "right", va="center",
                     fontsize=plots_style.fontsize(7),
                     color=plots_style.TEXT_SECONDARY, style="italic")

    trials = int(rows[0]["n_trials"]) if rows else 0
    plots_style.suptitle(fig, "Hebb, pseudo-inversa y Hamming sobre los 5 QR: recuperacion frente al ruido",
                         fontsize=12, x=0.01, ha="left")
    fig.tight_layout(rect=plots_style.rect((0, 0.1, 1, 0.94), slide=(0, 0.12, 1, 1)))
    _caption(fig, f"Cada punto agrupa {trials} ensayos (5 QR, 30 ensayos, 10 seeds); la banda es +- el desvio "
                  "entre seeds. hebb y pinv comparten la MISMA grilla de ruido (D-05); el lookup de Hamming la "
                  "reproduce con el mismo k y las mismas etiquetas de seed pero sorteos propios, independientes "
                  "del core en C (comparacion sobre la misma distribucion, no sobre sorteos identicos). El "
                  "veredicto de verdict.json se deriva de esta misma curva, no al reves (D-02).")
    plots_style.save_figure(fig, out_stem)


# ---------- per-step energy trace, hebb and pinv (HOP-05 "energia por paso") ----------

def _plot_energy_trace_slide(by_key: dict, rules: list, sources: list, levels: list, labels: list, out_stem) -> None:
    """Slide layout of the energy trace: 5 rows x 3 columns do not fit the slide figure area at slide type size,
    so there is one row per dynamical rule and one column per noise level, with the five QR traces of the same
    cell overlaid (colour by QR). The same traced trials as the report figure, each on its own energy scale."""
    plt = plots_style.apply_style()
    qr_colors = plots_style.palette_for(labels)
    fig, axes = plt.subplots(len(rules), len(levels), figsize=plots_style.figsize((12.0, 6.0)), squeeze=False)
    for i, rule in enumerate(rules):
        for c, level in enumerate(levels):
            ax = axes[i, c]
            values = []
            for source in sources:
                series = sorted(by_key.get((rule, source, round(level, 2)), []))
                if series:
                    ax.step([step for step, _e in series], [energy for _s, energy in series], where="post",
                            color=qr_colors[labels[source]], linewidth=1.8, label=labels[source])
                    values.extend(energy for _s, energy in series)
            if values and max(values) - min(values) < 1e-6 * max(1.0, abs(max(values))):
                # a constant trace (the stored QR is already a fixed point): one tick, no 1e-9 offset label
                level_value = float(np.mean(values))
                ax.set_ylim(level_value - 1.0, level_value + 1.0)
                ax.set_yticks([level_value])
                ax.set_yticklabels([f"{level_value:.1f}".replace("-", "\u2212")])
            if i == 0:
                ax.set_title(f"ruido {_fmt(level)}", fontsize=plots_style.fontsize(10), loc="left")
            if c == 0:
                ax.set_ylabel(f"energia {rule}")
            if i == len(rules) - 1:
                ax.set_xlabel("paso (asincrono)")
    handles, names = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, names, fontsize=plots_style.fontsize(8), frameon=False, ncol=len(names), loc="lower center")
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    plots_style.save_figure(fig, out_stem)


def plot_energy_trace(rows: list[dict], out_stem) -> None:
    """Rows: the five QR; columns: ENERGY_LEVELS, fixed by index before looking at any curve. Overlays hebb's and
    pinv's traced-trial per-step energy in the same panel (color by rule, Plan 04): both are async reference-update
    traces of one fixed seed, so HOP-05's "energia por paso" is rendered for both dynamical rules. pinv's energy
    magnitude is far smaller than Hebb's integer-sum energy (its W entries are bounded, not sums over N=1369
    patterns): a shared y-axis would flatten pinv's curve to an invisible line, so each panel gives pinv its own
    twin y-axis (same color-by-rule convention as the cost panel of plot_recovery)."""
    plt = plots_style.apply_style()
    labels = _qr_labels()
    rules = [rule for rule in DYNAMICAL_RULES if any(r["rule"] == rule for r in rows)]
    colors = plots_style.palette_for(rules)
    sources = sorted({int(r["source"]) for r in rows})
    levels = [level for level in ENERGY_LEVELS if any(abs(float(r["noise"]) - level) < 1e-9 for r in rows)]
    by_key: dict[tuple, list] = {}
    for r in rows:
        key = (r["rule"], int(r["source"]), round(float(r["noise"]), 2))
        by_key.setdefault(key, []).append((int(r["step"]), float(r["energy"])))
    if plots_style.variant() == "slide":
        _plot_energy_trace_slide(by_key, rules, sources, levels, labels, out_stem)
        return
    fig, axes = plt.subplots(len(sources), len(levels), figsize=(4.0 * len(levels), 2.3 * len(sources) + 1.3),
                             squeeze=False, sharex=False)
    legend_handles: list = []
    for r, source in enumerate(sources):
        for c, level in enumerate(levels):
            ax = axes[r, c]
            twin = ax.twinx() if "pinv" in rules else None
            panel_axes = {"hebb": ax, "pinv": twin if twin is not None else ax}
            drew = False
            for rule in rules:
                series = sorted(by_key.get((rule, source, round(level, 2)), []))
                if not series:
                    continue
                steps = [s for s, _e in series]
                energies = [e for _s, e in series]
                line, = panel_axes[rule].step(steps, energies, where="post", color=colors[rule], linewidth=1.6,
                                              label=RULE_LABELS.get(rule, rule))
                if r == 0 and c == 0:
                    legend_handles.append(line)
                drew = True
            if not drew:
                ax.axis("off")
                if twin is not None:
                    twin.axis("off")
                continue
            ax.set_title(f"{labels[source]}, ruido {_fmt(level)}", fontsize=9, loc="left")
            if c == 0:
                ax.set_ylabel("energia hebb", color=colors.get("hebb", plots_style.TEXT_PRIMARY), fontsize=8)
            if twin is not None and c == len(levels) - 1:
                twin.set_ylabel("energia pinv", color=colors.get("pinv", plots_style.TEXT_PRIMARY), fontsize=8)
            if r == len(sources) - 1:
                ax.set_xlabel("paso (actualizacion asincrona)")
    if legend_handles:
        fig.legend(legend_handles, [h.get_label() for h in legend_handles], fontsize=8, frameon=False, ncol=2,
                  loc="upper right", bbox_to_anchor=(0.99, 0.985))
    plots_style.suptitle(fig, "Energia por paso, asincrono (hebb vs pinv, un ensayo trazado por celda, seed fija)",
                         fontsize=12, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.07, 1, 0.93))
    _caption(fig, "Un ensayo por panel (el primero trazado de cada QR y nivel de ruido de la seed fija de "
                  "energy_trace.csv) para hebb y para pinv, no elegido por su forma. Cada panel tiene un eje "
                  "propio por regla (la energia de pinv es mucho menor en magnitud que la de hebb, que suma sobre "
                  "N=1369). La energia asincrona nunca sube para ninguna de las dos reglas (HOP-05 'energia por "
                  "paso'), a diferencia de la energia final por nivel que recall.csv promedia sobre todos los "
                  "ensayos.")
    plots_style.save_figure(fig, out_stem)


# ---------- shift triptych: source / shifted / recovered under pinv (HOP-07, D-11b) ----------

def plot_shift(shift: dict, out_stem) -> None:
    """One row per shift magnitude in shift.json: the source QR glyph, the shifted query glyph and the
    recovered-state glyph (display polarity dark = +1), each annotated with the MEASURED Hamming distance
    to the source - never a forced or predicted number, read straight from shift.json (D-11b)."""
    from matplotlib.colors import ListedColormap

    plt = plots_style.apply_style()
    n = int(shift["n_pixels"])
    side = int(round(n ** 0.5))
    source_img = np.asarray(shift["source_pattern"], dtype=np.int64).reshape(side, side)
    shifts = sorted(shift["shifts"], key=lambda e: int(e["shift"]))
    labels = _qr_labels()
    source_label = labels[int(shift["source"])]
    cmap = ListedColormap([GLYPH_OFF, GLYPH_ON])
    slide = plots_style.variant() == "slide"
    if slide:  # one row: the source, then (shifted, recovered) for each shift magnitude
        fig, axes = plt.subplots(1, 1 + 2 * len(shifts), figsize=plots_style.figsize((8.4, 3.6 * len(shifts) + 0.8)),
                                 squeeze=False)
        panels_row = [(source_img, f"{source_label}\n(original)")]
        for entry in shifts:
            panels_row.append((np.asarray(entry["query"], dtype=np.int64).reshape(side, side),
                               f"desplazado {entry['shift']} px\nHamming = {entry['query_hamming']}"))
            panels_row.append((np.asarray(entry["recovered"], dtype=np.int64).reshape(side, side),
                               f"pinv recupera\nHamming = {entry['recovered_hamming']}"))
        for col, (img, title) in enumerate(panels_row):
            ax = axes[0, col]
            ax.imshow(img, cmap=cmap, vmin=-1, vmax=1, interpolation="nearest")
            ax.set_title(title, fontsize=plots_style.fontsize(9))
            _clean_glyph_axes(ax)
    else:
        fig, axes = plt.subplots(len(shifts), 3, figsize=(8.4, 3.6 * len(shifts) + 0.8), squeeze=False)
    for row, entry in enumerate([] if slide else shifts):  # the report grid; the slide row is drawn above
        query_img = np.asarray(entry["query"], dtype=np.int64).reshape(side, side)
        recovered_img = np.asarray(entry["recovered"], dtype=np.int64).reshape(side, side)
        panels = (
            (source_img, f"{source_label} (original)"),
            (query_img, f"desplazado {entry['shift']} px\n(Hamming = {entry['query_hamming']})"),
            (recovered_img, f"recuperado bajo pinv\n(Hamming = {entry['recovered_hamming']})"),
        )
        for col, (img, title) in enumerate(panels):
            ax = axes[row, col]
            ax.imshow(img, cmap=cmap, vmin=-1, vmax=1, interpolation="nearest")
            ax.set_title(title, fontsize=9)
            _clean_glyph_axes(ax)
    plots_style.suptitle(fig, "Sensibilidad a corrimientos: antes / desplazado / recuperado bajo pinv (HOP-07, D-11b)",
                fontsize=12, x=0.01, ha="left")
    # subplots_adjust (not tight_layout, D-11b figure legibility fix): row titles need generous hspace or
    # they collide with the glyph of the row above (found and fixed before this task's commit).
    if slide:
        fig.subplots_adjust(left=0.02, right=0.98, top=0.78, bottom=0.02, wspace=0.12)
    else:
        fig.subplots_adjust(left=0.02, right=0.98, top=0.90, bottom=0.14, hspace=0.75, wspace=0.08)
    _caption(fig, f"Corrimiento con relleno en cero ({shift['edge_convention']}); la red evoluciona desde la "
                  "consulta desplazada bajo la W de pseudo-inversa con una corrida asincrona propia (no la traza "
                  "de hopfield.py). La distancia de Hamming medida a la fuente es un hallazgo, nunca forzada: "
                  "este corrimiento de pocos pixeles ya mueve una fraccion grande de los 1369 pixeles.")
    plots_style.save_figure(fig, out_stem)


# ---------- the Hebb majority attractor (HOP-07, D-11a, Pitfall 1) ----------

def plot_majority(majority: dict, out_stem) -> None:
    """The pixel-wise majority attractor glyph (display polarity dark = +1) plus a bar of its Hamming
    distance to each of the five stored QR - never zero, the root cause of Hebb's failure on these
    correlated patterns (D-11a)."""
    from matplotlib.colors import ListedColormap

    plt = plots_style.apply_style()
    n = int(majority["n_pixels"])
    side = int(round(n ** 0.5))
    maj_img = np.asarray(majority["majority"], dtype=np.int64).reshape(side, side)
    labels = _qr_labels()
    hamming = [int(h) for h in majority["hamming_to_targets"]]
    colors = plots_style.palette_for(labels)
    cmap = ListedColormap([GLYPH_OFF, GLYPH_ON])
    fig, (glyph_ax, bar_ax) = plt.subplots(1, 2, figsize=plots_style.figsize((9.6, 3.6)),
                                           gridspec_kw={"width_ratios": [1, 1.6]})
    glyph_ax.imshow(maj_img, cmap=cmap, vmin=-1, vmax=1, interpolation="nearest")
    glyph_ax.set_title("Atractor mayoria de Hebb", fontsize=plots_style.fontsize(10))
    _clean_glyph_axes(glyph_ax)
    bar_ax.bar(labels, hamming, color=[colors[label] for label in labels])
    top = max(hamming) if hamming else 0
    bar_ax.set_ylim(0, top * 1.18 if top else 1)
    for index, value in enumerate(hamming):
        bar_ax.text(index, value + top * 0.03, str(value), ha="center", va="bottom", fontsize=plots_style.fontsize(8))
    bar_ax.set_ylabel("distancia de Hamming" if plots_style.variant() == "slide"
                      else f"distancia de Hamming al atractor (de {n})", fontsize=plots_style.fontsize(9))
    bar_ax.set_title("Distancia a cada QR almacenado", fontsize=plots_style.fontsize(10), loc="left")
    plots_style.suptitle(fig, "El atractor comun de Hebb no coincide con ningun QR almacenado (HOP-07, D-11a)", fontsize=12,
                x=0.01, ha="left")
    if plots_style.variant() == "slide":
        fig.subplots_adjust(left=0.03, right=0.98, top=0.9, bottom=0.1, wspace=0.3)
    else:
        fig.subplots_adjust(left=0.03, right=0.98, top=0.82, bottom=0.26, wspace=0.28)
    _caption(fig, f"Mayoria pixel a pixel de los 5 QR (signo de la suma por pixel); distancia minima "
                  f"{min(hamming) if hamming else 0}, maxima {max(hamming) if hamming else 0} de {n} pixeles - "
                  "nunca cero. Es el estado al que la dinamica de Hebb tiende a colapsar en vez de recuperar la "
                  "consulta, la causa raiz medida del fallo visto en el panel de recuperacion (HOP-04, D-11a).")
    plots_style.save_figure(fig, out_stem)


# ---------- driver ----------

def require_same_code(run: dict, repo_dir=TP_DIR) -> None:
    """Refuse unless the network code is the one run.json recorded (mirrors Phase 4's WR-02). A run.json without
    code_identity counts as every file changed."""
    changed = hopfield_qr.changed_code_files(run.get("code_identity"), repo_dir)
    if changed:
        raise SystemExit(f"the results come from different network code: {', '.join(changed)} differ from the "
                         "sha256 recorded in run.json (code_identity); re-run make hopfield-qr")


def require_same_limits_code(limits_run: dict, repo_dir=TP_DIR) -> None:
    """Refuse unless the limitation generators' own code (LIMITS_CODE_FILES) is the one qr_limits/run.json
    recorded. A run.json without code_identity counts as every file changed."""
    changed = hopfield_qr_limits.changed_code_files(limits_run.get("code_identity"), repo_dir)
    if changed:
        raise SystemExit(f"the limitation results come from different code: {', '.join(changed)} differ from "
                         "the sha256 recorded in qr_limits/run.json (code_identity); re-run make hopfield-qr-limits")


def draw(results_dir, out_dir, patterns_path=None, check_rule: bool = True, check_code: bool = True,
         repo_dir=TP_DIR, limits_results_dir=None) -> list[Path]:
    results_dir = Path(results_dir)
    out_dir = Path(out_dir)
    run_path = results_dir / "run.json"
    if not run_path.exists():
        raise SystemExit(f"{run_path}: not found, run make hopfield-qr first")
    if check_rule:
        hopfield_qr_select.require_same_rule(run_path, repo_dir)
    run = _read_json(run_path)
    if check_code:
        require_same_code(run, repo_dir)

    # qr_limits/run.json carries only code_identity (no rule identity of its own, D-01): the SAME protocol
    # was already checked above against the recall driver's run.json, so only the limitation generators'
    # own code (LIMITS_CODE_FILES) needs its own refusal here.
    if limits_results_dir is None:
        limits_results_dir = results_dir.parent / "qr_limits"
    limits_results_dir = Path(limits_results_dir)
    limits_run_path = limits_results_dir / "run.json"
    if not limits_run_path.exists():
        raise SystemExit(f"{limits_run_path}: not found, run make hopfield-qr-limits first")
    limits_run = _read_json(limits_run_path)
    if check_code:
        require_same_limits_code(limits_run, repo_dir)

    overlaps = _read_json(results_dir / "overlaps.json")
    if patterns_path is None:
        patterns_path = TP_DIR / run["design"]["patterns_path"]
    patterns = hopfield.load_patterns(patterns_path)
    recall_rows = _read_rows(results_dir / "recall.csv")
    energy_rows = _read_rows(results_dir / "energy_trace.csv")
    majority = _read_json(limits_results_dir / "majority.json")
    shift = _read_json(limits_results_dir / "shift.json")

    out_dir.mkdir(parents=True, exist_ok=True)
    # D-08: all six figures also get a slide variant, drawn by the same plot functions.
    for _ in plots_style.iter_variants():
        plot_qr(patterns, out_dir / "qr")
        plot_overlaps(overlaps, out_dir / "overlaps")
        plot_recovery(recall_rows, out_dir / "recovery")
        plot_energy_trace(energy_rows, out_dir / "energy_trace")
        plot_shift(shift, out_dir / "shift")
        plot_majority(majority, out_dir / "majority")
    return [out_dir / f"{stem}.{suffix}" for stem in FIGURE_STEMS for suffix in ("svg", "png")]


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(TP_DIR).as_posix()
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS, help="directory of make hopfield-qr")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="directory of the figures")
    parser.add_argument("--limits-results", type=Path, default=DEFAULT_LIMITS_RESULTS,
                        help="directory of make hopfield-qr-limits")
    args = parser.parse_args(argv)
    if not (args.results / "run.json").exists():
        raise SystemExit(f"{args.results / 'run.json'}: not found, run make hopfield-qr first")
    for path in draw(args.results, args.out, limits_results_dir=args.limits_results):
        print(_display(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
