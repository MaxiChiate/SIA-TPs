---
phase: 01-fundaci-n-auditor-a-de-datos-y-pca
plan: 08
subsystem: analysis
tags: [pca, eigh, correlation-matrix, eigenvalue plot, biplot, sensitivity, matplotlib, numpy]
status: complete

requires:
  - phase: 01-fundaci-n-auditor-a-de-datos-y-pca
    provides: "prepared z-scored matrices (plan 01-04), plots_style and the section 5 decision rule (plan 01-06), make test with 3 C tests and pytest (plan 01-07)"
provides:
  - "analysis/pca.py: correlation PCA by np.linalg.eigh, orientation convention, k_80 and retired criterion, eigenvalues plot, loadings, biplot, sensitivity comparison"
  - "make pca: analysis/results/pca/{audited,all31_sensitivity}/ and sensitivity.json/.md"
  - "Sections 6, 6.1 and 7 of deliverables/01-datos-pca.md and the extended section 8"
affects: [02-kohonen, 03-oja, report, slides]

actuals:
  tokens: 8400
  tasks: 2
  commits: 3
plan_head_before: 95409bb679136046d1ca1f56e3d7ed5e40ee6b30
plan_head_after: 92b04d7a3e3fd2b642f90e8079c0b33e9a2f31c6

tech-stack:
  added: []
  patterns:
    - "Orientation convention: each eigenvector flipped so its largest-magnitude coefficient is positive (Phase 3 reuses it)"
    - "Sensitivity run shares the code path; only the stem, folder and a SENSIBILIDAD title prefix differ"

key-files:
  created:
    - analysis/pca.py
    - analysis/tests/test_pca.py
  modified:
    - Makefile
    - deliverables/01-datos-pca.md

key-decisions:
  - "The rule of section 5 was applied unchanged: audited set gives k_80 = 6 and retired criterion = 6 (agree), both near their thresholds (5 components reach 79.1 %, eigenvalue 6 is 1.04)"
  - "PCA stays diagnostic: Kohonen and Oja use the 26 z-scored audited variables (D-13)"
  - "Eigenvalue plot drawn as two stacked panels on a shared component axis instead of a twin y-axis"

patterns-established:
  - "Biplot labels stacked with thin leader lines when near-collinear arrows would overprint"

requirements-completed: [DATA-04, DATA-05]

duration: 40min
completed: 2026-10-20
---

# Phase 1 Plan 08: PCA and 31-column sensitivity Summary

**Correlation PCA by `np.linalg.eigh` on the audited 26-variable matrix (k for 80 % = 6, retired criterion = 6) with eigenvalues plot, loadings and biplot, a labelled 31-column run that shows exactly 5 null eigenvalues, and the written interpretation in the Phase 1 fragment.**

## Accomplishments

- `analysis/pca.py` (numpy and matplotlib only): `PcaResult`, `correlation_matrix`, `pca_eigh`, `orient`, `k_by_variance`, `(function retired)`, `scores`, `loadings`, `reconstruct`, `read_prepared` (checks header against meta features and row count against meta `n_rows`, T-01-17), `spearman`, `main`. `make pca` writes, for `audited` and `all31_sensitivity`, eigenvalues, eigenvectors, loadings, scores, eigenvalues plot, loadings and biplot figures (SVG and PNG) and `decision.json`, plus `sensitivity.json` and `sensitivity.md`.
- Audited results from `decision.json`: eigenvalue sum 26 (within 1e-9), 0 null eigenvalues, `k_80` 6, `(field retired)` 6, `(field retired)` true, PC1 53.2 %, PC2 8.5 %, cumulative PC2 61.7 %.
- 31-column run: 5 null eigenvalues (minimum -3.2e-16), `k_80` 6, `(field retired)` 7 (the two criteria disagree), PC1 48.0 %, PC2 9.8 %. Against the audited set on the 26 common variables: abs cos 0.99998 (PC1) and 0.968 (PC2); score correlations PC1 Pearson -0.9992 and Spearman -0.9982 (sign flip comes from the orientation convention picking another variable as the largest coefficient), PC2 Pearson 0.922 and Spearman 0.893.
- `deliverables/01-datos-pca.md`: sections 6, 6.1 and 7 inserted before section 8, every number copied from the generated files; section 8 now lists `make pca` and `make test` (3 C tests and 6 Python tests). Sections 1 to 5 untouched.
- `make test`: C runner `63 checks, 0 failed` (3 C tests) and `6 passed` in pytest, 9 tests in total.

## Task Commits

1. Task 1 RED: `40f0e65` test(01-08): eigenvalue sum and full reconstruction test (failed with `ModuleNotFoundError: pca`)
2. Task 1 GREEN: `98a9ee2` feat(01-08): `analysis/pca.py` and the `pca` Makefile target
3. Task 2: `92b04d7` docs(01-08): sections 6, 6.1, 7 and 8 of the Phase 1 fragment

## Deviations from Plan

### Design choice

**1. [Rule 1 - presentation] Eigenvalue plot as two panels instead of a second y-axis**
- **Found during:** Task 1 (loaded the dataviz skill, as the plan asks)
- **Issue:** the plan describes the cumulative percentage "on a second axis"; the dataviz guidance forbids dual-axis charts.
- **Fix:** eigenvalues with the retired criterion line on top, cumulative percentage with the 80 % line below, shared component axis; the `k_80` bar and point are highlighted in both. All requested elements are present.
- **Files modified:** `analysis/pca.py`
- **Commit:** 98a9ee2

### Minor

- Biplot labels of near-collinear arrows overprinted in the first render; they are now stacked with thin leader lines (same commit).
- `decision.json` holds exactly the keys the plan lists; the biplot scale `s` appears only in the figure subtitle and is quoted in the document from there (6.43).

None of the other plan content changed. The TDD cycle was committed as RED then GREEN.

## Known Stubs

None.

## Threat Flags

None. T-01-17 mitigated by `read_prepared` (header and row count checks); T-01-18 by the section 5 precondition and the doc line check against `decision.json`; T-01-SC: no new dependencies.

## Human checks pending

The plan lists visual checks of `eigenvalues_variance.png`, `loadings.png` and both `biplot.png` files. I looked at the audited eigenvalues plot, loadings and biplot and the 31-column biplot after the label fix; they are legible (8 labelled arrows, scale in the subtitle, four topic colours, SENSIBILIDAD title on the sensitivity figure). A reviewer should still read sections 6 and 7 next to the figures; the PC1 and PC2 names are my reading of the printed loadings.

## Self-Check: PASSED

- `analysis/pca.py`, `analysis/tests/test_pca.py`, `Makefile`, `deliverables/01-datos-pca.md` exist and are committed.
- Commits 40f0e65, 98a9ee2, 92b04d7 exist on the worktree branch.
- Verify commands run: pytest `1 passed`, `PCA_OK`, `DOC_PCA_OK`, `make test` 63 checks 0 failed and 6 passed.
