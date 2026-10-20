---
phase: 01-fundaci-n-auditor-a-de-datos-y-pca
plan: 05
subsystem: infra
tags: [c, config, dispatch, kohonen, hopfield, oja, stubs]

requires:
  - phase: 01-01
    provides: "C skeleton: strict KeySpec config, matrix loader, results writer, model dispatch table, oja stub"
  - phase: 01-04
    provides: "datos/prepared/creadores_zscore.csv (50 x 26 audited z-scores)"
provides:
  - "run_kohonen stub: sample-initialised k x k prototypes and nearest-prototype assignments (prototypes.csv, assignments.csv)"
  - "run_hopfield stub: seeded pixel flips per noise level and overlap with the stored pattern (queries.csv)"
  - "KOHONEN_KEYS (grid_k) and HOPFIELD_KEYS (noise_levels) strict key tables; registry order kohonen, oja, hopfield in both config.c and models.c"
  - "Example configs for the three models; oja and kohonen read ../datos/prepared/creadores_zscore.csv, hopfield reads tests/fixtures/patterns_small.csv"
affects: [01-07, 01-08, phase-02, phase-03, phase-04, phase-05]

actuals:
  tokens: 3000     # chars/4 over the 6 new files (10548 chars) plus about 1500 chars of edits
  tasks: 2
  commits: 2
plan_head_before: ef9273fbf5fd9e55ce5cbeb5d856fd940c2f3bf8
plan_head_after: 102225109e4a7f85271be152aa4e40a9a375bd4a

tech-stack:
  added: []
  patterns:
    - "A new model is one runner in models/, one row in MODELS (models.c) and one row in MODEL_KEYS (config.c), in the same order"
    - "Model-specific values are read with the typed config getters and range-checked before any allocation"
    - "Stubs are deterministic, draw only from the passed Rng and write the same file names the real model will keep"

key-files:
  created:
    - TP4/neuron/models/kohonen_stub.c
    - TP4/neuron/models/hopfield_stub.c
    - TP4/neuron/config.json.kohonen.example
    - TP4/neuron/config.json.hopfield.example
    - TP4/neuron/tests/fixtures/patterns_small.csv
  modified:
    - TP4/neuron/io/config.c
    - TP4/neuron/io/config.h
    - TP4/neuron/models/models.c
    - TP4/neuron/models/models.h
    - TP4/neuron/config.json.oja.example
    - TP4/analysis/README.md

key-decisions:
  - "grid_k is bounded by floor(sqrt(n_samples)) computed with integer arithmetic (7 for 50 samples), and the check runs before the prototype buffer is allocated (T-01-11)"
  - "Hopfield validates that every pattern value is exactly -1 or 1 and every noise level is in [0, 1] before any flip, so k = lround(level * n) always lies in [0, n] (T-01-12)"
  - "Failed runs still leave a results/ directory, as in plan 01-01; left unchanged because results/ is not versioned"

patterns-established:
  - "Stub outputs fix the file names and column headers (prototypes.csv, assignments.csv, queries.csv) that Phases 2, 4 and 5 keep when they replace the bodies"

requirements-completed: [INFRA-01, INFRA-02]

status: complete
duration: 12min
completed: 2026-10-20
---

# Phase 01 Plan 05: Kohonen and Hopfield stubs, per-model keys, real-data examples Summary

**The single `neuron` binary now dispatches kohonen, oja and hopfield from the `model` key alone, each with its own strict key table, and the oja and kohonen examples run on the audited 50 x 26 creators matrix with byte-identical same-seed run directories.**

## Performance

- **Duration:** about 12 min
- **Tasks:** 2
- **Files created:** 5, modified: 6

## Accomplishments

- `run_kohonen`: loads the input, picks `grid_k * grid_k` distinct samples as prototypes with a seeded shuffle, assigns every sample to its nearest prototype (lowest index wins ties) and writes `prototypes.csv` (9 lines), `assignments.csv` (50 lines) and metrics `model, seed, n_samples, n_features, grid_k, n_neurons, occupied_neurons, mean_bmu_distance`. On the real data with seed 1: 9 of 9 neurons occupied, mean BMU distance 3.5228.
- `run_hopfield`: flips the first `lround(level * n)` entries of a seeded shuffle for each pattern and level; `queries.csv` has the header `pattern,noise,flipped,overlap` and 6 rows for 2 patterns x 3 levels. Noise 0 gives flipped 0 and overlap 1 for both letters; overlap at 0.1 is 0.76 (3 flips) and at 0.2 is 0.60 (5 flips).
- Strict keys per model: `grid_k` inside an oja config fails with `unknown key "grid_k"`, `grid_k: 2.5` fails naming `grid_k`, a kohonen config without it fails with `missing key "grid_k"`, `noise_levels` as `["a"]` or `[]` fails naming `noise_levels`, and model `som` fails with `(available: kohonen, oja, hopfield)`.
- `analysis/sweep.py analysis/series_smoke_oja.json` still runs 3 of 3 runs ok against the new oja example, and the README row for the series now names `datos/prepared/creadores_zscore.csv`.

## Task Commits

1. **Task 1: kohonen stub, strict grid_k, oja and kohonen on audited data** - `2787545` (feat)
2. **Task 2: hopfield stub, strict noise_levels, +-1 letters fixture** - `1022251` (feat)

## Verification

- `make -C neuron` builds without warnings under `-Wall -Wextra -Wpedantic`.
- `diff -r` between two same-seed run directories is clean for kohonen, oja and hopfield; oja metrics show `"n_samples": 50` and `"n_features": 26`; kohonen metrics show `"n_neurons": 9`.
- `KOHONEN_STRICT_OK` and `HOPFIELD_STRICT_OK` conditions both met (all bad configs exit non-zero with the expected key in stderr).
- Extra checks beyond the plan: `grid_k` 8 and 0 fail with `grid_k must be between 1 and 7`; `noise_levels: [1.5]` fails with `noise_levels[0] = 1.5 is outside [0, 1]`; a hopfield config pointed at the z-score CSV fails with `patterns must contain only -1 and 1`.
- `grep -c 'run_kohonen\|run_hopfield\|run_oja' neuron/models/models.c` prints 3.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `.venv` and `datos/prepared/` missing in the worktree**
- **Found during:** start of Task 1
- **Issue:** both are not versioned, so the worktree had neither.
- **Fix:** ran `make venv` (pins already approved in plan 01-02, no new package) and `.venv/bin/python scripts/prepare_creadores.py`. Nothing tracked changed.

**2. [Rule 2 - Consistency] Updated the header comment in `io/config.h` and the smoke row in `analysis/README.md`**
- **Found during:** Task 1
- **Issue:** `config.h` still said "oja here; kohonen and hopfield come with plan 01-05", and the README row for `series_smoke_oja` named the fixture the oja example no longer reads (flagged in the executor notes).
- **Fix:** both texts now match the code.
- **Commit:** `2787545`

The Hopfield registry rows (`HOPFIELD_KEYS`, `run_hopfield` declaration and table entry) were added in Task 2 rather than Task 1, so that each task commit builds on its own.

## Authentication Gates

None.

## Known Stubs

All three runners are intentional stubs, as the plan states; each is replaced by its phase without changing dispatch, config tables or file names:

- `TP4/neuron/models/kohonen_stub.c` (no training, no neighbourhood): replaced in Phase 2.
- `TP4/neuron/models/oja_stub.c` (random unit vector, not Oja's rule): replaced in Phase 3.
- `TP4/neuron/models/hopfield_stub.c` (no weights, no recall; only noise and overlap): replaced in Phases 4 and 5.

## Threat Flags

None. T-01-11 (grid_k bounds before allocation) and T-01-12 (noise level range, +-1 check, `CONFIG_ARRAY_MAX` bound) are implemented; no new dependencies.

## Next Phase Readiness

Plan 01-07 can add the series files for kohonen and hopfield and the C test runner on top of these key tables and example configs. The hopfield example is relative to `neuron/` (`tests/fixtures/patterns_small.csv`); the oja and kohonen examples need `datos/prepared/creadores_zscore.csv`, which a fresh checkout generates with `scripts/prepare_creadores.py`.

## Self-Check: PASSED

- FOUND: TP4/neuron/models/kohonen_stub.c, TP4/neuron/models/hopfield_stub.c
- FOUND: TP4/neuron/config.json.kohonen.example, TP4/neuron/config.json.hopfield.example, TP4/neuron/tests/fixtures/patterns_small.csv
- FOUND: commits 2787545 and 1022251 on the worktree branch
