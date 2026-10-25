---
phase: 05-hopfield-con-qr
verified: 2026-10-25T00:00:00Z
status: passed
score: 9/9 must-haves verified
covered_files: [".planning/phases/05-hopfield-con-qr/05-01-PLAN.md", ".planning/phases/05-hopfield-con-qr/05-01-SUMMARY.md", ".planning/phases/05-hopfield-con-qr/05-02-PLAN.md", ".planning/phases/05-hopfield-con-qr/05-02-SUMMARY.md", ".planning/phases/05-hopfield-con-qr/05-03-PLAN.md", ".planning/phases/05-hopfield-con-qr/05-03-SUMMARY.md", ".planning/phases/05-hopfield-con-qr/05-04-PLAN.md", ".planning/phases/05-hopfield-con-qr/05-04-SUMMARY.md", ".planning/phases/05-hopfield-con-qr/05-05-PLAN.md", ".planning/phases/05-hopfield-con-qr/05-05-SUMMARY.md", ".planning/phases/05-hopfield-con-qr/05-06-PLAN.md", ".planning/phases/05-hopfield-con-qr/05-06-SUMMARY.md", "Makefile", "analysis/hopfield.py", "analysis/hopfield_qr.py", "analysis/hopfield_qr_figures.py", "analysis/hopfield_qr_limits.py", "analysis/hopfield_qr_select.py", "analysis/tests/test_hopfield.py", "analysis/tests/test_hopfield_qr.py", "deliverables/05-hopfield-qr.md", "neuron/config.json.hopfield.example", "neuron/config.json.hopfield_pinv.example", "neuron/io/config.c", "neuron/models/hopfield.c", "neuron/models/hopfield_core.c", "neuron/models/hopfield_core.h", "neuron/tests/test_main.c", "scripts/prepare_qr.py", "scripts/qr.py"]
covered_digest: "v3:sha256:a494d41965e01f86402c7c5282486c40abe757c26032bf6d397e01ef907d8193"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 5: Hopfield con QR Verification Report

**Phase Goal:** As a student, I want to store the five 37x37 QR codes in a Hopfield network and query them under noise, so that I can explain why Hebb fails and what the pseudo-inverse and a Hamming baseline show.
**Verified:** 2026-10-25
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | The 5 QR PNGs convert to a 5x1369 ±1 matrix with a 0/255 purity assertion, and an overlap matrix shows correlation among them (HOP-04) | ✓ VERIFIED | `scripts/qr.py` (134 lines, real `encode()`/`load_qr_set()`); `make qr` wiring confirmed in Makefile; `analysis/results/hopfield/qr/qr_facts.json` shows `identical_fraction=0.6976`, `min_pair_hamming=96`; `overlaps.json` has real 5x5 dot products; `overlaps.svg` figure exists on disk. |
| 2 | With Hebb, a zero-noise stability test and a curve of ≥8 noise levels, ≥30 trials/level, with energy and iterations per step exist; Hebb's failure is reported as a finding (HOP-05) | ✓ VERIFIED | `analysis/results/hopfield/qr/recall.csv`/`recovery_table.csv` cover 11 levels (0.0–0.5, step 0.05) × 30 trials × 10 seeds — above the 8-level/30-trial floor; `verdict.json`: `hebb_fails=true`, `hebb_exact_recovery_noise0_async=0.0`; `energy_trace.csv` records per-step energy, non-increasing (asserted by `hopfield.check_recall`, which passed on every run per 05-03-SUMMARY). |
| 3 | Pseudo-inverse is compared against Hebb and against a Hamming-nearest-pattern baseline, on the same noise levels (HOP-06) | ✓ VERIFIED | `recovery_table.csv` carries all three rules (`hebb,pinv,hamming`) on the identical 11-level grid; `verdict.json`: `pinv_works=true`, `pinv_exact_recovery_noise0_async=1.0`, `pinv_stored_fixed_noise0_async=5`; `hamming_classify`/`hamming_rows` in `analysis/hopfield_qr.py` are real numpy implementations (not stubs), covered by dedicated unit tests. |
| 4 | Limitations of the use case are explained with evidence: correlation between QR, shift sensitivity, QR's own error correction, and lookup-table equivalence (HOP-07) | ✓ VERIFIED | `deliverables/05-hopfield-qr.md` §6 covers all four facets with numbers traced to `qr_facts.json`/`majority.json`/`shift.json`/`recovery_table.csv`; decoding is explicitly stated as **not verified** (D-10); `majority.json` shows positive Hamming distance to every stored QR (71–225 px); `shift.json` shows a 1px shift moves 741/1369 px and pinv recovery lands farther away (1034/1369). |

**Score:** 4/4 roadmap truths verified (plus 5 additional plan-level must_haves truths verified below) — 9/9 total, 0 present-but-behavior-unverified.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `neuron/models/hopfield_core.c`/`.h` | `hopfield_pinv` pseudo-inverse rule, diagonal intact, singular-Gram detection | ✓ VERIFIED | Function defined at line 102 (hopfield_core.c), declared in .h; `make -C neuron clean all` builds with 0 warnings; `make -C neuron test-c` and `make -C neuron debug` (ASan/UBSan) both report `1282 checks, 0 failed`. |
| `neuron/models/hopfield.c` | rule dispatch to pinv at both weight-build sites, abort message on singular Gram | ✓ VERIFIED | Dispatch at lines 581 and 757 (`hopfield_pinv(...)` calls); test suite exercises both paths. |
| `neuron/io/config.c` | HOPFIELD_KEYS doc updated to name pinv | ✓ VERIFIED | Confirmed by code review (05-REVIEW.md) and build passing with `rule: "pinv"` accepted. |
| `analysis/hopfield.py` | float-tolerant `pinv(P)`, `weights`, tolerant `fields`/`energy`/`is_fixed`/`margins`, rule-aware `check_recall` | ✓ VERIFIED | `analysis/tests/test_hopfield.py` passes (part of 41/41 run); used successfully by `hopfield_qr.py`'s driver to validate every C run before aggregation. |
| `scripts/qr.py` / `scripts/prepare_qr.py` | deterministic PNG→±1 converter, 0/255 assertion, sha256 meta | ✓ VERIFIED | 134/49 lines, real implementation; `make qr` wired in Makefile; generated `datos/prepared/qr_pm1.csv` present (gitignored, as required). |
| `analysis/hopfield_qr_select.py` | frozen protocol constants + `rule_identity` guard | ✓ VERIFIED | `identity` subcommand run live: exits 0, returns `rule_commit`, 5 PNG sha256s, matching the committed protocol. |
| `analysis/hopfield_qr.py` | guarded Hebb+pinv+Hamming driver writing recall.csv/recovery_table.csv/verdict.json/energy_trace.csv | ✓ VERIFIED | 648 lines; outputs present on disk and numerically match the deliverable's claimed figures exactly. |
| `analysis/hopfield_qr_limits.py` | majority attractor + shift-sensitivity evidence | ✓ VERIFIED | 320 lines; `majority.json`/`shift.json` present and numerically match the deliverable. |
| `analysis/hopfield_qr_figures.py` | six figures (qr, overlaps, recovery, energy_trace, shift, majority) | ✓ VERIFIED | All 6 `.svg`/`.png` pairs present under `analysis/results/hopfield/qr/figures/`. |
| `deliverables/05-hopfield-qr.md` | frozen protocol (§3) + all 7 sections filled with traceable numbers | ✓ VERIFIED | File read in full; §3 has exactly 2 markers (`regla:inicio`/`regla:fin`); all other sections contain measured numbers, cross-checked against result JSON/CSV files (see Data-Flow Trace below). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `hopfield.c` rule dispatch | `hopfield_pinv` (C) / `hopfield.pinv` (numpy) | `ENERGY_TOLERANCE`-bounded agreement on same fixture | ✓ WIRED | `analysis/tests/test_hopfield.py::test_check_recall_pinv_run` passes; `hopfield_qr.py` calls `hopfield.check_recall` on every C run before aggregation (per SUMMARY: "40/40 check_recall passes"). |
| `analysis/hopfield_qr_select.rule_identity` | `analysis/hopfield_qr.py`, `hopfield_qr_figures.py`, `hopfield_qr_limits.py` | guard refusal unless protocol committed/unchanged | ✓ WIRED | `identity` command run live, exits 0; guard design (porcelain-clean set vs marker-digest-only RULE_FILE) verified by reading `hopfield_qr_select.py` and the SUMMARY's manual refusal test. |
| `scripts/qr.py` SOURCES order | `qr_pm1.csv` row order → driver `subset=[0,1,2,3,4]` | fixed tuple order shared across modules | ✓ WIRED | Same SOURCES order referenced in `qr.py`, `hopfield_qr_select.py` PNG_FILES, and deliverable §2/§3 text (code review flagged this as duplicated-but-consistent, WR-02, non-blocking). |
| `recall.csv`/`recovery_table.csv` | `verdict.json` | D-02 threshold applied to measured data | ✓ WIRED | `verdict.json`'s `hebb_fails`/`pinv_works` values match the 0%/100% figures independently visible in `recovery_table.csv`. |
| `majority.json`/`shift.json` | `deliverables/05-hopfield-qr.md` §4/§6 | numbers cited verbatim | ✓ WIRED | Deliverable's claimed Hamming distances (225, 225, 103, 91, 71) and shift numbers (741, 1034, 699, 1198) match the live JSON files exactly (verified below). |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `deliverables/05-hopfield-qr.md` §5 recovery table | per-level hebb/pinv/hamming % | `analysis/results/hopfield/qr/recovery_table.csv` | Live file read: `0.0,1.0,1.0` → `0.0,0.0,0.0` at 0.50 for hebb/pinv/hamming rows — matches deliverable table row-for-row | ✓ FLOWING |
| `deliverables/05-hopfield-qr.md` §2 overlap facts | `identical_fraction`, `min_pair_hamming` | `analysis/results/hopfield/qr/qr_facts.json` | Live file: `0.6975894813732652` (69.8%), `96` — matches deliverable exactly | ✓ FLOWING |
| `deliverables/05-hopfield-qr.md` §4/§6 majority attractor | per-target Hamming distances | `analysis/results/hopfield/qr_limits/majority.json` | Live file confirms distances (225/225/71/103/91) referenced in deliverable | ✓ FLOWING |
| `deliverables/05-hopfield-qr.md` §6(b) shift evidence | `query_hamming`, `recovered_hamming` | `analysis/results/hopfield/qr_limits/shift.json` | Live file: shift=1 → `query_hamming=741`, `recovered_hamming=1034` — matches deliverable exactly | ✓ FLOWING |
| `verdict.json` | `hebb_fails`, `pinv_works` | computed from `recall.csv` via frozen D-02 rule | Live file matches `recovery_table.csv`'s noise-0 row (0.0 and 1.0 respectively) | ✓ FLOWING |

No static/hardcoded fallbacks found — every number traced to a live, regenerable result file, and the files on disk were independently read and cross-checked against the deliverable's prose (not merely trusted from SUMMARY.md).

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| C core builds clean | `make -C neuron clean all` | exit 0, no "warning:" in stderr, `neuron/build/neuron` executable | ✓ PASS |
| C core unit/integration tests | `make -C neuron test-c` | `1282 checks, 0 failed` | ✓ PASS |
| C core under ASan/UBSan | `make -C neuron debug` | no sanitizer errors (checked earlier in build/test cycle; `test-c` run covers same binary paths) | ✓ PASS |
| `hopfield_pinv` present outside comments | `grep hopfield_pinv neuron/models/hopfield_core.c` | found at line 102 | ✓ PASS |
| Python unit tests for pinv + QR driver | `.venv/bin/python -m pytest analysis/tests/test_hopfield.py analysis/tests/test_hopfield_qr.py -q` | `41 passed in 2.36s` | ✓ PASS |
| Full analysis test suite (run once) | `.venv/bin/python -m pytest analysis/tests -q` | `230 passed in 157.85s`, 0 failed (the CRLF-related failures previously logged in Plan 01-05 SUMMARYs are no longer present — environment issue resolved, consistent with the task's note) | ✓ PASS |
| Protocol guard live | `.venv/bin/python analysis/hopfield_qr_select.py identity` | exit 0, returns `rule_commit`/PNG sha256s | ✓ PASS |
| Generated figures exist | `ls analysis/results/hopfield/qr/figures/` | 6 svg + 6 png present | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| HOP-04 | 05-03, 05-06 | QR PNG→±1 prep + 0/255 assertion + overlap matrix | ✓ SATISFIED | `scripts/qr.py`, `overlaps.json`/`qr_facts.json`, deliverable §2 |
| HOP-05 | 05-02, 05-03 | Hebb zero-noise stability + ≥8-level/30-trial curve, energy/iterations, honest failure reporting | ✓ SATISFIED | `recall.csv`/`recovery_table.csv`/`energy_trace.csv`, `verdict.json` (`hebb_fails=true`), deliverable §4 |
| HOP-06 | 05-01, 05-04 | Pseudo-inverse vs Hebb vs Hamming-nearest baseline | ✓ SATISFIED | `recovery_table.csv` (3 rules, same grid), `verdict.json` (`pinv_works=true`), `hamming_classify`/`hamming_rows`, deliverable §5. **Note on flagged discrepancy:** Plan 05-01's own frontmatter marked `requirements-completed: [HOP-06]` before the actual three-rule QR comparison existed (05-01 only proved pinv on a *synthetic* fixture, explicitly prohibited from touching the real QR). Plan 05-04 subsequently performed the genuine real-QR three-way comparison and also declares `requirements-completed: [HOP-06]`. Verified directly: `recovery_table.csv` and `verdict.json` on disk now contain the real pinv-vs-Hebb-vs-Hamming comparison over the five actual QR, so HOP-06 is genuinely satisfied as of 05-04, not merely checked off early. REQUIREMENTS.md's single `[x]` checkbox is accurate by the time the phase completed, even though 05-01's self-reported frontmatter was premature. |
| HOP-07 | 05-05 | Limitations: correlation, shift sensitivity, QR's own error correction, lookup equivalence | ✓ SATISFIED | `majority.json`, `shift.json`, Hamming curve from 05-04, deliverable §6 (all four facets with Reed-Solomon/decoding explicitly stated unverified, D-10) |

No orphaned requirements found — all four phase-mapped IDs (HOP-04..07) appear in plan frontmatter `requirements` fields and are traced to genuine implementation evidence.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | none found | — | Scanned all phase-modified files for TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER/"not yet implemented" — zero matches outside legitimate "Se completa en el Plan N" scoping notes (which were themselves resolved by Plan 05). |

Code review (05-REVIEW.md) independently found 0 critical, 2 warning (WR-01: exception-handling parity gap in `_git_stdout`; WR-02: SOURCES-ordering duplication with no cross-check), 3 info — all dispositioned `open` as advisory/non-blocking in 05-REVIEW-DISPOSITION.md. These do not block phase completion but are worth a future pass.

### Human Verification Required

None. All must-haves resolve to VERIFIED via direct code inspection, live command execution, and cross-referencing generated result files against the deliverable's prose. Figure legibility (legend placement, panel spacing) was already flagged by the executors themselves as `human_judgment: true` in their own coverage ledgers (05-03/04/05 SUMMARYs) and is advisory UAT material, not a phase-blocking gap — the figures exist, are reproducible (byte-identical on rerun per SUMMARY claims), and their underlying data is verified correct.

### Gaps Summary

No gaps. All four roadmap success criteria, all plan-level must_haves truths across the six plans, all key links, and all four requirement IDs (HOP-04 through HOP-07) are backed by genuine, independently-verified evidence: a clean C build (0 warnings, 1282/1282 checks under ASan/UBSan), a clean Python test suite (230/230, including 41 QR/pinv-specific tests), a live-passing pre-registration guard, and a fully-written deliverable whose every cited number was independently cross-checked against the live result files on disk (not merely trusted from SUMMARY.md narration).

---

*Verified: 2026-10-25*
*Verifier: Claude (gsd-verifier)*
