---
phase: 05-hopfield-con-qr
plan: 03
subsystem: ai-ml
tags: [hopfield, hebb, qr, noise-curve, energy-trace, overlap-matrix, matplotlib]

# Dependency graph
requires:
  - phase: 05-hopfield-con-qr
    provides: "05-01 (hopfield_pinv + float-tolerant analysis/hopfield.py), 05-02 (frozen protocol in
      deliverables/05-hopfield-qr.md section 3 + analysis/hopfield_qr_select.py's rule_identity/frozen
      constants), 05-06 (scripts/qr.py + make qr -> datos/prepared/qr_pm1.csv)"
provides:
  - "analysis/hopfield_qr.py: guarded Hebb recall driver over the five real QR (N=1369), refuses unless
    hopfield_qr_select.rule_identity accepts the protocol commit; writes overlaps.json, qr_facts.json,
    recall.csv, energy_trace.csv, protocol.json, verdict.json, run.json under
    analysis/results/hopfield/qr/ (not versioned)"
  - "analysis/hopfield_qr_figures.py: QR glyphs, 5x5 overlap heatmap, Hebb recovery-vs-noise curve (exact
    match + continuous |m| + sweeps/energy panels) and a per-step energy panel from energy_trace.csv;
    refuses to draw on a changed rule or network code"
  - "make hopfield-qr and make hopfield-qr-figures Makefile targets"
  - "verdict.json's hebb_fails=true (measured 0% exact recovery at noise 0, async), derived from the
    frozen D-02 rule applied to the actual recall.csv data - the honest finding Plan 04's pinv series
    answers"
affects: ["05-04 (pinv series reuses energy_trace_rows's rule-generic capture and recall.csv's RECALL_COLUMNS
    shape; fills verdict.json's pinv_* fields)", "05-05 (limitations section draws on overlaps.json /
    qr_facts.json)", "deliverables/05-hopfield-qr.md sections 1, 2 and 4"]

# Actuals (#2632)
actuals:
  tokens: 11015
  tasks: 3
  commits: 3
  plan_head_before: 8a47b63b40ec878c348e3af3156f8bda28b8d62b
  plan_head_after: 5e43a5e6ff45527baeb308a9c4eff9abb550f8ea

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "energy_trace.csv has no seed column by design: the driver captures the traced trial (trace_trials=1)
      of ONE fixed seed (the first frozen seed, hopfield_qr_select.SEEDS[0]) per (source, noise) cell of
      the async reference update, not all ten seeds - mixing seeds under the same key would interleave
      independent per-step sequences and could look non-monotonic even though every single run's async
      energy never rises (discovered empirically during this plan's own verification, fixed before commit)"
    - "energy_trace_rows(ran, rule, seed) is written generic over `rule` so Plan 04's pinv series appends
      its own per-step rows with no further code"
    - "verdict.json's pinv_* fields are left null at this plan (Plan 04 fills them); the file is written
      once, not re-opened and merged, keeping each plan's write self-contained"

key-files:
  created:
    - analysis/hopfield_qr.py
    - analysis/hopfield_qr_figures.py
    - analysis/tests/test_hopfield_qr.py
  modified:
    - Makefile

key-decisions:
  - "MAX_SWEEPS=200 and TRACE_TRIALS=1 are implementation parameters local to analysis/hopfield_qr.py, not
    read from hopfield_qr_select.py: the frozen protocol (D-01..D-11) fixes the noise grid, trial/seed
    counts, updates, subset and verdict thresholds, but never a sweep ceiling or trace width - those are
    implementation choices, documented as such in a module comment."
  - "energy_trace.csv captures exactly one fixed seed (ENERGY_TRACE_SEED = hopfield_qr_select.SEEDS[0] = 1)
    per (source, noise) cell, chosen by index before looking at any curve, to match the file's seedless
    column schema (rule, update, source, noise, step, energy) specified by the plan."
  - "mean_final_overlap in recall.csv is the mean of the ABSOLUTE final overlap |m| with the pattern that
    was perturbed (own m_a, not a signed mean), per the plan's explicit D-03 wording."
  - "The per-step energy figure (energy_trace.svg) uses a fixed 3-level, 5-source grid (noise 0.0, 0.25,
    0.5 - start/middle/top of the frozen grid, picked by index) rather than all 11 levels, to keep one
    figure legible; all 11 levels are in energy_trace.csv itself for anyone who wants the full detail."

requirements-completed: [HOP-04, HOP-05]

coverage:
  - id: D1
    description: "make hopfield-qr drives the Hebb rule over the five real QR (N=1369) under both updates,
      refusing unless the Plan 02 protocol commit is in place, and writes recall.csv covering the 11-level
      0..0.5 noise grid with 30 trials and 10 seeds, well over the HOP-05 floor"
    requirement: "HOP-05"
    verification:
      - kind: integration
        ref: "make hopfield-qr (manual run this plan): RUN_OK, 20/20 runs ok, recall.csv 22 rows (2 updates
          x 11 levels)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The Hebb D-02 verdict (fails iff exact recovery at noise 0 async < 100%) is computed from
      the actual recall output and recorded in verdict.json as a finding, not hard-asserted; measured
      recall at noise 0 async is 0%, so hebb_fails=true, matching PITFALLS.md Pitfall 1's prior measurement
      but derived independently here from this run's own data"
    requirement: "HOP-05"
    verification:
      - kind: integration
        ref: "plan verify script (HEBB_VERDICT_RECORDED): re-derives hebb_fails from recall.csv and compares
          to verdict.json"
        status: pass
    human_judgment: false
  - id: D3
    description: "The 5x5 overlap matrix, the fraction of pixels identical in all five QR and the minimum
      pairwise Hamming distance are computed in numpy as input facts (max|overlap|=0.86, identical
      fraction=69.8%, min pairwise Hamming=96 - matching PITFALLS.md Pitfall 1's prior measurement)"
    requirement: "HOP-04"
    verification:
      - kind: integration
        ref: "plan verify script (FACTS_OK) + analysis/results/hopfield/qr/overlaps.json,qr_facts.json"
        status: pass
      - kind: unit
        ref: "analysis/tests/test_hopfield_qr.py#test_overlap_matrix_equals_p_pt,
          test_identical_fraction_is_the_fraction_of_constant_columns,
          test_min_pair_hamming_matches_the_known_minimum"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every C run passes analysis/hopfield.check_recall before aggregation (a disagreement
      removes the output and stops the driver); the async per-step energy in energy_trace.csv is
      non-increasing within tolerance in every traced cell (HOP-05 'energia por paso')"
    requirement: "HOP-05"
    verification:
      - kind: integration
        ref: "make hopfield-qr: 20/20 check_recall passes; plan verify script PER_STEP_ENERGY_OK"
        status: pass
    human_judgment: false
  - id: D5
    description: "make hopfield-qr-figures draws the QR glyphs, the overlap heatmap, the Hebb recovery
      curve (exact match, continuous |m|, sweeps/energy) and the per-step energy panel, reproducibly
      (byte-identical SVG on rerun), refusing on a changed rule or network code"
    requirement: "HOP-04,HOP-05"
    verification:
      - kind: integration
        ref: "make hopfield-qr-figures (FIGS_OK), cmp -s rerun (SVG_REPRODUCIBLE), Makefile grep (MK_FIGS)"
        status: pass
    human_judgment: true
    rationale: "Figure legibility and layout (legend placement, caption wording, color scale) were
      inspected visually this plan but are a judgment call a human reviewer should confirm at UAT."

# Metrics
duration: 70min
completed: 2026-10-25
status: complete
---

# Phase 5 Plan 3: Hebb recall over the five QR - guarded driver, tracer figures, tests Summary

**The tracer slice of Phase 5 end to end: PNG-to-pm1 input -> guarded Hebb driver -> C core at N=1369 -> numpy cross-check -> aggregated recall/energy -> figures, with the Hebb D-02 verdict computed honestly from the measured data (0% exact recovery at every noise level, confirming the pre-registered hypothesis without hard-coding it).**

## Performance

- **Duration:** 70 min (including a mid-session interruption/resume with no rework)
- **Started:** 2026-10-24T23:56:00Z (approx.)
- **Completed:** 2026-10-25T01:06:19Z
- **Tasks:** 3
- **Files modified:** 3 created, 1 modified (Makefile)

## Accomplishments

- `analysis/hopfield_qr.py`: end-to-end guarded driver. Refuses to run unless
  `hopfield_qr_select.rule_identity` accepts the Plan 02 protocol commit and `datos/prepared/qr_pm1.csv`
  matches the committed PNGs. Runs the Hebb rule over both updates (async reference, sync comparison), the
  10 frozen seeds and the 11-level 0..0.5 noise grid (30 trials/level); every C run passes
  `analysis/hopfield.check_recall` before aggregation.
- Writes `overlaps.json` / `qr_facts.json` (HOP-04): the five QR's max |overlap| = 0.86, mean |overlap| =
  0.67, 69.8% of pixels identical across all five, minimum pairwise Hamming distance = 96 of 1369 -
  matching `PITFALLS.md` Pitfall 1's prior measurement, computed here independently from this run's own
  data, not copied.
- `recall.csv`: Hebb's exact recovery rate is 0% at every one of the 22 (update, noise) cells, including
  noise 0 - the QR are not even fixed points for Hebb before any noise is added. The continuous mean
  |final overlap| with the target sits flat at ~0.79 regardless of noise, and `mean_final_energy` is
  identical across noise levels too, consistent with the network collapsing to one common attractor
  regardless of the query.
- `energy_trace.csv` and `verdict.json`: `hebb_fails = true` is derived by applying the frozen D-02
  threshold ("exact recovery at noise 0 async < 100%") to the measured 0% - recorded as a finding, never
  hard-coded to the prediction. The async per-step energy trace is non-increasing in every traced cell.
- `analysis/hopfield_qr_figures.py`: four reproducible figures (QR glyphs, overlap heatmap, recovery/overlap/
  cost-energy curve, per-step energy panels) under `analysis/results/hopfield/qr/figures/`, refusing to draw
  on a changed protocol or network code (mirrors Phase 4's WR-02).
- `analysis/tests/test_hopfield_qr.py`: 6 passing tests covering the pure numpy helpers (hand-computed on a
  5x5 "staircase" fixture) and the guard refusal (monkeypatched `rule_identity` raising, driver propagates
  and creates no output directory).

## Task Commits

Each task was committed atomically:

1. **Task 1: guarded Hebb recall driver over the five QR, end to end (analysis/hopfield_qr.py)** -
   `2b268ba` (feat)
2. **Task 2: tracer figures - QR glyphs, 5x5 overlap matrix, Hebb recovery curve
   (analysis/hopfield_qr_figures.py)** - `920c506` (feat)
3. **Task 3: tests for the driver's pure helpers and the guard refusal
   (analysis/tests/test_hopfield_qr.py)** - `5e43a5e` (test)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified

- `analysis/hopfield_qr.py` - guarded driver: `Design`/`default_design`, `overlap_matrix` /
  `identical_fraction` / `min_pair_hamming` / `overlaps_json` / `qr_facts_json`, `recall_series` /
  `run_series` / `aggregate_recall`, `energy_trace_rows`, `protocol_json` / `verdict_json`, `code_identity`
  family, `run()` / `main()`
- `analysis/hopfield_qr_figures.py` - `plot_qr`, `plot_overlaps`, `plot_recall_noise`, `plot_energy_trace`,
  `require_same_code`, `draw()` / `main()`
- `analysis/tests/test_hopfield_qr.py` - 6 tests on the pure helpers and the guard refusal
- `Makefile` - `hopfield-qr` (depends on `qr`) and `hopfield-qr-figures` targets, both added to `.PHONY`

## Decisions Made

- `MAX_SWEEPS` (200) and `TRACE_TRIALS` (1) live as module constants in `analysis/hopfield_qr.py`, not in
  `analysis/hopfield_qr_select.py`: the frozen protocol (D-01..D-11) never fixes a sweep ceiling or trace
  width, only the noise grid, trial/seed counts, updates, subset and verdict thresholds. Documented inline
  as implementation parameters, not part of the pre-registration.
- `ENERGY_TRACE_SEED = hopfield_qr_select.SEEDS[0]` (seed 1): `energy_trace.csv`'s column schema (rule,
  update, source, noise, step, energy) has no seed column, by the plan's own specification. The first
  implementation captured all 10 seeds' traces under the same (source, noise) key, which the plan's own
  per-step monotonicity verify check correctly flagged as a failure (interleaved sequences from different
  seeds can look non-monotonic even though each individual seed's async run never raises energy). Fixed by
  restricting the capture to one fixed seed, picked by index before looking at any curve.
- `mean_final_overlap` is the mean of `|m_a|` (absolute overlap with the pattern that was perturbed), per
  the plan's explicit instruction, not a signed mean - this matters here because the network's common
  attractor could in principle have negative overlap with some targets.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] energy_trace.csv mixed all 10 seeds' traces under one (source, noise) key**
- **Found during:** Task 1's own verification (the plan's `PER_STEP_ENERGY_OK` check)
- **Issue:** The first implementation of `energy_trace_rows` looped over every `Ran` item of the async
  update across all 10 seeds, writing one traced-trial sequence per seed under the same `(source, noise)`
  key with no seed column to distinguish them. Grouping and sorting by `(source, noise, step)` then
  interleaved ten independent async energy sequences (each individually non-increasing, but with different
  convergence speeds), which the monotonicity check correctly rejected as 56 MB of mixed data.
- **Fix:** Added `ENERGY_TRACE_SEED` (the first frozen seed) and restricted `energy_trace_rows` to only the
  `Ran` items whose `task.seed == seed`, matching the file's seedless column schema exactly as specified by
  the plan. Reduced the file from ~56 MB (10 seeds) to ~5.7 MB (1 seed); the per-step monotonicity check
  then passed cleanly.
- **Files modified:** `analysis/hopfield_qr.py`
- **Committed in:** `2b268ba` (Task 1 commit) - the fix landed before the first commit, so no separate
  commit exists for it.

---

**Total deviations:** 1 auto-fixed (Rule 1, caught and fixed by the plan's own verify script before
committing - no broken state was ever committed).
**Impact on plan:** No scope creep; the fix is confined to `energy_trace_rows` and a two-line module
constant, with no change to any other output's shape or the frozen protocol.

## Issues Encountered

- The full `make hopfield-qr` run (20 C binary runs at N=1369: 5 patterns x 11 levels x 30 trials x 2
  updates x 10 seeds = 33,000 trials total) takes roughly 3 minutes wall-clock in this environment. An
  early verification attempt used a 300s foreground `timeout` wrapper that killed the process mid-run
  (exit 143) before it could finish writing `run.json`; this was an artifact of the verification harness,
  not a defect in the driver - the actual run completes well within its own `max_sweeps` bound. Re-run
  without the artificial timeout completed cleanly (`EXIT:0`).
- A mid-session usage-limit interruption occurred after the required-reading phase but before any file was
  written; the resumed session verified via `git log`/`git status` that no partial work existed and
  restarted cleanly from Task 1, per the coordinator's explicit resume instructions.

## Known Stubs

None. `analysis/results/hopfield/qr/` (recall.csv, overlaps.json, qr_facts.json, energy_trace.csv,
protocol.json, verdict.json, run.json, figures/) is generated output, not committed as source, per the
plan's prohibition and the project's "results generated no se versionan" convention.

## Threat Flags

None - the plan's `<threat_model>` already covers the three new-surface threats this plan touches
(T-05-06 qr_pm1.csv into the C binary via `is_pm_one`, T-05-07 trace/weight memory at N=1369 bounded by
`trace_trials=1` and the existing `NEURONS_MAX`/`TRACE_ROWS_MAX` core limits, T-05-SC no new package
installs). No new trust boundary was introduced.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 04 (pseudo-inverse series) can reuse `recall_series`/`run_series`/`aggregate_recall`'s shape
  (RECALL_COLUMNS already has a `rule` column) and `energy_trace_rows`'s rule-generic signature with no
  change to this plan's code; it only needs to call them with `rule="pinv"` and fill `verdict.json`'s
  `pinv_exact_recovery_noise0_async` / `pinv_works` / `pinv_rule` fields (left `null` here).
- Plan 05 (limitations, HOP-07) can read `overlaps.json` and `qr_facts.json` directly - both are
  independent of any network run and already contain the correlation-as-root-cause evidence (max/mean
  |overlap|, identical fraction, minimum pairwise Hamming).
- `deliverables/05-hopfield-qr.md` sections 1 ("Algoritmo y salidas"), 2 ("Los 5 QR y su preparacion") and
  4 ("Hebb: estabilidad y curva de ruido") are still placeholder text ("Se completa en el Plan 05... 03/05")
  per Plan 02's explicit scoping; this plan produced the data and figures those sections will cite but did
  not write deliverable prose, matching the plan's own `<output>` spec (only the SUMMARY.md was required).
- Known pre-existing, unrelated: `datos/letters/alphabet_5x5.txt` CRLF causes pre-existing unrelated
  `test_hopfield_select.py`/`test_letters.py` failures in this environment (`core.autocrlf=input`); logged
  already in STATE.md and `deferred-items.md` from Plan 01, not touched by this plan.

## Self-Check: PASSED

- FOUND: analysis/hopfield_qr.py
- FOUND: analysis/hopfield_qr_figures.py
- FOUND: analysis/tests/test_hopfield_qr.py
- FOUND: .planning/phases/05-hopfield-con-qr/05-03-SUMMARY.md
- FOUND commit 2b268ba (Task 1) on HEAD
- FOUND commit 920c506 (Task 2) on HEAD
- FOUND commit 5e43a5e (Task 3) on HEAD

---
*Phase: 05-hopfield-con-qr*
*Completed: 2026-10-25*
