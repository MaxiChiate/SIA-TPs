"""Writes the +-1 matrix of the five fixed 37x37 QR PNGs (HOP-04); never runs the network.

Run from anywhere:

  .venv/bin/python scripts/prepare_qr.py [--show]

Outputs (generated, not versioned) in --out-dir (default datos/prepared):
  qr_pm1.csv        header p0..p1368, 5 rows of -1/1 in the fixed SOURCES order
  qr_pm1.meta.json  source, per-PNG sha256, sources order, encoding, polarity, n_patterns, n_pixels
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import qr


def display(path: Path) -> str:
    try:
        return path.resolve().relative_to(qr.TP_DIR).as_posix()
    except ValueError:
        return path.name


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source-dir", type=Path, default=qr.HOPFIELD_DIR)
    parser.add_argument("--out-dir", type=Path, default=qr.PREPARED_DIR)
    parser.add_argument("--show", action="store_true", help="print the five QR names before writing")
    args = parser.parse_args()

    try:
        qr_set, paths = qr.prepare(args.source_dir, args.out_dir)
    except qr.QrError as error:
        print(f"qr: {error}", file=sys.stderr)
        sys.exit(1)

    if args.show:
        for name in qr_set.names:
            print(name)
    for path in paths:
        print(f"wrote {display(path)}")


if __name__ == "__main__":
    main()
