#!/usr/bin/env python3
"""Writes report.html into a sweep directory: one variant per color, compared across seeds.

    python3 analysis/sweep_report.py [analysis/results/<sweep>]   # without one, the latest sweep

sweep.py calls it at the end. Same charts and style as scripts/run_report.py (inline SVG, standard
library only), but each line is a variant averaged over its seeds instead of one run.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from sweep import RESULTS_DIR, RunSummary, read_summary
from run_report import (
    EPOCH_METRICS, HEIGHT, MARGIN_BOTTOM, MARGIN_TOP, STYLE, ZOOM_HINT, ZOOM_SCRIPT, EpochRecord, Scale, axes,
    figure, fmt, legend, load_epochs, x_scale, y_scale, y_ticks, zoomable_svg,
)

SPLITS = {"validation": "validación", "train": "train"}
# Fewer than run_report: here there are 8 curve views, each with every variant
MAX_PLOTTED_EPOCHS = 400
MAX_HOVER_COLUMNS = 100  # each hover column lists every variant, so they are the bulk of the page


@dataclass(frozen=True)
class VariantRuns:
    index: int  # fixes the color: series-<index + 1>
    label: str
    overrides: dict[str, Any]
    summaries: list[RunSummary]  # every run, failed ones included
    epochs: list[list[EpochRecord]]  # one list per successful run

    @property
    def css(self) -> str:
        return f"series-{self.index + 1}"

    @property
    def ok(self) -> list[RunSummary]:
        return [summary for summary in self.summaries if summary.status == "ok"]


# Final metric -> (label, how to read it off a summary); accuracy is shown in percent
FINAL_METRICS: dict[str, tuple[str, Callable[[RunSummary], float | None]]] = {
    "validation_mse": ("MSE validación", lambda s: s.validation_mse),
    "train_mse": ("MSE train (mejor época)", lambda s: s.train_mse),
    "accuracy": ("Aciertos validación (%)", lambda s: None if s.accuracy is None else 100 * s.accuracy),
    "epochs_run": ("Épocas entrenadas", lambda s: s.epochs_run),
    "elapsed_s": ("Tiempo de entrenamiento (s)", lambda s: s.elapsed_s),
}


# ---------- loading ----------

def load_variants(sweep_dir: Path, plan: dict[str, Any]) -> list[VariantRuns]:
    summaries = read_summary(sweep_dir / "summary.csv")
    variants = []
    for index, variant in enumerate(plan["variants"]):
        own = [summary for summary in summaries if summary.variant == index]
        epochs = [load_epochs(sweep_dir / "runs" / summary.run) for summary in own if summary.status == "ok"]
        variants.append(VariantRuns(index, variant["label"], variant["overrides"], own, epochs))
    return variants


# ---------- statistics ----------

def mean_std(values: list[float]) -> tuple[float, float] | None:
    if not values:
        return None
    return statistics.fmean(values), statistics.stdev(values) if len(values) > 1 else 0.0


def present(values: list[float | None]) -> list[float]:
    return [value for value in values if value is not None]


def at_epoch(records: list[EpochRecord], epoch: int) -> EpochRecord:
    """A run that converged early keeps its last value: training stopped there."""
    return records[min(epoch, len(records) - 1)]


@dataclass(frozen=True)
class CurvePoint:
    epoch: int
    mean: float
    lo: float
    hi: float


def mean_curve(variant: VariantRuns, split: str, metric: str, epochs: list[int]) -> list[CurvePoint]:
    points = []
    for epoch in epochs:
        values = [getattr(at_epoch(records, epoch), split)[metric] for records in variant.epochs]
        points.append(CurvePoint(epoch, statistics.fmean(values), min(values), max(values)))
    return points


def plotted_epochs(variants: list[VariantRuns]) -> list[int]:
    last = max(len(records) - 1 for variant in variants for records in variant.epochs)
    step = math.ceil((last + 1) / MAX_PLOTTED_EPOCHS)
    shown = list(range(0, last + 1, step))
    return shown if shown[-1] == last else [*shown, last]


# ---------- charts ----------

def value_scale(values: list[float]) -> Scale:
    """Log once the values span more than two orders of magnitude, like run_report's learning curve."""
    positive = [value for value in values if value > 0]
    if positive and len(positive) == len(values) and max(positive) / min(positive) > 100:
        return Scale(math.floor(math.log10(min(positive))), math.ceil(math.log10(max(positive))),
                     HEIGHT - MARGIN_BOTTOM, MARGIN_TOP, log=True)
    return y_scale((min(0.0, min(values)), max(values) * 1.05 or 1))


def curve_svg(variants: list[VariantRuns], epochs: list[int], split: str, metric: str) -> str:
    curves = {variant.index: mean_curve(variant, split, metric, epochs) for variant in variants}
    values = [value for curve in curves.values() for point in curve for value in (point.lo, point.hi)]
    x, y = x_scale((0, epochs[-1] or 1)), value_scale(values)

    bands, lines = [], []
    for variant in variants:
        curve = curves[variant.index]
        upper = " ".join(f"{x(p.epoch):.1f},{y(p.hi):.1f}" for p in curve)
        lower = " ".join(f"{x(p.epoch):.1f},{y(p.lo):.1f}" for p in reversed(curve))
        bands.append(f'<polygon class="band {variant.css}" points="{upper} {lower}"/>')
        points = " ".join(f"{x(p.epoch):.1f},{y(p.mean):.1f}" for p in curve)
        lines.append(f'<polyline class="line {variant.css}" points="{points}"/>')

    # Invisible columns carry every variant's value, at most MAX_HOVER_COLUMNS of the plotted epochs
    hovered = range(0, len(epochs), math.ceil(len(epochs) / MAX_HOVER_COLUMNS))
    slot = (x.px_hi - x.px_lo) / max(len(hovered) - 1, 1)
    hits = []
    for k in hovered:
        epoch = epochs[k]
        tip = f"época {epoch}\n" + "\n".join(
            f"{variant.label}: {fmt(curves[variant.index][k].mean)}  [{fmt(curves[variant.index][k].lo)}, "
            f"{fmt(curves[variant.index][k].hi)}]" for variant in variants)
        hits.append(f'<rect class="hit" x="{x(epoch) - slot / 2:.1f}" y="{MARGIN_TOP}" width="{slot:.1f}" '
                    f'height="{y.px_lo - MARGIN_TOP:.1f}" data-tip="{html.escape(tip)}"/>')

    label = f"{EPOCH_METRICS[metric]} {SPLITS[split]}"
    y_label = f"{label} (escala log)" if y.log else label
    return zoomable_svg(axes(x, y, "época", y_label), "".join(bands) + "".join(lines) + "".join(hits), x, y,
                        f"{label} por época, promedio de cada variante")


def segmented(group: str, options: dict[str, str]) -> str:
    buttons = "".join(f'<button type="button" data-value="{key}" aria-pressed="{str(i == 0).lower()}">'
                      f'{html.escape(label)}</button>' for i, (key, label) in enumerate(options.items()))
    return f'<div class="segmented" data-group="{group}">{buttons}</div>'


def switchable(key: str, first: bool, chart: str) -> str:
    return f'<div class="switch-chart" data-key="{key}"{"" if first else " hidden"}>{chart}</div>'


def learning_curves_chart(variants: list[VariantRuns]) -> str:
    epochs = plotted_epochs(variants)
    metrics = list(variants[0].epochs[0][0].train)
    charts = "".join(
        switchable(f"{split}|{metric}", (split, metric) == ("validation", metrics[0]),
                   curve_svg(variants, epochs, split, metric))
        for split in SPLITS for metric in metrics
    )
    controls = (f'<div class="curve-controls">{segmented("split", SPLITS)}'
                f'{segmented("metric", {metric: EPOCH_METRICS[metric] for metric in metrics})}'
                f'<label class="bands-toggle"><input type="checkbox"> rango entre seeds</label></div>')
    caption = ("Cada línea es el promedio de las seeds de una variante; la banda (opcional) va del mínimo al "
               "máximo. Una corrida que convergió antes queda con su último valor." + ZOOM_HINT
               + (f" Se grafica 1 de cada {epochs[1] - epochs[0]} épocas." if len(epochs) > 1 and epochs[1] > 1 else ""))
    items = [(variant.css, variant.label) for variant in variants]
    return figure("Curva de aprendizaje por variante", controls + legend(items) + charts, caption).replace(
        "<figure>", '<figure class="switchable">', 1)


def category_axes(labels: list[str], y: Scale, y_label: str) -> tuple[str, list[float], float]:
    """y axis like run_report's, one x band per variant. Returns the svg, the band centers and width."""
    x = x_scale((0, 1))
    width = (x.px_hi - x.px_lo) / len(labels)
    centers = [x.px_lo + width * (k + 0.5) for k in range(len(labels))]
    parts = ['<g class="ticks">']
    for tick in y_ticks(y):
        py = y(tick)
        parts.append(f'<line class="grid" x1="{x.px_lo}" x2="{x.px_hi}" y1="{py:.1f}" y2="{py:.1f}"/>')
        parts.append(f'<text class="tick" x="{x.px_lo - 8}" y="{py:.1f}" text-anchor="end" '
                     f'dominant-baseline="middle">{fmt(tick)}</text>')
    parts.append("</g>")
    for center, label in zip(centers, labels):
        parts.append(f'<text class="tick" x="{center:.1f}" y="{y.px_lo + 18}" text-anchor="middle">'
                     f'{html.escape(label)}</text>')
    parts.append(f'<line class="axis" x1="{x.px_lo}" x2="{x.px_hi}" y1="{y.px_lo}" y2="{y.px_lo}"/>')
    parts.append(f'<text class="label" transform="translate(14 {(y.px_lo + y.px_hi) / 2}) rotate(-90)" '
                 f'text-anchor="middle">{html.escape(y_label)}</text>')
    return "".join(parts), centers, width


def final_metric_svg(variants: list[VariantRuns], metric: str, varied: str) -> str:
    label, read = FINAL_METRICS[metric]
    values = {v.index: [(s.seed, read(s)) for s in v.ok if read(s) is not None] for v in variants}
    y = value_scale([value for pairs in values.values() for _, value in pairs])
    if y.log:
        label += " (escala log)"
    frame, centers, width = category_axes([v.label for v in variants], y, label)

    marks = []
    for variant, center in zip(variants, centers):
        pairs = values[variant.index]
        for i, (seed, value) in enumerate(pairs):
            # Seeds spread across the middle half of the band so equal values don't hide each other
            px = center + ((i / (len(pairs) - 1) - 0.5) * 0.5 * width if len(pairs) > 1 else 0)
            tip = f"{variant.label} · seed {seed}\n{FINAL_METRICS[metric][0]} = {fmt(value)}"
            marks.append(f'<g data-tip="{html.escape(tip)}"><circle class="hit" cx="{px:.1f}" cy="{y(value):.1f}" r="9"/>'
                         f'<circle class="{variant.css}" cx="{px:.1f}" cy="{y(value):.1f}" r="4"/></g>')
        if pairs:
            mean = statistics.fmean(value for _, value in pairs)
            tip = f"{variant.label}\npromedio de {len(pairs)} seeds = {fmt(mean)}"
            marks.append(f'<g data-tip="{html.escape(tip)}"><line class="mean" x1="{center - 0.35 * width:.1f}" '
                         f'x2="{center + 0.35 * width:.1f}" y1="{y(mean):.1f}" y2="{y(mean):.1f}"/></g>')
    return zoomable_svg(frame, "".join(marks), x_scale((0, 1)), y, f"{FINAL_METRICS[metric][0]} por {varied}",
                        zoom_x=False)


def final_metrics_chart(variants: list[VariantRuns], varied: str) -> str:
    metrics = {metric: label for metric, (label, read) in FINAL_METRICS.items()
               if any(read(summary) is not None for variant in variants for summary in variant.ok)}
    charts = "".join(switchable(metric, i == 0, final_metric_svg(variants, metric, varied))
                     for i, metric in enumerate(metrics))
    caption = ("Cada punto es una seed (con los pesos finales, los de la mejor época de train); la raya es el "
               "promedio de la variante. Arrastrá para hacer zoom en el eje y; doble clic para volver.")
    controls = f'<div class="curve-controls">{segmented("final", metrics)}</div>'
    return figure(f"Resultado final por {varied}", controls + charts, caption).replace(
        "<figure>", '<figure class="switchable">', 1)


# ---------- page sections ----------

def mean_std_cell(values: list[float], scale: float = 1, suffix: str = "") -> str:
    stats = mean_std([value * scale for value in values])
    if stats is None:
        return "–"
    mean, std = stats
    return f"{fmt(mean)}{suffix} ± {fmt(std)}{suffix}" if len(values) > 1 else f"{fmt(mean)}{suffix}"


def convergence_cell(variant: VariantRuns) -> str:
    flags = [summary.converged for summary in variant.ok if summary.converged is not None]
    return f"{sum(flags)}/{len(flags)}" if flags else "–"


def summary_section(variants: list[VariantRuns]) -> str:
    means = {v.index: mean_std(present([s.validation_mse for s in v.ok])) for v in variants}
    best = min((v.index for v in variants if means[v.index]), key=lambda i: means[i][0], default=None)
    has_accuracy = any(s.accuracy is not None for v in variants for s in v.ok)
    headers = ["variante", "corridas", "convergieron", "épocas", "MSE validación", "MSE train (mejor)",
               *(["aciertos validación"] if has_accuracy else []), "tiempo (s)"]
    rows = []
    for v in variants:
        name = f'<i class="swatch {v.css}"></i>{html.escape(v.label)}' + (" <b>· mejor</b>" if v.index == best else "")
        cells = [name, f"{len(v.ok)}/{len(v.summaries)}", convergence_cell(v),
                 mean_std_cell(present([s.epochs_run for s in v.ok])),
                 mean_std_cell(present([s.validation_mse for s in v.ok])),
                 mean_std_cell(present([s.train_mse for s in v.ok])),
                 *([mean_std_cell(present([s.accuracy for s in v.ok]), 100, "%")] if has_accuracy else []),
                 mean_std_cell(present([s.elapsed_s for s in v.ok]))]
        rows.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>")
    head = "".join(f"<th>{html.escape(header)}</th>" for header in headers)
    note = ('<p class="note">Promedio ± desvío entre seeds. <b>Mejor</b> = menor MSE de validación promedio. '
            '<b>Convergieron</b> cuenta las corridas que cumplieron el criterio de corte (<code>tolerance</code>, '
            'o cero mal clasificadas con <code>sign</code>); – si el config no tiene criterio.</p>')
    return (f'<section><h2>Resumen por variante</h2><div class="table-wrap"><table class="data summary">'
            f'<thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>{note}</section>')


def config_section(plan: dict[str, Any], variants: list[VariantRuns]) -> str:
    rows = [(key, json.dumps(value)) for key, value in plan["base_config"].items() if key != "seed"]
    rows += [(f"{key} (todas)", json.dumps(value)) for key, value in plan["set"].items()]
    rows.append(("seeds", json.dumps(plan["seeds"])))
    rows += [(f"variante {v.label}", json.dumps(v.overrides)) for v in variants]
    body = "".join(f"<tr><th>{html.escape(key)}</th><td>{html.escape(value)}</td></tr>" for key, value in rows)
    note = '<p class="note">Config base, lo que la serie fija para todas las corridas, y lo que cambia cada variante.</p>'
    return f'<section><h2>Configuración</h2>{note}<table class="config">{body}</table></section>'


def optional(value: float | None, scale: float = 1, suffix: str = "") -> str:
    return "–" if value is None else f"{fmt(value * scale)}{suffix}"


def runs_section(sweep_dir: Path, variants: list[VariantRuns]) -> str:
    headers = ["corrida", "variante", "seed", "estado", "épocas", "mejor época", "MSE train", "MSE validación",
               "aciertos", "tiempo (s)"]
    rows = []
    for v in variants:
        for s in v.summaries:
            has_report = (sweep_dir / "runs" / s.run / "report.html").exists()
            link = (f'<a href="runs/{html.escape(s.run)}/report.html">{html.escape(s.run)}</a>' if has_report
                    else html.escape(s.run))
            cells = [link, html.escape(v.label), str(s.seed), html.escape(s.status), optional(s.epochs_run),
                     optional(s.best_epoch), optional(s.train_mse), optional(s.validation_mse),
                     optional(s.accuracy, 100, "%"), optional(s.elapsed_s)]
            rows.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>")
    head = "".join(f"<th>{html.escape(header)}</th>" for header in headers)
    note = '<p class="note">Cada corrida con link tiene su propio reporte (el mismo que arma <code>make run</code>); sin link, se arma con <code>python3 scripts/run_report.py &lt;carpeta&gt;</code>.</p>'
    return (f'<section><h2>Corridas ({sum(len(v.summaries) for v in variants)})</h2>{note}<div class="table-wrap">'
            f'<table class="data runs"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>')


# Slots 1-2 are run_report's; 3-8 follow the same validated categorical order, light and dark
EXTRA_STYLE = """
:root { --series-3: #1baf7a; --series-4: #eda100; --series-5: #e87ba4; --series-6: #008300; --series-7: #4a3aa7;
        --series-8: #e34948; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { --series-3: #199e70; --series-4: #c98500; --series-5: #d55181;
                                    --series-6: #008300; --series-7: #9085e9; --series-8: #e66767; }
}
""" + "".join(
    f"svg .line.series-{k} {{ stroke: var(--series-{k}); }} svg circle.series-{k} {{ fill: var(--series-{k}); "
    f"stroke: var(--surface-2); stroke-width: 1.5; }} svg .band.series-{k} {{ fill: var(--series-{k}); }} "
    f".swatch.series-{k} {{ background: var(--series-{k}); }}\n" for k in range(1, 9)
) + """
svg .band { opacity: 0.14; display: none; }
.show-bands svg .band { display: inline; }
svg .mean { stroke: var(--text-primary); stroke-width: 2; stroke-linecap: round; }
svg g[data-tip]:hover line.mean { stroke-width: 3; }
.legend { flex-wrap: wrap; }
.bands-toggle { font-size: 13px; color: var(--text-secondary); display: inline-flex; align-items: center; gap: 6px; }
.summary td:first-child, .summary th:first-child, .runs td:first-child, .runs th:first-child,
.runs td:nth-child(2), .runs th:nth-child(2), .runs td:nth-child(4), .runs th:nth-child(4) { text-align: left; }
.data a { color: var(--series-1); }
code { font-family: ui-monospace, monospace; font-size: 12px; }
"""

SCRIPT = ZOOM_SCRIPT + """
// Every segmented control picks one part of the chart key; the chart whose data-key matches is shown
document.querySelectorAll("figure.switchable").forEach((figure) => {
  const groups = [...figure.querySelectorAll(".segmented")];
  function update() {
    const key = groups.map((group) => group.querySelector('[aria-pressed="true"]').dataset.value).join("|");
    figure.querySelectorAll(".switch-chart").forEach((chart) => { chart.hidden = chart.dataset.key !== key; });
  }
  groups.forEach((group) => group.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      group.querySelectorAll("button").forEach((other) => other.setAttribute("aria-pressed", other === button));
      update();
    });
  }));
  const bands = figure.querySelector(".bands-toggle input");
  if (bands) bands.addEventListener("change", () => figure.classList.toggle("show-bands", bands.checked));
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


def render(sweep_dir: Path) -> str:
    plan = json.loads((sweep_dir / "plan.json").read_text())
    variants = load_variants(sweep_dir, plan)
    varied = plan["vary"] or "variante"
    plotted = [v for v in variants if v.epochs]
    charts = [learning_curves_chart(plotted), final_metrics_chart(plotted, varied)] if plotted else []
    title = f"Serie {plan['name']}"
    subtitle = (f"{sweep_dir.name} · {len(variants)} variantes × {len(plan['seeds'])} seeds · "
                f"{plan['base_config']['activation']} · validación sobre "
                f"{Path(plan['base_config']['validation_dataset']).name}")
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>{STYLE}{EXTRA_STYLE}</style>
</head>
<body>
<main>
<h1>{html.escape(title)}</h1>
<p class="subtitle">{html.escape(subtitle)}</p>
{summary_section(variants)}
<section><h2>Comparación</h2><div class="charts">{"".join(charts)}</div></section>
{config_section(plan, variants)}
{runs_section(sweep_dir, variants)}
</main>
<div id="tip" hidden></div>
<script>{SCRIPT}</script>
</body>
</html>
"""


def write_report(sweep_dir: Path) -> Path:
    report = sweep_dir / "report.html"
    report.write_text(render(sweep_dir))
    return report


def latest_sweep() -> Path:
    """The one whose summary.csv was written last."""
    summaries = list(RESULTS_DIR.glob("*/summary.csv")) if RESULTS_DIR.exists() else []
    sweeps = [path.parent for path in sorted(summaries, key=lambda path: path.stat().st_mtime)]
    if not sweeps:
        raise SystemExit(f"no sweeps in {RESULTS_DIR}")
    return sweeps[-1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sweep_dir", type=Path, nargs="?", help="sweep directory (default: latest)")
    args = parser.parse_args()
    print(f"report -> {write_report(args.sweep_dir or latest_sweep())}")


if __name__ == "__main__":
    main()
