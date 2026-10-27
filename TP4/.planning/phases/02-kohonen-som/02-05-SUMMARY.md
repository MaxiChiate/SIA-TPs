---
phase: 02-kohonen-som
plan: 05
subsystem: analysis
tags: [som, u-matrix, component-planes, figures, deterministic-svg, matplotlib, pytest]

requires:
  - phase: 02-kohonen-som
    provides: "02-04 selection.json (chosen k = 5, figure seed 4, figure_run), aggregate.csv and the guarded rule digest (require_same_rule); 02-02 som.py run reader"
provides:
  - "analysis/som.py: adjacent_pairs, edge_distances, umatrix (mean distance to the existing 4-neighbors)"
  - "analysis/som_figures.py: plot_map, plot_planes, plot_stage1_curves, plot_trace, main_planes, neuron_raw_means, main; make som-figures"
  - "Figures under analysis/results/som/figures/ (map, planes_main, planes_appendix, stage1_curves, trace as SVG+PNG, hits_members.csv)"
  - "deliverables/02-kohonen.md section 5 (how to read each figure, numbers from the outputs)"
affects: [02-06]

actuals:
  tokens: 21000
  tasks: 2
  commits: 3
plan_head_before: abdf0d11c4be4bae6a7c622c923ff60555e8603b
plan_head_after: 97309b48d5020ae62c1b599cdfe23dbf606dd100
commits: 3

tech-stack:
  added: []
  patterns:
    - "Empty neurons hatched with fill=False rectangles over the heatmap, so the colour below stays readable and no empty neuron looks like it holds creators"
    - "Shared symmetric z scale (vmax = max |value| over z planes) on a dedicated colourbar column; raw planes get their own inset colourbar"
    - "main() validates the figure run against selection.json (grid_k, features) and refuses before drawing"

key-files:
  created:
    - analysis/som_figures.py
    - analysis/tests/test_som_figures.py
  modified:
    - analysis/som.py
    - Makefile
    - deliverables/02-kohonen.md

key-decisions:
  - "Stability SD in the stage-1 curves is computed in som_figures from stability.csv (ddof 1 over the 45 seed pairs) because aggregate.csv carries only the mean"
  - "Empty neurons are hatched in the z planes too (their prototype is interpolation), not only blanked in raw planes"
  - "Section 5 reads the figure run only; regions and the PCA contrast stay in section 6 (plan 02-06)"

requirements-completed: [SOM-04]

coverage:
  - id: D1
    description: "U-matrix = mean Euclidean distance to existing 4-neighbors, proven on a hand 2 x 2 grid; adjacency has 2 k (k - 1) ordered pairs"
    requirement: SOM-04
    verification:
      - kind: unit
        ref: "analysis/tests/test_som_figures.py#test_umatrix_2x2, #test_adjacent_pairs"
        status: pass
    human_judgment: false
  - id: D2
    description: "Main planes follow the PC1/PC2 loading rule; every figure type renders and a rerun gives byte-identical SVGs"
    requirement: SOM-04
    verification:
      - kind: unit
        ref: "analysis/tests/test_som_figures.py#test_main_planes_rule, #test_figures_deterministic (4 passed)"
        status: pass
      - kind: other
        ref: "make som-figures twice, shasum of the five SVGs identical (FIGURES_OK)"
        status: pass
    human_judgment: false
  - id: D3
    description: "make som-figures refuses when the rule sha256 differs from selection.json or when no grid was chosen"
    requirement: SOM-04
    verification:
      - kind: other
        ref: "manual run with a copied selection.json (rule_sha256 zeroed; chosen_k null): both exit 1 before writing figures"
        status: pass
    human_judgment: false
  - id: D4
    description: "Legibility of the five figures and faithfulness of the section 5 reading (hatched empty neurons, full U scale, centred z scale, captions with seed and arbitrary orientation)"
    requirement: SOM-04
    verification:
      - kind: other
        ref: "SECTION5_OK command; PNGs viewed by the executor (map, planes_main, planes_appendix, stage1_curves, trace)"
        status: pass
    human_judgment: true
    rationale: "Reading quality of the figures and of the prose needs a human pass; the executor checked the PNGs but the plan lists this as a human check"

duration: 25min
completed: 2026-10-21
status: complete
---

# Phase 2 Plan 05: Hit map, U-matrix and component planes of the chosen grid Summary

**The U-matrix (tested on a hand 2 x 2 grid) and four deterministic figures of the k = 5 map, seed 4 (hit map + U-matrix, component planes, stage-1 curves, trace), regenerate with `make som-figures` and are read in section 5 of the report.**

## Accomplishments

- **Task 1 (TDD).** `som.adjacent_pairs`, `som.edge_distances`, `som.umatrix`; `som_figures.Plane`, `plot_map`, `plot_planes`, `plot_stage1_curves`, `plot_trace`, `main_planes`, `neuron_raw_means`. 4 tests: the 2 x 2 U-matrix gives [3, 5, (1 + sqrt(85)) / 2, (5 + sqrt(85)) / 2] within 1e-12, k = 3 has 12 pairs, the main-plane rule on a synthetic loadings matrix, and byte-identical SVGs on a 3 x 3 fixture run.
- **Task 2.** `som_figures.main` (rule digest check, refuses on no chosen grid, validates run k and features, builds the figures from `figure_run`), `make som-figures`, `hits_members.csv` and section 5. Main planes (rule, not by looks): `average_caption_words`, `average_impressions`, `average_video_views`, `average_reach` (PC1) and `argentina_audience_pct`, `estimated_argentina_reach`, `topic_dogs_pct`, `monthly_posts` (PC2), plus raw `topic_art_pct` and `content_showcase_pct`.
- **What the map shows (figure run, seed 4).** 3 empty neurons ((0,3), (1,2), (3,3)), 7 single-creator neurons, maximum 5 creators; U from 1,59 to 2,97; the longest edge (3,67) joins two occupied neurons, while four of the six longest edges touch an empty neuron (interpolation, Pitfall 6). QE and TE are flat over the last 10 % of epochs (QE 2,7224 to 2,7239, TE 0,06).

## Task Commits

1. **Task 1 RED:** `3cdfb9c` test(02-05): 4 failing tests (collection error, `som_figures` absent)
2. **Task 1 GREEN:** `d7cca67` feat(02-05): U-matrix, adjacency and figure functions (4 passed)
3. **Task 2:** `97309b4` feat(02-05): `make som-figures` and report section 5

## TDD Gate Compliance

- **RED:** `3cdfb9c`; pytest failed at collection with `ModuleNotFoundError: No module named 'som_figures'`, the intended failure for a module that did not exist.
- **GREEN:** `d7cca67`; all 4 tests pass.
- **REFACTOR:** none (a `set_bad` deprecation warning was removed before the GREEN commit).

## Deviations from Plan

None - plan executed exactly as written. Layout of the planes figure (spacing, colourbar inset, two-line titles for raw planes, plain-number formatting for `price_ars`) was tuned after viewing the PNGs and before the Task 2 commit; it changes no data or rule.

## Verification

- `pytest analysis/tests/test_som_figures.py`: 4 passed. `make test`: 118 C checks, 42 pytest passed.
- `make som-figures` twice: identical SVG hashes (FIGURES_OK). SECTION5_OK. `hits_members.csv`: 25 rows summing to 50.
- Refusals checked by hand: zeroed `rule_sha256` and `chosen_k = null` both exit 1 with no figures written.
- The text between the rule markers of `deliverables/02-kohonen.md`, `analysis/som_select.py` and `analysis/series_som_stage1.json` was not touched (the deliverable diff is additions only).

## Known Stubs

None.

## Threat Flags

None. T-02-13 (figure run only from `selection.json`, rule digest checked first, every caption prints k, schedule and seed) and T-02-14 (U scale [min, max], empty neurons hatched, shared symmetric z scale) are implemented as planned.

## Issues Encountered

None. `analysis/results/` is gitignored, so the figures are regenerated with `make som-figures` rather than versioned.

## Next Phase Readiness

Ready for 02-06 (regions, PCA contrast): `som.umatrix`, `som.edge_distances`, `som.adjacent_pairs` and `hits_members.csv` are available for the region cut and the edge-wise Spearman.

## Self-Check: PASSED

- Files found: `analysis/som_figures.py`, `analysis/tests/test_som_figures.py`, `analysis/som.py` additions, `Makefile` target, section 5.
- Commits found in HEAD: `3cdfb9c`, `d7cca67`, `97309b4`.
