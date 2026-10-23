---
phase: "4"
slug: "hopfield-n-cleo-y-letras"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-23"
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | C: `check()`/`check_close()` in `neuron/tests/test_main.c` (ASan/UBSan via `make -C neuron debug`); Python: pytest |
| **Config file** | `neuron/Makefile` (`test-c`, `debug`, `test`); `analysis/tests/conftest.py` |
| **Quick run command** | `make -C neuron test-c` (C) or the touched `analysis/tests/test_*.py` (Python) |
| **Full suite command** | `make test && make -C neuron debug` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `make -C neuron test-c` or the relevant pytest file
- **After every plan wave:** Run `make test && make -C neuron debug`
- **Before `/gsd-verify-work`:** Full suite green plus the guarded driver (`make hopfield-letters` or equivalent) on a clean tree
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

Filled by the planner from the research map (`04-RESEARCH.md` §Validation Architecture). Requirement → test map:

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| HOP-01 | W symmetric, zero diagonal, integral; course example | C unit | `make -C neuron test-c` | ❌ W0 | ⬜ pending |
| HOP-01 | Tie h_i = 0 keeps state | C unit | `make -C neuron test-c` | ❌ W0 | ⬜ pending |
| HOP-01 | Async energy non-increasing (1e-9), incremental E = from-scratch E | C unit | `make -C neuron test-c` | ❌ W0 | ⬜ pending |
| HOP-01 | Sync 2-cycle detected; async converges from same start | C unit | `make -C neuron test-c` | ❌ W0 | ⬜ pending |
| HOP-01 | Classifier stored/inverse/mixture/other | C unit | `make -C neuron test-c` | ❌ W0 | ⬜ pending |
| HOP-01 | Strict config (unknown/missing/mistyped/other-task keys, bad subset) | C unit | `make -C neuron test-c` | ❌ W0 | ⬜ pending |
| HOP-01 | Same seed → identical bytes | C integration | `make -C neuron test-c` | ✅ extend | ⬜ pending |
| HOP-01 | No memory errors | sanitizer | `make -C neuron debug` | ✅ | ⬜ pending |
| HOP-02 | Alphabet shape, no duplicates/inverse pairs, J = statement | pytest | `.venv/bin/python -m pytest analysis/tests/test_letters.py -q` | ❌ W0 | ⬜ pending |
| HOP-02 | Selection rule + tie-breaks + guard | pytest | `.venv/bin/python -m pytest analysis/tests/test_hopfield_select.py -q` | ❌ W0 | ⬜ pending |
| HOP-02 | Recall cross-check (numpy) and capacity 14950 rows | pytest | `.venv/bin/python -m pytest analysis/tests/test_hopfield.py -q` | ❌ W0 | ⬜ pending |
| HOP-03 | Spurious trial exists, reclassified identically by numpy | pytest | `.venv/bin/python -m pytest analysis/tests/test_hopfield.py -q` | ❌ W0 | ⬜ pending |
| All | `diff -r` reproducibility | pytest | `.venv/bin/python -m pytest analysis/tests/test_hopfield.py -k reproducible -q` | ❌ W0 | ⬜ pending |
| All | Figures build | pytest smoke | `.venv/bin/python -m pytest analysis/tests/test_hopfield_figures.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `neuron/models/hopfield_core.[ch]` + `HOPFIELD_KEYS` rows
- [ ] New tests in `neuron/tests/test_main.c` + `neuron/tests/fixtures/patterns_mix.csv` (synthetic, independent of the real alphabet)
- [ ] `analysis/tests/test_letters.py`, `test_hopfield_select.py`, `test_hopfield.py`, `test_hopfield_figures.py`
- [ ] Update existing hopfield cases in `test_main.c`, `config.json.hopfield.example`, `series_smoke_hopfield.json`
- [ ] `make venv` (no `TP4/.venv` in this checkout)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Alphabet bitmaps read as the intended letters | HOP-02 | Visual judgment | Open the letters figure and check each glyph |
| Rule text and tie-breaks approved before commit | HOP-02 | Pre-registration decision (D-04) | Checkpoint: user approves rule text |
| Written interpretation (orthogonality, capacity vs 0.138N, spurious state) | HOP-02, HOP-03 | Prose quality | Read the deliverable sections |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
