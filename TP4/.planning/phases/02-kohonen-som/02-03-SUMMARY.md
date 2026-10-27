---
phase: 02-kohonen-som
plan: 03
subsystem: analysis
tags: [som, grid-selection, pre-registration, numpy, pytest, git-guard]

requires:
  - phase: 01-fundaci-n-auditor-a-de-datos-y-pca
    provides: "sweep.py series/variants support, pca.py module style, deliverables/01-datos-pca.md section 5 format"
provides:
  - "deliverables/02-kohonen.md sections 1 and 2: the SOM algorithm and the grid-selection rule between <!-- regla:inicio --> / <!-- regla:fin -->"
  - "analysis/som_select.py: aggregate, passes_filters, select_grid (chosen | no_eligible_grid), rule_digest, rule_guard, radius0_ladder, stage2_series"
  - "analysis/series_som_stage1.json: 14 variants x 10 seeds = 140 runs"
  - "One rule commit (ea7a0b1) holding rule text, rule code and stage-1 series, made before any trained SOM exists"
affects: [02-01, 02-02, 02-04, 02-05, 02-06]

actuals:
  tokens: 9400
  tasks: 3
  commits: 2
plan_head_before: accf7bed364fcfa1fb733a15a946b81290408fce
plan_head_after: ea7a0b11202d19bb2ffed71a0e43a58bdd6f3d00
commits: 2

tech-stack:
  added: []
  patterns:
    - "Pre-registered rule as three files in one commit, guarded by git status and a sha256 of the text between markers"
    - "Pure select_grid over aggregated dict rows; no fallback switch, two outcomes only"

key-files:
  created:
    - analysis/som_select.py
    - analysis/tests/test_som_select.py
    - analysis/series_som_stage1.json
    - deliverables/02-kohonen.md
  modified: []

key-decisions:
  - "Task 1 answer was approve: terms 1-10 are committed exactly as written in the plan, with no edited terms"
  - "select_grid has exactly two outcomes, chosen and no_eligible_grid; occupancy is never relaxed (D-14), the rule text carries 'La ocupación no se relaja nunca.'"
  - "Rule commit ea7a0b1 adds som_select.py, the stage-1 series and the rule text together; rule_digest of the section is d1c69242551cca987d7fab1b496ec6382c587a216e2ea074bea8c50e9e55bb37 and sha256 of som_select.py is b592469bc4ae0786b4d65d7b0a0161a8d4e365951247cec403c8d728a689954d"

patterns-established:
  - "Marker-delimited rule section hashed with rule_digest; rule_guard refuses untracked or modified rule files (argument-list git calls, no shell)"

requirements-completed: [SOM-03]

coverage:
  - id: D1
    description: "Grid-selection rule written in Spanish between markers in deliverables/02-kohonen.md, with every open term pinned"
    requirement: SOM-03
    verification:
      - kind: other
        ref: "Task 3 RULE_DOC_OK command (markers, 17 bold labels, 0,05 / 20 % / 31,25 / 1040, D-14 sentence, rule_digest 64-hex)"
        status: pass
    human_judgment: true
    rationale: "Faithfulness of the prose to D-10..D-15 and to the approved terms is a judgment over meaning; a string check cannot confirm it"
  - id: D2
    description: "select_grid, aggregate, rule_digest, rule_guard and stage2_series as pure tested code"
    requirement: SOM-03
    verification:
      - kind: unit
        ref: "analysis/tests/test_som_select.py (13 passed)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Stage-1 series resolving to 14 variants x 10 seeds = 140 runs with explicit Kohonen keys"
    requirement: SOM-03
    verification:
      - kind: unit
        ref: "analysis/tests/test_som_select.py#test_stage1_series_shape"
        status: pass
      - kind: other
        ref: "python3 analysis/sweep.py analysis/series_som_stage1.json --dry-run (DRYRUN_OK)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Rule text, rule code and stage-1 series share one commit made before any trained SOM exists"
    requirement: SOM-03
    verification:
      - kind: other
        ref: "SAME_RULE_COMMIT_OK check of Task 3 (ea7a0b1); git ls-files shows neuron/models/kohonen_stub.c and no kohonen.c"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-10-21
status: complete
---

# Phase 2 Plan 03: Grid-selection rule fixed before the SOM runs Summary

**The Kohonen grid-selection rule (filters TE <= 0,05 / <= 20 % empty / >= 2 creators per occupied neuron, lowest QE-LOO, 1-SD stability tie band, no grid when occupancy leaves nothing) is committed as Spanish text, as the pure function `select_grid` and as a 140-run stage-1 series in one commit, before any trained SOM exists.**

## Performance

- **Duration:** about 25 min (continuation run, Task 1 was resolved by the user beforehand)
- **Completed:** 2026-10-21
- **Tasks:** 3 (1 decision checkpoint, 2 auto)
- **Files created:** 4

## Accomplishments

- **Task 1 (checkpoint:decision), answer "approve".** Terms 1-10 went into the committed rule exactly as written in the plan, with no edited terms. No edit contradicts D-01..D-15, and none relaxes the occupancy filters.
- **Task 2 (TDD).** `analysis/som_select.py` encodes D-11..D-14: `aggregate` (per-seed ratios, ddof 1 SDs, failed runs and missing LOO raise ValueError), `passes_filters`, `select_grid` (step rows only, gaussian reported, training-QE argmin reported, outcomes `chosen` and `no_eligible_grid` only), `rule_digest`, `rule_guard`, `radius0_ladder` and `stage2_series`. Twelve tests cover each branch, including equality at the three thresholds, the tie band with a strict `<`, equal stability going to the smaller k, TE-only relaxation and the no-eligible case.
- **Task 3.** `deliverables/02-kohonen.md` (section 1 algorithm and outputs, written from the 02-01 plan text and D-01..D-05, citing slide pages 15 and 26 for the `<` versus `<=` choice; section 2 the rule between the markers with the 17 bold-labelled bullets), `analysis/series_som_stage1.json` (14 variants, seeds 1..10) and `test_stage1_series_shape` (13th test).
- **Rule commit.** `ea7a0b1` adds the rule text, `som_select.py` and the stage-1 series together; `rule_guard` on the three files returns that hash, and the tracked Kohonen model is still `neuron/models/kohonen_stub.c` (no `kohonen.c`).

## Task Commits

1. **Task 1:** decision only, no commit.
2. **Task 2 RED:** `4f66f22` test(02-03): 12 failing tests (test file only; `som_select.py` stays uncommitted by plan, D-10).
3. **Task 2 GREEN and Task 3:** `ea7a0b1` feat(02-03): the single rule commit (rule text + `som_select.py` + stage-1 series + 13th test).

## TDD Gate Compliance

- **RED:** `4f66f22`. The run failed at collection with `ModuleNotFoundError: No module named 'som_select'`, i.e. the module under test did not exist. `workflow.tdd_mode` is not enabled in `.planning/config.json`, so `gsd_run check tdd-red-evidence` was not required; its classifier would label a collection error as INVALID_RED. Semantic assessment: the failure is the intended one for a not-yet-written module, and every one of the 12 tests then went green with the implementation, so no test was vacuous.
- **GREEN:** `ea7a0b1`. The plan fixes the GREEN commit to be the rule commit (Task 2 forbids committing `som_select.py` earlier), so GREEN and the Task 3 commit coincide.
- **REFACTOR:** none.

## Deviations from Plan

None - plan executed exactly as written. Two non-deviations worth noting: `.venv` did not exist and was created with the plan's documented command (`python3.12 -m venv .venv`, pinned `analysis/requirements.txt`); and the 13th test was added in Task 3 as the plan specifies, so the Task 2 count of 12 passed was observed before it existed.

**Total deviations:** 0.

## Issues Encountered

- `docs/Kohonen Model.pdf` could not be rendered by the Read tool (no `pdftoppm`). Pages 15 and 24-27 were extracted with `pypdf` installed in a scratch venv under the session scratchpad, outside the repo, as T-02-SC allows. Nothing was added to `.venv` or `requirements.txt`.

## Known Stubs

None. The plan's files hold no placeholder data; `stage2_series(k)` is intentionally generated later for the chosen k by plan 02-04.

## Threat Flags

None. The only new surface is `rule_guard`'s git calls, already covered by T-02-09 (argument lists, fixed paths, cwd set, no shell).

## Handoff to later plans

- 02-04 records, in `selection.json`: rule commit `ea7a0b11202d19bb2ffed71a0e43a58bdd6f3d00`, `rule_digest` of the section `d1c69242551cca987d7fab1b496ec6382c587a216e2ea074bea8c50e9e55bb37` and sha256 of `analysis/som_select.py` `b592469bc4ae0786b4d65d7b0a0161a8d4e365951247cec403c8d728a689954d`. Any later change to those files voids the pre-registration claim (D-10).
- `aggregate` expects `summary.csv` rows with `label, seed, status, grid_k, neighborhood, radius0, radius_final, eta0, eta_final, epochs, n_samples, qe, te, occupied_neurons, empty_fraction`, `loo_by_seed.csv` rows with `label, seed, qe_loo`, and `stability_by_label[label] = (value, nan_pairs)` as returned by `som.stability`.
- 02-01 (wave 2) can now start: its precondition (rule commit exists, files tracked and clean) holds.

## Self-Check: PASSED

- FOUND: `analysis/som_select.py`, `analysis/tests/test_som_select.py`, `analysis/series_som_stage1.json`, `deliverables/02-kohonen.md`
- FOUND commits `4f66f22` and `ea7a0b1` (ancestors of HEAD); `git rev-list --count accf7be..HEAD` = 2
- `pytest analysis/tests/test_som_select.py`: 13 passed; sweep dry-run prints `14 variants x 10 seeds = 140 runs`; RULE_DOC_OK, NO_RELAXATION_OK and SAME_RULE_COMMIT_OK printed
- `git status --porcelain` on the four plan files is empty; no `analysis/results/` directory exists
