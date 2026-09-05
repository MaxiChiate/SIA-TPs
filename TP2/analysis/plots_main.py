#!/usr/bin/env python3
"""CLI for the sweep plots.

    python3 analysis/plots_main.py                    # the most recent sweep
    python3 analysis/plots_main.py analysis/results/20260905T011224Z
    python3 analysis/plots_main.py --out /tmp/graficos

Writes three standalone HTML charts next to the sweep's CSVs:

    fitness.html     best fitness per generation, one line per variant
    diversity.html   genotypic diversity per generation - the convergence story
    comparison.html  final fitness per variant, with one dot per seed
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.graph_objects as go  # noqa: E402

from analysis.config import PROJECT_ROOT  # noqa: E402
from analysis.plots_data import (  # noqa: E402
    SweepData,
    SweepDataError,
    final_values,
    latest_sweep,
    load_sweep,
    mean_curve,
)
from analysis.plots_style import (  # noqa: E402
    TEXT_SECONDARY,
    base_layout,
    end_label,
    palette_for,
    write_html,
)

DEFAULT_RESULTS = PROJECT_ROOT / "analysis" / "results"


def _curve_figure(
    data: SweepData, column: str, title: str, y_title: str
) -> go.Figure:
    """One line per variant, averaged over seeds, with a direct label at its end."""
    colors = palette_for(data.variants)
    curves = mean_curve(data, column)

    figure = go.Figure()
    annotations = []
    for variant, (generations, values) in curves.items():
        figure.add_trace(
            go.Scatter(
                x=generations,
                y=values,
                name=variant,
                mode="lines",
                line={"color": colors[variant], "width": 2},
                hovertemplate="%{y:.4f}<extra></extra>",
            )
        )
        annotations.append(
            end_label(variant, generations[-1], values[-1], colors[variant])
        )

    seeds = ", ".join(str(seed) for seed in data.seeds)
    layout = base_layout(
        title, f"Promedio de {len(data.seeds)} seeds ({seeds})", "Generación", y_title
    )
    layout["annotations"] = annotations
    figure.update_layout(**layout)
    return figure


def fitness_figure(data: SweepData) -> go.Figure:
    return _curve_figure(
        data, "best_fitness", "Mejor fitness por generación", "Fitness del mejor individuo"
    )


def diversity_figure(data: SweepData) -> go.Figure:
    return _curve_figure(
        data,
        "genotypic_diversity",
        "Diversidad genotípica por generación",
        "Desvío estándar medio por locus",
    )


def comparison_figure(data: SweepData) -> go.Figure:
    """Final fitness per variant: one hollow dot per seed plus a filled mean.

    A dot plot and not bars on purpose. Fitness here lives in a narrow band near
    1.0, so a bar chart would need a truncated axis to show any difference - and a
    truncated bar misrepresents magnitude, because a bar's length *is* the value.
    Dots encode position, so a zoomed axis is honest.

    The per-seed dots are the point of the chart: if one variant's seeds spread
    wider than the gap between two variants, that gap is not a result.
    """
    colors = palette_for(data.variants)
    values = final_values(data, "best_fitness")
    ranked = sorted(
        (v for v in data.variants if v in values),
        key=lambda v: sum(values[v]) / len(values[v]),
    )

    figure = go.Figure()
    # Mean values are labelled in the right margin rather than next to their
    # diamond: a seed dot landing near the mean would sit under the text.
    labels = []
    for variant in ranked:
        seen = values[variant]
        mean = sum(seen) / len(seen)
        figure.add_trace(
            go.Scatter(
                x=seen, y=[variant] * len(seen), mode="markers",
                marker={
                    "color": "#ffffff", "size": 10,
                    "line": {"color": colors[variant], "width": 2},
                },
                hovertemplate="seed: %{x:.4f}<extra></extra>", showlegend=False,
            )
        )
        figure.add_trace(
            go.Scatter(
                x=[mean], y=[variant], mode="markers",
                marker={"color": colors[variant], "size": 13, "symbol": "diamond"},
                hovertemplate="media: %{x:.4f}<extra></extra>", showlegend=False,
            )
        )
        labels.append({
            "x": 1, "xref": "paper", "xanchor": "left",
            "y": variant, "yref": "y", "yanchor": "middle",
            "text": f"  {mean:.4f}", "showarrow": False,
            "font": {"color": TEXT_SECONDARY, "size": 11},
        })

    layout = base_layout(
        "Fitness final por variante",
        "Rombo = media de las seeds · círculo = cada seed por separado",
        "Mejor fitness alcanzado",
        "",
    )
    layout["hovermode"] = "closest"
    layout["showlegend"] = False
    layout["yaxis"]["showgrid"] = False
    layout["annotations"] = labels
    flat = [value for variant in ranked for value in values[variant]]
    span = max(flat) - min(flat)
    pad = span * 0.15 if span else 0.01
    layout["xaxis"]["range"] = [min(flat) - pad, max(flat) + pad]
    layout["margin"] = {"l": 160, "r": 90, "t": 120, "b": 60}
    figure.update_layout(**layout)
    return figure


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="analysis/plots_main.py",
        description="Draw the charts of one sweep from its CSVs.",
    )
    parser.add_argument(
        "sweep", nargs="?", default=None,
        help="sweep results directory (default: the most recent one)",
    )
    parser.add_argument(
        "--out", default=None,
        help="where to write the HTMLs (default: inside the sweep directory)",
    )
    return parser.parse_args(argv[1:])


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    try:
        directory = Path(args.sweep) if args.sweep else latest_sweep(DEFAULT_RESULTS)
        data = load_sweep(directory)
    except SweepDataError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1

    out_dir = Path(args.out) if args.out else directory
    print(f"sweep:    {directory}")
    print(f"variantes: {', '.join(data.variants)}")
    print(f"seeds:     {', '.join(str(seed) for seed in data.seeds)}\n")

    for name, figure in (
        ("fitness.html", fitness_figure(data)),
        ("diversity.html", diversity_figure(data)),
        ("comparison.html", comparison_figure(data)),
    ):
        print(f"  {write_html(figure, out_dir / name)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
