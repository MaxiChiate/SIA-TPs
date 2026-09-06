"""Run the GA and write only its data. Draws nothing.

Usage:
    python simulate.py [config.json] [--out DIR] [--snapshot-every N]
                       [--progress-every N | --quiet]

Writes ``history.csv`` / ``history.json`` (one row per generation),
``summary.json`` (best fitness, stop reason, resolved problem, full config),
``best.json`` (the winning genotype at full precision) and ``figures.json``
(that genotype enumerated as shapes + colour). With ``--snapshot-every N`` it
also writes ``checkpoints.jsonl``, which is what ``render_snapshots.py`` draws
from afterwards.

This is the script to time. ``summary.json``'s ``elapsed_seconds`` measures the
engine loop, and the loop no longer contains a rasterizer or, at
``--progress-every 0``, a stream of prints - so the number is the algorithm and
nothing else. Use ``run.py`` when the pictures are wanted in one command.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ga.config import ConfigError
from pipeline import results_dir, simulate


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "config", nargs="?", default="config.json",
        help="path to the run's config JSON (default: config.json)",
    )
    parser.add_argument(
        "--out", default=None,
        help="results directory (default: results/<config stem>_<timestamp>/)",
    )
    parser.add_argument(
        "--snapshot-every", type=int, default=0,
        help="keep the generation's best individual every N generations, for "
             "render_snapshots.py to draw later (0 = disabled)",
    )
    parser.add_argument(
        "--progress-every", type=int, default=1,
        help="print a progress line every N generations (0 = silent). The "
             "printing happens inside the timed loop, so raise it for timing runs",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="shorthand for --progress-every 0",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    config_path = Path(args.config)
    out_dir = results_dir(config_path, args.out)

    try:
        result = simulate(
            config_path,
            out_dir,
            snapshot_every=args.snapshot_every,
            progress_every=0 if args.quiet else args.progress_every,
        )
    except ConfigError as err:
        print(f"config error: {err}", file=sys.stderr)
        return 1

    print(
        f"\nbest fitness {result.best.fitness:.6f} at generation "
        f"{result.best_generation} (stopped: {result.stop_reason})"
    )
    print(
        f"{result.generations} generations, {result.evaluations} evaluations, "
        f"{result.elapsed_seconds:.1f}s "
        f"({result.elapsed_seconds / max(result.generations, 1) * 1000:.1f} ms/gen)"
    )
    print(f"data written to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
