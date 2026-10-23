---
phase: 03-oja-y-decisiones-de-campa-a
plan: 03
subsystem: analysis
tags: [python, numpy, oja, pca, convergence, matplotlib]

requires:
  - phase: 01-datos-y-pca
    provides: "analysis/results/pca/audited (eigenvectors.csv, scores.csv) from make pca, the PCA orientation, pca._pearson and dominant_topics, plots_style"
  - phase: 03-oja-y-decisiones-de-campa-a
    provides: "plan 03-01: the Oja binary and its run files (weights.csv, index.csv, trace.csv, metrics.json); plan 03-02: the committed campaign rule (so no Oja result existed before it, D-07)"
provides:
  - "analysis/oja.py and `make oja`: 10-seed Oja series through sweep.py, read as C wrote it, compared with PC1 in Python"
  - "analysis/results/oja/: runs.json, comparison.json, seeds.csv, index.csv (figure seed 1, D-02 sign), weights.csv, dispersion.json, convergence.csv, report_pc1.md, report_convergence.md, convergence.svg/png"
  - "The pivot margin of the D-02 convention (0,00275 between average_caption_words and average_impressions)"
affects: [03-04, 03-05, 03-06]

actuals:
  tokens: 8000
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "A reader of the C run files that refuses on any header or row-count mismatch naming the file (T-03-07), like som.read_run"
    - "Report files made only of table rows and bullets with comma decimals, so a later plan pastes them verbatim into the deliverable"

key-files:
  created:
    - analysis/oja.py
    - analysis/series_oja.json
    - analysis/tests/test_oja.py
  modified:
    - Makefile

key-decisions:
  - "Python never re-orients a run: every seed is read with the D-02 sign C applied and is checked, not flipped; all 10 seeds came out with w . v1 > 0 and pivot average_caption_words"
  - "The comparison table keeps the planned 6 decimals, which prints 1,000000 for abs(cos); the precision lives in dispersion.json and in the worst-seed line of report_convergence.md (1 - abs(cos) = 2,5e-07)"
  - "The pivot margin is printed with 5 decimals (0,00275) because the rounded 4-decimal coefficients would suggest 0,0028"

patterns-established:
  - "Figure with 10 seeds: thin TEXT_SECONDARY lines plus the figure seed in palette slot 1, never palette_for with 10 names"

requirements-completed: [OJA-01, OJA-02]

coverage:
  - id: D1
    description: "make oja runs the 10-seed Oja series and compares the figure seed with PC1: abs(cos) 0,9999998, same orientation, Pearson 0,99999998, Spearman 1, overlap@5 5 of 5 and overlap@10 10 of 10, max abs difference 2,0e-03"
    requirement: OJA-02
    verification:
      - kind: integration
        ref: "make oja; comparison.json asserted abs_cos > 0.99 and cos > 0, 10 seeds, index.csv ranks 1..50 -> OJA_PC1_OK"
        status: pass
      - kind: unit
        ref: "analysis/tests/test_oja.py#test_smoke_run_matches_pc1"
        status: pass
    human_judgment: false
  - id: D2
    description: "The D-05 pytest on the real z-scored data: abs(cos(w, v1)) > 0.99 with the PCA orientation, length 1, index = Z w, epochs + 1 trace rows, pivot equal to the PCA pivot; and every input column centered"
    requirement: OJA-02
    verification:
      - kind: unit
        ref: "analysis/tests/test_oja.py#test_smoke_run_matches_pc1 and #test_input_is_centered"
        status: pass
    human_judgment: false
  - id: D3
    description: "Seed dispersion: 10 of 10 seeds above 0.99 with the PCA orientation and the single pivot average_caption_words; pairwise abs(cos) between seeds at least 0,9999993; per-creator index range at most 3,1e-03"
    requirement: OJA-01
    verification:
      - kind: integration
        ref: "dispersion.json asserted in the Task 2 verify -> OJA_CONVERGENCE_OK"
        status: pass
    human_judgment: false
  - id: D4
    description: "Per-epoch convergence for 10 seeds (abs(cos(w_e, v1)) computed in Python from trace.csv, C's w_norm and delta_w), the convergence figure, and the pivot margin of the D-02 convention"
    requirement: OJA-01
    verification:
      - kind: unit
        ref: "analysis/tests/test_oja.py#test_convergence_abs_cos_normalizes"
        status: pass
      - kind: integration
        ref: "convergence.csv has 10 x 501 rows; two consecutive make oja give identical hashes except runs.json"
        status: pass
    human_judgment: false
  - id: D5
    description: "report_pc1.md (table plus four seed bullets) and report_convergence.md hold only table rows and bullets with comma decimals, ready to paste into sections 1 and 2 of the deliverable"
    requirement: OJA-02
    verification:
      - kind: integration
        ref: "line-type assertion in the Task 2 verify -> OJA_CONVERGENCE_OK"
        status: pass
    human_judgment: true
    rationale: "Whether the Spanish wording of the bullets reads well in the deliverable is a judgment for the user and for plan 03-04, which pastes them"

duration: 8min
completed: 2026-10-22
status: complete

plan_head_before: 434679fa4e5a845548ca3c08960b88e480148c3f
plan_head_after: 9a58194475d9da16e8de8f0833f780ff9f43e926
---

# Phase 3 Plan 03: Oja against PC1 Summary

**`make oja` runs the 10-seed Oja series through the C binary and shows in Python that the neuron learns PC1 with the PCA orientation in every seed (abs(cos) 0,9999993 or better, same pivot), with per-epoch convergence from trace.csv, a convergence figure, and the 0,00275 pivot margin that bounds the D-02 sign convention**

## Performance

- **Duration:** about 8 min (the start time was not captured; estimated from the previous plan's close)
- **Completed:** 2026-10-22T14:29:18Z
- **Tasks:** 2 (the first a tracer)
- **Files modified:** 4 (3 created, 1 modified)

## Accomplishments

- `analysis/oja.py` reads each run folder as C wrote it (`read_oja_run`, refuses on header or row-count mismatch naming the file), reads PC1 from `make pca` (`read_pca`, refuses naming `make pca`), and compares the figure seed with PC1: abs(cos) 0,9999998, signed cos positive, Pearson 0,99999998, Spearman 1,0000, overlap@5 5 de 5, overlap@10 10 de 10, largest abs(index - PC1 score) 2,0e-03.
- Dispersion over seeds 1 to 10 (D-03): 10 de 10 above 0,99 and with the PCA orientation, one pivot (`average_caption_words`), minimum pairwise abs(cos) 0,9999993, per-creator index range at most 3,1e-03 (mean 1,5e-03), worst seed 6 with 1 - abs(cos) = 2,5e-07.
- Convergence (D-01): abs(cos(w_e, v1)) is computed in Python per seed and epoch from the weights in trace.csv, next to C's w_norm and delta_w; seed 1 passes 1 - abs(cos) < 1e-3 at epoch 8; the figure has three panels (1 - abs(cos) on a log axis, abs(w) before renormalizing, delta w on a log axis).
- Pivot margin written to dispersion.json and report_convergence.md: average_caption_words +0,2521 against average_impressions -0,2493, margin 0,00275, the limit of the D-02 convention (a different dataset could flip the pivot and with it the sign of w and the index).
- Two consecutive `make oja` give identical hashes for every CSV, JSON, MD and SVG except runs.json; `deliverables/03-oja-campanas.md` and the rule files are untouched.

## Task Commits

1. **Task 1: end-to-end `make oja` (tracer)**
   - RED `109bef4` (test): five tests. The module `oja` did not exist, so the red run was a collection `ModuleNotFoundError` for the whole file; this is the intended reason (every target test names a symbol that does not exist yet), but it is not an assertion-level failure, and `test_input_is_centered` could not be shown red on its own because it asserts a property of the data, not new behavior.
   - GREEN `62ee5b9` (feat): `analysis/series_oja.json`, `analysis/oja.py`, the `oja` Makefile target; the five tests pass and `make oja` writes the six files.
2. **Task 2: dispersion, convergence, pivot margin, figure and reports**
   - RED `cf9184d` (test): `test_convergence_abs_cos_normalizes` failed with `AttributeError: module 'oja' has no attribute 'convergence_rows'` (1 failed, 5 passed).
   - GREEN `9a58194` (feat): `dispersion`, `convergence_rows`, `pivot_margin`, `plot_convergence` and the report bullets; six tests pass.

**Plan metadata:** the docs commit that holds this SUMMARY, STATE.md and ROADMAP.md follows.

No REFACTOR commit: no cleanup was warranted.

## Files Created/Modified

- `analysis/oja.py` - run reader, PCA reader, comparison, seed dispersion, convergence, pivot margin, figure, report writers, CLI
- `analysis/series_oja.json` - the 10-seed series over `neuron/config.json.oja.example`
- `analysis/tests/test_oja.py` - six tests (centered input, D-05 smoke run, compare, top-k and overlap, reader contract, convergence)
- `Makefile` - target `oja: pca` and `oja` in `.PHONY`

## Decisions Made

- No re-orientation in Python (prohibition D-02/D-05): `cos` is reported signed and `n_same_orientation` counts the seeds with w . v1 > 0; all 10 pass on their own.
- The planned 6-decimal table prints `1,000000` for abs(cos) because the true value is 0,9999998; the detail is in comparison.json and in the `1 - abs(cos)` bullet. Kept as planned instead of changing the precision that plan 03-04 expects.
- The margin line uses 5 decimals so it does not contradict the 4-decimal coefficients printed beside it.

## Deviations from Plan

**Commit policy (orchestrator override, not a plan deviation).** The plan text says not to stage or commit and to leave commits to the user; the orchestrator's explicit instruction for this run was that the executor commits. Four task commits (TDD red and green for each task) were made, staging files by explicit path, never `.planning/milestone.lock`. The plan's acceptance criterion `git diff --cached --quiet` was checked before each staging step and held.

Otherwise none - plan executed exactly as written.

**Total deviations:** 0 auto-fixed.

## Issues Encountered

None. `make test` in neuron/ was not used (the known unquoted `$(PY)` space issue); pytest was run as `.venv/bin/python -m pytest analysis/tests -q` (71 passed). Each `make oja` adds a timestamped `analysis/results/series_oja_*` sweep folder (gitignored); runs.json names the latest.

## Known Stubs

None.

## Threat Flags

None - no new surface beyond the plan's threat register: T-03-07 (header, sample numbering and row-count checks, feature-order and creator-order refusals), T-03-08 (signed cos and pivot checked for all 10 seeds, margin reported, no re-orientation), T-03-09 (argument-list subprocesses through sweep.py).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 03-04 can paste `report_pc1.md` and `report_convergence.md` verbatim into sections 1 and 2, and read `index.csv` (figure seed 1, D-02 sign) for the D-06 evidence; `weights.csv` is ready for the maintenance demo of plan 03-06.
- Concern to carry into the write-up: the pivot margin is only 0,00275, so the sign convention is stable on these data but fragile in general.

---
*Phase: 03-oja-y-decisiones-de-campa-a*
*Completed: 2026-10-22*

## Self-Check: PASSED

- Files exist: `analysis/oja.py`, `analysis/series_oja.json`, `analysis/tests/test_oja.py`, and the 11 outputs under `analysis/results/oja/`
- Commits are ancestors of HEAD: `109bef4`, `62ee5b9`, `cf9184d`, `9a58194`; `git rev-list --count 434679f..HEAD` is 4
- `pytest analysis/tests` 71 passed, `test_oja.py` 6 passed; `make oja` twice with identical hashes except runs.json; OJA_PC1_OK and OJA_CONVERGENCE_OK printed; `git diff --quiet -- deliverables/03-oja-campanas.md` exits 0
