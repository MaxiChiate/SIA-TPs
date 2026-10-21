---
phase: 02-kohonen-som
plan: 01
subsystem: neuron
tags: [som, kohonen, c, strict-config, qe, te, occupancy, asan, ubsan]

requires:
  - phase: 02-kohonen-som
    provides: "plan 02-03 rule commit ea7a0b1 (rule text, som_select.py, stage-1 series), made before any trained SOM"
provides:
  - "neuron/models/kohonen.c: Kohonen SOM in C (sample init with reshuffle on wrap, shuffled epochs, exponential eta and radius decay, step or gaussian neighborhood)"
  - "Seven required Kohonen config keys (grid_k, neighborhood, radius0, radius_final, eta0, eta_final, epochs) with range checks before any allocation"
  - "Run files: prototypes.csv, assignments.csv (+bmu2), occupancy.csv, trace.csv, metrics.json with 19 keys (qe, te, occupancy summary)"
  - "kohonen_decay, kohonen_radius, kohonen_neighbor_weight exported in models.h and pinned by the C test kohonen training"
affects: [02-02, 02-04, 02-05, 02-06]

actuals:
  tokens: 7000
  tasks: 2
  commits: 2
plan_head_before: d29f20f9be7a8b36500e61d1230cc27be85eb10a
plan_head_after: ffec07323289f21243e4742f0f12f493c72e125d
commits: 2

tech-stack:
  added: []
  patterns:
    - "measure() shared by the final metrics and every trace row, so the last trace row equals the final qe/te"
    - "Config values range-checked in read_params before any allocation; KeySpec only checks types"

key-files:
  created:
    - neuron/models/kohonen.c
  modified:
    - neuron/io/config.c
    - neuron/config.json.kohonen.example
    - neuron/tests/test_main.c
    - neuron/models/models.h
    - neuron/README.md

key-decisions:
  - "Step neighborhood uses d2 <= R^2 + 1e-12 (D-01): R = 1 reaches the four adjacent cells and not the diagonals"
  - "Radius is clamped to radius_final (fmax) so pow() undershoot cannot push the last steps below the floor"
  - "TE counts a diagonal winner/runner-up pair as an error: adjacency is |dr| + |dc| == 1"
  - "k^2 > n is allowed (D-07): pick_prototypes reshuffles at every wrap of i % n, so repeated starting prototypes are intended and nothing reads past the sample array"

requirements-completed: [SOM-01, SOM-02]

coverage:
  - id: D1
    description: "Example config trains a sample-initialised 4 x 4 map on the 50 audited creators and writes qe, te and occupancy summary to metrics.json and one hits row per neuron (summing to 50) to occupancy.csv"
    requirement: SOM-01
    verification:
      - kind: other
        ref: "Task 1 SOM_RUN_OK command (two same-seed runs diff -r identical, 19 metrics, n_neurons 16, 16 occupancy rows summing to 50)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Smoke series over grid_k 2, 3, 4 gives 9 ok rows with qe, te and empty_fraction summary columns"
    requirement: SOM-02
    verification:
      - kind: other
        ref: "Task 1 SMOKE_OK command (analysis/sweep.py analysis/series_smoke_kohonen.json)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Seven keys required and typed; out-of-range or missing values exit non-zero naming the key"
    requirement: SOM-01
    verification:
      - kind: unit
        ref: "neuron/tests/test_main.c#test_kohonen_training (11 rejection cases) and #test_config_strict_validation"
        status: pass
      - kind: other
        ref: "Task 2 SOM_STRICT_OK command (hex, eta0 1.0, step radius_final 0.5, missing epochs, grid_k 1)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Step kernel at R = 1 updates four neighbors and not diagonals; gaussian sigma never 0; decay hits start and end; trace.csv runs from epoch 0 (eta0, radius0) to the last epoch (eta_final, radius_final)"
    requirement: SOM-01
    verification:
      - kind: unit
        ref: "neuron/tests/test_main.c#test_kohonen_training"
        status: pass
      - kind: other
        ref: "Task 2 TRACE_OK command (261 rows on the real data, first row 0,0.5,2, last row 260,0.01,1)"
        status: pass
    human_judgment: false
  - id: D5
    description: "grid_k up to 32 runs, including more neurons than samples, without reading past the sample array"
    requirement: SOM-01
    verification:
      - kind: other
        ref: "make -C neuron debug (ASan + UBSan, k = 3 on the 6-row fixture) printed DEBUG_OK; Task 2 K8_OK (k = 8 on 50 rows, 64 occupancy rows summing to 50)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Agreement of the C qe, te and occupancy with an independent numpy recomputation"
    requirement: SOM-02
    verification: []
    human_judgment: true
    rationale: "Deliberately moved to plan 02-02 Task 1 (numpy cross-check); not verified in this plan"

duration: 4 min
completed: 2026-10-21
status: complete
---

# Phase 2 Plan 01: Kohonen SOM in C Summary

**Hand-written Kohonen SOM in C (sample init, shuffled epochs, exponential eta and radius decay, step or gaussian neighborhood) with seven strict config keys, QE/TE/occupancy in metrics.json, occupancy.csv and a per-epoch trace.csv, pinned by a C test that also passes under ASan and UBSan.**

## Performance

- **Duration:** about 4 min (17:39:57Z to 17:43:21Z)
- **Tasks:** 2 (Task 1 tracer, Task 2 auto)
- **Files:** 1 created (renamed from the stub), 5 modified

## Accomplishments

- **Task 1 (tracer).** Precondition held: the three rule files were tracked and clean, and the rule commit `ea7a0b1` is an ancestor of the commit that creates `kohonen.c` (`ORDER_OK`). `kohonen_stub.c` was `git mv`ed to `kohonen.c`; `KOHONEN_KEYS` now has the seven required rows; `read_params` checks `grid_k` (2..32, no dependency on n), `neighborhood`, `epochs` (1..100000) and the sample count before any allocation. The example config (k = 4, step, R 2 to 1, eta 0.5 to 0.01, 260 epochs) trains a map on the real 50 creators; two same-seed runs are `diff -r` identical; the smoke series gives 9 ok rows with `qe`, `te`, `empty_fraction` columns. Tracer verified end-to-end before expanding.
- **Task 2.** `read_params` also checks `radius0 >= 1`, `radius_final` (`>= 1` for step, `> 0` for gaussian, `<= radius0`), `0 < eta0 < 1` and `0 < eta_final <= eta0`. `trace.csv` has epoch 0 plus one row per epoch (261 rows for the example; last row is epoch 260, eta 0.01, radius 1). The three helpers are exported in `models.h`. `test_kohonen_training` covers the kernels, the decay, k^2 > n (9 neurons on 6 rows), the trace schedule, the gaussian same-seed case and 11 rejected configs. `neuron/README.md` documents the seven keys, the four output files and the 19 metrics.
- **Verification run:** `make -C neuron test-c` 118 checks, 0 failed (4 ok lines); `make -C neuron debug` clean under ASan and UBSan; `pytest analysis/tests` 19 passed; k = 8 on the 50 creators writes 64 occupancy rows summing to 50.

## Task Commits

1. **Task 1:** `47d5424` feat(02-01): train a Kohonen SOM in C with seven strict config keys
2. **Task 2:** `ffec073` feat(02-01): validate schedule values, trace the training and pin both kernels with C tests

## Deviations from Plan

None - plan executed exactly as written.

**Total deviations:** 0.

## Issues Encountered

None. `.venv` and `datos/prepared/` already existed, so the Environment step was a no-op.

## Known Stubs

None. The Oja and Hopfield models are still Phase 1 stubs, but they are outside this plan's files.

## Threat Flags

None. The surface this plan adds (grid_k, epochs, radii and rates deciding sizes and divisions) is covered by T-02-01, T-02-02 and T-02-03; the mitigations are in place (range checks before allocation, `order[i % n]` with reshuffle, radius clamp, `occupied > 0` guard).

## Handoff to later plans

- 02-02 Task 1 owns the independent numpy recomputation of qe, te and occupancy against these run files, plus `analysis/som.py` and the `analysis/README.md` smoke-series row. The numpy agreement is NOT verified here.
- Run-file contract: `assignments.csv` is `sample,bmu,row,col,distance,bmu2`; `occupancy.csv` is `neuron,row,col,hits` (neuron = row * k + col); `trace.csv` is `epoch,eta,radius,qe,te`; `metrics.json` keys in order are `model, seed, n_samples, n_features, grid_k, n_neurons, neighborhood, epochs, radius0, radius_final, eta0, eta_final, qe, te, occupied_neurons, empty_fraction, mean_hits_occupied, max_hits, singleton_neurons`. The stub's `mean_bmu_distance` is gone (qe replaces it).
- The rule files of plan 02-03 were not touched, and no value from the example run, the smoke series or the k = 8 run was used to edit them (D-10).

## Self-Check: PASSED

- FOUND: `neuron/models/kohonen.c`, `neuron/io/config.c`, `neuron/config.json.kohonen.example`, `neuron/tests/test_main.c`, `neuron/models/models.h`, `neuron/README.md`
- FOUND commits `47d5424` and `ffec073` (ancestors of HEAD); `git rev-list --count d29f20f..HEAD` = 2
- `git ls-files neuron/models/kohonen_stub.c` prints nothing; ORDER_OK printed for the plan-level D-10 ancestry check
