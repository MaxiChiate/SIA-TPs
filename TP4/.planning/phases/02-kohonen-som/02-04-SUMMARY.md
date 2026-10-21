---
phase: 02-kohonen-som
plan: 04
subsystem: analysis
tags: [som, stage-driver, pre-registration, git-guard, loo, stability, robustness, pytest]

requires:
  - phase: 02-kohonen-som
    provides: "02-03 rule commit ea7a0b1 (rule text, som_select.py, stage-1 series); 02-01 Kohonen C core; 02-02 som.py stability/medoid and som_loo.run_loo"
provides:
  - "analysis/som_stage.py: guarded stage driver (run_stage, rule_identity, require_same_rule, write_stage2, main) and make som-stage1 / som-stage2"
  - "Stage-1 results under analysis/results/som/series_som_stage1/ (aggregate, loo, loo_by_seed, stability, stage, selection.json); chosen grid k = 5"
  - "analysis/series_som_stage2.json generated for k = 5 and committed before stage 2 ran"
  - "Stage-2 results under analysis/results/som/series_som_stage2/ (robustness.csv/json); verdict: no robusta"
  - "deliverables/02-kohonen.md sections 3 (stage 1, chosen grid) and 4 (stage 2, robustness)"
affects: [02-05, 02-06]

actuals:
  tokens: 9100
  tasks: 3
  commits: 4
plan_head_before: d891fb2ba5cd4328c4411c9c2d2f956e654995b1
plan_head_after: 56a5b2ea0de3faec878af651f2fa867f2dcda662
commits: 4

tech-stack:
  added: []
  patterns:
    - "rule_commit taken from git log --diff-filter=A of the rule file, so later commits (section 3, stage-2 series) never move it; rule_guard used only as the clean-and-tracked check"
    - "Stage output folder wiped before the sweep, so a failed re-run leaves no stale aggregate.csv or selection.json"

key-files:
  created:
    - analysis/som_stage.py
    - analysis/tests/test_som_stage.py
    - analysis/series_som_stage2.json
  modified:
    - Makefile
    - deliverables/02-kohonen.md

key-decisions:
  - "Stage 1 under the committed rule chose k = 5 (step), decided by QE-LOO: k = 4 and 5 survived the filters, k = 5 has the lowest QE-LOO, and k = 4 is more than five SDs above it so the tie band holds only k = 5"
  - "Stage 2 verdict is no robusta: occupancy filters pass in all 10 variants, TE exceeds 0,05 in five (radius0-5, eta0-0.25, eta0-0.9, epochs-50, epochs-520); k is not re-selected"
  - "Stability is reported as mean ± SD over the 45 seed pairs (selection only uses the mean)"

requirements-completed: [SOM-03]

coverage:
  - id: D1
    description: "make som-stage1 / som-stage2 refuse to run on an untracked, modified or split-committed rule, and stop on any failed run or training"
    requirement: SOM-03
    verification:
      - kind: unit
        ref: "analysis/tests/test_som_stage.py (5 passed: test_run_stage_fixture, test_run_stage_failure_stops, test_write_stage2, test_require_same_rule, test_rule_identity_guards_code)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Stage 1 ran 140 runs and 7 000 LOO trainings under the committed rule; selection.json records rule commit ea7a0b1, rule and code sha256, chosen k = 5, figure seed 4"
    requirement: SOM-03
    verification:
      - kind: other
        ref: "Task 2 STAGE1_OK command (14 aggregate rows, 7 000 loo rows, rule_commit == adding commit of rule, som_select.py and stage-1 series)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Deliverable section 3: step and gaussian tables (mean ± SD over 10 seeds), rule branches in order, chosen grid, rule commit, training-QE argmin, figure seed"
    requirement: SOM-03
    verification:
      - kind: other
        ref: "Task 2 STAGE1_OK command (four summary lines match selection.json)"
        status: pass
    human_judgment: true
    rationale: "Agreement between the prose paragraph and the tables is a reading judgment beyond the four checked lines"
  - id: D4
    description: "analysis/series_som_stage2.json equals stage2_series(5), generated and committed before stage 2 ran; section 4 reports the robustness verdict without re-selecting k"
    requirement: SOM-03
    verification:
      - kind: other
        ref: "Task 2 STAGE1_OK + STAGE2_PLAN_OK, Task 3 STAGE2_OK (verdict line matches robustness.json); make test FULL_SUITE_OK (118 C checks, 38 pytest)"
        status: pass
    human_judgment: true
    rationale: "Prose on how QE-LOO and stability move along each ladder is a judgment over the tables"

duration: 4min
completed: 2026-10-21
status: complete
---

# Phase 2 Plan 04: Pre-registered grid selection run and robustness check Summary

**A guarded driver ran the 140-run stage 1 under the committed rule (commit ea7a0b1) and chose k = 5 by QE-LOO; stage 2 on k = 5 then found the choice not robust, because TE crosses 0,05 in five of nine schedule variants while occupancy always passes.**

## Performance

- **Duration:** about 4 min (start 2026-10-21T17:50:53Z)
- **Tasks:** 3 (all auto; Task 1 TDD)
- **Files created:** 3, modified: 2
- **Stage 1:** 140 runs + 7 000 LOO trainings, about 24 s on 10 cores; **Stage 2:** 100 runs + 5 000 trainings

## Accomplishments

- **Task 1 (TDD).** `analysis/som_stage.py` with `run_stage`, `rule_identity`, `require_same_rule`, `write_stage2` and `main`; `make som-stage1` / `make som-stage2`. `rule_identity` runs `rule_guard` over the rule text, `analysis/som_select.py`, the stage-1 series and the series being run (clean-and-tracked check only), takes `rule_commit` from `git log --diff-filter=A` of the rule file, refuses unless `som_select.py` and the stage-1 series were added in that same commit, and records `select_commit` / `select_sha256`. `require_same_rule` rechecks both sha256. The real repo returns the 02-03 identity (commit `ea7a0b11...`, rule sha `d1c69242...`, code sha `b592469b...`).
- **Task 2.** `make som-stage1` wrote aggregate, loo, loo_by_seed, stability, stage and selection.json. Outcome `chosen`, k = 5 (`decided_by: qe_loo`, `te_filter_dropped: false`, `qe_train_argmin_k: 8`, figure seed 4, run `033_k5-step_seed4`). Section 3 holds the step and gaussian tables, the rule branches in order and the four summary lines. `write-stage2` produced `analysis/series_som_stage2.json` (10 variants x 10 seeds), committed before stage 2.
- **Task 3.** `make som-stage2` passed its guard and ran. Section 4 has the per-variant table, a paragraph on QE-LOO (flat, 3,288 to 3,336) and stability (0,565 to 0,693, small against the 0,15 to 0,20 pair-to-pair spread), and `- Veredicto de robustez: no robusta (radius0-5, eta0-0.25, eta0-0.9, epochs-50, epochs-520)`.

## Task Commits

1. **Task 1 RED:** `318ddbc` test(02-04): 5 failing tests (collection error, `som_stage` absent)
2. **Task 1 GREEN:** `2d7ec19` feat(02-04): `som_stage.py` + Makefile targets (5 passed)
3. **Task 2:** `7c783a2` feat(02-04): section 3 + `analysis/series_som_stage2.json`
4. **Task 3:** `56a5b2e` docs(02-04): section 4

## TDD Gate Compliance

- **RED:** `318ddbc`; `pytest` failed at collection with `ModuleNotFoundError: No module named 'som_stage'`, the intended failure for a module that did not exist (`workflow.tdd_mode` is not enabled, so `check tdd-red-evidence` was not required).
- **GREEN:** `2d7ec19`; all 5 tests pass.
- **REFACTOR:** none.

## Deviations from Plan

None - plan executed exactly as written. Small implementation choices inside the plan's latitude, not deviations:

- `rule_identity` also includes `analysis/series_som_stage1.json` in the clean-and-tracked guard when the series being run is the stage-2 one, so a modified stage-1 series stops stage 2 too.
- `run_stage` removes the stage's output folder before the sweep (not after), so a stopped re-run cannot leave an older `aggregate.csv` or `selection.json`.
- A relative series path is taken relative to TP4, the same convention as `rule_identity`.
- Stability in the tables is mean ± SD over the 45 seed pairs (computed from `stability.csv`), to keep every table cell in the mean ± SD form of D-08; the selection rule uses only the mean.

**Total deviations:** 0.

## Issues Encountered

None. No run or LOO training failed. `make test` passes (118 C checks, 38 pytest).

## Known Stubs

None.

## Threat Flags

None. The only new surface is the stage driver's git calls (argument lists, fixed paths, cwd set, no shell), covered by T-02-09 and T-02-10.

## Handoff to later plans

- 02-05 and 02-06 may read `analysis/results/som/series_som_stage1/selection.json`: chosen k = 5, label `k5-step`, figure seed 4, figure run `analysis/results/series_som_stage1_2026-10-21_14-52-22/runs/033_k5-step_seed4`, rule commit `ea7a0b11202d19bb2ffed71a0e43a58bdd6f3d00`. `require_same_rule(selection.json, RULE_FILE)` still passes (rule and code unchanged).
- Honest limits of the chosen grid, stated in section 3: stability of k = 5 (0,672) is below k = 4 (0,791) but the rule does not use it outside the tie band; TE passes by a small margin (0,046 ± 0,034, 3 of 10 seeds above 0,05).
- `analysis/results/` is gitignored; the sweep folders exist only locally and are regenerated by `make som-stage1` / `make som-stage2`.

## Self-Check: PASSED

- FOUND: `analysis/som_stage.py`, `analysis/tests/test_som_stage.py`, `analysis/series_som_stage2.json`, `deliverables/02-kohonen.md`, `selection.json`, `robustness.json`
- FOUND commits `318ddbc`, `2d7ec19`, `7c783a2`, `56a5b2e` (ancestors of HEAD); `git rev-list --count d891fb2..HEAD` = 4
- `pytest analysis/tests/test_som_stage.py`: 5 passed; STAGE1_OK, STAGE2_PLAN_OK, STAGE2_OK and FULL_SUITE_OK printed; selection.json `rule_sha256` equals the current `rule_digest`
