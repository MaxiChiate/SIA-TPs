#!/usr/bin/env python3
"""CLI for a series' charts: writes all of them plus the index.html that fronts them.

    python3 analysis/plots_main.py                       # every series under analysis/results
    python3 analysis/plots_main.py analysis/results/series_eta_2026-10-04_18-56-21
    python3 analysis/plots_main.py --x elapsed_s --tablas --abrir

Needs plotly (`pip install -r analysis/requirements.txt`); `sweep.py` and its report.html don't.

One command and one entry point: the charts of a series are read together (the trajectory says what
happened, the comparison says whether it is a result), and splitting them across commands only invites
presenting half. Written next to the series' CSVs:

    index.html        links every chart below, plus the summary tables and the config the runs used
    validation.html   validation MSE per epoch, averaged over seeds
    train.html        train MSE per epoch
    gap.html          validation minus train: the generalization gap
    compare_*.html    final dots per seed, boxplot, paired differences or rank stability, convergence
                      speed, cost against quality, generalization and (when there is one) accuracy
    plotly.min.js     the plotly.js the charts share

and `analysis/results/index.html`, the landing page over every series.

Every curve marks the full min-max range across seeds with error bars, so a difference between two
variants can be read against the spread that produced it. `--x elapsed_s` plots the trajectory charts
against training time as well as epochs, for the series where an epoch doesn't cost the same in every
variant (batch_size, architecture); those charts get the axis name as a suffix, so both sit side by side.
"""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

import plotly.graph_objects as go

from plots_compare import ComparisonError, comparison_charts, print_tables, summary_tables
from plots_data import (
    X_COLUMNS, SweepData, SweepDataError, curve_bands, fixed_captions, fixed_config, generalization_gap,
    load_sweep, load_summary_rows, sweep_catalog, varied_knob,
)
from plots_index import Chart, IndexPage, catalog_page, write_index
from plots_style import (
    ERROR_MARKS, add_error_bars, as_axis_value, base_layout, end_label, is_log_scale, palette_for, write_html,
)

DEFAULT_RESULTS = Path(__file__).resolve().parent / "results"


def _end_labels(curves: dict[str, tuple[list[float], list[float]]], colors: dict[str, str], log: bool) -> list[dict]:
    """Direct labels at the line ends, skipping the ones that would overlap.

    Curves that converge end within a hair of each other, so labelling every line stacks unreadable text.
    The separated ones get a label; the legend and the unified hover cover the rest.
    """
    if not curves:
        return []
    finals = sorted(((as_axis_value(ys[-1], log), xs[-1], variant) for variant, (xs, ys) in curves.items()),
                    reverse=True)
    all_values = [as_axis_value(value, log) for _, ys in curves.values() for value in ys]
    minimum_gap = (max(all_values) - min(all_values)) * 0.045

    labels: list[dict] = []
    last_placed: float | None = None
    for value, x, variant in finals:
        if last_placed is None or abs(last_placed - value) >= minimum_gap:
            labels.append(end_label(variant, x, value, colors[variant]))
            last_placed = value
    return labels


def _curve_figure(data: SweepData, value, title: str, y_title: str, captions: list[str],
                  x_column: str = "epoch", allow_log: bool = True) -> go.Figure:
    """One line per variant, averaged over seeds, over its min-max seed band."""
    colors = palette_for(data.variants)
    bands = curve_bands(data, value, x_column=x_column)
    if not bands:
        raise SweepDataError(f"no data to plot for {title!r}")

    figure = go.Figure()
    for variant, band in bands.items():
        figure.add_trace(go.Scatter(x=band.x, y=band.mean, name=variant, mode="lines",
                                    line={"color": colors[variant], "width": 2},
                                    hovertemplate="%{y:.4g}<extra></extra>"))
    # Each variant samples its bars at a different offset, so the bars interleave along x
    for position, (variant, band) in enumerate(bands.items()):
        add_error_bars(figure, band.error_marks(ERROR_MARKS, phase=position / max(len(bands), 1)), colors[variant])

    log = allow_log and is_log_scale([v for band in bands.values() for v in (*band.low, *band.high)])
    layout = base_layout(
        title, [f"Media de {len(data.seeds)} seeds; las barras de error marcan el rango completo entre ellas"
                + (" · escala logarítmica" if log else ""), *captions],
        X_COLUMNS[x_column], y_title)
    layout["annotations"] = _end_labels({variant: (band.x, band.mean) for variant, band in bands.items()}, colors, log)
    if log:
        layout["yaxis"]["type"] = "log"
    figure.update_layout(**layout)
    return figure


def trajectory_charts(data: SweepData, captions: list[str], x_column: str) -> list[tuple[Chart, go.Figure]]:
    """The per-epoch charts, with their index entries."""
    suffix = "" if x_column == "epoch" else f"_{x_column}"
    axis = X_COLUMNS[x_column].lower()
    # The extra-axis charts share the index with the default ones, so their entries must say which axis they are
    against = "" if not suffix else f" (contra {axis})"
    return [
        (Chart(f"validation{suffix}.html", f"MSE de validación{against}",
               f"Error sobre las muestras que la red no ve, contra {axis}. Es la curva que resume la serie: dice qué "
               "tan bien generaliza cada variante y cuándo deja de mejorar.", group="trayectoria"),
         _curve_figure(data, "validation_mse", "MSE de validación", "MSE de validación", captions, x_column)),
        (Chart(f"train{suffix}.html", f"MSE de train{against}",
               f"Error sobre las muestras con las que se entrena, contra {axis}. Lo que minimiza el entrenamiento "
               "(la época 0 son los pesos iniciales).", group="trayectoria"),
         _curve_figure(data, "train_mse", "MSE de train", "MSE de train", captions, x_column)),
        (Chart(f"gap{suffix}.html", f"Brecha de generalización{against}",
               "Validación menos train. Si crece mientras train baja, la red memoriza en vez de aprender; si se queda "
               "en cero con los dos altos, subajusta.", group="trayectoria"),
         _curve_figure(data, generalization_gap, "Brecha de generalización: validación − train",
                       "MSE de validación − MSE de train", captions, x_column, allow_log=False)),
    ]


def _meta_rows(data: SweepData, directory: Path, knob: str, captions: list[str]) -> list[tuple[str, str]]:
    """What actually ran, for the foot of the index, read from the series' own outputs."""
    failed = sum(row["status"] != "ok" for row in load_summary_rows(directory))
    seconds = sum(row["elapsed_s"] for row in data.summary if row.get("elapsed_s"))
    rows = [
        ("serie", directory.name),
        ("varía", f"{knob}: {', '.join(data.variants)}"),
        ("seeds", ", ".join(str(seed) for seed in data.seeds)),
        ("corridas", f"{len(data.summary)} exitosas" + (f", {failed} fallidas" if failed else "")),
        ("tiempo total", f"{seconds:.0f} s de entrenamiento"),
    ]
    rows += [(line.split(":")[0].lower(), line.split(": ", 1)[1]) for line in captions]
    return rows


def is_up_to_date(directory: Path, out_dir: Path) -> bool:
    """Whether `out_dir` already holds an index newer than the series' CSVs.

    Redrawing every series on every invocation is the price of one command covering them all; comparing
    mtimes keeps the common case (one new series, several unchanged) fast. `--force` is the override.
    """
    index = out_dir / "index.html"
    if not index.is_file():
        return False
    newest_input = max((path.stat().st_mtime for name in ("summary.csv", "plan.json")
                        if (path := directory / name).is_file()), default=0.0)
    return index.stat().st_mtime >= newest_input


def render_sweep(directory: Path, out_dir: Path, x_column: str, show_tables: bool) -> tuple[int, str]:
    """Draw one series' charts and its index. Returns `(chart count, knob)`."""
    data = load_sweep(directory)
    captions = fixed_captions(fixed_config(data.plan))
    knob = varied_knob(directory, data.plan)

    # Epochs always, plus the requested axis when it is a different one: writing only the alternate would
    # leave the default charts on disk but unlinked from the index that is supposed to front them
    charts = trajectory_charts(data, captions, "epoch")
    if x_column != "epoch":
        charts += trajectory_charts(data, captions, x_column)

    # A single variant has a trajectory but nothing to compare, so the comparison half is skipped
    tables = []
    if len(data.variants) > 1:
        charts += comparison_charts(data, captions, knob)
        tables = summary_tables(data)

    for chart, figure in charts:
        write_html(figure, out_dir / chart.href)
    if show_tables:
        print_tables(tables)

    page = IndexPage(
        heading=f"TP3 · {knob}",
        subtitle=f"{', '.join(data.variants)} · {len(data.seeds)} seeds · {len(charts)} gráficos",
        lead="Cada variante corre las mismas seeds, y una seed fija los pesos iniciales (y el orden del shuffle): las "
             "corridas están pareadas y se separan únicamente por lo que la serie varía. Los gráficos de trayectoria "
             "cuentan qué pasó; los de comparación, si la diferencia entre dos variantes es un resultado o es "
             "dispersión entre seeds.",
        meta_rows=_meta_rows(data, directory, knob, captions), tables=tables)
    write_index(out_dir / "index.html", page, [chart for chart, _ in charts])
    return len(charts), knob


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="analysis/plots_main.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sweep", nargs="?", type=Path,
                        help="only redraw this series directory (default: every series under analysis/results); "
                             "the landing page is rewritten either way")
    parser.add_argument("--out", type=Path,
                        help="root to write into (default: the results directory itself); each series gets its "
                             "own subdirectory")
    parser.add_argument("--x", dest="x_column", default="epoch", choices=sorted(X_COLUMNS),
                        help="draw the trajectory charts against a second axis as well as epochs; use elapsed_s "
                             "for series where an epoch costs different amounts per variant")
    parser.add_argument("--force", action="store_true", help="redraw series whose index is newer than their CSVs")
    parser.add_argument("--tablas", action="store_true", help="also print the summary tables to the terminal")
    parser.add_argument("--abrir", action="store_true", help="open the landing page in the browser when done")
    return parser.parse_args(argv[1:])


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = args.out or DEFAULT_RESULTS

    if args.sweep:
        targets = [args.sweep]
    else:
        targets = [summary.directory for summary in sweep_catalog(DEFAULT_RESULTS)]
        if not targets:
            print(f"error: no series under {DEFAULT_RESULTS}: run analysis/sweep.py first", file=sys.stderr)
            return 1

    failures = 0
    for directory in targets:
        out_dir = root / directory.name if args.out else directory
        if not args.force and is_up_to_date(directory, out_dir):
            print(f"  {directory.name}  al día, se saltea")
            continue
        try:
            count, knob = render_sweep(directory, out_dir, args.x_column, args.tablas)
        except (SweepDataError, ComparisonError) as error:
            # One unusable series must not cost the landing page or the others
            print(f"  {directory.name}  error: {error}", file=sys.stderr)
            failures += 1
            continue
        print(f"  {directory.name}  {knob}: {count} gráficos")

    page, entries = catalog_page(sweep_catalog(DEFAULT_RESULTS))
    landing = write_index(root / "index.html", page, entries)
    print(f"\nlanding: {landing}")
    if args.abrir:
        webbrowser.open(landing.as_uri())
    return 1 if failures and failures == len(targets) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
