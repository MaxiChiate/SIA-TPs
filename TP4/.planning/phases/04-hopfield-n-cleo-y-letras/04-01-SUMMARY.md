---
phase: 04-hopfield-n-cleo-y-letras
plan: 01
subsystem: neuron (C core)
tags: [hopfield, c, hebb, async, sync, energy, classifier]
requires: []
provides:
  - "hopfield_core.[ch]: pure Hopfield core (Hebb, fields, energy, async and sync runs with trace, classifier, stability margin)"
  - "run_hopfield: recall task writing stored.csv, overlaps.csv, trials.csv, trace.csv, states.csv and a 20-key metrics.json"
  - "HOPFIELD_KEYS: task, rule, update, max_sweeps, trials, noise_levels, subset, trace_trials"
affects: [04-02, 04-03, 04-04, 04-05, phase-5]
tech-stack:
  added: []
  patterns: ["integer W held exactly in doubles, zero diagonal, no 1/N", "incremental energy checked against from-scratch energy"]
key-files:
  created:
    - neuron/models/hopfield_core.h
    - neuron/models/hopfield_core.c
    - neuron/models/hopfield.c
    - neuron/tests/fixtures/patterns_mix.csv
  modified:
    - neuron/io/config.c
    - neuron/tests/test_main.c
    - neuron/config.json.hopfield.example
    - analysis/series_smoke_hopfield.json
  removed:
    - neuron/models/hopfield_stub.c
decisions:
  - "The stub's queries.csv is dropped; its columns pattern, noise, flipped, overlap live on in trials.csv"
  - "Stored is checked for every pattern before inverse, so a stored pattern equal to the negation of another is classified stored"
  - "Sync two-cycle: new state equal to the state two steps back; the detection state is final, converged stays 0, cycle 2"
requirements-completed: [HOP-01]
status: complete
commits: 0
plan_head_before: 609de8759965ac1b4738643c33d86db9c6bd70ea
plan_head_after: 609de8759965ac1b4738643c33d86db9c6bd70ea
actuals:
  tokens: 13000
  tasks: 3
  commits: 0
---

# Phase 4 Plan 01: Hopfield core Summary

A real discrete Hopfield network in C: integer Hebb W with zero diagonal, asynchronous updates with a fresh permutation per sweep (reference), synchronous updates with two-cycle detection, energy logged at every step, and every final state classified as stored, inverse, mixture of three or other. It is validated on a synthetic fixture only; the real letters were never touched (D-04).

## Tasks

1. **Tracer, end-to-end async recall.** The stub was moved to `hopfield.c` and rewritten. `hopfield_core.[ch]` holds the pure core, `HOPFIELD_KEYS` has the eight strict keys, `patterns_mix.csv` is the six-pattern synthetic fixture, and the example config and smoke series were updated. `HOPFIELD_RUN_OK`, `SMOKE_OK` (4 ok rows) and the C test "hopfield run" passed.
2. **Sync dynamics and "hopfield core".** `hopfield_sync_step` and `hopfield_sync_run` (two-cycle detection), the `update: "sync"` option, a third smoke variant (6 ok rows including `sync`) and the core test, which covers the course example, integrality and symmetry, the tie rule, 200 random async starts (monotone energy, incremental equal to from-scratch, fixed final state), the N = 2 two-cycle, every classifier branch and the stability margin. `SYNC_OK` passed.
3. **Refusals and sanitizers.** `hopfield_run_accepts` with 16 cases (subset out of range, repeated or fractional, missing subset or trace_trials, trace_trials 5 or -1, max_sweeps 0 or 10001, trials 0, update hex, rule pinv, task bogus, noise 1.5, a zero entry in the input). `make -C neuron debug` printed no sanitizer report. `HOPFIELD_STRICT_OK` passed (six bad configs exit non-zero naming the key).

## Verification

- `make -C neuron clean all`: no warnings. `make -C neuron test-c`: 609 checks, 0 failed, with `ok   hopfield run` and `ok   hopfield core`. `make -C neuron debug`: clean under ASan/UBSan.
- The example config and its sync twin give byte-identical directories for the same seed. Metrics of the example run: stored_fixed 4, energy_increases 0, recall_rate 0.9417.
- Planning-time numpy values reproduced exactly: min margins 10, 2, 12, 16; energies -304, -332, -288, -268; overlap d01 = 0.36; the mixture of rows (0, 2, 3) is classified as expected.
- Nothing staged or committed. `neuron/README.md`, `analysis/README.md` and `neuron/models/models.h` untouched (plan 04-04). Nothing read `datos/letters/` or `datos/prepared/alphabet_pm1.csv`.

## Deviations from Plan

**1. [Rule 2 - Missing critical functionality] Extra table-size guard.** The plan caps `p x levels x trials` at 2,000,000 rows, but trials.csv has `22 + p` columns, so 2,000,000 rows at p = 64 would need over 1 GB. `read_params` also refuses a trials table or a states table above 50,000,000 values (400 MB), with a message naming `trials` or `trace_trials`. Files: `neuron/models/hopfield.c`.

**2. [Rule 3 - Blocking] `.venv` was absent.** Created with `make venv` (the four audited pins of `analysis/requirements.txt`, nothing else installed) so the smoke sweep could run. `.venv` is not tracked.

**3. Classifier pass order.** The plan text says stored and inverse are checked "in one pass in that order so stored wins over a later inverse". The implementation uses two passes (stored over all patterns, then inverse) so that stored wins even when the inverse match has the lower index. This matches the stated intent and the must_have "stored, then inverse, then mixture, then other".

**4. Session interruption.** The run was interrupted by a session rate limit after the C sources and the first test edits were written. On resume the working tree was inspected (nothing staged, edits intact), and the remaining test functions, the sync variant and all verifications were done without redoing earlier work.

## Known Stubs

None.

## Pre-existing issues (out of scope)

`tests/test_main.c` already produced `-Wformat-truncation` warnings in `compare_dirs`, `same_seed_same_bytes` and the Kohonen test (lines unchanged by this plan). They do not touch the binary build, which stays warning-free. The new Hopfield test uses a larger path buffer and adds none.

## Threat Flags

None. The config and input boundaries named in T-04-01 and T-04-02 are covered: subset indices, `trace_trials`, `n_cols` and the table sizes are validated before any allocation, the trace is capped at 1,000,000 rows with a clear error, and the C tests pass under the sanitizers. T-04-03: incremental energy replayed against from-scratch energy over 200 runs.

## Self-Check: PASSED

Files found: `neuron/models/hopfield_core.h`, `hopfield_core.c`, `hopfield.c`, `neuron/tests/fixtures/patterns_mix.csv`; `hopfield_stub.c` absent. No commits were made by design (user commits by hand), so `commits: 0` is the measured count.
