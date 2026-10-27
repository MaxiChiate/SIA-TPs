---
phase: 04-hopfield-n-cleo-y-letras
plan: 04
subsystem: neuron (C capacity task) and analysis (numpy cross-check)
tags: [hopfield, capacity, c, numpy, cross-check, sampled-subsets]
requires: ["04-01"]
provides:
  - "run_hopfield task capacity: exhaustive (lexicographic) or seed-drawn distinct p-subsets, per-subset overlaps, n_stable, min_margin and recall rate in capacity.csv, 14-key metrics.json"
  - "HOPFIELD_KEYS: p, n_subsets"
  - "analysis/hopfield.py: numpy recomputation of every recall and capacity output (check_recall, check_capacity)"
  - "Hopfield documentation of both tasks in neuron/README.md, models.h and the smoke-series row of analysis/README.md"
affects: [04-05, 04-07]
tech-stack:
  added: []
  patterns: ["checks that replay saved data instead of the RNG", "all-or-nothing allocation of capacity buffers", "bounded combinatorics (early-stop binomial, capped draws)"]
key-files:
  created:
    - neuron/config.json.hopfield_capacity.example
    - analysis/hopfield.py
    - analysis/tests/test_hopfield.py
  modified:
    - neuron/models/hopfield.c
    - neuron/io/config.c
    - neuron/tests/test_main.c
    - neuron/README.md
    - neuron/models/models.h
    - analysis/README.md
decisions:
  - "Sampled subsets are drawn before any trial (shuffle, take p, sort, accept if new), so the subset list depends only on the seed; exhaustive mode uses no RNG for the list"
  - "The numpy check replays the saved async visits and sync steps from the saved query, so a tampered state, energy, changed flag or class is caught without any RNG"
  - "energy_increases of a sync run is recomputed only when every trial is traced; async must be 0"
requirements-completed: [HOP-02, HOP-01]
status: complete
commits: 0
plan_head_before: 23c35639151d9899c9bc6c3958672c24c51e2831
plan_head_after: 23c35639151d9899c9bc6c3958672c24c51e2831
actuals:
  tokens: 33000
  tasks: 3
  commits: 0
---

# Phase 4 Plan 04: Capacity task and numpy cross-check Summary

The Hopfield runner now has a `capacity` task (every p-subset of the input, or n_subsets distinct seed-drawn subsets) and `analysis/hopfield.py` recomputes every number a recall or capacity run writes from the run directory alone. Both are proven on the synthetic fixture only; the letters were never read (D-04).

## Tasks

1. **Tracer, exhaustive capacity end to end.** Keys `p` and `n_subsets` were appended to `HOPFIELD_KEYS`; `read_params` was split into `read_recall_keys` and `read_capacity_keys` after the shared checks (task, rule, update, ranges, noise, input shape). `run_capacity` stores each subset, computes n_stable and min_margin through `hopfield_min_margin`, max and mean pair overlap, then runs the noisy trials with the single `Rng`. The 15 fixture rows give the planning-time `n_stable` (4 2 4 3 4 2 4 4 3 4 ...) and `min_margin` (2 -2 4 -2 6 -6 ...) values exactly; `CAPACITY_OK`, the C test "hopfield capacity" and the first pytest tests passed.
2. **Sampled subsets, refusals, documentation.** `draw_subsets` and `next_combination`, the refusals (n_subsets at or above C(n_rows, p), p 0 or 7, n_subsets -1 or 10001, two noise levels, subset or trace_trials with capacity, missing p, p or n_subsets with recall), `make debug` clean under ASan/UBSan (`DEBUG_OK`), `CAPACITY_STRICT_OK`. Spanish README rows for all ten Hopfield keys, both output tables and the class codes, the models.h comment and the smoke-series row.
3. **Complete recall cross-check.** `check_recall` recomputes stored.csv, overlaps.csv, every trials.csv column that is deterministic, replays each traced trial (async visits and sync steps, with fields, flips, energies, sweeps, convergence, two-cycle), reclassifies every final state and recomputes the metrics. 19 tests (>= 14), including seven parametrised tampering cases and `test_runs_are_reproducible`.

> **Correction (gap closure 04-08, WR-01).** This overstates the check. Replayed step by step in numpy: the traced trials only (the first trial per letter and level of each recall run, 2,080 of the 62,400 recall trials, plus all 1,200 spurious-search trials). Recomputed for every run: W, stored.csv, overlaps and the capacity stability columns (max/mean overlap, n_stable, stable_fraction, min_margin). Only range- and consistency-checked: class, converged, sweeps, flips and correct of the other 60,320 recall trials, and the capacity recall_rate and mean_sweeps. The same applies to the frontmatter lines of this file that say "every" or "all".

## Verification

- `make -C neuron test-c`: 1100 checks, 0 failed, with `ok   hopfield run`, `ok   hopfield core`, `ok   hopfield capacity`. `make -C neuron debug`: clean.
- `.venv/bin/python -m pytest analysis/tests/test_hopfield.py -q`: 19 passed; whole `analysis/tests`: 114 passed. `HOPFIELD_PY_OK`, `NO_EXTRA_LIBS_OK`, `DOCS_OK`.
- Nothing staged. Nothing read `datos/letters/` or `datos/prepared/alphabet_pm1.csv`. No `0.138N` threshold anywhere (the task only reports fractions).

## Deviations from Plan

**1. [Process] Sampled mode implemented in Task 1.** The plan lets Task 1 fail with "sampled subsets are not implemented" until Task 2; since the validation, drawing and writer share one function, both modes were written together and Task 2's tests were added right after. No behavior difference in the end state.

**2. [Rule 2 - Missing critical functionality] Extra table-size guard.** `read_capacity_keys` also refuses a capacity.csv above 50,000,000 values (as plan 04-01 did for trials.csv), with a message naming p and n_subsets.

**3. Commit accounting.** The user committed plan 04-03's files (`23c3563`) while this plan ran; nothing here was committed, so `commits: 0` and `plan_head_before == plan_head_after` record the HEAD seen at SUMMARY time (the per-plan ledger was not created, because no commit step ran).

## Known Stubs

None.

## Threat Flags

None. T-04-10: C(n_rows, p) is computed with an early stop at 200000, n_subsets <= 10000 and below C, work <= 50,000,000, draws capped at 1000 x n_subsets; refusals are tested and the tests run under the sanitizers. T-04-11: tampering of capacity.csv, trials.csv, trace.csv, states.csv, stored.csv and metrics.json is detected and named by the tests.

## Self-Check: PASSED

Files found: `neuron/models/hopfield.c`, `neuron/config.json.hopfield_capacity.example`, `analysis/hopfield.py`, `analysis/tests/test_hopfield.py`; `git diff --cached --quiet` exits 0.
