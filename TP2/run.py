"""CLI entry point: run one GA config end-to-end and write its results.

Usage:
    python run.py [config.json] [--out DIR] [--snapshot-every N]
                   [--export-width W] [--export-height H]
                   [--no-gif] [--gif-frame-ms MS] [--gif-hold-ms MS]
                   [--progress-every N | --quiet]

The one-command path: simulate, then draw. It is exactly ``simulate.py``
followed by ``render_final.py`` and ``render_snapshots.py`` - the three stages
live in ``pipeline.py`` and this script only chains them, so there is one
implementation of each and no way for the combined path to drift from the
separate ones.

Writes into the results directory: ``history.csv`` / ``history.json`` (unless
the config's ``write_history`` is ``false``), ``summary.json``, ``best.json``,
``figures.json``, ``final.png``, and - only with ``--snapshot-every`` -
``checkpoints.jsonl``, ``snapshots/gen_*.png`` and ``progress.gif``.

For timing work use ``simulate.py`` instead: the rendering here happens after
the engine loop and is not in ``elapsed_seconds``, but it is still minutes of
wall clock that a timing sweep has no reason to pay.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ga.config import ConfigError
from pipeline import (
    CHECKPOINTS_FILE,
    render_final,
    render_snapshots,
    results_dir,
    simulate,
)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a GA config end-to-end.")
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
        help="save an intermediate render every N generations (0 = disabled)",
    )
    parser.add_argument(
        "--export-width", type=int, default=None,
        help="final render width (default: the source image's native width)",
    )
    parser.add_argument(
        "--export-height", type=int, default=None,
        help="final render height (default: the source image's native height)",
    )
    parser.add_argument(
        "--no-gif", action="store_true",
        help="skip progress.gif (it is built whenever --snapshot-every is set)",
    )
    parser.add_argument(
        "--gif-frame-ms", type=int, default=120,
        help="milliseconds per snapshot frame in progress.gif (default: 120)",
    )
    parser.add_argument(
        "--gif-hold-ms", type=int, default=3000,
        help="milliseconds to hold the final image in progress.gif (default: 3000)",
    )
    parser.add_argument(
        "--progress-every", type=int, default=1,
        help="print a progress line every N generations (0 = silent)",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="shorthand for --progress-every 0"
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

    render_final(out_dir, args.export_width, args.export_height)
    if (out_dir / CHECKPOINTS_FILE).is_file():
        render_snapshots(
            out_dir,
            args.export_width,
            args.export_height,
            gif=not args.no_gif,
            frame_ms=args.gif_frame_ms,
            hold_ms=args.gif_hold_ms,
        )

    print(
        f"\nbest fitness {result.best.fitness:.6f} at generation "
        f"{result.best_generation} (stopped: {result.stop_reason})"
    )
    print(f"results written to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
