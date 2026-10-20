---
phase: 01-fundaci-n-auditor-a-de-datos-y-pca
plan: 04
subsystem: data
tags: [python, numpy, csv, zscore, scaler, audit, pytest]

requires:
  - phase: 01-02
    provides: "pinned .venv with numpy and pytest"
provides:
  - "scripts/creadores.py: loader with 50x33 check, exact dependency check, audit rule, scaler fit/transform/inverse, meta read/write, new-creator mapping"
  - "scripts/prepare_creadores.py: one command that writes the audited 26-variable and the all31 sensitivity z-scored matrices with their meta files into datos/prepared/"
  - "scripts/map_creator.py: maps raw creator rows into the saved z-score space using only a meta file"
  - "analysis/tests/conftest.py and test_creadores.py: 5 pytest tests"
affects: [01-05, 01-06, 01-07, 01-08, phase-02, phase-03]

actuals:
  tokens: 5047     # chars/4 over the 6 files written (20188 chars)
  tasks: 2
  commits: 2
plan_head_before: a6a346ff5d92a766d65f91ce9e26d7433c38f223
plan_head_after: ede14259bc1a01a652b3e5ab3d634c4815b9cd68

tech-stack:
  added: []
  patterns:
    - "Prepared inputs are generated, deterministic and not versioned (datos/.gitignore holds prepared/)"
    - "Every prepared file is written to a temp name in the same folder and moved with os.replace, so a concurrent reader never sees a half-written file"
    - "Python writes values with repr(float) so C strtod reads the exact double; no timestamp and no absolute path inside any prepared file"
    - "csv stdlib + numpy only, no dataframe library (D-06)"

key-files:
  created:
    - TP4/scripts/creadores.py
    - TP4/scripts/prepare_creadores.py
    - TP4/scripts/map_creator.py
    - TP4/analysis/tests/conftest.py
    - TP4/analysis/tests/test_creadores.py
    - TP4/datos/.gitignore
  modified: []

key-decisions:
  - "The audit rule drops exactly price_ars, organic_posts_pct, total_engagement_per_1000, topic_art_pct and content_showcase_pct; the group members are chosen by lowest ddof=1 variance in original units, re-derived from the data on every run, never hard-coded"
  - "audit_variables stops with a ValueError naming the relation if any of the 5 dependencies exceeds 1e-6, so the rule cannot silently apply to data where a dependency stopped being exact"
  - "Near-redundant variables (estimated_argentina_reach, |r| > 0.9 partners of followers) are kept, as D-10 states"
  - "map_creator.py and prepare_creadores.py share one CSV formatter (zscore_csv_text) and one transform, which is why mapping datos/creadores.csv reproduces creadores_zscore.csv byte for byte"

patterns-established:
  - "creadores.prepare(source, out_dir) is the single code path for generating the prepared files; the CLI and the pytest session fixture both call it"

requirements-completed: [DATA-01, DATA-02, DATA-03, DATA-05]

status: complete
duration: 15min
completed: 2026-10-20
---

# Phase 01 Plan 04: Audited z-scored creadores matrix and saved scaler Summary

**One command (`scripts/prepare_creadores.py`) turns datos/creadores.csv into the audited 26-variable z-scored matrix plus the labelled 31-column sensitivity matrix, each with a `.meta.json` scaler, and `scripts/map_creator.py` maps new creators with that scaler alone.**

## Performance

- **Duration:** about 15 min
- **Tasks:** 2 (both TDD: tests written and seen failing first)
- **Files created:** 6 (plus 4 generated, not versioned, files in datos/prepared/)

## Accomplishments

- Loader reads with the `csv` module and fails with a `ValueError` naming "50" and "33" when the file is not 50 rows by 33 columns; ragged rows and non-numeric or non-finite cells are reported with line, column and raw text (DATA-01, T-01-07).
- Audit: 26 variables kept in original column order; 5 dropped (`price_ars`, `organic_posts_pct`, `total_engagement_per_1000`, `topic_art_pct`, `content_showcase_pct`), each with a Spanish reason and a reconstruction formula, stored in the meta file (DATA-02, code half).
- Audited matrix has rank 26 and smallest correlation eigenvalue above 1e-5; the 31-column matrix has exactly 5 correlation eigenvalues below 1e-10 and 26 above 1e-5 (DATA-05, data half).
- Meta keys in the order `variant, note, source, n_rows, ddof, features, mean, std, dropped, creator_id, name`; `source` is the relative `datos/creadores.csv`, ddof 1, no log and no winsorizing.
- `map_creator.py --meta ... --input datos/creadores.csv` is byte-identical to `datos/prepared/creadores_zscore.csv` (DATA-03).
- Reruns reproduce identical sha256 for all four prepared files, starting from a missing `datos/prepared/`.

## Task Commits

1. **Task 1: audited z-scored matrix and 31-column sensitivity matrix with saved scaler** - `5100ab0` (feat)
2. **Task 2: new creator mapped with the saved scaler alone** - `ede1425` (feat)

## Verification

- Two consecutive `prepare_creadores.py` runs (the first from a missing folder) give identical sha256; `ls -A datos/prepared` shows exactly 4 files and no leftover temp file; `git check-ignore` confirms the CSV is ignored and `git ls-files datos/prepared` prints nothing: `PREPARE_OK` condition met.
- Headers: 26 columns audited (none of the 5 dropped names), 31 in all31, 50 data rows; meta contains `"variant": "audited"`, `"ddof": 1`, `"source": "datos/creadores.csv"`; all31 meta contains `SENSIBILIDAD`; no absolute path in `datos/prepared`; no `import pandas` in scripts or analysis.
- `map_creator.py` output vs `creadores_zscore.csv`: `cmp` clean (`MAP_OK`); `--help` lists `--meta`, `--input`, `--out`.
- `.venv/bin/python -m pytest analysis/tests -q`: 3 passed after Task 1, 5 passed after Task 2; `grep -c '^def test_'` prints 5.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `.venv` missing in the worktree**
- **Found during:** start of Task 1
- **Issue:** the worktree has no `.venv` (not versioned).
- **Fix:** ran `make venv` from plan 01-02 (the pins were already approved by the user there); no new package was introduced.
- **Files modified:** none tracked.

**2. [Rule 2 - Robustness] Added `prepare()` to the library and a session fixture in the tests**
- **Found during:** Task 1
- **Issue:** the plan's tests read `datos/prepared/`, which is generated and not versioned, so a fresh clone running `pytest` before `prepare_creadores.py` would fail on missing files.
- **Fix:** `creadores.prepare(source, out_dir)` holds the one code path used by the CLI; the `prepared` pytest fixture calls it only when one of the four files is missing. The plan's export list is a subset of what the module exposes (extra helpers: `prepare`, `zscore_csv_text`, `_atomic_write`).
- **Commit:** `5100ab0`

No other deviations; the audit numbers match the planning measurements (topic_art_pct and content_showcase_pct lowest variance, 26 kept).

## Authentication Gates

None.

## Known Stubs

None.

## Threat Flags

None. The mitigations assigned to this plan are in place: T-01-07 (csv parsing, 50x33 check, named errors), T-01-08 (deterministic outputs, no timestamps, relative source), T-01-10 (named KeyError, scaler only, no refit).

## Next Phase Readiness

Plans 01-05 to 01-08 can read `datos/prepared/creadores_zscore.csv` and `.meta.json` (and the all31 pair) and import `creadores` through the `conftest.py` path setup. Each root Makefile target that reads those files must depend on a `prepare` target running `.venv/bin/python scripts/prepare_creadores.py` (plan 01-06 onward), because the folder is not versioned.

## Self-Check: PASSED

- FOUND: TP4/scripts/creadores.py, TP4/scripts/prepare_creadores.py, TP4/scripts/map_creator.py
- FOUND: TP4/analysis/tests/conftest.py, TP4/analysis/tests/test_creadores.py, TP4/datos/.gitignore
- FOUND: commits 5100ab0 and ede1425 on the worktree branch
