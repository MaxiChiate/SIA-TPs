#!/usr/bin/env python3
"""Figures of the Hopfield-on-QR comparison (HOP-04, HOP-05, HOP-06): glyphs, overlaps, the three-rule
recovery/overlap/cost comparison (hebb, pinv, hamming) and the per-step energy trace for the two
dynamical rules (hebb, pinv).

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
# The three rules compared on the recovery figure, and the two with dynamics (the per-step energy panel and the
# cost/iterations panel are hebb-vs-pinv only: the Hamming baseline has no sweeps or energy, D-09).
RULES = ("hebb", "pinv", "hamming")
DYNAMICAL_RULES = ("hebb", "pinv")
RULE_LABELS = {"hebb": "Hebb", "pinv": "pseudo-inversa", "hamming": "Hamming 1-NN (lookup)"}
# Representative noise levels for the per-step energy panel, fixed by index before looking at any curve: the
# start, the middle and the top of the frozen 0..0.5 grid (D-05), not chosen for how their curves turned out.
ENERGY_LEVELS = (0.0, 0.25, 0.5)
FIGURE_STEMS = ("qr", "overlaps", "recovery", "energy_trace")
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


# ---------- the three-rule recovery curve, continuous overlap, sweeps and energy (HOP-06, D-03, D-09) ----------

def plot_recovery(rows: list[dict], out_stem) -> None:
    """Three panels: exact recovery (hebb, pinv, hamming - async as the reference line, sync a labelled
    companion for the two dynamical rules, hamming a single no-update line) with +-seed-SD bands; the continuous
    mean |final overlap| for the same three; and the dynamical cost (sweeps, final energy) for hebb vs pinv only
    (the Hamming lookup has no dynamics, annotated as instantaneous, D-09). Colour is by rule (stable across
    panels), linestyle by update (solid async, dashed sync)."""
    plt = plots_style.apply_style()
    colors = plots_style.palette_for(list(RULES))
    fig, axes = plt.subplots(1, 3, figsize=(16.5, 5.4))
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

    recall_ax.set_ylim(0, 1.18)
    recall_ax.set_xlabel("nivel de ruido (fraccion de pixeles invertidos)")
    recall_ax.set_ylabel("tasa de recuperacion exacta")
    recall_ax.legend(fontsize=6.5, frameon=False, ncol=1, loc="upper left", bbox_to_anchor=(0.0, 1.02))
    recall_ax.set_title("Exito exacto, 3 reglas (D-03, D-08)", fontsize=10, loc="left")

    pinv_zero = next((r for r in rows if r["rule"] == "pinv" and r["update"] == "async"
                      and abs(float(r["noise"])) < 1e-9), None)
    if pinv_zero is not None:
        rate0 = float(pinv_zero["recall_rate"])
        recall_ax.annotate(
            f"pinv a ruido 0: {_fmt(rate0 * 100, 0)}% exacto\n({'los 5 QR son' if rate0 == 1.0 else 'no todos los QR son'} "
            "puntos fijos)",
            xy=(0.98, 0.04), xycoords="axes fraction", ha="right", va="bottom", fontsize=7.5,
            color=plots_style.TEXT_SECONDARY, style="italic")

    overlap_ax.set_ylim(0, 1.02)
    overlap_ax.set_xlabel("nivel de ruido")
    overlap_ax.set_ylabel("|solapamiento final| medio con el objetivo")
    overlap_ax.legend(fontsize=6.5, frameon=False, loc="lower left")
    overlap_ax.set_title("Cercania continua, 3 reglas (|m|, D-03)", fontsize=10, loc="left")

    cost_ax.set_xlabel("nivel de ruido")
    cost_ax.set_ylabel("barridos medios (marcador cuadrado)")
    energy_ax.set_ylabel("energia final media (marcador triangulo)")
    handles = cost_ax.get_legend_handles_labels()[0] + energy_ax.get_legend_handles_labels()[0]
    labels_all = cost_ax.get_legend_handles_labels()[1] + energy_ax.get_legend_handles_labels()[1]
    cost_ax.legend(handles, labels_all, fontsize=6, frameon=False, loc="lower right", bbox_to_anchor=(0.72, 0.0))
    cost_ax.set_title("Costo dinamico: hebb vs pinv (D-09)", fontsize=10, loc="left")
    cost_ax.annotate("Hamming: lookup\ninstantaneo, sin\nbarridos ni energia", xy=(0.99, 0.5),
                     xycoords="axes fraction", ha="right", va="center", fontsize=7,
                     color=plots_style.TEXT_SECONDARY, style="italic")

    trials = int(rows[0]["n_trials"]) if rows else 0
    fig.suptitle("Hebb, pseudo-inversa y Hamming sobre los 5 QR: recuperacion frente al ruido", fontsize=12,
                x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.1, 1, 0.94))
    _caption(fig, f"Cada punto agrupa {trials} ensayos (5 QR, 30 ensayos, 10 seeds); la banda es +- el desvio "
                  "entre seeds. hebb y pinv comparten la MISMA grilla de ruido (D-05); el lookup de Hamming la "
                  "reproduce con el mismo k y las mismas etiquetas de seed pero sorteos propios, independientes "
                  "del core en C (comparacion sobre la misma distribucion, no sobre sorteos identicos). El "
                  "veredicto de verdict.json se deriva de esta misma curva, no al reves (D-02).")
    plots_style.save_figure(fig, out_stem)


# ---------- per-step energy trace, hebb and pinv (HOP-05 "energia por paso") ----------

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
    fig.suptitle("Energia por paso, asincrono (hebb vs pinv, un ensayo trazado por celda, seed fija)", fontsize=12,
                x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.07, 1, 0.93))
    _caption(fig, "Un ensayo por panel (el primero trazado de cada QR y nivel de ruido de la seed fija de "
                  "energy_trace.csv) para hebb y para pinv, no elegido por su forma. Cada panel tiene un eje "
                  "propio por regla (la energia de pinv es mucho menor en magnitud que la de hebb, que suma sobre "
                  "N=1369). La energia asincrona nunca sube para ninguna de las dos reglas (HOP-05 'energia por "
                  "paso'), a diferencia de la energia final por nivel que recall.csv promedia sobre todos los "
                  "ensayos.")
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
    plot_recovery(recall_rows, out_dir / "recovery")
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
