#!/usr/bin/env python3
"""Writes report.html into a run directory: config, learning curve, validation error, charts and raw results.

Takes a run directory (results/<date>_<time>_<activation>/); without one, uses the latest run.
`make run` calls it after every run. Standard library only: the charts are inline SVG.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import math
from dataclasses import dataclass
from pathlib import Path

from run_error import RESULTS_DIR, RunError, latest_run, output_columns, run_error

MAX_PLOTTED_SAMPLES = 2000
MAX_PLOTTED_EPOCHS = 1000
MAX_TABLE_ROWS = 10000
MAX_SHOWN_INPUTS = 10  # with more inputs (784 pixels) the x values are left out of tooltips and tables
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


@dataclass(frozen=True)
class Weight:
    layer: int
    neuron: int
    index: int  # 0 is the bias
    initial: float
    final: float


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
    weights: list[Weight]
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


def load_weights(run_dir: Path) -> list[Weight]:
    with (run_dir / "weights.csv").open(newline="") as file:
        return [
            Weight(int(row["layer"]), int(row["neuron"]), int(row["weight"]), float(row["initial"]),
                   float(row["final"]))
            for row in csv.DictReader(file)
        ]


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
    return Run(run_dir, config, load_samples(run_dir), load_weights(run_dir), load_epochs(run_dir),
               load_snapshots(run_dir))


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
    parts = []
    for tick in y_ticks(y):
        py = y(tick)
        parts.append(f'<line class="grid" x1="{x.px_lo}" x2="{x.px_hi}" y1="{py:.1f}" y2="{py:.1f}"/>')
        parts.append(f'<text class="tick" x="{x.px_lo - 8}" y="{py:.1f}" text-anchor="end" '
                     f'dominant-baseline="middle">{fmt(tick)}</text>')
    for tick in nice_ticks(x.lo, x.hi):
        px = x(tick)
        parts.append(f'<text class="tick" x="{px:.1f}" y="{y.px_lo + 18}" text-anchor="middle">{fmt(tick)}</text>')
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


def figure(title: str, chart: str, caption: str = "", legend: str = "") -> str:
    caption_html = f"<figcaption>{caption}</figcaption>" if caption else ""
    return f'<figure><h3>{html.escape(title)}</h3>{legend}{chart}{caption_html}</figure>'


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
    chart = svg(axes(x, y, "ζ (esperado)", "predicción") + diagonal + f'<g class="snapshot-dots">{dots}</g>',
                "Predicción contra valor esperado")
    caption = "La diagonal punteada es la predicción perfecta (predicción = ζ). " + note
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
    return figure("Ajuste sobre la entrada", svg(axes(x, y, "x1", "salida") + line + dots, "Ajuste sobre x1"),
                  note, legend(items))


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
    caption = ("Error después de cada época, con los pesos ya actualizados; la época 0 son los pesos iniciales."
               + (f" Se grafica 1 de cada {step} épocas." if step > 1 else ""))
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
    return svg(axes(x, y, "época", y_label) + "".join(lines) + hits, f"{label} de train y validación por época")


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

def stat(label: str, value: str) -> str:
    return f'<div class="stat"><div class="stat-label">{label}</div><div class="stat-value">{value}</div></div>'


def stats_section(run: Run, error: RunError) -> str:
    tiles = [
        stat("Muestras", str(run.n_samples)),
        stat("E = ½·Σ(ζ−O)²", fmt(error.energy)),
        stat("MSE", fmt(error.mse)),
        stat("MAE", fmt(error.mae)),
        stat("máx |e|", fmt(error.max_abs_error)),
    ]
    if run.n_outputs > 1:
        count = argmax_hits(run)
        tiles.append(stat("Aciertos (argmax)", f"{count}/{run.n_samples} · {100 * count / run.n_samples:.1f}%"))
        return f'<section class="stats">{"".join(tiles)}</section>'
    hits = classification_hits(run.samples)
    if hits is not None:
        count, threshold = hits
        tiles.append(stat(f"Aciertos (umbral {fmt(threshold)})",
                          f"{count}/{error.n_samples} · {100 * count / error.n_samples:.1f}%"))
    return f'<section class="stats">{"".join(tiles)}</section>'


def training_time(epochs: list[EpochRecord]) -> str | None:
    if not epochs or epochs[-1].elapsed is None:
        return None
    total = epochs[-1].elapsed
    per_epoch = total / max(epochs[-1].epoch, 1)
    return f"{total:.2f} s ({1000 * per_epoch:.3g} ms por época)"


def config_section(run: Run) -> str:
    rows = [("Arquitectura", architecture(run)), *((key, json.dumps(value)) for key, value in run.config.items())]
    time = training_time(run.epochs)
    if time is not None:
        rows.insert(1, ("Tiempo de entrenamiento", time))
    body = "".join(f"<tr><th>{html.escape(key)}</th><td>{html.escape(str(value))}</td></tr>" for key, value in rows)
    return f'<section><h2>Configuración</h2><table class="config">{body}</table></section>'


def charts_section(run: Run) -> str:
    charts = [prediction_vs_zeta_chart(run.samples, run.snapshots), error_histogram_chart(run.samples)]
    if run.n_inputs == 1 and run.n_outputs == 1:
        charts.insert(1, fit_chart(run.samples))
    if run.epochs:
        charts.insert(0, learning_curve_chart(run.epochs))
    return f'<section><h2>Entrenamiento y validación</h2><div class="charts">{"".join(charts)}</div></section>'


GLOSSARY = [
    ("e = ζ − O", "error de una muestra: lo esperado menos lo que da la red."),
    ("E = ½·Σ e²", "la función que minimiza el entrenamiento; Δw = −η·∂E/∂w sale de derivarla. "
                   "El ½ cancela el 2 de la derivada. Crece con la cantidad de muestras."),
    ("MSE = Σ e² / N = 2E / N", "E promediado por muestra: se puede comparar entre datasets de distinto "
                                "tamaño (train vs. validación)."),
    ("MAE = Σ |e| / N", "error medio en las unidades de ζ; pesa menos los errores grandes."),
    ("máx |e|", "la peor muestra."),
    ("train / validación", "el mismo error medido sobre train_dataset (lo que ve el entrenamiento) o sobre "
                           "validation_dataset (muestras que no ve; si baja train y sube validación, hay overfitting)."),
]


def glossary_section() -> str:
    items = "".join(f"<dt>{html.escape(term)}</dt><dd>{html.escape(text)}</dd>" for term, text in GLOSSARY)
    return f'<section><h2>Qué es cada error</h2><dl class="glossary">{items}</dl></section>'


def table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{html.escape(header)}</th>" for header in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return f'<div class="table-wrap"><table class="data"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def weights_section(run: Run) -> str:
    rows = [[str(w.layer), str(w.neuron), "bias" if w.index == 0 else f"w{w.index}", fmt(w.initial), fmt(w.final),
             fmt(w.final - w.initial)] for w in run.weights]
    return (f'<section><h2>Pesos ({len(run.weights)})</h2>'
            f'{table(["capa", "neurona", "peso", "inicial", "final", "Δ"], rows)}</section>')


def predictions_section(run: Run) -> str:
    shown = run.samples[:MAX_TABLE_ROWS]
    show_inputs = run.n_inputs <= MAX_SHOWN_INPUTS
    show_outputs = run.n_outputs > 1
    headers = [*(["muestra", "salida"] if show_outputs else []),
               *(f"x{j + 1}" for j in range(run.n_inputs) if show_inputs), "ζ", "predicción", "e"]
    rows = [[*([str(s.number), str(s.output)] if show_outputs else []),
             *(fmt(value) for value in s.inputs if show_inputs), fmt(s.zeta), fmt(s.prediction), fmt(s.error)]
            for s in shown]
    notes = []
    if len(run.samples) > MAX_TABLE_ROWS:
        notes.append(f"Primeras {MAX_TABLE_ROWS} filas de {len(run.samples)}; el resto está en predictions.csv.")
    if not show_inputs:
        notes.append(f"Sin las {run.n_inputs} entradas; están en predictions.csv.")
    note = f'<p class="note">{" ".join(notes)}</p>' if notes else ""
    return f'<section><h2>Predicciones ({run.n_samples})</h2>{note}{table(headers, rows)}</section>'


STYLE = """
:root {
  color-scheme: light;
  --surface: #fcfcfb; --surface-2: #f3f2ef; --border: #e2e1dc;
  --text-primary: #0b0b0b; --text-secondary: #52514e; --text-muted: #7a7973;
  --grid: #e8e7e3; --series-1: #2a78d6; --series-2: #eb6834;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --surface: #1a1a19; --surface-2: #232321; --border: #383835;
    --text-primary: #ffffff; --text-secondary: #c3c2b7; --text-muted: #8f8e86;
    --grid: #2e2e2c; --series-1: #3987e5; --series-2: #d95926;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--surface); color: var(--text-primary);
       font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 1100px; margin: 0 auto; padding: 24px 16px 48px; }
h1 { font-size: 22px; margin: 0 0 4px; }
h2 { font-size: 17px; margin: 32px 0 12px; }
h3 { font-size: 14px; margin: 0 0 8px; color: var(--text-secondary); font-weight: 600; }
.subtitle { color: var(--text-muted); margin: 0; font-family: ui-monospace, monospace; font-size: 13px; }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }
.stat { background: var(--surface-2); border: 1px solid var(--border); border-radius: 8px; padding: 12px 14px; }
.stat-label { color: var(--text-secondary); font-size: 13px; }
.stat-value { font-size: 20px; font-weight: 600; font-variant-numeric: tabular-nums; }
.charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 460px), 1fr)); gap: 16px; }
figure { margin: 0; background: var(--surface-2); border: 1px solid var(--border); border-radius: 8px; padding: 14px; }
figcaption, .note { color: var(--text-muted); font-size: 13px; margin-top: 6px; }
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
.glossary { display: grid; grid-template-columns: max-content 1fr; gap: 4px 16px; font-size: 13px; margin: 0; }
.glossary dt { font-family: ui-monospace, monospace; }
.glossary dd { margin: 0; color: var(--text-secondary); }
@media (max-width: 560px) { .glossary { grid-template-columns: 1fr; } .glossary dd { margin-bottom: 8px; } }
svg g[data-tip]:hover circle:not(.hit), svg g[data-tip]:hover path { stroke: var(--text-primary); stroke-width: 1.5; }
.legend { display: flex; gap: 16px; font-size: 13px; color: var(--text-secondary); margin-bottom: 4px; }
.swatch { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; vertical-align: -1px; }
.swatch.series-1 { background: var(--series-1); } .swatch.series-2 { background: var(--series-2); }
table { border-collapse: collapse; font-size: 13px; font-variant-numeric: tabular-nums; }
th, td { padding: 4px 12px 4px 0; text-align: left; border-bottom: 1px solid var(--border); }
.config th { color: var(--text-secondary); font-weight: 500; }
.config td { font-family: ui-monospace, monospace; }
.data td { text-align: right; } .data th { text-align: right; color: var(--text-secondary); }
.table-wrap { overflow: auto; max-height: 420px; border: 1px solid var(--border); border-radius: 8px; }
.table-wrap table { width: 100%; }
.table-wrap th, .table-wrap td { padding: 4px 12px; }
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
.segmented { display: inline-flex; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; }
.segmented button { font: inherit; font-size: 13px; padding: 3px 10px; border: 0; background: transparent;
                    color: var(--text-secondary); cursor: pointer; }
.segmented button + button { border-left: 1px solid var(--border); }
.segmented button[aria-pressed="true"] { background: var(--text-primary); color: var(--surface); }
#tip { position: fixed; pointer-events: none; background: var(--text-primary); color: var(--surface);
       padding: 6px 8px; border-radius: 6px; font-size: 12px; white-space: pre; z-index: 10; }
"""

SCRIPT = """
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
      group.querySelectorAll("circle").forEach((circle) => circle.setAttribute("cy", toPx(prediction).toFixed(1)));
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
<p class="subtitle">{html.escape(run.dir.name)} · validación sobre {html.escape(run.config["validation_dataset"])}</p>
<h2>Error de validación (pesos finales)</h2>
{stats_section(run, error)}
{glossary_section()}
{charts_section(run)}
{config_section(run)}
{weights_section(run)}
{predictions_section(run)}
</main>
<div id="tip" hidden></div>
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
