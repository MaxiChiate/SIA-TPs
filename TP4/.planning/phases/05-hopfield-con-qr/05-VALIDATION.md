---
phase: "05"
slug: "hopfield-con-qr"
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-25"
---

# Phase 05 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Reconstructed from PLAN/SUMMARY artifacts after execution (State B).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (Python, `analysis/`) + custom C test harness (`neuron/tests/test_main.c`) |
| **Config file** | none — plain pytest discovery under `analysis/tests/`; `neuron/Makefile` drives the C harness |
| **Quick run command** | `python3 -m pytest analysis/tests/test_hopfield_qr.py analysis/tests/test_hopfield.py analysis/tests/test_qr.py -q` |
| **Full suite command** | `make -C neuron test-c && python3 -m pytest analysis/tests/ -q` |
| **Estimated runtime** | ~5 s (Python unit tests) + ~15 s (C harness); the real end-to-end runs (`make hopfield-qr`, `make hopfield-qr-figures`) take 3–80 min and are integration-level, not part of the quick/full unit suites |

---

## Sampling Rate

- **After every task commit:** `python3 -m pytest analysis/tests/test_hopfield_qr.py analysis/tests/test_hopfield.py analysis/tests/test_qr.py -q`
- **After every plan wave:** `make -C neuron test-c && python3 -m pytest analysis/tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~20 s (unit suites); end-to-end QR runs are run once per plan, not per task

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-T1 | 01 | 1 | HOP-06 | Pinv rule rejects singular Gram instead of inventing weights | unit+integration | `make -C neuron test-c` | ✅ | ✅ green |
| 05-01-T2 | 01 | 1 | HOP-06 | numpy twin matches C core in float64, no int64 truncation | unit | `python3 -m pytest analysis/tests/test_hopfield.py -q` | ✅ | ✅ green |
| 05-02-T1 | 02 | 2 | HOP-05 | Protocol frozen one-way; checkpoint blocks until human approval | checkpoint (manual) | N/A — human sign-off, not automatable | N/A | ✅ approved |
| 05-02-T2 | 02 | 2 | HOP-05 | `rule_identity` guard refuses a changed protocol/PNG set | unit | `python3 -m pytest analysis/tests/test_hopfield_qr.py -k guard -q` | ✅ | ✅ green |
| 05-03-T1 | 03 | 3 | HOP-04, HOP-05 | Guarded Hebb driver refuses on stale rule identity | unit | `python3 -m pytest analysis/tests/test_hopfield_qr.py -q` | ✅ | ✅ green |
| 05-03-T2 | 03 | 3 | HOP-05 | Tracer figures refuse to render on changed rule/network code | integration | `make hopfield-qr && make hopfield-qr-figures` | ✅ | ✅ green (measured: Hebb 0% exact recovery at every noise level) |
| 05-03-T3 | 03 | 3 | HOP-04, HOP-05 | Pure-numpy helpers cross-check the C-driven recall | unit | `python3 -m pytest analysis/tests/test_hopfield_qr.py -q` | ✅ | ✅ green |
| 05-04-T1 | 04 | 4 | HOP-06 | Pinv series + Hamming 1-NN baseline on the same frozen grid | integration | `make hopfield-qr` | ✅ | ✅ green (measured: pinv 100% exact recovery at noise 0) |
| 05-04-T2 | 04 | 4 | HOP-06 | Three-rule figures, per-step energy with separate scales | integration | `make hopfield-qr-figures` | ✅ | ✅ green |
| 05-04-T3 | 04 | 4 | HOP-06 | Pinv exact-fixed-point stability + Hamming baseline unit tests | unit | `python3 -m pytest analysis/tests/test_hopfield_qr.py -q` | ✅ | ✅ green |
| 05-05-T1 | 05 | 5 | HOP-07 | Majority attractor + shift-sensitivity evidence, never forced | unit+integration | `make hopfield-qr-limits` + `python3 -m pytest analysis/tests/test_hopfield_qr.py -q` | ✅ | ✅ green |
| 05-05-T2 | 05 | 5 | HOP-07 | Shift triptych / majority figures refuse on stale code identity | integration | `make hopfield-qr-limits` | ✅ | ✅ green |
| 05-05-T3 | 05 | 5 | HOP-07 | Deliverable sections filled with real measured numbers only | doc | manual review (markers intact, `rule_identity` still passes) | ✅ | ✅ green |
| 05-06-T1 | 06 | 1 | HOP-04 | PNG→pm-one conversion refuses non-{0,255} or wrong-shape input | unit | `python3 -m pytest analysis/tests/test_qr.py -q` | ✅ | ✅ green (gap filled post-execution, see Validation Audit below) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure (pytest + the project's C test harness) covered all phase requirements; no new framework install was needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Pre-registration approval (hypothesis, noise grid, verdict thresholds) | HOP-05 | One-way human sign-off is the point of the gate (D-01) — automating it would defeat the pre-registration | Re-run `/gsd-execute-phase 05` only if the protocol must change; any edit after results exist invalidates the "fixed beforehand" claim |
| Reed-Solomon decoding claim (declared unverified, D-10) | HOP-07 | Decoding was explicitly out of scope for this phase; the deliverable states this honestly rather than testing an unimplemented decoder | None — documented limitation, not a testable behavior |

---

## Validation Sign-Off

- [x] All tasks have automated verify or a documented manual-only reason
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none needed)
- [x] No watch-mode flags
- [x] Feedback latency < 20s (unit suites)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** 2026-10-25

---

## Validation Audit

| Gaps found | Resolved | Escalated |
|---|---|---|
| 1 | 1 | 0 |

Gap: `scripts/qr.py` / `scripts/prepare_qr.py` (HOP-04, plan 05-06) had no dedicated pytest file — only verified once via `make qr`'s inline checks. Resolved by the gsd-nyquist-auditor: `analysis/tests/test_qr.py` (26 tests, mirroring `test_letters.py`'s coverage — shape, purity, polarity, row-major order, determinism, atomicity of refusal, meta/provenance). Mutation-tested against 5 defect classes (polarity swap, thresholding instead of purity check, transposition, missing purity check, missing shape check) — all detected. No implementation bugs found.
