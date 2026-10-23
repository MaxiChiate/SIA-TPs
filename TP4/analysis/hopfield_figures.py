#!/usr/bin/env python3
"""Figures of the pre-registered Hopfield letters run (HOP-02, HOP-03, D-06): glyphs, overlaps, cross terms, recall,
energy, capacity and the spurious state.

    .venv/bin/python analysis/hopfield_figures.py [--results DIR] [--out DIR]

Reads the files `make hopfield-letters` wrote (selection.json, orthogonality.json, run.json, recall.csv, the
recall sweep, capacity_p4.csv, capacity_by_p.csv, capacity.json and spurious.json) and refuses to draw unless `hopfield_select.require_same_rule` accepts the selection.json: the rule
text, the selection code, the alphabet and the converter must be the ones the run recorded (D-04). It also
refuses when the network code (the C core, the driver, the config reader and the numpy control) differs from the
sha256 that run.json recorded as code_identity: those files are not pinned by the rule, but the figures must come
from the code that produced the results (WR-02). The energy
panels are the first traced trial of seed ENERGY_SEED for each letter of the separated set and each level of
ENERGY_LEVELS_K, fixed by index before looking at any curve. Every figure goes through plots_style.save_figure, so
a rerun gives byte-identical SVG files. numpy and matplotlib (through plots_style) only.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import textwrap
from pathlib import Path

import numpy as np

TP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TP_DIR / "scripts"))
sys.path.insert(0, str(TP_DIR / "analysis"))

import hopfield  # noqa: E402
import hopfield_letters  # noqa: E402
import hopfield_select  # noqa: E402
import plots_style  # noqa: E402

DEFAULT_RESULTS = TP_DIR / "analysis" / "results" / "hopfield" / "letters"
DEFAULT_OUT = TP_DIR / "analysis" / "results" / "hopfield" / "figures"
ENERGY_LEVELS_K = (3, 6, 9)
ENERGY_SEED = 1
SET_NAMES = ("separated", "correlated")
SET_LABELS = {"separated": "separado", "correlated": "correlacionado"}
VARIANTS = ("separated-async", "separated-sync", "correlated-async", "correlated-sync")
FAILURE_CLASSES = (("wrong_stored_rate", "otra letra almacenada"), ("inverse_rate", "inverso"),
                   ("mixture_rate", "mezcla"), ("other_rate", "otro"))
NEUTRAL_BAR = "#b9b8b3"
GLYPH_ON = "#1f1f1f"
GLYPH_OFF = "#ecebe6"
FIGURE_STEMS = ("letters", "overlaps", "max_overlap_hist", "cross_terms", "recall_noise", "energy", "capacity_p4",
                "capacity_by_p", "spurious")
SPURIOUS_ORDER = ("inverse", "mixture", "other")
SPURIOUS_TEXT = {"inverse": "inverso", "mixture": "mezcla", "other": "otro"}
MEAN_OVERLAP_STEP = 0.04


# ---------- small helpers ----------

def _caption(fig, text: str, width: int = 125, y: float = 0.01) -> None:
    fig.text(0.01, y, textwrap.fill(text, width), ha="left", va="bottom", fontsize=8,
             color=plots_style.TEXT_SECONDARY)


def _fmt(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def _side(n_pixels: int) -> int:
    side = int(round(math.sqrt(n_pixels)))
    if side * side != n_pixels:
        raise SystemExit(f"{n_pixels} pixels is not a square glyph")
    return side


def _read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _read_rows(path: Path) -> list[dict]:
    with Path(path).open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def _colors() -> dict:
    return plots_style.palette_for(list(SET_NAMES))


def _clean_glyph_axes(ax) -> None:
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


# ---------- glyphs ----------

def plot_letters(patterns, letters, sets: dict, out_stem) -> None:
    """All glyphs on a grid of 6 columns; a coloured frame marks the letters of each set.

    sets maps a set name to the row indices of its letters."""
    from matplotlib.colors import ListedColormap
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle

    plt = plots_style.apply_style()
    patterns = np.asarray(patterns)
    n_letters, n_pixels = patterns.shape
    side = _side(n_pixels)
    colors = _colors()
    columns = 6
    rows = math.ceil(n_letters / columns)
    fig, axes = plt.subplots(rows, columns, figsize=(1.7 * columns + 0.6, 1.8 * rows + 1.6))
    axes = np.atleast_2d(axes)
    cmap = ListedColormap([GLYPH_OFF, GLYPH_ON])
    for index in range(rows * columns):
        ax = axes[index // columns, index % columns]
        if index >= n_letters:
            ax.axis("off")
            continue
        ax.imshow(patterns[index].reshape(side, side), cmap=cmap, vmin=-1, vmax=1, interpolation="nearest")
        ax.set_title(letters[index], fontsize=10)
        _clean_glyph_axes(ax)
        offset = 0.0
        for name in SET_NAMES:
            if index in sets.get(name, ()):
                ax.add_patch(Rectangle((-0.5 + offset, -0.5 + offset), side - 2 * offset, side - 2 * offset,
                                       fill=False, edgecolor=colors[name], linewidth=3.2))
                offset += 0.16
    handles = [Line2D([0], [0], color=colors[name], linewidth=3.2,
                      label=f"{SET_LABELS[name]}: {', '.join(letters[i] for i in sets.get(name, ()))}")
               for name in SET_NAMES]
    fig.legend(handles=handles, loc="upper right", fontsize=9, frameon=False, ncol=2)
    fig.suptitle("Alfabeto de 5×5 (píxel encendido = +1, oscuro)", fontsize=12, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.08, 1, 0.94), h_pad=1.6)
    _caption(fig, "Cada glifo es el patrón ±1 de la letra, fila por fila. El marco de color señala las letras de "
                  "cada set elegido por la regla fijada antes de las corridas (solo con los bitmaps).")
    plots_style.save_figure(fig, out_stem)


# ---------- overlaps ----------

def plot_overlaps(orthogonality: dict, out_stem) -> None:
    plt = plots_style.apply_style()
    n = int(orthogonality["n_pixels"])
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 6.0))
    image = None
    for ax, name in zip(axes, SET_NAMES):
        entry = orthogonality[name]
        overlaps = np.asarray(entry["overlaps"], dtype=np.float64)
        dots = np.asarray(entry["dots"])
        p = len(entry["letters"])
        image = ax.imshow(overlaps, cmap=plots_style.DIVERGING, vmin=-1, vmax=1, aspect="equal")
        for row in range(p):
            for col in range(p):
                strong = abs(overlaps[row, col]) > 0.6
                ax.text(col, row, f"{int(dots[row, col])}\n{_fmt(overlaps[row, col])}", ha="center", va="center",
                        fontsize=10, color="white" if strong else plots_style.TEXT_PRIMARY)
        ax.set_xticks(range(p))
        ax.set_yticks(range(p))
        ax.set_xticklabels(entry["letters"], fontsize=11)
        ax.set_yticklabels(entry["letters"], fontsize=11)
        ax.tick_params(length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.set_title(f"Set {SET_LABELS[name]}: {''.join(entry['letters'])}", fontsize=10, loc="left")
    bar = fig.colorbar(image, ax=list(axes), fraction=0.035, pad=0.03)
    bar.set_label("solapamiento d / N")
    fig.suptitle("Solapamientos entre las letras de cada set", fontsize=12, x=0.01, ha="left")
    fig.subplots_adjust(left=0.05, right=0.86, top=0.88, bottom=0.2)
    _caption(fig, f"En cada celda, el producto escalar entero d y el solapamiento d / {n}. Con N = {n} píxeles d es "
                  "impar, así que ningún par es exactamente ortogonal; la diagonal vale 1 por definición. Las dos "
                  "matrices comparten la escala de -1 a 1.")
    plots_style.save_figure(fig, out_stem)


# ---------- distribution of the max overlap over all subsets ----------

def plot_max_overlap_hist(selection: dict, out_stem) -> None:
    plt = plots_style.apply_style()
    histogram = selection["max_abs_overlap_histogram"]
    colors = _colors()
    overlaps = [entry["max_abs_overlap"] for entry in histogram]
    counts = [entry["n_subsets"] for entry in histogram]
    total = int(sum(counts))
    n = int(round(histogram[0]["max_abs_dot"] / histogram[0]["max_abs_overlap"]))
    size = len(selection[SET_NAMES[0]]["letters"])
    step = (overlaps[1] - overlaps[0]) if len(overlaps) > 1 else 2.0 / n
    fig, ax = plt.subplots(figsize=(10.5, 5.6))
    for entry in histogram:
        marked = [name for name in SET_NAMES if name in entry["sets"]]
        color = colors[marked[0]] if marked else NEUTRAL_BAR
        ax.bar(entry["max_abs_overlap"], entry["n_subsets"], width=0.85 * step, color=color)
        label = f"{entry['n_subsets']}"
        if marked:
            label += "\n" + ", ".join(f"{SET_LABELS[m]} {selection[m]['letters']}" for m in marked)
        ax.text(entry["max_abs_overlap"], entry["n_subsets"], label, ha="center", va="bottom", fontsize=8)
    ax.set_xticks(overlaps)
    ax.set_xticklabels([f"{_fmt(entry['max_abs_overlap'])}\nd = {entry['max_abs_dot']}" for entry in histogram],
                       fontsize=8)
    ax.set_xlabel("máximo |solapamiento| entre los pares del subconjunto (d / N)")
    ax.set_ylabel("subconjuntos")
    ax.set_ylim(0, max(counts) * 1.2)
    fig.suptitle(f"Máximo |solapamiento| de los {total} subconjuntos de {size} letras", fontsize=12, x=0.01,
                 ha="left")
    fig.tight_layout(rect=(0, 0.1, 1, 0.95))
    _caption(fig, f"Cada barra cuenta los subconjuntos de {size} letras cuyo par más parecido tiene ese |d|; d es "
                  f"impar para N = {n}. Las barras de color contienen el set separado y el correlacionado "
                  f"elegidos por la regla; el total es {total}.")
    plots_style.save_figure(fig, out_stem)


# ---------- cross terms ----------

def plot_cross_terms(orthogonality: dict, out_stem) -> None:
    from matplotlib.patches import Rectangle

    plt = plots_style.apply_style()
    n = int(orthogonality["n_pixels"])
    side = _side(n)
    p = len(orthogonality[SET_NAMES[0]]["letters"])
    limit = max(abs(v) for name in SET_NAMES for row in orthogonality[name]["margins"] for v in row)
    fig, axes = plt.subplots(len(SET_NAMES), p, figsize=(2.55 * p + 1.0, 2.7 * len(SET_NAMES) + 1.5))
    axes = np.atleast_2d(axes)
    image = None
    for r, name in enumerate(SET_NAMES):
        entry = orthogonality[name]
        for c in range(p):
            ax = axes[r, c]
            margin = np.asarray(entry["margins"][c], dtype=np.int64).reshape(side, side)
            image = ax.imshow(margin, cmap=plots_style.DIVERGING, vmin=-limit, vmax=limit, aspect="equal")
            for row in range(side):
                for col in range(side):
                    strong = abs(margin[row, col]) > 0.55 * limit
                    ax.text(col, row, str(int(margin[row, col])), ha="center", va="center", fontsize=6.5,
                            color="white" if strong else plots_style.TEXT_PRIMARY)
                    if margin[row, col] < 0:
                        ax.add_patch(Rectangle((col - 0.5, row - 0.5), 1, 1, fill=False,
                                               edgecolor=plots_style.TEXT_PRIMARY, linewidth=2.2))
            wrong = int(entry["wrong_pixels"][c])
            status = "punto fijo" if wrong == 0 else f"{wrong} {'píxel' if wrong == 1 else 'píxeles'} mal"
            ax.set_title(f"{entry['letters'][c]}: {status}", fontsize=9)
            _clean_glyph_axes(ax)
            if c == 0:
                ax.set_ylabel(f"Set {SET_LABELS[name]}", fontsize=10)
    fig.subplots_adjust(left=0.05, right=0.88, top=0.89, bottom=0.17, hspace=0.3)
    cax = fig.add_axes([0.91, 0.22, 0.015, 0.62])
    bar = fig.colorbar(image, cax=cax)
    bar.set_label("margen ξ_i h_i = (N − p) + término de cruce")
    fig.suptitle("Margen de estabilidad de cada píxel de cada letra", fontsize=12, x=0.01, ha="left")
    _caption(fig, f"Margen de cada píxel cuando la letra misma es la consulta: ξ_i h_i = (N − p) + término de cruce, "
                  f"con N − p = {n - p}. Los píxeles con margen negativo (recuadro negro) se invierten al primer "
                  "paso, de modo que esa letra no es un punto fijo. Escala simétrica compartida.")
    plots_style.save_figure(fig, out_stem)


# ---------- recall against noise ----------

def plot_recall_noise(recall_rows: list[dict], out_stem) -> None:
    plt = plots_style.apply_style()
    present = [v for v in VARIANTS if any(f"{r['set']}-{r['update']}" == v for r in recall_rows)]
    colors = plots_style.palette_for(list(VARIANTS))
    fig, axes = plt.subplots(1, 3, figsize=(14.0, 5.6), gridspec_kw={"width_ratios": [1.5, 1, 1]})
    left = axes[0]
    n_pixels = 25
    for variant in present:
        rows = sorted((r for r in recall_rows if f"{r['set']}-{r['update']}" == variant),
                      key=lambda r: int(r["flipped"]))
        k = np.array([int(r["flipped"]) for r in rows])
        rate = np.array([float(r["recall_rate"]) for r in rows])
        sd = np.array([float(r["recall_sd_seeds"]) for r in rows])
        style = "-" if variant.endswith("async") else "--"
        left.plot(k, rate, style, marker="o", markersize=4, color=colors[variant],
                  label=variant.replace("separated", "separado").replace("correlated", "correlacionado"))
        left.fill_between(k, np.clip(rate - sd, 0, 1), np.clip(rate + sd, 0, 1), color=colors[variant], alpha=0.15,
                          linewidth=0)
    left.set_ylim(0, 1.02)
    left.set_xlabel("píxeles invertidos k")
    left.set_ylabel("tasa de recuperación exacta")
    left.legend(fontsize=8, frameon=False, loc="lower left")
    top = left.secondary_xaxis("top", functions=(lambda k: k / n_pixels, lambda f: f * n_pixels))
    top.set_xlabel("fracción de ruido k / N")
    left.set_title("Recuperación de la letra propia", fontsize=10, loc="left")

    for ax, name in zip(axes[1:], SET_NAMES):
        label = f"{name}-async"
        rows = sorted((r for r in recall_rows if f"{r['set']}-{r['update']}" == label),
                      key=lambda r: int(r["flipped"]))
        if not rows:
            ax.axis("off")
            continue
        k = np.array([int(r["flipped"]) for r in rows])
        bottom = np.zeros(len(rows))
        for index, (column, text) in enumerate(FAILURE_CLASSES):
            share = np.array([float(r[column]) for r in rows])
            ax.bar(k, share, bottom=bottom, color=plots_style.palette_for(
                [c for c, _t in FAILURE_CLASSES])[column], label=text, width=0.8)
            bottom += share
        ax.set_ylim(0, 1.02)
        ax.set_xticks(range(0, int(k.max()) + 1, 2))
        ax.set_xlabel("píxeles invertidos k")
        ax.set_ylabel("proporción de ensayos")
        ax.set_title(f"Fallas, set {SET_LABELS[name]} asíncrono", fontsize=10, loc="left")
        if name == SET_NAMES[0]:
            ax.legend(fontsize=8, frameon=False, loc="upper left")
    cycle_max = max((float(r["cycle_rate"]) for r in recall_rows if r["update"] == "async"), default=0.0)
    trials = int(recall_rows[0]["n_trials"]) if recall_rows else 0
    fig.suptitle("Recuperación frente al ruido", fontsize=12, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.1, 1, 0.95))
    _caption(fig, "Éxito = match exacto de la letra de la propia consulta (la regla). Cada punto agrupa "
                  f"{trials} ensayos (30 por letra, 4 letras, 10 seeds); la banda es ± el desvío entre seeds. Los "
                  "paneles de la derecha reparten los fallos del modo asíncrono según el estado final (suman "
                  f"1 − tasa; ciclos en asíncrono: tasa máxima {_fmt(cycle_max, 3)}).")
    plots_style.save_figure(fig, out_stem)


# ---------- energy per update of the pre-registered traced trials ----------

def _recall_run_dir(results_dir: Path, label: str, seed: int) -> Path:
    runs = sorted((Path(results_dir) / "sweeps" / "recall" / "runs").glob(f"*_{label}_seed{seed}"))
    if len(runs) != 1:
        raise SystemExit(f"expected one recall run for {label} seed {seed} in {results_dir}, found {len(runs)}")
    return runs[0]


def energy_panels(results_dir) -> list[dict]:
    """One panel per (letter of the separated set, k in ENERGY_LEVELS_K present in the design): the first traced
    trial of seed ENERGY_SEED in the separated-async run, found by its index and never by its energies."""
    results_dir = Path(results_dir)
    design = _read_json(results_dir / "run.json")["design"]
    orth = _read_json(results_dir / "orthogonality.json")["separated"]
    letters = design["letters"]
    n_pixels = int(_read_json(results_dir / "orthogonality.json")["n_pixels"])
    levels = list(design["recall_levels"])
    per_level = int(design["recall_trials"])
    ks = [int(math.floor(level * n_pixels + 0.5)) for level in levels]
    run_dir = _recall_run_dir(results_dir, "separated-async", ENERGY_SEED)
    trials = {int(r["trial"]): r for r in _read_rows(run_dir / "trials.csv")}
    trace: dict[int, list[dict]] = {}
    for row in _read_rows(run_dir / "trace.csv"):
        trace.setdefault(int(row["trial"]), []).append(row)

    panels = []
    for position, row_index in enumerate(orth["indices"]):
        for k in ENERGY_LEVELS_K:
            if k not in ks:
                continue
            trial = (position * len(levels) + ks.index(k)) * per_level
            row = trials.get(trial)
            if row is None or trial not in trace:
                raise SystemExit(f"trial {trial} (letter {letters[row_index]}, k = {k}) is not traced in {run_dir.name}")
            if int(row["pattern"]) != position or int(float(row["flipped"])) != k:
                raise SystemExit(f"trial {trial} is not the first trial of letter {letters[row_index]} at k = {k}")
            steps = sorted(trace[trial], key=lambda r: int(r["step"]))
            sweeps = [int(r["sweep"]) for r in steps]
            sweep_ends = [i for i in range(1, len(steps)) if i == len(steps) - 1 or sweeps[i + 1] != sweeps[i]]
            klass = int(float(row["class"]))
            match = int(float(row["match_a"]))
            panels.append({
                "letter": letters[row_index], "k": k, "noise": float(row["noise"]), "trial": trial,
                "energies": [float(r["energy"]) for r in steps], "sweep_ends": sweep_ends,
                "class": hopfield_select.CLASS_NAMES[klass],
                "final_letter": letters[orth["indices"][match]] if klass == hopfield.CLASS_STORED else None,
                "correct": int(float(row["correct"])) == 1, "converged": int(float(row["converged"])) == 1,
                "stored_energy": float(orth["stored_energies"][position]),
                "e_start": float(row["e_start"]), "e_final": float(row["e_final"]),
                "updates": int(float(row["updates"])), "sweeps": int(float(row["sweeps"])),
                "hamming_final": int(float(row["hamming_final"])),
            })
    return panels


CLASS_TEXT = {"stored": "almacenada", "inverse": "inverso", "mixture": "mezcla", "other": "otro"}


def plot_energy(panels: list[dict], out_stem) -> None:
    plt = plots_style.apply_style()
    letters = list(dict.fromkeys(p["letter"] for p in panels))
    ks = sorted({p["k"] for p in panels})
    by_key = {(p["letter"], p["k"]): p for p in panels}
    fig, axes = plt.subplots(len(letters), len(ks), figsize=(4.2 * len(ks), 2.5 * len(letters) + 1.3),
                             squeeze=False, sharex=False)
    colors = _colors()
    for r, letter in enumerate(letters):
        for c, k in enumerate(ks):
            ax = axes[r, c]
            panel = by_key.get((letter, k))
            if panel is None:
                ax.axis("off")
                continue
            x = np.arange(len(panel["energies"]))
            ax.step(x, panel["energies"], where="post", color=colors["separated"], linewidth=1.6)
            ax.axhline(panel["stored_energy"], color=plots_style.TEXT_SECONDARY, linewidth=1.0, linestyle=":")
            for end in panel["sweep_ends"]:
                ax.axvline(end, color=plots_style.GRID, linewidth=1.0, linestyle="--", zorder=0)
            verdict = "correcta" if panel["correct"] else "incorrecta"
            klass = CLASS_TEXT[panel["class"]]
            if panel["final_letter"] is not None:
                klass += f" {panel['final_letter']}"
            ax.set_title(f"{letter}, k = {k}: {klass}, {verdict}", fontsize=9, loc="left")
            if c == 0:
                ax.set_ylabel("energía")
            if r == len(letters) - 1:
                ax.set_xlabel("actualización")
    fig.suptitle("Energía por actualización asíncrona (set separado, primer ensayo trazado de la seed "
                 f"{ENERGY_SEED})", fontsize=12, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    _caption(fig, f"Un ensayo por panel, fijado por índice antes de la corrida (el primero trazado de cada letra y "
                  f"nivel, seed {ENERGY_SEED}), no elegido por su forma. Línea punteada: energía de la letra "
                  "almacenada; guiones verticales: fin de cada barrido. La energía asíncrona nunca sube "
                  "(energy_increases = 0), pero bajar no es recuperar: el título dice qué estado quedó.")
    plots_style.save_figure(fig, out_stem)


# ---------- capacity over all subsets of four letters ----------

def _bucket(value: float) -> float:
    return round(float(value), 2)


def plot_capacity_p4(rows: list[dict], selection: dict, out_stem) -> None:
    """Left: share of subsets by number of stable letters per max |overlap| bucket. Right: mean recall rate per
    bucket (10th to 90th percentile band) and against mean |overlap| rounded to MEAN_OVERLAP_STEP (dashed)."""
    plt = plots_style.apply_style()
    colors = _colors()
    p = len([k for k in rows[0] if k.startswith("idx_")])
    max_ov = np.array([float(r["max_abs_overlap"]) for r in rows])
    mean_ov = np.array([float(r["mean_abs_overlap"]) for r in rows])
    n_stable = np.array([int(r["n_stable"]) for r in rows])
    recall = np.array([float(r["recall_rate_mean"]) for r in rows])
    buckets = sorted({_bucket(v) for v in max_ov})
    keys = np.array([_bucket(v) for v in max_ov])
    cmap = plt.get_cmap("Blues")
    stack_colors = [cmap(0.15 + 0.8 * i / max(p, 1)) for i in range(p + 1)]
    letters_of = {r["letters"]: r for r in rows}
    fig, axes = plt.subplots(1, 2, figsize=(14.0, 6.0))

    left = axes[0]
    x = np.arange(len(buckets))
    bottom = np.zeros(len(buckets))
    counts = np.array([(keys == b).sum() for b in buckets])
    for count in range(p + 1):
        share = np.array([((keys == b) & (n_stable == count)).sum() / max((keys == b).sum(), 1) for b in buckets])
        left.bar(x, share, bottom=bottom, color=stack_colors[count], label=f"{count} estables", width=0.8,
                 edgecolor="white", linewidth=0.4)
        bottom += share
    for position, total in zip(x, counts):
        left.text(position, 1.01, str(int(total)), ha="center", va="bottom", fontsize=7, rotation=90)
    marks = []
    for name in SET_NAMES:
        entry = selection.get(name)
        row = letters_of.get(entry["letters"]) if entry else None
        if row is not None:
            marks.append((name, row))
    for name, row in marks:
        position = buckets.index(_bucket(row["max_abs_overlap"]))
        left.plot([position], [0.035], marker="^", color=colors[name], markersize=10, markeredgecolor="white",
                  linestyle="none", label=f"set {SET_LABELS[name]} {row['letters']}")
    left.set_xticks(x)
    left.set_xticklabels([_fmt(b) for b in buckets], fontsize=7, rotation=90)
    left.set_ylim(0, 1.0)
    left.set_xlabel("máximo |solapamiento| del subconjunto (d / N); arriba, cantidad de subconjuntos")
    left.set_ylabel("proporción de subconjuntos")
    left.legend(fontsize=7, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=4)
    left.set_title("Letras estables por subconjunto (determinista)", fontsize=10, loc="left", pad=28)

    right = axes[1]
    mean_rate = np.array([recall[keys == b].mean() for b in buckets])
    low = np.array([np.percentile(recall[keys == b], 10) for b in buckets])
    high = np.array([np.percentile(recall[keys == b], 90) for b in buckets])
    right.fill_between(buckets, low, high, color=NEUTRAL_BAR, alpha=0.5, linewidth=0,
                       label="percentiles 10 a 90 (máx |solap.|)")
    right.plot(buckets, mean_rate, "-", marker="o", markersize=3.5, color=plots_style.TEXT_PRIMARY,
               label="media por máx |solapamiento|")
    mean_keys = np.round(mean_ov / MEAN_OVERLAP_STEP) * MEAN_OVERLAP_STEP
    mean_buckets = sorted({round(float(v), 4) for v in mean_keys})
    right.plot(mean_buckets, [recall[np.isclose(mean_keys, b)].mean() for b in mean_buckets], "--", marker="s",
               markersize=3.5, color=plots_style.TEXT_SECONDARY, label="media por |solapamiento| medio (paso 0,04)")
    for name, row in marks:
        right.plot([float(row["max_abs_overlap"])], [float(row["recall_rate_mean"])], marker="^", markersize=10,
                   linestyle="none", color=colors[name], label=f"set {SET_LABELS[name]} {row['letters']}")
    right.set_ylim(0, 1.02)
    right.set_xlabel("|solapamiento| (d / N)")
    right.set_ylabel("tasa de recuperación con ruido 0,12")
    right.legend(fontsize=7, frameon=False, loc="upper right")
    right.set_title("Recuperación con k = 3 píxeles invertidos", fontsize=10, loc="left", pad=28)
    fig.suptitle(f"Capacidad con p = {p}: los {len(rows)} subconjuntos de {p} letras", fontsize=12, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.1, 1, 0.95))
    _caption(fig, f"{len(rows)} subconjuntos; la estabilidad (punto fijo) es determinista, la recuperación a ruido 0,12 "
                  "(k = 3) es la media de 10 seeds. Los triángulos marcan el set separado y el correlacionado de la regla.")
    plots_style.save_figure(fig, out_stem)


# ---------- capacity against p ----------

def plot_capacity_by_p(rows: list[dict], capacity: dict, out_stem) -> None:
    plt = plots_style.apply_style()
    rows = sorted(rows, key=lambda r: int(r["p"]))
    p_values = np.array([int(r["p"]) for r in rows])
    extension = np.array([int(r["extension"]) == 1 for r in rows])
    exhaustive = np.array([int(r["exhaustive"]) == 1 for r in rows])
    n = int(capacity.get("n_pixels", 25))
    series = (("mean_stable_fraction", "sd_stable_fraction", "fracción estable media", plots_style.palette_for(
        ["a", "b"])["a"], "o"),
              ("mean_recall_rate", "sd_recall_rate", "tasa de recuperación media (ruido 0,12)",
               plots_style.palette_for(["a", "b"])["b"], "s"))
    fig, ax = plt.subplots(figsize=(12.0, 6.2))
    for mean_key, sd_key, label, color, marker in series:
        mean = np.array([float(r[mean_key]) for r in rows])
        sd = np.array([float(r[sd_key]) for r in rows])
        ax.fill_between(p_values, np.clip(mean - sd, 0, 1), np.clip(mean + sd, 0, 1), color=color, alpha=0.18,
                        linewidth=0)
        ax.plot(p_values, mean, "-", color=color, linewidth=1.2, label=label)
        for flag_ext in (False, True):
            for flag_exh in (False, True):
                mask = (extension == flag_ext) & (exhaustive == flag_exh)
                if not mask.any():
                    continue
                ax.plot(p_values[mask], mean[mask], linestyle="none", marker="D" if flag_ext else marker,
                        markersize=6, markerfacecolor="white" if flag_exh else color, markeredgecolor=color,
                        markeredgewidth=1.4)
    if extension.any():
        first = int(p_values[extension].min())
        ax.axvline(first - 0.5, color=plots_style.TEXT_SECONDARY, linewidth=1.0, linestyle=":")
        ax.text(first - 0.4, 0.96, "extensión por la regla\n(rombos)", fontsize=8, va="top",
                color=plots_style.TEXT_SECONDARY)
    near_zero = capacity.get("p_extension", {}).get("near_zero")
    if near_zero is not None:
        ax.axhline(float(near_zero), color=plots_style.TEXT_SECONDARY, linewidth=1.0, linestyle="--")
        ax.text(float(p_values.min()) + 3.0, float(near_zero) - 0.012, f"\"~0\" de la regla = {_fmt(float(near_zero))}",
                fontsize=8, ha="left", va="top", color=plots_style.TEXT_SECONDARY)
    orders = capacity.get("orders_of_magnitude", {})
    references = (("0.138N", "0,138N ≈ {v} (orden de magnitud, patrones al azar)", "-."),
                  ("0.15N", "0,15N = {v} (curso, orden de magnitud)", (0, (1, 1))))
    reference_handles = []
    for key, text, style in references:
        if key in orders:
            value = float(orders[key])
            reference_handles.append(ax.axvline(value, color=plots_style.TEXT_PRIMARY, linewidth=1.0, linestyle=style,
                                                alpha=0.8, label=text.format(v=_fmt(value))))
    ax.set_xlim(p_values.min() - 0.5, p_values.max() + 0.5)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("cantidad de letras almacenadas p")
    ax.set_ylabel("media entre las 10 seeds (banda: ± desvío)")
    ax.legend(fontsize=8, frameon=False, loc="upper right", bbox_to_anchor=(1.0, 0.9))
    fig.suptitle(f"Capacidad frente a p (N = {n})", fontsize=12, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.1, 1, 0.95))
    _caption(fig, "Por p, 200 subconjuntos al azar de letras por seed (todos los posibles cuando son menos; marcador "
                  "hueco = exhaustivo). Las letras son patrones correlacionados; las referencias 0,138N y 0,15N valen "
                  "para patrones al azar con N grande, se marcan solo como órdenes de magnitud y no son un umbral.")
    plots_style.save_figure(fig, out_stem)


# ---------- the pre-registered spurious state ----------

def plot_spurious(spurious: dict, out_stem) -> None:
    """One row per pre-registered pick (inverse, mixture, other, those present): query glyph, final glyph, overlap
    bars with the stored letters, and the energy per step against the stored energies."""
    from matplotlib.colors import ListedColormap

    plt = plots_style.apply_style()
    picks = [(name, spurious["picks"][name]) for name in SPURIOUS_ORDER if name in spurious.get("picks", {})]
    stored = list(spurious.get("stored_letters", []))
    stored_energies = list(spurious.get("stored_energies", []))
    seeds = [str(s) for s in spurious.get("seeds_tried", [])]
    counts = spurious.get("counts_by_seed", {})
    cmap = ListedColormap([GLYPH_OFF, GLYPH_ON])
    colors = _colors()
    n_rows = max(len(picks), 1)
    fig, axes = plt.subplots(n_rows, 4, figsize=(15.0, 3.3 * n_rows + 1.8), squeeze=False,
                             gridspec_kw={"width_ratios": [0.8, 0.8, 1.2, 1.6]})
    count_text = "; ".join(
        f"seed {seed}: " + ", ".join(f"{CLASS_TEXT[c]} {counts[seed].get(c, 0)}" for c in ("stored", "inverse",
                                                                                              "mixture", "other"))
        for seed in seeds if seed in counts)
    if not picks:
        for ax in axes[0]:
            ax.axis("off")
        axes[0, 0].text(0.0, 0.5, "Ningún ensayo convergido terminó en inverso, mezcla u otro en las seeds de la regla.",
                        fontsize=11, transform=axes[0, 0].transAxes)
    for row, (name, pick) in enumerate(picks):
        side = _side(len(pick["query"]))
        ax_q, ax_f, ax_o, ax_e = axes[row]
        ax_q.imshow(np.asarray(pick["query"]).reshape(side, side), cmap=cmap, vmin=-1, vmax=1,
                    interpolation="nearest")
        ax_q.set_title(f"consulta {pick['letter']}, seed {pick['seed']}, ensayo {pick['trial']}\n"
                       f"{pick['flipped']} píxeles invertidos", fontsize=9, loc="left")
        _clean_glyph_axes(ax_q)
        ax_f.imshow(np.asarray(pick["final"]).reshape(side, side), cmap=cmap, vmin=-1, vmax=1,
                    interpolation="nearest")
        detail = SPURIOUS_TEXT[name]
        if pick["match_letters"]:
            detail += ": " + " ".join(("+" if sign > 0 else "−") + letter
                                       for sign, letter in zip(pick["signs"], pick["match_letters"]))
        fixed = "punto fijo" if pick.get("is_fixed") else "no es punto fijo"
        ax_f.set_title(f"estado final: {detail}\n{fixed}", fontsize=9, loc="left")
        _clean_glyph_axes(ax_f)
        overlaps = np.asarray(pick["overlaps"], dtype=np.float64)
        ax_o.bar(range(len(overlaps)), overlaps, color=colors["separated"], width=0.6)
        ax_o.axhline(0, color=plots_style.TEXT_SECONDARY, linewidth=0.8)
        ax_o.set_ylim(-1.05, 1.05)
        ax_o.set_xticks(range(len(overlaps)))
        ax_o.set_xticklabels(stored[:len(overlaps)] or [str(i) for i in range(len(overlaps))])
        ax_o.set_ylabel("solapamiento m")
        ax_o.set_title("solapamiento con las letras almacenadas", fontsize=9, loc="left")
        trace = np.asarray(pick["energy_trace"], dtype=np.float64)
        ax_e.step(np.arange(len(trace)), trace, where="post", color=colors["separated"], linewidth=1.6)
        for letter, energy in zip(stored, stored_energies):
            ax_e.axhline(float(energy), color=plots_style.TEXT_SECONDARY, linewidth=1.0, linestyle=":")
        if stored_energies:
            ax_e.text(len(trace) - 1, float(stored_energies[0]) + 4,
                      "letras almacenadas: " + ", ".join(f"{l} {_fmt(float(e), 0)}" for l, e in zip(stored,
                                                                                                     stored_energies)),
                      fontsize=7, ha="right", va="bottom", color=plots_style.TEXT_SECONDARY)
        ax_e.axhline(float(pick["e_final"]), color=plots_style.TEXT_PRIMARY, linewidth=1.0, linestyle="--")
        ax_e.set_xlabel("actualización")
        ax_e.set_ylabel("energía")
        ax_e.set_title(f"energía: inicial {_fmt(float(pick['e_start']), 0)}, final {_fmt(float(pick['e_final']), 0)} "
                       "(guiones)", fontsize=9, loc="left")
    title = "Estado espurio elegido por la regla (primer ensayo convergido de cada clase)"
    if not spurious.get("found_target", False):
        title = "Estado espurio: sin mezcla ni otro convergido en las seeds de la regla"
    fig.suptitle(title, fontsize=12, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.1, 1, 0.95))
    _caption(fig, "Clases de los ensayos convergidos por seed probada (" + (count_text or "sin datos") + "). Ningún "
                  "ejemplo se eligió a mano: es el primero en el orden del archivo de cada clase. La energía final "
                  "se lee frente a las energías medidas de las letras almacenadas, sin una regla general.")
    plots_style.save_figure(fig, out_stem)


# ---------- driver ----------

def require_same_code(run: dict, repo_dir=TP_DIR) -> None:
    """Refuse unless the network code is the one run.json recorded (WR-02). A run.json without code_identity
    counts as every file changed."""
    changed = hopfield_letters.changed_code_files(run.get("code_identity"), repo_dir)
    if changed:
        raise SystemExit(f"the results come from different network code: {', '.join(changed)} differ from the "
                         "sha256 recorded in run.json (code_identity); re-run make hopfield-letters (WR-02)")


def draw(results_dir, out_dir, patterns_path=None, check_rule: bool = True, check_code: bool = True,
         repo_dir=TP_DIR) -> list[Path]:
    results_dir = Path(results_dir)
    out_dir = Path(out_dir)
    selection_path = results_dir / "selection.json"
    if not selection_path.exists():
        raise SystemExit(f"{selection_path}: not found, run make hopfield-letters first")
    if check_rule:
        hopfield_select.require_same_rule(selection_path)
    selection = _read_json(selection_path)
    orthogonality = _read_json(results_dir / "orthogonality.json")
    run = _read_json(results_dir / "run.json")
    if check_code:
        require_same_code(run, repo_dir)
    design = run["design"]
    if patterns_path is None:
        patterns_path = TP_DIR / design["patterns_path"]
    patterns = hopfield.load_patterns(patterns_path)
    sets = {name: selection[name]["indices"] for name in SET_NAMES}
    recall_rows = _read_rows(results_dir / "recall.csv")

    out_dir.mkdir(parents=True, exist_ok=True)
    plot_letters(patterns, design["letters"], sets, out_dir / "letters")
    plot_overlaps(orthogonality, out_dir / "overlaps")
    plot_max_overlap_hist(selection, out_dir / "max_overlap_hist")
    plot_cross_terms(orthogonality, out_dir / "cross_terms")
    plot_recall_noise(recall_rows, out_dir / "recall_noise")
    plot_energy(energy_panels(results_dir), out_dir / "energy")
    plot_capacity_p4(_read_rows(results_dir / "capacity_p4.csv"), selection, out_dir / "capacity_p4")
    plot_capacity_by_p(_read_rows(results_dir / "capacity_by_p.csv"), _read_json(results_dir / "capacity.json"),
                       out_dir / "capacity_by_p")
    plot_spurious(_read_json(results_dir / "spurious.json"), out_dir / "spurious")
    return [out_dir / f"{stem}.{suffix}" for stem in FIGURE_STEMS for suffix in ("svg", "png")]


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(TP_DIR).as_posix()
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS, help="directory of make hopfield-letters")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="directory of the figures")
    args = parser.parse_args(argv)
    if not (args.results / "selection.json").exists():
        raise SystemExit(f"{args.results / 'selection.json'}: not found, run make hopfield-letters first")
    for path in draw(args.results, args.out):
        print(_display(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
