#!/usr/bin/env python3
"""Sensitivity to the learning rate: validation accuracy against eta, one line per optimizer.

Stage 1 of the optimizer comparison (docs/optimizers_roadmap.md, step 8): each series_eta_<optimizer>.json
sweeps eta for one optimizer. This chart puts them side by side, and the table it prints picks each
optimizer's best eta for stage 2.

    python3 analysis/plots_eta_sensitivity.py                    # the latest results of each series_eta_*.json
    python3 analysis/plots_eta_sensitivity.py <series dir> ...   # or these series
    python3 analysis/plots_eta_sensitivity.py --output path.html

Needs plotly, like plots_main.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean

import plotly.graph_objects as go

from plots_data import SweepDataError, load_summary_rows
from plots_style import base_layout, palette_for, translucent, write_html

RESULTS = Path(__file__).resolve().parent / "results"

# series_eta_<name>.json, in the order the chart and the table list them
OPTIMIZER_SERIES = ("gd", "adaptive", "momentum", "rmsprop", "adam")


@dataclass(frozen=True)
class EtaPoint:
    eta: float
    accuracies: tuple[float, ...]  # validation accuracy of each seed, as a fraction

    @property
    def mean(self) -> float:
        return fmean(self.accuracies)


@dataclass(frozen=True)
class OptimizerSweep:
    optimizer: str
    directory: Path
    points: tuple[EtaPoint, ...]  # sorted by eta

    def best(self) -> EtaPoint:
        """Highest mean accuracy. max keeps the first of a tie, which is the smaller (steadier) eta."""
        return max(self.points, key=lambda point: point.mean)

    def best_on_edge(self) -> bool:
        """The best eta is the smallest or the largest tried: the optimum may lie outside the grid."""
        return self.best().eta in (self.points[0].eta, self.points[-1].eta)


def latest_series(name: str) -> Path:
    candidates = sorted(RESULTS.glob(f"series_eta_{name}_*/summary.csv"))  # the timestamp sorts by date
    if not candidates:
        raise SweepDataError(f"no results of series_eta_{name}.json under {RESULTS}: run it with sweep.py")
    return candidates[-1].parent


def optimizer_name(directory: Path) -> str:
    plan = json.loads((directory / "plan.json").read_text())
    return plan.get("set", {}).get("optimizer", "gd")


def run_eta(directory: Path, run: str) -> float:
    """From the run's own config, so it holds whether the series varied eta alone or with other keys."""
    config = json.loads((directory / "runs" / run / "config.json").read_text())
    return float(config["eta"])


def load_optimizer_sweep(directory: Path) -> OptimizerSweep:
    by_eta: dict[float, list[float]] = defaultdict(list)
    for row in load_summary_rows(directory):
        if row["status"] != "ok":
            continue
        if row.get("accuracy") is None:
            raise SweepDataError(f"{directory}: runs without accuracy; this chart needs a classification series")
        by_eta[run_eta(directory, row["run"])].append(row["accuracy"])
    if not by_eta:
        raise SweepDataError(f"{directory}: no successful run")
    points = tuple(EtaPoint(eta, tuple(accuracies)) for eta, accuracies in sorted(by_eta.items()))
    return OptimizerSweep(optimizer_name(directory), directory, points)


def add_optimizer(figure: go.Figure, sweep: OptimizerSweep, color: str) -> None:
    """Every seed as a faint dot, the mean as a line, and a star on the best eta."""
    figure.add_trace(go.Scatter(
        x=[point.eta for point in sweep.points for _ in point.accuracies],
        y=[100 * accuracy for point in sweep.points for accuracy in point.accuracies],
        mode="markers", marker={"color": translucent(color, 0.45), "size": 7}, showlegend=False,
        hovertemplate=f"{sweep.optimizer}<br>η %{{x:g}}<br>una seed: %{{y:.2f}}%<extra></extra>",
    ))
    figure.add_trace(go.Scatter(
        x=[point.eta for point in sweep.points], y=[100 * point.mean for point in sweep.points],
        mode="lines+markers", name=sweep.optimizer, line={"color": color, "width": 2},
        marker={"color": color, "size": 8},
        hovertemplate=f"{sweep.optimizer}<br>η %{{x:g}}<br>promedio: %{{y:.2f}}%<extra></extra>",
    ))
    best = sweep.best()
    figure.add_trace(go.Scatter(
        x=[best.eta], y=[100 * best.mean], mode="markers", showlegend=False,
        marker={"symbol": "star", "size": 18, "color": color, "line": {"color": "#0b0b0b", "width": 1}},
        hovertemplate=f"{sweep.optimizer}: mejor η %{{x:g}} (%{{y:.2f}}%)<extra></extra>",
    ))


def sensitivity_figure(sweeps: list[OptimizerSweep]) -> go.Figure:
    colors = palette_for([sweep.optimizer for sweep in sweeps])
    figure = go.Figure()
    for sweep in sweeps:
        add_optimizer(figure, sweep, colors[sweep.optimizer])
    seeds = max(len(point.accuracies) for sweep in sweeps for point in sweep.points)
    layout = base_layout(
        "Sensibilidad a η: accuracy de validación según la tasa de aprendizaje",
        [f"Línea: promedio de {seeds} seeds. Puntos: cada seed. Estrella: el mejor η de cada optimizador.",
         "Una curva ancha y plana tolera errores al elegir η; una angosta y empinada, no."],
        "η (escala logarítmica)", "Accuracy de validación (%)",
    )
    layout["xaxis"]["type"] = "log"
    layout["hovermode"] = "closest"  # each optimizer has its own grid of eta: there's no shared x to unify on
    figure.update_layout(layout)
    return figure


def print_best(sweeps: list[OptimizerSweep]) -> None:
    print(f"{'optimizador':<14}{'mejor η':>10}{'accuracy':>11}{'rango seeds':>18}")
    for sweep in sweeps:
        best = sweep.best()
        spread = f"{100 * min(best.accuracies):.2f}–{100 * max(best.accuracies):.2f}%"
        note = "  <- en el borde de la grilla: probar un η más allá" if sweep.best_on_edge() else ""
        print(f"{sweep.optimizer:<14}{best.eta:>10g}{100 * best.mean:>10.2f}%{spread:>18}{note}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("series", nargs="*", type=Path,
                        help="series result dirs (default: the latest of each series_eta_<optimizer>.json)")
    parser.add_argument("--output", type=Path, default=RESULTS / "eta_sensitivity.html",
                        help="where the chart goes (default: analysis/results/eta_sensitivity.html)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        directories = args.series or [latest_series(name) for name in OPTIMIZER_SERIES]
        sweeps = [load_optimizer_sweep(directory) for directory in directories]
    except SweepDataError as error:
        sys.exit(f"error: {error}")
    print_best(sweeps)
    print(f"\n-> {write_html(sensitivity_figure(sweeps), args.output)}")


if __name__ == "__main__":
    main()
