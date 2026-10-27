---
phase: 01-fundaci-n-auditor-a-de-datos-y-pca
plan: 03
subsystem: infra
tags: [python, stdlib, sweep, summary-csv, multi-seed, reproducibility]

requires:
  - phase: 01-01
    provides: "neuron/build/neuron binary, run contract (results -> dir, config.json + metrics.json), oja stub and tracked fixture"
provides:
  - "analysis/sweep.py: model-agnostic multi-seed series runner writing one summary.csv"
  - "Series file format (base_config, set, vary + values, variants, seeds, workers, dotted keys, underscore comments)"
  - "Sweep output layout analysis/results/{series}_{date}_{time}/ with series.json, plan.json, configs/, runs/, summary.csv"
  - "analysis/series_smoke_oja.json smoke series and analysis/README.md"
affects: [01-05 oja config pointing at prepared data, 01-07 kohonen and hopfield series, phases 2-5 hyperparameter and seed studies]

actuals:
  tokens: 5200      # chars/4 over the four project files written (20651 chars)
  tasks: 2
  commits: 2
plan_head_before: a6a346ff5d92a766d65f91ce9e26d7433c38f223
plan_head_after: 39142d656f433277aca995621476fa2dfed04a10

tech-stack:
  added: []
  patterns:
    - "Series runner: Variant x seed -> Task -> one subprocess per run (argument list, cwd = sweep dir), failures recorded as rows"
    - "Config paths stored relative to the sweep dir (os.path.relpath), config passed to the binary as configs/{run}.json, so no run file and no error message holds an absolute path"
    - "summary.csv columns: fixed run columns, then varied keys, then metrics.json keys; byte-identical across repeated sweeps"

key-files:
  created:
    - TP4/analysis/sweep.py
    - TP4/analysis/series_smoke_oja.json
    - TP4/analysis/.gitignore
    - TP4/analysis/README.md
  modified: []

key-decisions:
  - "D-05 deviation: sweep.py is copied and adapted from TP3, not a byte copy (see Deviations)"
  - "The binary receives the config path relative to the sweep dir (configs/{run}.json), not the absolute path the plan's text shows, so its error messages in summary.csv are reproducible and path-free"
  - "write_summary takes the varied keys as a third argument, because the column rule needs the varied-key order and rows alone do not carry it"
  - "After all runs, partial run directories left in the sweep's results/ (failed runs, no metrics.json) are deleted and the folder removed if empty; the reason lives in summary.csv and the config in configs/"

patterns-established:
  - "A missing metrics.json after a zero exit counts as a failed run (error: metrics.json missing)"
  - "Series runner exits 1 when any row is not ok but still writes summary.csv and prints summary -> path as the last stdout line"

requirements-completed: [INFRA-03]

coverage:
  - id: D1
    description: "sweep.py over series_smoke_oja.json writes summary.csv with 3 ok rows, header run,variant,label,seed,status,model,n_samples,n_features,w_norm,index_mean,index_std; two sweeps give cmp-identical summary.csv and diff -r-identical runs/, with no absolute path in runs/"
    requirement: INFRA-03
    verification:
      - kind: other
        ref: "plan 01-03 Task 1 automated block (SWEEP_OK)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A base config the binary rejects gives exit 1, summary.csv written with one error row per seed naming the rejected key, and no leftover results/ folder in the sweep dir"
    requirement: INFRA-03
    verification:
      - kind: other
        ref: "plan 01-03 Task 2 second automated block (FAILURE_PATH_OK, run against a scratchpad series and config)"
        status: pass
    human_judgment: false
  - id: D3
    description: "--dry-run prints 'series ...: 1 variants x 3 seeds = 3 runs' and creates nothing under analysis/results/"
    requirement: INFRA-03
    verification:
      - kind: other
        ref: "plan 01-03 Task 2 first automated block (DRYRUN_OK), results/ entry count unchanged before and after"
        status: pass
    human_judgment: false
  - id: D4
    description: "vary + values with a mix of working and failing variants records ok and error rows side by side with the varied key as a column; dotted override keys create nested objects"
    requirement: INFRA-03
    verification:
      - kind: other
        ref: "ad hoc series in the scratchpad (input varied between the fixture and a missing file; set key a.b rejected by the binary as unknown key a)"
        status: pass
    human_judgment: false

duration: ~15min (start time was not captured)
completed: 2026-10-20
status: complete
---

# Phase 1 Plan 03: Multi-seed series runner Summary

**`analysis/sweep.py` turns a series file (base config, optional `vary`/`variants`, seeds) into one reproducible `summary.csv` by running the single `neuron` binary once per variant and seed, recording failed runs as `error:` rows instead of aborting.**

## Performance

- **Duration:** about 15 min (start time was not captured)
- **Completed:** 2026-10-20
- **Tasks:** 2 of 2
- **Files:** 4 created, 0 modified

## Accomplishments

- INFRA-03 closed: `python3 analysis/sweep.py analysis/series_smoke_oja.json` builds the binary, runs 3 seeds in parallel and writes `summary.csv` with header `run,variant,label,seed,status,model,n_samples,n_features,w_norm,index_mean,index_std`. `seed` is not repeated even though `metrics.json` also holds it.
- Reproducibility (D-04): two consecutive sweeps give `cmp`-identical `summary.csv` and `diff -r`-identical `runs/`. The timestamp lives only in the sweep folder name (a second sweep in the same second gets `_2`). The config copy inside each run holds `"input": "../../../neuron/tests/fixtures/zscore_small.csv"`, never the absolute TP4 path (grep over `runs/` finds none).
- Failure path: a rejected config gives one `error: configs/{run}.json: unknown key "bogus"` row per seed, exit status 1, `summary.csv` still written, last stdout line still `summary -> path`. A mixed series (fixture plus a missing file) shows ok rows and error rows together, with the varied `input` as a column. Per the 01-01 note, a run whose `metrics.json` is missing counts as failed.
- `--dry-run` prints the plan and returns before `make` and before creating `analysis/results/`. Bad series files stop with a `SystemExit` naming the file and key (unknown series key, missing `base_config`, `vary` without `values`, `vary` together with `variants`, bad `seeds` or `workers`).
- Dotted override keys (`set_dotted`) create intermediate objects; the base config is deep-copied per task. `analysis/README.md` (Spanish) documents usage, series keys, output layout, column rule, failure behavior and the table of existing series.

## Task Commits

1. **Task 1: sweep.py, series_smoke_oja.json, .gitignore** - `5a88358` (feat). This commit already contained the full failure path and `--dry-run`, since they are part of the same runner.
2. **Task 2: README and verification of failure and dry-run paths** - `39142d6` (docs). Only the README is new here; the Task 2 behaviors were verified against the Task 1 code and needed no code change.

## Deviations from Plan

### Recorded deviation from locked decision D-05 ("se copia tal cual")

As the plan instructs, recorded here citing D-05. `sweep.py` is copied from `../TP3/analysis/sweep.py` and adapted, not byte-copied, because the verbatim file cannot run in TP4:

- TP3 lines 36-38 insert `TP3/scripts` into `sys.path` and import `run_error` and `run_report` at module level, and `main` imports `sweep_report`; none exist in TP4 and 01-PATTERNS.md says not to copy them in Phase 1, so the verbatim file dies with an ImportError before planning a run.
- `RunSummary`, `summarize` and `read_summary` parse TP3 MLP metrics (epochs, validation MSE, accuracy) that the TP4 `metrics.json` does not contain; summary rows are now generic dicts.
- `PATH_KEYS` named TP3 dataset keys and resolved them to absolute paths, which D-04 forbids inside run files; it is now `("input",)` rewritten with `os.path.relpath`.

Kept from TP3: the frozen dataclasses `Variant`, `Series`, `Task` (and `Task.name`), `load_series`, `series_variants`, `value_label`, `plan`, `build_binary`, the `run_task` subprocess call shape, the `ThreadPoolExecutor` + `as_completed` loop, `print_progress` on stderr, `write_plan`, `print_plan` and the CLI. Amending D-05 to "copiar y adaptar" is a user decision outside this plan; CONTEXT.md already carries the amended wording.

### Small implementation choices inside the plan's scope

- The binary is invoked with the config path relative to the sweep dir (`configs/{run}.json`, `cwd=sweep_dir`) instead of the absolute path. Error messages in `summary.csv` therefore name `configs/000_base_seed1.json` and stay identical across sweeps.
- `write_summary(rows, path, varied=())` gained the varied-keys argument (rule (e) needs their order).
- Leftover partial run directories in the sweep's `results/` are removed after the series (the plan only asked for removing an empty folder; failed runs leave a directory with just `config.json`, so an emptiness check would never fire).

### Auto-fixed issues

None. No Rule 1-3 fixes were needed.

## Notes for later plans

- The failure reason in `summary.csv` is the binary's last stderr line. For file-level failures the last line can be generic (a missing `input` file reports `configs/...json: the oja run failed` because the specific `perror` line comes earlier). Config validation errors (unknown, missing, wrong-typed keys) are specific. If later models want specific reasons for runtime failures, their runner should print the reason as the last stderr line.
- Plan 01-05 changes `neuron/config.json.oja.example` to point at `datos/prepared/creadores_zscore.csv`; the smoke series then needs that file (the README row for `series_smoke_oja` names the tracked fixture and must be updated there).
- Plan 01-07 series with `vary` or `variants` will be the first to exercise varied-key columns on real models; the mixed-failure ad hoc series above is the only coverage of that path so far.
- The ledger file for the `commits:` measurement (`.git/worktrees/.../gsd-plan-head-before-01-03`) could not be written from inside the isolated worktree; the base was the known spawn commit `a6a346f`, and `git rev-list --count a6a346f..HEAD` printed 2 before this SUMMARY commit.

## Known Stubs

None. (The oja model behind the smoke series is the intentional stub from 01-01.)

## Threat Surface

No new surface beyond the plan's threat model. Mitigations applied: `subprocess.run` with an argument list and no shell, per-run configs serialized with `json.dumps` (T-01-06); path keys rewritten with `os.path.relpath`, verified by grepping `runs/` for the absolute TP4 path (T-01-19); unknown series keys raise `SystemExit` naming key and file, the binary rejects unknown override keys (T-01-20); standard library only, nothing installed (T-01-SC).

## Self-Check: PASSED

- Files exist: `TP4/analysis/sweep.py`, `TP4/analysis/series_smoke_oja.json`, `TP4/analysis/.gitignore`, `TP4/analysis/README.md` (all four in `git show --stat` of commits `5a88358` and `39142d6`).
- Commits `5a88358` and `39142d6` exist on `worktree-agent-a9135f09c6e8ab54e`.
- Acceptance greps passed (no `run_report`/`run_error`/`sweep_report`, no numpy/matplotlib/plotly/pandas import, `ThreadPoolExecutor`, `os.path.relpath`, `PATH_KEYS = ("input",)` present, no `shell=True`); README mentions `series_smoke_oja.json`, `vary`, `variants`, `seeds`, `--dry-run`, `summary.csv`.
- STATE.md and ROADMAP.md untouched.
