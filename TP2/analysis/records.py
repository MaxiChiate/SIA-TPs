"""Output schema: the two CSVs a sweep produces, and their incremental writers.

Two files rather than one, because the plots need two shapes of data:

``summary.csv``  one row per run - to compare variants against each other
                 (final fitness, when it got there, how long it took).
``history.csv``  one row per (run, generation), long format - to draw the
                 fitness and diversity curves over time. Join to the summary on
                 ``(variant, seed)``.

Both dataclasses hold primitives only: they serialise to CSV without surprises
and travel through pickle between processes without dragging engine objects
along.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import IO, Iterable

STATUS_OK = "ok"        # the run finished and produced a best individual
STATUS_ERROR = "error"  # the run raised; the row keeps the message

STATUSES = (STATUS_OK, STATUS_ERROR)


@dataclass(frozen=True, slots=True)
class RunRecord:
    """The outcome of ONE run: one variant at one seed."""

    # --- identity ---
    sweep_id: str
    variant: str
    seed: int
    overrides: str  # JSON blob: what this variant changed vs. the base config

    # --- outcome ---
    status: str
    best_fitness: float | None
    best_generation: int | None
    stop_reason: str | None
    generations: int | None
    evaluations: int | None
    elapsed_seconds: float | None

    # --- final-generation snapshot, for cheap comparisons ---
    final_mean_fitness: float | None
    final_diversity: float | None

    # --- context (identical across the whole batch) ---
    started_at_utc: str
    git_commit: str | None
    error_message: str | None


@dataclass(frozen=True, slots=True)
class HistoryRow:
    """One generation of one run: ``GenerationRecord`` plus the run's identity."""

    sweep_id: str
    variant: str
    seed: int
    generation: int
    best_fitness: float
    mean_fitness: float
    std_fitness: float
    worst_fitness: float
    genotypic_diversity: float
    cumulative_evaluations: int
    cumulative_seconds: float


SUMMARY_COLUMNS: tuple[str, ...] = tuple(field.name for field in fields(RunRecord))
HISTORY_COLUMNS: tuple[str, ...] = tuple(field.name for field in fields(HistoryRow))


class CsvWriter:
    """Appends dataclass rows to a CSV, flushing each one.

    Incremental on purpose: a sweep can run for an hour, and if it is cut short
    (Ctrl-C, a dead battery) the rows already finished stay on disk.
    """

    def __init__(self, path: Path, columns: tuple[str, ...]) -> None:
        self.path = path
        self.columns = columns
        self._handle: IO[str] | None = None
        self._writer: csv.DictWriter | None = None

    def __enter__(self) -> "CsvWriter":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._handle, fieldnames=list(self.columns))
        self._writer.writeheader()
        self._handle.flush()
        return self

    def write(self, row) -> None:
        if self._writer is None or self._handle is None:
            raise RuntimeError("CsvWriter used outside its context manager")
        self._writer.writerow(asdict(row))
        self._handle.flush()

    def write_all(self, rows: Iterable) -> None:
        for row in rows:
            self.write(row)

    def __exit__(self, *exc_info) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None
            self._writer = None


def summary_writer(path: Path) -> CsvWriter:
    return CsvWriter(path, SUMMARY_COLUMNS)


def history_writer(path: Path) -> CsvWriter:
    return CsvWriter(path, HISTORY_COLUMNS)
