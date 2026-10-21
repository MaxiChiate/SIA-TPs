---
phase: 02-kohonen-som
plan: 02
subsystem: analysis
tags: [som, numpy, cross-check, spearman, stability, leave-one-out, tdd]

requires:
  - phase: 02-kohonen-som
    provides: "02-01 Kohonen C core and run-file contract; 02-03 pre-registered rule (stability and figure-seed terms)"
provides:
  - "analysis/som.py: SomRun, read_run, distances, metrics_from_prototypes, nearest_distance, run_binary"
  - "Tie-aware Spearman, grid_distance_vector, seed_spearman_matrix, stability (value, nan_pairs), medoid_seed"
  - "analysis/som_loo.py: write_folds, run_loo, main (QE leave-one-out CLI writing loo.csv, loo_by_seed.csv, folds/)"
  - "Numpy proof that the C qe, te, hits, bmu, bmu2 and occupancy summary are correct for both kernels (k^2 > n included)"
affects: [02-04, 02-05, 02-06]

actuals:
  tokens: 6700
  tasks: 3
  commits: 6
plan_head_before: d641dbdfe6b9cb15e43812409199d8edc11371c5
plan_head_after: 31c2e15c2b6faed332e86af28a0521b6c96781a8
commits: 6

tech-stack:
  added: []
  patterns:
    - "Independent recomputation: metrics_from_prototypes uses a stable argsort so the lowest index wins ties like nearest() in C"
    - "One TemporaryDirectory per LOO training under out_dir/tmp; jobs collected through pool.map with per-job exception capture, first failure reported in (variant, seed, fold) order"

key-files:
  created:
    - analysis/som.py
    - analysis/som_loo.py
    - analysis/tests/test_som.py
    - analysis/tests/test_som_stats.py
  modified:
    - analysis/README.md

key-decisions:
  - "read_run also checks sample numbering and neuron = row * k + col in assignments.csv and occupancy.csv, not only the headers"
  - "run_loo deletes a stale loo.csv / loo_by_seed.csv before training, so a failed run can never leave an old file that looks current"
  - "The failure message reports the first failure by (variant, seed, fold) order, not by completion order, so it is deterministic"

requirements-completed: [SOM-02, SOM-03]

coverage:
  - id: D1
    description: "numpy recomputation of qe, te, hits, both BMU columns and the occupancy summary equals the C output within 1e-12 for step k=8 and gaussian k=4"
    requirement: SOM-02
    verification:
      - kind: unit
        ref: "analysis/tests/test_som.py#test_recompute_metrics_from_run (2 passed)"
        status: pass
    human_judgment: false
  - id: D2
    description: "read_run raises ValueError naming the file when a header or the neuron numbering breaks the C contract"
    requirement: SOM-02
    verification:
      - kind: unit
        ref: "analysis/tests/test_som.py#test_read_run_rejects_broken_contract"
        status: pass
    human_judgment: false
  - id: D3
    description: "Tie-aware Spearman, orientation- and order-invariant stability with the NaN rule, and the figure-seed medoid"
    requirement: SOM-03
    verification:
      - kind: unit
        ref: "analysis/tests/test_som_stats.py (7 passed: ranks, spearman sqrt(0.9), grid distance, rotation/reflection, creator permutation, all-NaN, medoid)"
        status: pass
    human_judgment: false
  - id: D4
    description: "QE leave-one-out: 12 rows on the fixture, byte-identical reruns, exact fold bytes, no leftovers, failure stops without loo.csv"
    requirement: SOM-03
    verification:
      - kind: unit
        ref: "analysis/tests/test_som_stats.py#test_loo_fixture, #test_loo_folds_bytes, #test_loo_failure_stops (3 passed)"
        status: pass
      - kind: other
        ref: "make test: 118 C checks, 0 failed; 33 pytest passed"
        status: pass
    human_judgment: false

duration: 8min
completed: 2026-10-21
status: complete
---

# Phase 2 Plan 02: Numpy proof of the SOM measures, seed stability and QE-LOO Summary

**analysis/som.py reads Kohonen run directories and reproduces qe, te, hits, both BMU columns and the occupancy summary of the C binary within 1e-12 for both kernels, adds a tie-aware Spearman seed stability with the committed NaN rule and the stability medoid, and analysis/som_loo.py runs QE leave-one-out with one temporary directory per training.**

## Performance

- **Duration:** about 8 min (plan started 17:39Z; finished 17:48Z)
- **Tasks:** 3 (all TDD)
- **Files:** 4 created, 1 modified

## Accomplishments

- **Task 1 (SOM-02 cross-check).** `metrics_from_prototypes` recomputes qe, te (diagonal winner/runner-up pairs count as errors, D-04), hits, bmu, bmu2 and the occupancy summary from the prototypes and the z matrix. For a step run (k = 8, 64 neurons on 50 creators, R 4 to 1) and a gaussian run (k = 4, R 2 to 0.5) every value equals the C output within 1e-12 and the BMU arrays match exactly; the last `trace.csv` row equals the final qe and te. This closes the numpy agreement that 02-01 deferred (its coverage item D6). `read_run` rejects a changed `occupancy.csv` header and a swapped `prototypes.csv` line, naming the file. The `series_smoke_kohonen` row of `analysis/README.md` now describes the trained SOM and its new summary columns.
- **Task 2 (D-13).** `average_ranks`, `spearman_ties`, `grid_distance_vector`, `seed_spearman_matrix`, `stability` and `medoid_seed` implement the committed **Estabilidad.** and **Semilla de las figuras.** terms (Euclidean grid distance, NaN pairs dropped and counted, all NaN gives 0.0, smallest seed on medoid ties). Rotation by 90 degrees and reflection leave stability at 1.0, a permutation of the creators leaves it unchanged within 1e-12, and `spearman_ties([1,2,2,3],[1,3,2,4])` equals sqrt(0.9).
- **Task 3 (D-09).** `som_loo.py` trains one map per held-out creator per (variant, seed) in its own `TemporaryDirectory`, measures the held-out creator's nearest-prototype distance in Python, averages folds per seed into `loo_by_seed.csv` and leaves seed-to-config aggregation to `som_select.aggregate`. Fixture: 12 rows for 2 seeds x 6 folds, byte-identical `loo.csv` across worker counts 2 and 3, no `tmp/` or `results/` left. A CLI smoke on the fixture printed `loo -> .../loo.csv`.

## Task Commits

1. Task 1 RED `1f3d415` test: numpy cross-check tests (collection fails, `som` did not exist)
2. Task 1 GREEN `88a579b` feat: `som.py` reader and recomputation, README row
3. Task 2 RED `034d60c` test: 7 stability-family tests (all failed with missing attributes)
4. Task 2 GREEN `7fd35a3` feat: stability functions
5. Task 3 RED `93d22f1` test: 3 LOO tests (collection error, `som_loo` did not exist)
6. Task 3 GREEN `31c2e15` feat: LOO driver

## TDD Gate Compliance

- **RED** commits `1f3d415`, `034d60c`, `93d22f1`. Tasks 1 and 3 failed at collection with `ModuleNotFoundError` for the module under test; Task 2 failed 7 of 7 with `AttributeError` for the missing functions. `workflow.tdd_mode` is not enabled in `.planning/config.json`, so `gsd_run check tdd-red-evidence` was not required; a collection error would be classified INVALID_RED by it, but the failure is the intended one (the unit under test did not yet exist) and every test went green afterwards with no change to its assertions.
- **GREEN** commits `88a579b`, `7fd35a3`, `31c2e15`.
- **REFACTOR:** none.

## Deviations from Plan

### Auto-fixed Issues

None. Additions beyond the plan, none of which change a planned behavior:

- Two extra tests in `test_som.py` (`test_read_run_rejects_broken_contract`, `test_nearest_distance_lowest_index_on_ties`) to cover the plan's `read_run` truth, which had no named test. The plan's `-k recompute` count stays at 2.
- A second assertion in `test_stability_all_nan` (one NaN pair among three seeds is dropped and counted) and a third case in `test_medoid_seed` (a row without finite entries never wins).

**Total deviations:** 0 (rule-based). During Task 2 a BSD `sed -i` call failed on macOS and the `import math` line was added with the Edit tool instead; no content was lost.

## Issues Encountered

None blocking. The real stage-1 series was deliberately not run (plan 02-04 does that behind the guard); the pre-registered rule files (`deliverables/02-kohonen.md`, `analysis/som_select.py`, `analysis/series_som_stage1.json`) were not touched.

## Known Stubs

None.

## Threat Flags

None. `run_binary` uses an argument list with `cwd` and no shell (T-02-05), temporary directories are named by `tempfile` and removed (T-02-06), and `read_run` raises on header or numbering mismatches (T-02-04). `grep shell=True analysis/som_loo.py` finds nothing.

## Handoff to later plans

- 02-04 can call `python analysis/som_loo.py analysis/series_som_stage1.json` (7 000 trainings, minutes) and feed `loo_by_seed.csv` (`label, variant, seed, n_folds, qe_loo`) to `som_select.aggregate`, which expects `label, seed, qe_loo`.
- `som.stability(bmus_by_seed, k)` returns `(value, nan_pairs)`, the shape `stability_by_label[label]` expects; `som.seed_spearman_matrix` plus `som.medoid_seed(matrix, seeds)` give the pre-declared figure seed.
- `som.read_run(run_dir).bmu` provides the per-seed BMU arrays; stability needs them in a fixed creator order, which `assignments.csv` guarantees.

## Self-Check: PASSED

- FOUND: `analysis/som.py`, `analysis/som_loo.py`, `analysis/tests/test_som.py`, `analysis/tests/test_som_stats.py`, `analysis/README.md` row
- FOUND commits `1f3d415`, `88a579b`, `034d60c`, `7fd35a3`, `93d22f1`, `31c2e15` (ancestors of HEAD); `git rev-list --count d641dbd..HEAD` = 6
- `pytest analysis/tests/test_som.py -k recompute`: 2 passed; `pytest analysis/tests/test_som_stats.py`: 10 passed; `make test`: 118 checks, 0 failed, 33 passed
