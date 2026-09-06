"""Draw a run's snapshots and assemble ``progress.gif``. Runs no GA.

Usage:
    python render_snapshots.py RESULTS_DIR [--export-width W] [--export-height H]
                               [--no-gif] [--gif-frame-ms MS] [--gif-hold-ms MS]

Reads ``checkpoints.jsonl`` - written by ``simulate.py --snapshot-every N`` -
and draws one PNG per checkpoint into ``snapshots/``, then splices them plus
``final.png`` into ``progress.gif``. ``final.png`` closes the animation because
the last checkpoint is only the best of *its* generation, while that is the
best individual of the whole run; it is rendered here if missing.

Image paths in the stored config are relative, so run this from ``TP2/``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pipeline import GIF_FILE, render_snapshots


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
    parser.add_argument(
        "--no-gif", action="store_true", help="draw the snapshots, skip progress.gif"
    )
    parser.add_argument(
        "--gif-frame-ms", type=int, default=120,
        help="milliseconds per snapshot frame (default: 120)",
    )
    parser.add_argument(
        "--gif-hold-ms", type=int, default=3000,
        help="milliseconds to hold the final image (default: 3000)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    out_dir = Path(args.results_dir)
    try:
        paths = render_snapshots(
            out_dir,
            args.export_width,
            args.export_height,
            gif=not args.no_gif,
            frame_ms=args.gif_frame_ms,
            hold_ms=args.gif_hold_ms,
        )
    except FileNotFoundError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1

    print(f"wrote {len(paths)} snapshots to {out_dir / 'snapshots'}")
    if not args.no_gif:
        print(f"wrote {out_dir / GIF_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
