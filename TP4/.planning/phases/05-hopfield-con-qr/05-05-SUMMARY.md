---
phase: 05-hopfield-con-qr
plan: 05
subsystem: ai-ml
tags: [hopfield, qr, limitations, shift-sensitivity, majority-attractor, deliverable, hop-07]

# Dependency graph
requires:
  - phase: 05-hopfield-con-qr
    provides: "05-02 (frozen protocol + hopfield_qr_select.py's rule_identity), 05-03 (overlaps.json,
      qr_facts.json, the guarded recall driver's CODE_FILES/code_identity pattern this plan's
      LIMITS_CODE_FILES mirrors), 05-04 (recall.csv's three rules, recovery_table.csv, verdict.json's
      pinv_works/pinv_stored_fixed_noise0_async)"
provides:
  - "analysis/hopfield_qr_limits.py: guarded script (refuses on a changed protocol, D-01) computing the
    pixel-wise Hebb majority attractor (majority.json, differs from every stored QR by a positive
    Hamming distance, D-11a) and a by-hand numpy async forward run (own implementation, not a library
    and not hopfield.py's trace-replay) that evolves a 1px/2px zero-padded shift of a stored QR under
    the pinv W (shift.json, D-11b) - sanity-checked to keep an unshifted stored QR fixed first"
  - "analysis/hopfield_qr_figures.py: plot_shift (before/shifted/recovered triptych) and plot_majority
    (attractor glyph + per-target Hamming bar), reading qr_limits/ and refusing on a changed
    LIMITS_CODE_FILES identity (require_same_limits_code, mirrors the existing recall CODE_FILES
    refusal, WR-02)"
  - "make hopfield-qr-limits Makefile target (depends on qr), writing under
    analysis/results/hopfield/qr_limits/ - a directory make hopfield-qr never rmtrees"
  - "deliverables/05-hopfield-qr.md: all result sections (1, 2, 4, 5, 6, 7) filled with measured
    numbers traced to result files; the four-facet HOP-07 limitations with evidence; the per-level
    recovery table for hebb/pinv/hamming; a working Como reproducir section. The frozen protocol
    (section 3, between the rule markers) is byte-identical to the Plan 02 commit."
affects: ["Phase 6 (consumes deliverables/05-hopfield-qr.md as the Hopfield-on-QR fragment)"]

# Actuals (#2632)
actuals:
  tokens: 13459
  tasks: 3
  commits: 3
  plan_head_before: 89cc225ba3228aacc6409d4abceecd8339395a77
  plan_head_after: fa770ec6aeecb8a197bae9b4f436839905237ef1

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "by_hand_async_run (analysis/hopfield_qr_limits.py) is a from-scratch numpy implementation of the
      asynchronous dynamics - NOT hopfield.py's _replay_async, which only replays a trace the C core
      already saved. This one actually drives the network from a query handed to it (field = W s kept
      incrementally after every flip, sign(h) or keep state on h == 0, a fresh permutation per sweep),
      needed because the shift demo's shifted query never goes through the C core at all."
    - "shift.json carries the full query/recovered/source_pattern pixel vectors (not just the Hamming
      numbers) so hopfield_qr_figures.py only plots and never re-runs the network dynamics itself -
      the limitation generator (hopfield_qr_limits.py) is the sole place the dynamics execute."
    - "qr_limits/ is a directory SIBLING of qr/ (both under analysis/results/hopfield/), guarded by its
      own LIMITS_CODE_FILES code_identity (no neuron binary hash, since this script never calls the C
      core) rather than being folded into the recall driver's run.json or rmtree scope."

key-files:
  created:
    - analysis/hopfield_qr_limits.py
  modified:
    - analysis/hopfield_qr_figures.py
    - analysis/tests/test_hopfield_qr.py
    - Makefile
    - deliverables/05-hopfield-qr.md

key-decisions:
  - "The majority attractor and the shift demo's source QR are both chosen by a fixed index (SHIFT_SOURCE
    = 0, the first QR in scripts/qr.py SOURCES order) before looking at any result, matching the existing
    convention (hopfield_qr.py's ENERGY_TRACE_SEED, hopfield_qr_figures.py's ENERGY_LEVELS)."
  - "The shift gate records whatever recovered_hamming turns out to be and never asserts it is positive
    (D-11b's explicit prohibition); the measured result is severe - a 1-2 px shift moves 51-54% of the
    1369 pixels (more than any i.i.d. noise level evaluated in Plan 04) and the pinv network's recovered
    state ends up FARTHER from the source (75-88%) than the shifted query itself, reported as a finding."
  - "The Hamming 1-NN baseline equals or exceeds pinv's exact-recovery rate at the two highest noise
    levels (81.5% vs 69.4% at 0.45; 16.7% vs 0% at 0.50, from Plan 04's recovery_table.csv) - reported
    honestly in deliverable section 5 as a 'the lookup is not just close, it actually wins' finding,
    sharpening the D-11c lookup-equivalence limitation beyond what the prior plan's SUMMARY framed as
    'tracks closely then diverges'."

requirements-completed: [HOP-07]

coverage:
  - id: D1
    description: "The pixel-wise majority of the five QR (the common Hebb attractor) is computed in
      numpy and shown to differ from every stored QR by a positive Hamming distance (225, 225, 71, 103,
      91 of 1369) - the correlation root cause of Hebb's failure (D-11a)"
    requirement: "HOP-07"
    verification:
      - kind: integration
        ref: "make hopfield-qr-limits (MAJORITY_OK): all 5 hamming_to_targets >= 1"
        status: pass
      - kind: unit
        ref: "analysis/tests/test_hopfield_qr.py#test_majority_attractor_differs_from_every_target,
          test_majority_json_reports_hamming_and_overlap_to_every_target"
        status: pass
    human_judgment: false
  - id: D2
    description: "A 1px and 2px shift of a stored QR, evolved under the pinv network by a by-hand async
      run, records the measured query/recovered Hamming distances as a finding, never forcing the
      predicted breakage (D-11b); the by-hand runner is sanity-checked to keep an unshifted stored QR
      fixed (0 flips) before its shift result is trusted"
    requirement: "HOP-07"
    verification:
      - kind: integration
        ref: "make hopfield-qr-limits (SHIFT_RECORDED): both 1px/2px entries present with positive
          query_hamming and non-negative recovered_hamming"
        status: pass
      - kind: unit
        ref: "analysis/tests/test_hopfield_qr.py#test_by_hand_async_run_keeps_an_unshifted_fixed_point_fixed,
          test_by_hand_async_run_actually_moves_an_unstable_pattern,
          test_shift_pattern_zero_pads_with_light_and_preserves_the_rest"
        status: pass
    human_judgment: false
  - id: D3
    description: "make hopfield-qr-limits writes majority.json/shift.json/run.json under its own
      qr_limits/ directory (never make hopfield-qr's qr/), refuses on a changed protocol, and records
      code_identity over LIMITS_CODE_FILES so hopfield_qr_figures.py can refuse on stale code"
    requirement: "HOP-07"
    verification:
      - kind: integration
        ref: "make hopfield-qr-limits (LIMITS_OK); require_same_limits_code refusal manually verified
          against a tampered code_identity"
        status: pass
    human_judgment: false
  - id: D4
    description: "The shift triptych (source/shifted/recovered glyphs with measured Hamming annotations)
      and the majority-attractor figure render reproducibly (byte-identical SVG on rerun) and refuse on
      a changed rule, recall CODE_FILES hash, or LIMITS_CODE_FILES hash"
    requirement: "HOP-07"
    verification:
      - kind: integration
        ref: "make hopfield-qr-figures (LIMIT_FIGS_OK), cmp -s rerun of shift.svg
          (SHIFT_SVG_REPRODUCIBLE)"
        status: pass
    human_judgment: true
    rationale: "Panel spacing on both new figures was adjusted after the first render (row titles
      collided with the glyph above on the shift triptych; the bar y-label crowded the value labels on
      the majority figure) - a legibility fix a human reviewer should confirm at UAT, as Plans 03-04
      already flagged for their own figures."
  - id: D5
    description: "deliverables/05-hopfield-qr.md's result sections (1, 2, 4, 5, 6, 7) report every
      number traced to a result file, the hebb/pinv verdicts verbatim from verdict.json, a per-level
      recovery table cross-checked against recovery_table.csv, the four HOP-07 limitation facets with
      evidence, the decoding-not-verified statement (D-10), and a working Como reproducir; the frozen
      protocol (section 3) is untouched and the guard still passes with no new commit"
    requirement: "HOP-07"
    verification:
      - kind: integration
        ref: "plan verify script: MARKERS_INTACT, GUARD_STILL_PASSES, DECODING_STATED, REPRODUCE_OK,
          RECOVERY_TABLE_RENDERED (all 5 checks pass)"
        status: pass
    human_judgment: false

# Metrics
duration: 25min
completed: 2026-10-25
status: complete
---

# Phase 5 Plan 5: QR limitations evidence and the completed deliverable Summary

**The four HOP-07 limitation facets backed by measured numbers and figures - the Hebb majority attractor (differs from every QR by 71-225 pixels), the shift demo (a 1-2 px shift moves more pixels than any noise level tested and pinv's recovery makes it worse, not better), the Hamming lookup actually beating pinv at the two highest noise levels, and the Reed-Solomon argument stated honestly as decoding-not-verified - assembled into the completed deliverables/05-hopfield-qr.md that closes Phase 5.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-10-24T23:27:00-03:00 (approx., after 05-04's final commit)
- **Completed:** 2026-10-24T23:50:15-03:00
- **Tasks:** 3
- **Files modified:** 1 created, 4 modified

## Accomplishments

- `analysis/hopfield_qr_limits.py`: a new guarded script (refuses unless `hopfield_qr_select.rule_identity`
  accepts the Plan 02 protocol commit) computing the pixel-wise Hebb majority attractor and running a
  from-scratch numpy asynchronous forward implementation (`by_hand_async_run` - our own code, not
  `hopfield.py`'s trace-replay) to evolve a 1px/2px zero-padded shift of the "beverages" QR under the pinv
  network. Sanity-checked first: the SAME runner keeps an unshifted stored QR fixed (0 flips), agreeing
  with the C core's `stored.csv` `fixed == 1`.
- `majority.json`: the majority attractor differs from every one of the five QR by a positive Hamming
  distance (225 beverages, 225 dessert, 71 food, 103 specials, 91 wine, of 1369) - matching
  `PITFALLS.md` Pitfall 1's prior order of magnitude, and matching `recall.csv`'s `mean_final_overlap`
  (0.791) exactly when averaged, confirming this is indeed the single attractor Hebb's dynamics collapses
  to regardless of noise level or which QR was queried.
- `shift.json`: measured, never forced - a 1px shift moves 741/1369 pixels (54.1%, more than any i.i.d.
  noise level evaluated in Plan 04) and pinv's recovered state ends up at 1034/1369 (75.5%) from the
  source, FARTHER than the shifted query itself; a 2px shift gives 699/1369 query and 1198/1369 (87.5%)
  recovered. A small geometric shift is far more damaging to pixel-wise recall than i.i.d. noise of
  similar or even larger apparent magnitude.
- `analysis/hopfield_qr_figures.py`: two new figures - the shift triptych (`shift.svg`, source/shifted/
  recovered glyphs with the measured Hamming annotations) and the majority-attractor figure (`majority.svg`,
  glyph plus a per-target Hamming bar) - reading `qr_limits/` and refusing to draw if `LIMITS_CODE_FILES`'s
  sha256 changed since the limitation run (`require_same_limits_code`, mirrors the existing recall-code
  refusal).
- `make hopfield-qr-limits` Makefile target, writing under `analysis/results/hopfield/qr_limits/` - a
  directory `make hopfield-qr` never touches, so a recall rerun can never delete the limitation evidence.
- `deliverables/05-hopfield-qr.md`: all six remaining placeholder sections filled with numbers traced to
  result files - the Hebb and pinv verdicts reported verbatim from `verdict.json`, a per-level
  exact-recovery table for hebb/pinv/hamming rendered from `recovery_table.csv`, the per-step energy
  citation (HOP-05), and the four-facet HOP-07 limitations section with the Reed-Solomon argument stated
  in text with decoding explicitly declared **not verified** (D-10). The frozen protocol (section 3) is
  byte-identical to the Plan 02 rule commit; `hopfield_qr_select.py identity` still exits 0.

## Task Commits

Each task was committed atomically:

1. **Task 1: majority attractor and shift-sensitivity evidence (analysis/hopfield_qr_limits.py)** -
   `37bfd4c` (feat)
2. **Task 2: shift triptych and majority-attractor figures (analysis/hopfield_qr_figures.py)** -
   `dce2b04` (feat)
3. **Task 3: write the deliverable result sections and Como reproducir
   (deliverables/05-hopfield-qr.md)** - `fa770ec` (docs)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified

- `analysis/hopfield_qr_limits.py` - `majority_attractor`/`majority_json`, `by_hand_async_run`,
  `_sanity_check_unshifted_fixed`, `shift_pattern`/`shift_json`, `code_identity`/`changed_code_files`
  over `LIMITS_CODE_FILES`, `run()`/`main()`
- `analysis/hopfield_qr_figures.py` - `plot_shift`, `plot_majority`, `require_same_limits_code`;
  `FIGURE_STEMS` extended with `"shift"`/`"majority"`; `draw()` reads `qr_limits/` and refuses on stale
  `LIMITS_CODE_FILES`
- `analysis/tests/test_hopfield_qr.py` - +9 tests (majority attractor on a hand-verified fixture, the
  by-hand runner's fixed-point sanity and its actually-flips counterpart, the shift builder's edge
  convention, shift.json's full pixel vectors)
- `Makefile` - `hopfield-qr-limits` target (depends on `qr`), added to `.PHONY`
- `deliverables/05-hopfield-qr.md` - sections 1, 2, 4, 5, 6, 7 filled; section 3 (frozen protocol)
  untouched

## Decisions Made

- `SHIFT_SOURCE = 0` (the first QR, "beverages") and `SHIFT_SEED = 1` are fixed by index before looking
  at any result, matching the existing convention set by `hopfield_qr.py`'s `ENERGY_TRACE_SEED` and
  `hopfield_qr_figures.py`'s `ENERGY_LEVELS`.
- The shift gate reports the measured `recovered_hamming` as-is and never asserts it is positive; the
  actual measurement (recovered farther from the source than the shifted query itself) is a stronger
  finding than the research's prediction of mere "breakage," and is reported honestly as such rather than
  softened.
- Section 5 of the deliverable states plainly that the Hamming 1-NN baseline equals or *exceeds* pinv's
  exact-recovery rate at the two highest noise levels (measured in Plan 04's `recovery_table.csv`: 81.5%
  vs 69.4% at noise 0.45; 16.7% vs 0% at noise 0.50) - a sharper framing of the D-11c lookup-equivalence
  limitation than "tracks closely then diverges," since the direction of the gap favors the trivial
  lookup, not the dynamical network.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - blocking issue] shift.json needed the full pixel vectors, not just the Hamming numbers, for Task 2's figure**
- **Found during:** Task 2 (writing `plot_shift`)
- **Issue:** Task 1's `shift_json` (as first written) recorded only `query_hamming`/`recovered_hamming`
  per shift magnitude. The shift triptych figure the plan requires (source/shifted/recovered glyphs)
  needs the actual pixel vectors of the shifted query and the recovered state, which were never run
  through the C core and so exist nowhere else - without them, `plot_shift` would have had to re-run the
  network dynamics itself, violating the "figures only plot" separation the rest of the codebase follows.
- **Fix:** Extended `shift_json` to also write `query`, `recovered` (per shift entry) and `source_pattern`
  (top-level) as pixel lists; added a unit test (`test_shift_json_includes_the_full_pixel_vectors_for_the_figures`)
  on a small synthetic fixture; re-ran `make hopfield-qr-limits` to regenerate `shift.json` with the new
  fields before Task 2's figures were drawn.
- **Files modified:** `analysis/hopfield_qr_limits.py`, `analysis/tests/test_hopfield_qr.py`
- **Committed in:** `dce2b04` (Task 2 commit, since the fix was discovered and made while implementing
  Task 2, not after Task 1's own commit).

**2. [Rule 1 - visual-QA bug] shift triptych row titles collided with the image above; majority figure's bar y-label crowded its value labels**
- **Found during:** Task 2's own visual inspection of the first render
- **Issue:** `plot_shift`'s default `tight_layout` spacing was too tight for a 2-row, 3-column grid of
  titled glyphs: the second row's titles overlapped the first row's images. `plot_majority`'s bar chart
  value labels crowded the y-axis label at the default `tight_layout` margins.
- **Fix:** Replaced `tight_layout` with explicit `fig.subplots_adjust(hspace=..., top=..., bottom=...)`
  calls tuned for each figure's layout, and added headroom to the bar chart's y-limit for its value
  labels - a legibility fix, not a data change (same pattern Plans 03-04 used for their own figures).
- **Files modified:** `analysis/hopfield_qr_figures.py`
- **Committed in:** `dce2b04` (Task 2 commit; the fix landed before the commit, so no separate commit
  exists for it).

---

**Total deviations:** 2 auto-fixed (Rule 3 extending `shift_json`'s output for the figure's own needs;
Rule 1 visual-QA spacing fixes caught before committing - no broken state was ever committed).
**Impact on plan:** No scope creep; both fixes are confined to the two files Task 1/2 already owned and
serve exactly the acceptance criteria those tasks specify (the triptych figure, legible rendering).

## Issues Encountered

- `make test` (run once at the end of this plan, covering the full C ASan/UBSan suite plus all of
  `analysis/tests/`) took ~2m41s and reported 198 passed, 6 failed - the SAME 6 pre-existing CRLF
  failures in `datos/letters/alphabet_5x5.txt` already logged in STATE.md and `deferred-items.md` since
  Plan 01 (`test_hopfield_select.py` x3, `test_letters.py` x3), confirmed still unrelated to this plan's
  changes (none of the 19 `test_hopfield_qr.py` tests - 12 pre-existing + 7 new this plan - are among the
  failures). Not fixed, per the documented out-of-scope decision.

## Known Stubs

None. `analysis/results/hopfield/qr_limits/` (majority.json, shift.json, run.json) is generated output,
not committed as source, per the project's "resultados generados no se versionan" convention.

## Threat Flags

None - the plan's `<threat_model>` already covers both threats this plan touches (T-05-09 deliverable
overclaiming, mitigated by every number tracing to a result file and the required decoding-not-verified
statement; T-05-10 a marker-text edit, mitigated by the marker-count and guard-identity checks both
passing after this plan's edits). No new trust boundary was introduced.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 5 is now complete: HOP-04, HOP-05, HOP-06 and HOP-07 are all marked complete in
  `.planning/REQUIREMENTS.md`, and `deliverables/05-hopfield-qr.md` has no remaining placeholder
  sections.
- Phase 6 can consume `deliverables/05-hopfield-qr.md` (all 7 sections) and the figures under
  `analysis/results/hopfield/qr/figures/` (qr, overlaps, recovery, energy_trace, shift, majority) directly.
- Known pre-existing, unrelated: `datos/letters/alphabet_5x5.txt` CRLF causes 6 pre-existing unrelated
  `test_hopfield_select.py`/`test_letters.py` failures in this environment (`core.autocrlf=input`);
  confirmed still present and unrelated by this plan's own `make test` run; already logged in STATE.md
  and `deferred-items.md` from Plan 01, not touched by this plan.

## Self-Check: PASSED

- FOUND: analysis/hopfield_qr_limits.py
- FOUND: analysis/hopfield_qr_figures.py (plot_shift, plot_majority, require_same_limits_code present)
- FOUND: analysis/tests/test_hopfield_qr.py (19 tests)
- FOUND: deliverables/05-hopfield-qr.md (sections 1, 2, 4, 5, 6, 7 filled; markers intact)
- FOUND: .planning/phases/05-hopfield-con-qr/05-05-SUMMARY.md
- FOUND commit 37bfd4c (Task 1) on HEAD
- FOUND commit dce2b04 (Task 2) on HEAD
- FOUND commit fa770ec (Task 3) on HEAD

---
*Phase: 05-hopfield-con-qr*
*Completed: 2026-10-25*
