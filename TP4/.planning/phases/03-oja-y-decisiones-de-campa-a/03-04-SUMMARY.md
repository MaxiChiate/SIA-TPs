---
phase: 03-oja-y-decisiones-de-campa-a
plan: 04
subsystem: analysis
tags: [python, numpy, oja, pca, matplotlib, deliverable]

requires:
  - phase: 03-oja-y-decisiones-de-campa-a
    provides: "plan 03-02: the committed rule between the markers of deliverables/03-oja-campanas.md and rule_identity(); plan 03-03: analysis/oja.py, make oja, report_pc1.md, report_convergence.md, index.csv, convergence figure"
provides:
  - "evidence() and plot_oja_vs_pc1() in analysis/oja.py; make oja also writes evidence_weights.csv, evidence_correlations.csv, evidence_top10.csv, evidence.json, report_evidence.md and oja_vs_pc1.svg/png"
  - "Sections 1-3 of deliverables/03-oja-campanas.md: algorithm and convergence, index vs PC1, and the written answer No to choosing the Oja maximum for any campaign"
  - "The index-followers correlation under both signs (Pearson -0,879 / Spearman -0,921 with the D-02 sign) for plan 03-05 to cite"
affects: [03-05, 03-06]

actuals:
  tokens: 6000
  tasks: 2
  commits: 5

tech-stack:
  added: []
  patterns:
    - "Report files made only of table rows and bullets, pasted verbatim into the deliverable and checked line by line with grep -qxF"
    - "Evidence shown under both signs of the D-02 convention so a sign choice cannot pass for a result"

key-files:
  created: []
  modified:
    - analysis/oja.py
    - analysis/tests/test_oja.py
    - deliverables/03-oja-campanas.md

key-decisions:
  - "Section 3 answers No first and says the maximum depends on a sign convention: D-02 gives INF031 (@mundoanimal.ar, perros, 17062 followers) and the opposite sign gives INF045 (@futbolsinvueltas, fútbol, 493194 followers)"
  - "The report keeps the planned 4-column correlation table; the sign labels read 'de D-02' and 'opuesto' so the bullets read naturally"
  - "The figure box prints abs(cos) with 7 decimals (0,9999998) while the report table keeps the planned 6 decimals (1,000000); section 2 explains the rounding"

patterns-established:
  - "evidence() matches the raw creators to the index by creator id and main refuses when the order of datos/creadores.csv differs from analysis/results/pca/ (T-03-07 carried over)"

requirements-completed: [OJA-01, OJA-02, OJA-03]

coverage:
  - id: D1
    description: "evidence() under both signs: 26 weights by abs(w), Pearson and tie-aware Spearman with followers and the four raw topic shares, top-10 overlap and dominant-topic composition, maximum creator under each sign"
    requirement: OJA-03
    verification:
      - kind: unit
        ref: "analysis/tests/test_oja.py#test_evidence_both_signs"
        status: pass
      - kind: integration
        ref: "make oja twice with identical hashes except runs.json; evidence files asserted in the Task 1 verify -> OJA_EVIDENCE_OK"
        status: pass
    human_judgment: false
  - id: D2
    description: "Section 3 opens with No and pastes every report_evidence.md line verbatim, with no use of the banned adjective"
    requirement: OJA-03
    verification:
      - kind: other
        ref: "line-by-line grep -qxF check of report_evidence.md inside section 3, **No.** first, banned-word scan -> SECTION3_OK"
        status: pass
    human_judgment: true
    rationale: "Whether the interpretive prose is honest about what the evidence supports is a judgment over meaning, not a string match"
  - id: D3
    description: "oja_vs_pc1 figure: PC1 score against the Oja index, coloured by dominant topic, identity line and agreement statistics"
    requirement: OJA-02
    verification:
      - kind: integration
        ref: "make oja twice with identical hashes with oja_vs_pc1.svg and .png present -> FIGURE_OK"
        status: pass
    human_judgment: true
    rationale: "Legibility of the figure was checked by looking at the PNG, which is a visual judgment"
  - id: D4
    description: "Sections 1 and 2 hold every report_convergence.md and report_pc1.md line verbatim and name convergence.svg and oja_vs_pc1.svg"
    requirement: OJA-01
    verification:
      - kind: other
        ref: "line-by-line check of the three report files inside sections 1, 2 and 3, headings 1 to 4 in order -> SECTIONS123_OK"
        status: pass
    human_judgment: true
    rationale: "Faithfulness of the prose to the pasted numbers and figures is a judgment over meaning"
  - id: D5
    description: "The text between the rule markers is unchanged and rule_identity() still passes"
    requirement: OJA-03
    verification:
      - kind: other
        ref: "rule_identity() printed rule commit a6212e89cdc654021cfda02d9d16237c8c21c332 after each deliverable edit; git diff --numstat on the deliverable shows 0 deletions -> RULE_INTACT_OK"
        status: pass
    human_judgment: false

duration: 8min
completed: 2026-10-22
status: complete

plan_head_before: 370b3c2f98c3ac99822cf8a61d8351ce00b8869b
plan_head_after: 32717abfd55162f7c180132fbb9fdd948c6a6e4e
---

# Phase 3 Plan 04: Oja evidence and written sections Summary

**`make oja` now writes the D-06 evidence under both signs (index vs followers Pearson -0,879, maximum INF031 or INF045 depending on the sign) and the index-vs-PC1 figure, and sections 1-3 of the deliverable answer "No" to choosing the Oja maximum for any campaign, with every report line pasted verbatim and the committed rule untouched**

## Performance

- **Duration:** about 8 min of work (started 2026-10-22T14:31:50Z)
- **Completed:** 2026-10-22T14:39Z
- **Tasks:** 2 (the first a tracer)
- **Files modified:** 3 (0 created, 3 modified), plus generated outputs under `analysis/results/oja/` (not versioned)

## Accomplishments

- `evidence(w, features, index, data, ids)` computes, for the D-02 sign and its opposite: the 26 weights by abs(w); Pearson and tie-aware Spearman with `followers` and the four raw topic shares (`topic_art_pct` included); the overlap of the index top 10 with the top 10 of each topic share and the dominant-topic composition of the index top 10; and the maximum creator under each sign. `main` writes the three CSV tables, `evidence.json` and `report_evidence.md` (three tables and two bullets, comma decimals).
- The evidence on the real data: the index tracks size inversely under D-02 (followers Pearson -0,879, Spearman -0,921); perros is the only topic above 0,4 in absolute correlation (+0,480); under D-02 seven of the index top 10 are perros creators and none arte, under the opposite sign five are fútbol, three maquillaje, one perros, one arte. The maximum is INF031 (@mundoanimal.ar, perros, 17062 followers) with D-02 and INF045 (@futbolsinvueltas, fútbol, 493194 followers) with the opposite sign.
- `plot_oja_vs_pc1` draws the PC1 score against the seed-1 index, coloured by dominant topic with the palette of the four topics, the identity line and a statistics box; I looked at the PNG: the 50 points sit on the line.
- Sections 1-3 of `deliverables/03-oja-campanas.md`: section 1 (algorithm, parameters, D-02 sign, convergence with its six bullets and the convergence figure), section 2 (comparison table and four seed bullets, `oja_vs_pc1.svg`), section 3 (opens with **No.**, what the index represents, the weights, correlations, top-10 tables and the two maximum bullets, and a three-reason conclusion that sends the choice to the rule of section 4).
- Two consecutive `make oja` give identical hashes for every CSV, JSON, MD and SVG except `runs.json`; `pytest analysis/tests` gives 72 passed; `rule_identity()` still returns rule commit `a6212e89...` after each deliverable edit and the deliverable diff has 0 deletions.

## Task Commits

1. **Task 1: end-to-end D-06 evidence and section 3 (tracer)**
   - RED `1692e16` (test): `test_evidence_both_signs` failed with `AttributeError: module 'oja' has no attribute 'evidence'` (1 failed). The target test failed on the symbol the plan adds, an import-level reason rather than an assertion on the behavior; the behavior assertions ran only after GREEN.
   - GREEN `0d5db94` (feat): `evidence`, `evidence_lines`, the new constants and the `main` writers; 7 tests pass, `OJA_EVIDENCE_OK` printed.
   - Section 3 `006f271` (docs): `SECTION3_OK` and `RULE_INTACT_OK` printed.
2. **Task 2: figure and sections 1 and 2**
   - `bb53cc4` (feat): `plot_oja_vs_pc1` and its call in `main`; `FIGURE_OK` printed.
   - `32717ab` (docs): sections 1 and 2; `SECTIONS123_OK` and `RULE_INTACT_OK` printed.

**Plan metadata:** the docs commit that holds this SUMMARY, STATE.md and ROADMAP.md follows. No REFACTOR commit: no cleanup was warranted.

## TDD Gate Compliance

Task 1 carried `tdd="true"`: RED (`test(03-04)`, `1692e16`) precedes GREEN (`feat(03-04)`, `0d5db94`). The RED evidence is a nonzero pytest exit on `AttributeError` for the missing function, not a classified assertion failure; the semantic assessment is that the target test executed and failed for the intended reason (the function did not exist yet). `gsd_run check tdd-red-evidence` was not run: the project has no TAP, JUnit or supported-format record for pytest output, as in plan 03-03.

## Files Created/Modified

- `analysis/oja.py` - `evidence`, `evidence_lines`, `plot_oja_vs_pc1`, the evidence constants, the `main` writers and the `TOPICS` import
- `analysis/tests/test_oja.py` - `test_evidence_both_signs`, the seventh test
- `deliverables/03-oja-campanas.md` - sections 1, 2 and 3 above section 4; the text between the rule markers is byte-identical

## Decisions Made

- The answer in section 3 is built on three points of evidence (a sign-dependent maximum, one topic and one size profile at each extreme, and an index that is mostly a size ordering) and states that the margin of the D-02 pivot (0,00275) makes the convention itself fragile.
- Section 1 states that `sign_flipped = 1` in all 10 seeds (C reversed the trained vector each time) and flags the plausible cause as unverified, instead of asserting it.
- The statistics box of the figure uses 7 decimals so it does not print 1,000000 for an abs(cos) of 0,9999998; the report table stays at the planned 6 decimals and section 2 explains the rounding.
- Section 1 notes that the margin bullet uses the PC1 coefficients (`v1`) while the section 3 weights are those of `w`, so `average_impressions` reads -0,2493 in one and -0,2494 in the other.

## Deviations from Plan

**Commit policy (orchestrator override, not a plan deviation).** The plan text says not to stage or commit and to leave commits to the user; the orchestrator's explicit instruction for this run was that the executor commits. Five task commits were made, staging files by explicit path, never `.planning/milestone.lock`, each ending with the Co-Authored-By line. The plan's acceptance criterion `git diff --cached --quiet` was checked before each staging step and held.

**1. [Rule 1 - Bug] Sign labels read "signo signo opuesto" in the first report bullet**
- **Found during:** Task 1 (first `make oja` after the GREEN code)
- **Issue:** `SIGN_LABELS` held "signo opuesto" and the bullet template already said "el signo", producing "el signo signo opuesto".
- **Fix:** the labels became "de D-02" and "opuesto"; the report was regenerated before committing.
- **Files modified:** analysis/oja.py
- **Verification:** `report_evidence.md` bullets read "Máximo con el signo de D-02" and "Máximo con el signo opuesto"; SECTION3_OK
- **Committed in:** `0d5db94`

**2. [Rule 1 - Bug] Section 3 overstated the topic position and the dogs weight**
- **Found during:** Task 1 (re-reading section 3 against the Phase 1 and Phase 2 deliverables)
- **Issue:** the draft said the Phase 1 PCA put the topics in PC3 and PC4, but section 6 puts only fútbol and maquillaje there and `deliverables/02-kohonen.md` 6.4 puts perros in PC2; it also called the dogs coefficient of `w` "the only topic weight".
- **Fix:** the sentence names the three topics and their components and cites both deliverables; the dogs coefficient (+0,1290) is described as the largest of the three training topics.
- **Files modified:** deliverables/03-oja-campanas.md
- **Verification:** SECTION3_OK, RULE_INTACT_OK
- **Committed in:** `006f271`

**Total deviations:** 2 auto-fixed (2 bugs in my own draft, both before their commit).
**Impact on plan:** None on scope; both fixes were corrections to wording that would have misstated the evidence.

## Issues Encountered

- A shell command of mine hung once on a stray `cat` waiting for stdin and was backgrounded; nothing had been written by it and the work was redone with the Edit tool.
- `make test` in neuron/ was not used (the known unquoted `$(PY)` space issue); pytest was run as `.venv/bin/python -m pytest analysis/tests -q` (72 passed). Each `make oja` adds a timestamped `analysis/results/series_oja_*` sweep folder (gitignored).

## Known Stubs

None.

## Threat Flags

None - no new surface beyond the plan's threat register: T-03-15 (creators matched to the index by id and the creator order checked in `main`; every report line of the three reports checked verbatim in its section; evidence shown under both signs and section 3 scanned for the banned adjective), T-03-16 (sections inserted outside the markers, `rule_identity()` passed after each deliverable edit), T-03-SC (no new package).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 03-05 can cite the index-followers correlation of `report_evidence.md` and append section 5 after section 4; sections 1-3 sit above the rule, as planned.
- Plan 03-06 can read `weights.csv` and `evidence_weights.csv` for the maintenance demo.
- Concern to carry: the sign convention (margin 0,00275) is stable on these data but fragile in general, which section 1 states.

---
*Phase: 03-oja-y-decisiones-de-campa-a*
*Completed: 2026-10-22*

## Self-Check: PASSED

- Files exist: `analysis/oja.py`, `analysis/tests/test_oja.py`, `deliverables/03-oja-campanas.md`, and `evidence_weights.csv`, `evidence_correlations.csv`, `evidence_top10.csv`, `evidence.json`, `report_evidence.md`, `oja_vs_pc1.svg`, `oja_vs_pc1.png` under `analysis/results/oja/`
- Commits are ancestors of HEAD: `1692e16`, `0d5db94`, `006f271`, `bb53cc4`, `32717ab`; `git rev-list --count 370b3c2..HEAD` is 5
- `pytest analysis/tests` 72 passed; `make oja` twice with identical hashes except runs.json; `OJA_EVIDENCE_OK`, `SECTION3_OK`, `FIGURE_OK`, `SECTIONS123_OK` and `RULE_INTACT_OK` printed
