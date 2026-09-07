"""Load a sweep's CSVs and aggregate them into the series each plot draws.

Reading and shaping only - nothing here knows about plotly. Uses the stdlib
``csv`` module rather than pandas: the files are a few thousand rows and adding a
dataframe dependency for ``mean()`` is not worth it.

Seeds are averaged per generation, so one variant is one line. The spread across
seeds is kept separately for the comparison chart, where it is the interesting
part (a difference smaller than the seed spread is not a difference).
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

# Columns whose values are numeric; everything else stays a string.
_INT_COLUMNS = frozenset({"seed", "generation", "cumulative_evaluations", "evaluations",
                          "best_generation", "generations"})
_FLOAT_COLUMNS = frozenset({"best_fitness", "mean_fitness", "std_fitness", "worst_fitness",
                            "genotypic_diversity", "cumulative_seconds", "elapsed_seconds",
                            "final_mean_fitness", "final_diversity"})


class SweepDataError(Exception):
    """The sweep directory is missing, empty, or holds no successful run."""


@dataclass(frozen=True, slots=True)
class SweepData:
    """One sweep's two tables, plus the variant order every plot shares."""

    directory: Path
    summary: list[dict]
    history: list[dict]
    variants: tuple[str, ...]

    @property
    def seeds(self) -> tuple[int, ...]:
        return tuple(sorted({row["seed"] for row in self.summary}))


def _coerce(row: dict[str, str]) -> dict:
    """Turn the numeric columns into numbers, leaving blanks as ``None``."""
    out: dict = {}
    for key, value in row.items():
        if value == "" or value is None:
            out[key] = None
        elif key in _INT_COLUMNS:
            out[key] = int(value)
        elif key in _FLOAT_COLUMNS:
            out[key] = float(value)
        else:
            out[key] = value
    return out


def load_rows(path: Path) -> list[dict]:
    """Read a CSV into a list of dicts with numeric columns already coerced."""
    if not path.is_file():
        raise SweepDataError(f"missing {path.name} in {path.parent}")
    with path.open(newline="", encoding="utf-8") as handle:
        return [_coerce(row) for row in csv.DictReader(handle)]


def latest_sweep(root: Path) -> Path:
    """The most recent sweep directory under ``root``.

    Sweep ids are UTC timestamps, so lexicographic order is chronological order.
    """
    if not root.is_dir():
        raise SweepDataError(f"no results directory at {root} - run analysis/main.py first")
    candidates = sorted(
        (child for child in root.iterdir() if (child / "summary.csv").is_file()),
        reverse=True,
    )
    if not candidates:
        raise SweepDataError(f"no sweep with a summary.csv under {root}")
    return candidates[0]


def load_sweep(directory: Path) -> SweepData:
    """Load both CSVs of one sweep, dropping runs that failed."""
    summary = [row for row in load_rows(directory / "summary.csv") if row["status"] == "ok"]
    if not summary:
        raise SweepDataError(f"{directory}: no successful run in summary.csv")
    history = load_rows(directory / "history.csv")

    # Order of first appearance in summary.csv, which is the order the sweep
    # config declared. Colours are assigned from this, so a variant keeps its
    # colour across every chart of the sweep.
    variants: list[str] = []
    for row in summary:
        if row["variant"] not in variants:
            variants.append(row["variant"])
    return SweepData(
        directory=directory,
        summary=summary,
        history=history,
        variants=tuple(variants),
    )


# What a curve can be plotted against. Generation is the default and is right
# whenever every variant pays the same per generation; the other two exist for
# the sweeps where it does not (population size and shape count change the cost
# of a generation, so equal generations is not equal work).
X_COLUMNS: dict[str, str] = {
    "generation": "Generación",
    "cumulative_evaluations": "Evaluaciones acumuladas",
    "cumulative_seconds": "Segundos acumulados",
}


@dataclass(frozen=True, slots=True)
class Band:
    """One variant's curve: the mean over seeds, plus the spread around it.

    ``low``/``high`` are the full min-max range across seeds, not a standard
    deviation. With ten runs the question a reader asks is "could these two
    variants have swapped places on a different seed", and the full range
    answers exactly that; a 1-sigma ribbon hides the tails that decide it.
    """

    x: list[float]
    mean: list[float]
    low: list[float]
    high: list[float]

    @property
    def spread(self) -> float:
        """Widest gap between the extreme seeds, over the whole curve."""
        return max((h - l for l, h in zip(self.low, self.high)), default=0.0)

    def error_marks(
        self, count: int, phase: float = 0.0
    ) -> tuple[list[float], list[float], list[float], list[float]]:
        """``count`` evenly spaced points of the curve as ``(x, y, up, down)``.

        An error bar per generation would be 150 bars per variant - solid ink
        that hides the very line it annotates - so the spread is marked at a
        handful of points and read as a sample of it.

        ``phase`` (in [0, 1)) shifts *which* points a variant samples, so several
        curves put their bars at different x instead of stacking them into an
        unreadable column. Shifting the sample beats nudging the bars sideways:
        a bar drawn off its own x is a bar drawn at a value the run never had.

        Up/down are distances from the mean, which is the form plotly's
        asymmetric ``error_y`` takes, and they preserve the full min-max range -
        the same quantity the curve's spread has always carried.
        """
        total = len(self.x)
        if total == 0 or count <= 0:
            return [], [], [], []
        step = total / min(count, total)
        indices = sorted({
            min(total - 1, int(step * (position + phase)))
            for position in range(min(count, total))
        } | {total - 1})
        return (
            [self.x[i] for i in indices],
            [self.mean[i] for i in indices],
            [self.high[i] - self.mean[i] for i in indices],
            [self.mean[i] - self.low[i] for i in indices],
        )


ValueSpec = str | Callable[[dict], float | None]


def _value_of(row: dict, value: ValueSpec) -> float | None:
    return row.get(value) if isinstance(value, str) else value(row)


def _series_by_seed(
    data: SweepData, value: ValueSpec, x_column: str
) -> dict[str, dict[int, dict[int, tuple[float, float]]]]:
    """``variant -> seed -> generation -> (x, y)``, dropping unusable rows."""
    out: dict[str, dict[int, dict[int, tuple[float, float]]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for row in data.history:
        y = _value_of(row, value)
        x = row.get(x_column)
        if y is None or x is None:
            continue
        out[row["variant"]][row["seed"]][row["generation"]] = (float(x), float(y))
    return out


def curve_bands(
    data: SweepData,
    value: ValueSpec,
    x_column: str = "generation",
    running_max: bool = False,
) -> dict[str, Band]:
    """Per variant, the seed-averaged curve of ``value`` with its seed spread.

    ``value`` is a history column, or a callable on a row for a derived
    quantity (the selective-pressure chart passes ``best - mean``).

    ``running_max`` accumulates the maximum **per seed, before averaging**.
    That order matters: the cumulative maximum of an average is not the average
    of the cumulative maxima, and only the latter is "what a run had achieved
    by generation g", averaged. It is what makes the curve comparable across
    survival strategies - under ``exclusive`` (mu,lambda) the generation's best
    can fall, so the raw column and this one are genuinely different questions.

    Generations reached by only some seeds still aggregate over whichever seeds
    got there, so a curve never breaks; the spread simply narrows.
    """
    if x_column not in X_COLUMNS:
        raise SweepDataError(
            f"unknown x column {x_column!r}; expected one of {sorted(X_COLUMNS)}"
        )
    by_seed = _series_by_seed(data, value, x_column)

    bands: dict[str, Band] = {}
    for variant in data.variants:
        seeds = by_seed.get(variant)
        if not seeds:
            continue

        # Per seed: walk its own generations in order, optionally accumulating.
        prepared: dict[int, dict[int, tuple[float, float]]] = {}
        for seed, points in seeds.items():
            best_so_far = float("-inf")
            walked: dict[int, tuple[float, float]] = {}
            for generation in sorted(points):
                x, y = points[generation]
                if running_max:
                    best_so_far = max(best_so_far, y)
                    y = best_so_far
                walked[generation] = (x, y)
            prepared[seed] = walked

        generations = sorted({g for walked in prepared.values() for g in walked})
        xs, means, lows, highs = [], [], [], []
        for generation in generations:
            found = [
                walked[generation] for walked in prepared.values() if generation in walked
            ]
            ys = [y for _, y in found]
            xs.append(sum(x for x, _ in found) / len(found))
            means.append(sum(ys) / len(ys))
            lows.append(min(ys))
            highs.append(max(ys))
        bands[variant] = Band(x=xs, mean=means, low=lows, high=highs)
    return bands


def best_minus_mean(row: dict) -> float | None:
    """Selective pressure: how far the generation's best sits above its average.

    A population that selection has collapsed onto one individual reads ~0
    here; one that selection is barely ordering keeps a wide gap. It is the
    quantity the parent-selection sweep is actually about, and it comes from
    two columns the CSV already carries.
    """
    best, mean = row.get("best_fitness"), row.get("mean_fitness")
    if best is None or mean is None:
        return None
    return best - mean


def mean_curve(
    data: SweepData, column: str
) -> dict[str, tuple[list[float], list[float]]]:
    """Backwards-compatible view of ``curve_bands``: just the mean line."""
    return {
        variant: (band.x, band.mean)
        for variant, band in curve_bands(data, column).items()
    }


def _flatten(config: dict, prefix: str, out: dict[str, Any]) -> None:
    """Config tree -> ``{"engine.n": 100, ...}``; lists become tuples so they compare."""
    for key, value in config.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            _flatten(value, path, out)
        else:
            out[path] = tuple(value) if isinstance(value, list) else value


def _resolved(directory: Path) -> dict:
    """``resolved.json`` as a dict, or ``{}`` when it is missing or unreadable.

    A sweep predating ``resolved.json`` simply loses the caption and the knob
    name; nothing that reads this treats an empty payload as an error.
    """
    path = directory / "resolved.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def fixed_config(directory: Path) -> dict[str, Any]:
    """The settings every variant of the sweep shared, from ``resolved.json``.

    Read from what actually ran rather than from the sweep config, so a chart's
    caption cannot drift from the run it describes. Whatever the sweep varied
    differs between variants and is dropped here - what is left is, by
    construction, the fixed part of the experiment.

    Returns ``{}`` for a sweep predating ``resolved.json``; the caption is then
    simply omitted.
    """
    payload = _resolved(directory)
    flattened = []
    for config in payload.get("variants", {}).values():
        out: dict[str, Any] = {}
        _flatten(config, "", out)
        flattened.append(out)
    if not flattened:
        return {}

    first, *rest = flattened
    return {
        key: value
        for key, value in first.items()
        if all(other.get(key, _MISSING) == value for other in rest)
    }


_MISSING = object()


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

# What the sweep varied -> how to name it in a title, in precedence order. A
# recipe can move a second knob to keep the comparison fair (serie_mutacion sets
# engine.pm=1.0 so 'gene' mutates one allele like the others), and the title has
# to name the operator under test, not the compensation. Operators first for
# exactly that reason. Falls back to the raw dotted path, so an unmapped knob
# gives an ugly title rather than a wrong one.
KNOB_NAMES = {
    "operators.parent_selection.name": "método de selección",
    "operators.crossover.name": "método de cruza",
    "operators.mutation.name": "método de mutación",
    "operators.survival.name": "estrategia de supervivencia",
    "engine.n": "tamaño de población",
    "engine.k": "cantidad de hijos",
    "engine.pc": "probabilidad de cruza",
    "engine.pm": "probabilidad de mutación",
    "problem.params.triangle_count": "cantidad de triángulos",
    "problem.params.color_space": "espacio de color",
}


def _format_value(key: str, value) -> str:
    if key == "problem.params.work_resolution" and isinstance(value, tuple):
        return "×".join(str(part) for part in value)
    if key == "problem.params.image_path":
        return Path(str(value)).name
    return str(value)


def fixed_captions(fixed: dict) -> list[str]:
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


def varied_paths(directory: Path) -> list[str]:
    """The config paths that differ between this sweep's variants.

    The mirror image of ``fixed_config``: whatever is *not* shared by every
    resolved variant is, by construction, what the sweep varied. Read from what
    actually ran, so a title cannot drift from the experiment it describes.
    """
    payload = _resolved(directory)
    flattened = []
    for config in payload.get("variants", {}).values():
        out: dict[str, Any] = {}
        _flatten(config, "", out)
        flattened.append(out)
    if len(flattened) < 2:
        return []

    first, *rest = flattened
    # 'seed' is listed in a resolved config but is a per-run value, not
    # something the sweep varied between variants.
    return [
        key for key, value in first.items()
        if key != "seed" and any(other.get(key) != value for other in rest)
    ]


def varied_knob(directory: Path) -> str:
    """Name of what this sweep changed, for the chart titles."""
    varied = varied_paths(directory)
    for key, name in KNOB_NAMES.items():
        if key in varied:
            return name
    return varied[0] if varied else "variante"


def final_values(data: SweepData, column: str) -> dict[str, list[float]]:
    """Per variant, one value per seed - the raw points behind the comparison."""
    values: dict[str, list[float]] = {variant: [] for variant in data.variants}
    for row in data.summary:
        if row.get(column) is not None:
            values[row["variant"]].append(row[column])
    return {variant: sorted(seen) for variant, seen in values.items() if seen}
