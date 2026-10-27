---
phase: 02-kohonen-som
plan: 06
subsystem: analysis
tags: [som, regions, profiles, pca-contrast, permutation, u-matrix, pytest]

requires:
  - phase: 02-kohonen-som
    provides: "02-04 selection.json (chosen k = 5, figure seed 4, figure_run) and require_same_rule; 02-05 adjacent_pairs, edge_distances, umatrix and som_figures.plot_planes; 02-02 som.py run reader and tie-aware Spearman"
provides:
  - "analysis/som_profiles.py: regions (committed 75th-percentile cut, 4-adjacency components, MIN_MEMBERS = 2), profiles, grid_r2, permutation_pvalue, r2_null, mantel_null, edge_contrast, high_u_edges, disagreements, plot_regions, main; make som-profiles"
  - "analysis/results/som/profiles/: regions.csv, region_profiles.csv, neuron_profiles.csv, pca_contrast.json, high_u_edges.csv, disagreements.csv, regions and pc_planes figures (SVG+PNG), byte-identical on rerun"
  - "deliverables/02-kohonen.md sections 6 (6.1 to 6.5) and 7 (Como reproducir); analysis/README.md SOM section and series rows"
affects: [phase-03-campaigns]

actuals:
  tokens: 11800
  tasks: 3
  commits: 4
plan_head_before: 71935b9a2edf400408af727b7770cf4d64397216
plan_head_after: f3b2f406dcd13be551aced66d8f760eff68bcc8f
commits: 4

tech-stack:
  added: []
  patterns:
    - "One np.random.default_rng(2026) created in main and consumed in a fixed order (R2 PC1 null, R2 PC2 null, Mantel null): rerun gives the same numbers and the same hashes"
    - "Statistics invariant to grid rotation and reflection (R2 on [1, row, col]); tested"
    - "The report quotes the pre-declared statistics in four fixed-shape lines checked against pca_contrast.json at 3 decimals"

key-files:
  created:
    - analysis/som_profiles.py
    - analysis/tests/test_som_profiles.py
  modified:
    - Makefile
    - deliverables/02-kohonen.md
    - analysis/README.md

key-decisions:
  - "The committed region rule yields a single region (R1, 50 creators) on the chosen map: 10 of 40 adjacent pairs exceed the 2,60 threshold, 5 of them touch an empty neuron and the other 5 do not disconnect the 22 occupied neurons. Reported as it came out; the percentile was not touched (it is pre-registered)"
  - "With one region, the agency reading (6.3) uses neuron profiles with at least 2 creators as description of the continuum, labelled as neurons, not regions; neurons with 1 creator stay flagged and unread"
  - "Disagreement pairs are defined as: plane distance at most the 25th percentile and largest grid distance (plano_cerca_grilla_lejos), and grid distance at most 1 with the largest plane distance (plano_lejos_grilla_cerca); ties by creator index"
  - "The edge-wise Spearman is reported without a p-value because the committed rule declares no null for it"

requirements-completed: [SOM-05]

coverage:
  - id: D1
    description: "Region rule per the committed text: synthetic 3 x 3 map with one far column returns the two expected regions and flags the one-creator region; empty neurons labelled -1"
    requirement: SOM-05
    verification:
      - kind: unit
        ref: "analysis/tests/test_som_profiles.py#test_regions_synthetic"
        status: pass
    human_judgment: false
  - id: D2
    description: "Raw-unit profiles, R2 invariant to rotation/reflection, seeded permutation nulls and p-value formula, edge contrast and high-U edge reading in original units"
    requirement: SOM-05
    verification:
      - kind: unit
        ref: "analysis/tests/test_som_profiles.py (6 passed)"
        status: pass
    human_judgment: false
  - id: D3
    description: "make som-profiles writes the ten outputs, identical hashes on rerun, 1000 permutations with seed 2026, hits summing to 50; refuses on a changed rule sha256 or with no chosen grid"
    requirement: SOM-05
    verification:
      - kind: other
        ref: "Task 2 verify command (PROFILES_OK, shasum diff empty); manual runs with a zeroed rule_sha256 and with outcome no_eligible_grid both exit 1 before writing"
        status: pass
    human_judgment: false
  - id: D4
    description: "Sections 6 and 7 of the report: four contrast lines match pca_contrast.json, literal Kohonen questions answered with the pre-declared numbers, commands match the Makefile; README lists SOM series, scripts and targets; make test passes"
    requirement: SOM-05
    verification:
      - kind: other
        ref: "SECTION67_OK, README_OK, FULL_SUITE_OK (118 C checks, 48 pytest passed)"
        status: pass
    human_judgment: true
    rationale: "Honesty and quality of the interpretation (one region, PC1 yes and PC2 no, disagreement pairs, U-matrix caveats) is a judgment over numbers and figures; the plan lists it as a human check"

duration: 6min
completed: 2026-10-21
status: complete
---

# Phase 2 Plan 06: Regions, profiles and PC1/PC2 contrast of the chosen map Summary

**The committed 75th-percentile region rule gives a single region (all 50 creators) on the k = 5 map, the layout follows PC1 almost exactly (R2 0,961, p = 0,001) but not PC2 (R2 0,055, p = 0,267), and the U-matrix walls between occupied neurons are jumps in size and price; `make som-profiles` regenerates everything byte for byte and report sections 6 and 7 say so.**

## Accomplishments

- **Task 1 (TDD).** `som_profiles` functions with six tests: the synthetic 3 x 3 map gives the two expected regions (30 and 1 creators, only the first interpretable, empty neurons -1), raw-unit profiles match a hand computation, `grid_r2` is equal within 1e-12 under rotation and reflection of the grid, the nulls are identical for the same seed, the edge contrast gives Spearman 1,0 on a map built to match PC1 and excludes edges with an empty neuron, and the high-U edges report delta raw = delta z times std.
- **Task 2.** `plot_regions`, `main`, the `som-profiles` Makefile target. Outputs under `analysis/results/som/profiles/`; two runs give identical hashes; `main` calls `require_same_rule` first and refuses with no chosen grid.
- **Task 3.** Section 6 (6.1 to 6.5) and section 7 of the report, and the SOM section plus two series rows in `analysis/README.md`.
- **Findings (figure run, k = 5, seed 4).**
  - Regions: threshold 2,60 cuts 10 of 40 adjacent pairs (5 touch an empty neuron; the other 5 are (1,4)-(2,4) 3,67, (2,3)-(2,4) 2,99, (2,1)-(2,2) 2,98, (2,1)-(3,1) 2,88, (3,1)-(3,2) 2,66); the 22 occupied neurons stay connected: one region R1, 50 creators, profile of the average creator (221 587 followers, 52,6 % Argentine audience, USD 1 701).
  - PC1/PC2: R2 PC1 0,961 (p = 0,001), R2 PC2 0,055 (p = 0,267), Mantel grid vs plane rho 0,599 (p = 0,001), grid vs 26-D z rho 0,635 (reference), edge-wise Spearman 0,481 (PC1) and 0,271 (PC2) over 29 edges (11 excluded).
  - Highest U edges among occupied neurons: (1,4)-(2,4) price +USD 2 116, followers +251 127, reach +97 110; (2,3)-(2,4) the same three variables; (2,1)-(2,2) entertainment share +34,4 points, review share -10,4, caption words -43,2. All three have a single-creator neuron at one end.

## Task Commits

1. **Task 1 RED:** `b597fa9` test(02-06): 6 failing tests (collection error, `som_profiles` absent)
2. **Task 1 GREEN:** `2b1d3f9` feat(02-06): region rule, raw-unit profiles and contrast statistics (6 passed)
3. **Task 2:** `c7687f6` feat(02-06): `make som-profiles`, `plot_regions`, `main`
4. **Task 3:** `f3b2f40` docs(02-06): report sections 6 and 7, README

## TDD Gate Compliance

- **RED:** `b597fa9`; pytest failed at collection with `ModuleNotFoundError: No module named 'som_profiles'`, the intended failure for a module that did not exist (same RED form as 02-05).
- **GREEN:** `2b1d3f9`; all 6 tests pass.
- **REFACTOR:** none.

## Deviations from Plan

None - plan executed exactly as written. Noted, not a deviation: the plan anticipated a single-region map (flagged assumption for SOM-05) and that is what the rule produced; section 6.3 therefore reads neuron profiles (at least 2 creators) as a description of a continuum instead of region by region.

## Known Stubs

None.

## Threat Flags

None. No new network, auth or file-access surface; creator names come from the already tracked `datos/creadores.csv` (T-02-16, accepted). T-02-15 and T-02-17 mitigations are in place (single seeded generator in fixed order, byte-identical reruns, `require_same_rule` before any computation).

## Verification

- `pytest analysis/tests/test_som_profiles.py`: 6 passed. `make test`: 118 C checks, 48 pytest passed.
- `make som-profiles` twice: identical hashes of CSV, JSON and SVG outputs; PROFILES_OK. SECTION67_OK and README_OK.
- Manual refusals: zeroed `rule_sha256` ("rule changed since stage 1") and `outcome: no_eligible_grid` both exit 1 before any output.
- The text between the rule markers of `deliverables/02-kohonen.md` is unchanged (`make som-profiles` passes the rule digest check after the report edits).

## Self-Check: PASSED

- FOUND: analysis/som_profiles.py, analysis/tests/test_som_profiles.py, analysis/results/som/profiles/pca_contrast.json
- FOUND commits: b597fa9, 2b1d3f9, c7687f6, f3b2f40 (all ancestors of HEAD)
