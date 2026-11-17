#!/usr/bin/env python3
"""Converts src/font.h (32 characters of 7x5 pixels) into the CSV the autoencoder trains on.

Each row is one character: 35 inputs (pixels, row by row, 1 = on) followed by the same 35 values as zetas,
since an autoencoder's expected output is its input.

    python3 scripts/font_to_csv.py [font.h] [out.csv]
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROWS, COLS = 7, 5


def read_font(path):
    text = path.read_text()
    text = re.sub(r"//[^\n]*", "", text)  # the comments name each character, they aren't data
    values = [int(h, 16) for h in re.findall(r"0x[0-9a-fA-F]+", text)]
    if len(values) % ROWS != 0:
        sys.exit(f"{path}: {len(values)} values, not a multiple of {ROWS}")
    return [values[i:i + ROWS] for i in range(0, len(values), ROWS)]


def pixels(character):
    # bit 4 is the leftmost pixel of a row
    return [(row >> (COLS - 1 - col)) & 1 for row in character for col in range(COLS)]


def main():
    font = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "src" / "font.h"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "neuron" / "data" / "font.csv"
    n = ROWS * COLS

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as file:
        file.write(",".join([f"x{i + 1}" for i in range(n)] + [f"zeta_{i + 1}" for i in range(n)]) + "\n")
        for character in read_font(font):
            row = pixels(character)
            file.write(",".join(map(str, row + row)) + "\n")
    print(out)


if __name__ == "__main__":
    main()
