#!/usr/bin/env python3
"""Figures of the post-hoc masked experiment (KD-9): the mask and the stored triple, and Hebb's recovery.

    .venv/bin/python analysis/hopfield_qr_masked_figures.py [--results DIR] [--out DIR]

Reads what `make hopfield-qr-masked` wrote (selection.json, ablation.json, recall.csv, run.json) and refuses to
draw if the protocol (hopfield_qr_select.require_same_rule) or the experiment's code (MASKED_CODE_FILES) changed
since the run. Every figure goes through plots_style.save_figure, report and slide variants.
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
import hopfield_qr_masked  # noqa: E402
import hopfield_qr_select  # noqa: E402
import plots_style  # noqa: E402
import qr  # noqa: E402

DEFAULT_RESULTS = TP_DIR / "analysis" / "results" / "hopfield" / "qr_masked"
DEFAULT_OUT = DEFAULT_RESULTS / "figures"
FIGURE_STEMS = ("masked_patterns", "masked_recovery")
RULES = ("hebb", "hamming")
RULE_LABELS = {"hebb": "Hebb, parte variable de 3 QR", "hamming": "Hamming 1-NN (lookup)"}
GLYPH_ON = "#1f1f1f"
GLYPH_OFF = "#ecebe6"
COMMON = "#b9b8b3"
ABLATION_LABELS = {
    "full_all": "5 QR\ncompletos",
    "masked_all": "5 QR\nparte variable",
    "full_subset": "3 QR\ncompletos",
    "masked_subset": "3 QR\nparte variable",
}


def _fmt(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def _read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _read_rows(path: Path) -> list[dict]:
    with Path(path).open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def plot_masked_patterns(patterns, selection: dict, out_stem) -> None:
    """The common template (grey = common pixel) and the chosen triple with its common pixels greyed out."""
    from matplotlib.colors import ListedColormap

    plt = plots_style.apply_style()
    P = np.asarray(patterns)
    side = int(round(P.shape[1] ** 0.5))
    mask = np.zeros(P.shape[1], dtype=bool)
    mask[selection["varying_indices"]] = True
    cmap = ListedColormap([GLYPH_OFF, COMMON, GLYPH_ON])  # -1 light, 0 common, +1 dark
    panels = [("píxeles variables (negro)", np.where(mask, 1, 0))]
    for index, name in zip(selection["chosen"], selection["chosen_names"]):
        panels.append((name, np.where(mask, P[index], 0)))
    fig, axes = plt.subplots(1, len(panels), figsize=plots_style.figsize((2.8 * len(panels) + 0.6, 3.4)))
    for ax, (title, image) in zip(axes, panels):
        ax.imshow(image.reshape(side, side), cmap=cmap, vmin=-1, vmax=1, interpolation="nearest")
        ax.set_title(title, fontsize=plots_style.fontsize(10))
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
    plots_style.suptitle(fig, f"La red guarda solo los {selection['n_varying']} píxeles que cambian entre los 5 QR",
                         fontsize=12, x=0.01, ha="left")
    fig.tight_layout(rect=plots_style.rect((0, 0.1, 1, 0.92)))
    plots_style.caption(fig, f"Gris: los {selection['n_common']} de {selection['n_pixels']} píxeles iguales en los 5 QR "
                             "(los patrones de localización y toda la zona que codifica lo común de las URL); se "
                             "completan desde esa plantilla común. Los 3 QR son el trío de menor producto escalar máximo entre pares.")
    plots_style.save_figure(fig, out_stem)


def plot_masked_recovery(rows: list[dict], ablation: dict, out_stem) -> None:
    """Left: exact recovery against noise, Hebb on the masked triple and the Hamming lookup on the same patterns.
    Right: the ablation, the fraction of stored patterns that are fixed points of Hebb at noise 0."""
    plt = plots_style.apply_style()
    colors = plots_style.palette_for(list(RULES))
    slide = plots_style.variant() == "slide"
    if slide:  # the slide shows only the recovery curve, at full size; the ablation stays in the report
        fig, recall_ax = plt.subplots(1, 1, figsize=plots_style.figsize((12.5, 4.8), slide=(11.5, 5.0)))
        bar_ax = None
    else:
        fig, (recall_ax, bar_ax) = plt.subplots(1, 2, figsize=plots_style.figsize((12.5, 4.8)),
                                                gridspec_kw={"width_ratios": (1.6, 1)})
    for rule in RULES:
        mine = sorted((r for r in rows if r["rule"] == rule), key=lambda r: float(r["noise"]))
        noise = np.array([float(r["noise"]) for r in mine])
        rate = np.array([float(r["recall_rate"]) for r in mine])
        sd = np.array([float(r["recall_sd_seeds"]) for r in mine])
        label = ("Hebb" if rule == "hebb" else "Hamming (lookup)") if slide else RULE_LABELS[rule]
        recall_ax.plot(noise, rate, "-", marker="o", markersize=4, color=colors[rule], label=label)
        recall_ax.fill_between(noise, np.clip(rate - sd, 0, 1), np.clip(rate + sd, 0, 1), color=colors[rule],
                               alpha=0.12, linewidth=0)
    recall_ax.set_ylim(0, 1.05)
    recall_ax.set_xlabel("nivel de ruido (fracción de píxeles variables invertidos)" if not slide else "nivel de ruido")
    recall_ax.set_ylabel("tasa de recuperación exacta")
    recall_ax.legend(fontsize=plots_style.fontsize(7.5), frameon=False, loc="lower left")
    recall_ax.set_title("Recuperación exacta", fontsize=plots_style.fontsize(10), loc="left")

    if bar_ax is not None:
        keys = [key for key, _m, _s in hopfield_qr_masked.ABLATION]
        fractions = [ablation[key]["stored_fixed"] / ablation[key]["n_patterns"] for key in keys]
        bars = bar_ax.bar(range(len(keys)), fractions, color=[COMMON] * (len(keys) - 1) + [colors["hebb"]])
        for bar, key in zip(bars, keys):
            item = ablation[key]
            bar_ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.03,
                        f"{item['stored_fixed']}/{item['n_patterns']}", ha="center", va="bottom",
                        fontsize=plots_style.fontsize(9), color=plots_style.TEXT_PRIMARY)
        bar_ax.set_xticks(range(len(keys)))
        bar_ax.set_xticklabels([ABLATION_LABELS[key] for key in keys], fontsize=plots_style.fontsize(8))
        bar_ax.set_ylim(0, 1.2)
        bar_ax.set_ylabel("QR que son punto fijo de Hebb")
        bar_ax.set_title("Sin ruido: hacen falta los dos pasos", fontsize=plots_style.fontsize(10), loc="left")

    trials = int(rows[0]["n_trials"]) if rows else 0
    plots_style.suptitle(fig, "Hebb sobre la parte variable de 3 QR: recuperación frente al ruido",
                         fontsize=12, x=0.01, ha="left")
    fig.tight_layout(rect=plots_style.rect((0, 0.1, 1, 0.93)))
    plots_style.caption(fig, f"Experimento posterior al protocolo, no preregistrado. Cada punto agrupa {trials} ensayos "
                             "(3 QR, 30 ensayos, 10 seeds); la banda es ± el desvío entre seeds. El ruido invierte "
                             "píxeles de la parte variable; los comunes se completan desde la plantilla.")
    plots_style.save_figure(fig, out_stem)


def require_same_code(run: dict, repo_dir=TP_DIR) -> None:
    changed = hopfield_qr_masked.changed_code_files(run.get("code_identity"), repo_dir)
    if changed:
        raise SystemExit(f"the masked results come from different code: {', '.join(changed)} differ from the sha256 "
                         "recorded in qr_masked/run.json; re-run make hopfield-qr-masked")


def draw(results_dir=DEFAULT_RESULTS, out_dir=None, patterns_path=None, check_rule: bool = True,
         check_code: bool = True, repo_dir=TP_DIR) -> list[Path]:
    results_dir = Path(results_dir)
    out_dir = Path(out_dir) if out_dir is not None else results_dir / "figures"
    run_path = results_dir / "run.json"
    if not run_path.exists():
        raise SystemExit(f"{run_path}: not found, run make hopfield-qr-masked first")
    if check_rule:
        hopfield_qr_select.require_same_rule(run_path, repo_dir)
    if check_code:
        require_same_code(_read_json(run_path), repo_dir)
    selection = _read_json(results_dir / "selection.json")
    ablation = _read_json(results_dir / "ablation.json")
    rows = _read_rows(results_dir / "recall.csv")
    patterns = hopfield.load_patterns(patterns_path if patterns_path is not None else qr.PREPARED_CSV)
    out_dir.mkdir(parents=True, exist_ok=True)
    for _ in plots_style.iter_variants():
        plot_masked_patterns(patterns, selection, out_dir / "masked_patterns")
        plot_masked_recovery(rows, ablation, out_dir / "masked_recovery")
    return [out_dir / f"{stem}.{suffix}" for stem in FIGURE_STEMS for suffix in ("svg", "png")]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    for path in draw(args.results, args.out):
        try:
            print(path.resolve().relative_to(TP_DIR).as_posix())
        except ValueError:
            print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
