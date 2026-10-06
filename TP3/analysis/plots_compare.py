"""Statistical comparison of a series' variants: is a difference a result or noise?

Charts and summary tables; `plots_main.py` is the CLI that writes them. They work on any series (eta,
architecture, batch size, activation, shuffle...) because every one asks the same question.

Why this and not more curves: curves show the trajectory, and a trajectory can't say whether two variants
really differ. These answer that, using the fact that every variant runs the same seeds: a seed fixes the
initial weights (and the shuffling), so the runs are paired and the comparison doesn't spend its resolution
on the between-seed spread.

The statistics are standard library only, in paired_stats.py: an exact sign-flip permutation test over 2^n
pairings, a percentile bootstrap, and Holm's correction for testing several variants against the leader.

Unlike fitness, the errors here are minimized: a Metric says which direction is better, and everything
that ranks or pairs variants reads it from there.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass

import plotly.graph_objects as go

from paired_stats import bootstrap_interval, holm_adjust, permutation_p_value
from plots_data import SweepData, final_values
from plots_index import Chart, Table
from plots_style import TEXT_SECONDARY, base_layout, is_log_scale, palette_for, translucent


BAND_ALPHA = 0.13


class ComparisonError(Exception):
    """The series has nothing comparable: one variant, or no shared seed."""


@dataclass(frozen=True)
class Metric:
    """A final per-run number from summary.csv, and which way is better."""

    column: str
    label: str
    lower_is_better: bool
    scale: float = 1.0  # accuracy is stored as a share and shown in percent
    fmt: str = ".4g"

    def show(self, value: float) -> str:
        return format(value, self.fmt)


METRICS = {
    "validation_mse": Metric("validation_mse", "MSE de validación", True),
    "accuracy": Metric("accuracy", "Aciertos de validación (%)", False, 100.0, ".2f"),
}
PRIMARY = METRICS["validation_mse"]


# ---------------------------------------------------------------------------
# Shaping
# ---------------------------------------------------------------------------

Values = dict[str, dict[int, float]]  # variant -> seed -> final value


def final_by_seed(data: SweepData, metric: Metric) -> Values:
    out: Values = defaultdict(dict)
    for row in data.summary:
        if row.get(metric.column) is not None:
            out[row["variant"]][row["seed"]] = metric.scale * row[metric.column]
    return out


def has_metric(data: SweepData, metric: Metric) -> bool:
    return any(row.get(metric.column) is not None for row in data.summary)


def shared_seeds(values: Values, variants) -> list[int]:
    """The seeds every variant completed: the ones that can be paired."""
    sets = [set(values.get(variant, {})) for variant in variants]
    return sorted(set.intersection(*sets)) if sets else []


def best_first(values: Values, variants, metric: Metric) -> list[str]:
    """Variants by mean, best first, so every chart here reads as a ranking."""
    return sorted((v for v in variants if values.get(v)),
                  key=lambda v: statistics.fmean(values[v].values()), reverse=not metric.lower_is_better)


def paired_improvements(values: Values, first: str, second: str, metric: Metric) -> tuple[list[int], list[float]]:
    """Per seed, how much better `first` is than `second` (positive: `first` wins), over the seeds both ran.

    The pairing is what makes a few seeds enough to say anything: a seed fixes the initial weights, so two
    variants start from the same network and diverge only through what the series varies.
    """
    seeds = shared_seeds(values, (first, second))
    if not seeds:
        raise ComparisonError(f"no seed ran both '{first}' and '{second}'; nothing to pair")
    sign = -1.0 if metric.lower_is_better else 1.0
    return seeds, [sign * (values[first][seed] - values[second][seed]) for seed in seeds]


def ranks_by_seed(values: Values, variants, metric: Metric) -> dict[str, list[float]]:
    """Per variant, its rank within each shared seed (1 = best), ties averaged.

    The scale-free companion to the mean: ranking inside a seed cancels out how lucky that initialization
    was, so a variant that is second by a hair on every seed doesn't read like one that wins half and
    collapses on the rest.
    """
    out: dict[str, list[float]] = {variant: [] for variant in variants}
    for seed in shared_seeds(values, variants):
        ordered = sorted(variants, key=lambda v: values[v][seed], reverse=not metric.lower_is_better)
        position = 0
        while position < len(ordered):
            tied = [v for v in ordered if values[v][seed] == values[ordered[position]][seed]]
            average = statistics.fmean(range(position + 1, position + 1 + len(tied)))
            for variant in tied:
                out[variant].append(average)
            position += len(tied)
    return out


def common_threshold(data: SweepData) -> float:
    """The validation MSE that *every* run reached at some epoch: the hardest bar all of them clear.

    Speed is only comparable against a bar all the runs clear; taking the winner's error would leave the
    weaker variants never reaching it and a chart of missing values.
    """
    best_by_run: dict[tuple[str, int], float] = {}
    for row in data.history:
        if row.get("validation_mse") is not None:
            key = (row["variant"], row["seed"])
            best_by_run[key] = min(best_by_run.get(key, float("inf")), row["validation_mse"])
    if not best_by_run:
        raise ComparisonError("no run reported a validation MSE")
    return max(best_by_run.values())


def epochs_to_threshold(data: SweepData, threshold: float) -> Values:
    """`variant -> seed -> first epoch whose validation MSE is at or under threshold`."""
    out: Values = defaultdict(dict)
    for row in data.history:
        mse = row.get("validation_mse")
        if mse is None or mse > threshold:
            continue
        seen = out[row["variant"]]
        if seen.get(row["seed"], row["epoch"] + 1) > row["epoch"]:
            seen[row["seed"]] = float(row["epoch"])
    return out


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def _boxplot(values: Values, variants, colors: dict[str, str], title: str, subtitles: list[str], y_title: str,
             log: bool = False) -> go.Figure:
    """Boxplot with every seed drawn beside its box: with a few seeds the box summarizes visible data, it
    doesn't replace it."""
    figure = go.Figure()
    for variant in variants:
        seen = list(values.get(variant, {}).values())
        if not seen:
            continue
        figure.add_trace(go.Box(
            y=seen, name=variant, marker={"color": colors[variant], "size": 7},
            line={"color": colors[variant], "width": 2}, fillcolor=translucent(colors[variant], BAND_ALPHA),
            boxpoints="all", jitter=0.5, pointpos=1.7, boxmean=True,
            hovertemplate="%{y:.4g}<extra></extra>", showlegend=False))
    layout = base_layout(title, subtitles, "", y_title)
    layout["showlegend"] = False
    layout["xaxis"]["showgrid"] = False
    layout["margin"] = {**layout["margin"], "r": 90, "b": 70}
    if log:
        layout["yaxis"]["type"] = "log"
    figure.update_layout(**layout)
    return figure


def _dot_rows(figure: go.Figure, rows: list[tuple[str, list[float]]], colors: dict[str, str], value_label: str,
              mean_text: str) -> list[dict]:
    """One hollow dot per seed and a filled diamond at the mean, one row per variant; returns the right-margin
    labels (next to the diamond a seed dot could sit under the text)."""
    labels = []
    for variant, seen in rows:
        mean = statistics.fmean(seen)
        figure.add_trace(go.Scatter(
            x=seen, y=[variant] * len(seen), mode="markers",
            marker={"color": "#ffffff", "size": 10, "line": {"color": colors[variant], "width": 2}},
            hovertemplate=f"{value_label}: %{{x:.4g}}<extra></extra>", showlegend=False))
        figure.add_trace(go.Scatter(
            x=[mean], y=[variant], mode="markers",
            marker={"color": colors[variant], "size": 13, "symbol": "diamond"},
            hovertemplate=f"media: %{{x:.4g}}<extra></extra>", showlegend=False))
        labels.append({"x": 1, "xref": "paper", "xanchor": "left", "y": variant, "yref": "y", "yanchor": "middle",
                       "text": f"  {mean_text.format(mean)}", "showarrow": False,
                       "font": {"color": TEXT_SECONDARY, "size": 11}})
    return labels


def comparison_figure(data: SweepData, captions: list[str], metric: Metric) -> go.Figure:
    """Final value per variant: one hollow dot per seed plus a filled mean.

    A dot plot and not bars: dots encode position, so a zoomed or log axis is honest, while a bar's length
    *is* the value and a truncated one lies. The per-seed dots are the point of the chart: if one variant's
    seeds spread wider than the gap between two variants, that gap is not a result.
    """
    colors = palette_for(data.variants)
    values = final_values(data, metric.column, metric.scale)
    ranked = list(reversed(best_first({v: dict(enumerate(s)) for v, s in values.items()}, data.variants, metric)))

    figure = go.Figure()
    labels = _dot_rows(figure, [(v, values[v]) for v in ranked], colors, "seed", "{:" + metric.fmt + "}")

    layout = base_layout(f"{metric.label} final por variante",
                         ["Rombo = media de las seeds · círculo = cada seed por separado", *captions],
                         metric.label, "")
    layout["hovermode"] = "closest"
    layout["showlegend"] = False
    layout["yaxis"]["showgrid"] = False
    layout["annotations"] = labels
    flat = [value for variant in ranked for value in values[variant]]
    if metric.lower_is_better and is_log_scale(flat):
        layout["xaxis"]["type"] = "log"
    else:
        span = max(flat) - min(flat)
        pad = span * 0.15 if span else abs(max(flat)) * 0.05 or 0.01
        layout["xaxis"]["range"] = [min(flat) - pad, max(flat) + pad]
    layout["margin"] = {**layout["margin"], "l": 160, "r": 90, "b": 60}
    figure.update_layout(**layout)
    return figure


def distribution_figure(data: SweepData, captions: list[str], knob: str, metric: Metric) -> go.Figure:
    """The headline comparison, with its spread."""
    colors = palette_for(data.variants)
    values = final_by_seed(data, metric)
    flat = [v for per_seed in values.values() for v in per_seed.values()]
    return _boxplot(
        values, best_first(values, data.variants, metric), colors, f"{metric.label} final por {knob}",
        ["Caja = cuartiles y mediana · línea punteada = media · un punto por seed "
         f"({len(data.seeds)} corridas por variante) · ordenado de mejor a peor", *captions],
        metric.label, log=metric.lower_is_better and is_log_scale(flat))


def paired_figure(data: SweepData, captions: list[str], knob: str, metric: Metric) -> go.Figure:
    """Per-seed improvement of the better variant over the other, plus its mean and CI.

    One bar per seed rather than two boxes: the seeds are paired, so the difference is a measurement in its
    own right. A bar below zero is a seed where the ranking flipped.
    """
    values = final_by_seed(data, metric)
    first, second = best_first(values, data.variants, metric)
    colors = palette_for(data.variants)
    seeds, improvements = paired_improvements(values, first, second, metric)
    mean = statistics.fmean(improvements)
    low, high = bootstrap_interval(improvements)
    p_value, exact = permutation_p_value(improvements)
    wins = sum(d > 0 for d in improvements)

    figure = go.Figure()
    figure.add_trace(go.Bar(
        x=[f"seed {seed}" for seed in seeds], y=improvements,
        marker={"color": [translucent(colors[first] if d > 0 else colors[second], 0.55) for d in improvements],
                "line": {"color": [colors[first] if d > 0 else colors[second] for d in improvements], "width": 1.5}},
        hovertemplate="%{y:+.4g}<extra></extra>", showlegend=False))
    # The mean and its interval ride in their own column past the seeds, on the scale of the values they summarize
    figure.add_trace(go.Scatter(
        x=["media"], y=[mean], mode="markers", marker={"color": TEXT_SECONDARY, "size": 13, "symbol": "diamond"},
        error_y={"type": "data", "symmetric": False, "array": [high - mean], "arrayminus": [mean - low],
                 "color": TEXT_SECONDARY, "thickness": 2, "width": 8},
        hovertemplate=f"media {mean:+.4g} · IC95% [{low:+.4g}, {high:+.4g}]<extra></extra>", showlegend=False))

    layout = base_layout(
        f"Diferencia pareada por seed: {first} contra {second}",
        [f"Cada seed fija los pesos iniciales, así que las dos variantes arrancan de la misma red · "
         f"barras arriba de 0 = gana {first}",
         f"{first} gana {wins} de {len(improvements)} seeds · media {mean:+.4g} · IC95% bootstrap "
         f"[{low:+.4g}, {high:+.4g}] · test de permutación pareado p{'' if exact else ' aprox.'} = {p_value:.4f}",
         *captions],
        "", f"Mejora de {metric.label} ({first} sobre {second})")
    layout["showlegend"] = False
    layout["xaxis"]["showgrid"] = False
    layout["shapes"] = [{"type": "line", "xref": "paper", "x0": 0, "x1": 1, "yref": "y", "y0": 0, "y1": 0,
                         "line": {"color": TEXT_SECONDARY, "width": 1}}]
    layout["margin"] = {**layout["margin"], "r": 90, "b": 80}
    figure.update_layout(**layout)
    return figure


def ranking_figure(data: SweepData, captions: list[str], knob: str, metric: Metric) -> go.Figure:
    """Mean rank per variant with the full range of ranks it took across seeds.

    What replaces the paired chart once there are more than two variants: the rank a variant took *within
    each seed* is still paired, and its range answers what the mean can't: is this ordering stable, or did
    it depend on the seed. A variant whose range spans the whole field didn't really win.
    """
    colors = palette_for(data.variants)
    values = final_by_seed(data, metric)
    ordered = best_first(values, data.variants, metric)
    ranks = ranks_by_seed(values, ordered, metric)

    figure = go.Figure()
    labels = []
    for variant in reversed(ordered):  # best on top
        seen = ranks[variant]
        if not seen:
            continue
        mean = statistics.fmean(seen)
        figure.add_trace(go.Scatter(
            x=[min(seen), max(seen)], y=[variant, variant], mode="lines",
            line={"color": translucent(colors[variant], 0.45), "width": 6}, hoverinfo="skip", showlegend=False))
        figure.add_trace(go.Scatter(
            x=seen, y=[variant] * len(seen), mode="markers",
            marker={"color": "#ffffff", "size": 9, "line": {"color": colors[variant], "width": 2}},
            hovertemplate="puesto %{x}<extra></extra>", showlegend=False))
        figure.add_trace(go.Scatter(
            x=[mean], y=[variant], mode="markers", marker={"color": colors[variant], "size": 13, "symbol": "diamond"},
            hovertemplate="puesto medio %{x:.2f}<extra></extra>", showlegend=False))
        labels.append({"x": 1, "xref": "paper", "xanchor": "left", "y": variant, "yref": "y", "yanchor": "middle",
                       "text": f"  {mean:.2f}", "showarrow": False, "font": {"color": TEXT_SECONDARY, "size": 11}})

    layout = base_layout(
        f"Puesto por seed: qué tan estable es el ranking de {knob}",
        ["Rombo = puesto medio · círculos = el puesto que tomó en cada seed · barra = rango completo · "
         f"1 = mejor {metric.label} de esa seed", *captions],
        "Puesto dentro de la seed", "")
    layout["hovermode"] = "closest"
    layout["showlegend"] = False
    layout["yaxis"]["showgrid"] = False
    layout["xaxis"]["dtick"] = 1
    layout["annotations"] = labels
    layout["margin"] = {**layout["margin"], "l": 190, "r": 90, "b": 60}
    figure.update_layout(**layout)
    return figure


def speed_figure(data: SweepData, captions: list[str], knob: str) -> go.Figure:
    """Epochs each variant needed to reach a validation MSE every run cleared.

    Separates "better" from "faster": a variant that ends higher but gets there in a third of the epochs is
    the right choice under an epoch budget, and no curve read at the last epoch will tell you that.
    """
    colors = palette_for(data.variants)
    threshold = common_threshold(data)
    values = epochs_to_threshold(data, threshold)
    ordered = sorted((v for v in data.variants if values.get(v)), key=lambda v: statistics.fmean(values[v].values()))
    return _boxplot(
        values, ordered, colors, f"Velocidad de convergencia por {knob}",
        [f"Épocas hasta un MSE de validación de {threshold:.4g}: el umbral más exigente que alcanzan todas las "
         "corridas de todas las variantes · menos es mejor", *captions],
        "Épocas hasta el umbral")


def tradeoff_figure(data: SweepData, captions: list[str], knob: str) -> go.Figure:
    """Training time against final validation MSE, one dot per run: what each variant pays for its quality."""
    colors = palette_for(data.variants)
    figure = go.Figure()
    for variant in data.variants:
        rows = [row for row in data.summary
                if row["variant"] == variant and row.get("elapsed_s") is not None and row.get("validation_mse") is not None]
        if not rows:
            continue
        figure.add_trace(go.Scatter(
            x=[row["elapsed_s"] for row in rows], y=[row["validation_mse"] for row in rows], name=variant,
            mode="markers", marker={"color": translucent(colors[variant], 0.55), "size": 11,
                                    "line": {"color": colors[variant], "width": 2}},
            text=[f"seed {row['seed']}" for row in rows],
            hovertemplate="%{text}<br>%{x:.3g} s<br>MSE %{y:.4g}<extra></extra>"))
    layout = base_layout(f"Costo contra calidad por {knob}",
                         ["Un punto por corrida · abajo = menor error de validación, izquierda = entrena más rápido",
                          *captions], "Segundos de entrenamiento", "MSE de validación")
    layout["hovermode"] = "closest"
    if is_log_scale([row["validation_mse"] for row in data.summary if row.get("validation_mse") is not None]):
        layout["yaxis"]["type"] = "log"
    figure.update_layout(**layout)
    return figure


def generalization_figure(data: SweepData, captions: list[str], knob: str) -> go.Figure:
    """Train MSE (best epoch) against validation MSE, one dot per run, over the y = x diagonal.

    A dot on the diagonal generalizes as well as it fits; above it the network does worse on samples it
    never trained on. Tells apart "underfits" (both high) from "overfits" (train low, validation high).
    """
    colors = palette_for(data.variants)
    rows_by_variant = {variant: [row for row in data.summary if row["variant"] == variant
                                 and row.get("train_mse") is not None and row.get("validation_mse") is not None]
                       for variant in data.variants}
    everything = [value for rows in rows_by_variant.values() for row in rows
                  for value in (row["train_mse"], row["validation_mse"])]
    log = is_log_scale(everything)

    figure = go.Figure()
    low, high = min(everything), max(everything)
    figure.add_trace(go.Scatter(x=[low, high], y=[low, high], mode="lines", hoverinfo="skip", showlegend=False,
                                line={"color": TEXT_SECONDARY, "width": 1.5, "dash": "dot"}))
    for variant, rows in rows_by_variant.items():
        if not rows:
            continue
        figure.add_trace(go.Scatter(
            x=[row["train_mse"] for row in rows], y=[row["validation_mse"] for row in rows], name=variant,
            mode="markers", marker={"color": translucent(colors[variant], 0.55), "size": 11,
                                    "line": {"color": colors[variant], "width": 2}},
            text=[f"seed {row['seed']}" for row in rows],
            hovertemplate="%{text}<br>train %{x:.4g}<br>validación %{y:.4g}<extra></extra>"))
    layout = base_layout(f"Generalización por {knob}",
                         ["Un punto por corrida · punteada = validación igual a train · arriba = peor sobre "
                          "muestras que no vio", *captions],
                         "MSE de train (mejor época)", "MSE de validación")
    layout["hovermode"] = "closest"
    if log:
        layout["xaxis"]["type"] = layout["yaxis"]["type"] = "log"
    figure.update_layout(**layout)
    return figure


# ---------------------------------------------------------------------------
# Summary tables
# ---------------------------------------------------------------------------

def metric_table(data: SweepData, metric: Metric) -> Table:
    values = final_by_seed(data, metric)
    ordered = best_first(values, data.variants, metric)
    ranks = ranks_by_seed(values, ordered, metric)
    rows = []
    for variant in ordered:
        seen = list(values[variant].values())
        deviation = statistics.stdev(seen) if len(seen) > 1 else 0.0
        rank = statistics.fmean(ranks[variant]) if ranks.get(variant) else float("nan")
        rows.append([variant, str(len(seen)), *(metric.show(v) for v in (
            statistics.fmean(seen), deviation, statistics.median(seen), min(seen), max(seen))), f"{rank:.2f}"])
    return Table(
        title=f"{metric.label} final", headers=["variante", "n", "media", "desvío", "mediana", "mín", "máx", "puesto"],
        rows=rows, highlight_first_row=True,
        note="Ordenado de mejor a peor. 'Puesto' es el promedio del lugar que sacó la variante dentro de cada "
             "seed: la misma comparación pero sin escala, así que no la domina una seed que salió fácil para todos.")


def speed_table(data: SweepData, ordered: list[str]) -> Table:
    threshold = common_threshold(data)
    reached = epochs_to_threshold(data, threshold)
    rows = []
    for variant in ordered:
        epochs = list(reached.get(variant, {}).values())
        times = [row["elapsed_s"] for row in data.summary if row["variant"] == variant and row.get("elapsed_s") is not None]
        if epochs:
            rows.append([variant, f"{statistics.median(epochs):.1f}", f"{min(epochs):.0f}", f"{max(epochs):.0f}",
                         f"{statistics.fmean(times):.3g}" if times else "–"])
    return Table(
        title="Velocidad y costo", headers=["variante", "épocas (mediana)", "mín", "máx", "segundos de entrenamiento"],
        rows=rows,
        note=f"Épocas hasta un MSE de validación de {threshold:.4g}, el umbral más exigente que alcanzan todas las "
             "corridas de todas las variantes. Menos es mejor.")


def paired_table(data: SweepData, metric: Metric) -> Table | None:
    """Every variant against the leader: the question a report answers is "is the winner really the winner",
    and k(k-1)/2 tests would spend the correction's budget on comparisons nobody reads."""
    values = final_by_seed(data, metric)
    ordered = best_first(values, data.variants, metric)
    if len(ordered) < 2:
        return None
    leader, *rest = ordered
    computed = []
    for variant in rest:
        _, improvements = paired_improvements(values, leader, variant, metric)
        p_value, exact = permutation_p_value(improvements)
        computed.append((variant, improvements, p_value, exact))
    adjusted = holm_adjust([row[2] for row in computed])

    rows = []
    for (variant, improvements, p_value, exact), corrected in zip(computed, adjusted):
        low, high = bootstrap_interval(improvements)
        wins = sum(d > 0 for d in improvements)
        rows.append([variant, f"{wins}/{len(improvements)}", f"{statistics.fmean(improvements):+.4g}",
                     f"[{low:+.4g}, {high:+.4g}]", f"{'' if exact else '~'}{p_value:.4f}", f"{corrected:.4f}"])
    note = ("Cada seed fija los pesos iniciales, así que las dos corridas de un par arrancan de la misma red y se "
            "separan solo por lo que la serie varía. 'Δ media' es cuánto mejora el líder en promedio. El test de "
            "permutación es exacto (2^n asignaciones de signo) y el IC es bootstrap percentil.")
    if len(rows) > 1:
        note += " 'p (Holm)' corrige por comparar varias variantes contra el mismo líder; es el valor a citar."
    return Table(title=f"Comparación pareada contra '{leader}' ({metric.label})",
                 headers=["variante", f"gana {leader}", "Δ media", "IC95%", "p", "p (Holm)"], rows=rows, note=note)


def summary_tables(data: SweepData) -> list[Table]:
    """The numbers behind the charts, as rows both the terminal and the index render: a report needs the
    figures themselves, and retyping them off a hover tooltip is how a wrong number gets quoted."""
    tables = [metric_table(data, PRIMARY)]
    if has_metric(data, METRICS["accuracy"]):
        tables.append(metric_table(data, METRICS["accuracy"]))
    tables.append(speed_table(data, best_first(final_by_seed(data, PRIMARY), data.variants, PRIMARY)))
    paired = paired_table(data, PRIMARY)
    if paired is not None:
        tables.append(paired)
    return tables


def print_tables(tables: list[Table]) -> None:
    """Render the summary tables to stdout, columns padded to their widest cell."""
    for table in tables:
        print(f"\n{table.title}")
        grid = [list(table.headers), *(list(row) for row in table.rows)]
        widths = [max(len(row[i]) for row in grid) for i in range(len(table.headers))]
        for position, row in enumerate(grid):
            cells = [cell.ljust(width) if i < table.numeric_from else cell.rjust(width)
                     for i, (cell, width) in enumerate(zip(row, widths))]
            print("  " + "  ".join(cells).rstrip())
            if position == 0:
                print("  " + "  ".join("-" * width for width in widths))


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def comparison_charts(data: SweepData, captions: list[str], knob: str) -> list[tuple[Chart, go.Figure]]:
    """Every comparison chart this series supports, with its index entry."""
    charts: list[tuple[Chart, go.Figure]] = [
        (Chart("compare_final.html", "MSE de validación final, seed por seed",
               "Un círculo por seed y un rombo en la media. Si las seeds de una variante se dispersan más que la "
               "distancia entre dos variantes, esa distancia no es un resultado."),
         comparison_figure(data, captions, PRIMARY)),
        (Chart("compare_distribution.html", "MSE de validación final por variante",
               "Boxplot con un punto por seed: mediana, cuartiles y la dispersión real detrás de la media."),
         distribution_figure(data, captions, knob, PRIMARY)),
    ]
    # Two variants have one difference worth drawing per seed; three or more don't, and the rank chart
    # answers the same stability question
    if len(data.variants) == 2:
        charts.append((Chart("compare_paired.html", "Diferencia pareada por seed",
                             "La diferencia seed por seed, con su media e IC95%. Una barra que cruza el cero es una "
                             "seed donde se dio vuelta el ranking."),
                       paired_figure(data, captions, knob, PRIMARY)))
    else:
        charts.append((Chart("compare_ranking.html", "Estabilidad del ranking",
                             "El puesto que sacó cada variante dentro de cada seed. Una variante cuyo rango cubre todo "
                             "el campo no ganó de verdad."),
                       ranking_figure(data, captions, knob, PRIMARY)))
    charts += [
        (Chart("compare_speed.html", "Velocidad de convergencia",
               "Épocas hasta un umbral de error que todas las corridas alcanzan. Separa 'mejor' de 'más rápido'."),
         speed_figure(data, captions, knob)),
        (Chart("compare_tradeoff.html", "Costo contra calidad",
               "Segundos de entrenamiento contra MSE de validación, un punto por corrida."),
         tradeoff_figure(data, captions, knob)),
        (Chart("compare_generalization.html", "Generalización",
               "MSE de train contra MSE de validación, un punto por corrida. Distingue subajuste (los dos altos) de "
               "sobreajuste (train bajo, validación alto)."),
         generalization_figure(data, captions, knob)),
    ]
    if has_metric(data, METRICS["accuracy"]):
        accuracy = METRICS["accuracy"]
        charts.append((Chart("compare_accuracy.html", "Aciertos de validación por variante",
                             "Porcentaje de muestras de validación clasificadas bien (por argmax, o por el umbral "
                             "entre las dos ζ), una por seed."),
                       distribution_figure(data, captions, knob, accuracy)))
    return charts
