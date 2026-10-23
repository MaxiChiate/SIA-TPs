---
phase: 04-hopfield-n-cleo-y-letras
plan: 08
subsystem: analysis (numpy cross-check claims, network code identity)
tags: [hopfield, gap-closure, wr-01, wr-02, provenance]
gap_closure: true
status: complete
closes: [WR-01, WR-02]
key-files:
  modified:
    - analysis/hopfield.py
    - analysis/hopfield_letters.py
    - analysis/hopfield_figures.py
    - analysis/tests/test_hopfield_letters.py
    - analysis/tests/test_hopfield_figures.py
    - analysis/README.md
    - deliverables/04-hopfield-letras.md
    - .planning/phases/04-hopfield-n-cleo-y-letras/04-04-SUMMARY.md
    - .planning/phases/04-hopfield-n-cleo-y-letras/04-05-SUMMARY.md
commits: 0
note: "No commits by instruction; everything is left unstaged."
---

# Phase 4 Plan 08: Gap closure (WR-01, WR-02) Summary

Narrowed every "every run/trial is recomputed in numpy" claim to what `analysis/hopfield.py` actually recomputes, and made `run.json` record the identity of the network code, which `hopfield_figures.py` now checks before drawing.

## Task 1: WR-01 (docs only)

Exact counts, from the code and `run.json`:

- Recomputed in every run: W, `stored.csv`, overlaps; in capacity runs, max/mean overlap, `n_stable`, `stable_fraction`, `min_margin` row by row (196,030 rows).
- Replayed step by step: the first trial per (letter, level) of each recall run, 40 runs x 4 letters x 13 levels x 1 = 2,080 of 62,400 recall trials, plus all 1,200 spurious-search trials (4 letters x 3 levels x 100).
- Range and consistency checks only: class, converged, sweeps, flips and correct of the other 60,320 recall trials; capacity `recall_rate` and `mean_sweeps`.

Edited: the module docstring of `analysis/hopfield.py` and the docstrings of `check_capacity` and `check_recall`; the module docstring and `run_series` docstring of `analysis/hopfield_letters.py`; `analysis/README.md` (the `hopfield.py` and `hopfield_letters.py` rows); section 1 "Control en Python" of the deliverable; correction notes in 04-04-SUMMARY.md and 04-05-SUMMARY.md. The `cross_checked_trials` key of run.json keeps its name (renaming would change the file beyond the identity fields); a code comment and the 04-05 note say it counts trials that went through `check_recall`.

## Task 2: WR-02

- `hopfield_letters.py`: `CODE_FILES` (the six files), `code_file_hashes`, `code_identity` (head, dirty, files, binary_sha256) and `changed_code_files`. Git is called with argument lists and no shell; paths come from the constant. `run.json` gets `code_identity` between the rule identity and `design`. Not written to selection.json: that file is written before the binary is built, and a single source in run.json is what the figures read.
- `hopfield_figures.py`: `require_same_code(run)` called from `draw` (parameter `check_code=True`) after reading run.json and before creating the output directory. A run.json without `code_identity` counts as all files changed.
- Tests: `test_run_json_records_code_identity`, `test_code_identity_dirty_flag_and_changed_files` (throwaway git repo in tmp_path), `test_code_identity_outside_a_repository`, `test_draw_accepts_the_recorded_network_code`, `test_draw_refuses_changed_network_code`, `test_draw_refuses_results_without_code_identity`.
- Deliverable section 8 (outside the rule markers): new paragraph "Qué fija la guardia y qué no", and the `make hopfield-figures` comment now says it refuses if the rule or the network code changed.

## Re-run check

`make hopfield-letters` and `make hopfield-figures` re-run against a copy taken before: `diff -rq` over all of `analysis/results/hopfield` (1,523 files, all CSV/JSON, SVG and PNG figures) shows exactly one difference, `letters/run.json`, and its diff is only the added `code_identity` block. In it `dirty` is `true` (the network code is uncommitted in this phase) and `head` is the rule commit 23c3563, which does not identify the code; the six sha256 values and the binary sha256 do. No number in the deliverable changed.

## Verification

- `make test`: 147 passed (was 141, +6 new). `make -C neuron debug`: 1100 checks, 0 failed.
- `.venv/bin/python analysis/hopfield_select.py identity`: exit 0.
- `git diff --cached --quiet`: nothing staged.
- `git status --porcelain` on the 6 frozen files: empty. The text between the rule markers is identical to the one at 23c3563, and the deliverable diff against 23c3563 removes 0 lines.

## Deviations from Plan

None. No STATE.md or ROADMAP.md edits (they were already modified before this plan).

## Known Stubs

None.

## Self-Check: PASSED
