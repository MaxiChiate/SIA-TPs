"""Charts for the slide deck, as HTML snippets in the Slides format (stdlib only).

Writes one snippet per chart into --out. Bars, heatmaps and legends are painted <div>s; lines are one
<svg> with every label as a pinned <p> over it (fonts never load inside an svg). Colors follow the
dataviz reference palette (categorical slots 1-5 in fixed order).

    python3 analysis/plots_presentation.py --out /tmp/charts
"""

from __future__ import annotations

import argparse
import csv
import math
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fraud_threshold  # noqa: E402

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
        pts = " ".join(f"{px(x):.1f},{py(y):.1f}" for x, y in line.points)
        svg.append(f'<polyline points="{pts}" fill="none" stroke="{line.color}" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"/>')
        if len(line.points) <= 12:
            for x, y in line.points:
                svg.append(f'<circle cx="{px(x):.1f}" cy="{py(y):.1f}" r="8" fill="{line.color}" stroke="#F5F3EC" stroke-width="2"/>')
    svg.append("</svg>")
    labels = [pinned(fmt_y(v), 0, py(v) - 16, left - 14, align="right") for v in yticks]
    labels += [pinned(fmt_x(v), px(v) - 60, top + plot_h + 12, 120, align="center") for v in xticks]
    labels += [pinned(text, px(value) + 12, top + 4, 260, color=INK) for value, text in vlines or []]
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


def eta_sensitivity() -> str:
    names = [("gd", "GD"), ("adaptive", "η adaptativo"), ("momentum", "Momentum"), ("rmsprop", "RMSProp"), ("adam", "Adam")]
    lines = []
    for index, (key, name) in enumerate(names):
        directory = latest(f"series_eta_{key}")
        by_eta: dict[float, list[float]] = {}
        for row in rows(directory / "summary.csv"):
            eta = float(row["label"].replace("eta=", "").replace("eta ", ""))
            by_eta.setdefault(eta, []).append(float(row["accuracy"]))
        lines.append(Line(name, [(eta, 100 * statistics.fmean(v)) for eta, v in sorted(by_eta.items())], SERIES[index]))
    chart = line_chart(lines, 1500, 500, [0.0001, 0.001, 0.01, 0.1], [90, 92, 94, 96, 98], xlog=True,
                       xlabel="Tasa de aprendizaje η (escala logarítmica)", ylabel="Accuracy de validación (%)",
                       fmt_x=lambda v: fmt(v, 4).rstrip("0").rstrip(","), fmt_y=lambda v: f"{v:g} %")
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


def threshold_curve(chosen: float = 0.82) -> str:
    directory = latest("series_fraud_final")
    run = next(r["run"] for r in rows(directory / "summary.csv") if r["label"] == "validacion" and r["seed"] == "1")
    scored = fraud_threshold.load(directory / "runs" / run / "predictions.csv", DATA / "fraud_drop3_validation_labels.csv")
    grid = [0.6 + 0.025 * i for i in range(13)]
    precision = [(t, fraud_threshold.counts_at(scored, t).precision) for t in grid]
    recall = [(t, fraud_threshold.counts_at(scored, t).recall) for t in grid]
    lines = [Line("Precisión", precision, SERIES[0]), Line("Recall", recall, SERIES[1])]
    chart = line_chart(lines, 1000, 480, [0.6, 0.7, 0.8, 0.9], [0.4, 0.6, 0.8, 1.0], xlabel="Umbral de detección", ylabel="Precisión y recall",
                       fmt_x=lambda v: fmt(v, 1), fmt_y=lambda v: fmt(v, 1), vlines=[(chosen, "Umbral 0,82")])
    return legend([(line.label, line.color) for line in lines]) + chart


CHARTS = {"fraud_feature_bars": fraud_feature_bars, "fraud_size_curve": fraud_size_curve, "threshold_curve": threshold_curve,
          "fraud_histogram": fraud_histogram, "fraud_curves": fraud_curves, "fraud_r2": fraud_r2,
          "digits_distribution": digits_distribution, "xor_convergence": xor_convergence, "eta_sensitivity": eta_sensitivity}


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
