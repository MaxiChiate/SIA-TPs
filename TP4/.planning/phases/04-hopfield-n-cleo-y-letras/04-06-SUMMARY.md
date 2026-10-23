---
phase: 04-hopfield-n-cleo-y-letras
plan: 06
subsystem: analysis (guarded Hopfield letters figures) and deliverable sections 2, 4, 5
tags: [hopfield, letters, figures, orthogonality, cross-term, recall, energy, deliverable]
requires:
  - phase: 04-hopfield-n-cleo-y-letras
    provides: "04-03 rule commit 23c3563 and guard; 04-05 make hopfield-letters result files"
provides:
  - "analysis/hopfield_figures.py: guarded figure script (plot_letters, plot_overlaps, plot_max_overlap_hist, plot_cross_terms, plot_recall_noise, plot_energy, energy_panels, draw, main)"
  - "make hopfield-figures; six figures (SVG + PNG) in analysis/results/hopfield/figures/ (generated, not versioned)"
  - "deliverables/04-hopfield-letras.md sections 2, 4 and 5 in Spanish, outside the rule markers"
affects: [04-07, deliverable-section-6]
tech-stack:
  added: []
  patterns: ["figure script runs require_same_rule first and refuses on any change (T-04-15)", "energy panels fixed by trial index (letter x n_levels + level) x trials, never by the energies (T-04-16)"]
key-files:
  created:
    - analysis/hopfield_figures.py
    - analysis/tests/test_hopfield_figures.py
  modified:
    - Makefile
    - deliverables/04-hopfield-letras.md
requirements-completed: [HOP-02]
status: complete
commits: 0
plan_head_before: 23c35639151d9899c9bc6c3958672c24c51e2831
plan_head_after: 23c35639151d9899c9bc6c3958672c24c51e2831
actuals:
  tokens: 15000
  tasks: 3
  commits: 0
duration: not measured
completed: 2026-10-23
---

# Phase 4 Plan 06: Hopfield letters figures and deliverable sections Summary

**`make hopfield-figures` draws the six figures (letters, overlaps, max-overlap histogram over the 14950 subsets, cross-term margins, recall against noise, energy of pre-registered traced trials) only if the rule guard accepts the run, with byte-identical SVGs on rerun; sections 2, 4 and 5 of the deliverable report them with numbers copied from the result files.**

## Accomplishments

- `draw` calls `hopfield_select.require_same_rule(selection.json)` before reading anything else; a selection.json with a wrong `rule_sha256` ends in `SystemExit` with `(D-04)` and writes no figure (tested).
- `energy_panels` picks, for each letter of the separated set (G R T V) and k = 3, 6, 9, the first traced trial of seed 1 in the separated-async run by index `(position x 13 + level index) x 30`, checks that trial is in the trace and has the expected pattern and k, and never reads an energy to choose (tested).
- Deliverable section 2 (alphabet, both sets with tie counts, overlaps, the disclosure with 25 of 26 coinciding glyphs, consistent with section 3 and 04-03-SUMMARY.md), section 4 (overlaps, histogram, cross terms) and section 5 (recall, energy) written in Spanish. The text between `<!-- regla:inicio -->` and `<!-- regla:fin -->` is untouched (`git diff` of the deliverable is insertions only; `hopfield_select.py identity` exits 0).

## Key numbers written into the deliverable (all from the result files)

- Sets: separated GRTV (max |d| 1, sum 6, unique subset with that max), correlated HMNW (max |d| 21, sum 110; 1575 subsets tie at max 21, one has the highest sum).
- Histogram over 14950: counts 1, 20, 207, 984, 1690, 1271, 3444, 1932, 3599, 227, 1575 (|d| = 1 to 21); separated is the only subset in the first bar, correlated is in the last bar (1575 = 10.5 %); median bar |d| = 13.
- Cross terms: GRTV all fixed points, cross term in [-3, 3], margins 18 to 24; HMNW only N fixed (min margin 4), H 2 wrong pixels (min -30), M 1 (-34), W 1 (-34). The failing pixels are exactly those where the letter disagrees with the other three (cross term -51, -55, -55); 19 of 25 pixels are common to all four letters.
- Recall (rate at k = 3 / 6 / 9 / 12): separated async 0.997 / 0.847 / 0.323 / 0.018, sync 1.000 / 0.904 / 0.336 / 0.003; correlated async 0.250 / 0.250 / 0.250 / 0.162, sync 0.250 / 0.250 / 0.250 / 0.200. Rate 1 up to k = 2 (async) and k = 3 (sync) for the separated set. Sync cycle_rate 0.0025 (k = 4), 0.048 (k = 6), 0.277 (k = 9), 0.336 (k = 10), 0.193 (k = 12); async never cycles. In the correlated set H, M, W end on the stored N in all 9000 failed trials per mode with k <= 9.
- Energy panels: 12 trials, all converged; 10 end at -264 (stored energy), 7 of those recover the letter and 3 (G k=9 to T, R k=9 inverse, V k=9 to T) do not; T k=6 ends in a mixture at -208 and T k=9 in an "other" state at -184. `energy_increases` is 0 in the 20 async recall runs.

## Verification

- `.venv/bin/python -m pytest analysis/tests/test_hopfield_figures.py -q`: 9 passed.
- `make hopfield-figures` twice: six SVG and PNG written, SVG bytes identical (`FIGURES_OK`); section checks `SECTIONS_OK` (2 before the markers, 4 and 5 after the end marker and in order, all six figures cited).
- `make test`: exit 0 (C tests plus 136 Python tests).
- `.venv/bin/python analysis/hopfield_select.py identity`: exit 0 after every deliverable edit. `git diff --cached --quiet`: exit 0. The seven frozen files have no change.

## Deviations from Plan

**1. [Process] No commits.** By instruction nothing was staged or committed; `commits: 0`, `plan_head_before == plan_head_after`. STATE.md and ROADMAP.md were not updated (instruction).

**2. [Choice within the plan] Recall-noise failure panels.** The plan asked for one failure-mix panel (separated, async) with a "cycle" share. Cycles are already counted inside the four classes (a cycle is classified where detected), so stacking a fifth share would double count; and the correlated set is where the failure mix is the story. The figure has three panels: recall lines, the failure mix of the separated async set, and that of the correlated async set (four classes each, summing to 1 - rate). The caption states the async cycle rate (0).

**3. [Choice within the plan] Hist caption and labels.** The histogram labels each bar with its count and names the set that falls in it; the secondary label is d under each overlap tick.

## Issues Encountered

A first render had the cross-terms colorbar covering the fourth column and a "1 píxeles" plural; fixed (dedicated colorbar axis, singular form) before writing the prose. No result was used to change a design or threshold.

## Known Stubs

None.

## Threat Flags

None. T-04-15 (guard before drawing, refusal test), T-04-16 (panels fixed by index, test pins the indices) are covered.

## Self-Check: PASSED

- Files found: `analysis/hopfield_figures.py`, `analysis/tests/test_hopfield_figures.py`, `Makefile` target `hopfield-figures`, six SVG and six PNG under `analysis/results/hopfield/figures/`, deliverable sections 2, 4, 5.
- Nothing staged; frozen files unchanged; identity CLI exits 0.
