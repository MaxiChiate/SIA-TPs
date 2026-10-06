"""Charts for the slide deck, as HTML snippets in the Slides format (stdlib only).

Writes one snippet per chart into --out. Bars, heatmaps and legends are painted <div>s; lines are one
<svg> with every label as a pinned <p> over it (fonts never load inside an svg). Colors follow the
dataviz reference palette (categorical slots 1-5 in fixed order).

    python3 analysis/plots_presentation.py --out /tmp/charts
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import fraud_calibration  # noqa: E402
import fraud_threshold  # noqa: E402
import model  # noqa: E402
import perturb_dataset  # noqa: E402

TP_DIR = Path(__file__).resolve().parent.parent
DATA = TP_DIR / "neuron" / "data"
RESULTS = TP_DIR / "analysis" / "results"

INK, MUTED, GRID, TRACK = "#15202B", "#4A5560", "#DAD6CA", "#E8E4D8"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]  # dataviz slots 1-5
FONT = "font-family:'IBM Plex Sans', Arial, sans-serif"


@dataclass(frozen=True)
class Line:
    label: str
    points: list[tuple[float, float]]
    color: str
    band: list[tuple[float, float, float]] | None = None  # (x, low, high): a translucent area behind the line


def latest(prefix: str) -> Path:
    return sorted(RESULTS.glob(f"{prefix}_*"))[-1]


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def fmt(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def pinned(text: str, left: float, top: float, width: float, size: int = 24, align: str = "left", color: str = MUTED) -> str:
    return (f'<p style="position:absolute;left:{left:.0f}px;top:{top:.0f}px;width:{width:.0f}px;font-size:{size}px;'
            f'color:{color};text-align:{align};white-space:nowrap">{text}</p>')


def legend(items: list[tuple[str, str]]) -> str:
    cells = "".join(
        f'<div style="display:flex;gap:12px;align-items:center"><div style="width:28px;height:8px;background:{color};border-radius:4px"></div>'
        f'<p style="font-size:26px;color:{INK}">{label}</p></div>' for label, color in items)
    return f'<div style="display:flex;gap:40px;flex-wrap:wrap">{cells}</div>'


def hbars(items: list[tuple[str, float, str, str]], vmax: float, label_w: int = 420, track_w: int = 760) -> str:
    """items: (label, value, color, value text)."""
    out = []
    for label, value, color, text in items:
        bar = max(4, round(track_w * value / vmax))
        out.append(
            f'<div style="display:flex;gap:24px;align-items:center">'
            f'<p style="font-size:28px;color:{INK};width:{label_w}px;text-align:right">{label}</p>'
            f'<div style="width:{track_w}px;display:flex"><div style="width:{bar}px;height:44px;background:{color};border-radius:0 6px 6px 0"></div></div>'
            f'<p style="font-size:28px;color:{INK};font-weight:600">{text}</p></div>')
    return f'<div style="display:flex;flex-direction:column;gap:14px">{"".join(out)}</div>'


def histogram(values: list[float], bins: int, cut: float, height: int = 360, bar_w: int = 36) -> str:
    counts = [0] * bins
    for value in values:
        counts[min(int(value * bins), bins - 1)] += 1
    top = max(counts)
    bars = []
    for index, count in enumerate(counts):
        color = SERIES[1] if (index + 1) / bins > cut + 1e-9 else SERIES[0]
        bars.append(f'<div style="width:{bar_w}px;height:{max(2, round(height * count / top))}px;background:{color};border-radius:4px 4px 0 0"></div>')
    width = bins * bar_w + (bins - 1) * 6
    axis = (f'<div style="display:flex;justify-content:space-between;width:{width}px"><p style="font-size:24px;color:{MUTED}">0</p>'
            f'<p style="font-size:24px;color:{MUTED}">0,5</p><p style="font-size:24px;color:{MUTED}">1</p></div>')
    return (f'<div style="display:flex;flex-direction:column;gap:12px"><div style="display:flex;gap:6px;align-items:flex-end;height:{height}px;'
            f'border-bottom:2px solid {MUTED}">{"".join(bars)}</div>{axis}</div>')


def grouped_bars(groups: list[str], series: list[tuple[str, str, list[float]]], height: int = 360, bar_w: int = 40, note: dict[tuple[int, int], str] | None = None) -> str:
    top = max(max(values) for _, _, values in series)
    cols = []
    for g, name in enumerate(groups):
        bars = []
        for s, (_, color, values) in enumerate(series):
            label = (note or {}).get((s, g), "")
            label_html = f'<p style="font-size:24px;font-weight:600">{label}</p>' if label else ""
            bars.append(f'<div style="display:flex;flex-direction:column;align-items:center;width:{bar_w}px">{label_html}'
                        f'<div style="width:{bar_w}px;height:{max(2, round(height * values[g] / top))}px;background:{color};border-radius:4px 4px 0 0"></div></div>')
        cols.append(f'<div style="display:flex;flex-direction:column;align-items:center;gap:8px"><div style="display:flex;gap:4px;align-items:flex-end;border-bottom:2px solid {MUTED}">{"".join(bars)}</div>'
                    f'<p style="font-size:28px">{name}</p></div>')
    return f'<div style="display:flex;gap:18px;align-items:flex-end;color:{INK}">{"".join(cols)}</div>'


def line_chart(lines: list[Line], width: int, height: int, xticks: list[float], yticks: list[float], xlog: bool = False,
               ylog: bool = False, xlabel: str = "", ylabel: str = "", fmt_x=None, fmt_y=None,
               vlines: list[tuple[float, str]] | None = None) -> str:
    left, right, top, bottom = 130, 20, 20, 90
    plot_w, plot_h = width - left - right, height - top - bottom
    xs = [x for line in lines for x, _ in line.points]
    ys = [y for line in lines for _, y in line.points]
    tx = (lambda v: math.log10(v)) if xlog else (lambda v: v)
    ty = (lambda v: math.log10(v)) if ylog else (lambda v: v)
    x0, x1 = tx(min(xticks)), tx(max(xticks))
    y0, y1 = ty(min(yticks)), ty(max(yticks))
    px = lambda v: left + plot_w * (tx(v) - x0) / (x1 - x0)
    py = lambda v: top + plot_h * (1 - (ty(v) - y0) / (y1 - y0))
    fmt_x = fmt_x or (lambda v: f"{v:g}")
    fmt_y = fmt_y or (lambda v: f"{v:g}")
    svg = [f'<svg aria-label="{ylabel} contra {xlabel}" style="position:absolute;left:0px;top:0px;width:{width}px;height:{height}px" '
           f'width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">']
    for value in yticks:
        svg.append(f'<line x1="{left}" y1="{py(value):.1f}" x2="{left + plot_w}" y2="{py(value):.1f}" stroke="{GRID}" stroke-width="2"/>')
    svg.append(f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="{MUTED}" stroke-width="2"/>')
    for value, _ in vlines or []:
        svg.append(f'<line x1="{px(value):.1f}" y1="{top}" x2="{px(value):.1f}" y2="{top + plot_h}" stroke="{INK}" stroke-width="3" stroke-dasharray="10 8"/>')
    for line in lines:
        if line.band:
            outline = [(x, high) for x, _, high in line.band] + [(x, low) for x, low, _ in reversed(line.band)]
            area = " ".join(f"{px(x):.1f},{py(y):.1f}" for x, y in outline)
            svg.append(f'<polygon points="{area}" fill="{line.color}" fill-opacity="0.18" stroke="none"/>')
    for line in lines:
        pts = " ".join(f"{px(x):.1f},{py(y):.1f}" for x, y in line.points)
        svg.append(f'<polyline points="{pts}" fill="none" stroke="{line.color}" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"/>')
        if len(line.points) <= 12:
            for x, y in line.points:
                svg.append(f'<circle cx="{px(x):.1f}" cy="{py(y):.1f}" r="8" fill="{line.color}" stroke="#F5F3EC" stroke-width="2"/>')
    svg.append("</svg>")
    labels = [pinned(fmt_y(v), 0, py(v) - 16, left - 14, align="right") for v in yticks]
    labels += [pinned(fmt_x(v), px(v) - 60, top + plot_h + 12, 120, align="center") for v in xticks]
    labels += [pinned(text, px(value) + 12, top + plot_h - 44, 260, color=INK) for value, text in vlines or []]
    labels.append(pinned(xlabel, left, height - 34, plot_w, align="center"))
    return f'<div style="position:relative;width:{width}px;height:{height}px">{"".join(svg)}{"".join(labels)}</div>'


def class_counts(name: str) -> list[int]:
    counts = [0] * 10
    for row in rows(DATA / f"{name}.csv"):
        counts[int(row["label"])] += 1
    return counts


def fraud_histogram() -> str:
    values = [float(r["big_model_fraud_probability"]) for r in rows(DATA / "fraud_dataset.csv")]
    return histogram(values, bins=20, cut=0.85)


def fraud_curves() -> str:
    directory = latest("series_fraud_activation")
    chosen = {"lineal eta 0.001": ("Lineal (η 0,001)", SERIES[0]), "logistic eta 0.01": ("Logistic (η 0,01)", SERIES[1])}
    lines = []
    for run_label, (name, color) in chosen.items():
        curves = []
        for row in rows(directory / "summary.csv"):
            if row["label"] == run_label:
                curves.append([float(r["train_mse"]) for r in rows(directory / "runs" / row["run"] / "epochs.csv")][:21])
        mean = [statistics.fmean(values) for values in zip(*curves)]
        lines.append(Line(name, [(e, max(v, 1e-3)) for e, v in enumerate(mean)], color))
    chart = line_chart(lines, 1500, 480, [0, 5, 10, 15, 20], [0.01, 0.1, 1], ylog=True, xlabel="Épocas", ylabel="MSE de train",
                       fmt_y=lambda v: fmt(v, 2))
    return legend([(line.label, line.color) for line in lines]) + chart


def fraud_r2() -> str:
    directory = latest("series_fraud_relu")
    variance = statistics.pvariance([float(r["big_model_fraud_probability"]) for r in rows(DATA / "fraud_dataset.csv")])
    r2 = {}
    for label in dict.fromkeys(r["label"] for r in rows(directory / "summary.csv")):
        mse = [float(r["train_mse"]) for r in rows(directory / "summary.csv") if r["label"] == label]
        r2[label] = 1 - statistics.fmean(mse) / variance
    names = {"lineal": "Lineal", "relu": "ReLU", "logistic": "Logistic", "relu [16]": "ReLU con [16]", "logistic [16]": "Logistic con [16]"}
    order = ["lineal", "relu", "logistic", "relu [16]", "logistic [16]"]
    colors = {"lineal": SERIES[0], "relu": SERIES[2], "logistic": SERIES[1], "relu [16]": SERIES[2], "logistic [16]": SERIES[1]}
    items = [(names[k], r2[k], colors[k], fmt(r2[k])) for k in order]
    return hbars(items, vmax=1.0, label_w=360, track_w=700)


def digits_distribution() -> str:
    digits, more = class_counts("digits"), class_counts("more_digits")
    note = {(0, 5): "271", (0, 8): "0", (1, 5): "542", (1, 8): "585"}
    chart = grouped_bars([str(d) for d in range(10)], [("digits", SERIES[0], digits), ("more_digits", SERIES[1], more)],
                         height=300, bar_w=52, note=note)
    return legend([("digits.csv (12 449)", SERIES[0]), ("more_digits.csv (15 741)", SERIES[1])]) + chart


def xor_convergence() -> str:
    items = [("GD", 2, SERIES[0]), ("Momentum", 5, SERIES[1]), ("RMSProp", 3, SERIES[2]), ("Adam", 3, SERIES[3])]
    return hbars([(name, value, color, f"{value} de 6") for name, value, color in items], vmax=6, label_w=240, track_w=720)


OPTIMIZERS = [("gd", "GD"), ("adaptive", "η adaptativo"), ("momentum", "Momentum"), ("rmsprop", "RMSProp"), ("adam", "Adam")]
OPTIMIZER_COLOR = {name: SERIES[i] for i, (_, name) in enumerate(OPTIMIZERS)}  # same color for the same optimizer in every chart


def eta_accuracies() -> dict[str, dict[float, float]]:
    """Mean validation accuracy (%) per optimizer and eta: the stage-1 grids plus the series that extend them."""
    found: dict[tuple[str, float], list[float]] = {}
    for key, _ in OPTIMIZERS:
        for row in rows(latest(f"series_eta_{key}") / "summary.csv"):
            found.setdefault((key, float(row["label"].replace("eta=", ""))), []).append(float(row["accuracy"]))
    for prefix in ("series_eta_edges", "series_eta_edges_high", "series_eta_edges_higher"):
        for row in rows(sorted(RESULTS.glob(f"{prefix}_2*"))[-1] / "summary.csv"):
            key, eta = row["label"].split()
            found.setdefault((key, float(eta)), []).append(float(row["accuracy"]))
    result: dict[str, dict[float, float]] = {key: {} for key, _ in OPTIMIZERS}
    for (key, eta), values in found.items():
        result[key][eta] = 100 * statistics.fmean(values)
    return result


def eta_sensitivity() -> str:
    by_optimizer = eta_accuracies()
    lines = []
    for key, name in OPTIMIZERS:
        points = [(eta, acc) for eta, acc in sorted(by_optimizer[key].items()) if acc >= 90 and eta <= 1]
        lines.append(Line(name, points, OPTIMIZER_COLOR[name]))
    chart = line_chart(lines, 1500, 500, [0.0001, 0.001, 0.01, 0.1, 1], [90, 92, 94, 96, 98], xlog=True,
                       xlabel="Tasa de aprendizaje η (escala logarítmica)", ylabel="Accuracy de validación (%)",
                       fmt_x=lambda v: fmt(v, 4).rstrip("0").rstrip(",") if v < 1 else "1", fmt_y=lambda v: f"{v:g} %")
    return legend([(line.label, line.color) for line in lines]) + chart


def dot_plot(groups: list[tuple[str, list[float], str]], lo: float, hi: float, ticks: list[float], width: int = 780, row: int = 64) -> str:
    """One row per group: a dot per seed and a dark bar at the mean."""
    left, top = 210, 8
    plot_w, height = width - left - 20, top + row * len(groups) + 56
    px = lambda v: left + plot_w * (v - lo) / (hi - lo)
    svg = [f'<svg aria-label="Accuracy por seed y media de cada optimizador" style="position:absolute;left:0px;top:0px;width:{width}px;height:{height}px" '
           f'width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">']
    for tick in ticks:
        svg.append(f'<line x1="{px(tick):.1f}" y1="{top}" x2="{px(tick):.1f}" y2="{top + row * len(groups)}" stroke="{GRID}" stroke-width="2"/>')
    labels = [pinned(f"{tick:.1f}".replace(".", ","), px(tick) - 50, top + row * len(groups) + 8, 100, align="center") for tick in ticks]
    for index, (name, values, color) in enumerate(groups):
        y = top + row * index + row / 2
        mean = statistics.fmean(values)
        svg.append(f'<line x1="{px(mean):.1f}" y1="{y - 18:.1f}" x2="{px(mean):.1f}" y2="{y + 18:.1f}" stroke="{INK}" stroke-width="5"/>')
        for value in values:
            svg.append(f'<circle cx="{px(value):.1f}" cy="{y:.1f}" r="9" fill="{color}" stroke="#F5F3EC" stroke-width="2"/>')
        labels.append(pinned(name, 0, y - 16, left - 24, size=28, align="right", color=INK))
    svg.append("</svg>")
    return f'<div style="position:relative;width:{width}px;height:{height}px">{"".join(svg)}{"".join(labels)}</div>'


def optimizer_dots(prefix: str, lo: float, hi: float, ticks: list[float]) -> str:
    runs = rows(sorted(RESULTS.glob(f"{prefix}_2*"))[-1] / "summary.csv")
    groups = [(name, [100 * float(r["accuracy"]) for r in runs if r["label"] == name], OPTIMIZER_COLOR[name]) for _, name in OPTIMIZERS]
    return dot_plot(groups, lo, hi, ticks)


def optimizer_validation_dots() -> str:
    return optimizer_dots("series_optimizer", 95.5, 97.0, [95.5, 96.0, 96.5, 97.0])


def optimizer_test_dots() -> str:
    return optimizer_dots("series_optimizer_test", 94.5, 96.5, [94.5, 95.0, 95.5, 96.0, 96.5])


def optimizer_curves() -> str:
    directory = sorted(RESULTS.glob("series_optimizer_2*"))[-1]
    runs = rows(directory / "summary.csv")
    lines = []
    for _, name in OPTIMIZERS:
        curves = [[float(e["validation_mse"]) for e in rows(directory / "runs" / r["run"] / "epochs.csv")] for r in runs if r["label"] == name]
        mean = [statistics.fmean(values) for values in zip(*curves)]
        lines.append(Line(name, [(epoch, mean[epoch]) for epoch in range(1, 51)], OPTIMIZER_COLOR[name]))
    chart = line_chart(lines, 1500, 480, [1, 10, 20, 30, 40, 50], [0.006, 0.008, 0.010, 0.012, 0.014, 0.016], xlabel="Épocas", ylabel="MSE de validación",
                       fmt_y=lambda v: fmt(v, 3))
    return legend([(line.label, line.color) for line in lines]) + chart


def confusion(predictions: Path) -> str:
    matrix = [[0] * 10 for _ in range(10)]
    for row in rows(predictions):
        real = max(range(10), key=lambda k: float(row[f"zeta_{k}"]))
        pred = max(range(10), key=lambda k: float(row[f"prediction_{k}"]))
        matrix[real][pred] += 1
    cell = 48
    box = f"width:{cell}px;height:{cell}px"
    parts = [f'<div style="{box}"></div>'] + [f'<p style="{box};color:{MUTED}">{k}</p>' for k in range(10)]
    for real in range(10):
        total = sum(matrix[real]) or 1
        parts.append(f'<p style="{box};color:{MUTED}">{real}</p>')
        for pred in range(10):
            count, fraction = matrix[real][pred], matrix[real][pred] / total
            if fraction < 0.004:
                parts.append(f'<div style="{box}"></div>')
                continue
            color = f"#{round(251 - fraction * 209):02x}{round(250 - fraction * 130):02x}{round(246 - fraction * 32):02x}"
            ink = ";color:#FFFFFF" if fraction > 0.55 else ""
            parts.append(f'<p style="{box};background:{color}{ink}">{count}</p>')
    return (f'<div style="display:grid;grid-template-columns:repeat(11, {cell}px);gap:2px;font-size:24px;line-height:2;text-align:center;color:{INK}">'
            f'{"".join(parts)}</div>')


def per_class_recall(predictions: Path) -> list[float]:
    hits, totals = [0] * 10, [0] * 10
    for row in rows(predictions):
        real = max(range(10), key=lambda k: float(row[f"zeta_{k}"]))
        pred = max(range(10), key=lambda k: float(row[f"prediction_{k}"]))
        totals[real] += 1
        hits[real] += real == pred
    return [100 * h / t for h, t in zip(hits, totals)]


def recall_comparison(only_digits: Path, with_more: Path) -> str:
    a, b = per_class_recall(only_digits), per_class_recall(with_more)
    note = {(0, 5): fmt(a[5], 0), (1, 5): fmt(b[5], 0), (0, 8): fmt(a[8], 0), (1, 8): fmt(b[8], 0)}
    chart = grouped_bars([str(d) for d in range(10)], [("digits", SERIES[0], a), ("more_digits", SERIES[1], b)], height=300, bar_w=52, note=note)
    return legend([("Entrenada con digits.csv", SERIES[0]), ("Entrenada con more_digits.csv", SERIES[1])]) + chart


def fraud_feature_bars() -> str:
    directory = latest("series_fraud_features")
    order = ["9 entradas", "6 entradas", "9 entradas, log(amount)", "6 entradas, log(amount)"]
    colors = [SERIES[0], SERIES[0], SERIES[1], SERIES[1]]
    items = []
    for label, color in zip(order, colors):
        mse = statistics.fmean(float(r["validation_mse"]) for r in rows(directory / "summary.csv") if r["label"] == label)
        items.append((label, mse, color, fmt(mse, 4)))
    return hbars(items, vmax=0.02, label_w=340, track_w=300)


def fraud_size_curve() -> str:
    directory = latest("series_fraud_train_size")
    sizes = {"5 % del train": 262, "10 % del train": 525, "25 % del train": 1312, "50 % del train": 2624, "100 % del train": 5250}
    points = []
    for label, n in sizes.items():
        mse = statistics.fmean(float(r["validation_mse"]) for r in rows(directory / "summary.csv") if r["label"] == label)
        points.append((n, mse))
    chart = line_chart([Line("MSE de validación", points, SERIES[0])], 820, 400, [262, 525, 1312, 2624, 5250], [0, 0.005, 0.010, 0.015],
                       xlog=True, xlabel="Muestras de entrenamiento (escala logarítmica)", ylabel="MSE de validación",
                       fmt_x=lambda v: f"{v:g}", fmt_y=lambda v: fmt(v, 3))
    return chart


def threshold_curve(chosen: float = 0.78) -> str:
    directory = latest("series_fraud_final")
    run = next(r["run"] for r in rows(directory / "summary.csv") if r["label"] == "validacion" and r["seed"] == "1")
    scored = fraud_threshold.load(directory / "runs" / run / "predictions.csv", DATA / "fraud_drop3_validation_labels.csv")
    grid = [0.6 + 0.025 * i for i in range(13)]
    precision = [(t, fraud_threshold.counts_at(scored, t).precision) for t in grid]
    recall = [(t, fraud_threshold.counts_at(scored, t).recall) for t in grid]
    lines = [Line("Precisión", precision, SERIES[0]), Line("Recall", recall, SERIES[1])]
    chart = line_chart(lines, 1000, 480, [0.6, 0.7, 0.8, 0.9], [0.4, 0.6, 0.8, 1.0], xlabel="Umbral de detección", ylabel="Precisión y recall",
                       fmt_x=lambda v: fmt(v, 1), fmt_y=lambda v: fmt(v, 1), vlines=[(chosen, "Umbral 0,78")])
    return legend([(line.label, line.color) for line in lines]) + chart


def fraud_reliability() -> str:
    """Observed fraud rate against the mean prediction (test), before and after Platt scaling fit on validation."""
    directory = latest("series_fraud_final")
    runs = {r["label"]: r["run"] for r in rows(directory / "summary.csv") if r["seed"] == "1"}
    validation = fraud_threshold.load(directory / "runs" / runs["validacion"] / "predictions.csv", DATA / "fraud_drop3_validation_labels.csv")
    test = fraud_threshold.load(directory / "runs" / runs["test"] / "predictions.csv", DATA / "fraud_drop3_test_labels.csv")
    a, b = fraud_calibration.fit_platt(validation.prediction, validation.label)
    raw = [(m, r) for m, r, _ in fraud_calibration.reliability(test.prediction, test.label)]
    platt = [(m, r) for m, r, _ in fraud_calibration.reliability([fraud_calibration.sigmoid(a * p + b) for p in test.prediction], test.label)]
    lines = [Line("Calibración perfecta", [(0.0, 0.0), (1.0, 1.0)], MUTED), Line("TinyModel sin calibrar", raw, SERIES[0]), Line("Con Platt", platt, SERIES[1])]
    chart = line_chart(lines, 900, 480, [0, 0.25, 0.5, 0.75, 1], [0, 0.25, 0.5, 0.75, 1], xlabel="Probabilidad predicha (media del intervalo)",
                       ylabel="Fraudes observados", fmt_x=lambda v: fmt(v, 2), fmt_y=lambda v: fmt(v, 2))
    return legend([(line.label, line.color) for line in lines]) + chart


def digits_vs_test() -> str:
    digits, test = class_counts("digits"), class_counts("digits_test")
    chart = grouped_bars([str(d) for d in range(10)], [("digits", SERIES[0], digits), ("digits_test", SERIES[2], test)],
                         height=300, bar_w=52, note={(0, 5): "271", (0, 8): "0"})
    return legend([("digits.csv (12 449)", SERIES[0]), ("digits_test.csv (2 497)", SERIES[2])]) + chart


def architecture_dots() -> str:
    runs = rows(sorted(RESULTS.glob("series_architecture_digits_2*"))[-1] / "summary.csv")
    labels = ["[] (simple)", "[16]", "[32]", "[64]", "[128]", "[64, 32]"]
    groups = [(label, [100 * float(r["accuracy"]) for r in runs if r["label"] == label], SERIES[0]) for label in labels]
    return dot_plot(groups, 92.0, 97.5, [92.0, 93.0, 94.0, 95.0, 96.0, 97.0], width=900)


def optimizer_digits_test_dots() -> str:
    return optimizer_dots("series_optimizer_digits_test", 84.5, 87.0, [84.5, 85.0, 85.5, 86.0, 86.5, 87.0])


def ex3_ablation() -> str:
    """Validation accuracy after each technique of Exercise 3 (one dot per seed), and the ensemble of 9 networks."""
    def accuracies(prefix: str, label: str) -> list[float]:
        return [100 * float(r["accuracy"]) for r in rows(sorted(RESULTS.glob(f"{prefix}_2*"))[-1] / "summary.csv") if r["label"] == label]
    step3 = sorted(RESULTS.glob("series_ex3_step3_2*"))[-1]
    loaded = [model.load_predictions(step3 / "runs" / r["run"] / "predictions.csv") for r in rows(step3 / "summary.csv")]
    ensemble = 100 * model.accuracy(model.average(loaded))
    steps = [("[64], more_digits", accuracies("series_ex3_step1", "more [64]")), ("+ unión de datos", accuracies("series_ex3_step1", "unión [64]")),
             ("+ [256]", accuracies("series_ex3_step1", "unión [256]")), ("+ aumento ×3", accuracies("series_ex3_step2", "aumento x3")),
             ("+ [512]", accuracies("series_ex3_step3", "a2 [512]")), ("Ensemble de 9", [ensemble])]
    return dot_plot([(name, values, SERIES[1] if name.startswith("Ensemble") else SERIES[0]) for name, values in steps], 96.0, 99.0,
                    [96.0, 97.0, 98.0, 99.0], width=1000)


ROBUSTNESS_NAMES = {"ex2_single": "Ej. 2, una red", "ex2_ensemble": "Ej. 2, ensemble de 10",
                    "ex3_single": "Ej. 3, una red", "ex3_ensemble": "Ej. 3, ensemble de 9"}


def robustness_rows() -> tuple[Path, list[dict[str, str]], list[str]]:
    """The latest analysis/robustness.py output: its directory, rows and models in their order (= color slot)."""
    directory = latest("robustness")
    found = rows(directory / "robustness.csv")
    return directory, found, list(dict.fromkeys(row["model"] for row in found))


def robustness_name(model: str, found: list[dict[str, str]]) -> str:
    return ROBUSTNESS_NAMES.get(model) or next(row["label"] for row in found if row["model"] == model)


def robustness_curve() -> str:
    """Accuracy against σ of the Gaussian noise: mean over the noise seeds, with a ± standard deviation band."""
    _, found, models = robustness_rows()
    lines = []
    for index, name in enumerate(models):
        by_sigma: dict[float, list[float]] = {}
        for row in found:
            if row["model"] == name:
                by_sigma.setdefault(float(row["sigma"]), []).append(100 * float(row["accuracy"]))
        stats = [(sigma, statistics.fmean(v), statistics.stdev(v) if len(v) > 1 else 0.0) for sigma, v in sorted(by_sigma.items())]
        lines.append(Line(robustness_name(name, found), [(s, m) for s, m, _ in stats], SERIES[index], [(s, m - d, m + d) for s, m, d in stats]))
    sigmas = sorted({x for line in lines for x, _ in line.points})
    low = math.floor(min(y for line in lines for _, y in line.points) / 10) * 10
    chart = line_chart(lines, 1040, 560, sigmas, list(range(low, 101, 10)), xlabel="Desvío σ del ruido gaussiano (píxeles en [0, 1])",
                       ylabel="Accuracy en test (%)", fmt_x=lambda v: fmt(v, 2).rstrip("0").rstrip(","), fmt_y=lambda v: f"{v:g} %")
    return legend([(line.label, line.color) for line in lines]) + chart


def pixel_paths(keys: list, side: int) -> dict:
    """svg path data per key (a color or level; None = background), one rectangle per horizontal run of equal keys."""
    paths: dict = {}
    for row in range(side):
        col = 0
        while col < side:
            key, start = keys[row * side + col], col
            while col < side and keys[row * side + col] == key:
                col += 1
            if key is not None:
                paths.setdefault(key, []).append(f"M{start} {row}h{col - start}v1h-{col - start}z")
    return paths


def pixel_image(values: list[float], side: int = 28, size: int = 196) -> str:
    """A grayscale image as one svg path per gray level (16 levels): dark ink on white, value 1 = ink."""
    levels = [round(15 * min(1.0, max(0.0, value))) or None for value in values]
    paths = pixel_paths(levels, side)
    shapes = "".join(f'<path d="{"".join(parts)}" fill="{INK}" fill-opacity="{level / 15:.2f}"/>' for level, parts in sorted(paths.items()))
    return (f'<svg aria-label="Imagen de {side}×{side} píxeles" width="{side}" height="{side}" viewBox="0 0 {side} {side}" style="width:{size}px;height:{size}px" shape-rendering="crispEdges" '
            f'xmlns="http://www.w3.org/2000/svg"><rect width="{side}" height="{side}" fill="#FFFFFF" stroke="{GRID}" stroke-width="0.3"/>{shapes}</svg>')


def noise_examples(sample: int = 0, seed: int = 1) -> str:
    """One test image at every σ of the robustness run, with the exact noise the models saw (same seed, same clip)."""
    run = json.loads((latest("robustness") / "run.json").read_text())
    table = perturb_dataset.load(Path(run["dataset"]))
    clip = run["clip"]
    cells = []
    for sigma in sorted(run["gaussian"]):
        rng = random.Random(seed)
        perturbations = ([perturb_dataset.gaussian(sigma, rng)] if sigma > 0 else []) + ([perturb_dataset.clip(*clip)] if clip else [])
        row = perturb_dataset.perturbed(perturb_dataset.Table(table.header, table.n_inputs, table.rows[:sample + 1]), perturbations)[sample]
        image = pixel_image([float(value) for value in row[:table.n_inputs]])
        cells.append(f'<div style="display:flex;flex-direction:column;align-items:center;gap:10px">{image}'
                     f'<p style="font-size:26px;color:{INK}">σ = {fmt(sigma, 2).rstrip("0").rstrip(",")}</p></div>')
    return f'<div style="display:flex;gap:28px">{"".join(cells)}</div>'


def robustness_by_class(sigma: float = 0.2) -> str:
    """Accuracy per digit at one σ (mean over the noise seeds): a row per model, darker = higher."""
    _, found, models = robustness_rows()
    n_classes = sum(1 for key in found[0] if key.startswith("accuracy_"))
    cell, name_w = 92, 330
    parts = [f'<div style="width:{name_w}px"></div>'] + [f'<p style="color:{MUTED}">{k}</p>' for k in range(n_classes)]
    for name in models:
        chosen = [row for row in found if row["model"] == name and abs(float(row["sigma"]) - sigma) < 1e-9]
        parts.append(f'<p style="text-align:right;padding:0 16px 0 0">{robustness_name(name, found)}</p>')
        for k in range(n_classes):
            value = statistics.fmean(float(row[f"accuracy_{k}"]) for row in chosen)
            color = f"#{round(251 - value * 209):02x}{round(250 - value * 130):02x}{round(246 - value * 32):02x}"
            ink = ";color:#FFFFFF" if value > 0.55 else ""
            parts.append(f'<p style="background:{color}{ink}">{fmt(100 * value, 0)}</p>')
    return (f'<div style="display:grid;grid-template-columns:{name_w}px repeat({n_classes}, {cell}px);gap:2px;font-size:26px;line-height:2.2;'
            f'text-align:center;color:{INK}">{"".join(parts)}</div>')


POSITIVE, NEGATIVE, NEUTRAL = "#e34948", "#2a78d6", "#f0efec"  # dataviz diverging pair: red <-> blue, gray midpoint
METHOD_NAMES = {"saliency": "Saliency", "grad_input": "Gradiente × entrada", "integrated": "Integrated gradients", "occlusion": "Oclusión 4×4"}


def diverging_image(values: list[float], side: int = 28, size: int = 100) -> str:
    """Red where the value pushes the class up, blue where it pushes it down, gray at 0. Scaled per map by the 99th
    percentile of |value|, so one extreme pixel doesn't wash out the rest; 8 opacity steps per arm."""
    magnitudes = sorted(abs(v) for v in values)
    scale = magnitudes[int(0.99 * (len(magnitudes) - 1))] or magnitudes[-1] or 1.0
    levels = [round(8 * min(1.0, abs(value) / scale)) for value in values]
    paths = pixel_paths([(POSITIVE if value > 0 else NEGATIVE, level) if level else None for value, level in zip(values, levels)], side)
    shapes = "".join(f'<path d="{"".join(parts)}" fill="{color}" fill-opacity="{level / 8:.2f}"/>' for (color, level), parts in sorted(paths.items()))
    return (f'<svg aria-label="Mapa de atribución" width="{side}" height="{side}" viewBox="0 0 {side} {side}" style="width:{size}px;height:{size}px" shape-rendering="crispEdges" '
            f'xmlns="http://www.w3.org/2000/svg"><rect width="{side}" height="{side}" fill="{NEUTRAL}"/>{shapes}</svg>')


def attribution_rows(prefix: str) -> tuple[list[dict[str, str]], list[list[float]]]:
    """The latest attribution_<prefix> output: its rows (without the a* columns) and the dataset's inputs."""
    directory = latest(prefix)
    run = json.loads((directory / "run.json").read_text())
    inputs, _ = model.load_dataset(Path(run["dataset"]))
    found = []
    with (directory / "attributions.csv").open(newline="") as file:
        reader = csv.reader(file)
        header = next(reader)
        first = header.index("a1")
        for row in reader:
            entry = dict(zip(header[:first], row[:first]))
            entry["values"] = [float(v) for v in row[first:]]
            found.append(entry)
    return found, inputs


def map_grid(columns: list[str], rows: list[tuple[str, list[str]]], label_w: int = 300, cell: int = 100) -> str:
    """rows: (label, one svg per column)."""
    head = [f'<div style="width:{label_w}px"></div>'] + [f'<p style="text-align:center;color:{MUTED}">{c}</p>' for c in columns]
    body = [cell for label, cells in rows for cell in [f'<p style="text-align:right;padding:0 14px 0 0;align-self:center">{label}</p>', *cells]]
    return (f'<div style="display:grid;grid-template-columns:{label_w}px repeat({len(columns)}, {cell}px);gap:8px;font-size:24px;color:{INK}">'
            f'{"".join(head + body)}</div>')


def diverging_legend() -> str:
    return legend([("a favor de la clase predicha", POSITIVE), ("en contra", NEGATIVE)])


def attribution_methods(name: str = "ex3_ensemble") -> str:
    """One sample per digit: the image, then a row per method (one model)."""
    found, inputs = attribution_rows("attribution_per_class")
    mine = [row for row in found if row["model"] == name]
    samples = list(dict.fromkeys(row["sample"] for row in mine))
    methods = list(dict.fromkeys(row["method"] for row in mine))
    by = {(row["sample"], row["method"]): row for row in mine}
    grid = [("Imagen", [pixel_image(inputs[int(s)], size=100) for s in samples])]
    grid += [(METHOD_NAMES[m], [diverging_image(by[s, m]["values"]) for s in samples]) for m in methods]
    columns = [f'{by[s, methods[0]]["true"]} → {by[s, methods[0]]["predicted"]}' for s in samples]
    return diverging_legend() + map_grid(columns, grid)


def attribution_models(method: str = "integrated") -> str:
    """One sample per digit: the image, then a row per model (one method)."""
    found, inputs = attribution_rows("attribution_per_class")
    mine = [row for row in found if row["method"] == method]
    samples = list(dict.fromkeys(row["sample"] for row in mine))
    models = list(dict.fromkeys(row["model"] for row in mine))
    by = {(row["sample"], row["model"]): row for row in mine}
    grid = [("Imagen", [pixel_image(inputs[int(s)], size=100) for s in samples])]
    for name in models:
        cells = []
        for s in samples:
            row = by[s, name]
            wrong = row["predicted"] != row["true"]
            frame = f'<div style="box-shadow:0 0 0 4px {INK}">' if wrong else "<div>"
            cells.append(f"{frame}{diverging_image(row['values'])}</div>")
        grid.append((f"{ROBUSTNESS_NAMES.get(name, name)}", cells))
    columns = [str(by[s, models[0]]["true"]) for s in samples]
    return diverging_legend() + map_grid(columns, grid, label_w=330)


def attribution_class_means(method: str = "grad_input") -> str:
    """Mean map per true class, a row per model: what each one looks at for each digit, on average."""
    found, _ = attribution_rows("attribution_class_means")
    mine = [row for row in found if row["method"] == method]
    models = list(dict.fromkeys(row["model"] for row in mine))
    classes = sorted({row["true"] for row in mine}, key=int)
    grid = []
    for name in models:
        cells = []
        for c in classes:
            maps = [row["values"] for row in mine if row["model"] == name and row["true"] == c]
            cells.append(diverging_image([statistics.fmean(values) for values in zip(*maps)]))
        grid.append((ROBUSTNESS_NAMES.get(name, name), cells))
    return diverging_legend() + map_grid(classes, grid, label_w=330)


def attribution_errors(name: str = "ex3_ensemble", method: str = "integrated", n: int = 10) -> str:
    """The first errors of a model: the image and the map toward the class it wrongly picked."""
    found, inputs = attribution_rows("attribution_errors")
    mine = [row for row in found if row["model"] == name and row["method"] == method][:n]
    grid = [("Imagen", [pixel_image(inputs[int(row["sample"])], size=100) for row in mine]),
            (METHOD_NAMES[method], [diverging_image(row["values"]) for row in mine])]
    return diverging_legend() + map_grid([f'{row["true"]} → {row["predicted"]}' for row in mine], grid)


def first_layer_weights(name: str = "ex2_single", n: int = 32) -> str:
    """The input weights of the first n hidden neurons of a single network, as 28×28 maps."""
    run = model.load_model(TP_DIR / "analysis" / "models" / f"{name}.json").runs[0]
    cells = [diverging_image(weights[1:], size=88) for weights in run.layers[0][:n]]
    return (legend([("peso positivo", POSITIVE), ("peso negativo", NEGATIVE)])
            + f'<div style="display:grid;grid-template-columns:repeat(8, 88px);gap:8px">{"".join(cells)}</div>')


CHARTS = {"attribution_methods": attribution_methods, "attribution_models": attribution_models,
          "attribution_class_means": attribution_class_means, "attribution_errors": attribution_errors,
          "first_layer_weights": first_layer_weights,
          "robustness_curve": robustness_curve, "noise_examples": noise_examples, "robustness_by_class": robustness_by_class,
          "ex3_ablation": ex3_ablation, "digits_vs_test": digits_vs_test, "architecture_dots": architecture_dots, "optimizer_digits_test_dots": optimizer_digits_test_dots,
          "fraud_reliability": fraud_reliability, "fraud_feature_bars": fraud_feature_bars, "fraud_size_curve": fraud_size_curve, "threshold_curve": threshold_curve,
          "fraud_histogram": fraud_histogram, "fraud_curves": fraud_curves, "fraud_r2": fraud_r2,
          "digits_distribution": digits_distribution, "xor_convergence": xor_convergence, "eta_sensitivity": eta_sensitivity,
          "optimizer_validation_dots": optimizer_validation_dots, "optimizer_test_dots": optimizer_test_dots, "optimizer_curves": optimizer_curves}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--confusion", type=Path, help="predictions.csv of a run on digits_test")
    parser.add_argument("--recall", type=Path, nargs=2, metavar=("DIGITS_RUN", "MORE_DIGITS_RUN"), help="predictions.csv of the two runs")
    parser.add_argument("--only", nargs="*", help="chart names (default: all that can be built)")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    builders = dict(CHARTS)
    if args.confusion:
        builders["confusion"] = lambda: confusion(args.confusion)
    if args.recall:
        builders["recall"] = lambda: recall_comparison(*args.recall)
    for name, build in builders.items():
        if args.only and name not in args.only:
            continue
        try:
            html = build()
        except (IndexError, FileNotFoundError, KeyError) as error:
            print(f"skip {name}: {error!r}")
            continue
        (args.out / f"{name}.html").write_text(html)
        print(f"{name}: {len(html)} bytes")


if __name__ == "__main__":
    main()
