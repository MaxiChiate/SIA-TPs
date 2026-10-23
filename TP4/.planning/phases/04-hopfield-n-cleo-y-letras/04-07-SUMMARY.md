---
phase: 04-hopfield-n-cleo-y-letras
plan: 07
subsystem: analysis (capacity and spurious figures) and deliverable
tags: [hopfield, letters, capacity, spurious-states, figures, deliverable, readme]
requires:
  - phase: 04-hopfield-n-cleo-y-letras
    provides: "04-05 result files (capacity_p4.csv, capacity_by_p.csv, capacity.json, spurious.json); 04-06 figures module and sections 2, 4 and 5"
provides:
  - "analysis/hopfield_figures.py: plot_capacity_p4, plot_capacity_by_p, plot_spurious; draw() now writes nine figures"
  - "deliverables/04-hopfield-letras.md: sections 1, 6, 7 and 8 (complete fragment, sections 1 to 8, rule region untouched)"
  - "analysis/README.md: ## Hopfield (Fase 4)"
affects: [phase-5-qr]
key-files:
  modified:
    - analysis/hopfield_figures.py
    - analysis/tests/test_hopfield_figures.py
    - deliverables/04-hopfield-letras.md
    - analysis/README.md
requirements-completed: [HOP-01, HOP-02, HOP-03]
status: complete
commits: 0
plan_head_before: 23c35639151d9899c9bc6c3958672c24c51e2831
plan_head_after: 23c35639151d9899c9bc6c3958672c24c51e2831
actuals:
  tokens: 30000
  tasks: 3
  commits: 0
duration: not measured
completed: 2026-10-23
---

# Phase 4 Plan 07: Capacity and spurious-state figures, sections 1/6/7/8, README Summary

**The Phase 4 fragment is complete: three more figures (capacity over the 14950 four-letter subsets, capacity against p to the rule's p = 26 limit, and the three pre-registered spurious states), sections 1, 6, 7 and 8 in Spanish with every number taken from the result files, the analysis README section, and a green full suite.**

## Accomplishments

- `plot_capacity_p4(rows, selection, out_stem)`: stacked share of subsets by number of stable letters per max |overlap| bucket, recall rate per bucket with a 10th to 90th percentile band and a dashed second line against mean |overlap| rounded to 0.04, triangles for the separated and correlated sets.
- `plot_capacity_by_p(rows, capacity, out_stem)`: stable fraction and recall rate against every p with the spread over seeds, hollow markers for exhaustive p, diamonds and a dotted line for the rule's extension, the rule's "~0" line at 0.05, and 0.138N and 0.15N as legend-labelled orders of magnitude for random patterns.
- `plot_spurious(spurious, out_stem)`: one row per pre-registered pick (query glyph, final glyph, overlaps, energy per step with stored energies), explicit title when `found_target` is false, class counts per seed in the caption.
- Tests: 5 new test functions (fixture capacity figures, synthetic by-p with and without extension, synthetic spurious with picks, inverse only and none, stems order); the determinism test now covers the nine figures.
- Sections written in the deliverable; the text between the rule markers is byte-identical and `hopfield_select.py identity` exits 0.

## Key numbers written into the deliverable (all from the result files)

Section 1: N = 25, W = sum of xi xi^T with zero diagonal and no 1/N, `max_sweeps` 100, async energy never rises (`energy_increases` 0 in the 20 async recall runs).

Section 6, `capacity_p4`: n_stable counts 0/1/2/3/4 = 284/1687/2653/3073/7253 over 14950 subsets; all-stable share 0.485; mean stable fraction 0.756; mean recall 0.644. The 1212 subsets with max |overlap| up to 0.28 are all fully stable (recall 0.998, 0.993, 0.979, 0.937 for |d| = 1, 3, 5, 7). At max |overlap| 0.84 (1575 subsets) the mean stable fraction is 0.550 and 177 (11.2 %) are fully stable. GRTV: 4/4 stable, recall 0.998; HMNW: 1/4 stable, recall 0.250 against the bucket mean 0.456, and the highest mean |overlap| (0.733) of its bucket. Mean |overlap| orders the subsets better than max |overlap| (Pearson with stable fraction -0.73 against -0.53; with recall -0.77 against -0.58), computed over the 14950 rows of `capacity_p4.csv`.

Section 6, `capacity_by_p` (stable fraction / recall rate): p = 1 1.000/1.000, p = 3 0.918/0.853, p = 4 0.749/0.636, p = 8 0.247/0.158. First p with stable fraction below 1/2: p = 6 (0.425); recall below 1/2 at p = 5 (0.444). The extension fired and ran p = 9 to 26: stable fraction 0.0536 at p = 24, 0.0554 at p = 25, 0.1154 at p = 26; `near_zero_reached` is false. Reported as a finding. 0.138N = 3.45 and 0.15N = 3.75 appear only as orders of magnitude; the curve has no break near them.

Section 7: seed 1 sufficed (`found_target` true); 1200 converged trials: stored 463, inverse 334, mixture 254, other 149. Picks (first converged trial per class in file order, all queries of G with 10 flipped pixels): inverse trial 1, final -R, energy -20 -> -264; mixture trial 3, +G -R +V, energy 12 -> -208; other trial 7, overlaps 0.28/0.36/-0.36/-0.68, energy 28 -> -200. Stored energies are -264 each. The text reads only these three states and makes no general claim about spurious energies.

Section 8: make venv, letters, hopfield-letters (with its refusal condition), hopfield-figures, test, and where each output goes.

## Verification

- `pytest analysis/tests/test_hopfield_figures.py -q`: 14 passed.
- `make hopfield-figures` writes nine figures (SVG and PNG), all non-empty.
- `.venv/bin/python analysis/hopfield_select.py identity`: exit 0 after every deliverable edit and at the end.
- DELIVERABLE_OK (headings exactly 1 to 8 in order), README_OK printed.
- RERUN_IDENTICAL_OK: a full `make hopfield-letters` and `make hopfield-figures` rerun gave `diff -r` identical letters results and identical SVGs.
- `make test`: exit 0 (141 Python tests passed, C tests pass). `make -C neuron debug`: exit 0, "1100 checks, 0 failed", no sanitizer report.
- `git diff --cached --quiet` exits 0 (nothing staged); `git status --porcelain` on the frozen files is empty.

## Deviations from Plan

**1. [Rule 1 - Plan gate false positive] The 0,138 grep gate.** The Task 1 gate `grep '0,138' | grep -v 'orden de magnitud'` after the rule region also matches the pre-existing section 5 line "otra letra almacenada 0,127, inverso 0,138, ..." (a failure rate, unrelated to 0,138N). Section 5 was not edited (override: extend sections 2, 4, 5 only if required), so that single line matches the gate literally. Every line this plan added that mentions 0,138N carries "orden de magnitud".

**2. [Interface choice] `plot_spurious(spurious, out_stem)`.** The plan's artifact listing gave a `letters_patterns` parameter; the figure needs only the glyphs of the query and the final state, which spurious.json already holds, and the stored letter names (`stored_letters`), so the parameter was dropped.

**3. [Process] No commits.** By instruction nothing was staged or committed, so `commits: 0`; STATE.md and ROADMAP.md were not updated.

**4. [Presentation] Rounded figures.** After a first look at the PNGs the reference-line labels of `capacity_by_p` were moved into the legend and the set markers of `capacity_p4` inside the bars, because the labels overlapped; no data or design choice changed.

## Issues Encountered

None. Nothing was tuned after seeing results.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- Files found: the six new figure files, `deliverables/04-hopfield-letras.md` (sections 1 to 8), `analysis/README.md` (Hopfield section).
- Nothing staged; frozen files and the rule region unchanged; identity exits 0.
