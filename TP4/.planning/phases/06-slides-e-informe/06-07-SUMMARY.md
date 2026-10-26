---
phase: 06-slides-e-informe
plan: 07
subsystem: figures
tags: [matplotlib, plots_style, slide-variant, hopfield, qr, letters, d-08]

requires:
  - phase: 06-slides-e-informe
    provides: "06-05: plots_style variant API (iter_variants, figsize, rect, fontsize, caption, suptitle, SLIDE_FIGSIZE) and the sha256 baseline approach"
  - phase: 06-slides-e-informe
    provides: "06-01: make results regenerated analysis/results/hopfield/**"
provides:
  - "Slide variants (PNG + SVG) of the Hopfield letter figures letters, overlaps, recall_noise, capacity_p4 and spurious under analysis/results/hopfield/figures/slide/"
  - "Slide variants (PNG + SVG) of the six QR figures qr, overlaps, recovery, majority, energy_trace and shift under analysis/results/hopfield/qr/figures/slide/"
  - "_caption in both Hopfield figure scripts reduced to a wrapper of plots_style.caption; suptitles go through plots_style.suptitle"
  - "analysis/tests/test_hopfield_qr_figures.py (5 tests, synthetic data) and one new test in test_hopfield_figures.py"
affects: [06-09, 06-10]

actuals:
  tokens: 14400
  tasks: 2
  commits: 2
plan_head_before: 0f0357d6468088da1e1818bb7d223de98d81248e
plan_head_after: 69805eddcebeb41d5195d6169a2d7ee8c986b1fe

tech-stack:
  added: []
  patterns:
    - "A driver reads the results once and wraps only the plot calls in `for _ in plots_style.iter_variants():`; report-only figures stay outside the loop"
    - "Slide-only layout changes branch on plots_style.variant() == 'slide' inside the plot function (or a small helper for a whole different grid); the report branch is the old code"
    - "A legend that would sit on data or on an axis label moves below the panels with fixed subplots_adjust margins in the slide variant"

key-files:
  created:
    - analysis/tests/test_hopfield_qr_figures.py
  modified:
    - analysis/hopfield_figures.py
    - analysis/hopfield_qr_figures.py
    - analysis/tests/test_hopfield_figures.py

key-decisions:
  - "Letters slide: the 26 glyphs in 2 rows of 13 (square pixels, aspect equal kept), legend centered on top. Spurious slide: one column per pick (query and final glyph over the overlap bars); the energy panels stay in the report because three rows of four panels do not fit the 2.6:1 area at 15 pt"
  - "QR recovery slide keeps its three panels (Hebb, pinv, Hamming on the same noise grid, D-04) with short legend names in one legend under the panels; the cost panel loses its in-panel legend because colour and line style are those of that legend"
  - "QR energy_trace slide: one row per dynamical rule and one column per noise level with the five QR traces overlaid (colour by QR), instead of 5 x 3 panels; same traced trials as the report. QR shift slide: one row of five glyphs (source, then shifted and recovered for each shift)"
  - "capacity_p4 slide shows the set markers in the right panel legend only and the stable-count shades in the left one"

patterns-established:
  - "Baseline first: sha256 of the 15 Exercise 2 report SVGs taken with unedited HEAD code in analysis/results/variant_baseline/ej2.sha256, checked to reproduce on a second run, then checked after each task"

requirements-completed: []  # DELIV-01 is declared by sibling plans of this phase still pending (requirements.ready-ids returned it as blocked)

duration: about 60min
completed: 2026-10-26
status: complete
---

# Phase 6 Plan 07: Slide variants of the Exercise 2 figures Summary

**Letters (5 figures) and QR (6 figures) of Exercise 2 now also draw a slide variant from the same plot code, including the Hebb/pinv/Hamming recovery comparison of D-04, with all 15 report SVGs byte-identical to the HEAD baseline and no Hopfield code-identity file touched.**

## Performance

- **Duration:** about 60 min (start time not recorded; estimate)
- **Tasks:** 2 of 2
- **Files modified:** 4 (1 created)

## Accomplishments

- Baseline taken first: `make hopfield-figures hopfield-qr-figures` on unedited HEAD, 15 report SVG hashes in `analysis/results/variant_baseline/ej2.sha256` (not versioned), and a second run reproduced them.
- `analysis/results/hopfield/figures/slide/{letters,overlaps,recall_noise,capacity_p4,spurious}` and `analysis/results/hopfield/qr/figures/slide/{qr,overlaps,recovery,majority,energy_trace,shift}` exist (SVG and 3200x1212 PNG). No slide file for max_overlap_hist, cross_terms, energy, capacity_by_p.
- `draw()` in both scripts returns the same report paths in the same order; `test_figures_deterministic` is unchanged and passes. `require_same_code` and the rule guard still run on every `make` (no refusal, so no ~46 min rerun).
- Every slide PNG was looked at and fixed: letters grid in two rows; overlaps with its own colorbar axes (the shared one covered the right matrix); recall_noise legend moved off the curves and titles shortened; capacity_p4 legends under the panels (they overlapped the x label); spurious redesigned as three columns; QR overlaps with the max and mean |overlap| text beside the matrix; QR energy_trace constant pinv trace at noise 0 shows one tick instead of a 1e-9 offset label.
- `make test`: 283 pytest passed (277 plus 6 new) and 1282 checks, 0 failed.

## Task Commits

1. **Task 1: slide variants of the letter figures** - `f39a132` (feat)
2. **Task 2: slide variants of the QR figures, byte check for all of Exercise 2** - `69805ed` (feat)

## Verification

- `LETTER_SLIDES_OK`, `PYTEST_OK` (18 passed in test_hopfield_figures.py), `EJ2_REPORT_BYTES_UNCHANGED` (15 of 15 OK), `HOPFIELD_CODE_UNTOUCHED`, `SUITE_OK` (283 passed).
- New tests: slide files exist with the SLIDE_FIGSIZE aspect (tolerance 0.02) for the five letter stems and for qr, overlaps, majority and energy_trace of the QR set; no slide file for the four report-only letter stems; a second report draw is byte-identical; drawing the slide does not change the report overlaps SVG.

## Deviations from Plan

### Interpretation of the plan

- The plan says the slide variants come from the same plot functions. For `spurious` (letters) and `energy_trace` and `shift` (QR) the slide branch uses a different grid, because the report grids (3 x 4, 5 x 3, 2 x 3 panels) cannot be read in the 12.8 x 4.85 in figure area at 15 pt. The same data is drawn; the spurious slide omits the energy panel and the per-pick seed and trial text (both stay in the report figure).
- The plan's test for the QR figures names plot_overlaps and plot_majority; the test file also covers plot_qr and the energy_trace slide layout on synthetic rows.
- The shift slide was not part of the plan's test (it needs `shift_json`, which runs the network); it was checked by looking at the PNG and by the report byte check.
- `_caption` in hopfield_figures.py no longer uses `textwrap`, so that import was removed.

**Total deviations:** 0 auto-fixed, 4 interpretations. **Impact:** none on the report output.

## Known Stubs

None.

## Threat Flags

None. Figure scripts only; T-06-16 mitigated (HOPFIELD_CODE_UNTOUCHED, `draw()` still runs `require_same_rule` and `require_same_code`, report SVG sha256 equal to the HEAD baseline), T-06-SC nothing installed.

## Issues Encountered

None beyond the slide layout fixes above.

## Next Phase Readiness

06-10 can upload the slide PNGs: letters, recall_noise, spurious (letters) and qr, majority, recovery, energy_trace (QR) are placed on slides; the slide variants of the letter overlaps, capacity_p4, the QR overlaps and shift are unplaced and belong in UNPLACED_SLIDE_FIGURES with a reason each. The Hopfield results files were not rewritten, only slide files were added.

## Self-Check: PASSED

- Files: analysis/tests/test_hopfield_qr_figures.py, analysis/hopfield_figures.py, analysis/hopfield_qr_figures.py, analysis/tests/test_hopfield_figures.py, and the eleven slide SVG/PNG pairs exist.
- Commits `f39a132` and `69805ed` are ancestors of HEAD; `git rev-list --count 0f0357d..HEAD` = 2 at the time of the last task commit.
