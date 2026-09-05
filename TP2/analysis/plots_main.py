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
    fixed_config,
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


# What to show in the "held fixed" caption, in reading order, split into the two
# lines it is rendered as. Anything the sweep varied never reaches here: it
# differs between variants, so ``fixed_config`` already dropped it.
_ENGINE_FIELDS = (
    ("engine.n", "N"),
    ("engine.k", "K"),
    ("engine.pc", "Pc"),
    ("engine.pm", "Pm"),
    ("engine.max_generations", "generaciones"),
    ("operators.parent_selection.name", "selección"),
    ("operators.crossover.name", "cruza"),
    ("operators.mutation.name", "mutación"),
    ("operators.survival.name", "supervivencia"),
)
_PROBLEM_FIELDS = (
    ("problem.params.image_path", "imagen"),
    ("problem.params.triangle_count", "triángulos"),
    ("problem.params.work_resolution", "resolución"),
)


def _format_value(key: str, value) -> str:
    if key == "problem.params.work_resolution" and isinstance(value, tuple):
        return "×".join(str(part) for part in value)
    if key == "problem.params.image_path":
        return Path(str(value)).name
    return str(value)


def _fixed_captions(fixed: dict) -> list[str]:
    """Two caption lines naming what was held constant across every run."""
    lines = []
    for label, fields in (("Fijo", _ENGINE_FIELDS), ("Problema", _PROBLEM_FIELDS)):
        parts = [
            f"{name} {_format_value(key, fixed[key])}"
            for key, name in fields
            if key in fixed
        ]
        if parts:
            lines.append(f"{label}: " + " · ".join(parts))
    return lines


def _end_labels(
    curves: dict[str, tuple[list[int], list[float]]], colors: dict[str, str]
) -> list[dict]:
    """Direct labels at the line ends, skipping the ones that would overlap.

    Curves that converge (which is what these runs do) end within a hair of each
    other, so labelling every line stacks unreadable text. Labelling the ones
    that are separated enough keeps the relief where it is legible; the legend
    and the unified hover cover the rest.
    """
    if not curves:
        return []
    finals = sorted(
        ((values[-1], generations[-1], variant) for variant, (generations, values) in curves.items()),
        reverse=True,
    )
    all_values = [value for _, values in curves.values() for value in values]
    minimum_gap = (max(all_values) - min(all_values)) * 0.045

    labels: list[dict] = []
    last_placed: float | None = None
    for value, generation, variant in finals:
        if last_placed is None or abs(last_placed - value) >= minimum_gap:
            labels.append(end_label(variant, generation, value, colors[variant]))
            last_placed = value
    return labels


def _curve_figure(
    data: SweepData, column: str, title: str, y_title: str, captions: list[str]
) -> go.Figure:
    """One line per variant, averaged over seeds, with a direct label at its end."""
    colors = palette_for(data.variants)
    curves = mean_curve(data, column)

    figure = go.Figure()
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
    annotations = _end_labels(curves, colors)

    seeds = ", ".join(str(seed) for seed in data.seeds)
    layout = base_layout(
        title,
        [f"Promedio de {len(data.seeds)} seeds ({seeds})", *captions],
        "Generación",
        y_title,
    )
    layout["annotations"] = annotations
    figure.update_layout(**layout)
    return figure


def fitness_figure(data: SweepData, captions: list[str]) -> go.Figure:
    return _curve_figure(
        data,
        "best_fitness",
        "Mejor fitness por generación",
        "Fitness del mejor individuo",
        captions,
    )


def diversity_figure(data: SweepData, captions: list[str]) -> go.Figure:
    return _curve_figure(
        data,
        "genotypic_diversity",
        "Diversidad genotípica por generación",
        "Desvío estándar medio por locus",
        captions,
    )


def comparison_figure(data: SweepData, captions: list[str]) -> go.Figure:
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
        ["Rombo = media de las seeds · círculo = cada seed por separado", *captions],
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
    # No legend on this one (each row is labelled by the y axis), so the bottom
    # margin only has to fit the axis title.
    layout["margin"] = {**layout["margin"], "l": 160, "r": 90, "b": 60}
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
    captions = _fixed_captions(fixed_config(directory))
    print(f"sweep:     {directory}")
    print(f"variantes: {', '.join(data.variants)}")
    print(f"seeds:     {', '.join(str(seed) for seed in data.seeds)}")
    for caption in captions:
        print(f"  {caption}")
    print()

    for name, figure in (
        ("fitness.html", fitness_figure(data, captions)),
        ("diversity.html", diversity_figure(data, captions)),
        ("comparison.html", comparison_figure(data, captions)),
    ):
        print(f"  {write_html(figure, out_dir / name)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
