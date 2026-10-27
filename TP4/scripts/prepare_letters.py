"""Writes the +-1 matrix of the approved 5x5 alphabet (D-01); never runs the network.

Run from anywhere:

  .venv/bin/python scripts/prepare_letters.py [--show]

Outputs (generated, not versioned) in --out-dir (default datos/prepared):
  alphabet_pm1.csv        header p0..p24, 26 rows of -1/1 in A..Z order (what the C binary reads)
  alphabet_pm1.meta.json  source, source_sha256, letters, encoding, n_patterns, n_pixels
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import letters


def display(path: Path) -> str:
    try:
        return path.resolve().relative_to(letters.TP_DIR).as_posix()
    except ValueError:
        return path.name


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=letters.ALPHABET_PATH)
    parser.add_argument("--out-dir", type=Path, default=letters.PREPARED_DIR)
    parser.add_argument("--show", action="store_true", help="print the 26 glyphs before writing")
    args = parser.parse_args()

    try:
        alphabet, paths = letters.prepare(args.source, args.out_dir)
    except letters.LettersError as error:
        print(f"letters: {error}", file=sys.stderr)
        sys.exit(1)

    if args.show:
        blocks = []
        for label, pattern in zip(alphabet.letters, alphabet.patterns):
            blocks.append("\n".join([label, *letters.render(pattern)]))
        print("\n\n".join(blocks))
        print()
    for path in paths:
        print(f"wrote {display(path)}")


if __name__ == "__main__":
    main()
