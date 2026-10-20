---
phase: 01-fundaci-n-auditor-a-de-datos-y-pca
plan: 01
subsystem: infra
tags: [c11, make, cjson, splitmix64, config-validation, run-directory, oja-stub]

requires: []
provides:
  - "neuron/build/neuron: single binary that dispatches by the config's model key (oja registered)"
  - "Run contract results/{timestamp}_{model}_seed{N}/ with byte-copied config.json, flat metrics.json and model CSVs, byte-identical for the same seed"
  - "Strict config layer: KeySpec tables (COMMON_KEYS plus one table per model) and typed getters with dotted keys"
  - "Numeric CSV with header loader (Matrix) used by every model runner"
  - "cJSON v1.7.19 vendored with sha256 provenance"
affects: [01-03 sweep.py, 01-05 kohonen and hopfield stubs, 01-07 C tests and debug target, phases 2-5]

actuals:
  tokens: 8900      # chars/4 over the project files written (35417 chars); the 4k vendored cJSON lines are excluded
  tasks: 2
  commits: 2
plan_head_before: 89a4aba5b39c2e640854e8d9987446d4ff7b7c5c
plan_head_after: d5ac9d1fc0efea525e5bd475a8ffdb48244d1fff

tech-stack:
  added: ["cJSON v1.7.19 (vendored, MIT)"]
  patterns:
    - "One Rng from the seed created in main and passed to the runner; no libc generator"
    - "Table-driven config validation: a new key in a later phase is one KeySpec row"
    - "Timestamp only in the run directory name; no file holds a time value or an absolute path"
    - "Vendored code compiled with its own VENDOR_CFLAGS, project code with -Wall -Wextra -Wpedantic"

key-files:
  created:
    - TP4/neuron/Makefile
    - TP4/neuron/.gitignore
    - TP4/neuron/main.c
    - TP4/neuron/rng.c
    - TP4/neuron/rng.h
    - TP4/neuron/io/config.c
    - TP4/neuron/io/config.h
    - TP4/neuron/io/matrix.c
    - TP4/neuron/io/matrix.h
    - TP4/neuron/io/results.c
    - TP4/neuron/io/results.h
    - TP4/neuron/models/models.c
    - TP4/neuron/models/models.h
    - TP4/neuron/models/oja_stub.c
    - TP4/neuron/config.json.oja.example
    - TP4/neuron/tests/fixtures/zscore_small.csv
    - TP4/neuron/vendor/cjson/cJSON.c
    - TP4/neuron/vendor/cjson/cJSON.h
    - TP4/neuron/vendor/cjson/LICENSE
    - TP4/neuron/vendor/cjson/VERSION
  modified: []

key-decisions:
  - "D-05 deviation: Makefile and results.c are copied and adapted, not verbatim (see Deviations); rng.c/h are byte copies"
  - "model_names() lists the registered models separated by comma and space; config.c keeps its own registry of key tables, which must stay in the same order as the runner table in models/models.c"
  - "Failed runs leave their (partial) results directory behind; the directory is created before the runner starts"

patterns-established:
  - "Runner signature int run_<model>(const Config *, Rng *, const Results *), 1 on success, 0 after printing the reason"
  - "Error messages are '<config path>: <problem>' on stderr and a non-zero exit"
  - "Run duration goes to stderr only; stdout is exactly 'results -> <dir>'"

requirements-completed: [INFRA-01, INFRA-02]

coverage:
  - id: D1
    description: "make builds neuron/build/neuron warning-free under -std=c11 -Wall -Wextra -Wpedantic -O2 with cJSON compiled with its own flags"
    requirement: INFRA-01
    verification:
      - kind: other
        ref: "make -C neuron clean all, stderr contains no 'warning:'"
        status: pass
    human_judgment: false
  - id: D2
    description: "oja config produces results/{timestamp}_oja_seed1/ with config.json, metrics.json, index.csv, weights.csv; two runs are byte-identical (diff -r)"
    requirement: INFRA-02
    verification:
      - kind: other
        ref: "plan 01-01 Task 1 second automated block (TRACER_OK), re-run after Task 2 (TRACER_STILL_OK)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Unknown, duplicate, missing and wrong-typed keys, a negative seed, a top-level array and an unknown model each exit non-zero with the file and key named"
    requirement: INFRA-01
    verification:
      - kind: other
        ref: "plan 01-01 Task 2 first automated block (STRICT_OK)"
        status: pass
    human_judgment: false

duration: ~20min (start time was not captured)
completed: 2026-10-20
status: complete
---

# Phase 1 Plan 01: C core tracer and strict config Summary

**One `neuron` binary reads a strictly validated JSON config (vendored cJSON v1.7.19), runs the oja stub from the splitmix64 Rng and writes a byte-reproducible `results/{timestamp}_oja_seed{N}/` directory with config copy, flat `metrics.json` and CSVs.**

## Performance

- **Duration:** about 20 min (start time was not captured)
- **Completed:** 2026-10-20
- **Tasks:** 2 of 2 (Task 1 tracer, Task 2 strict config)
- **Files:** 20 created, 0 modified (cJSON.c, cJSON.h and LICENSE downloaded, rng.c and rng.h copied byte for byte)

## Accomplishments

- Tracer proven end to end on the oja path: `./build/neuron config.json.oja.example` prints exactly one stdout line `results -> results/2026-..._oja_seed1`, and `diff -r` between two runs prints nothing (the second run lands in a different directory because the timestamp is in the name; contents are identical). The copied `config.json` is byte-identical to the example and no file contains the absolute neuron path.
- Strict config (D-02): `config_validate_object` rejects unknown, duplicate, missing and wrong-typed keys, recurses into `KEY_OBJECT`, and the merged common plus model table is bounded by `CONFIG_KEYS_MAX`. Typed getters (`config_get_int|number|string|number_array`) reach nested objects with dotted keys. Messages observed:
  `unknown key "bogus"`, `duplicate key "seed"`, `key "seed" must be an integer`, `seed must be >= 0`, `missing key "seed"`, `the top level must be an object`, `unknown model "som" (available: oja)`.
- Getters, nested validation and array bounds were exercised with a throwaway harness under ASan and UBSan (not committed; the C test runner is plan 01-07). The oja run itself also passed ASan and UBSan.
- `matrix_load` keeps a last line without a trailing newline (the fixture is written that way on purpose), checks the column count of every row, `strtod` end pointers and `isfinite`, and guards the element-count overflow when growing.

## Task Commits

1. **Task 1: oja tracer from config.json to a reproducible run directory** - `7e21770` (feat)
2. **Task 2: strict table-driven config, per-model key tables, typed getters** - `d5ac9d1` (feat)

The tracer gate (early integration checkpoint) was run in interactive end-of-phase mode with an automated-only verify: the end-to-end verify was re-run after Task 1 and again after Task 2, and passed both times, so no human checkpoint was raised.

## Deviations from Plan

### Recorded deviation from locked decision D-05 ("se copia tal cual")

As the plan instructs, recorded here citing D-05. `rng.c` and `rng.h` are byte copies of TP3 (checked with `cmp`). `neuron/Makefile` and `neuron/io/results.c` are copied and adapted instead, because a verbatim copy cannot satisfy the other locked decisions:

- **Makefile:** TP3 compiles every source with one `CFLAGS` carrying `-O3`, `-march=native` and three float-reordering flags (CLAUDE.md forbids the reordering flags in TP4 so that C and numpy results stay comparable), has no per-file flags (D-01 requires cJSON compiled without `-Wextra`/`-Wpedantic`) and globs `activation/` and `optimizer/`. Kept verbatim: variable layout, wildcard `SOURCES`, object and dependency rules, `-MMD -MP`, `-include $(DEPS)`, make 3.81 syntax.
- **results.c:** TP3 names the folder `{timestamp}_{activation}` and writes and reads MLP weights, predictions, epochs and snapshots. D-04 requires `{timestamp}_{model}_seed{N}`. Kept verbatim: the `_POSIX_C_SOURCE` line, `make_dir`, `make_run_dir`, `open_in_run_dir`, `copy_file`. Small hardening added on top: `snprintf` truncation of the file path and `fwrite` failures are errors.

Amending D-05 to "copiar y adaptar" is a user decision; CONTEXT.md already carries the amended wording for this and for 01-03.

### Auto-fixed issues

None. The plan was executed as written; no Rule 1-3 fixes were needed.

## Notes for later plans

- **01-07 `make debug`:** compiling `vendor/cjson/cJSON.c` with `-fsanitize=address,undefined` makes clang emit 6 `-Wdeprecated-declarations` warnings for `sprintf` (they do not appear in the normal `-O2` build; checked: `-fsanitize` is what triggers them). The debug target should keep cJSON on its vendor flags plus `-Wno-deprecated-declarations`, or the warning-free criterion fails there.
- **01-05:** a model must be added in two places that have to stay in the same order: the `MODELS` table in `neuron/models/models.c` and the `MODEL_KEYS` registry in `neuron/io/config.c`. The `available:` list printed by `config.c` and the one from `model_names()` both come from these tables.
- **Sweeps (01-03):** a run that fails after `results_create` leaves a partial run directory with only `config.json`. `sweep.py` should treat a missing `metrics.json` as a failed run.
- `input` is resolved relative to the directory the binary runs from (`neuron/` for `make run`).

## Known Stubs

- `neuron/models/oja_stub.c` is an intentional stub required by D-03 (random unit vector projection, no learning). Phase 3 replaces the body with Oja's rule; the signature, config keys table (`OJA_KEYS`, empty for now) and output files are the contract it keeps.

## Threat Surface

No new surface beyond the plan's threat model. Mitigations applied: config larger than `CONFIG_FILE_MAX` rejected before parsing and `cJSON_Delete` on every failure path (T-01-01); model and input lengths checked, never truncated, key table bounded, `snprintf` results checked for the run directory (T-01-02); `getline`, exact column counts, `strtod` end pointer, `isfinite` and overflow check in `matrix_load` (T-01-03); run directory built only from the timestamp, a model name restricted to letters, digits, `_`, `.`, `-` (and not starting with a dot) and the numeric seed (T-01-04); no absolute paths or timestamps inside run files, verified with a grep for the absolute neuron path (T-01-05); cJSON downloaded only from the `v1.7.19` tag over https with sha256 per file in `neuron/vendor/cjson/VERSION` (T-01-SC).

## Self-Check: PASSED

- All 20 files listed in `key-files.created` exist in the commit (`git show --stat` of both commits).
- Commits `7e21770` and `d5ac9d1` exist on `worktree-agent-a4fb3a236b9afdbb9`; `git rev-list --count 89a4aba..HEAD` printed 2 before this SUMMARY commit.
- `cmp` of `rng.c` and `rng.h` against TP3 exits 0; `grep -cE '[0-9a-f]{64}' neuron/vendor/cjson/VERSION` prints 3; the `rand(`/`srand(`/`drand48(` grep over `main.c`, `io` and `models` finds nothing.
