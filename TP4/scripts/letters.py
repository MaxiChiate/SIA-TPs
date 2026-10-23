"""Reads and encodes the hand-drawn 5x5 alphabet of D-01 ('*' = +1, '.' = -1, row-major).

Library only, no side effects on import. This module only reads and encodes bitmaps: it never
runs the network. The text format is, per letter, a label line (A..Z, in order) and five rows of
five characters, with exactly one empty line between blocks. Written files hold no timestamp and
no absolute path, so a rerun reproduces them byte for byte.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np

TP_DIR = Path(__file__).resolve().parent.parent
ALPHABET_PATH = TP_DIR / "datos" / "letters" / "alphabet_5x5.txt"
PREPARED_DIR = TP_DIR / "datos" / "prepared"
PREPARED_CSV = PREPARED_DIR / "alphabet_pm1.csv"

SIDE = 5
N_PIXELS = SIDE * SIDE
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ON = "*"
OFF = "."
ENCODING = "row-major 5x5, '*' = +1, '.' = -1"


class LettersError(ValueError):
    """The alphabet text or file does not follow the D-01 / D-02 contract."""


@dataclass(frozen=True)
class Alphabet:
    letters: tuple[str, ...]
    patterns: np.ndarray  # (26, 25) int64, values +-1
    source_sha256: str


def encode(rows) -> np.ndarray:
    """Map five strings of '*' and '.' to the 25-vector of +-1 (pixel 5r + c)."""
    rows = list(rows)
    if len(rows) != SIDE or any(len(row) != SIDE for row in rows):
        raise LettersError(f"expected {SIDE} rows of {SIDE} characters")
    values = []
    for row in rows:
        for char in row:
            if char == ON:
                values.append(1)
            elif char == OFF:
                values.append(-1)
            else:
                raise LettersError(f"unexpected {char!r} in a glyph row")
    return np.array(values, dtype=np.int64)


def render(pattern) -> list[str]:
    """Inverse of encode: a 25-vector of +-1 back to its five rows."""
    flat = np.asarray(pattern).reshape(-1)
    if flat.size != N_PIXELS:
        raise LettersError(f"expected {N_PIXELS} pixels, found {flat.size}")
    chars = [ON if value > 0 else OFF for value in flat]
    return ["".join(chars[SIDE * r : SIDE * (r + 1)]) for r in range(SIDE)]


def parse_alphabet(text: str) -> Alphabet:
    """Parse the D-01 text into 26 +-1 patterns, refusing every D-02 violation with letter and line."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()  # the single final newline

    letters: list[str] = []
    patterns: list[np.ndarray] = []
    i = 0
    while i < len(lines):
        if lines[i] == "":
            raise LettersError(f"line {i + 1}: unexpected empty line (one empty line between blocks)")
        if len(letters) >= len(LETTERS):
            raise LettersError(f"line {i + 1}: expected {len(LETTERS)} letters, found more")
        expected = LETTERS[len(letters)]
        label = lines[i]
        if label != expected:
            raise LettersError(
                f"line {i + 1}: expected label {expected!r} (letter {expected}), found {label!r}"
            )
        start = i + 1
        end = start
        while end < len(lines) and lines[end] != "":
            end += 1
        rows = lines[start:end]
        if len(rows) != SIDE:
            raise LettersError(
                f"line {i + 1}: letter {expected}: expected {SIDE} rows, found {len(rows)}"
            )
        for offset, row in enumerate(rows):
            line_number = start + offset + 1
            for char in row:
                if char not in (ON, OFF):
                    raise LettersError(f"line {line_number}: letter {expected}: unexpected {char!r}")
            if len(row) != SIDE:
                raise LettersError(
                    f"line {line_number}: letter {expected}: expected {SIDE} characters, found {len(row)}"
                )
        letters.append(expected)
        patterns.append(encode(rows))
        i = end
        if i < len(lines):  # lines[i] is the empty separator
            i += 1
            if i >= len(lines) or lines[i] == "":
                raise LettersError(f"line {i}: unexpected empty line (one empty line between blocks)")

    if len(letters) != len(LETTERS):
        raise LettersError(f"expected {len(LETTERS)} letters, found {len(letters)}")

    matrix = np.vstack(patterns).astype(np.int64)
    gram = matrix @ matrix.T
    for a in range(len(LETTERS)):
        for b in range(a + 1, len(LETTERS)):
            if gram[a, b] == N_PIXELS:
                raise LettersError(f"letters {LETTERS[a]} and {LETTERS[b]} are identical")
            if gram[a, b] == -N_PIXELS:
                raise LettersError(
                    f"letters {LETTERS[a]} and {LETTERS[b]} are inverse of each other"
                    " (the classifier could not tell them apart)"
                )

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return Alphabet(letters=tuple(letters), patterns=matrix, source_sha256=digest)


def load_alphabet(path: Path = ALPHABET_PATH) -> Alphabet:
    path = Path(path)
    if not path.is_file():
        try:
            shown = path.resolve().relative_to(TP_DIR).as_posix()
        except ValueError:
            shown = str(path)
        raise LettersError(f"alphabet file not found: {shown}")
    return parse_alphabet(path.read_bytes().decode("utf-8"))


def _atomic_write(path: Path, text: str) -> None:
    """Write via a temporary file in the same folder, then os.replace: readers never see half."""
    handle, temp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", newline="", encoding="utf-8") as file:
            file.write(text)
        os.replace(temp_name, path)
    except BaseException:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
        raise


def _source_label(source: Path) -> str:
    try:
        return Path(source).resolve().relative_to(TP_DIR).as_posix()
    except ValueError:
        return Path(source).name


def write_prepared(alphabet: Alphabet, out_dir: Path, source: Path) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "alphabet_pm1.csv"
    meta_path = out_dir / "alphabet_pm1.meta.json"

    header = ",".join(f"p{k}" for k in range(N_PIXELS))
    body = [",".join(str(int(v)) for v in row) for row in alphabet.patterns]
    meta = {
        "source": _source_label(source),
        "source_sha256": alphabet.source_sha256,
        "letters": LETTERS,
        "encoding": ENCODING,
        "n_patterns": len(LETTERS),
        "n_pixels": N_PIXELS,
    }
    _atomic_write(csv_path, "\n".join([header, *body]) + "\n")
    _atomic_write(meta_path, json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    return [csv_path, meta_path]


def prepare(source: Path = ALPHABET_PATH, out_dir: Path = PREPARED_DIR) -> tuple[Alphabet, list[Path]]:
    """Parse the alphabet and write the CSV and its meta; a refused alphabet writes nothing."""
    alphabet = load_alphabet(source)
    return alphabet, write_prepared(alphabet, out_dir, source)
