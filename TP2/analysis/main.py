#!/usr/bin/env python3
"""CLI for the experiment runner.

    python3 analysis/main.py                     # uses analysis/sweep.json
    python3 analysis/main.py serie_a.json
    python3 analysis/main.py serie_a.json --workers 8
    python3 analysis/main.py serie_a.json --dry-run   # show the plan, run nothing

Writes ``summary.csv`` (one row per run) and ``history.csv`` (one row per
generation) into ``<output_dir>/<sweep_id>/``, flushing as it goes so a batch
that gets interrupted still leaves usable data.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

# Invoked as `python3 analysis/main.py`, without -m: the project root is not on
# the path yet, so `analysis` and `ga` would not be importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analysis.config import (  # noqa: E402
    PROJECT_ROOT,
    SweepConfigError,
    load_sweep_config,
)
from analysis.records import (  # noqa: E402
    STATUS_OK,
    history_writer,
    summary_writer,
)
from analysis.runner import (  # noqa: E402
    build_tasks,
    make_sweep_id,
    run_sweep,
    write_resolved_configs,
)

DEFAULT_SWEEP = PROJECT_ROOT / "analysis" / "sweep.json"


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="analysis/main.py",
        description="Run a sweep of GA configs and dump comparable CSVs.",
    )
    parser.add_argument(
        "sweep", nargs="?", default=None,
        help=f"sweep config JSON (default: {DEFAULT_SWEEP.name})",
    )
    parser.add_argument("--workers", type=int, help="override 'workers' from the config")
    parser.add_argument("--output-dir", help="override 'output_dir' from the config")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="validate and print the plan without running anything",
    )
    parser.add_argument("--quiet", action="store_true", help="do not print each run")
    return parser.parse_args(argv[1:])


def _apply_overrides(sweep, args):
    changes = {}
    if args.workers is not None:
        if args.workers < 1:
            raise SweepConfigError("--workers must be >= 1")
        changes["workers"] = args.workers
    if args.output_dir:
        path = Path(args.output_dir)
        changes["output_dir"] = path if path.is_absolute() else PROJECT_ROOT / path
    return replace(sweep, **changes) if changes else sweep


def _print_plan(sweep, sweep_id: str, out_dir: Path) -> None:
    print(f"sweep_id:    {sweep_id}")
    print(f"sweep:       {sweep.source_path}")
    print(f"base config: {sweep.base_config_path}")
    print(f"variants:    {', '.join(variant.label for variant in sweep.variants)}")
    print(f"seeds:       {', '.join(str(seed) for seed in sweep.seeds)}")
    print(f"workers:     {sweep.workers}")
    print(f"runs:        {sweep.total_runs()}")
    print(f"output:      {out_dir}")


def main(argv: list[str]) -> int:
    args = _parse_args(argv)

    try:
        sweep = load_sweep_config(args.sweep or DEFAULT_SWEEP)
        sweep = _apply_overrides(sweep, args)
    except SweepConfigError as err:
        print(f"sweep config error: {err}", file=sys.stderr)
        return 1

    sweep_id = make_sweep_id()
    out_dir = sweep.output_dir / sweep_id
    _print_plan(sweep, sweep_id, out_dir)

    tasks = build_tasks(sweep, sweep_id)
    if args.dry_run:
        print("\n--dry-run: nothing was executed. Would run:")
        for task in tasks:
            print(f"  {task.describe()}")
        return 0

    print()
    write_resolved_configs(sweep, tasks, out_dir)
    total = len(tasks)
    written = 0
    failed = 0

    def progress(record, index: int, total: int) -> None:
        if args.quiet:
            return
        if record.status == STATUS_OK:
            detail = (
                f"best={record.best_fitness:.6f} @gen {record.best_generation:<4} "
                f"({record.stop_reason}, {record.elapsed_seconds:.1f}s)"
            )
        else:
            detail = f"ERROR  {record.error_message}"
        print(
            f"[{index:>{len(str(total))}}/{total}] {record.variant} / seed {record.seed}"
            f"  {detail}",
            flush=True,
        )

    try:
        with summary_writer(out_dir / "summary.csv") as summary, history_writer(
            out_dir / "history.csv"
        ) as history:
            for record, rows in run_sweep(sweep, sweep_id=sweep_id, progress=progress):
                summary.write(record)
                history.write_all(rows)
                written += 1
                failed += record.status != STATUS_OK
    except KeyboardInterrupt:
        print(f"\ninterrupted: {written}/{total} runs left in {out_dir}", file=sys.stderr)
        return 130

    print(f"\n{written} runs -> {out_dir}")
    print("  summary.csv  one row per run")
    print("  history.csv  one row per generation")
    if failed:
        print(f"  WARNING: {failed} run(s) failed; see error_message", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
