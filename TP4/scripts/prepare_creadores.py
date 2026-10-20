"""Writes the audited z-scored creators matrix and the all-31 sensitivity matrix.

Run from anywhere:

  .venv/bin/python scripts/prepare_creadores.py

Outputs (generated, not versioned) in --out-dir (default datos/prepared):
  creadores_zscore.csv / .meta.json       audited set, 26 variables (D-08, D-09)
  creadores_zscore_all31.csv / .meta.json sensitivity set, 31 variables (DATA-05)
"""

from __future__ import annotations

import argparse
from pathlib import Path

import creadores


def display(path: Path) -> str:
    try:
        return path.resolve().relative_to(creadores.TP_DIR).as_posix()
    except ValueError:
        return path.name


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=creadores.RAW_PATH)
    parser.add_argument("--out-dir", type=Path, default=creadores.PREPARED_DIR)
    args = parser.parse_args()

    audit, paths = creadores.prepare(args.source, args.out_dir)

    print(f"kept {len(audit.kept)} variables, dropped {len(audit.dropped)}:")
    for dropped in audit.dropped:
        print(f"  {dropped.name}: {dropped.reason} ({dropped.reconstruct})")
    for path in paths:
        print(f"wrote {display(path)}")


if __name__ == "__main__":
    main()
