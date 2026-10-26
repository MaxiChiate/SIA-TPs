---
phase: 03-oja-y-decisiones-de-campa-a
verified: 2026-10-26T12:00:00Z
status: passed
score: 5/5 must-haves verified
covered_files:
  - ".planning/phases/03-oja-y-decisiones-de-campa-a/03-01-PLAN.md"
  - ".planning/phases/03-oja-y-decisiones-de-campa-a/03-01-SUMMARY.md"
  - ".planning/phases/03-oja-y-decisiones-de-campa-a/03-02-PLAN.md"
  - ".planning/phases/03-oja-y-decisiones-de-campa-a/03-02-SUMMARY.md"
  - ".planning/phases/03-oja-y-decisiones-de-campa-a/03-03-PLAN.md"
  - ".planning/phases/03-oja-y-decisiones-de-campa-a/03-03-SUMMARY.md"
  - ".planning/phases/03-oja-y-decisiones-de-campa-a/03-04-PLAN.md"
  - ".planning/phases/03-oja-y-decisiones-de-campa-a/03-04-SUMMARY.md"
  - ".planning/phases/03-oja-y-decisiones-de-campa-a/03-05-PLAN.md"
  - ".planning/phases/03-oja-y-decisiones-de-campa-a/03-05-SUMMARY.md"
  - ".planning/phases/03-oja-y-decisiones-de-campa-a/03-06-PLAN.md"
  - ".planning/phases/03-oja-y-decisiones-de-campa-a/03-06-SUMMARY.md"
  - "analysis/campaigns.py"
  - "analysis/campaigns_select.py"
  - "analysis/maintenance_demo.py"
  - "analysis/oja.py"
  - "deliverables/03-oja-campanas.md"
  - "neuron/models/oja.c"
covered_digest: "v3:sha256:1b97b1112019bad7d3b032c8d03909e00d6d1e6320ddec2a0d7b37a66fcc2b9d"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 5/5
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 3: Oja y decisiones de campaña Verification Report

**Phase Goal:** As a campaign analyst, I want to build an Oja index and recommend creators per campaign against a followers-only strategy, so that I can choose with evidence and know when the index misleads.
**Verified:** 2026-10-26
**Status:** passed
**Re-verification:** Yes. The 2026-10-22 report (`human_needed`) was marked stale because `analysis/campaigns.py` and `analysis/oja.py` changed afterwards (Phase 6 commits `506f3e7` and `a732fb4`). This pass checks that those two commits changed no Phase 3 result, rule or must-have, and closes the three human items through the completed UAT.

## What changed since the stale report

| Commit | File | Nature of the change | Effect on Phase 3 |
|--------|------|----------------------|-------------------|
| `506f3e7` | `analysis/oja.py` | `plot_oja_vs_pc1` takes the report or the slide variant (`plots_style.variant()`); `main` calls it inside `iter_variants()` | Drawing only. No change to the C call, the 10-seed series, the comparison, the dispersion gates or the evidence text |
| `a732fb4` | `analysis/campaigns.py` | `plot_shortlists_biplot` and `plot_shortlists_som` take both variants; captions use `plots_style.caption` instead of `som_figures._caption`; the plot calls move inside `iter_variants()` | Drawing only. `rule_identity()` is still the first call of `main`, and the list selection, metrics and reports are untouched |

I read both diffs in full: every hunk is inside a `plot_*` function or the final plotting calls of `main`. No other Phase 3 covered file changed after 2026-10-22 (`git log --since=2026-10-22` for `deliverables/03-oja-campanas.md`, `campaigns_select.py`, `oja.c`, `maintenance_demo.py`, `series_oja.json` and the rule test returns only the 2026-10-22 Phase 3 commits).

Evidence that no result moved:

- The four report SVGs of this phase (`oja/convergence.svg`, `oja/oja_vs_pc1.svg`, `campaigns/shortlists_biplot.svg`, `campaigns/shortlists_som.svg`) still hash to the entries in `analysis/results/variant_baseline/ej1.sha256` (`shasum -c`: 4 OK).
- Every line of the six report files (`report_convergence.md`, `report_evidence.md`, `report_pc1.md`, `report_campaigns.md`, `report_reading.md`, `report_demo.md`) appears verbatim in `deliverables/03-oja-campanas.md` (`grep -xF`, 0 missing lines in all six).
- `campaigns_select.rule_identity()` returns commit `a6212e89...`, rule sha256 `90113af5...`, selector sha256 `1d1bfe77...`, identical to `analysis/results/campaigns/selection_identity.json`.
- Stored numbers are as in the first report: `oja/comparison.json` has abs_cos 0.9999998, Spearman 1.0, overlap@5 5/5, overlap@10 10/10; `oja/dispersion.json` has 10/10 seeds above the abs(cos) gate, 10/10 with the same orientation, pivot `average_caption_words`, worst 1-abs(cos) 2.5e-07; `oja/index.csv` has 50 rows.

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Oja runs in C on centered data with small decreasing eta, renormalized weights and fixed sign convention, and leaves the 50-creator index with convergence evidence | VERIFIED | `neuron/models/oja.c` (unchanged since `5f1f540`) implements the rule, decay, renormalization, `oja_orient` and the per-epoch trace. `analysis/results/oja/{index,weights,convergence}.csv`, `convergence.svg`, `dispersion.json` as above. Behavioral evidence: C suite `make -C neuron test` 1282 checks, 0 failed (run by the caller), and `test_oja.py` runs the real data against PC1 (39 phase-related tests passed when I re-ran `test_oja`, `test_campaigns`, `test_campaigns_select`, `test_maintenance_demo`, `test_variants_ej1`) |
| 2 | A table compares the Oja index with the PC1 projection using abs(cos) and rank correlation | VERIFIED | `comparison.json` values above; the table in section 2 of the fragment equals `report_pc1.md` line by line |
| 3 | Written interpretation with evidence (correlation with followers and topics) of why choosing the maximum for any campaign is wrong | VERIFIED | Section 3 opens with "No.", and `report_evidence.md` is embedded verbatim. The word "mejor" occurs nowhere in the fragment (0 matches) |
| 4 | Per campaign a recommendation justified with Kohonen, Oja and PCA, compared with followers-only at the same k (overlap@k, topic share, cost per Argentine reach), no ROI claims | VERIFIED | Sections 5.1-5.6 present; `comparison.csv`, `objective_metrics.csv`, `shortlists.csv` present; the rule guard passes; the first verification reproduced all six lists independently from `datos/creadores.csv`, and since then no list-producing code or rule input changed (only plotting). Prose fairness: UAT test 1 passed |
| 5 | Concrete maintenance answers for a new campaign, new creators/variables and the monthly update, backed by the saved scaler and retrain decisions | VERIFIED | Section 6 and `analysis/results/maintenance/{demo.json,report_demo.md,synthetic_creator.csv,synthetic_z.csv}`; `maintenance_demo.py` untouched since 2026-10-22; `test_maintenance_demo.py` passes. Concreteness: UAT test 3 passed |

**Score:** 5/5 truths verified (0 present-but-behavior-unverified).

### Human items from the previous report

| Previous item | Now |
|---------------|-----|
| Fairness of section 5 / fútbol recommendation | Resolved: `03-UAT.md` test 1, pass (2026-10-26) |
| Section 7 regeneration pipeline in order | Resolved: `03-UAT.md` test 2, pass |
| Prose fidelity of sections 1-3 and 6 | Resolved: `03-UAT.md` test 3, pass |

`03-UAT.md` is `status: complete`, 3 of 3 passed, 0 issues. I found no new item that needs a human, so the human verification section is empty and the status is `passed`.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `neuron/models/oja.c` | Oja rule, index, trace | VERIFIED | Unchanged; dispatched by `models.c`; tested under sanitizers |
| `analysis/oja.py`, `series_oja.json`, `tests/test_oja.py` | Comparison, dispersion, convergence, evidence | VERIFIED | Only the figure code changed; outputs in `analysis/results/oja/` |
| `analysis/campaigns_select.py` + test | Pre-registered rule | VERIFIED | Frozen, no diff since `a6212e8` |
| `analysis/campaigns.py` + test | Guarded run, metrics, figures | VERIFIED | Guard is first in `main`; figures now have report and slide variants |
| `analysis/maintenance_demo.py` + test | Synthetic creator demo | VERIFIED | Unchanged |
| `deliverables/03-oja-campanas.md` | Sections 1-7 | VERIFIED | Sections 1-7 present; no TBD/FIXME/XXX/TODO/HACK in any covered file |

### Key Link Verification

| From | To | Status | Details |
|------|----|--------|---------|
| `models.c` | `oja.c` | WIRED | Dispatch `run_oja`; C dispatch tests pass |
| `oja.py` | PCA eigenvectors, 10-seed sweep | WIRED | `comparison.json` and `runs.json` present |
| `campaigns.py` | `campaigns_select.rule_identity`, `oja/index.csv`, SOM selection | WIRED | Guard first; `selection_identity.json` matches |
| `maintenance_demo.py` | `scripts/map_creator.py`, `oja/weights.csv` | WIRED | Unchanged |
| Fragment sections | `report_*.md` | WIRED | 0 missing lines in six files |
| `campaigns.py` / `oja.py` | `plots_style.iter_variants` | WIRED | Both variants written: `oja/slide/oja_vs_pc1.*`, `campaigns/slide/shortlists_*.*`; the report variants remain byte-identical to baseline |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real data | Status |
|----------|------|--------|-----------|--------|
| Section 5 lists and tables | six shortlists plus baselines | `datos/creadores.csv` through the frozen rule | Yes | FLOWING |
| Sections 2-3 numbers | comparison, evidence | real C runs vs PCA output | Yes | FLOWING |
| Section 6 demo | BMU distance, Oja index | saved SOM run and `weights.csv` (synthetic input, labelled) | Yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Python suite (caller's regression gate) | `.venv/bin/python -m pytest analysis/tests -q` | 473 passed | PASS |
| C suite (caller's regression gate) | `make -C neuron test` | 1282 checks, 0 failed | PASS |
| Phase 3 tests (my run) | `pytest test_oja test_campaigns test_campaigns_select test_maintenance_demo test_variants_ej1 -q` | 39 passed | PASS |
| Rule guard | `campaigns_select.rule_identity()` | commit `a6212e8`, hashes as pinned | PASS |
| Report SVGs unchanged by Phase 6 | `shasum -c` on `variant_baseline/ej1.sha256` entries for oja and campaigns | 4 OK | PASS |
| Fragment embeds the reports | `grep -xF` per line, six reports | 0 missing | PASS |

I did not run `make campaigns` or `make maintenance` (they re-run SOM stage 1); the existing `analysis/results/` was read instead.

### Probe Execution

No phase-declared probes. Step 7c not applicable.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| OJA-01 | 03-01, 03-03, 03-04 | Oja in C, centered data, small decaying eta, renormalized, fixed sign | SATISFIED | `oja.c`, C tests, `dispersion.json`, `convergence.csv` |
| OJA-02 | 03-03, 03-04 | Index vs PC1 with abs(cos) and rank correlation | SATISFIED | `comparison.json`, section 2 |
| OJA-03 | 03-04 | Interpretation with evidence why the maximum is wrong | SATISFIED | Section 3 |
| CAMP-01 | 03-02, 03-05 | Recommendation per campaign justified with Kohonen, Oja, PCA | SATISFIED | Sections 4, 5.1-5.4, 5.6; UAT test 1 |
| CAMP-02 | 03-02, 03-05 | Comparison vs followers-only at the same k, no ROI claims | SATISFIED | Section 5.5, `comparison.csv` |
| CAMP-03 | 03-06 | Concrete maintenance answers | SATISFIED | Section 6, `maintenance_demo.py`; UAT test 3 |

All six IDs are declared in the PLAN frontmatter, marked Complete in `.planning/REQUIREMENTS.md` (lines 100-105 map them to Phase 3), and no other requirement maps to Phase 3. No orphaned requirements.

### Prohibitions (judgment tier)

Unchanged from the first report and not touched by the two Phase 6 commits: no eigen-solver in `oja.c`; orientation only by the largest-|value| rule; no campaign result existed before the rule commit; price, SOM, PCA and Oja do not decide list membership; no ROI claim; the synthetic creator is labelled and kept out of every list; "mejor" never appears. These are non-authoritative judgment-tier readings, and the UAT (fairness, fidelity) found no problem with them.

### Anti-Patterns Found

None. No debt markers in the covered files; the Phase 6 diffs add no stubs, no empty handlers and no hardcoded data.

### Known open items (not new gaps)

- `03-REVIEW-DISPOSITION.md`: WR-01 to WR-05 and IN-01 to IN-09 are all still `open`. As assessed in the first report, none breaks a must-have: WR-01 (guard does not pin `som_select.py`/`creadores.py`) and WR-02 (Oja gates not enforced in `main()`) concern robustness to future edits or other data; WR-03 (section 5.5 "Métrica objetivo" true by construction) is a wording caveat the recommendation does not rely on; WR-04 is reproducibility cost; WR-05 (drift demo cannot reach the retrain branch) is stated as "no es una prueba" in section 6. Nothing in the Phase 6 diffs touches them.
- `03-SECURITY.md`: `threats_open: 0`.

### Human Verification Required

None.

### Gaps Summary

No gaps. The two Phase 6 changes to covered files are figure-variant drawing only; every Phase 3 result, the pre-registered rule and the fragment text are intact, the full regression gates pass, and the three previously pending human items were answered by the completed UAT (3/3 pass). All six requirement IDs are accounted for.

---

_Verified: 2026-10-26_
_Verifier: Claude (gsd-verifier)_
