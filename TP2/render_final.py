"""Draw ``final.png`` from a finished run. Runs no GA.

Usage:
    python render_final.py RESULTS_DIR [--export-width W] [--export-height H]

Reads ``best.json`` (the winning genotype) and ``summary.json`` (the config
that produced it, so the picture is drawn by the same kernel, colour space and
triangle count that scored it) out of the results directory. The config file
itself is not needed, and neither is the machine the run happened on.

Defaults to the source image's native resolution. Image paths in the stored
config are relative, so run this from ``TP2/``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pipeline import render_final


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("results_dir", help="a directory simulate.py wrote")
    parser.add_argument(
        "--export-width", type=int, default=None,
        help="render width (default: the source image's native width)",
    )
    parser.add_argument(
        "--export-height", type=int, default=None,
        help="render height (default: the source image's native height)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        path = render_final(
            Path(args.results_dir), args.export_width, args.export_height
        )
    except FileNotFoundError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
