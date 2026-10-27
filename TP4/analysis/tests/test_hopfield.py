"""Cross-check of the C Hopfield outputs against the numpy recomputation, on the synthetic fixture only (D-04).

Nothing here reads datos/letters/ or datos/prepared/alphabet_pm1.csv: the six-pattern fixture of plan 04-01 stands
in until the user's rule commit.
"""

from __future__ import annotations

import filecmp
import os
import shutil
from pathlib import Path

import numpy as np
import pytest

import hopfield
import som
import sweep
from hopfield import HopfieldCheckError

FIXTURE = Path(__file__).resolve().parent.parent.parent / "neuron" / "tests" / "fixtures" / "patterns_mix.csv"

BASE = {
    "model": "hopfield",
    "seed": 3,
    "rule": "hebb",
    "update": "async",
    "max_sweeps": 100,
    "trials": 4,
}
RECALL = {
    "task": "recall",
    "noise_levels": [0.0, 0.24, 0.48],
    "subset": [0, 1, 2, 3],
    "trace_trials": 4,
}


@pytest.fixture(scope="module", autouse=True)
def binary():
    sweep.build_binary()


@pytest.fixture(scope="module")
def patterns():
    return hopfield.load_patterns(FIXTURE)


def run_fixture(tmp_path, **keys):
    config = {**BASE, "input": os.path.relpath(FIXTURE, tmp_path), **keys}
    return som.run_binary(config, tmp_path)


def run_recall(tmp_path, **keys):
    return run_fixture(tmp_path, **{**RECALL, **keys})


def run_capacity(tmp_path, **keys):
    return run_fixture(tmp_path, **{"task": "capacity", "noise_levels": [0.12], "trials": 2, **keys})


def copy_run(run_dir, tmp_path):
    target = tmp_path / "tampered"
    shutil.copytree(run_dir, target)
    return target


def rewrite_cell(path, row, column, new_value):
    """Replace one cell of a CSV (row 0-based after the header, column by name)."""
    lines = path.read_text().splitlines()
    header = lines[0].split(",")
    cells = lines[row + 1].split(",")
    cells[header.index(column)] = new_value
    lines[row + 1] = ",".join(cells)
    path.write_text("\n".join(lines) + "\n")


# ---------- capacity ----------

def test_capacity_p4_matches_numpy(tmp_path, patterns):
    run_dir = run_capacity(tmp_path, p=4, n_subsets=0)
    summary = hopfield.check_capacity(run_dir, patterns)
    assert summary["rows"] == 15
    assert abs(summary["mean_stable_fraction"] - 0.9) < 1e-12

    header, table = hopfield.read_table(run_dir / "capacity.csv")
    assert table[:, header.index("n_stable")].tolist() == [4, 2, 4, 3, 4, 2, 4, 4, 3, 4, 4, 4, 4, 4, 4]
    assert table[:, header.index("min_margin")].tolist() == [2, -2, 4, -2, 6, -6, 4, 10, -2, 2, 6, 10, 6, 10, 10]


def test_capacity_detects_tampering(tmp_path, patterns):
    run_dir = run_capacity(tmp_path, p=4, n_subsets=0)
    tampered = copy_run(run_dir, tmp_path)
    rewrite_cell(tampered / "capacity.csv", 3, "n_stable", "4")
    with pytest.raises(HopfieldCheckError, match="n_stable"):
        hopfield.check_capacity(tampered, patterns)


def test_capacity_sampled_matches_numpy(tmp_path, patterns):
    run_dir = run_capacity(tmp_path, p=3, n_subsets=10)
    assert hopfield.check_capacity(run_dir, patterns)["rows"] == 10
    header, table = hopfield.read_table(run_dir / "capacity.csv")
    idx = table[:, 1:4].astype(int)
    assert all(row[0] < row[1] < row[2] for row in idx)
    assert len({tuple(row) for row in idx}) == 10

    tampered = copy_run(run_dir, tmp_path)
    lines = (tampered / "capacity.csv").read_text().splitlines()
    cells = lines[1].split(",")
    lines[2] = ",".join([lines[2].split(",")[0]] + cells[1:])  # row 1 gets the subset of row 0
    (tampered / "capacity.csv").write_text("\n".join(lines) + "\n")
    with pytest.raises(HopfieldCheckError, match="capacity.csv"):
        hopfield.check_capacity(tampered, patterns)


# ---------- the network ----------

COURSE = np.array([[1, 1, -1, -1], [-1, -1, 1, 1]])


def test_course_example():
    W = hopfield.hebb(COURSE)
    assert W[0, 1] == 2 and W[0, 2] == -2  # w12 = 2, w13 = -2 in the course's 1-based numbering
    zeta = np.array([1, -1, -1, -1])
    assert hopfield.energy(W, COURSE[0]) == -12
    assert hopfield.energy(W, zeta) == 0
    assert hopfield.classify(COURSE, COURSE[0]) == (0, (0, -1, -1), (1, 0, 0))
    assert hopfield.is_fixed(W, COURSE[0])
    assert not hopfield.is_fixed(W, zeta)


def test_cross_terms_identity(patterns):
    P = patterns[:4]
    W = hopfield.hebb(P)
    n, p = P.shape[1], P.shape[0]
    aligned = P * (P @ W)
    cross = hopfield.cross_terms(P)
    assert np.array_equal(aligned, n - p + cross)
    margin, wrong = hopfield.margins(W, P)
    assert np.array_equal(margin, (n - p + cross).min(axis=1))
    assert margin.tolist() == [10, 2, 12, 16]
    assert wrong.tolist() == [0, 0, 0, 0]


def test_classify_branches(patterns):
    P = patterns[:4]
    assert hopfield.classify(P, P[2]) == (hopfield.CLASS_STORED, (2, -1, -1), (1, 0, 0))
    assert hopfield.classify(P, -P[0]) == (hopfield.CLASS_INVERSE, (0, -1, -1), (-1, 0, 0))
    mixture = np.where(P[0] + P[2] + P[3] > 0, 1, -1)
    assert hopfield.classify(P, mixture) == (hopfield.CLASS_MIXTURE, (0, 2, 3), (1, 1, 1))
    assert hopfield.classify(P[:2], mixture)[0] == hopfield.CLASS_OTHER
    damaged = P[0].copy()
    damaged[:3] *= -1
    assert hopfield.classify(P, damaged)[0] == hopfield.CLASS_OTHER


def test_is_fixed_tie():
    W = np.array([[0, 1, -1], [1, 0, 1], [-1, 1, 0]])
    s = np.array([-1, 1, 1])
    assert hopfield.fields(W, s).tolist() == [0, 0, 2]  # neuron 0 and 1 sit on an exact tie
    assert hopfield.is_fixed(W, s)
    assert not hopfield.is_fixed(W, np.array([1, -1, 1]))


# ---------- pseudo-inverse (D-06/D-07) ----------

# A small CORRELATED pm-one fixture (not the QR): hebb leaves pattern 0 (wrong=2) and pattern 1 (wrong=1) unstable,
# pattern 2 fixed; pinv (Gram det = 160, invertible) makes all three exact fixed points (planning-time numpy).
CORR_PINV = np.array([
    [1, 1, -1, 1, 1, -1, -1, -1],
    [-1, 1, 1, -1, 1, 1, -1, 1],
    [-1, 1, 1, -1, -1, 1, -1, 1],
])


def test_pinv_fixes_correlated_fixture_hebb_cannot():
    P = CORR_PINV
    Wh = hopfield.hebb(P)
    hebb_wrong = [hopfield.margins(Wh, P)[1][a] for a in range(3)]
    assert any(w > 0 for w in hebb_wrong)  # hebb leaves at least one pattern non-fixed

    Wp = hopfield.pinv(P)
    assert Wp.dtype == np.float64
    assert np.any(np.diag(Wp) != 0)  # the diagonal is left intact (D-07)
    for a in range(3):
        assert hopfield.is_fixed(Wp, P[a])  # every stored pattern is an exact fixed point under pinv


def test_energy_not_truncated_for_fractional_w():
    P = CORR_PINV
    Wp = hopfield.pinv(P)
    s = P[0]
    exact = float(-0.5 * (s.astype(np.float64) @ Wp @ s.astype(np.float64)))
    truncated = float(-0.5 * (s.astype(np.int64) @ Wp.astype(np.int64) @ s.astype(np.int64)))
    got = hopfield.energy(Wp, s)
    assert abs(got - exact) < 1e-9
    assert abs(got - truncated) > 1e-6  # the old int64 cast would have silently truncated Wp's fractional entries


def test_check_recall_pinv_run(tmp_path, patterns):
    run_dir = run_recall(tmp_path, rule="pinv")
    summary = hopfield.check_recall(run_dir, patterns)
    assert summary == {"trials": 48, "traced": 48}
    header, table = hopfield.read_table(run_dir / "stored.csv")
    assert table[:, header.index("fixed")].tolist() == [1, 1, 1, 1]


# ---------- recall ----------

@pytest.mark.parametrize("update", ["async", "sync"])
def test_check_recall(tmp_path, patterns, update):
    run_dir = run_recall(tmp_path, update=update)
    summary = hopfield.check_recall(run_dir, patterns)
    assert summary == {"trials": 48, "traced": 48}


def test_check_recall_partial_trace(tmp_path, patterns):
    run_dir = run_recall(tmp_path, trace_trials=1)
    assert hopfield.check_recall(run_dir, patterns) == {"trials": 48, "traced": 4 * 3}


TAMPERS = [
    ("trials.csv", 5, "e_final", "12345"),
    ("trials.csv", 5, "class", "3"),
    ("trials.csv", 5, "correct", "0"),
    ("trials.csv", 20, "flipped", "7"),
    ("trace.csv", 4, "energy", "999"),
    ("states.csv", 1, "s_3", "TOGGLE"),
    ("stored.csv", 1, "min_margin", "99"),
]


@pytest.mark.parametrize("file,row,column,new_value", TAMPERS)
def test_check_recall_detects_tampering(tmp_path, patterns, file, row, column, new_value):
    run_dir = run_recall(tmp_path)
    tampered = copy_run(run_dir, tmp_path)
    if new_value == "TOGGLE":
        header, table = hopfield.read_table(tampered / file)
        new_value = str(int(-table[row, header.index(column)]))
    rewrite_cell(tampered / file, row, column, new_value)
    with pytest.raises(HopfieldCheckError) as caught:
        hopfield.check_recall(tampered, patterns)
    assert file in str(caught.value) and column in str(caught.value)


def test_check_recall_detects_metric_tampering(tmp_path, patterns):
    run_dir = run_recall(tmp_path)
    tampered = copy_run(run_dir, tmp_path)
    text = (tampered / "metrics.json").read_text().replace('"stored_fixed": 4', '"stored_fixed": 3')
    (tampered / "metrics.json").write_text(text)
    with pytest.raises(HopfieldCheckError, match="stored_fixed"):
        hopfield.check_recall(tampered, patterns)


# ---------- reproducibility ----------

def assert_same_tree(left: Path, right: Path):
    comparison = filecmp.dircmp(left, right)
    assert not comparison.left_only and not comparison.right_only and not comparison.funny_files
    _match, mismatch, errors = filecmp.cmpfiles(left, right, comparison.common_files, shallow=False)
    assert not mismatch and not errors
    for name in comparison.common_dirs:
        assert_same_tree(left / name, right / name)


def test_runs_are_reproducible(tmp_path):
    one, two, three = (tmp_path / name for name in ("one", "two", "three"))
    for folder in (one, two, three):
        folder.mkdir()
    first = run_recall(one)
    second = run_recall(two)
    other = run_recall(three, seed=4)
    assert_same_tree(first, second)
    assert (first / "trials.csv").read_bytes() != (other / "trials.csv").read_bytes()
