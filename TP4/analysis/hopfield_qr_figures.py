#!/usr/bin/env python3
"""Figures of the pre-registered Hebb-on-QR tracer run (HOP-04, HOP-05): glyphs, overlaps, the Hebb recovery
curve and the per-step energy trace.

    .venv/bin/python analysis/hopfield_qr_figures.py [--results DIR] [--out DIR]

Reads the files `make hopfield-qr` wrote (overlaps.json, qr_facts.json, recall.csv, energy_trace.csv, run.json)
and refuses to draw (SystemExit) if `hopfield_qr_select.require_same_rule` rejects run.json - the protocol text,
the guard code, scripts/qr.py or one of the five PNGs changed since the run - or if the network code (the C core,
the driver, the config reader and the numpy control) differs from the sha256 run.json recorded as code_identity:
that identity is not pinned by the pre-registration guard, but the figures must come from the code that produced
the results (mirrors Phase 4's WR-02). Every figure goes through plots_style.save_figure, so a rerun gives
byte-identical SVG files. numpy and matplotlib (through plots_style) only.
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
import hopfield_qr_select  # noqa: E402
import plots_style  # noqa: E402
import qr  # noqa: E402

DEFAULT_RESULTS = TP_DIR / "analysis" / "results" / "hopfield" / "qr"
DEFAULT_OUT = DEFAULT_RESULTS / "figures"
UPDATES = ("async", "sync")
UPDATE_LABELS = {"async": "asincrono (referencia)", "sync": "sincrono"}
# Representative noise levels for the per-step energy panel, fixed by index before looking at any curve: the
# start, the middle and the top of the frozen 0..0.5 grid (D-05), not chosen for how their curves turned out.
ENERGY_LEVELS = (0.0, 0.25, 0.5)
FIGURE_STEMS = ("qr", "overlaps", "recall_noise", "energy_trace")
NEUTRAL_BAR = "#b9b8b3"
GLYPH_ON = "#1f1f1f"
GLYPH_OFF = "#ecebe6"


# ---------- small helpers ----------

def _caption(fig, text: str, width: int = 125, y: float = 0.01) -> None:
    import textwrap

    fig.text(0.01, y, textwrap.fill(text, width), ha="left", va="bottom", fontsize=8,
             color=plots_style.TEXT_SECONDARY)


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
    fig, axes = plt.subplots(1, p, figsize=(2.6 * p + 0.6, 3.2))
    for index, ax in enumerate(axes):
        ax.imshow(patterns[index].reshape(side, side), cmap=cmap, vmin=-1, vmax=1, interpolation="nearest")
        ax.set_title(labels[index], fontsize=10)
        _clean_glyph_axes(ax)
    fig.suptitle("Los 5 QR almacenados (37x37, pixel oscuro = +1)", fontsize=12, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.08, 1, 0.92))
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
    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    image = ax.imshow(matrix, cmap=plots_style.DIVERGING, vmin=-1, vmax=1, aspect="equal")
    for row in range(p):
        for col in range(p):
            strong = abs(matrix[row, col]) > 0.6
            ax.text(col, row, f"{int(dots[row, col])}\n{_fmt(matrix[row, col])}", ha="center", va="center",
                    fontsize=10, color="white" if strong else plots_style.TEXT_PRIMARY)
    ax.set_xticks(range(p))
    ax.set_yticks(range(p))
    ax.set_xticklabels(labels, fontsize=10, rotation=20, ha="right")
    ax.set_yticklabels(labels, fontsize=10)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    bar = fig.colorbar(image, ax=ax, fraction=0.045, pad=0.03)
    bar.set_label("solapamiento d / N")
    fig.suptitle("Solapamientos entre los 5 QR almacenados", fontsize=12, x=0.01, ha="left")
    fig.subplots_adjust(left=0.18, right=0.86, top=0.88, bottom=0.2)
    _caption(fig, f"En cada celda, el producto escalar entero d y el solapamiento d / {n}. max|solapamiento| = "
                  f"{_fmt(overlaps['max_abs_overlap'])}, media = {_fmt(overlaps['mean_abs_overlap'])}: los 5 QR "
                  "estan lejos de ser ortogonales entre si, la causa raiz del fallo de Hebb (HOP-04, D-11a).")
    plots_style.save_figure(fig, out_stem)


# ---------- the Hebb recovery curve, continuous overlap, sweeps and energy (HOP-05, D-03, D-09) ----------

def plot_recall_noise(rows: list[dict], out_stem) -> None:
    plt = plots_style.apply_style()
    colors = plots_style.palette_for(list(UPDATES))
    fig, axes = plt.subplots(1, 3, figsize=(16.5, 5.4))
    recall_ax, overlap_ax, cost_ax = axes
    energy_ax = cost_ax.twinx()
    for update in UPDATES:
        mine = sorted((r for r in rows if r["update"] == update), key=lambda r: float(r["noise"]))
        if not mine:
            continue
        noise = np.array([float(r["noise"]) for r in mine])
        rate = np.array([float(r["recall_rate"]) for r in mine])
        sd = np.array([float(r["recall_sd_seeds"]) for r in mine])
        overlap = np.array([float(r["mean_final_overlap"]) for r in mine])
        sweeps = np.array([float(r["mean_sweeps"]) for r in mine])
        energy = np.array([float(r["mean_final_energy"]) for r in mine])
        style = "-" if update == "async" else "--"
        label = UPDATE_LABELS[update]
        recall_ax.plot(noise, rate, style, marker="o", markersize=4, color=colors[update], label=label)
        recall_ax.fill_between(noise, np.clip(rate - sd, 0, 1), np.clip(rate + sd, 0, 1), color=colors[update],
                               alpha=0.15, linewidth=0)
        overlap_ax.plot(noise, overlap, style, marker="o", markersize=4, color=colors[update], label=label)
        cost_ax.plot(noise, sweeps, style, marker="s", markersize=4, color=colors[update],
                    label=f"{label}: barridos")
        energy_ax.plot(noise, energy, style, marker="^", markersize=4, color=colors[update], alpha=0.55,
                       label=f"{label}: energia")
    recall_ax.set_ylim(0, 1.02)
    recall_ax.set_xlabel("nivel de ruido (fraccion de pixeles invertidos)")
    recall_ax.set_ylabel("tasa de recuperacion exacta")
    recall_ax.legend(fontsize=8, frameon=False, loc="upper right")
    recall_ax.set_title("Exito exacto (D-03)", fontsize=10, loc="left")

    overlap_ax.set_ylim(0, 1.02)
    overlap_ax.set_xlabel("nivel de ruido")
    overlap_ax.set_ylabel("|solapamiento final| medio con el objetivo")
    overlap_ax.set_title("Cercania continua (|m|, D-03)", fontsize=10, loc="left")

    cost_ax.set_xlabel("nivel de ruido")
    cost_ax.set_ylabel("barridos medios (marcador cuadrado)")
    energy_ax.set_ylabel("energia final media (marcador triangulo)")
    handles = cost_ax.get_legend_handles_labels()[0] + energy_ax.get_legend_handles_labels()[0]
    labels_all = cost_ax.get_legend_handles_labels()[1] + energy_ax.get_legend_handles_labels()[1]
    cost_ax.legend(handles, labels_all, fontsize=7, frameon=False, loc="center left")
    cost_ax.set_title("Costo dinamico: barridos y energia final (D-09)", fontsize=10, loc="left")

    trials = int(rows[0]["n_trials"]) if rows else 0
    fig.suptitle("Hebb sobre los 5 QR: recuperacion frente al ruido", fontsize=12, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.1, 1, 0.94))
    _caption(fig, f"Cada punto agrupa {trials} ensayos (5 QR, 30 ensayos, 10 seeds); la banda del panel izquierdo "
                  "es +- el desvio entre seeds. Exito exacto nunca despega de 0 incluso a ruido 0 (D-02): el "
                  "veredicto de verdict.json se deriva de esta misma curva, no al reves.")
    plots_style.save_figure(fig, out_stem)


# ---------- per-step energy trace (HOP-05 "energia por paso") ----------

def plot_energy_trace(rows: list[dict], out_stem) -> None:
    """Rows: the five QR; columns: ENERGY_LEVELS, fixed by index before looking at any curve."""
    plt = plots_style.apply_style()
    labels = _qr_labels()
    sources = sorted({int(r["source"]) for r in rows})
    levels = [level for level in ENERGY_LEVELS if any(abs(float(r["noise"]) - level) < 1e-9 for r in rows)]
    by_key: dict[tuple, list] = {}
    for r in rows:
        key = (int(r["source"]), round(float(r["noise"]), 2))
        by_key.setdefault(key, []).append((int(r["step"]), float(r["energy"])))
    fig, axes = plt.subplots(len(sources), len(levels), figsize=(4.0 * len(levels), 2.3 * len(sources) + 1.3),
                             squeeze=False, sharex=False)
    color = plots_style.palette_for(["qr"])["qr"]
    for r, source in enumerate(sources):
        for c, level in enumerate(levels):
            ax = axes[r, c]
            series = sorted(by_key.get((source, round(level, 2)), []))
            if not series:
                ax.axis("off")
                continue
            steps = [s for s, _e in series]
            energies = [e for _s, e in series]
            ax.step(steps, energies, where="post", color=color, linewidth=1.6)
            ax.set_title(f"{labels[source]}, ruido {_fmt(level)}", fontsize=9, loc="left")
            if c == 0:
                ax.set_ylabel("energia")
            if r == len(sources) - 1:
                ax.set_xlabel("paso (actualizacion asincrona)")
    fig.suptitle("Energia por paso, Hebb asincrono (un ensayo trazado por celda, seed fija)", fontsize=12, x=0.01,
                ha="left")
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    _caption(fig, "Un ensayo por panel (el primero trazado de cada QR y nivel de ruido de la seed fija de "
                  "energy_trace.csv), no elegido por su forma. La energia asincrona nunca sube "
                  "(HOP-05 'energia por paso'), a diferencia de la energia final por nivel que recall.csv "
                  "promedia sobre todos los ensayos.")
    plots_style.save_figure(fig, out_stem)


# ---------- driver ----------

def require_same_code(run: dict, repo_dir=TP_DIR) -> None:
    """Refuse unless the network code is the one run.json recorded (mirrors Phase 4's WR-02). A run.json without
    code_identity counts as every file changed."""
    changed = hopfield_qr.changed_code_files(run.get("code_identity"), repo_dir)
    if changed:
        raise SystemExit(f"the results come from different network code: {', '.join(changed)} differ from the "
                         "sha256 recorded in run.json (code_identity); re-run make hopfield-qr")


def draw(results_dir, out_dir, patterns_path=None, check_rule: bool = True, check_code: bool = True,
         repo_dir=TP_DIR) -> list[Path]:
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

    overlaps = _read_json(results_dir / "overlaps.json")
    if patterns_path is None:
        patterns_path = TP_DIR / run["design"]["patterns_path"]
    patterns = hopfield.load_patterns(patterns_path)
    recall_rows = _read_rows(results_dir / "recall.csv")
    energy_rows = _read_rows(results_dir / "energy_trace.csv")

    out_dir.mkdir(parents=True, exist_ok=True)
    plot_qr(patterns, out_dir / "qr")
    plot_overlaps(overlaps, out_dir / "overlaps")
    plot_recall_noise(recall_rows, out_dir / "recall_noise")
    plot_energy_trace(energy_rows, out_dir / "energy_trace")
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
    args = parser.parse_args(argv)
    if not (args.results / "run.json").exists():
        raise SystemExit(f"{args.results / 'run.json'}: not found, run make hopfield-qr first")
    for path in draw(args.results, args.out):
        print(_display(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
