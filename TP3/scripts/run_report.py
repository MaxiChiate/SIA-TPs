#!/usr/bin/env python3
"""Writes report.html into a run directory: validation error, learning curve, confusion matrix, charts and config.

Takes a run directory (results/<date>_<time>_<activation>/); without one, uses the latest run.
`make run` calls it after every run. Standard library only: the charts are inline SVG. Three tabs (summary,
charts, config); every explanation lives behind an (i) button that opens a modal. The full weights and
predictions stay in weights.csv and predictions.csv.
"""

from __future__ import annotations

import argparse
import csv
import html
import itertools
import json
import math
from dataclasses import dataclass
from pathlib import Path

from run_error import RESULTS_DIR, RunError, latest_run, output_columns, run_error

MAX_PLOTTED_SAMPLES = 2000
MAX_PLOTTED_EPOCHS = 1000
MAX_SHOWN_INPUTS = 10  # with more inputs (784 pixels) the x values are left out of tooltips
HISTOGRAM_BINS = 20

WIDTH, HEIGHT = 640, 340
MARGIN_LEFT, MARGIN_RIGHT, MARGIN_TOP, MARGIN_BOTTOM = 60, 16, 16, 44


# One zeta and its prediction. With several outputs each sample becomes one Sample per output, so
# the errors are averaged over samples x outputs, like epochs.csv does.
@dataclass(frozen=True)
class Sample:
    inputs: list[float]
    zeta: float
    prediction: float
    number: int  # 1-based sample number in predictions.csv
    output: int | None  # None with a single output

    @property
    def error(self) -> float:
        return self.zeta - self.prediction


# epochs.csv column suffix -> label; the first one is the curve shown by default
EPOCH_METRICS = {"mse": "MSE", "error": "E", "mae": "MAE", "max_error": "máx |e|"}


@dataclass(frozen=True)
class EpochRecord:
    epoch: int  # 0 is the untrained network
    train: dict[str, float]  # keyed by EPOCH_METRICS
    validation: dict[str, float]
    elapsed: float | None  # seconds spent training so far; None for runs from before elapsed_s existed


@dataclass(frozen=True)
class Snapshot:
    epoch: int
    predictions: list[float]  # aligned with Run.samples


@dataclass(frozen=True)
class Run:
    dir: Path
    config: dict
    samples: list[Sample]
    epochs: list[EpochRecord]  # empty for runs from before epochs.csv existed
    snapshots: list[Snapshot]  # validation predictions at a few epochs; empty for older runs

    @property
    def n_inputs(self) -> int:
        return len(self.samples[0].inputs)

    @property
    def n_outputs(self) -> int:
        return sum(1 for sample in self.samples if sample.number == 1)

    @property
    def n_samples(self) -> int:
        return self.samples[-1].number


@dataclass(frozen=True)
class Scale:
    lo: float
    hi: float
    px_lo: float
    px_hi: float
    log: bool = False  # lo and hi are then exponents of 10

    def __call__(self, value: float) -> float:
        if self.log:
            value = math.log10(value)
        return self.px_lo + (value - self.lo) / (self.hi - self.lo) * (self.px_hi - self.px_lo)


# ---------- loading ----------

def load_samples(run_dir: Path) -> list[Sample]:
    with (run_dir / "predictions.csv").open(newline="") as file:
        reader = csv.DictReader(file)
        names = list(reader.fieldnames or [])
        rows = list(reader)
    outputs = list(zip(output_columns(names, "zeta"), output_columns(names, "prediction")))
    samples = []
    for number, row in enumerate(rows, start=1):
        inputs = [float(value) for key, value in row.items() if key.startswith("x")]
        for (zeta, output), (prediction, _) in outputs:
            samples.append(Sample(inputs, float(row[zeta]), float(row[prediction]), number, output))
    return samples


def load_epochs(run_dir: Path) -> list[EpochRecord]:
    path = run_dir / "epochs.csv"
    if not path.exists():
        return []
    with path.open(newline="") as file:
        rows = list(csv.DictReader(file))
    # Older runs only have some of the metrics
    metrics = [metric for metric in EPOCH_METRICS if rows and f"train_{metric}" in rows[0]]
    return [
        EpochRecord(int(row["epoch"]), {m: float(row[f"train_{m}"]) for m in metrics},
                    {m: float(row[f"validation_{m}"]) for m in metrics},
                    float(row["elapsed_s"]) if "elapsed_s" in row else None)
        for row in rows
    ]


def load_snapshots(run_dir: Path) -> list[Snapshot]:
    path = run_dir / "predictions_by_epoch.csv"
    if not path.exists():
        return []
    with path.open(newline="") as file:
        rows = list(csv.DictReader(file))
    # epoch_<e> with a single output, epoch_<e>_<output> with several; flattened like load_samples
    columns_by_epoch: dict[int, list[str]] = {}
    for key in rows[0] if rows else []:
        if key.startswith("epoch_"):
            epoch = int(key.removeprefix("epoch_").split("_")[0])
            columns_by_epoch.setdefault(epoch, []).append(key)
    return [Snapshot(epoch, [float(row[column]) for row in rows for column in columns])
            for epoch, columns in columns_by_epoch.items()]


def load_run(run_dir: Path) -> Run:
    config = json.loads((run_dir / "config.json").read_text())
    return Run(run_dir, config, load_samples(run_dir), load_epochs(run_dir), load_snapshots(run_dir))


# ---------- metrics ----------

def architecture(run: Run) -> str:
    return "-".join(str(size) for size in [run.n_inputs, *run.config["hidden_layers"], run.n_outputs])


def classification_hits(samples: list[Sample]) -> tuple[int, float] | None:
    """With exactly two distinct zetas, each prediction is classified by the closer one."""
    classes = sorted({sample.zeta for sample in samples})
    if len(classes) != 2:
        return None
    threshold = (classes[0] + classes[1]) / 2
    hits = sum((sample.prediction >= threshold) == (sample.zeta >= threshold) for sample in samples)
    return hits, threshold


def argmax_hits(run: Run) -> int:
    """With several outputs, a sample is a hit when its largest prediction is at its largest zeta."""
    hits = 0
    for start in range(0, len(run.samples), run.n_outputs):
        outputs = run.samples[start:start + run.n_outputs]
        expected = max(outputs, key=lambda sample: sample.zeta)
        predicted = max(outputs, key=lambda sample: sample.prediction)
        hits += expected is predicted
    return hits


def confusion_matrix(run: Run) -> list[list[int]]:
    """Rows are the expected class (largest zeta), columns the predicted one (largest prediction)."""
    size = run.n_outputs
    matrix = [[0] * size for _ in range(size)]
    for start in range(0, len(run.samples), size):
        outputs = run.samples[start:start + size]
        expected = max(range(size), key=lambda k: outputs[k].zeta)
        predicted = max(range(size), key=lambda k: outputs[k].prediction)
        matrix[expected][predicted] += 1
    return matrix


# ---------- svg primitives ----------

def fmt(value: float) -> str:
    return f"{value:.4g}"


def padded_domain(values: list[float]) -> tuple[float, float]:
    lo, hi = min(values), max(values)
    if lo == hi:
        return lo - 1, hi + 1
    pad = (hi - lo) * 0.05
    return lo - pad, hi + pad


def nice_ticks(lo: float, hi: float, count: int = 5) -> list[float]:
    raw_step = (hi - lo) / count
    magnitude = 10 ** math.floor(math.log10(raw_step))
    step = next(m * magnitude for m in (1, 2, 5, 10) if m * magnitude >= raw_step)
    first = math.ceil(lo / step) * step
    return [first + i * step for i in range(int((hi - first) / step) + 1)]


def x_scale(domain: tuple[float, float]) -> Scale:
    return Scale(*domain, MARGIN_LEFT, WIDTH - MARGIN_RIGHT)


def y_scale(domain: tuple[float, float]) -> Scale:
    return Scale(*domain, HEIGHT - MARGIN_BOTTOM, MARGIN_TOP)


def y_ticks(y: Scale) -> list[float]:
    if not y.log:
        return nice_ticks(y.lo, y.hi)
    step = max(1, math.ceil((y.hi - y.lo) / 6))
    return [10.0 ** exponent for exponent in range(math.ceil(y.lo), math.floor(y.hi) + 1, step)]


def axes(x: Scale, y: Scale, x_label: str, y_label: str) -> str:
    """Grid and ticks go in g.ticks, which the zoom redraws; the axis line and labels stay."""
    parts = ['<g class="ticks">']
    for tick in y_ticks(y):
        py = y(tick)
        parts.append(f'<line class="grid" x1="{x.px_lo}" x2="{x.px_hi}" y1="{py:.1f}" y2="{py:.1f}"/>')
        parts.append(f'<text class="tick" x="{x.px_lo - 8}" y="{py:.1f}" text-anchor="end" '
                     f'dominant-baseline="middle">{fmt(tick)}</text>')
    for tick in nice_ticks(x.lo, x.hi):
        px = x(tick)
        parts.append(f'<text class="tick" x="{px:.1f}" y="{y.px_lo + 18}" text-anchor="middle">{fmt(tick)}</text>')
    parts.append("</g>")
    parts.append(f'<line class="axis" x1="{x.px_lo}" x2="{x.px_hi}" y1="{y.px_lo}" y2="{y.px_lo}"/>')
    parts.append(f'<text class="label" x="{(x.px_lo + x.px_hi) / 2}" y="{HEIGHT - 6}" '
                 f'text-anchor="middle">{html.escape(x_label)}</text>')
    parts.append(f'<text class="label" transform="translate(14 {(y.px_lo + y.px_hi) / 2}) rotate(-90)" '
                 f'text-anchor="middle">{html.escape(y_label)}</text>')
    return "".join(parts)


def dot(px: float, py: float, css_class: str, tip: str) -> str:
    # The transparent circle is the hit target, bigger than the visible mark
    return (f'<g data-tip="{html.escape(tip)}"><circle class="hit" cx="{px:.1f}" cy="{py:.1f}" r="9"/>'
            f'<circle class="{css_class}" cx="{px:.1f}" cy="{py:.1f}" r="4"/></g>')


def svg(body: str, title: str) -> str:
    return (f'<svg viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{html.escape(title)}">'
            f'{body}</svg>')


_clip_ids = itertools.count()


def zoomable_svg(frame: str, marks: str, x: Scale, y: Scale, title: str, zoom_x: bool = True) -> str:
    """Drag a box to zoom, double click to reset (ZOOM_SCRIPT). The marks are clipped to the plot area and
    the scales go in data-scales so the script can redraw the ticks; zoom_x=False zooms only y."""
    clip = f"plot-{next(_clip_ids)}"
    top, bottom = min(y.px_lo, y.px_hi), max(y.px_lo, y.px_hi)
    scales = {"x": [x.lo, x.hi, x.px_lo, x.px_hi, x.log] if zoom_x else None,
              "y": [y.lo, y.hi, y.px_lo, y.px_hi, y.log], "xRange": [x.px_lo, x.px_hi]}
    return (f'<svg class="zoomable" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{html.escape(title)}" '
            f'data-scales="{html.escape(json.dumps(scales))}">'
            f'<defs><clipPath id="{clip}"><rect x="{x.px_lo}" y="{top}" width="{x.px_hi - x.px_lo}" '
            f'height="{bottom - top}"/></clipPath></defs>{frame}'
            f'<g class="plot" clip-path="url(#{clip})">{marks}</g>'
            f'<rect class="zoom-box" x="0" y="0" width="0" height="0" style="display: none"/></svg>')


ZOOM_HINT = " Arrastrá para hacer zoom; doble clic para volver."


def info(title: str, body: str) -> str:
    """The (i) button. Its text opens in the page's modal (MODAL_SCRIPT) instead of sitting on the page."""
    if not body.startswith("<"):
        body = f"<p>{body}</p>"
    return (f'<button type="button" class="info" aria-label="Más información: {html.escape(title)}" '
            f'data-title="{html.escape(title)}">i</button><template>{body}</template>')


def card_head(tag: str, title: str, body: str = "") -> str:
    help_button = info(title, body) if body else ""
    return f'<div class="card-head"><{tag}>{html.escape(title)}</{tag}>{help_button}</div>'


def figure(title: str, chart: str, caption: str = "", legend: str = "") -> str:
    return f'<figure>{card_head("h3", title, caption)}{legend}{chart}</figure>'


def legend(items: list[tuple[str, str]]) -> str:
    entries = "".join(f'<span><i class="swatch {css_class}"></i>{html.escape(label)}</span>'
                      for css_class, label in items)
    return f'<div class="legend">{entries}</div>'


# ---------- charts ----------

def plotted(samples: list[Sample]) -> tuple[list[Sample], str]:
    if len(samples) <= MAX_PLOTTED_SAMPLES:
        return samples, ""
    step = math.ceil(len(samples) / MAX_PLOTTED_SAMPLES)
    return samples[::step], f"Se grafica 1 de cada {step} muestras ({len(samples[::step])} de {len(samples)})."


def sample_label(sample: Sample) -> str:
    label = f"muestra {sample.number}"
    if sample.output is not None:
        label += f" · salida {sample.output}"
    if len(sample.inputs) <= MAX_SHOWN_INPUTS:
        label += "\nx = (" + ", ".join(fmt(value) for value in sample.inputs) + ")"
    return label


def sample_tip(sample: Sample) -> str:
    return (f"{sample_label(sample)}\nζ = {fmt(sample.zeta)}\n"
            f"predicción = {fmt(sample.prediction)}\ne = {fmt(sample.error)}")


def prediction_vs_zeta_chart(samples: list[Sample], snapshots: list[Snapshot]) -> str:
    """With snapshots, a slider moves the dots through the epochs; it starts at the last one (final weights)."""
    shown, note = plotted(samples)
    step = math.ceil(len(samples) / len(shown))
    snapshot_values = [value for snapshot in snapshots for value in snapshot.predictions]
    # Same domain for every epoch, so the dots move against fixed axes
    domain = padded_domain([s.zeta for s in samples] + [s.prediction for s in samples] + snapshot_values)
    x, y = x_scale(domain), y_scale(domain)
    diagonal = (f'<line class="reference" x1="{x(domain[0]):.1f}" y1="{y(domain[0]):.1f}" '
                f'x2="{x(domain[1]):.1f}" y2="{y(domain[1]):.1f}"/>')
    dots = "".join(dot(x(s.zeta), y(s.prediction), "series-1", sample_tip(s)) for s in shown)
    chart = zoomable_svg(axes(x, y, "ζ (esperado)", "predicción"), diagonal + f'<g class="snapshot-dots">{dots}</g>',
                         x, y, "Predicción contra valor esperado")
    caption = "La diagonal punteada es la predicción perfecta (predicción = ζ)." + ZOOM_HINT + " " + note
    if not snapshots:
        return figure("Predicción vs. ζ", chart, caption)
    return figure("Predicción vs. ζ por época", snapshot_controls(samples, snapshots, step, y) + chart,
                  caption + " Validación con los pesos de cada época.")


def snapshot_controls(samples: list[Sample], snapshots: list[Snapshot], step: int, y: Scale) -> str:
    last_epoch = snapshots[-1].epoch or 1
    data = {
        "epochs": [snapshot.epoch for snapshot in snapshots],
        "percents": [round(100 * snapshot.epoch / last_epoch) for snapshot in snapshots],
        "mse": [sum((s.zeta - p) ** 2 for s, p in zip(samples, snapshot.predictions)) / len(samples)
                for snapshot in snapshots],
        "zetas": [s.zeta for s in samples[::step]],
        "labels": [sample_label(s) for s in samples[::step]],
        "predictions": [snapshot.predictions[::step] for snapshot in snapshots],
        "y": [y.lo, y.hi, y.px_lo, y.px_hi],
    }
    last = len(snapshots) - 1
    return (f'<div class="snapshot-controls"><button type="button" class="play" aria-label="Reproducir">▶</button>'
            f'<input type="range" min="0" max="{last}" value="{last}" step="1" aria-label="Época">'
            f'<span class="snapshot-label"></span></div>'
            f'<script type="application/json" class="snapshot-data">{json.dumps(data, separators=(",", ":"))}</script>')


def fit_chart(samples: list[Sample]) -> str:
    """Only for one input: the learned function next to the expected one."""
    shown, note = plotted(sorted(samples, key=lambda s: s.inputs[0]))
    x = x_scale(padded_domain([s.inputs[0] for s in samples]))
    y = y_scale(padded_domain([s.zeta for s in samples] + [s.prediction for s in samples]))
    points = " ".join(f"{x(s.inputs[0]):.1f},{y(s.prediction):.1f}" for s in shown)
    line = f'<polyline class="line series-1" points="{points}"/>'
    dots = "".join(dot(x(s.inputs[0]), y(s.zeta), "series-2", sample_tip(s)) for s in shown)
    items = [("series-2", "ζ (esperado)"), ("series-1", "predicción")]
    return figure("Ajuste sobre la entrada", zoomable_svg(axes(x, y, "x1", "salida"), line + dots, x, y, "Ajuste sobre x1"),
                  ZOOM_HINT.strip() + " " + note, legend(items))


def learning_curve_chart(epochs: list[EpochRecord]) -> str:
    """One SVG per metric; the buttons above show one at a time."""
    step = math.ceil(len(epochs) / MAX_PLOTTED_EPOCHS)
    shown = epochs[::step] if epochs[-1] in epochs[::step] else [*epochs[::step], epochs[-1]]
    metrics = list(epochs[0].train)
    buttons = "".join(
        f'<button type="button" data-metric="{metric}" aria-pressed="{str(i == 0).lower()}">'
        f'{html.escape(EPOCH_METRICS[metric])}</button>'
        for i, metric in enumerate(metrics)
    )
    charts = "".join(
        f'<div class="metric-chart" data-metric="{metric}"{"" if i == 0 else " hidden"}>'
        f'{metric_curve(shown, metric)}</div>'
        for i, metric in enumerate(metrics)
    )
    items = [("series-1", "train"), ("series-2", "validación")]
    caption = ("<p>Error después de cada época, con los pesos ya actualizados; la época 0 son los pesos iniciales.</p>"
               "<p><b>train</b> es el error sobre <code>train_dataset</code>, lo que ve el entrenamiento. "
               "<b>validación</b> es sobre muestras que no ve (<code>validation_dataset</code>, o la parte que "
               "<code>validation_split</code> aparta de train): si baja train y sube "
               "validación, hay overfitting.</p>"
               f"<p>{ZOOM_HINT.strip()}</p>"
               + (f"<p>Se grafica 1 de cada {step} épocas.</p>" if step > 1 else ""))
    controls = f'<div class="curve-controls"><div class="segmented">{buttons}</div>{legend(items)}</div>'
    return figure("Curva de aprendizaje", controls + charts, caption)


def metric_curve(shown: list[EpochRecord], metric: str) -> str:
    label = EPOCH_METRICS[metric]
    values = [value for r in shown for value in (r.train[metric], r.validation[metric])]
    positive = [value for value in values if value > 0]
    # Log scale once the error spans more than two orders of magnitude, else the tail is a flat line
    log = bool(positive) and len(positive) == len(values) and max(positive) / min(positive) > 100
    x = x_scale((0, shown[-1].epoch or 1))
    if log:
        y = Scale(math.floor(math.log10(min(positive))), math.ceil(math.log10(max(positive))),
                  HEIGHT - MARGIN_BOTTOM, MARGIN_TOP, log=True)
    else:
        y = y_scale((0, max(values) * 1.05 or 1))

    lines = []
    for css_class, split in (("series-1", "train"), ("series-2", "validation")):
        points = " ".join(f"{x(r.epoch):.1f},{y(getattr(r, split)[metric]):.1f}" for r in shown)
        lines.append(f'<polyline class="line {css_class}" points="{points}"/>')

    # One invisible column per plotted epoch carries the tooltip
    slot = (x.px_hi - x.px_lo) / max(len(shown) - 1, 1)
    hits = "".join(
        f'<rect class="hit" x="{x(r.epoch) - slot / 2:.1f}" y="{MARGIN_TOP}" width="{slot:.1f}" '
        f'height="{y.px_lo - MARGIN_TOP:.1f}" data-tip="{html.escape(epoch_tip(r, metric))}"/>'
        for r in shown
    )
    y_label = f"{label} (escala log)" if log else label
    return zoomable_svg(axes(x, y, "época", y_label), "".join(lines) + hits, x, y,
                        f"{label} de train y validación por época")


def epoch_tip(record: EpochRecord, metric: str) -> str:
    label = EPOCH_METRICS[metric]
    return (f"época {record.epoch}\ntrain: {label} {fmt(record.train[metric])}\n"
            f"validación: {label} {fmt(record.validation[metric])}")


def error_histogram_chart(samples: list[Sample]) -> str:
    errors = [s.error for s in samples]
    lo, hi = min(errors), max(errors)
    if lo == hi:
        lo, hi = lo - 1, hi + 1
    width = (hi - lo) / HISTOGRAM_BINS
    counts = [0] * HISTOGRAM_BINS
    for error in errors:
        counts[min(int((error - lo) / width), HISTOGRAM_BINS - 1)] += 1

    x = x_scale((lo, hi))
    y = y_scale((0, max(counts) * 1.05))
    bars = []
    for i, count in enumerate(counts):
        if count == 0:
            continue
        left, right = x(lo + i * width) + 1, x(lo + (i + 1) * width) - 1  # 2px gap between bars
        top = y(count)
        tip = f"e ∈ [{fmt(lo + i * width)}, {fmt(lo + (i + 1) * width)})\n{count} muestras"
        bars.append(f'<g data-tip="{html.escape(tip)}"><rect class="hit" x="{left:.1f}" y="{MARGIN_TOP}" '
                    f'width="{right - left:.1f}" height="{y.px_lo - MARGIN_TOP:.1f}"/>'
                    f'<path class="series-1" d="{bar_path(left, right, top, y.px_lo)}"/></g>')
    zero = (f'<line class="reference" x1="{x(0):.1f}" x2="{x(0):.1f}" y1="{MARGIN_TOP}" y2="{y.px_lo}"/>'
            if lo < 0 < hi else "")
    return figure("Distribución del error", svg(axes(x, y, "e = ζ − predicción", "muestras") + zero + "".join(bars),
                                                "Histograma del error por muestra"),
                  "Error de cada muestra de validación; la línea punteada es e = 0.")


def bar_path(left: float, right: float, top: float, base: float) -> str:
    """Rounded at the data end (top), square at the baseline."""
    radius = min(4, (right - left) / 2, base - top)
    return (f"M{left:.1f},{base:.1f} V{top + radius:.1f} Q{left:.1f},{top:.1f} {left + radius:.1f},{top:.1f} "
            f"H{right - radius:.1f} Q{right:.1f},{top:.1f} {right:.1f},{top + radius:.1f} V{base:.1f} Z")


# ---------- page sections ----------

def stat(label: str, value: str, info_body: str, sub: str = "", accent: bool = False) -> str:
    sub_html = f'<div class="stat-sub">{sub}</div>' if sub else ""
    css = "stat accent" if accent else "stat"
    return (f'<div class="{css}"><div class="stat-label">{html.escape(label)}{info(label, info_body)}</div>'
            f'<div class="stat-value">{value}</div>{sub_html}</div>')


RESIDUAL = "<p><b>e = ζ − O</b>: error de una muestra, lo esperado menos lo que da la red.</p>"

STAT_INFO = {
    "energy": RESIDUAL + "<p><b>E = ½·Σ e²</b>: la función que minimiza el entrenamiento; Δw = −η·∂E/∂w sale de "
                         "derivarla. El ½ cancela el 2 de la derivada. Crece con la cantidad de muestras.</p>",
    "mse": RESIDUAL + "<p><b>MSE = Σ e² / N = 2E / N</b>: E promediado por muestra, así que se puede comparar entre "
                      "datasets de distinto tamaño (train vs. validación). Con varias salidas, N cuenta "
                      "muestras × salidas.</p>",
    "mae": "<p><b>MAE = Σ |e| / N</b>: error medio en las unidades de ζ; pesa menos los errores grandes que el MSE.</p>",
    "max_error": "<p><b>máx |e|</b>: el error de la peor muestra.</p>",
}


def accuracy_stat(run: Run, error: RunError) -> str | None:
    """Hits by argmax with several outputs, by the closer of the two zetas otherwise; None for regression."""
    if run.n_outputs > 1:
        count, total = argmax_hits(run), run.n_samples
        body = ("<p>Una muestra es un acierto cuando la salida más alta de la red coincide con la ζ más alta "
                "(argmax).</p>")
    else:
        hits = classification_hits(run.samples)
        if hits is None:
            return None
        (count, threshold), total = hits, error.n_samples
        body = (f"<p>Con dos valores de ζ, cada predicción se clasifica por el más cercano: el umbral es "
                f"{fmt(threshold)}.</p>")
    return stat("Aciertos", f"{100 * count / total:.1f}%", body, sub=f"{count} de {total} muestras", accent=True)


def stats_section(run: Run, error: RunError) -> str:
    tiles = [
        accuracy_stat(run, error),
        stat("MSE", fmt(error.mse), STAT_INFO["mse"]),
        stat("MAE", fmt(error.mae), STAT_INFO["mae"]),
        stat("máx |e|", fmt(error.max_abs_error), STAT_INFO["max_error"]),
        stat("E = ½·Σ(ζ−O)²", fmt(error.energy), STAT_INFO["energy"]),
        stat("Muestras", str(run.n_samples),
             "<p>Muestras de validación, medidas con los pesos finales (los de la época con menor MSE de train).</p>"),
    ]
    return f'<section class="stats">{"".join(tile for tile in tiles if tile)}</section>'


def share(count: int, total: int) -> str:
    return f"{100 * count / total:.1f}%" if total else "–"


def confusion_cell(count: int, row_total: int, is_diagonal: bool) -> str:
    """Shade by the share of the row, so each class reads the same whatever its size."""
    intensity = round(80 * count / row_total) if row_total else 0
    color = "--series-1" if is_diagonal else "--series-2"
    style = f' style="background: color-mix(in srgb, var({color}) {intensity}%, transparent)"' if count else ""
    return f"<td{style}>{count}</td>"


def confusion_section(run: Run) -> str:
    """Per-class hits (recall) and precision; a class with no samples shows –, e.g. digits.csv has no 8."""
    matrix = confusion_matrix(run)
    size = run.n_outputs
    row_totals = [sum(row) for row in matrix]
    column_totals = [sum(matrix[i][j] for i in range(size)) for j in range(size)]
    rows = []
    for i, row in enumerate(matrix):
        cells = "".join(confusion_cell(count, row_totals[i], i == j) for j, count in enumerate(row))
        rows.append(f'<tr><th>{i}</th>{cells}<td>{row_totals[i]}</td><td>{share(row[i], row_totals[i])}</td></tr>')
    precision = "".join(f"<td>{share(matrix[j][j], column_totals[j])}</td>" for j in range(size))
    header = "".join(f"<th>{j}</th>" for j in range(size))
    body = "".join(rows)
    footer = f'<tr><th>precisión</th>{precision}<td></td><td></td></tr>'
    table_html = (f'<div class="table-wrap"><table class="data confusion"><thead><tr><th>real ↓ · predicho →</th>{header}'
                  f'<th>muestras</th><th>aciertos</th></tr></thead><tbody>{body}{footer}</tbody></table></div>')
    note = ('<p>Cada fila es la clase real (ζ más grande) y cada columna la que predijo la red '
            '(salida más grande).</p>'
            '<p><b>Aciertos</b> = diagonal / muestras de la fila (recall).</p>'
            '<p><b>Precisión</b> = diagonal / predichas en la columna.</p>'
            '<p>El color es la parte de la fila: azul en la diagonal, naranja fuera de ella.</p>')
    return f'<section class="card">{card_head("h2", "Matriz de confusión", note)}{table_html}</section>'


def validation_source(config: dict) -> str:
    """Where the validation samples come from: its own file, or a share of train_dataset."""
    if "validation_dataset" in config:
        return config["validation_dataset"]
    return f"{100 * config['validation_split']:g}% de {config['train_dataset']} (split_seed {config['split_seed']})"


def training_time(epochs: list[EpochRecord]) -> str | None:
    if not epochs or epochs[-1].elapsed is None:
        return None
    total = epochs[-1].elapsed
    per_epoch = total / max(epochs[-1].epoch, 1)
    return f"{total:.2f} s ({1000 * per_epoch:.3g} ms por época)"


def chips(run: Run) -> str:
    """The run at a glance, next to the title."""
    trained = run.epochs[-1].epoch if run.epochs else run.config["epochs"]
    items = [architecture(run), run.config["activation"], f"η {run.config['eta']}", f"{trained} épocas"]
    if run.epochs and run.epochs[-1].elapsed is not None:
        items.append(f"{run.epochs[-1].elapsed:.1f} s")
    return f'<div class="chips">{"".join(f"<span>{html.escape(item)}</span>" for item in items)}</div>'


FILES_INFO = (
    "<p>Los pesos y las predicciones completos no están en esta página; están en la carpeta de la corrida:</p>"
    "<ul><li><code>config.json</code>: copia exacta del config con el que se corrió.</li>"
    "<li><code>weights.csv</code>: una fila por peso (capa, neurona, peso, inicial, final; el peso 0 es el bias).</li>"
    "<li><code>predictions.csv</code>: por muestra de validación, entradas, ζ y predicción.</li>"
    "<li><code>epochs.csv</code>: error de train y validación por época.</li>"
    "<li><code>predictions_by_epoch.csv</code>: predicciones de validación en 11 épocas.</li></ul>"
)


def config_section(run: Run) -> str:
    rows = [("Arquitectura", architecture(run)), *((key, json.dumps(value)) for key, value in run.config.items())]
    time = training_time(run.epochs)
    if time is not None:
        rows.insert(1, ("Tiempo de entrenamiento", time))
    body = "".join(f"<tr><th>{html.escape(key)}</th><td>{html.escape(str(value))}</td></tr>" for key, value in rows)
    return (f'<section class="card">{card_head("h2", "Configuración", FILES_INFO)}'
            f'<table class="config">{body}</table></section>')


def charts_section(run: Run) -> str:
    charts = [prediction_vs_zeta_chart(run.samples, run.snapshots), error_histogram_chart(run.samples)]
    if run.n_inputs == 1 and run.n_outputs == 1:
        charts.insert(1, fit_chart(run.samples))
    return f'<div class="charts">{"".join(charts)}</div>'


def summary_section(run: Run, error: RunError) -> str:
    parts = [stats_section(run, error)]
    if run.epochs:
        parts.append(learning_curve_chart(run.epochs))
    if run.n_outputs > 1:
        parts.append(confusion_section(run))
    return "".join(parts)


def tabbed(tabs: list[tuple[str, str, str]]) -> str:
    """(key, label, html) per tab. The first one shows until TAB_SCRIPT restores the last one picked."""
    buttons = "".join(
        f'<button type="button" role="tab" data-tab="{key}" aria-selected="{str(i == 0).lower()}" '
        f'tabindex="{0 if i == 0 else -1}">{label}</button>' for i, (key, label, _) in enumerate(tabs))
    panels = "".join(
        f'<div class="panel" role="tabpanel" data-tab="{key}"{"" if i == 0 else " hidden"}>{content}</div>'
        for i, (key, _, content) in enumerate(tabs))
    return f'<nav class="tabs" role="tablist">{buttons}</nav>{panels}'


STYLE = """
:root {
  color-scheme: light;
  --surface: #f4f5f7; --surface-2: #ffffff; --border: #e3e5e9;
  --text-primary: #14161a; --text-secondary: #4b5058; --text-muted: #7b818b;
  --grid: #eceef1; --series-1: #2a78d6; --series-2: #eb6834; --accent-soft: #eaf2fd; --accent-border: #c5dbf6;
  --shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
}
* { box-sizing: border-box; }
[hidden] { display: none !important; }
body { margin: 0; background: var(--surface); color: var(--text-primary);
       font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 1140px; margin: 0 auto; padding: 28px 16px 56px; }
h1 { font-size: 24px; margin: 0 0 4px; letter-spacing: -0.01em; }
h2 { font-size: 17px; margin: 32px 0 12px; }
h3 { font-size: 14px; margin: 0; color: var(--text-secondary); font-weight: 600; }
code { font-family: ui-monospace, monospace; font-size: 12px; }
.subtitle { color: var(--text-muted); margin: 0; font-family: ui-monospace, monospace; font-size: 13px; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.chips span { background: var(--surface-2); border: 1px solid var(--border); border-radius: 999px; padding: 2px 12px;
              font-size: 13px; color: var(--text-secondary); font-variant-numeric: tabular-nums; }

.tabs { display: flex; gap: 4px; margin: 24px 0 20px; border-bottom: 1px solid var(--border); }
.tabs button { font: inherit; font-weight: 500; padding: 8px 16px; border: 0; border-bottom: 2px solid transparent;
               margin-bottom: -1px; background: transparent; color: var(--text-secondary); cursor: pointer; }
.tabs button:hover { color: var(--text-primary); }
.tabs button[aria-selected="true"] { color: var(--series-1); border-bottom-color: var(--series-1); }
.panel { display: grid; gap: 20px; }

.card, figure { margin: 0; background: var(--surface-2); border: 1px solid var(--border); border-radius: 12px;
                padding: 16px; box-shadow: var(--shadow); }
.card-head { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.card-head h2 { margin: 0; font-size: 16px; }
.info { flex: none; width: 20px; height: 20px; padding: 0; border: 1px solid var(--border); border-radius: 50%;
        background: var(--surface-2); color: var(--text-muted); font: italic 600 12px/1 Georgia, serif; cursor: pointer; }
.info:hover, .info:focus-visible { color: var(--series-1); border-color: var(--series-1); background: var(--accent-soft); outline: 0; }

.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }
.stat { background: var(--surface-2); border: 1px solid var(--border); border-radius: 12px; padding: 14px 16px;
        box-shadow: var(--shadow); }
.stat.accent { background: var(--accent-soft); border-color: var(--accent-border); }
.stat-label { display: flex; align-items: center; gap: 6px; color: var(--text-secondary); font-size: 13px; }
.stat-value { font-size: 26px; font-weight: 650; font-variant-numeric: tabular-nums; letter-spacing: -0.01em; }
.stat.accent .stat-value { color: var(--series-1); }
.stat-sub { color: var(--text-muted); font-size: 12px; font-variant-numeric: tabular-nums; }

.charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 460px), 1fr)); gap: 20px; }
.note { color: var(--text-muted); font-size: 13px; margin-top: 6px; }
svg { width: 100%; height: auto; display: block; }
svg .grid { stroke: var(--grid); stroke-width: 1; }
svg .axis { stroke: var(--text-muted); stroke-width: 1; }
svg .tick { fill: var(--text-muted); font-size: 11px; font-variant-numeric: tabular-nums; }
svg .label { fill: var(--text-secondary); font-size: 12px; }
svg .reference { stroke: var(--text-muted); stroke-width: 1.5; stroke-dasharray: 4 4; }
svg .hit { fill: transparent; }
svg circle.series-1, svg path.series-1 { fill: var(--series-1); }
svg circle.series-2 { fill: var(--series-2); }
svg circle.series-1, svg circle.series-2 { stroke: var(--surface-2); stroke-width: 1.5; }
svg .line { fill: none; stroke: var(--series-1); stroke-width: 2; stroke-linejoin: round; }
svg .line.series-2 { stroke: var(--series-2); }
svg rect.hit[data-tip]:hover { fill: var(--grid); opacity: 0.5; }
svg g[data-tip]:hover circle:not(.hit), svg g[data-tip]:hover path { stroke: var(--text-primary); stroke-width: 1.5; }
.legend { display: flex; gap: 16px; font-size: 13px; color: var(--text-secondary); margin-bottom: 4px; }
.swatch { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; vertical-align: -1px; }
.swatch.series-1 { background: var(--series-1); } .swatch.series-2 { background: var(--series-2); }
table { border-collapse: collapse; font-size: 13px; font-variant-numeric: tabular-nums; }
th, td { padding: 4px 12px 4px 0; text-align: left; border-bottom: 1px solid var(--border); }
.config { width: 100%; }
.config th { color: var(--text-secondary); font-weight: 500; width: 40%; padding: 6px 12px 6px 0; }
.config td { font-family: ui-monospace, monospace; }
.config tr:last-child th, .config tr:last-child td { border-bottom: 0; }
.data td { text-align: right; } .data th { text-align: right; color: var(--text-secondary); }
.table-wrap { overflow: auto; max-height: 420px; border: 1px solid var(--border); border-radius: 8px; }
.table-wrap table { width: 100%; }
.table-wrap th, .table-wrap td { padding: 5px 12px; }
.table-wrap thead th { position: sticky; top: 0; background: var(--surface-2); }
.curve-controls { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 4px; }
.curve-controls .legend { margin: 0; }
.snapshot-controls { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; font-size: 13px;
                     color: var(--text-secondary); font-variant-numeric: tabular-nums; }
.snapshot-controls input { flex: 1; min-width: 0; accent-color: var(--series-1); }
.snapshot-controls .play { font: inherit; width: 28px; height: 24px; border: 1px solid var(--border); border-radius: 6px;
                           background: transparent; color: var(--text-primary); cursor: pointer; }
.snapshot-label { min-width: 210px; }
svg .snapshot-dots circle { transition: cy 0.35s ease; }
svg.zoomable { cursor: crosshair; touch-action: none; user-select: none; }
svg .zoom-box { fill: var(--series-1); fill-opacity: 0.12; stroke: var(--series-1); stroke-width: 1; }
.segmented { display: inline-flex; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; }
.segmented button { font: inherit; font-size: 13px; padding: 3px 10px; border: 0; background: transparent;
                    color: var(--text-secondary); cursor: pointer; }
.segmented button + button { border-left: 1px solid var(--border); }
.segmented button[aria-pressed="true"] { background: var(--series-1); color: #fff; }
#tip { position: fixed; pointer-events: none; background: var(--text-primary); color: var(--surface-2);
       padding: 6px 8px; border-radius: 6px; font-size: 12px; white-space: pre; z-index: 10; }

dialog.modal { width: min(540px, calc(100vw - 32px)); padding: 0; border: 0; border-radius: 14px;
               background: var(--surface-2); color: var(--text-primary); box-shadow: 0 24px 64px rgba(16, 24, 40, 0.28); }
dialog.modal::backdrop { background: rgba(16, 24, 40, 0.4); }
.modal-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 16px 20px 0; }
.modal-title { font-size: 17px; margin: 0; color: var(--text-primary); }
.modal-close { font: inherit; font-size: 22px; line-height: 1; width: 30px; height: 30px; border: 0; border-radius: 6px;
               background: transparent; color: var(--text-muted); cursor: pointer; }
.modal-close:hover { background: var(--surface); color: var(--text-primary); }
.modal-body { padding: 8px 20px 20px; color: var(--text-secondary); font-size: 14px; }
.modal-body p { margin: 8px 0; } .modal-body ul { margin: 8px 0; padding-left: 20px; } .modal-body li { margin: 4px 0; }
"""

# Box zoom for the charts made with zoomable_svg. Every mark under g.plot keeps its unzoomed coordinates in
# el._base; a zoom is an affine map per axis from those to the plot area, and the ticks are redrawn for the
# zoomed domain. Rects are only moved sideways: they are full-height hover columns.
ZOOM_SCRIPT = """
const ZOOM_ATTRS = {circle: [["cx", "x"], ["cy", "y"]], line: [["x1", "x"], ["x2", "x"], ["y1", "y"], ["y2", "y"]],
                    rect: [["x", "x"], ["width", "w"]]};
const IDENTITY = {ax: 1, bx: 0, ay: 1, by: 0};

function baseOf(el) {
  if (!el._base) {
    el._base = {};
    if (el.hasAttribute("points")) el._base.points = el.getAttribute("points");
    for (const [attr] of ZOOM_ATTRS[el.tagName] || []) el._base[attr] = Number(el.getAttribute(attr));
  }
  return el._base;
}

function place(el, zoom) {
  const base = baseOf(el);
  if (base.points !== undefined) {
    el.setAttribute("points", base.points.split(" ").map((pair) => {
      const [px, py] = pair.split(",").map(Number);
      return `${(zoom.ax * px + zoom.bx).toFixed(1)},${(zoom.ay * py + zoom.by).toFixed(1)}`;
    }).join(" "));
    return;
  }
  for (const [attr, axis] of ZOOM_ATTRS[el.tagName] || []) {
    const value = axis === "x" ? zoom.ax * base[attr] + zoom.bx : axis === "y" ? zoom.ay * base[attr] + zoom.by
                                                                              : zoom.ax * base[attr];
    el.setAttribute(attr, value.toFixed(1));
  }
}

// For code that moves marks (the snapshot slider): value is unzoomed, the current zoom is applied on top
function setBase(el, attr, value) {
  baseOf(el)[attr] = value;
  const svg = el.closest("svg.zoomable");
  place(el, (svg && svg._zoom) || IDENTITY);
}

const fmtTick = (value) => Number(value.toPrecision(4)).toString();

function niceTicks(lo, hi, count = 5) {
  const raw = (hi - lo) / count;
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 5, 10].map((m) => m * magnitude).find((s) => s >= raw);
  const ticks = [];
  for (let k = Math.ceil(lo / step); k * step <= hi + step * 1e-9; k++) ticks.push(Number((k * step).toPrecision(12)));
  return ticks;
}

// [lo, hi] are exponents of 10 on a log scale; under one decade there are no powers left, so linear ticks
function scaleTicks(lo, hi, log) {
  if (!log) return niceTicks(lo, hi);
  const step = Math.max(1, Math.ceil((hi - lo) / 6));
  const powers = [];
  for (let e = Math.ceil(lo); e <= Math.floor(hi); e += step) powers.push(10 ** e);
  return powers.length >= 2 ? powers : niceTicks(10 ** lo, 10 ** hi).filter((value) => value > 0);
}

function drawTicks(svg, x, y) {
  const NS = "http://www.w3.org/2000/svg";
  const group = svg.querySelector(".ticks");
  group.replaceChildren();
  const add = (tag, attrs, text) => {
    const el = document.createElementNS(NS, tag);
    for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value);
    if (text !== undefined) el.textContent = text;
    group.appendChild(el);
  };
  const toPx = ([lo, hi, pxLo, pxHi, log], value) => pxLo + ((log ? Math.log10(value) : value) - lo) / (hi - lo) * (pxHi - pxLo);
  const [left, right] = JSON.parse(svg.dataset.scales).xRange;
  for (const tick of scaleTicks(y[0], y[1], y[4])) {
    const py = toPx(y, tick).toFixed(1);
    add("line", {class: "grid", x1: left, x2: right, y1: py, y2: py});
    add("text", {class: "tick", x: left - 8, y: py, "text-anchor": "end", "dominant-baseline": "middle"}, fmtTick(tick));
  }
  if (!x) return;
  for (const tick of scaleTicks(x[0], x[1], x[4])) {
    add("text", {class: "tick", x: toPx(x, tick).toFixed(1), y: y[2] + 18, "text-anchor": "middle"}, fmtTick(tick));
  }
}

function applyZoom(svg, zoom) {
  svg._zoom = zoom;
  svg.querySelectorAll(".plot circle, .plot line, .plot rect, .plot polyline, .plot polygon").forEach((el) => place(el, zoom));
}

document.querySelectorAll("svg.zoomable").forEach((svg) => {
  const scales = JSON.parse(svg.dataset.scales);
  const box = svg.querySelector(".zoom-box");
  const ticksHtml = svg.querySelector(".ticks").innerHTML;
  const [left, right] = scales.xRange;
  const [bottom, top] = [scales.y[2], scales.y[3]];
  const toSvg = (event) => new DOMPoint(event.clientX, event.clientY).matrixTransform(svg.getScreenCTM().inverse());
  const clamp = (value, lo, hi) => Math.min(Math.max(value, lo), hi);
  let start = null;

  svg.addEventListener("pointerdown", (event) => {
    const point = toSvg(event);
    if (point.x < left || point.x > right || point.y < top || point.y > bottom) return;
    start = point;
    svg.setPointerCapture(event.pointerId);
  });
  svg.addEventListener("pointermove", (event) => {
    if (!start) return;
    const point = toSvg(event);
    const x0 = scales.x ? Math.min(start.x, clamp(point.x, left, right)) : left;
    const x1 = scales.x ? Math.max(start.x, clamp(point.x, left, right)) : right;
    const y0 = Math.min(start.y, clamp(point.y, top, bottom)), y1 = Math.max(start.y, clamp(point.y, top, bottom));
    Object.entries({x: x0, y: y0, width: x1 - x0, height: y1 - y0}).forEach(([key, value]) => box.setAttribute(key, value));
    box.style.display = "";
  });
  svg.addEventListener("pointerup", () => {
    if (!start) return;
    start = null;
    box.style.display = "none";
    const [x0, y0, w, h] = ["x", "y", "width", "height"].map((key) => Number(box.getAttribute(key)));
    if (h < 5 || (scales.x && w < 5)) return;
    // The box is in zoomed pixels: back to unzoomed ones, then the map that stretches them over the plot area
    const zoom = svg._zoom || IDENTITY;
    const bx0 = (x0 - zoom.bx) / zoom.ax, bx1 = (x0 + w - zoom.bx) / zoom.ax;
    const by0 = (y0 - zoom.by) / zoom.ay, by1 = (y0 + h - zoom.by) / zoom.ay;
    const ax = scales.x ? (right - left) / (bx1 - bx0) : 1, ay = (bottom - top) / (by1 - by0);
    applyZoom(svg, {ax, bx: scales.x ? left - ax * bx0 : 0, ay, by: top - ay * by0});
    // Domain of the zoomed area, read off the unzoomed scales
    const at = ([lo, hi, pxLo, pxHi, log], px) => [lo + (px - pxLo) / (pxHi - pxLo) * (hi - lo), log];
    const x = scales.x && [at(scales.x, bx0)[0], at(scales.x, bx1)[0], left, right, scales.x[4]];
    const y = [at(scales.y, by1)[0], at(scales.y, by0)[0], bottom, top, scales.y[4]];
    drawTicks(svg, x, y);
  });
  svg.addEventListener("dblclick", () => {
    applyZoom(svg, IDENTITY);
    svg.querySelector(".ticks").innerHTML = ticksHtml;
  });
});
"""

MODAL_HTML = """<dialog class="modal" id="info-modal" aria-labelledby="info-modal-title">
<div class="modal-head"><h3 class="modal-title" id="info-modal-title"></h3>
<button type="button" class="modal-close" aria-label="Cerrar">×</button></div>
<div class="modal-body"></div>
</dialog>"""

# Every (i) button (see info()) is followed by a <template> with its text; the click copies it into the one modal
MODAL_SCRIPT = """
const modal = document.getElementById("info-modal");
document.addEventListener("click", (event) => {
  const button = event.target.closest("button.info");
  if (button) {
    modal.querySelector(".modal-title").textContent = button.dataset.title;
    modal.querySelector(".modal-body").replaceChildren(button.nextElementSibling.content.cloneNode(true));
    modal.showModal();
  } else if (event.target === modal || event.target.closest(".modal-close")) {
    modal.close();
  }
});
"""

TAB_SCRIPT = """
// Tabs; the last one picked is remembered so the auto-reload of report_server keeps it
const tabButtons = [...document.querySelectorAll('[role="tab"]')];
function showTab(key) {
  if (!tabButtons.some((button) => button.dataset.tab === key)) return;
  tabButtons.forEach((button) => {
    button.setAttribute("aria-selected", button.dataset.tab === key);
    button.tabIndex = button.dataset.tab === key ? 0 : -1;
  });
  document.querySelectorAll('[role="tabpanel"]').forEach((panel) => { panel.hidden = panel.dataset.tab !== key; });
  try { localStorage.setItem("reportTab", key); } catch (error) {}
}
tabButtons.forEach((button, i) => {
  button.addEventListener("click", () => showTab(button.dataset.tab));
  button.addEventListener("keydown", (event) => {
    const step = {ArrowRight: 1, ArrowLeft: -1}[event.key];
    if (!step) return;
    const next = tabButtons[(i + step + tabButtons.length) % tabButtons.length];
    showTab(next.dataset.tab);
    next.focus();
  });
});
try { const saved = localStorage.getItem("reportTab"); if (saved) showTab(saved); } catch (error) {}
"""

SCRIPT = ZOOM_SCRIPT + MODAL_SCRIPT + TAB_SCRIPT + """
// Learning curve metric; remembered so the auto-reload of report_server keeps it
function showMetric(metric) {
  const buttons = document.querySelectorAll(".segmented button");
  if (![...buttons].some((button) => button.dataset.metric === metric)) return;
  buttons.forEach((button) => button.setAttribute("aria-pressed", button.dataset.metric === metric));
  document.querySelectorAll(".metric-chart").forEach((chart) => { chart.hidden = chart.dataset.metric !== metric; });
  try { localStorage.setItem("curveMetric", metric); } catch (error) {}
}
document.querySelectorAll(".segmented button").forEach((button) => {
  button.addEventListener("click", () => showMetric(button.dataset.metric));
});
try { const saved = localStorage.getItem("curveMetric"); if (saved) showMetric(saved); } catch (error) {}

// Prediction vs zeta through the epochs: the slider picks a snapshot and moves every dot's y
document.querySelectorAll(".snapshot-data").forEach((script) => {
  const data = JSON.parse(script.textContent);
  const figure = script.closest("figure");
  const slider = figure.querySelector("input[type=range]");
  const label = figure.querySelector(".snapshot-label");
  const play = figure.querySelector(".play");
  const groups = figure.querySelectorAll(".snapshot-dots g");
  const [lo, hi, pxLo, pxHi] = data.y;
  const toPx = (value) => pxLo + (value - lo) / (hi - lo) * (pxHi - pxLo);
  const fmt = (value) => Number(value.toPrecision(4)).toString();

  function show(k) {
    slider.value = k;
    label.textContent = `época ${data.epochs[k]} (${data.percents[k]}%) · MSE ${fmt(data.mse[k])}`;
    groups.forEach((group, i) => {
      const prediction = data.predictions[k][i];
      group.querySelectorAll("circle").forEach((circle) => setBase(circle, "cy", toPx(prediction)));
      group.dataset.tip = `${data.labels[i]}\n` +
        `ζ = ${fmt(data.zetas[i])}\npredicción = ${fmt(prediction)}\ne = ${fmt(data.zetas[i] - prediction)}\n` +
        `época ${data.epochs[k]}`;
    });
  }

  let timer = null;
  function stop() { clearInterval(timer); timer = null; play.textContent = "▶"; }
  play.addEventListener("click", () => {
    if (timer) return stop();
    if (Number(slider.value) === data.epochs.length - 1) show(0);
    play.textContent = "❚❚";
    timer = setInterval(() => {
      const next = Number(slider.value) + 1;
      if (next >= data.epochs.length) return stop();
      show(next);
    }, 700);
  });
  slider.addEventListener("input", () => { stop(); show(Number(slider.value)); });
  show(Number(slider.value));
});

const tip = document.getElementById("tip");
document.addEventListener("pointerover", (event) => {
  const target = event.target.closest("[data-tip]");
  tip.hidden = !target;
  if (target) tip.textContent = target.dataset.tip;
});
document.addEventListener("pointermove", (event) => {
  tip.style.left = Math.min(event.clientX + 12, innerWidth - tip.offsetWidth - 8) + "px";
  tip.style.top = event.clientY + 12 + "px";
});
"""


def render(run: Run) -> str:
    error = run_error([(s.zeta, s.prediction) for s in run.samples])
    title = f"{run.config['activation']} {architecture(run)}"
    tabs = [("summary", "Resumen", summary_section(run, error)), ("charts", "Gráficos", charts_section(run)),
            ("config", "Configuración", config_section(run))]
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Corrida {html.escape(title)}</title>
<style>{STYLE}</style>
</head>
<body>
<main>
<h1>Corrida {html.escape(title)}</h1>
<p class="subtitle">{html.escape(run.dir.name)} · validación sobre {html.escape(validation_source(run.config))}</p>
{chips(run)}
{tabbed(tabs)}
</main>
<div id="tip" hidden></div>
{MODAL_HTML}
<script>{SCRIPT}</script>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path, nargs="?", help="run directory (default: latest)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dir = args.run_dir or latest_run(RESULTS_DIR)
    report = run_dir / "report.html"
    report.write_text(render(load_run(run_dir)))
    print(f"report  -> {report}")


if __name__ == "__main__":
    main()
