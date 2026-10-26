---
phase: 06-slides-e-informe
plan: 05
subsystem: figures
tags: [matplotlib, plots_style, slide-variant, som, figures, d-08]

requires:
  - phase: 06-slides-e-informe
    provides: "06-02: 06-ARTIFACT-FORMAT.md (figure_area 1664x630 px, PNG figures at about 2x their box)"
  - phase: 06-slides-e-informe
    provides: "06-01: make results regenerated analysis/results/**"
provides:
  - "analysis/plots_style.py: VARIANTS, use_variant, variant, iter_variants, figsize, rect, fontsize, caption, suptitle, SLIDE_FIGSIZE, SLIDE_FONT_SIZE, SLIDE_PNG_DPI; variant-aware apply_style and save_figure"
  - "Slide variants (PNG + SVG) of the SOM map, stage-1 curves, regions and PC planes under <figure dir>/slide/"
  - "analysis/tests/test_plots_style.py (11 tests)"
affects: [06-06, 06-07, 06-09, 06-10]

actuals:
  tokens: 7500
  tasks: 2
  commits: 2
plan_head_before: 935c8fa13c37700078135b645dda194033da9f3f
plan_head_after: 82b29b79aab75cd9004c86610583c54c2e38260d

tech-stack:
  added: []
  patterns:
    - "One plot function, two renderers: size, type scale, caption and suptitle come from plots_style; a driver draws both with `for _ in plots_style.iter_variants(): plot(...)`"
    - "Report values equal matplotlib defaults (font.size 10.0), so report SVG bytes are unchanged; proved with a sha256 baseline taken at HEAD before any edit"
    - "Slide figures are saved under <dir>/slide/<stem> with a 250 dpi PNG (full-width 3200 px, about 2x the 1664 px box)"

key-files:
  created:
    - analysis/tests/test_plots_style.py
  modified:
    - analysis/plots_style.py
    - analysis/som_figures.py
    - analysis/som_profiles.py

key-decisions:
  - "SLIDE_FIGSIZE is (12.8, 4.85) = 1664x630 px, the figure_area recorded in 06-ARTIFACT-FORMAT.md (about 2.6:1), not a full 16:9 canvas. A figure that shares the slide passes its own slide= size to figsize()"
  - "Hard-coded text sizes go through plots_style.fontsize(report_pt), scaled by SLIDE_FONT_SIZE / 10 in a slide, because rcParams alone do not reach fontsize= literals"
  - "Slide PNGs use 250 dpi (SLIDE_PNG_DPI), so a full-width figure is about 3200 px as 06-ARTIFACT-FORMAT.md section 3 asks"
  - "som_figures._caption stays as a one-line wrapper of plots_style.caption for campaigns.py until 06-06"

patterns-established:
  - "Slide-only layout changes branch on plots_style.variant() == 'slide' inside the plot function (regions: map beside legend with equal aspect; stage-1 legend and note moved off the curves); the report branch is the old code verbatim"

requirements-completed: []  # DELIV-01 is shared with sibling plans of this phase; not marked complete here (see Deviations)

duration: 25min
completed: 2026-10-26
status: complete
---

# Phase 6 Plan 05: Slide variants of the figures Summary

**D-08 variant switch in plots_style (report or slide) with slide versions of the four SOM slide figures drawn by the same matplotlib code, and the report SVGs byte-identical to HEAD.**

## Performance

- **Duration:** about 25 min
- **Tasks:** 2 of 2
- **Files modified:** 4 (1 created)

## Accomplishments

- `plots_style` owns the variant state. `iter_variants()` yields report then slide and restores report in a `finally`, so a plot that raises cannot leave the next report figure in slide style (tested).
- `make som-figures` and `make som-profiles` now also write `slide/map`, `slide/stage1_curves`, `slide/regions` and `slide/pc_planes` (SVG and PNG). `planes_main`, `planes_appendix` and `trace` stay report-only.
- The 7 report SVGs have the same sha256 as the baseline captured at HEAD before the first edit (`analysis/results/variant_baseline/som.sha256`, not versioned).
- The four slide figures were looked at as PNGs: legible type, no overlapping labels, cells of the regions map square.
- No guarded file changed (`GUARDED_UNTOUCHED`); `make test`: 273 pytest passed (262 before plus 11 new) and 1282 checks, 0 failed.

## Task Commits

1. **Task 1: variant switch in plots_style, report output byte-identical** - `ee924b8` (feat)
2. **Task 2: slide variants of the SOM figures** - `82b29b7` (feat)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] `fontsize()` helper and slide PNG dpi**
- **Found during:** Task 1 and the first look at the slide PNGs
- **Issue:** Every plot function hard-codes `fontsize=8/10/11/12`, which beats rcParams, so `font.size` alone leaves the slide text small. Also, the default 150 dpi gives a 1920 px wide PNG, below the "about 2x the box" contract of 06-ARTIFACT-FORMAT.md section 3.
- **Fix:** Added `plots_style.fontsize(report_pt)` and `SLIDE_PNG_DPI = 250`, both in the plots_style API (the plan listed neither by name).
- **Files modified:** analysis/plots_style.py, analysis/som_figures.py, analysis/som_profiles.py
- **Commit:** ee924b8, 82b29b7

**2. [Rule 1 - Bug] Slide-only overlaps found by looking at the PNGs**
- **Found during:** Task 2
- **Issue:** At 15 pt the stage-1 legend sat on the "menor QE" note and curves, and regions drawn side by side stretched its cells (not square).
- **Fix:** Slide branch moves the legend to the empty top right of the "Creadores por neurona ocupada" panel, anchors the note in axes fraction, and sets `ax.set_aspect("equal")` for regions. The report branch is the old code.
- **Files modified:** analysis/som_figures.py, analysis/som_profiles.py
- **Commit:** 82b29b7

### Interpretation of the plan

- The plan says "16:9" in the truths but defines SLIDE_FIGSIZE from the recorded `figure_area` (about 2.6:1, 1664x630 px, because the slide title takes the top). I followed the explicit rule: `(12.8, 4.85)`. The aspect check in the verify block compares against `SLIDE_FIGSIZE`, so it passes. A half-width figure (816x454 px, 1.8:1) passes `slide=(12.8/2, ...)` to `figsize()`.
- The `plot_map` test was added in Task 2 as the plan says (kept out of the Task 1 commit).
- `requirements-completed` left empty: DELIV-01 is declared across sibling plans of this phase, and the slides themselves do not exist yet.

**Total deviations:** 2 auto-fixed, 1 interpretation. **Impact:** none on the report output; the slide figures fit the recorded figure area.

## Known Stubs

None.

## Threat Flags

None. No network, auth or file-access surface added; only figure scripts changed (T-06-12 mitigated: report sha256 equal to baseline, guarded set untouched).

## Issues Encountered

None beyond the slide layout fixes above. The first test of `caption` and `suptitle` counted `fig.texts`, which also contains the suptitle; the test was corrected, not the code.

## Next Phase Readiness

06-06 and 06-07 can apply the same mechanism to the other figure scripts: replace literal figsize and rect with `plots_style.figsize`/`rect`, text sizes with `plots_style.fontsize`, `_caption` and `fig.suptitle` with `plots_style.caption`/`suptitle`, and wrap the slide figures in `plots_style.iter_variants()`. 06-06 also switches campaigns.py from `som_figures._caption` to `plots_style.caption`. 06-10 uploads the slide PNGs (3200x1212 for the four SOM figures).

## Self-Check: PASSED

- FOUND: analysis/plots_style.py, analysis/tests/test_plots_style.py, analysis/results/som/figures/slide/map.png, stage1_curves.png, analysis/results/som/profiles/slide/regions.png, pc_planes.png
- FOUND commits: ee924b8, 82b29b7
- REPORT_BYTES_UNCHANGED, SLIDE_SOM_OK, GUARDED_UNTOUCHED, 273 passed, 1282 checks 0 failed
