---
phase: 06-slides-e-informe
plan: 06
subsystem: figures
tags: [matplotlib, plots_style, slide-variant, pca, oja, campaigns, d-08]

requires:
  - phase: 06-slides-e-informe
    provides: "06-05: plots_style variant API (iter_variants, figsize, rect, fontsize, caption, suptitle) and the sha256 baseline approach"
provides:
  - "Slide variants (PNG + SVG) of the audited PCA scree and biplot, the Oja index vs PC1 figure and the two campaign shortlist figures, under <figure dir>/slide/"
  - "campaigns.py off som_figures._caption: captions and suptitles go through plots_style"
  - "analysis/tests/test_variants_ej1.py (4 tests on synthetic data)"
affects: [06-08, 06-10]

actuals:
  tokens: 4000
  tasks: 2
  commits: 2
plan_head_before: d35b0189524191cd1b085fc3c0d8f4953aef369a
plan_head_after: a732fb474df3ebc0ccdf3e4f4fd2add2d3a3750e

tech-stack:
  added: []
  patterns:
    - "A driver computes the data once and wraps only the plot calls in `for _ in plots_style.iter_variants():`"
    - "pca.py keeps its own VARIANTS (data sets); the figure variant loop lives in _figure_variants(folder): report+slide for audited, report only for all31_sensitivity"
    - "Slide-only layout changes branch on plots_style.variant() == 'slide' inside the plot function; the report branch is the old code"

key-files:
  created:
    - analysis/tests/test_variants_ej1.py
  modified:
    - analysis/pca.py
    - analysis/oja.py
    - analysis/campaigns.py

key-decisions:
  - "Slide layouts: PCA scree side by side (not stacked); biplot legend outside the axes; Oja plot square with legend and statistics on its right; campaign biplot keeps the 2 x 2 panels with the legend of each panel to its right (own lists by name); campaign SOM grids in one row of four"
  - "Exercise 1 report baseline kept in analysis/results/variant_baseline/ej1.sha256 (10 SVGs, not versioned); all 10 still match after the changes"

patterns-established:
  - "A legend that would cover data points moves outside the axes in the slide variant"

requirements-completed: []  # DELIV-01 is declared by sibling plans of this phase still pending (requirements.ready-ids returned it as blocked)

duration: 30min
completed: 2026-10-26
status: complete
---

# Phase 6 Plan 06: Slide variants of the Exercise 1 figures Summary

**PCA scree and biplot (audited set), Oja index vs PC1 and the two campaign shortlist figures now also draw a slide variant from the same plot code, with all 10 Exercise 1 report SVGs byte-identical to the HEAD baseline and the campaign rule untouched.**

## Performance

- **Duration:** about 30 min
- **Tasks:** 2 of 2
- **Files modified:** 4 (1 created)

## Accomplishments

- Baseline taken with the unedited HEAD code (`make pca`, `make oja`, `.venv/bin/python analysis/campaigns.py`), after checking that a second run reproduces the same hashes. 10 SVGs in `analysis/results/variant_baseline/ej1.sha256`.
- `analysis/results/pca/audited/slide/{scree,biplot}`, `analysis/results/oja/slide/oja_vs_pc1`, `analysis/results/campaigns/slide/{shortlists_biplot,shortlists_som}` exist (SVG and 3200x1212 PNG). No slide file for loadings, convergence or the all31 folder.
- `campaigns.py` has no non-comment reference to `som_figures._caption` (2 at HEAD); `campaigns_select.py`, `deliverables/` and `analysis/series_oja.json` unchanged; the rule guard still passed on every run.
- `campaigns.py` was always invoked directly with `.venv/bin/python`, never through `make campaigns` (T-06-15).
- All slide PNGs were looked at and iterated: scree ticks every other component and the k note moved off the 80 % line; biplot label stacking gap enlarged for the larger type; campaign legends moved beside their panels so they no longer hide points.
- `make test`: 277 pytest passed (273 plus 4 new), 1282 checks, 0 failed.

## Task Commits

1. **Task 1: PCA scree and biplot, Oja index vs PC1, test file** - `506f3e7` (feat)
2. **Task 2: campaign shortlist figures, off som_figures._caption** - `a732fb4` (feat)

## Verification

- `EJ1_SLIDES_PCA_OJA`, `EJ1_REPORT_BYTES_UNCHANGED`, `CAMPAIGN_RULE_UNTOUCHED` printed; pytest of the three PCA/Oja files passed (12) and the full suite passed (`make test`).
- `shasum -a 256 -c analysis/results/variant_baseline/ej1.sha256`: 10 of 10 OK.

## Deviations from Plan

### Interpretation of the plan

- The plan says the 2 x 2 panel grid of the campaigns "stays" in the slide. That holds for the shortlist biplot. For the SOM-map shortlists (not placed on any slide, 06-10 lists it in UNPLACED_SLIDE_FIGURES) four square grids in one row fill the 2.6:1 box far better than a 2 x 2, so the slide variant uses a row of four; the report keeps 2 x 2. One panel per campaign is kept.
- The slide biplot legends changed to short labels ("base: followers", own lists by objective name) and sit beside each panel, because the report-style legend inside the panels covered the points and the baseline markers at the slide type size.
- The tests also cover `plot_oja_vs_pc1` (the plan only named the PCA plots), and the dominant-topic lookup of `plot_biplot` is monkeypatched so the synthetic test needs no `datos/`.

**Total deviations:** 0 auto-fixed, 3 interpretations. **Impact:** none on the report output.

## Known Stubs

None.

## Threat Flags

None. Figure scripts only; T-06-14 mitigated (rule, selector and series untouched, report SVG sha256 equal to baseline, rule guard still runs), T-06-15 mitigated (no `make campaigns`), T-06-SC nothing installed.

## Issues Encountered

None.

## Next Phase Readiness

06-08 can read the rewritten `analysis/results/{pca,oja,campaigns}` files (same content as before; only slide files were added). 06-10 can upload the five slide PNGs; `shortlists_som` is the unplaced one.

## Self-Check: PASSED

- Files: analysis/tests/test_variants_ej1.py, analysis/pca.py, analysis/oja.py, analysis/campaigns.py, and the five slide SVG/PNG pairs exist.
- Commits `506f3e7` and `a732fb4` are ancestors of HEAD; `git rev-list --count d35b018..HEAD` = 2 at the time of the last task commit.
