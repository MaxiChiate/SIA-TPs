---
phase: "2"
slug: "kohonen-som"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-21"
validated: "2026-10-26"
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | C: `check()`/`check_close()` in `neuron/tests/test_main.c` (ASan/UBSan via `make -C neuron debug`); Python: pytest |
| **Config file** | `neuron/Makefile` (`test-c`, `debug`, `test`); `analysis/tests/conftest.py` |
| **Quick run command** | `make -C neuron test-c` (C) or the touched `analysis/tests/test_som*.py` (Python) |
| **Full suite command** | `make test && make -C neuron debug` |
| **Estimated runtime** | ~30 seconds (the six `test_som*.py` files alone: ~2,5 s) |

---

## Sampling Rate

- **After every task commit:** Run `make -C neuron test-c` or the relevant pytest file
- **After every plan wave:** Run `make test && make -C neuron debug`
- **Before `/gsd-verify-work`:** Full suite green plus `make som-figures` and `make som-profiles` byte-identical on rerun
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

Reconstructed from `02-RESEARCH.md` §Validation Architecture and the `<automated>` blocks of plans 02-01 to 02-06. Requirement → test map:

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| SOM-01 | Strict config: new keys missing / mistyped; values refused (`neighborhood`, `eta0 >= 1`, `eta_final > eta0`, `radius_final` per mode, `grid_k` bounds) | C unit | `make -C neuron test-c` (`config strict validation`, `kohonen training` §e) | ✅ | ✅ green |
| SOM-01 | Step R = 1 reaches the 4 neighbors and not the diagonals; gaussian weight `exp(-d²/2σ²)` | C unit | `make -C neuron test-c` (`kohonen training` §a) | ✅ | ✅ green |
| SOM-01 | eta and R decay from start to end values; `trace.csv` endpoints | C unit | `make -C neuron test-c` (`kohonen training` §b, §c) | ✅ | ✅ green |
| SOM-01 | k² > n (9 neurons, 6 samples) initializes without overflow; hits sum to n | C unit + sanitizer | `make -C neuron test-c` §c; `make -C neuron debug` | ✅ | ✅ green |
| SOM-01/02 | Same seed → identical bytes (step and gaussian); seed changes the run | C integration | `make -C neuron test-c` (`same seed, same bytes`, `kohonen training` §d) | ✅ | ✅ green |
| SOM-01 | No memory errors | sanitizer | `make -C neuron debug` | ✅ | ✅ green |
| SOM-02 | `metrics.json` qe / te / occupancy equal an independent numpy recomputation; occupancy matches assignments | pytest integration | `.venv/bin/python -m pytest analysis/tests/test_som.py -q` | ✅ | ✅ green |
| SOM-02 | Run reader rejects a broken output contract; BMU lowest index on ties | pytest | `.venv/bin/python -m pytest analysis/tests/test_som.py -q` | ✅ | ✅ green |
| SOM-03 | Tie-aware Spearman, average ranks, grid distance; stability invariant to rotation/reflection and creator order; all-NaN case; medoid seed | pytest | `.venv/bin/python -m pytest analysis/tests/test_som_stats.py -q` | ✅ | ✅ green |
| SOM-03 | QE leave-one-out: n folds on the fixture, byte-stable folds, a failed fold stops the driver | pytest | `.venv/bin/python -m pytest analysis/tests/test_som_stats.py -q -k loo` | ✅ | ✅ green |
| SOM-03 | `select_grid`: filter boundaries, lowest QE-LOO, tie band by stability, smaller k on equal stability, gaussian ignored, TE-only drop, no eligible grid | pytest | `.venv/bin/python -m pytest analysis/tests/test_som_select.py -q` | ✅ | ✅ green |
| SOM-03 | Rule pre-registration: rule digest between markers, git guard (untracked / modified / clean), stage-1 series shape, stage-2 one-at-a-time | pytest (tmp git repo) | `.venv/bin/python -m pytest analysis/tests/test_som_select.py -q -k "digest or guard or stage"` | ✅ | ✅ green |
| SOM-03 | Stage driver on the fixture; failure stops; stage-2 series written; same rule required; rule identity guards the selection code | pytest | `.venv/bin/python -m pytest analysis/tests/test_som_stage.py -q` | ✅ | ✅ green |
| SOM-04 | U-matrix on a hand-computed 2 × 2; adjacency pairs; main-planes rule; figures deterministic on rerun | pytest | `.venv/bin/python -m pytest analysis/tests/test_som_figures.py -q` | ✅ | ✅ green |
| SOM-05 | Region rule on synthetic grid; raw-unit profiles; R² on grid coordinates invariant to rotation/reflection; seeded permutation null; edge contrast; high-U edges in raw units | pytest | `.venv/bin/python -m pytest analysis/tests/test_som_profiles.py -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Observed on 2026-10-26: `make -C neuron test-c` → 1282 checks, 0 failed; `make -C neuron debug` → 1282 checks, 0 failed, no sanitizer reports; the six `test_som*.py` files → 42 passed.

---

## Wave 0 Requirements

- [x] Kohonen cases in `neuron/tests/test_main.c` (`kohonen training`, strict keys, `same_seed_same_bytes` for step and gaussian) + `neuron/tests/fixtures/zscore_small.csv`
- [x] `analysis/tests/test_som.py`, `test_som_stats.py`, `test_som_select.py`, `test_som_stage.py`, `test_som_figures.py`, `test_som_profiles.py`
- [x] `analysis/series_smoke_kohonen.json` for the end-to-end smoke series

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Rule terms approved before commit (pre-registration, commit `ea7a0b1`) | SOM-03 | Pre-registration decision (checkpoint 02-03 Task 1) | Checkpoint: user approved the rule text; guard is automated afterwards |
| Written interpretation: region profiles for the use case, PC1/PC2 contrast, what a high U-matrix distance means | SOM-05 | Prose quality | Read sections 5 and 6 of `deliverables/02-kohonen.md` |
| Figures read correctly (hit map, U-matrix, component planes) | SOM-04 | Visual judgment | Open `analysis/results/som/figures/*.png` |

Known open review findings (`02-REVIEW-DISPOSITION.md`, WR-01 to WR-04) are defects in edge cases, not uncovered requirements; WR-01 and IN-01 touch the pre-registered rule and stay open by decision (see `CLAUDE.md`, Pendientes).

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
