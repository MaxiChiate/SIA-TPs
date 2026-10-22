---
phase: 03-oja-y-decisiones-de-campa-a
plan: 01
subsystem: neuron
tags: [c, oja, hebbian, online-learning, sanitizers]

requires:
  - phase: 01-datos-y-pca
    provides: "creadores_zscore.csv (50 x 26), the PCA sign convention (largest |coefficient| positive), the C core (config, matrix, results, rng) and the sweep loop"
  - phase: 02-kohonen
    provides: "kohonen_decay exported in models.h, the read_params / epoch-loop / trace-writer shape reused by oja.c"
provides:
  - "neuron/models/oja.c: Oja's rule for one neuron (run_oja, exported oja_orient)"
  - "Three strict Oja config keys (eta0, eta_final, epochs) with range checks and the eta0 x max|x|^2 < 1 stability bound"
  - "Run files weights.csv (oriented unit w), index.csv, trace.csv (per-epoch w_norm, delta_w, weights) and a 16-key metrics.json"
  - "Fifth C test 'oja training' passing plain and under ASan/UBSan"
affects: [03-02, 03-03, 03-04, 03-05, 03-06]

actuals:
  tokens: 9500
  tasks: 2
  commits: 0

tech-stack:
  added: []
  patterns:
    - "Oja model mirrors kohonen.c: read_params validation before allocation, one Rng drives start vector and shuffles, trace buffer of epochs + 1 rows written by results_write_table"
    - "Orientation (D-02) done in C by a tie-safe largest-|value| rule exported for the tests"

key-files:
  created:
    - neuron/models/oja.c
  modified:
    - neuron/io/config.c
    - neuron/models/models.h
    - neuron/config.json.oja.example
    - neuron/tests/test_main.c
    - neuron/README.md
    - analysis/series_smoke_oja.json
  deleted:
    - neuron/models/oja_stub.c

key-decisions:
  - "Example config eta0 0.001 / eta_final 0.0001 / epochs 500 worked as planned: pivot average_caption_words for seeds 1, 2 and 3, eta0 x max|x|^2 = 0.0573, so no parameter change was needed"
  - "oja_orient stays a pure void-array helper returning 1 when it negated; the pivot index is recomputed from the oriented w by a static largest_abs, valid because negation keeps every |w_j|"
  - "Value checks (eta0, eta_final, stability bound) were added after the red test, so the fixture-convergence checks were green before them and the four rejection checks were the red ones"

patterns-established:
  - "Stability product eta0 x max|x|^2 is reported as a metric (eta0_max_x2) and enforced < 1 before training"

requirements-completed: [OJA-01]

coverage:
  - id: D1
    description: "Oja's rule in C on the 50 x 26 z-scored creators: unit w oriented to a positive largest coefficient (pivot average_caption_words), 50-row index.csv, 501-row trace.csv and the 16-key metrics.json, byte-identical for the same seed"
    requirement: OJA-01
    verification:
      - kind: integration
        ref: "cd neuron && ./build/neuron config.json.oja.example (twice, diff -r) -> OJA_RUN_OK"
        status: pass
    human_judgment: false
  - id: D2
    description: "Strict Oja config: missing/mistyped eta0, eta_final, epochs and out-of-range values (eta0 1.0, eta_final > eta0, epochs 0 or 100001, eta0 x max|x|^2 >= 1) exit non-zero naming the key"
    requirement: OJA-01
    verification:
      - kind: unit
        ref: "neuron/tests/test_main.c#oja training (d) and config strict validation"
        status: pass
      - kind: integration
        ref: "five bad configs through ./build/neuron -> OJA_STRICT_OK"
        status: pass
    human_judgment: false
  - id: D3
    description: "Trained, oriented w on the 6-row fixture matches the oriented top eigenvector within 5e-3 per component, plain and under AddressSanitizer + UndefinedBehaviorSanitizer; oja_orient handles negative pivot, positive pivot and tie"
    requirement: OJA-01
    verification:
      - kind: unit
        ref: "neuron/tests/test_main.c#oja training (a)-(c) via make -C neuron test-c and make -C neuron debug"
        status: pass
    human_judgment: false
  - id: D4
    description: "Smoke series over 3 seeds yields 3 ok rows with w_norm_final, delta_w_final and eta0_max_x2 columns in summary.csv"
    requirement: OJA-01
    verification:
      - kind: integration
        ref: "analysis/sweep.py analysis/series_smoke_oja.json -> SMOKE_OK"
        status: pass
    human_judgment: false

duration: 10min
completed: 2026-10-22
status: complete

plan_head_before: 04c972612465931baf409c5c32f2dd68e1f8c13a
plan_head_after: 04c972612465931baf409c5c32f2dd68e1f8c13a
---

# Phase 3 Plan 01: Oja's rule in C Summary

**Oja's rule for one neuron in C on the 26 audited z-scored variables (exponential eta 0.001 to 0.0001, 500 shuffled epochs), with in-C renormalization and the PCA sign convention, a per-epoch weight trace, strict value validation including the eta0 x max|x|^2 < 1 stability bound, and a fifth sanitizer-clean C test**

## Performance

- **Duration:** about 10 min
- **Started:** 2026-10-22T13:35:00Z (approximate; the start time was not captured)
- **Completed:** 2026-10-22T13:39:00Z
- **Tasks:** 2
- **Files modified:** 8 (1 created by rename, 1 deleted, 6 modified)

## Accomplishments

- `neuron/models/oja.c` (renamed from the stub) trains one neuron with `w += eta y (x - y w)`, start vector uniform in [0, 1) scaled to length 1, shuffled epochs, `kohonen_decay` schedule over `epochs x n` steps, a divergence guard per epoch, then renormalizes and orients w in C (`oja_orient`, exported).
- The example config on the real data gives pivot `average_caption_words` (weight 0.2521, `sign_flipped` 1), `w_norm_final` 1.00032, `delta_w_final` 1.4e-4, `eta0_max_x2` 0.0573, `index_std` 3.683; two same-seed runs are `diff -r` identical.
- `trace.csv` holds epoch 0 (eta 0.001, w_norm 1, delta_w 0) plus 500 epoch rows with the 26 weights, ready for the convergence evidence of plan 03-03.
- Smoke series (seeds 1-3) gives 3 ok rows, pivot `average_caption_words` in all three, with the new metric columns in summary.csv.
- C tests: five, 176 checks, 0 failed, both `make test-c` and `make debug` (ASan + UBSan).

## Task Commits

No task commits, by design. The plan's Commits note and the user's standing preference (project memory) say the user commits by hand at the end of the phase and that this plan must not touch the git index; `git diff --cached --name-only` prints nothing. The working tree holds the changes unstaged (the stub removal appears as ` D neuron/models/oja_stub.c` plus untracked `neuron/models/oja.c`).

1. **Task 1: end-to-end Oja (tracer)** - uncommitted (feat)
2. **Task 2: validation, oja_orient export, C test, README** - uncommitted (feat/test/docs)

**Plan metadata:** not committed (same reason).

## Files Created/Modified

- `neuron/models/oja.c` - Oja training, orientation, projection, trace/weights/index/metrics writers (renamed from `oja_stub.c`)
- `neuron/io/config.c` - `OJA_KEYS` with `eta0`, `eta_final`, `epochs`
- `neuron/models/models.h` - real description of `run_oja`; `oja_orient` declared under "Oja helpers"
- `neuron/config.json.oja.example` - eta0 0.001, eta_final 0.0001, epochs 500
- `neuron/tests/test_main.c` - Oja literals updated to the strict keys, three negative Oja key cases, `oja_run_accepts`, `test_oja_training` registered fifth
- `neuron/README.md` - Oja keys, three CSVs, 16 metrics keys, five C tests (Spanish)
- `analysis/series_smoke_oja.json` - comment now names Oja's rule

## Decisions Made

- The planned parameters needed no adjustment: pivot is `average_caption_words` for seeds 1, 2 and 3, so Step 10's fallback (lower eta_final / raise epochs) was not used and the orientation rule was never touched.
- `oja_orient` returns only the flip flag; the pivot index for `metrics.json` is recomputed from the oriented w with the shared static `largest_abs` (same index, since negation preserves every |w_j|).
- `same_seed_same_bytes("oja", ..., "trace.csv")` uses the trace as the seed-dependent file because its row 0 holds the seeded start vector.

## Deviations from Plan

None - plan executed exactly as written. The two procedural points that differ from the orchestrator's generic "commit each task" instruction follow the plan itself (see Task Commits), not a deviation from it. In Task 2's red run, only the four value-rejection checks failed (eta0 1.0, eta_final above eta0, eta_final 0, eta0 0.4); the fixture-convergence checks passed before the validation was added because Task 1's training was already correct.

## Issues Encountered

- `.venv` and `datos/prepared/` were missing at start; `make prepare` created them (the four pinned packages of `analysis/requirements.txt`, nothing else installed).

## Known Stubs

None in this plan's files. `hopfield_stub.c` remains a stub by roadmap (Phases 4-5).

## Threat Flags

None - no new network, auth or file-access surface beyond the plan's threat register (T-03-01 epochs bound before allocation, T-03-02 range and stability checks plus divergence guard, T-03-03 header array freed and sanitizer run, all implemented).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plans 03-02 (campaign rule) and 03-03 (Oja vs PC1, convergence, 10-seed dispersion) can read `weights.csv`, `index.csv` and `trace.csv` from any run of `neuron/config.json.oja.example`.
- Note for 03-03: PC1's two largest coefficients are close (0.2521 vs -0.2493); the C pivot was `average_caption_words` in all three smoke seeds here, and 03-03 reports it for the 10-seed series.
- Working-tree changes are uncommitted; the user commits at the end of the phase. The stub rename is a plain filesystem move, so `git add` of both `neuron/models/oja.c` and the deletion of `oja_stub.c` is needed at commit time.

---
*Phase: 03-oja-y-decisiones-de-campa-a*
*Completed: 2026-10-22*

## Self-Check: PASSED

- `neuron/models/oja.c` exists, `neuron/models/oja_stub.c` absent
- `make -C neuron clean all` without diagnostics; `make -C neuron test-c` and `make -C neuron debug`: 176 checks, 0 failed
- OJA_RUN_OK, SMOKE_OK, OJA_STRICT_OK, DOCS_OK all printed; `git diff --cached --name-only` empty
