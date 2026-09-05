"""Parallel orchestrator: run every (variant, seed) and emit results as they land.

One process per run, bounded by a ``ProcessPoolExecutor``. Parallelising across
runs rather than inside them is the right grain here: a single GA run is a long
sequential chain of generations, while runs are completely independent of each
other. ``analysis.config.config_for`` correspondingly pins each run's own
``engine.processes`` to 1 so the two levels never oversubscribe the CPU.

``run_sweep`` is a generator: it yields each result the moment it is ready, so
the CLI can write CSV rows incrementally instead of buffering the whole batch.
"""

from __future__ import annotations

import json
import subprocess
import traceback
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from multiprocessing import get_context
from pathlib import Path
from typing import Any, Callable, Iterator

# Imported for their registration side effects: with the "spawn" start method
# each worker re-imports this module, and the registry must be populated there
# too before ``load_config`` can resolve any operator by name.
import ga.operators  # noqa: F401
import problems.triangles  # noqa: F401
from ga.config import load_config
from ga.core.engine import Engine

from .config import PROJECT_ROOT, SweepConfig, config_for
from .records import STATUS_ERROR, STATUS_OK, HistoryRow, RunRecord

ProgressHook = Callable[[RunRecord, int, int], None]


@dataclass(frozen=True, slots=True)
class Task:
    """One unit of work: a fully resolved run config plus its identity."""

    sweep_id: str
    variant: str
    seed: int
    overrides: str
    config: dict[str, Any]
    started_at_utc: str
    git_commit: str | None

    def describe(self) -> str:
        return f"{self.variant} / seed {self.seed}"


def make_sweep_id(now: datetime | None = None) -> str:
    """Batch id: a filename-safe UTC timestamp."""
    moment = now or datetime.now(timezone.utc)
    return moment.strftime("%Y%m%dT%H%M%SZ")


def git_commit() -> str | None:
    """Short commit hash of the working tree, or ``None`` outside a repo."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout.strip() or None


def build_tasks(sweep: SweepConfig, sweep_id: str) -> list[Task]:
    """The cartesian product variant x seed.

    Seeds are the outer loop so that a batch cut short still holds one seed of
    every variant, rather than every seed of the first few variants.
    """
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    commit = git_commit()
    tasks: list[Task] = []
    for seed in sweep.seeds:
        for variant in sweep.variants:
            tasks.append(
                Task(
                    sweep_id=sweep_id,
                    variant=variant.label,
                    seed=seed,
                    overrides=json.dumps(variant.overrides, sort_keys=True),
                    config=config_for(sweep, variant, seed),
                    started_at_utc=started_at,
                    git_commit=commit,
                )
            )
    return tasks


def execute_task(task: Task) -> tuple[RunRecord, list[HistoryRow]]:
    """Run one GA to completion and package its result. Never raises."""
    try:
        loaded = load_config(task.config)
        result = Engine(loaded.problem, loaded.engine_config, loaded.rng).run()
    except Exception as err:  # noqa: BLE001 - one bad run must not sink the batch
        return _error_record(task, f"{type(err).__name__}: {err}", traceback.format_exc()), []

    final = result.history[-1]
    record = RunRecord(
        sweep_id=task.sweep_id,
        variant=task.variant,
        seed=task.seed,
        overrides=task.overrides,
        status=STATUS_OK,
        best_fitness=result.best.fitness,
        best_generation=result.best_generation,
        stop_reason=result.stop_reason,
        generations=result.generations,
        evaluations=result.evaluations,
        elapsed_seconds=result.elapsed_seconds,
        final_mean_fitness=final.mean_fitness,
        final_diversity=final.genotypic_diversity,
        started_at_utc=task.started_at_utc,
        git_commit=task.git_commit,
        error_message=None,
    )
    rows = [
        HistoryRow(
            sweep_id=task.sweep_id,
            variant=task.variant,
            seed=task.seed,
            generation=entry.generation,
            best_fitness=entry.best_fitness,
            mean_fitness=entry.mean_fitness,
            std_fitness=entry.std_fitness,
            worst_fitness=entry.worst_fitness,
            genotypic_diversity=entry.genotypic_diversity,
            cumulative_evaluations=entry.cumulative_evaluations,
            cumulative_seconds=entry.cumulative_seconds,
        )
        for entry in result.history
    ]
    return record, rows


def _error_record(task: Task, message: str, detail: str) -> RunRecord:
    print(detail)  # the full traceback goes to the console, the message to the CSV
    return RunRecord(
        sweep_id=task.sweep_id,
        variant=task.variant,
        seed=task.seed,
        overrides=task.overrides,
        status=STATUS_ERROR,
        best_fitness=None,
        best_generation=None,
        stop_reason=None,
        generations=None,
        evaluations=None,
        elapsed_seconds=None,
        final_mean_fitness=None,
        final_diversity=None,
        started_at_utc=task.started_at_utc,
        git_commit=task.git_commit,
        error_message=message,
    )


def run_sweep(
    sweep: SweepConfig,
    sweep_id: str | None = None,
    progress: ProgressHook | None = None,
) -> Iterator[tuple[RunRecord, list[HistoryRow]]]:
    """Run the whole batch, yielding each run's result as it completes."""
    sweep_id = sweep_id or make_sweep_id()
    tasks = build_tasks(sweep, sweep_id)
    total = len(tasks)

    results = (
        _run_serial(tasks) if sweep.workers == 1 else _run_parallel(tasks, sweep.workers)
    )
    for index, (record, rows) in enumerate(results, start=1):
        if progress is not None:
            progress(record, index, total)
        yield record, rows


def _run_serial(tasks: list[Task]) -> Iterator[tuple[RunRecord, list[HistoryRow]]]:
    for task in tasks:
        yield execute_task(task)


def _run_parallel(
    tasks: list[Task], workers: int
) -> Iterator[tuple[RunRecord, list[HistoryRow]]]:
    """Results come back in submission order, not completion order.

    ``Executor.map`` is deliberate: a sweep's rows should land in a stable,
    reproducible order so two batches of the same config diff cleanly. The cost
    is that a slow run holds back the rows queued behind it.
    """
    # "spawn" gives a clean child on every platform and avoids inheriting the
    # parent's imported state.
    context = get_context("spawn")
    with ProcessPoolExecutor(max_workers=workers, mp_context=context) as pool:
        yield from pool.map(execute_task, tasks)


def write_resolved_configs(sweep: SweepConfig, tasks: list[Task], out_dir: Path) -> None:
    """Dump what actually ran, so a batch can be reproduced from its own output."""
    payload = {
        "sweep_config": str(sweep.source_path),
        "base_config": str(sweep.base_config_path),
        "seeds": list(sweep.seeds),
        "variants": {
            task.variant: task.config for task in tasks if task.seed == sweep.seeds[0]
        },
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "resolved.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
