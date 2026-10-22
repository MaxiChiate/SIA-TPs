---
phase: 03-oja-y-decisiones-de-campa-a
plan: 06
subsystem: analysis
tags: [python, numpy, maintenance, drift-check, synthetic-creator, deliverable]
status: complete

requires:
  - phase: 03-oja-y-decisiones-de-campa-a
    provides: "plan 03-03: analysis/results/oja/weights.csv and index.csv (saved w, D-02 sign); plan 03-05: sections 1-5 of the deliverable and the committed rule (a6212e89)"
  - phase: 02-kohonen-som
    provides: "selection.json and the k5-step figure run of make som-stage1 (BMU on the 5 x 5 map, 50 training BMU distances)"
  - phase: 01-fundaci-n-auditor-a-de-datos-y-pca
    provides: "scripts/map_creator.py and datos/prepared/creadores_zscore.meta.json (saved scaler)"
provides:
  - "analysis/maintenance_demo.py and make maintenance: a flagged synthetic creator (SYN001, @sintetico_demo) built from the column medians with the five exact relations restored, mapped with scripts/map_creator.py, placed on the Phase 2 map, given its Oja index with the saved w and checked for drift (D-18, D-19)"
  - "analysis/results/maintenance/ (generated): synthetic_creator.csv, synthetic_z.csv, demo.json (synthetic true), report_demo.md"
  - "Sections 6 (mantenimiento) and 7 (cómo reproducir) of deliverables/03-oja-campanas.md, after section 5 and with the rule block untouched"
  - "analysis/README.md rows for series_oja, the updated series_smoke_oja and the make oja, campaigns and maintenance targets"
affects: [phase-06-report]

actuals:
  tokens: 5700
  tasks: 2
  commits: 3

plan_head_before: 545f55ba74cf2e5cc11974af83c1e5ee39d92ade
plan_head_after: 69e2ca4ed27396c73345eacdef6a5573ec0e70a7
commits: 3

tech-stack:
  added: []
  patterns:
    - "The demo maps through the CLI (subprocess with sys.executable and an argument list, no shell, check=True) and cross-checks the result against transform_new_creator at 1e-12"
    - "Drift flags only when the BMU distance is strictly above the largest training distance; the percentile is the fraction of training distances at or below the new one"

key-files:
  created:
    - analysis/maintenance_demo.py
    - analysis/tests/test_maintenance_demo.py
  modified:
    - Makefile
    - deliverables/03-oja-campanas.md
    - analysis/README.md

key-decisions:
  - "The synthetic creator is made of medians, so it sits closer to a prototype (BMU (3, 1), distance 1,329) than every training creator (training QE mean 2,724, maximum 3,651, p95 3,545) and the verdict is: no hace falta re-entrenar. The section says this shows the mechanism, not that real creators of a new month would pass"
  - "Rank convention: the synthetic index (0,249) is ranked against the 50 training indices without being added, so it takes place 24 of 1..51"
  - "report_demo.md says '0,0 % of the training distances are at or below the creator's' instead of 'percentile 0,0', so the reading is not inverted"

patterns-established:
  - "Generated report lines are pasted verbatim into the deliverable by a script and checked line by line with grep -qxF (as in plan 03-05)"

requirements-completed: [CAMP-03]

coverage:
  - id: D1
    description: "make maintenance builds SYN001 / @sintetico_demo from the medians with the five exact relations restored, maps it with scripts/map_creator.py and the saved .meta.json, and writes synthetic true in demo.json and the word sintético in every report line about it; a rerun is byte-identical"
    requirement: CAMP-03
    verification:
      - kind: unit
        ref: "analysis/tests/test_maintenance_demo.py#test_synthetic_creator_relations, test_map_creator_cli_matches_transform"
        status: pass
      - kind: integration
        ref: "make maintenance, a rerun with identical shasum of the four files, then the Task 1 verify script -> DEMO_OK"
        status: pass
    human_judgment: false
  - id: D2
    description: "BMU on the k5-step figure run, Oja index with the saved w (z . w reproduces the index.csv value of INF001 to 1e-15) and a drift check that flags retraining only above the largest training BMU distance, with QE mean, maximum, p95 and the creator's percentile reported"
    requirement: CAMP-03
    verification:
      - kind: unit
        ref: "analysis/tests/test_maintenance_demo.py#test_drift_check_threshold, test_bmu_and_index_rank"
        status: pass
      - kind: integration
        ref: "DEMO_OK: bmu inside the 5 x 5 grid, boolean drift, finite index, oja_rank equal to 1 + the number of the 50 index.csv values above it"
        status: pass
    human_judgment: false
  - id: D3
    description: "Section 6 answers the four maintenance questions concretely (campaña nueva, creadores nuevos, variables nuevas, actualización mensual) plus the demo with every report_demo.md bullet verbatim; section 7 lists the eight commands; analysis/README.md lists series_oja and the three targets"
    requirement: CAMP-03
    verification:
      - kind: integration
        ref: "Task 2 verify script -> SECTIONS67_OK (headings 1 to 7 in order, five bold labels, every report bullet present, eight make commands)"
        status: pass
    human_judgment: true
    rationale: "Whether each answer is concrete and actionable is a judgment over meaning; the human-check of Task 2 (read sections 6 and 7 and run the section 7 commands in order) is pending"
---

# Phase 3 Plan 6: Maintenance demo, sections 6 and 7 Summary

**`make maintenance` takes a flagged synthetic creator (median profile) through the saved scaler, the k5-step map, the saved Oja w and a drift check (no retraining: its BMU distance 1,329 is under the training maximum 3,651), and sections 6 and 7 answer the four maintenance questions and the reproduction steps.**

## Performance

- **Duration:** about 25 min (start not timestamped; estimated from the commit times)
- **Tasks:** 2 (a TDD tracer and a documentation task)
- **Files:** 5 (2 created, 3 modified)

## Accomplishments

- `analysis/maintenance_demo.py`: `synthetic_creator`, `write_raw_csv`, `map_with_cli`, `bmu`, `drift_check`, `index_rank`, `main`. It refuses naming `make oja`, `make som-stage1` or `make prepare` when an input is missing, checks the Phase 2 rule through `som_stage.require_same_rule`, and cross-checks the CLI mapping against `transform_new_creator` at 1e-12.
- Result of the demo: BMU (fila 3, col 1) on the 5 x 5 map (seed 4 of the figure run), distance 1,329; training QE 2,724, maximum 3,651, p95 3,545; verdict no hace falta re-entrenar; Oja index 0,249, place 24 among the 50.
- Section 6 with the five bold labels, the five report lines verbatim and a sentence on what the verdict means; section 7 with the eight commands in order. The text between `<!-- regla:inicio -->` and `<!-- regla:fin -->` is unchanged (its sha256 compared before and after the edit) and `rule_identity()` still returns rule commit a6212e89.
- Four new tests (`test_maintenance_demo.py`); the whole Python suite is 83 passed and the C suite is `176 checks, 0 failed`.

## Task Commits

1. Task 1 RED: `d083111` test(03-06): failing tests for the synthetic creator, drift check, CLI mapping and BMU rank
2. Task 1 GREEN: `ff03466` feat(03-06): `analysis/maintenance_demo.py` and the `maintenance` Makefile target
3. Task 2: `69e2ca4` docs(03-06): sections 6 and 7 and the analysis/README.md rows

No refactor commit (nothing to change after GREEN).

## Deviations from Plan

### Commit policy (instruction from the orchestrator, not a rule deviation)

The plan text says not to stage or commit; the orchestrator's explicit instruction overrode it, so every task was committed with explicit paths and the `Co-Authored-By` trailer. `.planning/milestone.lock` was never staged.

### Auto-fixed Issues

**1. [Rule 1 - Wording] Percentile line of report_demo.md**
- **Found during:** Task 1 verification
- **Issue:** "queda en el percentil 0,0 %" reads as "lowest in the distribution of distances" only after thought, and the creator is below every training distance, which is easy to misread as an outlier
- **Fix:** the line now says "el 0,0 % de esas distancias es menor o igual que la del creador sintético"
- **Files modified:** analysis/maintenance_demo.py
- **Commit:** ff03466 (the line was fixed before the GREEN commit)

**Total deviations:** 1 wording fix. **Impact:** none on numbers or checks.

## Issues Encountered

- `docs/Archivo SIATP 42026.pdf` page 4 could not be read (no `pdftoppm`); the maintenance questions were taken from D-18 of 03-CONTEXT.md, which restates them, and from Pitfall 20.
- `make test` in neuron/ still breaks on the space in the repository path (known, pre-existing, out of scope). The same suites were run by hand: `.venv/bin/python -m pytest analysis/tests -q` gives 83 passed and the C tests give 176 checks, 0 failed.

## Known Stubs

None. The synthetic creator is deliberate and flagged (SYN001, @sintetico_demo, `synthetic: true`), not a stub.

## Threat Flags

None. T-03-13 (spoofing of a real creator) is mitigated by the id, the name, `synthetic: true` and the word sintético in every report line, and the files exist only under analysis/results/maintenance/. T-03-14 (command injection) is mitigated by an argument list, `sys.executable`, a fixed script path and no shell. No package was installed.

## Next Phase Readiness

Phase 3 has all six plans executed; verification and phase completion belong to the orchestrator. Pending human check: read sections 6 and 7 and run the section 7 commands in order.

## Self-Check: PASSED

- FOUND: analysis/maintenance_demo.py, analysis/tests/test_maintenance_demo.py, analysis/results/maintenance/demo.json
- FOUND commits: d083111, ff03466, 69e2ca4
- 83 pytest tests passed, the C suite reports 176 checks, 0 failed, `rule_identity()` returns a6212e89cdc654021cfda02d9d16237c8c21c332
