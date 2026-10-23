"""Tests of the 5x5 alphabet converter (HOP-02, D-01, D-02) on a synthetic alphabet.

The synthetic alphabet is random noise with the J of the statement in row 9. It is not a letter
set: no network code runs on it and it says nothing about the real alphabet of plan 04-03.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

import letters

TP_DIR = Path(__file__).resolve().parent.parent.parent
CLI = TP_DIR / "scripts" / "prepare_letters.py"
ALL_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# The J of the statement (docs/Archivo SIATP 42026.pdf, section 2.2), hard-coded.
STATEMENT_J_ROWS = ("*****", "...*.", "...*.", "*..*.", "***..")
STATEMENT_J = np.array(
    [
        [1, 1, 1, 1, 1],
        [-1, -1, -1, 1, -1],
        [-1, -1, -1, 1, -1],
        [1, -1, -1, 1, -1],
        [1, 1, 1, -1, -1],
    ],
    dtype=np.int64,
)


def synthetic_patterns() -> np.ndarray:
    patterns = np.random.default_rng(25).choice([-1, 1], size=(26, 25))
    patterns[9] = STATEMENT_J.reshape(-1)
    return patterns


def _block(label: str, pattern) -> list[str]:
    chars = ["*" if value == 1 else "." for value in pattern]
    return [label] + ["".join(chars[5 * r : 5 * r + 5]) for r in range(5)]


def synthetic_text() -> str:
    patterns = synthetic_patterns()
    blocks = ["\n".join(_block(label, patterns[k])) for k, label in enumerate(ALL_LETTERS)]
    return "\n\n".join(blocks) + "\n"


def write_text(tmp_path: Path, text: str, name: str = "alphabet.txt") -> Path:
    path = tmp_path / name
    path.write_bytes(text.encode("utf-8"))
    return path


def edited(transform) -> str:
    """Apply transform to the list of lines of the synthetic text; return the new text."""
    lines = synthetic_text().split("\n")
    transform(lines)
    return "\n".join(lines)


def line_of(label: str) -> int:
    """0-based index of the label line of a letter in the synthetic text."""
    return synthetic_text().split("\n").index(label)


def test_synthetic_parses():
    alphabet = letters.parse_alphabet(synthetic_text())
    assert "".join(alphabet.letters) == ALL_LETTERS
    assert alphabet.patterns.shape == (26, 25)
    assert alphabet.patterns.dtype == np.int64
    assert set(np.unique(alphabet.patterns)) <= {-1, 1}
    assert np.array_equal(alphabet.patterns[9], STATEMENT_J.reshape(-1))


def test_j_matches_statement():
    encoded = letters.encode(STATEMENT_J_ROWS).reshape(5, 5)
    assert np.array_equal(encoded, STATEMENT_J)
    assert tuple(letters.render(encoded)) == STATEMENT_J_ROWS


def test_render_roundtrip():
    alphabet = letters.parse_alphabet(synthetic_text())
    blocks = synthetic_text().strip("\n").split("\n\n")
    for k, block in enumerate(blocks):
        assert letters.render(alphabet.patterns[k]) == block.split("\n")[1:]
        assert np.array_equal(letters.encode(block.split("\n")[1:]), alphabet.patterns[k])


def test_synthetic_alphabet_has_no_identical_or_inverse_pairs():
    patterns = letters.parse_alphabet(synthetic_text()).patterns
    gram = patterns @ patterns.T
    off_diagonal = gram[~np.eye(26, dtype=bool)]
    assert not np.any(off_diagonal == 25)
    assert not np.any(off_diagonal == -25)


def test_prepare_writes_csv_and_meta(tmp_path):
    source = write_text(tmp_path, synthetic_text())
    alphabet, paths = letters.prepare(source, tmp_path / "out")
    csv_path, meta_path = paths
    lines = csv_path.read_text().split("\n")
    assert lines[-1] == ""
    lines = lines[:-1]
    assert lines[0] == ",".join(f"p{k}" for k in range(25))
    assert len(lines) == 27
    for k in range(26):
        assert [int(v) for v in lines[k + 1].split(",")] == list(alphabet.patterns[k])
    assert lines[10] == ",".join(str(int(v)) for v in STATEMENT_J.reshape(-1))
    meta = json.loads(meta_path.read_text())
    assert meta["letters"] == ALL_LETTERS
    assert meta["n_pixels"] == 25
    assert meta["n_patterns"] == 26
    assert meta["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()


def test_prepare_is_deterministic(tmp_path):
    source = write_text(tmp_path, synthetic_text())
    first = letters.prepare(source, tmp_path / "one")[1]
    second = letters.prepare(source, tmp_path / "two")[1]
    for a, b in zip(first, second):
        assert a.read_bytes() == b.read_bytes()


def test_missing_alphabet_is_reported(tmp_path):
    with pytest.raises(letters.LettersError, match="not found"):
        letters.load_alphabet(tmp_path / "absent.txt")


def test_cli_prepares_synthetic_alphabet(tmp_path):
    source = write_text(tmp_path, synthetic_text())
    result = subprocess.run(
        [sys.executable, str(CLI), "--source", str(source), "--out-dir", str(tmp_path / "cli")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert sum(1 for line in result.stdout.splitlines() if line.startswith("wrote ")) == 2
    expected = letters.prepare(source, tmp_path / "lib")[1][0]
    assert (tmp_path / "cli" / "alphabet_pm1.csv").read_bytes() == expected.read_bytes()


def _drop_last_block(lines):
    index = line_of("Z")
    del lines[index - 1 : index + 6]  # empty separator + Z block


def _swap_b_c(lines):
    b, c = line_of("B"), line_of("C")
    lines[b], lines[c] = "C", "B"


def _lowercase_a(lines):
    lines[line_of("A")] = "a"


def _four_rows(lines):
    del lines[line_of("Q") + 5]


def _six_chars(lines):
    lines[line_of("K") + 2] += "*"


def _bad_char(lines):
    row = lines[line_of("M") + 3]
    lines[line_of("M") + 3] = "x" + row[1:]


def _trailing_space(lines):
    lines[line_of("D") + 1] += " "


def _e_equals_f(lines):
    e, f = line_of("E"), line_of("F")
    lines[f + 1 : f + 6] = lines[e + 1 : e + 6]


def _o_negates_a(lines):
    a, o = line_of("A"), line_of("O")
    for r in range(1, 6):
        lines[o + r] = "".join("." if c == "*" else "*" for c in lines[a + r])


def _double_empty(lines):
    lines.insert(line_of("H") - 1, "")


@pytest.mark.parametrize(
    ("transform", "patterns"),
    [
        (_drop_last_block, ["26"]),
        (_swap_b_c, ["letter B", "line "]),
        (_lowercase_a, ["letter A", "line "]),
        (_four_rows, ["letter Q", "5 rows", "line "]),
        (_six_chars, ["letter K", "5 characters", "line "]),
        (_bad_char, ["letter M", "'x'", "line "]),
        (_trailing_space, ["letter D", "' '", "line "]),
        (_e_equals_f, ["identical", "E", "F"]),
        (_o_negates_a, ["inverse", "A", "O"]),
        (_double_empty, ["empty line", "line "]),
    ],
)
def test_refuses_malformed(tmp_path, transform, patterns):
    path = write_text(tmp_path, edited(transform))
    with pytest.raises(letters.LettersError) as info:
        letters.load_alphabet(path)
    for pattern in patterns:
        assert pattern in str(info.value)


def test_cli_show_prints_glyphs(tmp_path):
    source = write_text(tmp_path, synthetic_text())
    out = tmp_path / "out"
    result = subprocess.run(
        [sys.executable, str(CLI), "--show", "--source", str(source), "--out-dir", str(out)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    start = lines.index("J")
    assert lines[start + 1 : start + 6] == list(STATEMENT_J_ROWS)
    assert sum(1 for line in lines if line.startswith("wrote ")) == 2


def test_cli_refuses_bad_alphabet(tmp_path):
    source = write_text(tmp_path, edited(_four_rows))
    out = tmp_path / "out"
    result = subprocess.run(
        [sys.executable, str(CLI), "--source", str(source), "--out-dir", str(out)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "letters:" in result.stderr
    assert not out.exists() or not any(out.iterdir())


# ---------------------------------------------------------------------------------------------
# The real alphabet (plan 04-03): bitmap checks only, no network quantity.
# ---------------------------------------------------------------------------------------------


def test_real_alphabet_letters_in_order():
    alphabet = letters.load_alphabet()
    assert "".join(alphabet.letters) == ALL_LETTERS
    assert alphabet.patterns.shape == (26, 25)
    assert set(np.unique(alphabet.patterns)) <= {-1, 1}


def test_real_alphabet_j_matches_statement():
    alphabet = letters.load_alphabet()
    j_row = alphabet.patterns[ALL_LETTERS.index("J")]
    assert np.array_equal(j_row.reshape(5, 5), STATEMENT_J)


def test_real_alphabet_has_no_identical_or_inverse_pairs():
    patterns = letters.load_alphabet().patterns
    gram = patterns @ patterns.T
    off_diagonal = gram[~np.eye(26, dtype=bool)]
    assert not np.any(off_diagonal == 25)
    assert not np.any(off_diagonal == -25)
