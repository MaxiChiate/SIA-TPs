---
phase: 03-oja-y-decisiones-de-campa-a
verified: 2026-10-22T16:00:00Z
status: human_needed
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
covered_digest: "v3:sha256:8917407a8cbae608d28335dd5d3863cbac71aa250f75c20ba244fd8ab1441ee0"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Read section 5 of deliverables/03-oja-campanas.md next to analysis/results/campaigns/ (tables, figures) and section 4. Pay particular attention to the fútbol recommendation (5.1) and the assumptions (1) to (5)."
    expected: "Every recommendation follows from the pasted numbers and the stated assumptions; the comparison with followers is fair (both baselines, same k, advantages of followers stated); nothing implies a commercial outcome (the phrases 'la ropa de entrenamiento es un producto que se elige viéndolo en uso' and 'es la lista más barata en total' are the ones to judge)."
    why_human: "Fairness and honesty of a recommendation is a judgment over meaning. The recommendation is explicitly a judgment and not a result of the rule."
  - test: "From TP4/ in a clean state run the section 7 commands in order (make venv, prepare, pca, som-stage1, oja, campaigns, maintenance, and the test suite)."
    expected: "Every number and figure of the fragment regenerates; make campaigns refuses only if the rule files changed. Note make test breaks on spaces in the repo path (pre-existing Phase 1 Makefile issue), so run .venv/bin/python -m pytest analysis/tests -q and make -C neuron test|debug separately."
    why_human: "Running the full regeneration pipeline (creates timestamped sweep directories and rewrites analysis/results/) was deliberately not done by the verifier; the existing results were inspected instead."
  - test: "Read sections 1 to 3 and 6 next to the report files and figures (convergence.svg, oja_vs_pc1.svg) and check the 'No.' answer in section 3 and the four maintenance answers in section 6."
    expected: "Prose matches the numbers; the maintenance answers are concrete and actionable."
    why_human: "Faithfulness and concreteness of interpretive prose (planned human-check items of plans 03-04 and 03-06)."
---

# Phase 3: Oja y decisiones de campaña Verification Report

**Phase Goal:** As a campaign analyst, I want to build an Oja index and recommend creators per campaign against a followers-only strategy, so that I can choose with evidence and know when the index misleads.
**Verified:** 2026-10-22
**Status:** human_needed
**Re-verification:** No, initial verification

## Goal Achievement

All five ROADMAP success criteria are supported by code and by data in the repository. No gap was found. Status is `human_needed` only because the plans themselves defer interpretive-prose judgments (fairness of the fútbol recommendation, concreteness of the maintenance answers, running section 7 end to end) to a human.

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Oja runs in C on centered data with small decreasing eta, renormalized weights and fixed sign convention, and leaves the 50-creator index with convergence evidence | VERIFIED | `neuron/models/oja.c` (304 lines) implements `w += eta*y*(x - y*w)`, exponential decay via `kohonen_decay` over `epochs*n` steps, fixed epochs, stability guard `eta0*max|x|^2 < 1` before allocation, final renormalization, `oja_orient` (largest-|value| positive, lowest index on tie), `index = x.w`, `trace.csv` per epoch. No eigen-solver in C. `config.json.oja.example`: eta0 0.001, eta_final 0.0001, 500 epochs. `analysis/results/oja/index.csv` has 50 rows. `dispersion.json`: 10/10 seeds abs(cos)>0.99, 10/10 same orientation, pivot `average_caption_words`, worst 1-abs(cos)=2.5e-07. `convergence.csv` + `convergence.svg` exist. C tests: `176 checks, 0 failed` plain and under ASan/UBSan (`make -C neuron debug`). |
| 2 | A table compares the Oja index with the PC1 projection using abs(cos) and rank correlation | VERIFIED | `analysis/results/oja/comparison.json`: abs_cos 0.9999998, cos>0, Pearson 0.99999998, Spearman 1.0, overlap@5 5/5, overlap@10 10/10. The table is in section 2 of the deliverable, line for line identical to `report_pc1.md`. `test_smoke_run_matches_pc1` runs the real data against PC1. |
| 3 | A written interpretation with evidence (correlation with followers and topics) of why choosing the maximum for any campaign is wrong | VERIFIED | Section 3 opens with "**No.**", gives the 26 weights, Pearson/Spearman with followers (-0,879/-0,921) and the four raw topic shares, top-10 overlap and composition, and the maximum under both signs (INF031 perros 17k followers vs INF045 fútbol 493k). Every line of `report_evidence.md` appears verbatim. The banned adjective "mejor" does not occur anywhere in the fragment. |
| 4 | For each campaign a recommendation justified with Kohonen, Oja and PCA, compared against followers-only at same k (overlap@k, topic share, cost per Argentine reach), without ROI claims | VERIFIED (prose fairness is a human item) | I recomputed all six lists independently from `datos/creadores.csv` with a separate script (stdlib only: dominant topic, ddof=1 z-scores, depth score, art composite, cost per thousand) and all six match section 5 exactly, as do both followers baselines for fútbol and global. Filter sizes 15/13/11/11 confirmed. Tables carry n, overlap@5 with both baselines, topic share, Argentine reach, total cost, USD per thousand. Kohonen/Oja/PCA appear as the descriptive reading in 5.6 (neuron, Oja rank, PC1/PC2 per list), which is exactly the D-15 design that the phase context locks as how CAMP-01 is satisfied. ROI: the only occurrences are explicit disclaimers (sections 4 and 5.5). Advantages of followers are listed. |
| 5 | Concrete maintenance answers for a new campaign, new creators/variables and the monthly update, backed by the saved scaler and retraining decisions | VERIFIED | Section 6 answers all four with concrete mechanics (new campaign = new rule, no retrain; new creators = `scripts/map_creator.py` + saved `.meta.json`, BMU, Oja `x.w`, retrain when BMU distance > training max; new variables = redo audit, restandardize, retrain; monthly = fixed seed, versioned scaler/codebook, content labels, D-02 sign). `analysis/results/maintenance/` holds `demo.json`, `report_demo.md`, `synthetic_creator.csv`, `synthetic_z.csv`; the demo's lines are verbatim in section 6; the creator is labelled SYN001/sintético. `test_map_creator_cli_matches_transform` passes. |

**Score:** 5/5 truths verified (0 present-but-behavior-unverified).

### Pre-registration (D-07) checks requested by the caller

| Check | Result |
|-------|--------|
| Rule commit `a6212e8` holds exactly three files | PASS: `analysis/campaigns_select.py`, `analysis/tests/test_campaigns_select.py`, `deliverables/03-oja-campanas.md` (`git show --stat`) |
| `rule_identity()` passes at HEAD | PASS: returns `rule_commit a6212e89...`, `rule_sha256 90113af5...`, `select_sha256 1d1bfe77...`; identical to `analysis/results/campaigns/selection_identity.json` and to the hashes quoted in section 5 |
| `campaigns.py` did not exist before the rule commit | PASS: first added in `4b80b3e`, after `a6212e8` |
| `campaigns.py` has no bypass of the guard | PASS: `rule_identity()` is the first call in `main` (line 434); no environment variable or skip flag |
| Frozen rule text/code unchanged since | PASS: `git status` clean apart from untracked `.planning/milestone.lock`; `rule_identity` compares against the rule commit |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `neuron/models/oja.c` | Oja rule, index, trace | VERIFIED | Substantive, dispatched via `run_oja`; `oja_stub.c` removed |
| `neuron/io/config.c`, `models.h`, `config.json.oja.example`, `neuron/README.md` | Strict Oja keys, docs | VERIFIED | Exercised by C tests (176 checks) |
| `analysis/oja.py`, `series_oja.json`, `tests/test_oja.py` | Comparison, dispersion, convergence, evidence | VERIFIED | Outputs present in `analysis/results/oja/` |
| `analysis/campaigns_select.py` + test | Pre-registered rule | VERIFIED | Frozen; tests pass |
| `analysis/campaigns.py` + test | Guarded run, metrics, 2 figures | VERIFIED | Outputs in `analysis/results/campaigns/` incl. both SVGs |
| `analysis/maintenance_demo.py` + test | Synthetic creator demo | VERIFIED | Outputs in `analysis/results/maintenance/` |
| `deliverables/03-oja-campanas.md` | Sections 1-7 | VERIFIED | 335 lines; sections 1-7 present; no TBD/FIXME/XXX/TODO in any phase file |
| `Makefile` targets `oja`, `campaigns`, `maintenance` | Reproduction | VERIFIED | Lines 70, 77, 83 |

### Key Link Verification

| From | To | Status | Details |
|------|----|--------|---------|
| `models.c` | `oja.c` | WIRED | dispatch `run_oja`; C dispatch test passes |
| `oja.c` | `kohonen_decay` | WIRED | used in `train` |
| `oja.py` | `pca/audited/eigenvectors.csv`, `sweep` | WIRED | comparison reads PCA output; 10-seed sweep produced `runs.json` |
| `campaigns.py` | `campaigns_select.rule_identity`, `oja/index.csv`, SOM `selection.json` | WIRED | guard first; tie-break reads `oja_index`; neurons from the Phase 2 figure run |
| `maintenance_demo.py` | `scripts/map_creator.py`, `oja/weights.csv` | WIRED | subprocess with argument list; saved `w` used for the index |
| Deliverable sections | `report_*.md` | WIRED | A line-by-line `grep -xF` of all six report files against the fragment: 0 missing lines |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real data | Status |
|----------|------|--------|-----------|--------|
| Section 5 lists/tables | six shortlists + baselines | `datos/creadores.csv` through `campaigns_select` | Yes, reproduced independently | FLOWING |
| Section 2/3 numbers | comparison, evidence | 10 real C runs of the binary vs PCA output | Yes | FLOWING |
| Section 6 demo | BMU distance, Oja index | saved SOM run + `weights.csv` | Yes (synthetic input by design, labelled) | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Python suite | `.venv/bin/python -m pytest analysis/tests -q` | 83 passed | PASS |
| C suite under sanitizers | `make -C neuron debug` | 176 checks, 0 failed | PASS |
| C suite plain | `make -C neuron test` (C part) | 176 checks, 0 failed (its pytest step breaks on the path with spaces, the known Phase 1 Makefile issue) | PASS |
| Rule guard | `campaigns_select.rule_identity()` | commit `a6212e8` | PASS |
| Independent list recomputation | stdlib script over `datos/creadores.csv` | all 6 own lists, global and fútbol in-topic baselines match section 5 | PASS |

### Probe Execution

No phase-declared probes (`probe-*.sh`). Step 7c not applicable.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| OJA-01 | 03-01, 03-03, 03-04 | Oja en C, centered data, small decaying eta, renormalized, fixed sign | SATISFIED | `oja.c`, C tests, `dispersion.json`, `convergence.csv` |
| OJA-02 | 03-03, 03-04 | Index vs PC1 with abs(cos) and rank correlation | SATISFIED | `comparison.json`, section 2 |
| OJA-03 | 03-04 | Interpretation with evidence why the maximum is wrong | SATISFIED | Section 3 |
| CAMP-01 | 03-02, 03-05 | Recommendation per campaign justified with Kohonen, Oja, PCA | SATISFIED (prose judgment is a human item) | Sections 4, 5.1-5.4, 5.6 |
| CAMP-02 | 03-02, 03-05 | Comparison vs followers-only, same k, no ROI claims | SATISFIED | Section 5.5, `comparison.csv` |
| CAMP-03 | 03-06 | Concrete maintenance answers | SATISFIED | Section 6, `maintenance_demo.py` |

All six IDs appear in PLAN frontmatter, are marked Complete in REQUIREMENTS.md, and map to Phase 3. No orphaned requirements.

### Prohibitions (must_haves.prohibitions, all judgment tier)

All were checked in code or by git history and none is violated: no eigen-solver in `oja.c`; orientation is only the largest-|value| rule; `oja.py` does not re-orient runs; no `campaigns.py` or campaign results existed before the rule commit; price, SOM, PCA and Oja do not decide list membership (the independent recomputation reproduces every list with the rule alone; section 5.6 reports that no tie reached the Oja tie-break); no ROI claim; the synthetic creator is labelled and kept out of every list; no use of "mejor" for the index. These are judgment-tier items with a non-authoritative verdict; the readings above should be confirmed by the human items.

### Code review warnings and whether they undermine a must-have

Dispositions in `03-REVIEW-DISPOSITION.md` are all still `open` (not yet triaged).

| Finding | Effect on must-haves |
|---------|----------------------|
| WR-01 (guard does not pin `som_select.py`/`creadores.py`) | Does not break SC4 today (the identity check passes and lists reproduce). It weakens the strength of the pre-registration only against future edits to unfrozen helpers. Advisory. |
| WR-02 (Oja gates not enforced in `main()`) | SC1/SC2 are true on the actual data (10/10 on both gates, worst 1-abs(cos)=2.5e-07). The risk is only that a future run on other data would not fail loudly. Advisory; fix outside frozen files is cheap. |
| WR-03 (section 5.5 "Métrica objetivo" true by construction for the in-topic baseline) | I checked that the sentence is factually correct on every row. It is not independent evidence, and a reader could take it as such, but the same section already states the in-topic baseline "no distingue" on topic and the recommendation does not rely on it. Does not undermine SC4; worth a one-sentence rewording (outside the markers). |
| WR-04 (Makefile re-runs upstream stages) | Reproducibility cost, not a goal failure. |
| WR-05 (drift demo cannot reach the retrain branch; in-sample threshold) | SC5 asks for concrete answers backed by the saved scaler and retrain decisions; the retrain rule is stated and unit-tested on toy numbers, and section 6 says the demo only shows the mechanism ("no es una prueba..."). The in-sample bias of the threshold is not mentioned. Advisory. |

None is a blocker.

### Anti-Patterns Found

None. No TBD/FIXME/XXX/TODO/HACK in the phase files. No stubs: every artifact is substantive and consumed downstream.

### Human Verification Required

1. **Fairness of the section 5 recommendation.** Read section 5 next to `analysis/results/campaigns/` and section 4. Expected: each recommendation follows from the pasted numbers and stated assumptions, the followers comparison is fair, and nothing implies a commercial outcome. Why human: judgment over meaning. The fútbol recommendation (profundidad first) is explicitly a judgment resting on assumption (1) about training apparel.
2. **Run section 7 in order.** Expected: all numbers and figures regenerate. Why human: the verifier did not re-run the pipeline, because it would write new timestamped sweep directories into `analysis/results/`. Use the Python and C test commands separately (the `make test` path-with-spaces issue is pre-existing).
3. **Prose faithfulness of sections 1-3 and 6.** Expected: prose matches numbers; maintenance answers are concrete. These are the planned human-check items of plans 03-04 and 03-06. All pasted tables and bullets already match their reports exactly.

### Gaps Summary

No gaps. All five success criteria hold in the codebase, the pre-registration chain is intact, and all six requirement IDs are accounted for. The only open items are the human judgments listed above and five non-blocking review warnings that are still untriaged.

---

_Verified: 2026-10-22_
_Verifier: Claude (gsd-verifier)_
