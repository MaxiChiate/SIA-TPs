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
from typing import Any

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


def mean_curve(
    data: SweepData, column: str
) -> dict[str, tuple[list[int], list[float]]]:
    """Per variant, ``column`` averaged over seeds at each generation.

    Generations present in only some seeds (a run that stopped early) still
    average over whatever seeds reached them, so a curve never breaks.
    """
    buckets: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in data.history:
        value = row.get(column)
        if value is not None:
            buckets[row["variant"]][row["generation"]].append(value)

    curves: dict[str, tuple[list[int], list[float]]] = {}
    for variant in data.variants:
        by_generation = buckets.get(variant)
        if not by_generation:
            continue
        generations = sorted(by_generation)
        curves[variant] = (
            generations,
            [sum(by_generation[g]) / len(by_generation[g]) for g in generations],
        )
    return curves


def _flatten(config: dict, prefix: str, out: dict[str, Any]) -> None:
    """Config tree -> ``{"engine.n": 100, ...}``; lists become tuples so they compare."""
    for key, value in config.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            _flatten(value, path, out)
        else:
            out[path] = tuple(value) if isinstance(value, list) else value


def fixed_config(directory: Path) -> dict[str, Any]:
    """The settings every variant of the sweep shared, from ``resolved.json``.

    Read from what actually ran rather than from the sweep config, so a chart's
    caption cannot drift from the run it describes. Whatever the sweep varied
    differs between variants and is dropped here - what is left is, by
    construction, the fixed part of the experiment.

    Returns ``{}`` for a sweep predating ``resolved.json``; the caption is then
    simply omitted.
    """
    path = directory / "resolved.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

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


def final_values(data: SweepData, column: str) -> dict[str, list[float]]:
    """Per variant, one value per seed - the raw points behind the comparison."""
    values: dict[str, list[float]] = {variant: [] for variant in data.variants}
    for row in data.summary:
        if row.get(column) is not None:
            values[row["variant"]].append(row[column])
    return {variant: sorted(seen) for variant, seen in values.items() if seen}
