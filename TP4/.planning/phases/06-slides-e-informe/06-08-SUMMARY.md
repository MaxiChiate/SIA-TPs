---
phase: 06-slides-e-informe
plan: 08
subsystem: deliverables-data
tags: [facts, drift-pins, deliverables-manifest, questions, checkpoint, d-11, d-12]

requires:
  - phase: 06-slides-e-informe
    provides: "06-04: facts.py (SOM slice), deliverables_manifest.py dataclasses, informe.make_slugify and render_fragment"
  - phase: 06-slides-e-informe
    provides: "06-05, 06-06, 06-07: the 20 slide variants and the final analysis/results files this plan reads"
provides:
  - "analysis/facts.py: load_facts for pca, som, oja, camp, maint, letters and qr (132 display keys from 26 sources), read_csv_source, pct_short"
  - "analysis/facts.py: DRIFT_PINS (68 pins, 9 to 26 per fragment), check_fragment_numbers and the `check` subcommand (D-12)"
  - "analysis/deliverables_manifest.py: FRAGMENTS (5), QUESTIONS (25), FIGURES (31, 20 with slide), `questions` review sheet; QUESTIONS_CHECKED_AGAINST_PDF and ANSWER_SECTIONS_CHECKED are True"
  - "test_questions_checked_against_pdf and test_answer_sections_checked guard both flags in make test"
affects: [06-09, 06-10, 06-11, 06-12]

actuals:
  tokens: 16100
  tasks: 3
  commits: 2
plan_head_before: 830bda7ca9adcd12b95d840cca8ab8fae7a6e155
plan_head_after: 15282b782ffd67413d4f35e6377cf9abd79b2de9

tech-stack:
  added: []
  patterns:
    - "Facts are grouped in one private loader per phase (_pca_facts ... _qr_facts) merged by load_facts; every number is formatted by dec, pct, pct_short or integer"
    - "A drift pin is (fragment number, phrase with {group.key} placeholders); check_fragment_numbers collapses whitespace runs and reports one message per failing pin"
    - "A test fixture tree (write_results) holds a minimal version of every SOURCES file and is shared by test_facts.py and test_informe.py"

key-files:
  created: []
  modified:
    - analysis/facts.py
    - analysis/deliverables_manifest.py
    - analysis/tests/test_facts.py
    - analysis/tests/test_deliverables_manifest.py

key-decisions:
  - "camp.<campaign>.* facts report one committed list per campaign, chosen by the constant RECOMMENDED_OBJECTIVE (futbol/profundidad, perros/costo_por_mil, maquillaje/profundidad, arte/engagement_profundidad), the objective the informe recommends; load_facts checks each pair against campaigns/selection_identity.json and stops if it is not a committed pair"
  - "pct_short added next to pct: a whole percentage prints without decimals (0 %, 100 %) as the QR prose writes it; every other QR percentage keeps one decimal"
  - "qr.noise_high is read from recovery_table.csv as the highest level where pinv recovery is still above 0 (0,45); the keys named *_at_0_NN read the row at that grid level"
  - "letters.spurious_class is the most frequent non-stored final class over the seeds tried (inverso)"

patterns-established:
  - "Question flags are flipped only from the recorded human reply, with a test that fails if either is reset"

requirements-completed: []  # DELIV-02 and DELIV-03 are also completed by 06-09 to 06-12 (informe table, README figure table); left pending here

duration: not recorded (two sessions around the Task 2 checkpoint)
completed: 2026-10-26
status: complete
---

# Phase 6 Plan 08: Facts, drift pins and the checked question manifest Summary

**Every number the informe and the slides quote now comes from facts.py (132 keys over the five phases), 68 pins tie the numbers typed in the five fragments to the results and pass on the real files, and the 25 enunciado questions were approved by a human against the PDF, with their answering sections, so both flags are True.**

## Performance

- **Tasks:** 3 of 3 (Task 2 was the blocking-human checkpoint)
- **Files modified:** 4
- **Tests:** `make test` 342 passed (298 before this session's work, +44 in test_facts.py and test_deliverables_manifest.py) and 1282 C checks, 0 failed

## Accomplishments

- Task 1 (earlier session): manifest of 5 fragments, 25 questions, 31 figures (20 with a slide variant), the `questions` review sheet; MANIFEST_FULL_OK and REVIEW_SHEET_OK passed.
- Task 3: both question flags set to True with their comments reworded, and two tests added; `facts.py` widened from the SOM slice to all five phases; `DRIFT_PINS` and `check_fragment_numbers` written; `python analysis/facts.py check` prints `DRIFT_OK 68 pins` on the real results.
- The drift check is not vacuous: a copy of fragment 02 with `R² de PC2 sobre la grilla: 0,055` changed to `0,056` made the command exit 1 and name fragment 2 and the filled phrase (done in the scratchpad, `deliverables/` untouched).

## Task Commits

1. **Task 1: full manifest and review sheet** - `fbdfec6` (feat)
2. **Task 2: checkpoint** - no commit (human reply below)
3. **Task 3: facts, drift pins, question flags** - `15282b7` (feat)

## Checkpoint log: Task 2 human reply

Reply to the blocking-human checkpoint (comparison of the 25 texts with docs/Archivo SIATP 42026.pdf, and the answering sections), verbatim:

> approved

Meaning, per the plan's resume-signal: all 25 question texts match the PDF exactly and every listed section answers its question.

- Question texts: **approved without corrections** (no `Q<id>: <texto>` line, so no QUESTIONS text changed).
- Answering sections: **sections approved without corrections** (no `Q<id> secciones:` line, so no anchor and no fragment field changed).
- `QUESTIONS_CHECKED_AGAINST_PDF = True` and `ANSWER_SECTIONS_CHECKED = True`; `analysis/deliverables_manifest.py questions` ends with `QUESTIONS 25 checked=True sections_checked=True`.

## Facts and pins

| Group | Source files | Keys (examples) |
|-------|--------------|-----------------|
| pca | audited/decision.json, sensitivity.json, audited/eigenvalues.csv | n_features, k_80, (field retired), var_pc1, var_pc2, cum_k80, (field retired) |
| som | pca_contrast.json, selection.json, robustness.json | chosen_k, r2_pc1, mantel_rho, edge_rho_pc1, n_failing_variants, figure_seed |
| oja | comparison.json, dispersion.json, evidence.json, evidence_correlations.csv, index.csv | n_seeds, abs_cos_min, corr_followers_pearson, max_id, pivot_margin |
| camp | selection_identity.json, shortlists.csv, comparison.csv | k, rule_commit, `<campaign>.top5`, `.criterion`, `.cost_per_thousand_ar`, `.overlap_followers` |
| maint | demo.json | bmu, distance, max_training_distance, retrain, index_place |
| letters | selection.json, orthogonality.json, capacity.json, spurious.json | separated_set, correlated_max_overlap, p4_stable_0..4, spur_*, spurious_class |
| qr | verdict.json, qr_facts.json, overlaps.json, protocol.json, recovery_table.csv, majority.json, shift.json | identical_fraction, hebb_exact_noise0, pinv_at_0_40..0_50, hamming_at_0_45, noise_high |

Pins per fragment: 1 -> 9, 2 -> 9, 3 -> 26, 4 -> 9, 5 -> 15 (68 in total; at least 25 and at least 3 per fragment are asserted by `test_drift_pins_are_at_least_25_with_at_least_3_per_fragment`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Percentages that print as whole numbers**
- **Found during:** Task 3 (pins of fragment 5)
- **Issue:** the fragment writes `0 %` and `100 %` in prose (`colapsa a 0 % en 0,50`), while `pct(0.0, 1)` gives `0,0 %`; a pin built on `pct` would report a false drift.
- **Fix:** added `facts.pct_short(fraction, digits=1)`; used only for the `qr.*` recovery facts. Tested in `test_pct_short_drops_decimals_of_whole_percentages`.
- **Files modified:** analysis/facts.py, analysis/tests/test_facts.py
- **Commit:** 15282b7

**2. [Rule 3 - Blocking] Test fixture tree widened for every source**
- **Found during:** Task 3
- **Issue:** `test_informe.py` builds its results tree with `test_facts.write_results`, which held only the three SOM files; `load_facts` now reads 26 sources.
- **Fix:** `write_results` writes a minimal version of every SOURCES file (the old SOM values are unchanged, so the earlier assertions still hold). `test_informe.py` needed no edit and passes.
- **Files modified:** analysis/tests/test_facts.py
- **Commit:** 15282b7

### Plan items not followed to the letter

- `campaigns/objective_metrics.csv` is listed in the interfaces but no fact reads it, so it is not in SOURCES (a source that nothing reads would also have no test). Every other file of the interfaces list is a source.
- The plan names `camp.c.criterion`, `top5`, `cost_per_thousand_ar` and `overlap_followers` for each campaign without saying which list. Fútbol has three committed objectives, so the choice is the editorial constant `RECOMMENDED_OBJECTIVE` (decision above); `camp.<campaign>.objective` exposes it, and `overlap_followers_tema` was added next to the global one.

## Findings

No drift: all 68 pins found their phrase on the first run, so no fragment and the JSON disagree. No pin had to be corrected after the run. `deliverables/` is unchanged (`git diff --quiet -- deliverables/` succeeds).

## Known Stubs

None. No `TODO`, placeholder text or empty UI-bound value in the four files.

## Threat Flags

None. No new endpoint, auth path or file access outside the read-only reads of `analysis/results` and `deliverables`.

## Self-Check: PASSED

- FOUND: analysis/facts.py, analysis/deliverables_manifest.py, analysis/tests/test_facts.py, analysis/tests/test_deliverables_manifest.py
- FOUND commits: fbdfec6, 15282b7 (both ancestors of HEAD)
- PYTEST_OK, QUESTIONS_CHECKED_OK, DRIFT_REAL_OK (68 pins) and FACTS_FULL_OK (132 keys) printed on the final tree
