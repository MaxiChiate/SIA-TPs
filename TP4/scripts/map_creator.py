"""Maps new creators into the saved z-score space using only the scaler in a .meta.json (DATA-03).

  .venv/bin/python scripts/map_creator.py \\
      --meta datos/prepared/creadores_zscore.meta.json --input nuevos.csv [--out z.csv]

--input is a CSV with a header and one raw creator per row. Column order is free, and extra
columns (creator_id, name, dropped variables) are ignored. The training data is never read, so
mapping datos/creadores.csv reproduces datos/prepared/creadores_zscore.csv byte for byte.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

import creadores


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--meta", type=Path, required=True, help="saved scaler (.meta.json)")
    parser.add_argument("--input", type=Path, required=True, help="CSV with raw creator rows")
    parser.add_argument("--out", type=Path, default=None, help="output CSV (default: stdout)")
    args = parser.parse_args()

    meta = creadores.load_meta(args.meta)
    with args.input.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        sys.exit(f"{args.input}: no creator rows")

    mapped = np.vstack([creadores.transform_new_creator(meta, row) for row in rows])
    text = creadores.zscore_csv_text(list(meta["features"]), mapped)
    if args.out is None:
        sys.stdout.write(text)
    else:
        args.out.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
