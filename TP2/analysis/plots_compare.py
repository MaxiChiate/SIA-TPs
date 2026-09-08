"""Statistical comparison of a sweep's variants: is a difference a result or noise?

Charts and summary tables; ``plots_main`` is the CLI that writes them. Works on
any series - cruza, mutación, selección, supervivencia, población, triángulos,
color - because every one of them asks the same question the consigna asks:
"decidir qué método usarían en diferentes circunstancias y por qué".

Why this and not more curves in ``plots_main``: those show the trajectory, and a
trajectory cannot say whether two variants actually differ. These answer that,
using the fact that every variant runs the same seeds - a seed fixes the initial
population and the RNG stream, so the runs are paired and the comparison never
spends its resolution on the between-seed spread.

The statistics are stdlib only, by design: an exact sign-flip permutation test
over 2^n pairings, a percentile bootstrap, and Holm's correction for testing
several variants against the leader. With ten seeds the exact test is 1024
cases, cheaper than the dependency it would otherwise need.
"""

from __future__ import annotations

import itertools
import random
import statistics
from collections import defaultdict

import plotly.graph_objects as go

from analysis.plots_data import Band, SweepData
from analysis.plots_index import Chart, Table
from analysis.plots_style import (
    ERROR_MARKS,
    TEXT_SECONDARY,
    add_error_bars,
    base_layout,
    palette_for,
    translucent,
)

# Fixed so a reported interval is the same number every time the script runs: a
# confidence interval that moves between two runs is not a number anyone can put
# on a slide. The cátedra's own guidance is to fix a seed for reproducibility.
BOOTSTRAP_SEED = 20260907
BOOTSTRAP_RESAMPLES = 20000

# Above this many pairs, enumerating every sign flip stops being free (2^n), so
# the test samples the same null distribution instead.
EXACT_PERMUTATION_LIMIT = 20

BAND_ALPHA = 0.13

class ComparisonError(Exception):
    """The sweep has nothing comparable: one variant, or no shared seed."""


# ---------------------------------------------------------------------------
# Shaping
# ---------------------------------------------------------------------------


def final_by_seed(data: SweepData, column: str) -> dict[str, dict[int, float]]:
    """``variant -> seed -> final value``, from ``summary.csv``."""
    out: dict[str, dict[int, float]] = defaultdict(dict)
    for row in data.summary:
        if row.get(column) is not None:
            out[row["variant"]][row["seed"]] = float(row[column])
    return out


def shared_seeds(values: dict[str, dict[int, float]], variants) -> list[int]:
    """The seeds every variant actually completed - the ones that can be paired."""
    sets = [set(values.get(variant, {})) for variant in variants]
    if not sets:
        return []
    common = set.intersection(*sets)
    return sorted(common)


def paired_differences(
    values: dict[str, dict[int, float]], first: str, second: str
) -> tuple[list[int], list[float]]:
    """Per-seed ``first - second``, over the seeds both variants ran.

    The pairing is what makes ten runs enough to say anything: a seed fixes the
    initial population and the whole RNG stream, so two variants start from the
    identical population and diverge only through the operator under test.
    """
    seeds = shared_seeds(values, (first, second))
    if not seeds:
        raise ComparisonError(f"no seed ran both '{first}' and '{second}'; nothing to pair")
    return seeds, [values[first][seed] - values[second][seed] for seed in seeds]


def permutation_p_value(differences: list[float]) -> tuple[float, bool]:
    """Two-sided p for "the sign of each difference was a coin flip".

    The null of a paired randomisation test: if the two variants were
    interchangeable, relabelling them within a seed would be equally likely, so
    each difference could have carried either sign. p is the share of the 2^n
    sign assignments whose mean is at least as extreme as the observed one. No
    normality assumption, which ten runs could not check anyway.

    Returns ``(p, exact)``; ``exact`` is False when n forced sampling, and the
    caption then says so rather than implying a precision p does not have.
    """
    n = len(differences)
    if n == 0:
        return 1.0, True
    observed = abs(statistics.fmean(differences))

    if n <= EXACT_PERMUTATION_LIMIT:
        extreme = sum(
            abs(statistics.fmean([s * d for s, d in zip(signs, differences)])) >= observed
            for signs in itertools.product((1, -1), repeat=n)
        )
        return extreme / 2**n, True

    rng = random.Random(BOOTSTRAP_SEED)
    extreme = sum(
        abs(statistics.fmean([d if rng.random() < 0.5 else -d for d in differences]))
        >= observed
        for _ in range(BOOTSTRAP_RESAMPLES)
    )
    return extreme / BOOTSTRAP_RESAMPLES, False


def holm_adjust(p_values: list[float]) -> list[float]:
    """Holm-Bonferroni, keeping the input order.

    Comparing six crossover methods against the leader is six tests, and at
    p<0.05 each one, a false winner among them is likelier than not. Holm is the
    cheap correction that stays valid without assuming the tests are independent
    (they are not - they share the leader's runs).
    """
    order = sorted(range(len(p_values)), key=lambda i: p_values[i])
    total = len(p_values)
    adjusted = [0.0] * total
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, (total - rank) * p_values[index])
        adjusted[index] = min(1.0, running)
    return adjusted


def bootstrap_interval(values: list[float], confidence: float = 0.95) -> tuple[float, float]:
    """Percentile bootstrap interval for the mean of ``values``.

    Non-parametric on purpose: ten paired differences are not enough to check
    normality, and the interval is only ever read as "does it clear zero".
    """
    if len(values) < 2:
        return (values[0], values[0]) if values else (0.0, 0.0)
    rng = random.Random(BOOTSTRAP_SEED)
    means = sorted(
        statistics.fmean(rng.choices(values, k=len(values)))
        for _ in range(BOOTSTRAP_RESAMPLES)
    )
    tail = (1.0 - confidence) / 2.0
    low = means[int(tail * len(means))]
    high = means[min(int((1.0 - tail) * len(means)), len(means) - 1)]
    return low, high


def ranks_by_seed(
    values: dict[str, dict[int, float]], variants
) -> dict[str, list[float]]:
    """Per variant, its rank within each shared seed (1 = best), ties averaged.

    The scale-free companion to the mean: ranking inside a seed cancels out how
    hard that particular starting population was, so a variant that is second by
    a hair on every seed does not read like one that wins half and collapses on
    the rest.
    """
    seeds = shared_seeds(values, variants)
    out: dict[str, list[float]] = {variant: [] for variant in variants}
    for seed in seeds:
        ordered = sorted(variants, key=lambda v: values[v][seed], reverse=True)
        position = 0
        while position < len(ordered):
            tied = [
                v for v in ordered
                if values[v][seed] == values[ordered[position]][seed]
            ]
            average = statistics.fmean(range(position + 1, position + 1 + len(tied)))
            for variant in tied:
                out[variant].append(average)
            position += len(tied)
    return out


def common_threshold(data: SweepData) -> float:
    """The best fitness that *every* run of the sweep reached.

    Speed is only comparable against a bar all the runs clear: taking, say, 90%
    of the winner's fitness would leave the weaker variants never reaching it and
    a chart of missing values. This is the highest bar that is defined for all.
    """
    finals = [
        row["best_fitness"] for row in data.summary if row.get("best_fitness") is not None
    ]
    if not finals:
        raise ComparisonError("no run reported a best_fitness")
    return min(finals)


def generations_to_threshold(
    data: SweepData, threshold: float
) -> dict[str, dict[int, int]]:
    """``variant -> seed -> first generation whose best fitness reaches ``threshold``."""
    out: dict[str, dict[int, int]] = defaultdict(dict)
    for row in data.history:
        best = row.get("best_fitness")
        if best is None or best < threshold:
            continue
        seen = out[row["variant"]]
        generation = row["generation"]
        if seen.get(row["seed"], generation + 1) > generation:
            seen[row["seed"]] = generation
    return out


def cost_curves(data: SweepData) -> dict[str, tuple[Band, float]]:
    """Per variant: the mean gap to the best already seen, and how often it opens.

    The gap at generation g is ``max(best_fitness up to g) - best_fitness[g]``:
    zero while the run keeps its best individual, positive exactly on the
    generations where the new population is worse than something already found
    and then thrown away. Under (mu+lambda) with elite pool selection it is zero
    by construction, which is why this chart *proves* the property instead of
    just suggesting it.

    Returns ``variant -> (band, regression_rate)``, where the rate is the share
    of generations with a positive gap, averaged over seeds.
    """
    per_seed: dict[str, dict[int, dict[int, float]]] = defaultdict(lambda: defaultdict(dict))
    for row in data.history:
        if row.get("best_fitness") is not None:
            per_seed[row["variant"]][row["seed"]][row["generation"]] = row["best_fitness"]

    out = {}
    for variant in data.variants:
        seeds = per_seed.get(variant)
        if not seeds:
            continue
        gaps: dict[int, dict[int, float]] = {}
        rates = []
        for seed, points in seeds.items():
            best_so_far = float("-inf")
            walked: dict[int, float] = {}
            for generation in sorted(points):
                best_so_far = max(best_so_far, points[generation])
                walked[generation] = best_so_far - points[generation]
            gaps[seed] = walked
            # Generation 0 has nothing to fall behind, so it is not a chance to
            # regress and would only dilute the rate.
            later = [gap for g, gap in walked.items() if g > 0]
            rates.append(sum(gap > 0 for gap in later) / len(later) if later else 0.0)

        generations = sorted({g for walked in gaps.values() for g in walked})
        means, lows, highs = [], [], []
        for generation in generations:
            seen = [w[generation] for w in gaps.values() if generation in w]
            means.append(statistics.fmean(seen))
            lows.append(min(seen))
            highs.append(max(seen))
        band = Band(x=[float(g) for g in generations], mean=means, low=lows, high=highs)
        out[variant] = (band, statistics.fmean(rates))
    return out


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------


def _ordered_by_mean(values: dict[str, dict[int, float]], variants) -> list[str]:
    """Variants best-first, so every chart here reads top-to-bottom as a ranking."""
    return sorted(
        (v for v in variants if values.get(v)),
        key=lambda v: statistics.fmean(values[v].values()),
        reverse=True,
    )


def _boxplot(
    values: dict[str, dict[int, float]],
    variants,
    colors: dict[str, str],
    title: str,
    subtitles: list[str],
    y_title: str,
) -> go.Figure:
    """Boxplot with every seed drawn beside its box.

    The box carries the shape the mean hides - median, quartiles - and the points
    keep ten runs from being read as a smooth population. With n=10 the box is a
    summary of visible data, not a replacement for it, so both are on the chart.
    """
    figure = go.Figure()
    for variant in variants:
        seen = list(values.get(variant, {}).values())
        if not seen:
            continue
        figure.add_trace(
            go.Box(
                y=seen, name=variant,
                marker={"color": colors[variant], "size": 7},
                line={"color": colors[variant], "width": 2},
                fillcolor=translucent(colors[variant], BAND_ALPHA),
                boxpoints="all", jitter=0.5, pointpos=1.7, boxmean=True,
                hovertemplate="%{y:.4f}<extra></extra>", showlegend=False,
            )
        )
    layout = base_layout(title, subtitles, "", y_title)
    layout["showlegend"] = False
    layout["xaxis"]["showgrid"] = False
    layout["margin"] = {**layout["margin"], "r": 90, "b": 70}
    figure.update_layout(**layout)
    return figure


def distribution_figure(data: SweepData, captions: list[str], knob: str) -> go.Figure:
    """Final fitness per variant: the headline comparison, with its spread."""
    colors = palette_for(data.variants)
    values = final_by_seed(data, "best_fitness")
    return _boxplot(
        values, _ordered_by_mean(values, data.variants), colors,
        f"Fitness final por {knob}",
        [
            "Caja = cuartiles y mediana · línea punteada = media · un punto por seed "
            f"({len(data.seeds)} corridas por variante) · ordenado de mejor a peor",
            *captions,
        ],
        "Mejor fitness alcanzado",
    )


def paired_figure(data: SweepData, captions: list[str], knob: str) -> go.Figure:
    """Per-seed difference between the two variants, plus its mean and CI.

    One bar per seed rather than two boxes side by side: the seeds are paired, so
    the difference is a measurement in its own right. A bar crossing zero is a
    seed where the ranking flipped, which is the honest way to present an effect
    this size.
    """
    values = final_by_seed(data, "best_fitness")
    first, second = _ordered_by_mean(values, data.variants)
    colors = palette_for(data.variants)
    seeds, differences = paired_differences(values, first, second)
    mean = statistics.fmean(differences)
    low, high = bootstrap_interval(differences)
    p_value, exact = permutation_p_value(differences)
    wins = sum(d > 0 for d in differences)

    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=[f"seed {seed}" for seed in seeds], y=differences,
            marker={
                "color": [
                    translucent(colors[first] if d > 0 else colors[second], 0.55)
                    for d in differences
                ],
                "line": {
                    "color": [colors[first] if d > 0 else colors[second] for d in differences],
                    "width": 1.5,
                },
            },
            hovertemplate="%{y:+.4f}<extra></extra>", showlegend=False,
        )
    )
    # The mean and its interval ride in their own column past the seeds, so the
    # summary is read on the same scale as the values it summarises.
    figure.add_trace(
        go.Scatter(
            x=["media"], y=[mean], mode="markers",
            marker={"color": TEXT_SECONDARY, "size": 13, "symbol": "diamond"},
            error_y={
                "type": "data", "symmetric": False,
                "array": [high - mean], "arrayminus": [mean - low],
                "color": TEXT_SECONDARY, "thickness": 2, "width": 8,
            },
            hovertemplate=f"media {mean:+.4f} · IC95% [{low:+.4f}, {high:+.4f}]<extra></extra>",
            showlegend=False,
        )
    )

    layout = base_layout(
        f"Diferencia pareada por seed: {first} − {second}",
        [
            "Cada seed fija la población inicial, así que las dos variantes arrancan "
            f"del mismo punto · barras arriba de 0 = gana {first}",
            f"{first} gana {wins} de {len(differences)} seeds · media {mean:+.4f} · "
            f"IC95% bootstrap [{low:+.4f}, {high:+.4f}] · test de permutación pareado "
            f"p{'' if exact else ' aprox.'} = {p_value:.4f}",
            *captions,
        ],
        "",
        f"Δ fitness final ({first} − {second})",
    )
    layout["showlegend"] = False
    layout["xaxis"]["showgrid"] = False
    layout["shapes"] = [{
        "type": "line", "xref": "paper", "x0": 0, "x1": 1,
        "yref": "y", "y0": 0, "y1": 0,
        "line": {"color": TEXT_SECONDARY, "width": 1},
    }]
    layout["margin"] = {**layout["margin"], "r": 90, "b": 80}
    figure.update_layout(**layout)
    return figure


def ranking_figure(data: SweepData, captions: list[str], knob: str) -> go.Figure:
    """Mean rank per variant with the full range of ranks it took across seeds.

    What replaces the paired-difference chart once there are more than two
    variants: with k variants there is no single difference to draw, but the rank
    a variant took *within each seed* is still paired, and its range answers the
    question the mean cannot - "is this ordering stable, or did it depend on the
    seed". A variant whose range spans the whole field did not really win.
    """
    colors = palette_for(data.variants)
    values = final_by_seed(data, "best_fitness")
    ordered = _ordered_by_mean(values, data.variants)
    ranks = ranks_by_seed(values, ordered)

    figure = go.Figure()
    labels = []
    for variant in ordered:
        seen = ranks[variant]
        if not seen:
            continue
        mean = statistics.fmean(seen)
        figure.add_trace(
            go.Scatter(
                x=[min(seen), max(seen)], y=[variant, variant], mode="lines",
                line={"color": translucent(colors[variant], 0.45), "width": 6},
                hoverinfo="skip", showlegend=False,
            )
        )
        figure.add_trace(
            go.Scatter(
                x=seen, y=[variant] * len(seen), mode="markers",
                marker={
                    "color": "#ffffff", "size": 9,
                    "line": {"color": colors[variant], "width": 2},
                },
                hovertemplate="puesto %{x}<extra></extra>", showlegend=False,
            )
        )
        figure.add_trace(
            go.Scatter(
                x=[mean], y=[variant], mode="markers",
                marker={"color": colors[variant], "size": 13, "symbol": "diamond"},
                hovertemplate="puesto medio %{x:.2f}<extra></extra>", showlegend=False,
            )
        )
        labels.append({
            "x": 1, "xref": "paper", "xanchor": "left",
            "y": variant, "yref": "y", "yanchor": "middle",
            "text": f"  {mean:.2f}", "showarrow": False,
            "font": {"color": TEXT_SECONDARY, "size": 11},
        })

    layout = base_layout(
        f"Puesto por seed: qué tan estable es el ranking de {knob}",
        [
            "Rombo = puesto medio · círculos = el puesto que tomó en cada seed · "
            "barra = rango completo · 1 = mejor de la generación de esa seed",
            *captions,
        ],
        "Puesto dentro de la seed",
        "",
    )
    layout["hovermode"] = "closest"
    layout["showlegend"] = False
    layout["yaxis"]["showgrid"] = False
    layout["xaxis"]["dtick"] = 1
    layout["annotations"] = labels
    layout["margin"] = {**layout["margin"], "l": 190, "r": 90, "b": 60}
    figure.update_layout(**layout)
    return figure


def speed_figure(data: SweepData, captions: list[str], knob: str) -> go.Figure:
    """Generations each variant needed to reach a bar every run cleared.

    The chart that separates "mejor" from "más rápido", which is exactly the
    circumstance the consigna asks about: a method that ends lower but gets there
    in a third of the generations is the right choice under a generation budget,
    and no fitness curve read at generation 150 will tell you that.
    """
    colors = palette_for(data.variants)
    threshold = common_threshold(data)
    reached = generations_to_threshold(data, threshold)
    values = {v: {s: float(g) for s, g in seeds.items()} for v, seeds in reached.items()}
    ordered = sorted(
        (v for v in data.variants if values.get(v)),
        key=lambda v: statistics.fmean(values[v].values()),
    )
    return _boxplot(
        values, ordered, colors,
        f"Velocidad de convergencia por {knob}",
        [
            f"Generaciones hasta alcanzar fitness {threshold:.4f} — el mejor umbral que "
            "alcanzan todas las corridas de todas las variantes · menos es mejor",
            *captions,
        ],
        "Generaciones hasta el umbral",
    )


def tradeoff_figure(data: SweepData, captions: list[str], knob: str) -> go.Figure:
    """Final diversity against final fitness, one dot per run.

    Turns "peor" into the exploration/explotación trade-off the operators encode:
    a variant that ends lower with a still-spread population had not finished
    converging, which is a different failure from one that converged onto a bad
    optimum, and only this chart tells them apart.
    """
    colors = palette_for(data.variants)
    fitness = final_by_seed(data, "best_fitness")
    diversity = final_by_seed(data, "final_diversity")

    figure = go.Figure()
    for variant in data.variants:
        seeds = shared_seeds({"f": fitness.get(variant, {}), "d": diversity.get(variant, {})}, ("f", "d"))
        if not seeds:
            continue
        figure.add_trace(
            go.Scatter(
                x=[diversity[variant][seed] for seed in seeds],
                y=[fitness[variant][seed] for seed in seeds],
                name=variant, mode="markers",
                marker={
                    "color": translucent(colors[variant], 0.55), "size": 11,
                    "line": {"color": colors[variant], "width": 2},
                },
                text=[f"seed {seed}" for seed in seeds],
                hovertemplate="%{text}<br>diversidad %{x:.5f}<br>fitness %{y:.4f}<extra></extra>",
            )
        )

    layout = base_layout(
        f"Explotación vs exploración al final de la corrida, por {knob}",
        [
            "Un punto por corrida · arriba = mejor aproximación, derecha = población "
            "menos convergida",
            *captions,
        ],
        "Diversidad genotípica final",
        "Mejor fitness alcanzado",
    )
    layout["hovermode"] = "closest"
    figure.update_layout(**layout)
    return figure


def cost_figure(data: SweepData, captions: list[str]) -> go.Figure:
    """How much fitness each survival strategy throws away replacing its population.

    Survival-only because it is the structural difference between (mu+lambda) and
    (mu,lambda), and a property of the operator rather than a result of this
    problem: additive picks survivors out of parents and children together, so
    the best individual is always eligible and the curve is pinned at zero;
    exclusive keeps only children, so every generation risks discarding it.
    """
    colors = palette_for(data.variants)
    curves = cost_curves(data)
    if not curves:
        raise ComparisonError("no history rows with best_fitness")

    figure = go.Figure()
    for variant, (band, _) in curves.items():
        figure.add_trace(
            go.Scatter(
                x=band.x, y=band.mean, name=variant, mode="lines",
                line={"color": colors[variant], "width": 2},
                hovertemplate="%{y:.4f}<extra></extra>",
            )
        )
    for position, (variant, (band, _)) in enumerate(curves.items()):
        marks = band.error_marks(ERROR_MARKS, phase=position / max(len(curves), 1))
        add_error_bars(figure, marks, colors[variant])

    rates = " · ".join(
        f"{variant}: {rate:.0%} de las generaciones" for variant, (_, rate) in curves.items()
    )
    layout = base_layout(
        "Costo del reemplazo: cuánto queda por debajo del mejor ya encontrado",
        [
            "0 = la generación conserva al mejor individuo hallado hasta ahí · "
            "media de las seeds, las barras de error marcan el rango completo",
            f"Generaciones que pierden al mejor — {rates}",
            *captions,
        ],
        "Generación",
        "Mejor histórico − mejor de la generación",
    )
    figure.update_layout(**layout)
    return figure


# ---------------------------------------------------------------------------
# Summary tables
# ---------------------------------------------------------------------------


def summary_tables(data: SweepData, is_survival: bool) -> list[Table]:
    """The numbers behind the charts, as rows both the terminal and the index render.

    Built once and rendered twice on purpose: a slide needs the charts, but the
    deck's notes and the README need the figures themselves, and retyping them
    off a hover tooltip is how a presentation ends up quoting a number that is
    not in the data.
    """
    fitness = final_by_seed(data, "best_fitness")
    diversity = final_by_seed(data, "final_diversity")
    ordered = _ordered_by_mean(fitness, data.variants)
    ranks = ranks_by_seed(fitness, ordered)
    threshold = common_threshold(data)
    speed = generations_to_threshold(data, threshold)
    tables: list[Table] = []

    rows = []
    for variant in ordered:
        seen = list(fitness[variant].values())
        deviation = statistics.stdev(seen) if len(seen) > 1 else 0.0
        rank = statistics.fmean(ranks[variant]) if ranks.get(variant) else float("nan")
        rows.append([
            variant, str(len(seen)), f"{statistics.fmean(seen):.4f}", f"{deviation:.4f}",
            f"{statistics.median(seen):.4f}", f"{min(seen):.4f}", f"{max(seen):.4f}",
            f"{rank:.2f}",
        ])
    tables.append(Table(
        title="Fitness final",
        headers=["variante", "n", "media", "desvío", "mediana", "mín", "máx", "puesto"],
        rows=rows,
        note="Ordenado de mejor a peor. 'Puesto' es el promedio del lugar que sacó la "
             "variante dentro de cada seed: es la misma comparación pero sin escala, "
             "así que no la domina una seed que salió fácil para todos.",
        highlight_first_row=True,
    ))

    rows = []
    for variant in ordered:
        reached = list(speed.get(variant, {}).values())
        spread = list(diversity.get(variant, {}).values())
        if not reached:
            continue
        rows.append([
            variant, f"{statistics.median(reached):.1f}", str(min(reached)),
            str(max(reached)), f"{statistics.fmean(spread) if spread else 0.0:.5f}",
        ])
    tables.append(Table(
        title="Velocidad y convergencia",
        headers=["variante", "generaciones (mediana)", "mín", "máx", "diversidad final"],
        rows=rows,
        note=f"Generaciones hasta fitness {threshold:.4f}, el mejor umbral que alcanzan "
             "todas las corridas de todas las variantes. Menos es mejor.",
    ))

    if is_survival:
        rows = [
            [variant, f"{rate:.0%}",
             f"{statistics.fmean(band.mean) if band.mean else 0.0:.4f}",
             f"{max(band.high) if band.high else 0.0:.4f}"]
            for variant, (band, rate) in cost_curves(data).items()
        ]
        tables.append(Table(
            title="Costo del reemplazo generacional",
            headers=["variante", "generaciones que pierden al mejor", "caída media", "caída máx"],
            rows=rows,
            note="Bajo (μ+λ) el mejor individuo siempre compite, así que la fila es 0 por "
                 "construcción. Bajo (μ,λ) cada generación es una oportunidad de tirarlo.",
        ))

    if len(ordered) < 2:
        return tables

    # Everything is tested against the leader rather than every pair against
    # every other: the question a presentation answers is "is the winner really
    # the winner", and k(k-1)/2 tests would spend the correction's budget on
    # comparisons nobody reads.
    leader, *rest = ordered
    computed = []
    for variant in rest:
        _, differences = paired_differences(fitness, leader, variant)
        p_value, exact = permutation_p_value(differences)
        computed.append((variant, differences, p_value, exact))
    adjusted = holm_adjust([row[2] for row in computed])

    rows = []
    for (variant, differences, p_value, exact), corrected in zip(computed, adjusted):
        low, high = bootstrap_interval(differences)
        wins = sum(d > 0 for d in differences)
        rows.append([
            variant, f"{wins}/{len(differences)}", f"{statistics.fmean(differences):+.4f}",
            f"[{low:+.4f}, {high:+.4f}]", f"{'' if exact else '~'}{p_value:.4f}",
            f"{corrected:.4f}",
        ])
    note = ("Cada seed fija la población inicial, así que las dos corridas de un par "
            "arrancan del mismo punto y se separan solo por el operador que se prueba. "
            "El test de permutación es exacto (2^n asignaciones de signo) y el IC es "
            "bootstrap percentil.")
    if len(rows) > 1:
        note += (" 'p (Holm)' corrige por comparar varias variantes contra el mismo "
                 "líder; es el valor a citar.")
    tables.append(Table(
        title=f"Comparación pareada contra '{leader}'",
        headers=["variante", f"gana {leader}", "Δ media", "IC95%", "p", "p (Holm)"],
        rows=rows,
        note=note,
    ))
    return tables


def print_tables(tables: list[Table]) -> None:
    """Render the summary tables to stdout, columns padded to their widest cell."""
    for table in tables:
        print(f"\n{table.title}")
        grid = [list(table.headers), *(list(row) for row in table.rows)]
        widths = [max(len(row[i]) for row in grid) for i in range(len(table.headers))]
        for position, row in enumerate(grid):
            cells = [
                cell.ljust(width) if i < table.numeric_from else cell.rjust(width)
                for i, (cell, width) in enumerate(zip(row, widths))
            ]
            print("  " + "  ".join(cells).rstrip())
            if position == 0:
                print("  " + "  ".join("-" * width for width in widths))
        if table.note:
            print(f"  ({table.note})")


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def comparison_charts(
    data: SweepData, captions: list[str], knob: str, is_survival: bool
) -> list[tuple[Chart, go.Figure]]:
    """Every comparison chart this sweep supports, with its index entry."""
    charts: list[tuple[Chart, go.Figure]] = [
        (
            Chart("compare_distribution.html", "Fitness final por variante",
                  "Boxplot con un punto por seed: mediana, cuartiles y la dispersión "
                  "real detrás de la media."),
            distribution_figure(data, captions, knob),
        ),
    ]

    # Two variants have one difference worth drawing per seed; three or more do
    # not, and the rank chart answers the same stability question.
    if len(data.variants) == 2:
        charts.append((
            Chart("compare_paired.html", "Diferencia pareada por seed",
                  "La diferencia seed por seed, con su media e IC95%. Una barra que "
                  "cruza el cero es una seed donde se dio vuelta el ranking."),
            paired_figure(data, captions, knob),
        ))
    else:
        charts.append((
            Chart("compare_ranking.html", "Estabilidad del ranking",
                  "El puesto que sacó cada variante dentro de cada seed. Una variante "
                  "cuyo rango cubre todo el campo no ganó de verdad."),
            ranking_figure(data, captions, knob),
        ))

    charts.append((
        Chart("compare_speed.html", "Velocidad de convergencia",
              "Generaciones hasta un umbral que todas las corridas alcanzan. Separa "
              "'mejor' de 'más rápido', que es la circunstancia que pregunta la consigna."),
        speed_figure(data, captions, knob),
    ))
    charts.append((
        Chart("compare_tradeoff.html", "Explotación vs exploración",
              "Diversidad final contra fitness final, un punto por corrida. Distingue "
              "terminar abajo sin converger de terminar abajo ya convergido."),
        tradeoff_figure(data, captions, knob),
    ))
    if is_survival:
        charts.append((
            Chart("survival_cost.html", "Costo del reemplazo generacional",
                  "Cuánto queda la población por debajo del mejor que ya había "
                  "encontrado. Demuestra el elitismo de (μ+λ) en vez de sugerirlo.",
                  group="estructura"),
            cost_figure(data, captions),
        ))
    return charts
