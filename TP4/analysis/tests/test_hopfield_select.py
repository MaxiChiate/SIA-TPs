"""Tests of the pre-registered letter rule as code (HOP-02, HOP-03, D-03..D-06, D-04b).

Selection is tested on a synthetic six-pattern alphabet with exact ties and, on the real alphabet, only
against a pure-Python brute force over bitmaps. The guard is tested in temporary git repositories. No network
quantity is computed anywhere here.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

import hopfield_select as h
import letters
import som_select

TP_DIR = Path(__file__).resolve().parent.parent.parent
SCRIPT = TP_DIR / "analysis" / "hopfield_select.py"
HEX40 = re.compile(r"[0-9a-f]{40}")
RULE_TEXT = "# Fase 4\n<!-- regla:inicio -->\nla regla\n<!-- regla:fin -->\n"

SYN = np.array(
    [
        [-1, -1, -1, 1, 1, 1, -1, -1, 1],
        [-1, 1, 1, 1, 1, -1, 1, 1, -1],
        [1, 1, 1, -1, -1, -1, -1, 1, -1],
        [1, -1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, -1, 1, -1, -1, 1, -1],
        [1, 1, -1, 1, -1, 1, 1, 1, 1],
    ],
    dtype=np.int64,
)
SYN_DOTS = {(0, 1): -3, (0, 2): -7, (0, 3): 1, (0, 4): -5, (0, 5): -1, (1, 2): 1, (1, 3): 1, (1, 4): 3,
            (1, 5): -1, (2, 3): -3, (2, 4): 7, (2, 5): -1, (3, 4): -1, (3, 5): 3, (4, 5): -3}


def brute_force(patterns):
    """Plain-int selection, independent of the module: returns (separated, correlated)."""
    rows = [[int(v) for v in row] for row in patterns]
    best_sep = best_cor = None
    for combo in itertools.combinations(range(len(rows)), 4):
        values = [abs(sum(x * y for x, y in zip(rows[a], rows[b]))) for a, b in itertools.combinations(combo, 2)]
        sep = (max(values), sum(values), combo)
        cor = (-max(values), -sum(values), combo)
        best_sep = sep if best_sep is None or sep < best_sep else best_sep
        best_cor = cor if best_cor is None or cor < best_cor else best_cor
    return best_sep[2], best_cor[2]


def test_pair_dots_are_exact_integers():
    dots = h.pair_dots(SYN)
    assert dots.dtype == np.int64
    assert np.array_equal(dots, dots.T)
    assert np.all(np.diag(dots) == 9)
    for (a, b), value in SYN_DOTS.items():
        assert dots[a, b] == value


def test_set_key_is_a_pair_of_ints():
    key = h.set_key(h.pair_dots(SYN), (0, 1, 3, 5))
    assert key == (3, 10)
    assert all(type(v) is int for v in key)


def test_separated_breaks_ties_by_sum_then_tuple():
    dots = h.pair_dots(SYN)
    assert h.select_sets(SYN)["separated"] == (0, 1, 3, 5)
    assert h.set_key(dots, (0, 1, 3, 5)) == (3, 10)
    assert h.set_key(dots, (1, 2, 3, 5)) == (3, 10)
    assert h.select_sets(SYN)["ties_separated"] == 2
    # another max-3 set has a larger sum, so the sum decides somewhere
    others = [c for c in itertools.combinations(range(6), 4)
              if h.set_key(dots, c)[0] == 3 and h.set_key(dots, c) != (3, 10)]
    assert others and all(h.set_key(dots, c)[1] > 10 for c in others)


def test_correlated_breaks_ties_by_higher_sum():
    chosen = h.select_sets(SYN)
    assert chosen["correlated"] == (0, 1, 2, 4)
    assert chosen["correlated_key"] == (7, 26)
    assert chosen["ties_correlated_max"] == 9
    assert chosen["ties_correlated_key"] == 1
    assert chosen["correlated"] != (0, 1, 2, 5)  # the lowest sum among the nine (D-04b)
    assert h.set_key(h.pair_dots(SYN), (0, 1, 2, 5))[1] == 14


def test_max_abs_histogram_syn():
    assert h.max_abs_histogram(SYN) == {3: 3, 5: 3, 7: 9}


def test_selection_matches_brute_force():
    patterns = letters.load_alphabet().patterns
    chosen = h.select_sets(patterns)
    separated, correlated = brute_force(patterns)
    assert chosen["separated"] == separated
    assert chosen["correlated"] == correlated


def test_real_alphabet_histogram():
    patterns = letters.load_alphabet().patterns
    histogram = h.max_abs_histogram(patterns)
    assert sum(histogram.values()) == 14950
    assert all(key % 2 == 1 and key <= 23 for key in histogram)
    rows = [[int(v) for v in row] for row in patterns]
    brute: dict[int, int] = {}
    for combo in itertools.combinations(range(26), 4):
        peak = max(abs(sum(x * y for x, y in zip(rows[a], rows[b]))) for a, b in itertools.combinations(combo, 2))
        brute[peak] = brute.get(peak, 0) + 1
    assert histogram == dict(sorted(brute.items()))


def test_design_constants():
    assert len(h.RECALL_LEVELS) == 13
    assert all(round(level * 25) == k for k, level in enumerate(h.RECALL_LEVELS))
    assert h.SEEDS == tuple(range(1, 11))
    assert h.CAPACITY_P_RANGE == tuple(range(1, 9))
    assert h.CAPACITY_NEAR_ZERO == 0.05
    assert h.CAPACITY_P_LIMIT == 26
    assert h.SPURIOUS_LEVELS == (0.40, 0.44, 0.48)
    assert h.MAX_SWEEPS == 100
    assert h.SET_SIZE == 4 and h.CAPACITY_P == 4 and h.CAPACITY_LEVEL == 0.12
    assert h.CLASS_NAMES == ("stored", "inverse", "mixture", "other")


def test_capacity_needs_next_p():
    assert h.capacity_needs_next_p(8, 0.06) is True
    assert h.capacity_needs_next_p(8, 0.05) is False
    assert h.capacity_needs_next_p(9, 0.30) is True
    assert h.capacity_needs_next_p(26, 0.50) is False
    assert all(h.capacity_needs_next_p(p, f, near_zero=1.0) is False for p in (1, 8, 25) for f in (0.0, 0.5, 1.0))
    assert h.capacity_needs_next_p(5, 0.9, p_limit=5) is False
    assert h.capacity_needs_next_p(4, 0.9, p_limit=5) is True


def row(trial, cls, converged):
    return {"trial": trial, "class": cls, "converged": converged}


def test_pick_spurious_first_converged_in_file_order():
    rows = [row(0, 0, 1), row(1, 2, 0), row(2, 3, 1), row(3, 2, 1), row(4, 1, 1), row(5, 2, 1), row(6, 3, 1),
            row(7, 1, 0)]
    picked = h.pick_spurious(rows)
    assert {code: r["trial"] for code, r in picked.items()} == {1: 4, 2: 3, 3: 2}
    assert h.pick_spurious([row(0, 0, 1), row(1, 2, 0)]) == {}
    only_inverse = h.pick_spurious([row(3, 1, 1), row(1, 1, 1)])
    assert list(only_inverse) == [1] and only_inverse[1]["trial"] == 1  # lowest trial index
    csv_like = h.pick_spurious([{"trial": "5", "class": "2", "converged": "1"}])
    assert csv_like[2]["trial"] == "5"


def test_spurious_needs_next_seed():
    assert h.spurious_needs_next_seed([row(0, 0, 1), row(1, 1, 1)]) is True
    assert h.spurious_needs_next_seed([row(0, 2, 0), row(1, 3, 0)]) is True
    assert h.spurious_needs_next_seed([]) is True
    assert h.spurious_needs_next_seed([row(0, 1, 1), row(1, 2, 1)]) is False
    assert h.spurious_needs_next_seed([row(0, 3, 1)]) is False


def test_report_is_bitmap_only():
    result = subprocess.run([sys.executable, str(SCRIPT), "report"], capture_output=True, text=True, cwd=TP_DIR)
    assert result.returncode == 0, result.stderr
    out = result.stdout
    alphabet = letters.load_alphabet()
    chosen = h.select_sets(alphabet.patterns)
    for key in ("separated", "correlated"):
        word = "".join(alphabet.letters[i] for i in chosen[key])
        assert word in out
    assert "integer dot products" in out
    assert len([line for line in out.splitlines() if re.match(r"^ *[A-Z] +-?\d", line)]) == 26
    assert alphabet.source_sha256 in out
    for banned in ("energy", "stable", "fixed", "margin", "recall", "capacity"):
        assert banned not in out.lower()


# ---------- guard, in temporary repositories ----------


def git(repo, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
                           *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


FILES = {
    h.SELECT_FILE: "SET_SIZE = 4\n",
    h.ALPHABET_FILE: "A\n*****\n",
    h.LETTERS_FILE: "SIDE = 5\n",
    h.RULE_FILE: RULE_TEXT,
}


def make_repo(path, first, second=None):
    path.mkdir(parents=True)
    git(path, "init", "-q")
    hashes = []
    for group in (first, second):
        if group is None:
            continue
        for rel, text in group.items():
            (path / rel).parent.mkdir(parents=True, exist_ok=True)
            (path / rel).write_text(text)
            git(path, "add", rel)
        git(path, "commit", "-q", "-m", "c")
        hashes.append(git(path, "rev-parse", "HEAD"))
    return hashes


def refused(repo):
    with pytest.raises(SystemExit) as caught:
        h.rule_identity(repo_dir=repo)
    assert str(caught.value).endswith("(D-04)")
    return str(caught.value)


def test_identity_after_rule_commit(tmp_path):
    repo = tmp_path / "repo"
    (c1,) = make_repo(repo, FILES)
    ident = h.rule_identity(repo_dir=repo)
    assert ident["rule_commit"] == c1 and HEX40.fullmatch(ident["rule_commit"])
    assert ident["rule_sha256"] == som_select.rule_digest(repo / h.RULE_FILE)
    for key, rel in (("select_sha256", h.SELECT_FILE), ("alphabet_sha256", h.ALPHABET_FILE),
                     ("letters_sha256", h.LETTERS_FILE)):
        assert ident[key] == hashlib.sha256((repo / rel).read_bytes()).hexdigest()


def test_identity_allows_alphabet_in_an_earlier_commit(tmp_path):
    repo = tmp_path / "repo"
    early = {h.ALPHABET_FILE: FILES[h.ALPHABET_FILE], h.LETTERS_FILE: FILES[h.LETTERS_FILE]}
    late = {h.SELECT_FILE: FILES[h.SELECT_FILE], h.RULE_FILE: RULE_TEXT}
    _, c2 = make_repo(repo, early, late)
    assert h.rule_identity(repo_dir=repo)["rule_commit"] == c2


def test_identity_allows_prose_outside_markers(tmp_path):
    repo = tmp_path / "repo"
    make_repo(repo, FILES)
    with (repo / h.RULE_FILE).open("a") as file:
        file.write("## 4. Resultados\nmas texto\n")
    assert h.rule_identity(repo_dir=repo)["rule_sha256"] == som_select.rule_digest(repo / h.RULE_FILE)


def test_identity_refuses_uncommitted_rule_change(tmp_path):
    repo = tmp_path / "repo"
    make_repo(repo, FILES)
    (repo / h.RULE_FILE).write_text(RULE_TEXT.replace("la regla", "otra regla"))
    assert "differs" in refused(repo)


def test_identity_refuses_committed_rule_change(tmp_path):
    repo = tmp_path / "repo"
    make_repo(repo, FILES)
    (repo / h.RULE_FILE).write_text(RULE_TEXT.replace("la regla", "otra regla"))
    git(repo, "add", h.RULE_FILE)
    git(repo, "commit", "-q", "-m", "edit the rule")
    assert "differs" in refused(repo)


@pytest.mark.parametrize("rel", [h.SELECT_FILE, h.ALPHABET_FILE, h.LETTERS_FILE])
def test_identity_refuses_dirty_file(tmp_path, rel):
    repo = tmp_path / "repo"
    make_repo(repo, FILES)
    with (repo / rel).open("a") as file:
        file.write("# changed\n")
    assert rel in refused(repo)


def test_identity_refuses_later_commit_on_code(tmp_path):
    repo = tmp_path / "repo"
    make_repo(repo, FILES)
    (repo / h.SELECT_FILE).write_text("SET_SIZE = 5\n")
    git(repo, "add", h.SELECT_FILE)
    git(repo, "commit", "-q", "-m", "edit the code")
    assert "after the rule commit" in refused(repo)


def test_identity_refuses_select_added_later(tmp_path):
    repo = tmp_path / "repo"
    first = {k: v for k, v in FILES.items() if k != h.SELECT_FILE}
    make_repo(repo, first, {h.SELECT_FILE: FILES[h.SELECT_FILE]})
    assert "not in the rule commit" in refused(repo)


def test_identity_refuses_untracked(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    for rel, text in FILES.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text)
    refused(repo)


def test_require_same_rule(tmp_path):
    repo = tmp_path / "repo"
    make_repo(repo, FILES)
    selection = tmp_path / "selection.json"
    selection.write_text(json.dumps(h.rule_identity(repo_dir=repo)))
    h.require_same_rule(selection, repo_dir=repo)

    for rel, key in ((h.ALPHABET_FILE, "alphabet"), (h.SELECT_FILE, h.SELECT_FILE), (h.LETTERS_FILE, h.LETTERS_FILE)):
        original = (repo / rel).read_bytes()
        (repo / rel).write_bytes(original + b"# x\n")
        with pytest.raises(SystemExit) as caught:
            h.require_same_rule(selection, repo_dir=repo)
        assert key in str(caught.value) and str(caught.value).endswith("(D-04)")
        (repo / rel).write_bytes(original)
    (repo / h.RULE_FILE).write_text(RULE_TEXT.replace("la regla", "otra"))
    with pytest.raises(SystemExit) as caught:
        h.require_same_rule(selection, repo_dir=repo)
    assert "rule text" in str(caught.value)
    with pytest.raises(SystemExit) as caught:
        h.require_same_rule(tmp_path / "missing.json", repo_dir=repo)
    assert "make hopfield-letters" in str(caught.value)
