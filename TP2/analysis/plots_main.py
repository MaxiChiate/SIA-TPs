#!/usr/bin/env python3
"""CLI for a sweep's charts: writes all of them plus the index.html that fronts them.

    python3 analysis/plots_main.py                    # the most recent sweep
    python3 analysis/plots_main.py analysis/results/20260905T011224Z
    python3 analysis/plots_main.py --out /tmp/graficos --abrir

    python3 analysis/plots_main.py --x cumulative_evaluations

One command and one entry point: the charts of a sweep are read together - the
trajectory says what happened, the comparison says whether it is a result - and
splitting them across two commands only invites presenting half of them. Written
next to the sweep's CSVs:

    index.html       links every chart below, plus the summary tables and the
                     configuration the runs actually used
    fitness.html     best fitness achieved, per-seed running maximum
    diversity.html   genotypic diversity - the convergence story
    pressure.html    best minus population mean - what selection is doing
    comparison.html  final fitness per variant, with one dot per seed
    compare_*.html   boxplot, paired differences or rank stability, convergence
                     speed, and the exploration trade-off (analysis/plots_compare.py)
    survival_cost.html  only when the sweep varies the survival operator

Every curve marks the full min-max range across seeds with error bars, so a
difference between two variants can be read against the spread that produced it. ``--x cumulative_evaluations`` re-plots the *trajectory* charts
against work done instead of generations, for the sweeps where a generation does
not cost the same in every variant; those charts are then suffixed with the axis
name so both versions can sit side by side.
"""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.graph_objects as go  # noqa: E402

from analysis.config import PROJECT_ROOT  # noqa: E402
from analysis.plots_compare import (  # noqa: E402
    ComparisonError,
    comparison_charts,
    print_tables,
    summary_tables,
)
from analysis.plots_data import (  # noqa: E402
    X_COLUMNS,
    Band,
    SweepData,
    SweepDataError,
    best_minus_mean,
    curve_bands,
    final_values,
    fixed_captions,
    fixed_config,
    latest_sweep,
    load_rows,
    load_sweep,
    varied_knob,
    varied_paths,
)
from analysis.plots_index import Chart, IndexPage, write_index  # noqa: E402
from analysis.plots_style import (  # noqa: E402
    ERROR_MARKS,
    TEXT_SECONDARY,
    add_error_bars,
    base_layout,
    end_label,
    palette_for,
    write_html,
)

DEFAULT_RESULTS = PROJECT_ROOT / "analysis" / "results"

# Below this, the generation's best and the best-so-far are the same curve and
# drawing both only doubles the ink. Above it, the gap *is* the result (a
# (mu,lambda) population can lose its best individual), so the raw curve is
# added as a dashed line. Expressed as a fraction of the chart's own y range,
# so it means the same thing at any fitness scale.
INSTABILITY_THRESHOLD = 0.02


def _end_labels(
    curves: dict[str, tuple[list[float], list[float]]], colors: dict[str, str]
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
    data: SweepData,
    value,
    title: str,
    y_title: str,
    captions: list[str],
    x_column: str = "generation",
    running_max: bool = False,
    raw_value: str | None = None,
) -> go.Figure:
    """One line per variant, averaged over seeds, over its min-max seed band.

    ``raw_value``, when given, is the untransformed column: it is drawn dashed
    for any variant whose two curves visibly disagree, and silently skipped for
    the rest. That keeps the extra ink on exactly the sweeps where the
    difference is the finding.
    """
    colors = palette_for(data.variants)
    bands = curve_bands(data, value, x_column=x_column, running_max=running_max)
    if not bands:
        raise SweepDataError(f"no data to plot for {value!r}")

    figure = go.Figure()
    for variant, band in bands.items():
        figure.add_trace(
            go.Scatter(
                x=band.x, y=band.mean, name=variant, mode="lines",
                line={"color": colors[variant], "width": 2},
                hovertemplate="%{y:.4f}<extra></extra>",
            )
        )
    # Each variant samples its bars at a different offset, so with several
    # curves the bars interleave along x instead of piling into one column.
    for position, (variant, band) in enumerate(bands.items()):
        marks = band.error_marks(ERROR_MARKS, phase=position / max(len(bands), 1))
        add_error_bars(figure, marks, colors[variant])

    everything = [v for band in bands.values() for v in (*band.low, *band.high)]
    y_range = (max(everything) - min(everything)) or 1.0

    unstable: list[str] = []
    if raw_value is not None:
        raw = curve_bands(data, raw_value, x_column=x_column)
        for variant, band in bands.items():
            other = raw.get(variant)
            if other is None:
                continue
            departure = max(
                (a - b for a, b in zip(band.mean, other.mean)), default=0.0
            )
            if departure < INSTABILITY_THRESHOLD * y_range:
                continue
            unstable.append(variant)
            figure.add_trace(
                go.Scatter(
                    x=other.x, y=other.mean, name=f"{variant} (por generación)",
                    mode="lines",
                    line={"color": colors[variant], "width": 1.5, "dash": "dot"},
                    hovertemplate="%{y:.4f}<extra></extra>",
                )
            )

    subtitles = [
        f"Media de {len(data.seeds)} seeds; las barras de error marcan el rango "
        "completo entre ellas",
        *captions,
    ]
    if unstable:
        subtitles.insert(
            1,
            "Punteado: el mejor de cada generación, para las variantes donde "
            f"cae por debajo del máximo alcanzado ({', '.join(unstable)})",
        )

    layout = base_layout(title, subtitles, X_COLUMNS[x_column], y_title)
    layout["annotations"] = _end_labels(
        {variant: (band.x, band.mean) for variant, band in bands.items()}, colors
    )
    figure.update_layout(**layout)
    return figure


def fitness_figure(
    data: SweepData, captions: list[str], x_column: str = "generation"
) -> go.Figure:
    """Best fitness *achieved by* each generation - a per-seed running maximum.

    Not the raw ``best_fitness`` column, which is the best of that generation
    alone. Under ``exclusive`` (mu,lambda) survival the whole population is
    replaced by its children, so the generation's best can be worse than one
    already seen; averaging that across seeds produces a jagged line that is no
    single run's trajectory. The running maximum answers "how good had this run
    got by generation g", which is the question every one of these sweeps is
    asking, and the raw curve is added dashed wherever the two diverge.
    """
    return _curve_figure(
        data,
        "best_fitness",
        "Mejor fitness alcanzado",
        "Fitness del mejor individuo",
        captions,
        x_column=x_column,
        running_max=True,
        raw_value="best_fitness",
    )


def diversity_figure(
    data: SweepData, captions: list[str], x_column: str = "generation"
) -> go.Figure:
    return _curve_figure(
        data,
        "genotypic_diversity",
        "Diversidad genotípica",
        "Desvío estándar medio por locus",
        captions,
        x_column=x_column,
    )


def pressure_figure(
    data: SweepData, captions: list[str], x_column: str = "generation"
) -> go.Figure:
    """The gap between the best individual and the population average.

    This is what a parent-selection method *does*: a strong one pulls the
    population up behind its best and the gap closes; a weak one leaves the
    average trailing. Two columns the CSV has always carried and nothing
    plotted. It doubles as the diagnostic for a mis-calibrated Boltzmann
    schedule - if its curve traces another method's, the temperature has
    collapsed it into that method.
    """
    return _curve_figure(
        data,
        best_minus_mean,
        "Presión selectiva: mejor − promedio",
        "Distancia del mejor al promedio de la población",
        captions,
        x_column=x_column,
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


def trajectory_charts(
    data: SweepData, captions: list[str], x_column: str
) -> list[tuple[Chart, go.Figure]]:
    """The four per-generation charts, with their index entries.

    ``comparison.html`` is not parameterised by ``--x``: it has no time axis at
    all, one dot per seed at the end of its run, so writing it once per axis
    choice would just overwrite the same chart.
    """
    suffix = "" if x_column == "generation" else f"_{x_column}"
    axis = X_COLUMNS[x_column].lower()
    # The extra-axis charts share the index with the default ones, so their
    # entries have to say which axis they are, not just what they plot.
    against = "" if not suffix else f" (contra {axis})"
    charts = [
        (
            Chart(f"fitness{suffix}.html", f"Mejor fitness alcanzado{against}",
                  f"Máximo acumulado por seed contra {axis}. Es la curva de "
                  "'qué tan bien iba esta corrida' que resume la serie.",
                  group="trayectoria"),
            fitness_figure(data, captions, x_column),
        ),
        (
            Chart(f"diversity{suffix}.html", f"Diversidad genotípica{against}",
                  "El gráfico de la convergencia prematura: si cae a cero antes de que "
                  "el fitness llegue a algo aceptable, la población se homogeneizó.",
                  group="trayectoria"),
            diversity_figure(data, captions, x_column),
        ),
        (
            Chart(f"pressure{suffix}.html", f"Presión selectiva{against}",
                  "La distancia del mejor individuo al promedio de su población: lo que "
                  "el método de selección efectivamente hace, generación a generación.",
                  group="trayectoria"),
            pressure_figure(data, captions, x_column),
        ),
    ]
    if not suffix:
        charts.append((
            Chart("comparison.html", "Fitness final, seed por seed",
                  "Un círculo por seed y un rombo en la media. Si las seeds de una "
                  "variante se dispersan más que la distancia entre dos variantes, esa "
                  "distancia no es un resultado.",
                  group="trayectoria"),
            comparison_figure(data, captions),
        ))
    return charts


def load_rows_quietly(directory: Path) -> list[dict]:
    """Every summary row including the failed ones, or nothing if unreadable.

    ``load_sweep`` drops failed runs on purpose - a chart of a crashed run is a
    lie - but the index should say out loud that some runs failed rather than
    quietly showing fewer seeds than the recipe asked for.
    """
    try:
        return load_rows(directory / "summary.csv")
    except SweepDataError:
        return []


def _meta_rows(data: SweepData, directory: Path, knob: str, captions: list[str]) -> list[tuple[str, str]]:
    """What actually ran, for the foot of the index.

    Read from the sweep's own outputs rather than from its recipe, so the page
    cannot describe a configuration that did not run - the same rule the chart
    captions follow.
    """
    commits = {row["git_commit"] for row in data.summary if row.get("git_commit")}
    started = sorted(row["started_at_utc"] for row in data.summary if row.get("started_at_utc"))
    seconds = sum(row["elapsed_seconds"] for row in data.summary if row.get("elapsed_seconds"))
    failed = sum(1 for row in load_rows_quietly(directory) if row.get("status") != "ok")
    rows = [
        ("serie", directory.name),
        ("varía", f"{knob} — {', '.join(data.variants)}"),
        ("seeds", ", ".join(str(seed) for seed in data.seeds)),
        ("corridas", f"{len(data.summary)} exitosas"
                     + (f", {failed} fallidas" if failed else "")),
        ("tiempo total", f"{seconds:.0f} s de cómputo"),
    ]
    rows += [(label, value) for label, value in (
        ("configuración fija", captions[0][len("Fijo: "):] if captions else ""),
        ("problema", captions[1][len("Problema: "):] if len(captions) > 1 else ""),
    ) if value]
    if started:
        rows.append(("primera corrida", started[0]))
    if commits:
        rows.append(("commit", ", ".join(sorted(commits))))
    return rows


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="analysis/plots_main.py",
        description="Draw every chart of one sweep from its CSVs, plus the index.html "
                    "that links them.",
    )
    parser.add_argument(
        "sweep", nargs="?", default=None,
        help="sweep results directory (default: the most recent one)",
    )
    parser.add_argument(
        "--out", default=None,
        help="where to write the HTMLs (default: inside the sweep directory)",
    )
    parser.add_argument(
        "--x", dest="x_column", default="generation", choices=sorted(X_COLUMNS),
        help="draw the trajectory charts against a SECOND axis as well as "
             "generations. Use cumulative_evaluations for sweeps where a "
             "generation costs different amounts per variant - population size, "
             "shape count - since there equal generations is not equal work. "
             "Both versions end up in the same index.",
    )
    parser.add_argument(
        "--abrir", action="store_true",
        help="open the index in the browser when it is done",
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

    fixed = fixed_config(directory)
    captions = fixed_captions(fixed)
    knob = varied_knob(directory)
    is_survival = "operators.survival.name" in varied_paths(directory)
    out_dir = Path(args.out) if args.out else directory

    print(f"sweep:     {directory}")
    print(f"varía:     {knob}")
    print(f"variantes: {', '.join(data.variants)}")
    print(f"seeds:     {', '.join(str(seed) for seed in data.seeds)}")
    for caption in captions:
        print(f"  {caption}")

    try:
        # Generations always, plus the requested axis when it is a different
        # one: writing only the alternate would leave the default-axis charts on
        # disk but unlinked from the index that is supposed to front them.
        charts = trajectory_charts(data, captions, "generation")
        if args.x_column != "generation":
            charts += trajectory_charts(data, captions, args.x_column)
        # A single-variant sweep has a trajectory but nothing to compare, so the
        # comparison half is skipped instead of failing the whole run.
        if len(data.variants) > 1:
            charts += comparison_charts(data, captions, knob, is_survival)
            tables = summary_tables(data, is_survival)
        else:
            print("\naviso: una sola variante, se omite la comparación entre variantes")
            tables = []
    except (SweepDataError, ComparisonError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 1

    print()
    for chart, figure in charts:
        write_html(figure, out_dir / chart.filename)
        print(f"  {chart.filename}")

    page = IndexPage(
        heading=f"TP2 · {knob}",
        subtitle=f"{', '.join(data.variants)} · {len(data.seeds)} seeds · "
                 f"{len(charts)} gráficos",
        lead="Cada variante corre las mismas seeds, y una seed fija la población "
             "inicial y todo el stream del RNG: las corridas están pareadas y se "
             "separan únicamente por lo que la serie varía. Los gráficos de "
             "trayectoria cuentan qué pasó; los de comparación, si la diferencia "
             "entre dos variantes es un resultado o es dispersión entre seeds.",
        meta_rows=_meta_rows(data, directory, knob, captions),
        tables=tables,
    )
    index = write_index(out_dir / "index.html", page, [chart for chart, _ in charts])
    print(f"\níndice:   {index}")

    if tables:
        print_tables(tables)
    if args.abrir:
        webbrowser.open(index.as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
