---
phase: 01-fundaci-n-auditor-a-de-datos-y-pca
plan: 07
subsystem: infra
tags: [make, sweep, c-tests, sanitizers, pytest, readme]

requires:
  - phase: 01-01
    provides: "C skeleton: strict KeySpec config, matrix loader, results writer, dispatch table"
  - phase: 01-02
    provides: "root Makefile with venv and prepare, pinned .venv"
  - phase: 01-03
    provides: "analysis/sweep.py"
  - phase: 01-04
    provides: "pytest suite (5 tests) and datos/prepared/ generator"
  - phase: 01-05
    provides: "kohonen and hopfield stubs, example configs, fixtures"
provides:
  - "series_smoke_kohonen.json (grid_k 2,3,4 x 3 seeds) and series_smoke_hopfield.json (two noise_levels variants x 2 seeds)"
  - "Root Makefile: default goal all (prepare + build), sweep SERIES=..., test, clean"
  - "neuron/tests/test_main.c with 3 tests; neuron/Makefile targets test-c, test, debug (ASan + UBSan)"
  - "neuron/README.md: config keys per model, run directory layout, reproducibility rule, stub outputs, extension points"
affects: [01-08, phase-02, phase-03, phase-04, phase-05]

actuals:
  tokens: 5500     # chars/4 over the 5 new files plus the Makefile and README edits (about 22000 chars)
  tasks: 2
  commits: 2
plan_head_before: a33180a39df1f4c9aa18499ca0b5046d189aa539
plan_head_after: a6a403305ecbdb748ada55f19f4cd71aa0aedd37

tech-stack:
  added: []
  patterns:
    - "Every root target that reads datos/prepared/ (all, sweep, test) depends on prepare; neuron/ regenerates it through $(MAKE) -C .. prepare only when the file is missing"
    - "C tests write only under build/test_tmp and clear it at start and end; expected-failure configs run with stderr sent to /dev/null"
    - "make debug re-invokes make with BUILD_DIR=build/debug and sanitizer CFLAGS, so the sanitizer flags reach compile and link"

key-files:
  created:
    - TP4/analysis/series_smoke_kohonen.json
    - TP4/analysis/series_smoke_hopfield.json
    - TP4/neuron/tests/test_main.c
    - TP4/neuron/README.md
  modified:
    - TP4/Makefile
    - TP4/neuron/Makefile
    - TP4/analysis/README.md

key-decisions:
  - "The seed-dependence check (seed + 1 changes a CSV) covers oja (weights.csv) and kohonen (prototypes.csv) only; the hopfield stub is exempt because its CSVs cannot depend on the seed"
  - "make debug compiles the vendored cJSON with -Wno-deprecated-declarations (clang emits 6 sprintf deprecation warnings), as noted for this plan"

patterns-established:
  - "make test is the gate for later phases: 3 C tests + 5 pytest, runnable from TP4/ or neuron/, on a fresh clone"
  - "A new series file per model, with the varied key as the column right after status"

requirements-completed: [INFRA-03, INFRA-04]

status: complete
duration: 25min
completed: 2026-10-20
---

# Phase 01 Plan 07: Series per model, make test gate and sanitizer build Summary

**From the TP4 root, a bare `make` regenerates the ignored `datos/prepared/`, builds the single binary, `make sweep SERIES=...` runs a series for any of the three models with its varied key as a column, and `make test` runs 3 C tests plus the 5 pytest tests (also under ASan/UBSan with `make -C neuron debug`).**

## Performance

- **Duration:** about 25 min
- **Tasks:** 2
- **Files created:** 4, modified: 3

## Accomplishments

- `series_smoke_kohonen.json` gives 9 ok runs with the header `run,variant,label,seed,status,grid_k,...`; `series_smoke_hopfield.json` gives 4 ok runs with `noise_levels` (JSON-encoded list) right after `status`; `series_smoke_oja.json` still gives 3 runs with `n_samples` 50 on the audited data. `analysis/README.md` lists both new series and the `make sweep` form.
- Root `Makefile`: `.DEFAULT_GOAL := all`; `all`, `sweep` and `test` depend on `prepare`; `clean` delegates to `neuron/`. Started with `datos/prepared` deleted, a bare `make` regenerates `creadores_zscore.csv` and builds `neuron/build/neuron`.
- `neuron/tests/test_main.c` (63 checks): `config strict validation` (3 valid configs, 13 invalid ones, nested `KEY_OBJECT` table, dotted `a.k`), `same seed, same bytes` (oja, kohonen, hopfield byte-for-byte over every file in the run directory, `rng_new(7)` stream, fixture load with no trailing newline) and `dispatch by model`. The runner uses TP3's `check` / `check_close` macros, `tests[]` table, `ok  ` / `FAIL` lines and `N checks, M failed` summary.
- `neuron/Makefile`: `test-c`, `test` (C then `$(PY) -m pytest ../analysis/tests -q`), `debug`, and the `$(PREPARED)` file rule that runs `$(MAKE) -C .. prepare` only when the CSV is missing.
- `neuron/README.md` in Spanish documents build and run, the non-versioned prepared input, tests, common and per-model keys, the run directory layout, the `diff -r` reproducibility rule, the files and metrics of each stub, and how to add a key, replace a stub body or add a model.

## Task Commits

1. **Task 1: series per model, root all / sweep / clean** - `c1dc41f` (feat)
2. **Task 2: make test, C runner, debug target, neuron README** - `a6a4033` (feat)

## Verification

- Task 1 automated check printed `SERIES_OK` starting with `datos/prepared` deleted.
- `make -C neuron test-c`: 3 `ok  ` lines, `63 checks, 0 failed` (`CTEST_OK`).
- `make -C neuron debug`: same 63 checks, no `runtime error`, `AddressSanitizer` or `LeakSanitizer` in the output (`DEBUG_OK`).
- `make test` at TP4/ and `make -C neuron test`, each started with `datos/prepared` deleted: C summary `0 failed`, pytest `5 passed`, `datos/prepared/creadores_zscore.csv` regenerated (`MAKE_TEST_OK`, `NEURON_TEST_OK`).
- `make clean` removes `neuron/build`; a following `make` rebuilds it. `neuron/build/test_tmp` is empty after the tests.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `.venv` and `datos/prepared/` missing in the worktree**
- **Found during:** start of Task 1
- **Issue:** both are not versioned, so the worktree had neither.
- **Fix:** `make venv` and `make prepare` (pins already approved in plan 01-02, no new package). Nothing tracked changed.

**2. [Rule 1 - Plan assumption] Hopfield stub cannot show a seed-dependent CSV**
- **Found during:** Task 2, designing `same seed, same bytes`
- **Issue:** the plan asks that a third run with seed + 1 writes a different CSV for each model. The hopfield stub flips `lround(level * n)` pixels, and `overlap = (n - 2k) / n` depends only on that count, so `queries.csv` and `metrics.json` are identical for every seed; the check would always fail.
- **Fix:** the seed + 1 check applies to oja (`weights.csv`) and kohonen (`prototypes.csv`); hopfield keeps the identical-bytes check and the test comment says why. The Hopfield phases (4 and 5) add output that does depend on the seed and should add the check then.
- **Files modified:** `TP4/neuron/tests/test_main.c`
- **Commit:** `a6a4033`

**3. [Rule 3 - Blocking] cJSON deprecation warnings in the sanitizer build**
- **Issue:** clang emits 6 `sprintf` deprecation warnings on the vendored cJSON.
- **Fix:** `VENDOR_CFLAGS` in `make debug` carries `-Wno-deprecated-declarations`, as the executor notes required. The normal build is unchanged.
- **Commit:** `a6a4033`

### Notes

- The plan's check `ls neuron/build/test_tmp | wc -l` can print a nonzero number on this machine because `ls` is aliased to `colorls` in the user's shell; `/bin/ls -A` shows the directory empty.
- `SERIES` for `make sweep` is run with `$(PY)` (the `.venv` python), although `sweep.py` itself needs only the standard library.

## Authentication Gates

None.

## Known Stubs

No new stubs. The three model runners remain the Phase 1 stubs listed in 01-05-SUMMARY.md (kohonen replaced in Phase 2, oja in Phase 3, hopfield in Phases 4 and 5). The series files and the C tests are written against the stub outputs and extend naturally when those phases keep the file names.

## Threat Flags

None. T-01-13: `make -C neuron debug` runs the whole C suite under AddressSanitizer and UndefinedBehaviorSanitizer with no report. T-01-14: the tests write only under `build/test_tmp` (ignored through `build/`) and remove it. T-01-SC: no downloads or installs beyond the pins approved in plan 01-02.

## Next Phase Readiness

`make test` is the gate for plan 01-08 and later phases; new keys go as rows in `io/config.c` plus a case in `config strict validation`, and new series copy the two series files here.

## Self-Check: PASSED

- FOUND: TP4/analysis/series_smoke_kohonen.json, TP4/analysis/series_smoke_hopfield.json, TP4/neuron/tests/test_main.c, TP4/neuron/README.md
- FOUND: commits c1dc41f and a6a4033 on the worktree branch
