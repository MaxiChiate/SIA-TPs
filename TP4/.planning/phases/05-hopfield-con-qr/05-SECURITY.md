---
phase: "05"
slug: "hopfield-con-qr"
status: verified
threats_open: 0
asvs_level: 1
created: "2026-10-25"
---

# Phase 05 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail. Threat registers were authored at plan time (every PLAN.md carries a `<threat_model>` block) — this is an L1 verification against that register, not a retroactive STRIDE build.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| config.json to C binary | untrusted config keys/values cross into the strict validator | model config (rule, subset, trace_trials) |
| stored-pattern CSV to C binary | untrusted pm-one matrix crosses into `is_pm_one` and the Gram inversion | pattern matrix (±1 values) |
| PNG bytes to scripts/qr.py | untrusted image content crosses into the converter | raw image bytes |
| analyst to pre-registration record | a later edit of the protocol or images after seeing results would corrupt the "fixed beforehand" claim | protocol text, PNG hashes |
| git working tree to the guard | uncommitted or changed guarded files crossing into a run | file content hashes |
| qr_pm1.csv to C binary | the pm-one pattern matrix crosses into `is_pm_one` and the dynamics at N=1369 | pattern matrix |
| run.json code_identity to the figures | a changed network core must not silently redraw stale results | code identity hash |
| stored-pattern matrix to pinv Gram | a rank-deficient set has no projection inverse | pattern matrix |
| recall.csv to the figures and report | a Hamming curve on a mismatched grid would misrepresent the comparison | measured recall data |
| result files to the deliverable | an unsourced or overclaimed number in the report | measured numbers |
| deliverable edits to the rule markers | an edit between the markers would silently break the pre-registration | protocol text |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-05-01 | Tampering | hopfield.c read_params (rule/subset) | low | mitigate | strict per-model key validation rejects unknown/missing/wrong-type keys; rule accepts only hebb or pinv — confirmed in 05-01-SUMMARY (hopfield.c dispatches rule="hebb"\|"pinv", aborts with clear message on unknown rule; tested in test_main.c) | closed |
| T-05-02 | Denial of Service | scripts/qr.py PNG read | low | mitigate | asserts mode L, shape 37x37, values in {0,255}; raises QrError and writes nothing on violation — verified by analysis/tests/test_qr.py's atomicity-of-refusal test (bad-gray/bad-shape PNG raises QrError, writes neither CSV nor meta) | closed |
| T-05-03 | Denial of Service | hopfield_pinv Gram inversion | medium | mitigate | Gauss-Jordan with partial pivoting; sub-tolerance pivot returns 0 and the model aborts rather than dividing by ~0 — confirmed in 05-01-SUMMARY, exercised by neuron/tests/test_main.c (1282 checks, 0 failed) | closed |
| T-05-04 | Repudiation | protocol/PNG tampering after results | high | mitigate | rule_digest over marker text + rule commit + five PNG sha256; rule_identity refuses if any guarded file changed after the rule commit — confirmed in 05-02-SUMMARY, exercised by downstream drivers (05-03/05-04/05-05 all call rule_identity first) | closed |
| T-05-05 | Tampering | guard bypass (running before commit) | medium | mitigate | downstream drivers call rule_identity first, exit non-zero unless the commit is in place; the decision checkpoint is blocking-human, never auto-approved — confirmed: this phase's own 05-02 checkpoint was presented to and approved by the user, never auto-approved | closed |
| T-05-06 | Tampering | qr_pm1.csv fed to the C binary | low | mitigate | `is_pm_one` (neuron/models/hopfield.c:61, called at line 265) aborts on any value other than -1/1 before processing; driver loads the same CSV the guard hashed | closed |
| T-05-07 | Denial of Service | trace/weights memory at N=1369 | medium | mitigate | trace_trials bounded `0..trials` (hopfield.c:122-123), TRACE_ROWS_MAX=1000000 cap (hopfield.c:30); W is ~15MB of doubles within NEURONS_MAX | closed |
| T-05-08 | Tampering | Hamming baseline grid/tie-break | low | mitigate | baseline reuses frozen NOISE_LEVELS/TRIALS and `k=lround(level*1369)`; ties resolve to lowest index — confirmed tested in 05-04-SUMMARY (test_hamming_classify_breaks_an_exact_tie_by_the_lowest_index) | closed |
| T-05-09 | Repudiation | deliverable overclaiming (decode/ROI) | medium | mitigate | every number traces to a result file; decoding-not-verified statement required and checked (D-10) — confirmed in 05-05-SUMMARY (Reed-Solomon decoding explicitly declared unverified, no ROI claim) | closed |
| T-05-10 | Tampering | deliverable edit touching the markers | medium | mitigate | marker-count and guard-identity checks fail if protocol text between markers changed — confirmed in 05-05-SUMMARY (MARKERS_INTACT, GUARD_STILL_PASSES verify checks both passed) | closed |
| T-05-SC | Tampering | npm/pip/cargo installs | high | mitigate | no new packages introduced across all 6 plans (Pillow, numpy, matplotlib already pinned in analysis/requirements.txt); no install task in any plan, so no [ASSUMED]/[SUS] package — confirmed unchanged `analysis/requirements.txt` in every SUMMARY | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above `high` (workflow.security_block_on) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

No accepted risks.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-25 | 11 | 11 | 0 | gsd-execute-phase orchestrator (L1 short-circuit: register authored at plan time, asvs_level=1, all mitigations verified against SUMMARY evidence and direct code inspection — no auditor spawn needed) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log (none)
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-25
