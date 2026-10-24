"""Independent numpy recomputation of the Hopfield outputs from a run directory (HOP-01, HOP-02, D-05).

The C binary (neuron/models/hopfield.c) writes stored.csv, overlaps.csv, trials.csv, trace.csv, states.csv and
metrics.json for task "recall", and capacity.csv and metrics.json for task "capacity". `check_recall` and
`check_capacity` read a run directory and raise `HopfieldCheckError` naming the file, the row and the column of the
first disagreement. What they recompute and what they only sanity-check is not the same thing:

Recomputed independently in numpy (W, fields, energies, fixed points, stability margins):
  - W, stored.csv and overlaps.csv of every run;
  - the capacity columns max/mean overlap, n_stable, stable_fraction and min_margin, row by row, and the
    mean_stable_fraction and all_stable_fraction of the capacity metrics.json;
  - the traced recall trials: the trial is replayed step by step from its saved query and trace (field, new state,
    energy of every row), its final state is classified again, and class, match, flips, sweeps, converged, cycle and
    the energies are compared. The recall series trace the first trial of each (letter, level) cell (trace_trials =
    1 of 30 trials), and the spurious-search series trace every trial.

Only range and consistency checks (not recomputed, since the final state of an untraced trial is not saved):
  - class, converged, sweeps, flips and correct of the untraced recall trials; `correct` is compared with the class
    and match_a written in the same row, so that check is circular for those trials;
  - the capacity recall_rate (in [0, 1]) and mean_sweeps (at least 1).

The recall rates that recall.csv and the recall figures aggregate therefore rest on the C-written columns for all
but the traced trials. The check never replays the random number generator: what the C code drew (which pixels were
flipped, the order of the async visits) is read back from the saved queries and traces and replayed as data.

Notation: P is the p x N matrix of stored patterns (+-1). Two rules build W: `hebb` gives W = P^T P with a zero
diagonal, exact integers; `pinv` gives W = P^T (P P^T)^-1 P (D-06), the pseudo-inverse / projection rule, real-valued
with a non-zero diagonal (D-07) - numpy.linalg.inv is an independent check here, not a Hopfield implementation, so
PROJECT.md's ban on packages that implement Hopfield does not cover it. Either way h = W s are the fields and
E = -1/2 s^T W s. Everything below (`fields`, `energy`, `is_fixed`, `margins`) works in float64 throughout rather
than casting W to int64: for Hebb's exact-integer entries this loses nothing (the magnitudes stay far inside
float64's exact-integer range), and it is what makes a real-valued pinv W safe to compare without truncating it to
zero. A pattern xi^a is a fixed point when no xi_i h_i(xi) falls below -ENERGY_TOLERANCE (a zero, or near-zero,
field keeps the state; the tolerance absorbs the rounding of a true pinv fixed point landing a hair below 0).

For Hebb only, with d_ab = xi^a . xi^b, the margin of a pattern splits as

    xi^a_i h_i(xi^a) = (N - p) + c_ai,   c_ai = sum over b != a of xi^a_i xi^b_i d_ab    (see `cross_terms`)

so the margin is N - p plus the cross term, and a pattern loses stability when the cross term reaches -(N - p).

numpy and the standard library only (PROJECT.md: Hopfield by hand, no pandas, no Hopfield package).
"""

from __future__ import annotations

import csv
import itertools
import json
import math
from pathlib import Path

import numpy as np

CLASS_STORED = 0
CLASS_INVERSE = 1
CLASS_MIXTURE = 2
CLASS_OTHER = 3

ENERGY_TOLERANCE = 1e-9
RATE_TOLERANCE = 1e-12


class HopfieldCheckError(ValueError):
    """A value written by the C binary disagrees with the numpy recomputation."""


# ---------- reading ----------

def load_patterns(path) -> np.ndarray:
    """The input CSV as an int64 matrix of -1 and 1 (header skipped); any other value raises ValueError."""
    with Path(path).open(newline="", encoding="utf-8") as file:
        rows = list(csv.reader(file))
    if len(rows) < 2:
        raise ValueError(f"{path}: no data rows")
    matrix = np.array([[float(cell) for cell in row] for row in rows[1:]], dtype=np.float64)
    if not np.all((matrix == 1) | (matrix == -1)):
        raise ValueError(f"{path}: patterns must contain only -1 and 1")
    return matrix.astype(np.int64)


def read_table(path) -> tuple[list[str], np.ndarray]:
    """(header, float64 array rows x columns) of a CSV written by results_write_table; zero rows give 0 x columns."""
    with Path(path).open(newline="", encoding="utf-8") as file:
        rows = list(csv.reader(file))
    if not rows:
        raise HopfieldCheckError(f"{Path(path).name}: empty file")
    header, body = rows[0], rows[1:]
    for number, row in enumerate(body):
        if len(row) != len(header):
            raise HopfieldCheckError(f"{Path(path).name} row {number}: {len(row)} cells, the header has {len(header)}")
    table = np.array([[float(cell) for cell in row] for row in body], dtype=np.float64).reshape(len(body), len(header))
    return header, table


def read_metrics(run_dir) -> dict:
    return json.loads((Path(run_dir) / "metrics.json").read_text())


def read_config(run_dir) -> dict:
    return json.loads((Path(run_dir) / "config.json").read_text())


# ---------- the network ----------

def hebb(P) -> np.ndarray:
    """W = P^T P with the diagonal zeroed; float64 (like the C core), but every entry is an exact integer."""
    P = np.asarray(P, dtype=np.float64)
    W = P.T @ P
    np.fill_diagonal(W, 0)
    return W


def pinv(P) -> np.ndarray:
    """W = P^T (P P^T)^-1 P, the pseudo-inverse / projection rule (D-06); float64, diagonal left intact (D-07) -
    the projection property that makes every row of P an exact fixed point (within ENERGY_TOLERANCE)."""
    P = np.asarray(P, dtype=np.float64)
    G = P @ P.T
    return P.T @ np.linalg.inv(G) @ P


def weights(rule: str, P) -> np.ndarray:
    """hebb(P) or pinv(P), selected by the rule read from the run (D-06)."""
    if rule == "hebb":
        return hebb(P)
    if rule == "pinv":
        return pinv(P)
    raise HopfieldCheckError(f"rule {rule!r}: expected \"hebb\" or \"pinv\"")


def fields(W, s) -> np.ndarray:
    return np.asarray(W, dtype=np.float64) @ np.asarray(s, dtype=np.float64)


def energy(W, s) -> float:
    """-1/2 s^T W s, float64 throughout (exact for Hebb's integer-valued W: the magnitudes stay far inside
    float64's exact-integer range, so nothing is lost by not casting to int64)."""
    s = np.asarray(s, dtype=np.float64)
    return float(-0.5 * (s @ np.asarray(W, dtype=np.float64) @ s))


def is_fixed(W, s, tol: float = ENERGY_TOLERANCE) -> bool:
    """True when no s_i h_i falls below -tol: a zero (or near-zero) field keeps the state, so a tie never breaks a
    fixed point, and a true pinv fixed point landing a hair below 0 from rounding still counts."""
    s = np.asarray(s, dtype=np.float64)
    return bool(np.all(s * fields(W, s) >= -tol))


def margins(W, P, tol: float = ENERGY_TOLERANCE) -> tuple[np.ndarray, np.ndarray]:
    """(min over i of xi_i h_i, count of i with xi_i h_i < -tol) for every row of P."""
    P = np.asarray(P, dtype=np.float64)
    aligned = P * (P @ np.asarray(W, dtype=np.float64))  # W is symmetric: (P W)[a, i] = h_i(xi^a)
    return aligned.min(axis=1), (aligned < -tol).sum(axis=1)


def cross_terms(P) -> np.ndarray:
    """c[a, i] = sum over b != a of xi^a_i xi^b_i d_ab, so that xi^a_i h_i(xi^a) = (N - p) + c[a, i]."""
    P = np.asarray(P, dtype=np.int64)
    d = P @ P.T
    p = P.shape[0]
    c = np.zeros_like(P)
    for a in range(p):
        for b in range(p):
            if b != a:
                c[a] += P[a] * P[b] * d[a, b]
    return c


def classify(P, s) -> tuple[int, tuple[int, int, int], tuple[int, int, int]]:
    """Mirror of hopfield_classify: stored (all patterns first), then inverse, then the mixture of a triple a < b < c
    with signs from bits 0..7 (bit 0 flips a, bit 1 b, bit 2 c), then other. Returns (code, match, sign) with -1
    and 0 in the unused slots."""
    P = np.asarray(P, dtype=np.int64)
    s = np.asarray(s, dtype=np.int64)
    n = P.shape[1]
    dots = P @ s
    for a in range(P.shape[0]):
        if dots[a] == n:
            return CLASS_STORED, (a, -1, -1), (1, 0, 0)
    for a in range(P.shape[0]):
        if dots[a] == -n:
            return CLASS_INVERSE, (a, -1, -1), (-1, 0, 0)
    for a, b, c in itertools.combinations(range(P.shape[0]), 3):
        for bits in range(8):
            sa = -1 if bits & 1 else 1
            sb = -1 if bits & 2 else 1
            sc = -1 if bits & 4 else 1
            total = sa * P[a] + sb * P[b] + sc * P[c]
            if np.array_equal(np.where(total > 0, 1, -1), s):
                return CLASS_MIXTURE, (a, b, c), (sa, sb, sc)
    return CLASS_OTHER, (-1, -1, -1), (0, 0, 0)


# ---------- comparing ----------

def _fail(file: str, row, column: str, c_value, numpy_value):
    raise HopfieldCheckError(f"{file} row {row}, column {column}: C {c_value!r}, numpy {numpy_value!r}")


def _expect(file: str, row, column: str, got, want, tol: float = 0.0, rel: float = 0.0):
    """Fails unless |got - want| <= tol + rel * |want|: rel adds a small relative tolerance on top of the
    absolute tol, used for field and overlap comparisons that would otherwise need a magnitude-dependent tol."""
    got_f, want_f = float(got), float(want)
    if abs(got_f - want_f) > tol + rel * abs(want_f):
        _fail(file, row, column, got_f, want_f)


def _col(header: list[str], name: str, file: str) -> int:
    if name not in header:
        raise HopfieldCheckError(f"{file}: no column {name}")
    return header.index(name)


def _rounded(x: float) -> int:
    """C lround for x >= 0 (half away from zero)."""
    return int(math.floor(x + 0.5))


def _pm_one(file: str, row: int, values: np.ndarray, prefix: str) -> np.ndarray:
    for j, v in enumerate(values):
        if v != 1 and v != -1:
            _fail(file, row, f"{prefix}{j}", float(v), "-1 or 1")
    return values.astype(np.int64)


# ---------- capacity ----------

def check_capacity(run_dir, patterns) -> dict:
    """Recompute the stability columns of every row of capacity.csv (recall_rate and mean_sweeps are only range
    checked) and check the four aggregates of metrics.json against the rows. Returns
    {"rows": count, "mean_stable_fraction": value}."""
    run_dir = Path(run_dir)
    patterns = np.asarray(patterns, dtype=np.int64)
    config = read_config(run_dir)
    p, n_subsets = int(config["p"]), int(config["n_subsets"])
    n_rows, n = patterns.shape
    header, table = read_table(run_dir / "capacity.csv")
    file = "capacity.csv"

    expected_header = (["subset"] + [f"idx_{c}" for c in range(p)]
                       + ["max_abs_overlap", "mean_abs_overlap", "n_stable", "stable_fraction", "min_margin",
                          "recall_rate", "mean_sweeps"])
    if header != expected_header:
        raise HopfieldCheckError(f"{file}: header {header}, expected {expected_header}")

    rows = table.shape[0]
    if n_subsets == 0:
        every = list(itertools.combinations(range(n_rows), p))
        if rows != len(every):
            raise HopfieldCheckError(f"{file}: {rows} rows, numpy {len(every)} subsets")
    elif rows != n_subsets:
        raise HopfieldCheckError(f"{file}: {rows} rows, n_subsets {n_subsets}")

    seen = set()
    for r in range(rows):
        _expect(file, r, "subset", table[r, 0], r)
        idx = tuple(int(v) for v in table[r, 1:1 + p])
        if n_subsets == 0:
            for c in range(p):
                _expect(file, r, f"idx_{c}", idx[c], every[r][c])
        else:
            for c in range(p):
                if not 0 <= idx[c] < n_rows:
                    _fail(file, r, f"idx_{c}", idx[c], f"an index below {n_rows}")
                if c > 0 and idx[c] <= idx[c - 1]:
                    _fail(file, r, f"idx_{c}", idx[c], f"more than idx_{c - 1}")
            if idx in seen:
                _fail(file, r, "idx_0", idx, "a subset not drawn before")
            seen.add(idx)

        P = patterns[list(idx)]
        W = hebb(P)
        margin, wrong = margins(W, P)
        n_stable = int((wrong == 0).sum())
        d = np.abs(P @ P.T)
        pairs = [d[a, b] for a in range(p) for b in range(a + 1, p)]
        max_abs = max(pairs) / n if pairs else 0.0
        mean_abs = sum(pairs) / (n * len(pairs)) if pairs else 0.0
        base = 1 + p
        _expect(file, r, "max_abs_overlap", table[r, base], max_abs, 1e-12)
        _expect(file, r, "mean_abs_overlap", table[r, base + 1], mean_abs, 1e-12)
        _expect(file, r, "n_stable", table[r, base + 2], n_stable)
        _expect(file, r, "stable_fraction", table[r, base + 3], n_stable / p, 1e-12)
        _expect(file, r, "min_margin", table[r, base + 4], int(margin.min()))
        if not 0.0 <= table[r, base + 5] <= 1.0:
            _fail(file, r, "recall_rate", float(table[r, base + 5]), "a value in [0, 1]")
        if table[r, base + 6] < 1.0:
            _fail(file, r, "mean_sweeps", float(table[r, base + 6]), "at least 1")

    base = 1 + p
    metrics = read_metrics(run_dir)
    stable_fraction = table[:, base + 3]
    wanted = {
        "n_subsets": rows,
        "mean_stable_fraction": float(stable_fraction.mean()),
        "all_stable_fraction": float((table[:, base + 2] == p).mean()),
        "mean_recall_rate": float(table[:, base + 5].mean()),
    }
    for key, value in wanted.items():
        _expect("metrics.json", "-", key, metrics[key], value, RATE_TOLERANCE)
    return {"rows": rows, "mean_stable_fraction": float(stable_fraction.mean())}


# ---------- recall ----------

def _check_stored(run_dir: Path, P: np.ndarray, W: np.ndarray, subset: list[int]) -> int:
    file = "stored.csv"
    header, table = read_table(run_dir / file)
    p, n = P.shape
    if table.shape[0] != p:
        raise HopfieldCheckError(f"{file}: {table.shape[0]} rows, numpy {p}")
    margin, wrong = margins(W, P)
    column = {name: _col(header, name, file) for name in header}
    for a in range(p):
        _expect(file, a, "pattern", table[a, column["pattern"]], a)
        _expect(file, a, "source_row", table[a, column["source_row"]], subset[a])
        _expect(file, a, "fixed", table[a, column["fixed"]], int(wrong[a] == 0))
        _expect(file, a, "min_margin", table[a, column["min_margin"]], margin[a], ENERGY_TOLERANCE)
        _expect(file, a, "wrong_pixels", table[a, column["wrong_pixels"]], int(wrong[a]))
        _expect(file, a, "energy", table[a, column["energy"]], energy(W, P[a]), ENERGY_TOLERANCE)

    file = "overlaps.csv"
    header, table = read_table(run_dir / file)
    overlaps = (P @ P.T) / n
    for a in range(p):
        _expect(file, a, "pattern", table[a, 0], a)
        for b in range(p):
            _expect(file, a, f"m_{b}", table[a, 1 + b], overlaps[a, b], tol=1e-12, rel=1e-9)
    return int((wrong == 0).sum())


def _replay_async(W, query, trace_rows, n, max_sweeps, file, first_row):
    """Replays the saved visits from the query: the field, the new state and the energy of every row are recomputed.
    Returns (final state, flips, sweeps, converged, rises)."""
    W = np.asarray(W, dtype=np.float64)
    diag = np.diag(W)  # 0 for hebb; the self term subtracted below so the incremental energy matches a non-zero
    # diagonal under pinv (mirrors hopfield_async_run's corrected formula in hopfield_core.c)
    s = query.astype(np.float64)
    e = energy(W, s)
    rises = 0
    flips = 0
    sweeps = 0
    seen = set()
    last_sweep_flips = 0
    for k, row in enumerate(trace_rows[1:], start=1):
        r = first_row + k
        _step, sweep, neuron, changed, shown = (float(v) for v in row[1:6])
        _expect(file, r, "step", row[1], k)
        sweep = int(sweep)
        neuron = int(neuron)
        if sweep != sweeps:
            if sweep != sweeps + 1 or len(seen) not in (0, n):
                _fail(file, r, "sweep", sweep, sweeps + 1)
            if sweeps > 0 and last_sweep_flips == 0:
                _fail(file, r, "sweep", sweep, "no sweep after a sweep without flips")
            sweeps = sweep
            seen = set()
            last_sweep_flips = 0
        if not 0 <= neuron < n or neuron in seen:
            _fail(file, r, "neuron", neuron, "a neuron not visited yet in this sweep")
        seen.add(neuron)
        h = float(W[neuron] @ s)
        new = s[neuron] if h == 0 else (1.0 if h > 0 else -1.0)
        did_change = int(new != s[neuron])
        _expect(file, r, "changed", changed, did_change)
        if did_change:
            e = e + 2 * s[neuron] * h - 2 * diag[neuron]
            s[neuron] = new
            flips += 1
            last_sweep_flips += 1
        _expect(file, r, "energy", shown, e, ENERGY_TOLERANCE)
        _expect(file, r, "energy", shown, energy(W, s), ENERGY_TOLERANCE)
        if shown > float(trace_rows[k - 1][5]) + ENERGY_TOLERANCE:
            rises += 1
    if len(seen) not in (0, n):
        raise HopfieldCheckError(f"{file} row {first_row + len(trace_rows) - 1}, column sweep: an unfinished sweep")
    converged = int(sweeps > 0 and last_sweep_flips == 0)
    if sweeps > max_sweeps:
        raise HopfieldCheckError(f"{file}: {sweeps} sweeps, max_sweeps {max_sweeps}")
    return s, flips, sweeps, converged, rises


def _replay_sync(W, query, trace_rows, max_sweeps, file, first_row):
    """Replays the saved synchronous steps. Returns (final state, flips, steps, converged, cycle, rises)."""
    s = query.copy()
    previous = None
    flips = 0
    converged = 0
    cycle = 0
    rises = 0
    prior_energy = float(trace_rows[0][5])
    steps = 0
    for k, row in enumerate(trace_rows[1:], start=1):
        r = first_row + k
        if converged or cycle:
            _fail(file, r, "step", k, "no step after convergence or a cycle")
        h = W @ s
        new = np.where(h > 0, 1, np.where(h < 0, -1, s))
        changed = int((new != s).sum())
        _expect(file, r, "step", row[1], k)
        _expect(file, r, "changed", row[4], changed)
        _expect(file, r, "energy", row[5], energy(W, new), ENERGY_TOLERANCE)
        if row[5] > prior_energy + ENERGY_TOLERANCE:
            rises += 1
        prior_energy = float(row[5])
        flips += changed
        steps = k
        if changed == 0:
            converged = 1
        elif k >= 2 and np.array_equal(new, previous):
            cycle = 2
        previous = s
        s = new
    if steps > max_sweeps:
        raise HopfieldCheckError(f"{file}: {steps} steps, max_sweeps {max_sweeps}")
    return s, flips, steps, converged, cycle, rises


def check_recall(run_dir, patterns) -> dict:
    """Check a recall run against the run directory and the input patterns: W, stored.csv and the overlaps are
    recomputed, each traced trial is replayed in full, and the other trials get range and consistency checks only
    (see the module docstring). Returns
    {"trials": n, "traced": m}: the trials in trials.csv and the trials replayed step by step."""
    run_dir = Path(run_dir)
    patterns = np.asarray(patterns, dtype=np.int64)
    config = read_config(run_dir)
    subset = [int(v) for v in config["subset"]]
    levels = [float(v) for v in config["noise_levels"]]
    trials_per_cell = int(config["trials"])
    trace_trials = int(config["trace_trials"])
    max_sweeps = int(config["max_sweeps"])
    sync = config["update"] == "sync"
    rule = config["rule"]
    P = patterns[subset]
    p, n = P.shape
    W = weights(rule, P)

    stored_fixed = _check_stored(run_dir, P, W, subset)

    file = "trials.csv"
    header, table = read_table(run_dir / file)
    column = {name: _col(header, name, file) for name in header}
    if len(header) != 22 + p or header[22:] != [f"m_{b}" for b in range(p)]:
        raise HopfieldCheckError(f"{file}: header {header}")
    n_trials = p * len(levels) * trials_per_cell
    if table.shape[0] != n_trials:
        raise HopfieldCheckError(f"{file}: {table.shape[0]} rows, numpy {n_trials}")

    def value(r, name):
        return table[r, column[name]]

    cells = [(a, l, t) for a in range(p) for l in range(len(levels)) for t in range(trials_per_cell)]
    for r, (a, l, t) in enumerate(cells):
        k = _rounded(levels[l] * n)
        _expect(file, r, "trial", value(r, "trial"), r)
        _expect(file, r, "pattern", value(r, "pattern"), a)
        _expect(file, r, "source_row", value(r, "source_row"), subset[a])
        _expect(file, r, "noise", value(r, "noise"), levels[l], 1e-12)
        _expect(file, r, "flipped", value(r, "flipped"), k)
        _expect(file, r, "overlap", value(r, "overlap"), (n - 2 * k) / n, 1e-12)
        klass = int(value(r, "class"))
        if klass not in (CLASS_STORED, CLASS_INVERSE, CLASS_MIXTURE, CLASS_OTHER):
            _fail(file, r, "class", klass, "a class code 0 to 3")
        converged = int(value(r, "converged"))
        if converged not in (0, 1):
            _fail(file, r, "converged", converged, "0 or 1")
        _expect(file, r, "updates", value(r, "updates"), value(r, "sweeps") * n)
        if not 1 <= value(r, "sweeps") <= max_sweeps:
            _fail(file, r, "sweeps", float(value(r, "sweeps")), f"between 1 and {max_sweeps}")
        hamming = value(r, "hamming_final")
        _expect(file, r, f"m_{a}", value(r, f"m_{a}"), (n - 2 * hamming) / n, 1e-12)
        cycle = int(value(r, "cycle"))
        if (not sync and cycle != 0) or cycle not in (0, 2) or (cycle == 2 and converged == 1):
            _fail(file, r, "cycle", cycle, "0 for async, 0 or 2 (not converged) for sync")

    # Traced trials: the trace, the query and the final state of every one are replayed
    traced_ids = [r for r, (_a, _l, t) in enumerate(cells) if t < trace_trials]
    s_header, states = read_table(run_dir / "states.csv")
    t_header, trace = read_table(run_dir / "trace.csv")
    if s_header != ["trial", "kind"] + [f"s_{j}" for j in range(n)]:
        raise HopfieldCheckError(f"states.csv: header {s_header}")
    if t_header != ["trial", "step", "sweep", "neuron", "changed", "energy"]:
        raise HopfieldCheckError(f"trace.csv: header {t_header}")
    if states.shape[0] != 2 * len(traced_ids):
        raise HopfieldCheckError(f"states.csv: {states.shape[0]} rows, numpy {2 * len(traced_ids)}")

    cursor = 0
    total_rises = 0
    for position, r in enumerate(traced_ids):
        a = cells[r][0]
        q_row, f_row = 2 * position, 2 * position + 1
        _expect("states.csv", q_row, "trial", states[q_row, 0], r)
        _expect("states.csv", q_row, "kind", states[q_row, 1], 0)
        _expect("states.csv", f_row, "trial", states[f_row, 0], r)
        _expect("states.csv", f_row, "kind", states[f_row, 1], 1)
        query = _pm_one("states.csv", q_row, states[q_row, 2:], "s_")
        final = _pm_one("states.csv", f_row, states[f_row, 2:], "s_")

        _expect("states.csv", q_row, "s_j (flipped pixels)", int((query != P[a]).sum()), value(r, "flipped"))
        _expect(file, r, "e_start", value(r, "e_start"), energy(W, query), ENERGY_TOLERANCE)

        end = cursor
        while end < trace.shape[0] and trace[end, 0] == r:
            end += 1
        block = trace[cursor:end]
        if block.shape[0] == 0:
            raise HopfieldCheckError(f"trace.csv row {cursor}: no rows for trial {r}")
        first = cursor
        cursor = end
        _expect("trace.csv", first, "step", block[0, 1], 0)
        _expect("trace.csv", first, "neuron", block[0, 3], -1)
        _expect("trace.csv", first, "energy", block[0, 5], value(r, "e_start"), ENERGY_TOLERANCE)

        if sync:
            replayed, flips, steps, converged, cycle, rises = _replay_sync(W, query, block, max_sweeps,
                                                                           "trace.csv", first)
            _expect(file, r, "cycle", value(r, "cycle"), cycle)
        else:
            replayed, flips, steps, converged, rises = _replay_async(W, query, block, n, max_sweeps, "trace.csv",
                                                                     first)
        total_rises += rises
        for j in range(n):
            if replayed[j] != final[j]:
                _fail("states.csv", f_row, f"s_{j}", int(final[j]), int(replayed[j]))
        _expect(file, r, "flips", value(r, "flips"), flips)
        _expect(file, r, "sweeps", value(r, "sweeps"), steps)
        _expect(file, r, "converged", value(r, "converged"), converged)
        _expect(file, r, "e_final", value(r, "e_final"), energy(W, final), ENERGY_TOLERANCE)
        _expect("trace.csv", cursor - 1, "energy", block[-1, 5], value(r, "e_final"), ENERGY_TOLERANCE)
        _expect(file, r, "hamming_final", value(r, "hamming_final"), int((final != P[a]).sum()))
        for b in range(p):
            _expect(file, r, f"m_{b}", value(r, f"m_{b}"), float(P[b] @ final) / n, 1e-12)
        code, match, sign = classify(P, final)
        _expect(file, r, "class", value(r, "class"), code)
        for slot, name in enumerate("abc"):
            _expect(file, r, f"match_{name}", value(r, f"match_{name}"), match[slot])
            _expect(file, r, f"sign_{name}", value(r, f"sign_{name}"), sign[slot])
        if int(value(r, "converged")) == 1 and not is_fixed(W, final):
            _fail(file, r, "converged", 1, "a final state that is not a fixed point")
    if cursor != trace.shape[0]:
        raise HopfieldCheckError(f"trace.csv row {cursor}: rows of a trial that is not traced")

    # correct = converged and stored and the right pattern, from the class and match that were just verified
    for r, (a, _l, _t) in enumerate(cells):
        correct = int(value(r, "converged") == 1 and value(r, "class") == CLASS_STORED and value(r, "match_a") == a)
        _expect(file, r, "correct", value(r, "correct"), correct)

    # Untraced trials can't be replayed, but the invariants that hold for every trial are checked
    traced = set(traced_ids)
    for r in range(n_trials):
        if r in traced:
            continue
        if not sync and value(r, "e_final") > value(r, "e_start") + ENERGY_TOLERANCE:
            _fail(file, r, "e_final", float(value(r, "e_final")), "at most e_start (async energy never rises)")
        if value(r, "flips") > value(r, "updates"):
            _fail(file, r, "flips", float(value(r, "flips")), "at most updates")

    # metrics.json from trials.csv
    metrics = read_metrics(run_dir)
    klass = table[:, column["class"]]
    match_a = table[:, column["match_a"]]
    pattern = table[:, column["pattern"]]
    wanted = {
        "n_patterns": p,
        "n_neurons": n,
        "n_levels": len(levels),
        "trials": trials_per_cell,
        "stored_fixed": stored_fixed,
        "recall_rate": float(table[:, column["correct"]].mean()),
        "wrong_stored_rate": float(((klass == CLASS_STORED) & (match_a != pattern)).mean()),
        "inverse_rate": float((klass == CLASS_INVERSE).mean()),
        "mixture_rate": float((klass == CLASS_MIXTURE).mean()),
        "other_rate": float((klass == CLASS_OTHER).mean()),
        "cycle_rate": float((table[:, column["cycle"]] > 0).mean()),
        "mean_sweeps": float(table[:, column["sweeps"]].mean()),
        "mean_flips": float(table[:, column["flips"]].mean()),
    }
    overlaps = np.abs(P @ P.T) / n
    wanted["max_abs_overlap"] = float(max((overlaps[a, b] for a in range(p) for b in range(a + 1, p)), default=0.0))
    for key, number in wanted.items():
        _expect("metrics.json", "-", key, metrics[key], number, RATE_TOLERANCE)
    if not sync:
        _expect("metrics.json", "-", "energy_increases", metrics["energy_increases"], 0)
    elif trace_trials == trials_per_cell:
        _expect("metrics.json", "-", "energy_increases", metrics["energy_increases"], total_rises)
    return {"trials": n_trials, "traced": len(traced_ids)}
