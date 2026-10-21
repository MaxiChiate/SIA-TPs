---
phase: 02-kohonen-som
verified: 2026-10-21T19:10:00Z
status: passed
score: 4/4 must-haves verified
covered_files:
  - ".planning/phases/02-kohonen-som/02-01-PLAN.md"
  - ".planning/phases/02-kohonen-som/02-01-SUMMARY.md"
  - ".planning/phases/02-kohonen-som/02-02-PLAN.md"
  - ".planning/phases/02-kohonen-som/02-02-SUMMARY.md"
  - ".planning/phases/02-kohonen-som/02-03-PLAN.md"
  - ".planning/phases/02-kohonen-som/02-03-SUMMARY.md"
  - ".planning/phases/02-kohonen-som/02-04-PLAN.md"
  - ".planning/phases/02-kohonen-som/02-04-SUMMARY.md"
  - ".planning/phases/02-kohonen-som/02-05-PLAN.md"
  - ".planning/phases/02-kohonen-som/02-05-SUMMARY.md"
  - ".planning/phases/02-kohonen-som/02-06-PLAN.md"
  - ".planning/phases/02-kohonen-som/02-06-SUMMARY.md"
  - "Makefile"
  - "analysis/som.py"
  - "analysis/som_figures.py"
  - "analysis/som_loo.py"
  - "analysis/som_profiles.py"
  - "analysis/som_select.py"
  - "analysis/som_stage.py"
  - "deliverables/02-kohonen.md"
  - "neuron/io/config.c"
  - "neuron/models/kohonen.c"
covered_digest: "v3:sha256:aab656d21823bf75f6af1e02aae1a068cb81c7e5f2e44c35b44c896b361a126a"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Decide whether a single region (R1 = all 50 creators) satisfies the goal 'read creator profiles by region'"
    expected: "Either accept the pre-registered region rule as honestly reported (profiles are then read per neuron, which the deliverable does), or open a new discussion to define regions differently. Do NOT edit the rule in place (it would void 'fijada de antemano')."
    why_human: "The committed rule (cut edges above P75 of prototype distances, connected components) produced n_regions = 1 on the chosen 5x5 map (pca_contrast.json). Technically correct and honest, but the goal's 'by region' reading is then carried by per-neuron profiles. Whether that meets the analyst's intent is a product judgment."
  - test: "Read section 2 of deliverables/02-kohonen.md (between <!-- regla:inicio --> and <!-- regla:fin -->) against D-10..D-15 in 02-CONTEXT.md"
    expected: "Prose and the executable som_select.py implement the same rule (filters TE<=0.05, empty<=20%, >=2 creators/occupied; lowest QE-LOO; 1-SD band then stability then smaller k; TE-only relaxation; no grid if occupancy fails)."
    why_human: "Rule-prose-vs-decision fidelity is a human-judgment item flagged in 02-03-SUMMARY. The verifier read both and found them consistent; sign-off is the human's."
  - test: "Open analysis/results/som/figures/*.svg|png and analysis/results/som/profiles/*.svg|png and judge legibility"
    expected: "Hit map, U-matrix, component planes, stage-1 curves, trace, regions, PC planes are legible at presentation size."
    why_human: "Visual legibility. Observed minor issue: in stage1_curves the annotation 'menor QE: k = 8' overlaps the k=6-7 step curve, and +/-SD error bars dip below 0 for TE and % empty. Not blocking."
  - test: "Read sections 5, 6 and 7 of the deliverable against the Phase 1 biplot (analysis/results/pca/audited/biplot.svg and deliverables/01-datos-pca.md section 6)"
    expected: "'Yes for PC1, no for PC2' is consistent with the biplot reading (PC1 = scale/price axis; PC2 = Argentine audience / dogs) and the creator-pair disagreements are real."
    why_human: "Interpretive prose quality and agreement with the biplot cannot be proven by grep. Numbers were independently recomputed (see below) and match."
  - test: "Review the judgment-tier prohibitions (non-authoritative LLM-judge verdicts below) - unverified-prohibition, human review recommended"
    expected: "Reviewer confirms the 12 prohibitions across plans 02-01..02-06 held."
    why_human: "ADR-550 D4: judgment-tier prohibitions are soft-gated; autonomous verdicts are flagged, never a silent pass."
---

# Phase 2: Kohonen SOM Verification Report

**Phase Goal:** As a campaign analyst, I want to train a Kohonen map of the 50 creators with a grid chosen by a rule fixed beforehand, so that I can read creator profiles by region and contrast them with PC1/PC2.
**Verified:** 2026-10-21T19:10:00Z
**Status:** human_needed
**Re-verification:** No - initial verification

No BLOCKER found. Every ROADMAP success criterion is backed by code and by artifacts I re-derived myself. `human_needed` is driven by the human-judgment checks the summaries flagged plus one product-level question (single region), not by a failed truth.

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria are the contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SOM run on z-scored data (k x k grid, decreasing neighborhood and eta, sample init) reports QE, TE and per-neuron occupancy in metrics.json and CSVs, reproducible by seed | VERIFIED | `neuron/models/kohonen.c` (450 lines): `kohonen_decay`/`kohonen_radius` (exponential, radius floored at `radius_final`), `kohonen_neighbor_weight` (step with `<=`, gaussian), update `weights[j] += eta*h*(sample[j]-weights[j])` (l.292), shuffled epochs via `rng_shuffle`, sample init. Run `033_k5-step_seed4/metrics.json` has qe, te, occupied_neurons, empty_fraction, mean_hits_occupied, max_hits, singleton_neurons; occupancy.csv, trace.csv, prototypes.csv, assignments.csv present. I recomputed QE/TE/occupancy in numpy from prototypes.csv: qe 2.7238248293658818, te 0.06, 22 occupied; identical to the C values. `make test`: 118 C checks 0 failed (incl. ASan/UBSan build per review), 48 pytest passed. Re-running `make som-figures` and `make som-profiles` reproduced all figure and profile files with identical md5. |
| 2 | Multi-seed sweep yields summary and the grid rule (QE, TE, occupancy, QE-LOO, seed stability) written and committed BEFORE looking at results; grid chosen by the rule, not lowest QE | VERIFIED | Rule commit `ea7a0b1` (14:37:25) adds `deliverables/02-kohonen.md` (rule between markers), `analysis/som_select.py`, `analysis/series_som_stage1.json`. First trained-SOM commit `47d5424` is 14:41:31; stage-1 run dir stamped 14:52:22. Rule text between markers and `som_select.py`/`series_som_stage1.json` are byte-identical to `ea7a0b1` today (diff empty). stage-1 `aggregate.csv` has 14 labels (k=2..8 x step/gaussian) x 10 seeds; `selection.json`: outcome chosen, chosen_k 5, decided_by qe_loo, te_filter_dropped false. Table: k=2,3 fail TE; k=4,5 pass all; k=6 fails creators (1.68); k=7,8 fail empty and creators. Training-QE argmin is k=8 and is reported but not used (D-15). Stage 2 series equals `som_select.stage2_series(5)` exactly; verdict robust=false (5 of 10 variants fail TE) is reported, k not re-selected. |
| 3 | For the chosen grid, hit map, U-matrix and component planes exist | VERIFIED | `analysis/results/som/figures/`: `map.svg/png` (hits + U side by side, empty hatched, U scale 1.59-2.97 full range), `planes_main.*` (4 PC1 + 4 PC2 loading variables, plus topic_art/content_showcase raw means), `planes_appendix.*` (all 26 + 5 excluded), `stage1_curves.*`, `trace.*`. Viewed map.png, planes_main.png, stage1_curves.png: content matches the section 5 prose (3 empty neurons at (0,3), (1,2), (3,3); max 5 at (0,0)). |
| 4 | Region profiles interpreted for the agency, contrasted with PC1/PC2 of the biplot, written answer to what a high U distance means | VERIFIED (see human item 1) | Section 6 of the deliverable: 6.1 regions, 6.2 raw-unit profiles, 6.3 agency reading, 6.4 PC1/PC2 contrast with pre-declared stats and permutation p, 6.5 U-matrix answer using `high_u_edges.csv`. I recomputed with numpy: R2(PC1 on BMU row,col) = 0.961324 and R2(PC2) = 0.055229, equal to `pca_contrast.json` (p = 0.001 and 0.267 from 1000 permutations, seed 2026). Caveat: the committed region rule yields one region (n_regions 1), so "by region" is carried by per-neuron profiles (neurons with <2 creators flagged). Honestly reported; routed to human. |

**Score:** 4/4 truths verified (0 present-but-behavior-unverified). Plan-level must_haves (02-01..02-06) were also checked: seven strict Kohonen config keys, `occupancy.csv`/`trace.csv`, grid_k up to 32 (k=8 gives 64 occupancy rows), C-vs-numpy cross-check, tie-aware Spearman, LOO driver, guarded stage driver, deterministic SVGs, region rule and permutation seeds.

### Deferred Items

None. Phase 3 (Oja, campaigns) consumes SOM regions but does not close any Phase 2 gap.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `neuron/models/kohonen.c` | Real SOM trainer | VERIFIED | 450 lines, `kohonen_stub.c` gone (`ls neuron/models`: hopfield_stub.c, kohonen.c, models.c, models.h, oja_stub.c); dispatch in models.c. |
| `neuron/io/config.c` | 7 strict Kohonen keys | VERIFIED | Tests for missing/typed/out-of-range keys pass. |
| `analysis/som.py` | Reader, numpy recomputation, Spearman, stability, U-matrix | VERIFIED | Imports only numpy/stdlib; no sklearn/minisom/scipy. |
| `analysis/som_select.py`, `series_som_stage1.json`, rule section | Pre-registered rule | VERIFIED | Unchanged since `ea7a0b1`. |
| `analysis/som_loo.py`, `som_stage.py` | LOO and guarded stages | VERIFIED | 7 000 LOO trainings recorded; stage2 series generated and committed. |
| `analysis/som_figures.py`, `som_profiles.py` | Figures and profiles | VERIFIED | Outputs regenerate byte-identically. |
| `Makefile` | som-stage1/2, som-figures, som-profiles | VERIFIED | Both figure/profile targets ran successfully. |
| `deliverables/02-kohonen.md` | Sections 1-7 | VERIFIED | Present, numbers match results files. |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| models.c | kohonen.c | dispatch `run_kohonen` | WIRED |
| config.c KOHONEN_KEYS | kohonen.c read_params | `radius_final` etc. | WIRED |
| som_stage.py | som_select.py | `rule_guard`/`rule_digest`/`SELECT_FILE` | WIRED |
| som_stage.py | som_loo.py, som.py | `run_loo`, `medoid_seed` | WIRED |
| som_figures.py / som_profiles.py | selection.json | `figure_run`, `chosen_k`, `require_same_rule` | WIRED (figure seed 4 = stability medoid in aggregate.csv) |
| som_profiles.py | pca.py | `pca_eigh` + scores | WIRED (R2 independently reproduced) |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real data | Status |
|----------|------|--------|-----------|--------|
| map.png / planes | hits, U, prototypes | C run `033_k5-step_seed4` outputs | yes (recomputed) | FLOWING |
| Section 3 table | mean +/- SD | `aggregate.csv` from 140 real runs + LOO | yes | FLOWING |
| Section 6 stats | R2, Mantel, edges | `pca_contrast.json` from real scores | yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full tests | `make test` | 118 checks 0 failed; 48 passed | PASS |
| C vs numpy QE/TE/occupancy | numpy script over `033_k5-step_seed4` | 2.7238248293658818 / 0.06 / 22 equal C | PASS |
| PC1/PC2 R2 on BMU | numpy lstsq | 0.96132 / 0.05523 equal pca_contrast.json | PASS |
| Reproducibility of figures and profiles | `make som-figures && make som-profiles`, md5 before/after | IDENTICAL | PASS |
| Stage-2 series is generated, not hand-edited | `som_select.stage2_series(5) == series_som_stage2.json` | True | PASS |
| Pre-registration intact | diff rule block, som_select.py, series stage 1 vs `ea7a0b1` | identical | PASS |

### Probe Execution

Step 7c: SKIPPED. No `probe-*.sh` is declared by any plan.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SOM-01 | 02-01 | SOM in C, k x k, decreasing neighborhood and eta, sample init | SATISFIED | kohonen.c, tests |
| SOM-02 | 02-01, 02-02 | QE, TE, occupancy | SATISFIED | metrics.json, numpy cross-check reproduced |
| SOM-03 | 02-02, 02-03, 02-04 | Multi-seed sweep, rule fixed before results (QE, TE, occupancy, LOO, stability) | SATISFIED | commit `ea7a0b1` precedes training; rule unchanged; selection.json |
| SOM-04 | 02-05 | Hit map, U-matrix, component planes | SATISFIED | figures present and viewed |
| SOM-05 | 02-06 | Region profiles contrasted with PC1/PC2; U-matrix answer | SATISFIED with caveat | Section 6; single region (human item 1) |

All five IDs appear in plan frontmatter (`requirements:` of 02-01..02-06) and in REQUIREMENTS.md (marked Complete, traceability Phase 2). No orphaned Phase 2 requirements.

### Code Review (02-REVIEW.md, 0 critical / 4 warning / 7 info, all open) - effect on must-haves

| Finding | Undermines a must-have? | Assessment |
|---------|-------------------------|------------|
| WR-01 equality tolerance in filters (pre-registered) | No | I read stage-1 and stage-2 values: no mean sits on a threshold, except stage-2 `epochs-1040` te_mean = 0.05 which passes. The k=5 choice (TE 0.046, empty 15.6 %, 2.39 creators) is not boundary-sensitive. Cannot be edited in place without voiding pre-registration. |
| WR-02 guard does not compare current text to rule commit | No in this run | I did the missing comparison: rule block, `som_select.py` and `series_som_stage1.json` are byte-identical to `ea7a0b1`. Guard is weaker than the doc implies but the claim is true here. |
| WR-03 stage-2 verdict does not check series k | No | Stage-2 aggregate has grid_k = 5 in all 10 rows and the series equals the generator output. |
| WR-04 gaussian NaN with radius_final < ~1e-162 | No | All series use radius_final = 1. Latent input-validation weakness only. |
| IN-01 QE-LOO monotone in k, so the rule is effectively "largest k passing the filters" | Does not break SOM-03, but is worth a human thought | Choice of k=5 is decided by filters; the deliverable discloses stage-2 fragility (5/10 variants fail TE). Design observation, not a defect. |
| IN-02..IN-07 | No | Hygiene. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (modified Phase 2 files) | - | `TBD`/`FIXME`/`XXX` grep over kohonen.c, config.c, som*.py, deliverable, Makefile, neuron README | none | No debt markers |
| neuron/models/kohonen.c | 199-206 | dead optional-hits allocation, unchecked calloc (IN-02) | Info | Unreachable path |
| analysis/som_stage.py, som_loo.py, som_profiles.py | - | duplicated CSV writer (IN-03) | Info | Maintainability |

### Judgment-tier prohibitions (NON-AUTHORITATIVE LLM-judge verdicts - unverified-prohibition, human review recommended)

| Plan | Prohibition | Verdict | Evidence |
|------|-------------|---------|----------|
| 02-01 | No external ML/SOM library | held | grep of imports in som*.py clean; trainer is hand-written C |
| 02-01 | No trained SOM on creators' data before the rule commit | held | `ea7a0b1` 14:37:25 < `47d5424` 14:41:31 < stage-1 run 14:52:22 |
| 02-02 | No external library for BMU/measures | held | numpy and stdlib only |
| 02-03 | No change to rule/series/select code after any stage-1 run | held | diff vs `ea7a0b1` empty |
| 02-03 | No choice by lowest training QE | held | chosen k=5, training-QE argmin k=8 reported only |
| 02-03 | No outcome picking a k failing occupancy | held | `select_grid` outcomes are only `chosen` / `no_eligible_grid` |
| 02-04 | No single-seed or best-seed results | held | tables are mean +/- SD over 10; the single drawn run is the pre-declared stability medoid |
| 02-04 | No re-selection from stage 2 / no hand edit of stage-2 series | held | robust=false reported, k stays 5; series equals generator |
| 02-05 | Seed/variables not chosen by looks; no truncated U scale or filled empty neurons | held | medoid seed 4; U scale 1.59-2.97 full; empty hatched |
| 02-06 | Topics do not validate regions | held | section 6.2/6.3 states topics are inputs |
| 02-06 | No profile of <2-creator neuron as a group | held | 7 singleton neurons flagged, excluded from table |
| 02-06 | No agree/disagree with biplot without declared stats and p | held | section 6.4 cites R2, Mantel, permutation p |

### Human Verification Required

1. **Single region vs the goal "by region".** Test: read 6.1-6.3. Expected: accept per-neuron reading or open a new discussion for a different region definition (do not edit the committed rule in place). Why human: product intent.
2. **Rule prose vs D-10..D-15.** Verifier found them consistent; needs sign-off.
3. **Figure legibility.** Minor overlap of the "menor QE: k = 8" label with the curve; error bars below zero.
4. **Sections 5-7 against the Phase 1 biplot.** Numbers reproduced; interpretation needs a reader.
5. **Judgment-tier prohibitions** above (flagged, non-authoritative).

### Gaps Summary

No gaps. The phase goal is achieved in code and artifacts: a hand-written C SOM trains reproducibly on the 26 z-scored variables, the grid rule was committed before any trained SOM ran and was not altered afterwards, k = 5 was chosen by that rule (not by QE), and the map, U-matrix, planes, profiles and PC1/PC2 contrast all exist and were independently recomputed. The four open code-review warnings do not undermine any must-have. Residual risk is interpretive: the pre-registered region rule collapsed the map into a single region, so the "by region" reading rests on per-neuron profiles, and stage-2 robustness failed on TE in 5 of 10 variants (both reported honestly in the deliverable).

---

_Verified: 2026-10-21T19:10:00Z_
_Verifier: Claude (gsd-verifier)_
