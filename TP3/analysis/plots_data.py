"""Load a series' results and aggregate them into what each chart draws.

Reading and shaping only: nothing here knows about plotly. Standard library `csv` instead of pandas, the
files are a few thousand rows.

A series directory (made by `sweep.py`) holds `plan.json`, `summary.csv` (one row per run) and
`runs/<run>/epochs.csv` (one row per epoch). The history the curves need is read from those epochs.csv,
so it doesn't need a file of its own; the price is that deleting `runs/` to save disk also deletes the curves.

Seeds are averaged per epoch, so one variant is one line. The spread across seeds is kept apart for the
comparison charts, where it is the interesting part: a difference smaller than the seed spread is not a
difference.
"""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

_SUMMARY_INT = frozenset({"variant", "seed", "epochs_run", "best_epoch"})
_SUMMARY_STRING = frozenset({"run", "label", "status"})
_NOT_A_CONFIG_KEY = "seed"  # per run, not something a series varies between variants


class SweepDataError(Exception):
    """The series directory is missing, empty, or holds no successful run."""


@dataclass(frozen=True)
class SweepData:
    """One series: its plan, the successful runs, every epoch of each, and the variant order all charts share."""

    directory: Path
    plan: dict[str, Any]
    summary: list[dict]  # successful runs only; "variant" is the label, "variant_index" its position
    history: list[dict]  # one row per (run, epoch): variant, seed, epoch, train_*, validation_*, elapsed_s
    variants: tuple[str, ...]

    @property
    def seeds(self) -> tuple[int, ...]:
        return tuple(sorted({row["seed"] for row in self.summary}))


# ---------- loading ----------

def _number(value: str) -> float | None:
    return None if value == "" else float(value)


def _coerce_summary(row: dict[str, str]) -> dict:
    out: dict = {}
    for key, value in row.items():
        if key in _SUMMARY_STRING:
            out[key] = value
        elif key == "converged":
            out[key] = None if value == "" else value == "True"
        elif value == "":
            out[key] = None
        else:
            out[key] = int(value) if key in _SUMMARY_INT else float(value)
    return out


def load_summary_rows(directory: Path) -> list[dict]:
    """Every row of summary.csv, the failed runs included; "variant" is renamed to its label."""
    path = directory / "summary.csv"
    if not path.is_file():
        raise SweepDataError(f"missing summary.csv in {directory}")
    with path.open(newline="", encoding="utf-8") as file:
        rows = [_coerce_summary(row) for row in csv.DictReader(file)]
    for row in rows:
        row["variant_index"] = row["variant"]
        row["variant"] = row["label"]
    return rows


def _load_epochs(path: Path, variant: str, seed: int) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as file:
        return [{"variant": variant, "seed": seed, "epoch": int(row["epoch"]),
                 **{key: _number(value) for key, value in row.items() if key != "epoch"}}
                for row in csv.DictReader(file)]


def load_history(directory: Path, summary: list[dict]) -> list[dict]:
    history: list[dict] = []
    for row in summary:
        path = directory / "runs" / row["run"] / "epochs.csv"
        if not path.is_file():
            raise SweepDataError(f"missing {path}: the curves are read from the runs' epochs.csv")
        history.extend(_load_epochs(path, row["variant"], row["seed"]))
    return history


def load_sweep(directory: Path) -> SweepData:
    plan_path = directory / "plan.json"
    if not plan_path.is_file():
        raise SweepDataError(f"missing plan.json in {directory}")
    plan = json.loads(plan_path.read_text())

    summary = [row for row in load_summary_rows(directory) if row["status"] == "ok"]
    if not summary:
        raise SweepDataError(f"{directory}: no successful run in summary.csv")

    # The order the series declared, which fixes each variant's color in every chart
    ran = {row["variant"] for row in summary}
    variants = tuple(variant["label"] for variant in plan["variants"] if variant["label"] in ran)
    return SweepData(directory, plan, summary, load_history(directory, summary), variants)


def latest_sweep(root: Path) -> Path:
    """The series whose summary.csv was written last."""
    candidates = sorted(root.glob("*/summary.csv"), key=lambda path: path.stat().st_mtime) if root.is_dir() else []
    if not candidates:
        raise SweepDataError(f"no series with a summary.csv under {root}: run analysis/sweep.py first")
    return candidates[-1].parent


# ---------- curves ----------

# What a curve can be plotted against. The epoch is right while every variant pays the same per epoch;
# seconds exist for the series where it doesn't (batch_size or the architecture change the cost of an epoch)
X_COLUMNS: dict[str, str] = {
    "epoch": "Época",
    "elapsed_s": "Segundos de entrenamiento",
}


@dataclass(frozen=True)
class Band:
    """One variant's curve: the mean over seeds, plus the spread around it.

    low/high are the full min-max range across seeds, not a standard deviation. With few seeds the question
    a reader asks is "could these two variants have swapped places on another seed", and the full range
    answers exactly that.
    """

    x: list[float]
    mean: list[float]
    low: list[float]
    high: list[float]

    def error_marks(self, count: int, phase: float = 0.0) -> tuple[list[float], list[float], list[float], list[float]]:
        """`count` evenly spaced points of the curve as `(x, y, up, down)`.

        `phase` in [0, 1) shifts which points a variant samples, so several curves put their bars at
        different x instead of stacking them. Up/down are distances from the mean, the form plotly's
        asymmetric `error_y` takes.
        """
        total = len(self.x)
        if total == 0 or count <= 0:
            return [], [], [], []
        step = total / min(count, total)
        indices = sorted({min(total - 1, int(step * (position + phase))) for position in range(min(count, total))}
                         | {total - 1})
        return ([self.x[i] for i in indices], [self.mean[i] for i in indices],
                [self.high[i] - self.mean[i] for i in indices], [self.mean[i] - self.low[i] for i in indices])


ValueSpec = str | Callable[[dict], float | None]


def generalization_gap(row: dict) -> float | None:
    """Validation MSE minus train MSE: how much worse the network does on samples it never trained on."""
    train, validation = row.get("train_mse"), row.get("validation_mse")
    return None if train is None or validation is None else validation - train


def _value_of(row: dict, value: ValueSpec) -> float | None:
    return row.get(value) if isinstance(value, str) else value(row)


def _points_by_seed(data: SweepData, value: ValueSpec, x_column: str) -> dict[str, dict[int, dict[int, tuple[float, float]]]]:
    """`variant -> seed -> epoch -> (x, y)`, dropping the rows that lack either."""
    out: dict[str, dict[int, dict[int, tuple[float, float]]]] = defaultdict(lambda: defaultdict(dict))
    for row in data.history:
        y, x = _value_of(row, value), row.get(x_column)
        if y is not None and x is not None:
            out[row["variant"]][row["seed"]][row["epoch"]] = (x, y)
    return out


def curve_bands(data: SweepData, value: ValueSpec, x_column: str = "epoch") -> dict[str, Band]:
    """Per variant, the seed-averaged curve of `value` with its seed spread.

    `value` is an epochs.csv column, or a callable on a row for a derived quantity. A run that stopped early
    keeps its last value for the epochs it didn't train (training ended there), so the average never mixes
    in fewer seeds toward the end. The x of a padded point isn't padded: it averages only the seeds that
    really got there.
    """
    bands: dict[str, Band] = {}
    for variant, seeds in _points_by_seed(data, value, x_column).items():
        last_epoch = max(max(points) for points in seeds.values())
        xs, means, lows, highs = [], [], [], []
        for epoch in range(last_epoch + 1):
            ys, real_xs = [], []
            for points in seeds.values():
                if epoch in points:
                    real_xs.append(points[epoch][0])
                    ys.append(points[epoch][1])
                else:
                    ys.append(points[max(points)][1])
            if not real_xs:
                continue
            xs.append(sum(real_xs) / len(real_xs))
            means.append(sum(ys) / len(ys))
            lows.append(min(ys))
            highs.append(max(ys))
        bands[variant] = Band(xs, means, lows, highs)
    return {variant: bands[variant] for variant in data.variants if variant in bands}


def final_values(data: SweepData, column: str, scale: float = 1.0) -> dict[str, list[float]]:
    """Per variant, one value per seed: the raw points behind the comparison."""
    values: dict[str, list[float]] = {variant: [] for variant in data.variants}
    for row in data.summary:
        if row.get(column) is not None:
            values[row["variant"]].append(scale * row[column])
    return {variant: sorted(seen) for variant, seen in values.items() if seen}


# ---------- config: what the series held fixed and what it varied ----------

def variant_configs(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """`label -> config`, as it ran (the seed aside): base, then the series' shared `set`, then the variant's own."""
    shared = {**plan["base_config"], **plan["set"]}
    return {variant["label"]: {key: value for key, value in {**shared, **variant["overrides"]}.items()
                               if key != _NOT_A_CONFIG_KEY}
            for variant in plan["variants"]}


def _as_comparable(value: Any) -> Any:
    return tuple(value) if isinstance(value, list) else value


def fixed_config(plan: dict[str, Any]) -> dict[str, Any]:
    """The settings every variant shared. Read from the resolved plan so a caption can't drift from the run."""
    configs = list(variant_configs(plan).values())
    first, *rest = configs
    return {key: value for key, value in first.items()
            if all(_as_comparable(other.get(key)) == _as_comparable(value) for other in rest)}


def varied_keys(plan: dict[str, Any]) -> list[str]:
    configs = list(variant_configs(plan).values())
    keys = {key for config in configs for key in config}
    return sorted(key for key in keys
                  if len({json.dumps(config.get(key), sort_keys=True) for config in configs}) > 1)


# Fixed-caption fields in reading order: the network, then the data
_NETWORK_FIELDS = (("activation", "activación"), ("hidden_layers", "capas ocultas"), ("eta", "η"),
                   ("batch_size", "batch"), ("epochs", "épocas"), ("shuffle", "shuffle"), ("tolerance", "tolerancia"))
_DATA_FIELDS = (("train_dataset", "train"), ("validation_dataset", "validación"),
                ("validation_split", "split de validación"), ("split_seed", "split_seed"))

# What a series varied -> how to name it in a title. Falls back to the raw key: an ugly title, not a wrong one
KNOB_NAMES = {
    "eta": "tasa de aprendizaje",
    "hidden_layers": "arquitectura",
    "batch_size": "tamaño de batch",
    "activation": "función de activación",
    "train_dataset": "dataset de entrenamiento",
    "shuffle": "shuffle",
    "epochs": "cantidad de épocas",
    "validation_split": "proporción de validación",
}


def _format_value(key: str, value: Any) -> str:
    if key.endswith("_dataset"):
        return Path(str(value)).name
    return json.dumps(value) if isinstance(value, (list, bool)) else str(value)


def fixed_captions(fixed: dict[str, Any]) -> list[str]:
    """Two caption lines naming what was held constant across every run."""
    lines = []
    for label, fields in (("Fijo", _NETWORK_FIELDS), ("Datos", _DATA_FIELDS)):
        parts = [f"{name} {_format_value(key, fixed[key])}" for key, name in fields if key in fixed]
        if parts:
            lines.append(f"{label}: " + " · ".join(parts))
    return lines


def varied_knob(sweep_dir: Path, plan: dict[str, Any]) -> str:
    """Name of what the series changed, for chart titles. A `title` in the series file wins."""
    series_path = sweep_dir / "series.json"
    if series_path.is_file():
        declared = json.loads(series_path.read_text()).get("title")
        if isinstance(declared, str) and declared:
            return declared
    varied = varied_keys(plan)
    for key, name in KNOB_NAMES.items():
        if key in varied:
            return name
    return varied[0] if varied else "variante"


# ---------- catalog ----------

@dataclass(frozen=True)
class SweepSummary:
    """One series as the landing page lists it, without loading its epochs."""

    directory: Path
    title: str
    variants: tuple[str, ...]
    seeds: int
    runs: int
    failed: int
    started: str
    has_charts: bool


_STARTED = re.compile(r"_(\d{4}-\d{2}-\d{2})_(\d{2})-(\d{2})-(\d{2})$")


def sweep_catalog(root: Path) -> list[SweepSummary]:
    """Every series under `root`, newest first. One with an unreadable summary is skipped, not fatal."""
    if not root.is_dir():
        return []
    out = []
    for summary_path in sorted(root.glob("*/summary.csv"), key=lambda path: path.stat().st_mtime, reverse=True):
        directory = summary_path.parent
        try:
            rows = load_summary_rows(directory)
            plan = json.loads((directory / "plan.json").read_text())
        except (SweepDataError, OSError, ValueError, KeyError):
            continue
        if not rows:
            continue
        variants = tuple(dict.fromkeys(row["variant"] for row in rows))
        match = _STARTED.search(directory.name)
        out.append(SweepSummary(
            directory, varied_knob(directory, plan), variants, len({row["seed"] for row in rows}), len(rows),
            sum(row["status"] != "ok" for row in rows),
            f"{match[1]} {match[2]}:{match[3]}" if match else "", (directory / "index.html").is_file()))
    return out
