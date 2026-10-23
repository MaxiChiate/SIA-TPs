#!/usr/bin/env python3
"""The pre-registered rule of deliverables/04-hopfield-letras.md section 3 as code (HOP-02, HOP-03, D-03..D-06).

The rule is written in Spanish in that file between the markers `<!-- regla:inicio -->` and
`<!-- regla:fin -->`. This module is its executable twin: the design constants, the integer selection of the
two 4-letter sets, the capacity extension rule, the spurious-example pick and the guard repeat the numbers of
that text. The text, this file, datos/letters/alphabet_5x5.txt and scripts/letters.py are committed together by
the user before the network runs on the letters (D-04, D-04b: once it runs, none of them changes).

The selection depends only on the bitmaps (D-03): everything computed here is an integer dot product between
letters. This module never computes a network quantity (Hebb weights, fields, energies, fixed points, recall,
capacity); `report` prints bitmap facts only.

    .venv/bin/python analysis/hopfield_select.py report
    .venv/bin/python analysis/hopfield_select.py identity
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

TP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TP_DIR / "scripts"))
sys.path.insert(0, str(TP_DIR / "analysis"))

import letters  # noqa: E402
import som_select  # noqa: E402

RULE_FILE = "deliverables/04-hopfield-letras.md"
SELECT_FILE = "analysis/hopfield_select.py"  # this module: guarded and hashed together with the rule text (D-04)
ALPHABET_FILE = "datos/letters/alphabet_5x5.txt"
LETTERS_FILE = "scripts/letters.py"
HEX40 = re.compile(r"[0-9a-f]{40}")

# ----------------------------------------------------------------------------------------------
# Design constants: the numbers written in the rule (D-03, D-05, D-06, HOP-03)
# ----------------------------------------------------------------------------------------------

SET_SIZE = 4
MAX_SWEEPS = 100
RECALL_LEVELS = tuple(k / 25 for k in range(13))  # k = 0..12 flipped pixels of 25
RECALL_TRIALS = 30
SEEDS = tuple(range(1, 11))
UPDATES = ("async", "sync")
TRACE_TRIALS = 1  # the full trace of the first trial per letter and level

CAPACITY_P = 4  # exhaustive over all C(26, 4) subsets
CAPACITY_LEVEL = 0.12  # k = 3 flipped pixels
CAPACITY_TRIALS = 30
CAPACITY_P_RANGE = (1, 2, 3, 4, 5, 6, 7, 8)
CAPACITY_SAMPLES = 200
CAPACITY_NEAR_ZERO = 0.05  # "stability ~ 0": mean stable fraction over the seeds at most this
CAPACITY_P_LIMIT = 26  # the extension stops at every letter
CAPACITY_REFERENCES = (0.138, 0.15)  # orders of magnitude to mark (x N), never a threshold (Pitfall 26)

SPURIOUS_LEVELS = (0.40, 0.44, 0.48)
SPURIOUS_TRIALS = 100
SPURIOUS_SEEDS = tuple(range(1, 11))
SPURIOUS_UPDATE = "async"
CLASS_NAMES = ("stored", "inverse", "mixture", "other")


# ----------------------------------------------------------------------------------------------
# Integer selection of the two sets (D-03, D-04b): bitmaps only
# ----------------------------------------------------------------------------------------------


def pair_dots(patterns) -> np.ndarray:
    """Exact integer dot products d_ab = xi^a . xi^b (int64, symmetric, diagonal N)."""
    matrix = np.asarray(patterns, dtype=np.int64)
    return matrix @ matrix.T


def set_key(dots, combo) -> tuple[int, int]:
    """(max over the pairs of |d|, sum over the pairs of |d|) of a subset, as Python ints."""
    values = [abs(int(dots[a, b])) for a, b in itertools.combinations(combo, 2)]
    return max(values), sum(values)


def select_sets(patterns) -> dict:
    """The separated and the correlated set over every subset of SET_SIZE letters (lexicographic order).

    separated:  minimise max |d|, then sum |d|, then the smallest index tuple.
    correlated: maximise max |d|, then sum |d|, then the smallest index tuple (the mirror of the separated
    rule, fixed by principle, D-04b). There is no tie-break parameter.
    """
    dots = pair_dots(patterns)
    scored = [(combo, *set_key(dots, combo)) for combo in itertools.combinations(range(len(dots)), SET_SIZE)]
    separated = min(scored, key=lambda item: (item[1], item[2], item[0]))
    correlated = min(scored, key=lambda item: (-item[1], -item[2], item[0]))
    separated_key = (separated[1], separated[2])
    correlated_key = (correlated[1], correlated[2])
    separated_tied = [item[0] for item in scored if (item[1], item[2]) == separated_key]
    correlated_tied = [item[0] for item in scored if (item[1], item[2]) == correlated_key]
    return {
        "separated": separated[0],
        "correlated": correlated[0],
        "separated_key": separated_key,
        "correlated_key": correlated_key,
        "ties_separated": len(separated_tied),
        "ties_correlated_max": sum(1 for item in scored if item[1] == correlated_key[0]),
        "ties_correlated_key": len(correlated_tied),
        "separated_tied": separated_tied,
        "correlated_tied": correlated_tied,
    }


def max_abs_histogram(patterns, size: int = SET_SIZE) -> dict:
    """{max |d| -> number of subsets of `size` letters}, keys sorted (D-06)."""
    dots = pair_dots(patterns)
    counts: dict[int, int] = {}
    for combo in itertools.combinations(range(len(dots)), size):
        peak = set_key(dots, combo)[0]
        counts[peak] = counts.get(peak, 0) + 1
    return dict(sorted(counts.items()))


# ----------------------------------------------------------------------------------------------
# Capacity extension and spurious pick, written before the runs (D-05, HOP-03)
# ----------------------------------------------------------------------------------------------


def capacity_needs_next_p(p, mean_stable_fraction, near_zero=CAPACITY_NEAR_ZERO, p_limit=CAPACITY_P_LIMIT) -> bool:
    """True iff the next p must run: p below the limit and the mean stable fraction over the seeds at p is
    still above `near_zero`. Called from the last p of CAPACITY_P_RANGE on, one p at a time (D-05)."""
    return p < p_limit and mean_stable_fraction > near_zero


def _as_int(value) -> int:
    return int(float(value))


def pick_spurious(rows) -> dict:
    """For each class code 1 (inverse), 2 (mixture), 3 (other): the converged row with the lowest trial.

    `rows` are the dicts of trials.csv in file order with at least trial, class and converged. A class with no
    converged row is omitted. A non-converged trial is never an example (HOP-03).
    """
    picked: dict = {}
    for row in rows:
        code = _as_int(row["class"])
        if code not in (1, 2, 3) or _as_int(row["converged"]) != 1:
            continue
        if code not in picked or _as_int(row["trial"]) < _as_int(picked[code]["trial"]):
            picked[code] = row
    return picked


def spurious_needs_next_seed(rows) -> bool:
    """True unless some converged trial ended in a mixture (2) or in another state (3)."""
    return not any(_as_int(row["converged"]) == 1 and _as_int(row["class"]) in (2, 3) for row in rows)


# ----------------------------------------------------------------------------------------------
# Report: bitmap facts only
# ----------------------------------------------------------------------------------------------


def _word(alphabet, combo) -> str:
    return "".join(alphabet.letters[i] for i in combo)


def _set_lines(alphabet, dots, name, combo, key, extra) -> list[str]:
    lines = [f"{name} set: {_word(alphabet, combo)}  indices {list(combo)}  max |d| = {key[0]}  sum |d| = {key[1]}"]
    lines += [f"  {extra}"]
    for a, b in itertools.combinations(combo, 2):
        d = int(dots[a, b])
        lines.append(f"  {alphabet.letters[a]}{alphabet.letters[b]}: d = {d:+d}  overlap = {d / 25:+.2f}")
    return lines


def report(alphabet) -> str:
    """Text lines: sha256, the dot-product table, both sets, the max |d| histogram and the set glyphs."""
    patterns = alphabet.patterns
    dots = pair_dots(patterns)
    chosen = select_sets(patterns)
    labels = alphabet.letters
    lines = [f"alphabet sha256: {alphabet.source_sha256}", "", "integer dot products d_ab (26 x 26):"]
    lines.append("    " + " ".join(f"{label:>3}" for label in labels))
    for i, label in enumerate(labels):
        lines.append(f"{label:>3} " + " ".join(f"{int(dots[i, j]):>3d}" for j in range(len(labels))))
    lines.append("")

    sep, cor = chosen["separated"], chosen["correlated"]
    lines += _set_lines(alphabet, dots, "separated", sep, chosen["separated_key"],
                        f"subsets sharing this (max, sum): {chosen['ties_separated']}")
    if chosen["ties_separated"] > 1 and chosen["ties_separated"] <= 10:
        lines.append("  sharing it: " + ", ".join(_word(alphabet, c) for c in chosen["separated_tied"]))
    lines.append("")
    extra = (f"subsets sharing this max: {chosen['ties_correlated_max']}; "
             f"sharing this (max, sum): {chosen['ties_correlated_key']}")
    lines += _set_lines(alphabet, dots, "correlated", cor, chosen["correlated_key"], extra)
    if chosen["ties_correlated_key"] <= 10:
        lines.append("  sharing it: " + ", ".join(_word(alphabet, c) for c in chosen["correlated_tied"]))
    lines.append("")

    histogram = max_abs_histogram(patterns)
    total = sum(histogram.values())
    lines.append(f"max |d| histogram over the {total} subsets of {SET_SIZE} letters:")
    for peak, count in histogram.items():
        lines.append(f"  max |d| = {peak:>2}: {count}")
    lines.append("")

    for name, combo in (("separated", sep), ("correlated", cor)):
        lines.append(f"glyphs of the {name} set {_word(alphabet, combo)}:")
        glyphs = [[labels[i]] + letters.render(patterns[i]) for i in combo]
        for row in range(len(glyphs[0])):
            lines.append("  " + "   ".join(f"{glyph[row]:<5}" for glyph in glyphs).rstrip())
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


# ----------------------------------------------------------------------------------------------
# "Committed before looking": the guard (D-04)
# ----------------------------------------------------------------------------------------------


def _git_stdout(args: list[str], repo_dir: Path) -> str:
    """Argument list, no shell, run in repo_dir (T-04-09)."""
    return subprocess.run(["git", *args], cwd=repo_dir, capture_output=True, text=True,
                          check=True).stdout.strip()


def _added_commit(path: str, repo_dir: Path) -> str:
    """The one commit that added `path` (git log --diff-filter=A). Never added, or added more than once, is
    refused: the rule commit must be unambiguous."""
    out = _git_stdout(["log", "--diff-filter=A", "--format=%H", "--", path], repo_dir)
    if not HEX40.fullmatch(out):
        raise SystemExit(f"{path}: expected exactly one commit that added it, git reports {out!r} (D-04)")
    return out


def _is_ancestor(older: str, newer: str, repo_dir: Path) -> bool:
    result = subprocess.run(["git", "merge-base", "--is-ancestor", older, newer], cwd=repo_dir,
                            capture_output=True, text=True)
    return result.returncode == 0


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rule_identity(repo_dir=TP_DIR) -> dict:
    """Refuse unless the rule text and the selection code were added in one commit, the alphabet and
    scripts/letters.py in that commit or an ancestor, nothing guarded changed after it, the three data and
    code files have no uncommitted change and the text between the markers equals the one at the rule commit.
    Returns the identity to record. Every refusal is a SystemExit ending in "(D-04)"."""
    repo_dir = Path(repo_dir).resolve()
    guarded = [SELECT_FILE, ALPHABET_FILE, LETTERS_FILE]
    try:
        som_select.rule_guard(guarded, repo_dir)
    except SystemExit as error:
        raise SystemExit(f"{error}; Phase 4: the selection code, the alphabet and scripts/letters.py must be "
                         "committed with the rule and unchanged (D-04)") from None

    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", "--", RULE_FILE], cwd=repo_dir,
                             capture_output=True, text=True)
    if tracked.returncode != 0:
        raise SystemExit(f"{RULE_FILE}: the rule text must be committed (D-04)")

    rule_commit = _added_commit(RULE_FILE, repo_dir)
    select_added = _added_commit(SELECT_FILE, repo_dir)
    if select_added != rule_commit:
        raise SystemExit(f"{SELECT_FILE} was added in commit {select_added}, not in the rule commit {rule_commit} "
                         f"that added {RULE_FILE} (D-04)")
    for path in (ALPHABET_FILE, LETTERS_FILE):
        added = _added_commit(path, repo_dir)
        if not _is_ancestor(added, rule_commit, repo_dir):
            raise SystemExit(f"{path} was added in commit {added}, which is not the rule commit {rule_commit} "
                             "or an ancestor of it (D-04)")
    for path in (SELECT_FILE, ALPHABET_FILE, LETTERS_FILE):
        last = _git_stdout(["log", "-1", "--format=%H", "--", path], repo_dir)
        if not HEX40.fullmatch(last) or not _is_ancestor(last, rule_commit, repo_dir):
            raise SystemExit(f"{path} changed in commit {last} after the rule commit {rule_commit} (D-04)")

    with tempfile.TemporaryDirectory() as folder:
        committed = Path(folder) / "rule.md"
        text = subprocess.run(["git", "show", f"{rule_commit}:./{RULE_FILE}"], cwd=repo_dir,
                              capture_output=True, check=True).stdout
        committed.write_bytes(text)
        committed_digest = som_select.rule_digest(committed)
    current_digest = som_select.rule_digest(repo_dir / RULE_FILE)
    if committed_digest != current_digest:
        raise SystemExit(f"the text between the markers of {RULE_FILE} differs from the one at the rule commit "
                         f"{rule_commit} (D-04)")
    return {
        "rule_commit": rule_commit,
        "rule_sha256": current_digest,
        "select_sha256": _sha256_file(repo_dir / SELECT_FILE),
        "alphabet_sha256": _sha256_file(repo_dir / ALPHABET_FILE),
        "letters_sha256": _sha256_file(repo_dir / LETTERS_FILE),
    }


def require_same_rule(selection_path, repo_dir=TP_DIR) -> None:
    """Later steps run only on the rule, code and alphabet that selection.json recorded (D-04)."""
    selection_path = Path(selection_path)
    repo_dir = Path(repo_dir)
    try:
        recorded = json.loads(selection_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise SystemExit(f"{selection_path}: cannot read the recorded identity (run make hopfield-letters first): "
                         f"{error} (D-04)")
    current = {
        "rule_sha256": som_select.rule_digest(repo_dir / RULE_FILE),
        "select_sha256": _sha256_file(repo_dir / SELECT_FILE),
        "alphabet_sha256": _sha256_file(repo_dir / ALPHABET_FILE),
        "letters_sha256": _sha256_file(repo_dir / LETTERS_FILE),
    }
    names = {"rule_sha256": "the rule text", "select_sha256": SELECT_FILE,
             "alphabet_sha256": ALPHABET_FILE, "letters_sha256": LETTERS_FILE}
    for key, value in current.items():
        if recorded.get(key) != value:
            raise SystemExit(f"{names[key]} changed since the identity was recorded: "
                             f"{recorded.get(key)} != {value} (D-04)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("report", help="bitmap facts: dot products, both sets, histogram (no network quantity)")
    commands.add_parser("identity", help="print the rule identity, refusing unless the rule commit exists")
    args = parser.parse_args(argv)
    if args.command == "report":
        try:
            alphabet = letters.load_alphabet()
        except letters.LettersError as error:
            raise SystemExit(f"letters: {error}")
        sys.stdout.write(report(alphabet))
    else:
        print(json.dumps(rule_identity(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
