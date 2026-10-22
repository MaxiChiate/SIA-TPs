---
phase: 03-oja-y-decisiones-de-campa-a
plan: 05
subsystem: analysis
tags: [python, numpy, matplotlib, campaigns, followers-baseline, deliverable]

requires:
  - phase: 03-oja-y-decisiones-de-campa-a
    provides: "plan 03-02: the committed rule (a6212e89) and campaigns_select.rule_identity(); plan 03-03: analysis/results/oja/index.csv and make oja; plan 03-04: sections 1-3 of the deliverable and the index-followers correlation"
  - phase: 02-kohonen-som
    provides: "selection.json of make som-stage1 (chosen k = 5, k5-step, figure run) for the neuron of each chosen creator"
provides:
  - "analysis/campaigns.py and make campaigns: rule_identity first, six own lists and two followers baselines each, the 18-row D-17 comparison, the objective means, the Kohonen/Oja/PCA reading and two figures"
  - "analysis/results/campaigns/ (generated): selection_identity.json, shortlists.csv, comparison.csv, objective_metrics.csv, report_campaigns.md, report_reading.md, shortlists_biplot.svg/png, shortlists_som.svg/png"
  - "Section 5 of deliverables/03-oja-campanas.md: a recommendation per campaign, the football recommendation with its assumptions, the comparison with choosing by followers only, and the Kohonen/Oja/PCA reading"
affects: [03-06]

actuals:
  tokens: 13800
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "A guarded run records the identity of the committed rule (commit, rule sha256, code sha256) in its results and in the first line of its report"
    - "Report files made only of bullets and table rows, pasted verbatim into the deliverable by a script and checked line by line with grep -qxF"

key-files:
  created:
    - analysis/campaigns.py
    - analysis/tests/test_campaigns.py
  modified:
    - Makefile
    - deliverables/03-oja-campanas.md

key-decisions:
  - "Football recommendation (a judgment, not a result of the rule): profundidad educativa first, descubrimiento second, alcance masivo last, resting on five stated assumptions; the depth list shares 0 of 5 creators with both baselines and costs USD 1367 in total, but reaches only 28873 Argentines"
  - "The lists are reported as they came out: @makeupconsejos and @vidaperruna are in the football discovery list because their raw topic shares make football dominant (59,1 % and 69,5 %), and section 5 asks a person to look at them before contacting them; the rule was not touched"
  - "The comparison is fair to followers: the global baseline is the cheapest per thousand in five of six comparisons and has the largest Argentine reach, and the section says so next to its disadvantages"
  - "No tie in any criterion or in followers occurred in the 18 lists, so the Oja index never decided who enters (D-13)"

patterns-established:
  - "main reads and validates every input (Oja index, PCA scores, SOM figure run, Phase 2 rule) before creating the output folder, so a refusal writes nothing"

requirements-completed: [CAMP-01, CAMP-02]

coverage:
  - id: D1
    description: "make campaigns calls rule_identity() first and refuses (SystemExit, nothing written) otherwise; selection_identity.json records rule_commit a6212e89cdc654021cfda02d9d16237c8c21c332, rule_sha256 and select_sha256"
    requirement: CAMP-01
    verification:
      - kind: unit
        ref: "analysis/tests/test_campaigns.py#test_main_refuses_without_rule"
        status: pass
      - kind: integration
        ref: "make campaigns, then the Task 1 verify script -> CAMPAIGNS_OK (rule_commit equals the commit that added the rule file)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Six own lists and two followers baselines each by the committed rule, k = 5, in rank order; comparison.csv with 18 rows (overlap@5, topic share, reach, cost, cost per thousand as a ratio of sums, criterion mean) and objective_metrics.csv with the raw means of every criterion variable"
    requirement: CAMP-02
    verification:
      - kind: unit
        ref: "analysis/tests/test_campaigns.py#test_overlap_counts_shared_ids_once, test_list_metrics_ratio_of_sums, test_list_metrics_short_and_empty_list, test_topic_share_counts_dominant, test_objective_means"
        status: pass
      - kind: integration
        ref: "two runs of analysis/campaigns.py give identical shasum for every CSV, JSON, MD and SVG; Task 2 verify -> READING_OK"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every chosen creator located on the SOM map (neuron row, col of the k5-step figure run), on the Oja index (index and rank) and on PC1/PC2, with two figures; none of it changes a list"
    requirement: CAMP-01
    verification:
      - kind: unit
        ref: "analysis/tests/test_campaigns.py#test_index_top_overlap"
        status: pass
      - kind: integration
        ref: "shortlists.csv reading columns present, neurons inside the 5 x 5 grid, Oja ranks in 1..50 -> READING_OK"
        status: pass
    human_judgment: true
    rationale: "Legibility of the two figures was judged by looking at the PNG twins, which is a visual judgment"
  - id: D4
    description: "Section 5 of the deliverable: every report line verbatim, the football recommendation with assumptions, the advantages and disadvantages of choosing by followers, the no-return sentence, and the text between the rule markers unchanged"
    requirement: CAMP-02
    verification:
      - kind: other
        ref: "line-by-line grep -qxF of report_campaigns.md and report_reading.md inside section 5, bold openers, no-return sentence, banned-phrase scan -> SECTION5_OK; rule_identity() -> RULE_INTACT_OK; git diff shows 0 deletions in the deliverable"
        status: pass
    human_judgment: true
    rationale: "Fairness and honesty of a recommendation, and that nothing implies a commercial outcome, is a judgment over meaning, not a string match"

duration: 9min
completed: 2026-10-22
status: complete

plan_head_before: 1a052981a9dcd045b696e9dfe4cfebc9511ef954
plan_head_after: 77a1abc62b2f110edf496379cb6d6100549c6409
---

# Phase 3 Plan 05: Campaign lists, followers baselines and section 5 Summary

**`make campaigns` applies the committed rule behind `rule_identity()` (commit a6212e89, identity recorded in its results) to give six own lists and two followers baselines each, an 18-row comparison and a Kohonen/Oja/PCA reading, and section 5 recommends creators per campaign, answers the football question with stated assumptions and compares fairly with followers only, with no return claims**

## Performance

- **Duration:** 9 min (started 2026-10-22T14:42:01Z, finished 2026-10-22T14:51Z)
- **Tasks:** 3 (the first a tracer), 5 commits
- **Files modified:** 4 (2 created, 2 modified), plus generated outputs under `analysis/results/campaigns/` (not versioned)

## Accomplishments

- `analysis/campaigns.py`: `main` calls `campaigns_select.rule_identity()` before it reads or creates anything and records `rule_commit`, `rule_sha256` and `select_sha256` in `selection_identity.json`; the first line of `report_campaigns.md` cites the commit. It reads the Oja index, the PCA scores and the Phase 2 figure run (after `som_stage.require_same_rule`) and checks the creator order of each, then writes everything byte-stably: two runs give identical CSV, JSON, MD and SVG files.
- The six own lists and two baselines per pair (k = 5): 18 rows in `comparison.csv`, the raw means of every criterion variable in `objective_metrics.csv` (18 "medias del criterio" bullets in the report), and for each chosen creator its neuron, Oja index and rank, and PC1/PC2 in `shortlists.csv`. Two figures, `shortlists_biplot` and `shortlists_som`, place the lists on the PC1-PC2 plane and on the k5-step map.
- What the rule produced, as it came out: the global followers list is the cheapest per thousand Argentines in five of six comparisons (USD 25,71; only the perros list, USD 17,94, is cheaper) and has the largest reach (881361), but only 20 % of it is football and 0 % art; the own lists have 100 % of the campaign's topic. Against the in-topic baseline the own list shares 0 to 3 of 5 creators, is cheaper per thousand in four objectives and dearer in two (descubrimiento, profundidad). Only the perros list has creators in the top 5 of the Oja index (2 of 5); no tie occurred in any criterion, so the index never decided anyone.
- Section 5: 5.1 to 5.4 per campaign (lists, table rows and criterion means pasted verbatim, recommendation tied to the D-11 assumption, total cost and cost per thousand), the football **Recomendación** (profundidad first) and **Supuestos**, 5.5 with both baselines, **Ventajas de elegir solo por followers**, **Desventajas** and the exact no-return sentence, and 5.6 with the ten reading bullets and the two figure paths.

## Task Commits

1. **Task 1: end-to-end `make campaigns` (tracer)**
   - RED `4b80b3e` (test): five tests failing on `NotImplementedError` stubs
   - GREEN `d6b6cb9` (feat): `analysis/campaigns.py`, `campaigns` Makefile target
2. **Task 2: objective means, reading and figures**
   - RED `dc87bbd` (test): two tests failing on `NotImplementedError` stubs
   - GREEN `ef35286` (feat): `objective_means`, `index_top_overlap`, the readers, the reading columns, `report_reading.md` and two figures
3. **Task 3: section 5 of the deliverable** - `77a1abc` (docs)

**Plan metadata:** the docs commit that holds this SUMMARY, STATE.md, ROADMAP.md and REQUIREMENTS.md.

## TDD notes

- RED evidence: each RED run executed the target tests, which reached the stub and failed with `NotImplementedError` (5 of 5 in Task 1; the 2 new tests of Task 2 with the 5 earlier ones passing). The stubs had to exist so that the failure is the planned behavior missing and not an import error. The plan is `type: execute`, so the plan-level `check tdd-red-evidence` gate does not apply; the semantic assessment above is the record.
- GREEN: 7 passed; the whole suite is 79 passed (`.venv/bin/python -m pytest analysis/tests -q`).

## Files Created/Modified

- `analysis/campaigns.py` - the guarded campaign run, readers, writers, reading and figures
- `analysis/tests/test_campaigns.py` - seven tests on synthetic creators
- `Makefile` - target `campaigns: oja som-stage1` and `campaigns` in `.PHONY`
- `deliverables/03-oja-campanas.md` - section 5 after section 4 (160 lines added, 0 deleted; the rule text is unchanged)

## Decisions Made

- The football recommendation is a judgment with five stated assumptions (what the client sells, which audience, budget, what the variables measure, sensitivity); it says which assumption flips it to descubrimiento or alcance.
- Two creators whose names suggest another topic but whose raw shares make football dominant are reported as they came out and flagged for a human look, instead of changing the filter.
- `read_som_bmu` returns `(k, label, seed, bmu)` and the SOM figure recomputes the hits from the BMU with `np.bincount` (equal to the run's `occupancy.csv`), so no fifth return value was needed.
- For football the SOM figure counts the union of the three own lists in each neuron (12 distinct creators) and says so in its caption.

## Deviations from Plan

### Commit policy (instruction from the orchestrator, not a deviation rule)

The plan text says to stage and commit nothing; the dispatch overrode it (the user wants the executor to commit), so every task was committed with explicit paths and `.planning/milestone.lock` was never staged.

### Auto-fixed Issues

None - plan executed exactly as written otherwise.

---

**Total deviations:** 0 auto-fixed
**Impact on plan:** none.

## Issues Encountered

- `pdftoppm` is not installed, so the statement PDF (pages 1 and 4) could not be rendered; the client descriptions came from D-10/D-11 in `03-CONTEXT.md`, which restate them.
- `make campaigns` re-runs `make oja` and `make som-stage1` each time (about 30 s on this machine); it is the dependency the plan specified.
- `make test` in `neuron/` still breaks on the space in the repo path (pre-existing); pytest was run directly.

## Known Stubs

None. (The `NotImplementedError` stubs of the RED commits are replaced in the GREEN commits.)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 03-06 can read `analysis/results/campaigns/` and `selection_identity.json` and cite sections 1-5 of the deliverable.
- The human check of section 5 (fairness of the football recommendation, and that nothing implies a commercial outcome) is still open and belongs to the verification of the phase.

## Self-Check: PASSED

- FOUND: analysis/campaigns.py, analysis/tests/test_campaigns.py, Makefile, deliverables/03-oja-campanas.md
- FOUND commits: 4b80b3e, d6b6cb9, dc87bbd, ef35286, 77a1abc
- `rule_identity()` returns a6212e89cdc654021cfda02d9d16237c8c21c332 after the deliverable commit

---
*Phase: 03-oja-y-decisiones-de-campa-a*
*Completed: 2026-10-22*
