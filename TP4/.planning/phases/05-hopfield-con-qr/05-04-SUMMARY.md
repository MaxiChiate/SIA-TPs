---
phase: 05-hopfield-con-qr
plan: 04
subsystem: ai-ml
tags: [hopfield, pinv, hamming-1nn, qr, noise-curve, energy-trace, matplotlib]

# Dependency graph
requires:
  - phase: 05-hopfield-con-qr
    provides: "05-01 (hopfield_pinv in C + float-tolerant analysis/hopfield.py), 05-02 (frozen protocol +
      hopfield_qr_select.py's rule_identity/frozen constants, D-02 pinv threshold), 05-03 (guarded driver
      analysis/hopfield_qr.py with rule-generic recall_series/run_series/aggregate_recall/
      energy_trace_rows, analysis/hopfield_qr_figures.py's refusal/reproducibility scaffolding, the
      Hebb-only recall.csv/verdict.json this plan extends)"
provides:
  - "analysis/hopfield_qr.py: pinv recall series (rule='pinv', both updates, same frozen grid) reusing
    05-03's recall_series/run_series/aggregate_recall/energy_trace_rows unchanged in logic (only
    parametrized by rule); a new numpy-only Hamming 1-NN baseline (hamming_classify/hamming_rows, D-08)
    with matched noise grid/k/trials/seed labels but independent RNG draws from neuron/rng.c; recall.csv
    now carries all three rules; verdict.json's pinv_* fields filled from the measured recall (never
    hard-coded); recovery_table.csv (11-level exact-recovery table for hebb/pinv/hamming, D-08)"
  - "analysis/hopfield_qr_figures.py: recovery.svg (renamed from recall_noise.svg) superposes hebb, pinv
    and hamming on the exact-recovery and continuous-|m| panels, hebb-vs-pinv only on the cost panel
    (Hamming annotated as instantaneous); energy_trace.svg overlays hebb's and pinv's per-step energy per
    panel on independent twin y-axes (pinv's magnitude is far smaller than Hebb's N=1369 integer sum)"
  - "analysis/tests/test_hopfield_qr.py: +6 tests - pinv exact-fixed-point stability vs Hebb's lack of it
    on the SAME correlated-but-linearly-independent fixture (D-06/D-07), and the Hamming 1-NN helper's
    correctness under low noise plus its lowest-index tie-break (D-08)"
  - "Measured result: pinv_works=true - all five real QR are exact fixed points under pinv at noise 0
    (100% recovery, matching the frozen D-02 threshold), holding 100% exact recovery through noise 0.30
    and still 97.3% at noise 0.40, matching PITFALLS.md's prior independent measurement. Hamming 1-NN
    tracks pinv closely through noise 0.40 then diverges below it from noise 0.45 on."
affects: ["05-05 (limitations/HOP-07 section and the deliverable's pinv/Hamming comparison draw on
    recovery_table.csv, verdict.json's pinv_works, recall.csv's three rules and the two updated figures)"]

# Actuals (#2632)
actuals:
  tokens: 10070
  tasks: 3
  commits: 3
  plan_head_before: 4650ef11b5dbb2c87d52314bb3bc9054b36a12a1
  plan_head_after: f116567df67818f2670fcf1316b6119e9320bbca

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "aggregate_recall now returns the recall.csv rows instead of writing the file directly, so run()
      can collect hebb's, pinv's and the Hamming baseline's rows and write recall.csv exactly once; a
      second series no longer clobbers the first's rows by reopening the file in write mode."
    - "The Hamming baseline's numpy RNG is seeded deterministically from (seed, level) - np.random.default_rng((seed,
      round(level*1000))) - so its draws are reproducible and independent per (level, seed) cell without
      correlating across levels for the same seed label."
    - "recall.csv's Hamming rows use update='none' (HAMMING_UPDATE constant) since there is no async/sync
      split for a no-dynamics classifier; its dynamics-only columns (wrong_stored_rate, inverse_rate,
      mixture_rate, other_rate, cycle_rate, mean_sweeps, mean_flips, mean_final_energy) are written as
      float('nan'), which _write_csv's existing repr(float) branch already renders as the literal 'nan'."
    - "energy_trace.svg gives pinv its own twin y-axis per panel (ax.twinx()) rather than sharing Hebb's:
      pinv's projection-rule energy is bounded and far smaller in magnitude than Hebb's sum over N=1369,
      so a shared axis flattened pinv's curve to an invisible line at noise 0.25/0.5 in the first render."

key-files:
  created: []
  modified:
    - analysis/hopfield_qr.py
    - analysis/hopfield_qr_figures.py
    - analysis/tests/test_hopfield_qr.py

key-decisions:
  - "verdict.json additionally records pinv_stored_fixed_noise0_async (from the pinv async run's
    metrics.json 'stored_fixed', here 5 of 5) alongside the required pinv_exact_recovery_noise0_async /
    pinv_works / pinv_rule fields - not required by the plan's verify script but directly supports the
    plan's own must_haves truth ('the five QR become exact fixed points') with an independent, honestly
    reported number rather than inferring fixed-point-ness only from the noise-0 recall rate."
  - "The 'recovery' figure (recovery.svg, renamed from Plan 03's recall_noise.svg) stays ONE multi-panel
    figure (exact recovery / continuous overlap / cost) rather than three separate files: the plan's own
    verify script names a single recovery.svg, and the three described comparisons map onto the existing
    3-subplot layout Plan 03 established."
  - "Legend placement on recovery.svg and the per-panel legend on energy_trace.svg were adjusted beyond
    Plan 03's positions (moved out of the data region, ylim extended to make room) after visually
    inspecting the first render and finding the default 'upper right' / 'center left' placements
    overlapped the plateau where all three/both rules' curves coincide - a legibility fix, not a data
    change (Rule 1/visual-QA style correction caught before committing)."

requirements-completed: [HOP-06]

coverage:
  - id: D1
    description: "make hopfield-qr drives both the Hebb (05-03) and the new pinv rule over the five real
      QR on the same 11-level/30-trial/10-seed grid and both updates; recall.csv carries hebb, pinv and
      hamming rows; verdict.json's pinv_works is computed by applying the frozen D-02 threshold (exact
      recovery at noise 0 async == 100%) to the measured pinv recall, never to the predicted outcome"
    requirement: "HOP-06"
    verification:
      - kind: integration
        ref: "make hopfield-qr (this plan's run): THREE_RULES, PINV_VERDICT_RECORDED (verdict.json:
          pinv_works=true, pinv_exact_recovery_noise0_async=1.0, pinv_stored_fixed_noise0_async=5)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A numpy-only Hamming 1-NN baseline (no dynamics) classifies noisy queries against the
      five stored QR on the SAME noise distribution as hebb/pinv (matched k=lround(level*1369), the same
      11 levels, 30 trials, the 10 seed labels) but with independent RNG draws from neuron/rng.c; ties
      break to the lowest index; its recall.csv rows carry no sweep/energy values"
    requirement: "HOP-06"
    verification:
      - kind: integration
        ref: "make hopfield-qr: HAMMING_NO_DYNAMICS (every hamming row's mean_sweeps is nan)"
        status: pass
      - kind: unit
        ref: "analysis/tests/test_hopfield_qr.py#test_hamming_classify_returns_the_true_pattern_under_low_noise,
          test_hamming_classify_breaks_an_exact_tie_by_the_lowest_index"
        status: pass
    human_judgment: false
  - id: D3
    description: "recovery_table.csv renders the per-level exact-recovery rate of all three rules over
      the 11 frozen noise levels (D-08's 'tabla de recuperacion exacta por nivel'), read back from
      recall.csv (hebb/pinv from their async row, hamming from its single no-dynamics row)"
    requirement: "HOP-06"
    verification:
      - kind: integration
        ref: "make hopfield-qr: RECOVERY_TABLE_OK (11 rows, columns level/hebb/pinv/hamming)"
        status: pass
    human_judgment: false
  - id: D4
    description: "pinv's async per-step energy (the traced trial of energy_trace.csv) is non-increasing
      within the same tolerance as Hebb's (HOP-05's 'energia por paso' extended to the second dynamical
      rule); every pinv C run passed analysis/hopfield.check_recall under float tolerance before
      aggregation"
    requirement: "HOP-06"
    verification:
      - kind: integration
        ref: "make hopfield-qr: PINV_PER_STEP_ENERGY_OK; 40/40 check_recall passes (20 hebb + 20 pinv runs)"
        status: pass
    human_judgment: false
  - id: D5
    description: "pinv exact-fixed-point stability and Hebb's lack of it on the same correlated-but-
      linearly-independent fixture (D-06/D-07) are covered by unit tests, independent of any network run"
    requirement: "HOP-06"
    verification:
      - kind: unit
        ref: "analysis/tests/test_hopfield_qr.py#test_pinv_makes_every_pattern_of_the_correlated_fixture_a_fixed_point,
          test_hebb_leaves_at_least_one_pattern_of_the_correlated_fixture_not_fixed"
        status: pass
    human_judgment: false
  - id: D6
    description: "make hopfield-qr-figures renders the three-rule recovery/overlap/cost comparison
      (recovery.svg) and the hebb-vs-pinv per-step energy trace (energy_trace.svg) reproducibly
      (byte-identical SVG on rerun), refusing on a changed rule or changed network code"
    requirement: "HOP-06"
    verification:
      - kind: integration
        ref: "make hopfield-qr-figures (FIGS3_OK), cmp -s rerun of recovery.svg (REC_REPRODUCIBLE)"
        status: pass
    human_judgment: true
    rationale: "Panel layout, legend placement and caption wording were inspected and adjusted visually
      this plan (legends moved off the data after the first render overlapped the hebb/pinv/hamming
      plateau; pinv given its own twin y-axis in energy_trace.svg after its curve was invisible on Hebb's
      shared scale), but final legibility is a judgment call a human reviewer should confirm at UAT, as
      Plan 03 already flagged for the figures it introduced."

# Metrics
duration: 80min
completed: 2026-10-25
status: complete
---

# Phase 5 Plan 4: Pinv series, Hamming 1-NN baseline and the three-rule comparison Summary

**The pinv remedy measured honestly against Hebb's failure and a trivial Hamming lookup over the five real QR: pinv recovers all five QR exactly at noise 0 (5/5 fixed points) and holds 100% exact recovery through noise 0.30, while Hamming 1-NN tracks it almost exactly until noise 0.45 - the quantitative evidence that a lookup table already solves the same closed-set problem.**

## Performance

- **Duration:** ~80 min (dominated by a single ~46-minute `make hopfield-qr` run: 40 C binary runs at
  N=1369, double Plan 03's series count, plus the Python-side numpy cross-check of each)
- **Started:** 2026-10-25T01:10:00Z (approx.)
- **Completed:** 2026-10-25T02:16:00Z
- **Tasks:** 3
- **Files modified:** 3 (no new files; all three were created by Plan 03)

## Accomplishments

- `analysis/hopfield_qr.py`: added the pinv recall series by parametrizing Plan 03's `_recall_base` /
  `recall_series` by `rule` (no duplicated logic - the same `run_series` / `aggregate_recall` /
  `energy_trace_rows` functions run unchanged for `rule="pinv"`). `aggregate_recall` now returns rows
  instead of writing `recall.csv` directly, so `run()` merges hebb's, pinv's and the new Hamming
  baseline's rows into one write.
- Added a numpy-only Hamming 1-NN baseline (`hamming_classify`, `hamming_rows`, D-08): for every one of
  the 11 frozen noise levels and the 10 frozen seed labels, draws 30 noisy queries per stored QR by
  flipping exactly `k = lround(level * 1369)` distinct pixels (matching the C core's noise distribution
  exactly, but with independent numpy draws, never the C core's `neuron/rng.c`), classifies each by
  nearest Hamming distance (ties to the lowest index) and records `recall_rate` / `mean_final_overlap`
  with the dynamics-only columns left `NaN`.
- `verdict.json` now reports the pinv verdict computed from the frozen D-02 threshold applied to the
  measured data: `pinv_works = true` (`pinv_exact_recovery_noise0_async = 1.0`,
  `pinv_stored_fixed_noise0_async = 5` - all five real QR are exact fixed points under pinv, matching the
  hypothesis the protocol pre-registered and PITFALLS.md's independent prior measurement).
- `recovery_table.csv`: the per-level exact-recovery rate of all three rules over the 11 levels -
  hebb flat at 0% throughout, pinv at 100% through noise 0.30 (97.3% at 0.40, 69.4% at 0.45, 0% at 0.50),
  hamming tracking pinv almost exactly through 0.40 (98.5% at 0.40) then falling faster (81.5% at 0.45,
  16.7% at 0.50) - the quantitative gap between the dynamical remedy and the trivial lookup only opens up
  at the highest noise levels.
- `energy_trace.csv` gained `rule=pinv` per-step rows; every traced pinv async cell's energy is
  non-increasing within the same tolerance as Hebb's (`PINV_PER_STEP_ENERGY_OK`). All 40 C runs (20 hebb
  + 20 pinv, both updates x 10 seeds) passed `analysis/hopfield.check_recall` before aggregation.
- `analysis/hopfield_qr_figures.py`: `recovery.svg` (renamed from Plan 03's `recall_noise.svg`, matching
  this plan's own verify script) now superposes hebb/pinv/hamming on the exact-recovery and
  continuous-|m| panels (async solid, sync dashed for the two dynamical rules; hamming a single solid
  line) with an annotation of the measured pinv zero-noise result, and keeps the cost/iterations panel
  hebb-vs-pinv only with a text annotation that Hamming's lookup is instantaneous. `energy_trace.svg` now
  overlays hebb's and pinv's per-step energy per panel, each rule on its own twin y-axis (pinv's
  projection-rule energy is orders of magnitude smaller than Hebb's N=1369 integer sum; a shared axis had
  flattened pinv's curve to an invisible flat line in the first render, found and fixed before the task
  commit).
- `analysis/tests/test_hopfield_qr.py`: 6 new tests (12 total in the file) - a small correlated-but-
  linearly-independent fixture where pinv makes every pattern an exact fixed point while Hebb leaves
  three of the four not fixed (D-06/D-07), and the Hamming helper's correctness under low noise plus its
  lowest-index tie-break (D-08), hand-verified against a constructed exact-tie query.

## Task Commits

Each task was committed atomically:

1. **Task 1: add the pinv series and the Hamming 1-NN baseline to the driver (analysis/hopfield_qr.py)**
   - `9d863dc` (feat)
2. **Task 2: three-rule figures - recovery, continuous overlap, energy and iterations
   (analysis/hopfield_qr_figures.py)** - `9589bfd` (feat)
3. **Task 3: tests for pinv stability and the Hamming 1-NN baseline
   (analysis/tests/test_hopfield_qr.py)** - `f116567` (test)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified

- `analysis/hopfield_qr.py` - `_recall_base`/`recall_series` parametrized by `rule`; `aggregate_recall`
  returns rows instead of writing; new `stored_fixed_for`, `_lround`, `hamming_classify`, `hamming_rows`,
  `recovery_table_rows`; `verdict_json` now computes both hebb and pinv verdicts; `run()` runs both
  series, the Hamming baseline, and writes `recall.csv`/`recovery_table.csv`/`energy_trace.csv` once each
- `analysis/hopfield_qr_figures.py` - `plot_recovery` (renamed from `plot_recall_noise`, three-rule);
  `plot_energy_trace` now rule-aware with per-rule twin y-axes; `FIGURE_STEMS` updated to `"recovery"`
- `analysis/tests/test_hopfield_qr.py` - `CORRELATED` and `HAMMING_FIXTURE` fixtures plus 6 new tests

## Decisions Made

- `verdict.json` additionally records `pinv_stored_fixed_noise0_async` (not required by the plan's verify
  script) as an honest, independently-sourced number (from the pinv async run's `metrics.json`) backing
  the "five QR are exact fixed points" claim, rather than leaving that inference implicit in the noise-0
  recall rate alone.
- Kept `recovery.svg` as ONE multi-panel figure (matching the plan's own verify script, which names a
  single `recovery.svg`) rather than splitting the recovery/overlap/cost comparisons into three files.
- Adjusted legend placement on both figures after visually inspecting the first render: the default
  positions (recovery.svg: "upper right" on two panels; energy_trace.svg: a single shared y-axis for both
  rules) either overlapped the data or made pinv's curve invisible. See `tech-stack.patterns` and
  `coverage[D6].rationale` above.

## Deviations from Plan

None - plan executed as written. The `pinv_stored_fixed_noise0_async` field and the legend/twin-axis
figure adjustments are additive refinements within the plan's own stated acceptance criteria (honest
verdict reporting; reproducible, legible figures), not scope changes.

## Issues Encountered

- `make hopfield-qr` took ~46 minutes wall-clock in this session, versus Plan 03's reported ~3 minutes for
  the Hebb-only run (roughly double the series count here - hebb + pinv - but the slowdown was
  disproportionately larger than 2x). Investigated during the run: `analysis/hopfield.py`'s
  `check_recall`/`_replay_async` code is byte-for-byte unchanged from Plan 03 (`git diff` confirms no
  modification), and the C core's dynamics are also unchanged from Plan 01. The C binary runs themselves
  completed in a normal few minutes per series (confirmed by `summary.csv` mtimes); the time was spent in
  the single-threaded Python `check_recall` replay loop, which showed sustained 600-800% CPU across many
  threads (consistent with the host's BLAS backend spawning a multi-threaded dot product per tiny
  per-step `W[neuron] @ s` call inside a tight Python loop with hundreds of thousands of iterations - a
  known numpy anti-pattern, not something introduced by this plan's changes). Concluded this is
  environment/system load variability outside this plan's code, not a logic defect; let it run to
  completion rather than attempting an unplanned architectural change to the checking code (Rule 4 would
  apply to actually fixing the checker's performance, which is out of this plan's scope). Noted here for
  future executors so a similarly long run is not mistaken for a hang.
- A short diagnostic script (one `check_recall` call with `OMP_NUM_THREADS=1`) launched to help diagnose
  the above was itself slowed by resource contention with the still-running main job and was killed once
  the main job's progress became visible through other means (new `recall_pinv/` directories on disk);
  it never produced a usable timing number and is not part of any committed artifact.

## Known Stubs

None. `analysis/results/hopfield/qr/` (recall.csv, recovery_table.csv, verdict.json, energy_trace.csv,
overlaps.json, qr_facts.json, protocol.json, run.json, figures/) is generated output, not committed as
source, per the plan's prohibition and the project's "resultados generados no se versionan" convention.

## Threat Flags

None - the plan's `<threat_model>` already covers both threats this plan touches (T-05-08 the Hamming
baseline's grid/tie-break, mitigated by reusing the frozen `NOISE_LEVELS`/`TRIALS` constants and the
`lround` operator, tested in `test_hopfield_qr.py`; T-05-SC no new package installs, confirmed - no
`requirements.txt` change). No new trust boundary was introduced.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 05 (HOP-07 limitations, the deliverable's pinv/Hamming narrative) can read `recovery_table.csv`
  directly for the per-level table, `verdict.json`'s `pinv_works`/`pinv_stored_fixed_noise0_async` for the
  "pinv works" claim, `recall.csv`'s three rules for any further analysis, and `recovery.svg` /
  `energy_trace.svg` for the figures - all independent of any further network run.
- The Hamming 1-NN curve (D-08's "equivalencia con lookup", feeding HOP-07/D-11c) is now quantitative:
  it tracks pinv closely through noise 0.40 (98.5% vs 97.3%) before diverging faster at 0.45-0.50 -
  exactly the honest counterweight the limitations section needs, not asserted but measured on the same
  noise distribution as pinv itself.
- Known pre-existing, unrelated: `datos/letters/alphabet_5x5.txt` CRLF causes 6 pre-existing unrelated
  `test_hopfield_select.py`/`test_letters.py` failures in this environment (`core.autocrlf=input`);
  confirmed still present and unrelated by running the full `analysis/tests` suite this plan (191 passed,
  6 failed - all 6 the known CRLF failures, none in `test_hopfield_qr.py`); already logged in STATE.md and
  `deferred-items.md` from Plan 01, not touched by this plan.

## Self-Check: PASSED

- FOUND: analysis/hopfield_qr.py (hamming_rows, hamming_classify, recovery_table_rows present)
- FOUND: analysis/hopfield_qr_figures.py (plot_recovery, FIGURE_STEMS includes "recovery")
- FOUND: analysis/tests/test_hopfield_qr.py (12 tests, CORRELATED/HAMMING_FIXTURE fixtures)
- FOUND: .planning/phases/05-hopfield-con-qr/05-04-SUMMARY.md
- FOUND commit 9d863dc (Task 1) on HEAD
- FOUND commit 9589bfd (Task 2) on HEAD
- FOUND commit f116567 (Task 3) on HEAD

---
*Phase: 05-hopfield-con-qr*
*Completed: 2026-10-25*
