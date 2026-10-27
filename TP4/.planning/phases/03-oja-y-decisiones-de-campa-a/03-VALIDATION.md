---
phase: "3"
slug: "oja-y-decisiones-de-campa-a"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-22"
validated: "2026-10-26"
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | C: `check()`/`check_close()` in `neuron/tests/test_main.c` (ASan/UBSan via `make -C neuron debug`); Python: pytest |
| **Config file** | `neuron/Makefile` (`test-c`, `debug`, `test`); `analysis/tests/conftest.py` |
| **Quick run command** | `make -C neuron test-c` (C) or the touched file among `analysis/tests/test_oja.py`, `test_campaigns_select.py`, `test_campaigns.py`, `test_maintenance_demo.py` |
| **Full suite command** | `make test && make -C neuron debug` |
| **Estimated runtime** | ~30 seconds (the four Phase 3 pytest files plus `make -C neuron test-c`: ~1 s) |

---

## Sampling Rate

- **After every task commit:** Run `make -C neuron test-c` or the relevant pytest file
- **After every plan wave:** Run `make test && make -C neuron debug`
- **Before `/gsd-verify-work`:** Full suite green, `rule_identity()` passes, and `make oja` / `make campaigns` / `make maintenance` byte-identical on rerun (except `runs.json`)
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

Reconstructed from the `<automated>` blocks of plans 03-01 to 03-06, their SUMMARY files and `03-SECURITY.md`. Checkpoint tasks (03-02 Tasks 1 and 3) are human gates and appear under Manual-Only.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | OJA-01 | T-03-01 | `epochs` bounded before allocation | C integration + smoke sweep | `make -C neuron test-c`; `analysis/sweep.py analysis/series_smoke_oja.json` (3 runs `ok`) | ✅ | ✅ green |
| 03-01-02 | 01 | 1 | OJA-01 | T-03-02, T-03-03 | Fixture convergence, trace, `oja_orient`; rejects `eta0 >= 1`, `eta_final > eta0`, `epochs 0`, missing key, `eta0 · max\|x\|² ≥` bound; no memory errors | C unit + sanitizer | `make -C neuron test-c` (`oja training`, `config strict validation`); `make -C neuron debug` | ✅ | ✅ green |
| 03-02-02 | 02 | 1 | CAMP-01, CAMP-02 | T-03-04, T-03-05 | Topic filter, one criterion per list, k = 5, Oja/`creator_id` tie-break, no padding, two followers baselines; `rule_identity` refuses changed rule text, changed selector, split commit, untracked files | pytest (synthetic + tmp git repos) | `.venv/bin/python -m pytest analysis/tests/test_campaigns_select.py -q` (17) | ✅ | ✅ green |
| 03-03-01 | 03 | 2 | OJA-01, OJA-02 | T-03-07, T-03-08 | Input centered; real-data run abs(cos(w, v1)) > 0.99 with PCA orientation, ‖w‖ = 1, index = Z w; compare identity/flip; top-k overlap; reader rejects bad header | pytest | `.venv/bin/python -m pytest analysis/tests/test_oja.py -q -k "centered or smoke or compare or top_k or rejects"` | ✅ | ✅ green |
| 03-03-02 | 03 | 2 | OJA-01 | — | Per-epoch abs(cos) from `trace.csv` normalizes; seed dispersion; `make oja` reruns byte-identical | pytest + rerun | `.venv/bin/python -m pytest analysis/tests/test_oja.py -q -k convergence` | ✅ | ✅ green |
| 03-04-01 | 04 | 3 | OJA-03 | T-03-15, T-03-16 | Evidence under both signs (correlation with followers and topics, top 10); section 3 embeds `report_evidence.md`, opens with "No.", no "mejor" | pytest + fragment grep | `.venv/bin/python -m pytest analysis/tests/test_oja.py -q -k evidence`; `analysis/facts.py check` | ✅ | ✅ green |
| 03-04-02 | 04 | 3 | OJA-02 | T-03-15 | Index-vs-PC1 figure; sections 1-2 embed `report_convergence.md` and `report_pc1.md` | fragment grep + rerun | `analysis/facts.py check`; per-line `grep -xF` of the reports in `deliverables/03-oja-campanas.md` | ✅ | ✅ green |
| 03-05-01 | 05 | 4 | CAMP-01, CAMP-02 | T-03-10, T-03-12 | `main` refuses without the committed rule; overlap counts shared ids once; cost per Argentine reach as ratio of sums; short/empty list; topic share | pytest | `.venv/bin/python -m pytest analysis/tests/test_campaigns.py -q -k "overlap_counts or ratio_of_sums or short_and_empty or topic_share or refuses"` | ✅ | ✅ green |
| 03-05-02 | 05 | 4 | CAMP-01 | — | Objective means; Oja-index top-k overlap; biplot and SOM figures deterministic | pytest + rerun | `.venv/bin/python -m pytest analysis/tests/test_campaigns.py -q -k "index_top or objective"` | ✅ | ✅ green |
| 03-05-03 | 05 | 4 | CAMP-01, CAMP-02 | — | Section 5 embeds `report_campaigns.md` and `report_reading.md`; no ROI claim | fragment grep | `analysis/facts.py check`; per-line `grep -xF` | ✅ | ✅ green |
| 03-06-01 | 06 | 5 | CAMP-03 | T-03-13, T-03-14 | Synthetic creator labelled and kept out of lists; CLI mapping equals scaler transform; drift threshold; BMU and index rank | pytest | `.venv/bin/python -m pytest analysis/tests/test_maintenance_demo.py -q` (4) | ✅ | ✅ green |
| 03-06-02 | 06 | 5 | CAMP-03 | — | Section 6 embeds `report_demo.md` with the four maintenance answers; section 7 names the targets | fragment grep + full suite | `analysis/facts.py check`; `make test` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Observed on 2026-10-26: the four Phase 3 pytest files → 35 passed; `make -C neuron test-c` → 1282 checks, 0 failed (`ok   oja training` among them); `make -C neuron debug` → 1282 checks, 0 failed, no sanitizer reports; `campaigns_select.rule_identity()` → rule commit `a6212e89cdc654021cfda02d9d16237c8c21c332`; `analysis/facts.py check` → `DRIFT_OK 68 pins`; every line of the six `report_*.md` files present in `deliverables/03-oja-campanas.md` (0 missing); "mejor" occurs 0 times in section 3.

---

## Wave 0 Requirements

- [x] Oja cases in `neuron/tests/test_main.c` (`oja training`, strict keys, `oja_run_accepts`) on `neuron/tests/fixtures/zscore_small.csv`
- [x] `analysis/tests/test_oja.py`, `test_campaigns_select.py`, `test_campaigns.py`, `test_maintenance_demo.py`
- [x] `analysis/series_smoke_oja.json` for the end-to-end smoke series

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Rule terms approved and committed before any list existed (pre-registration, commit `a6212e8`) | CAMP-01, CAMP-02 | Pre-registration decision (checkpoints 03-02 Tasks 1 and 3) | User approved and committed the rule; the guard is automated afterwards (`rule_identity`) |
| Fairness of section 5 and the fútbol recommendation; no commercial outcome implied | CAMP-01, CAMP-02 | Prose judgment | `03-UAT.md` test 1 (pass, 2026-10-26) |
| Sections 1-3 and 6 faithful to the figures; section 3 argues "No." with evidence; maintenance answers concrete | OJA-03, CAMP-03 | Prose quality | `03-UAT.md` test 3 (pass, 2026-10-26) |
| Section 7 pipeline regenerates every number in order | CAMP-03 | Slow (re-runs SOM stage 1) | `03-UAT.md` test 2 (pass, 2026-10-26) |

Known open review findings (`03-REVIEW-DISPOSITION.md`, WR-01 to WR-05 and IN-01 to IN-09) are robustness and wording caveats, not uncovered requirements; see `03-VERIFICATION.md`, "Known open items".

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-10-26

## Validation Audit 2026-10-26

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
