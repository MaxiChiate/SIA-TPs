---
phase: 06-slides-e-informe
plan: 11
subsystem: deliverables-assembly
tags: [make, deliverables, slides, informe, readme, claude-md, repro-docs, sentinels, deliv-03]

requires:
  - phase: 06-slides-e-informe
    provides: "06-01 results sentinels and venv fallback; 06-09 informe.py with --notes; 06-10 slides.py; 06-08 manifest FIGURES; 06-03 DECISIONS.md"
provides:
  - "Makefile: phony slides and deliverables, SLIDE_SENTINELS (7 file rules), INFORME_FLAGS"
  - "README.md (TP4 root): reproduction guide with one row per manifest figure (31), main tables, no-uv path, measured run time, how to force a step, manual publish steps"
  - "CLAUDE.md (TP4 root): session starting point in the TP3 shape; .planning/config.json claude_md_path -> ./CLAUDE.md"
  - "analysis/tests/test_repro_docs.py: 22 tests that keep the three reproduction documents present and consistent"
affects: [06-12]

actuals:
  tokens: 10300
  tasks: 3
  commits: 3
plan_head_before: f4ac9583d42242264175466fa3e71eadf07d91b7
plan_head_after: 7b11a7d93ec8e03f987ebd3b6928ac9867ad3b65

tech-stack:
  added: []
  patterns:
    - "One file sentinel per figure script (the last slide figure it writes), order-only prerequisites on the matching results sentinel, because GNU Make 3.81 has no grouped targets"
    - "Docs checks are functions of a root folder: the real tree is checked with the same functions that the scratch-copy failing cases exercise"

key-files:
  created:
    - README.md
    - CLAUDE.md
    - analysis/tests/test_repro_docs.py
  modified:
    - Makefile
    - .planning/config.json

key-decisions:
  - "INFORME_FLAGS is empty because 06-ARTIFACT-FORMAT.md says notes_supported: true (the plan's literal rule); switching the informe to carry the presenter-script annex is a one-line change to --notes analysis/results/slides/notes.md, and deliverables already runs slides.py first"
  - "Each slide sentinel waits (order-only) for the results sentinel written by the same script, so on a fresh tree the script runs once and the slide sentinel is already satisfied"

patterns-established:
  - "A documented `make <target>` is only valid if the Makefile defines it; README rows carry the figure path and its make target on one line"

requirements-completed: []  # DELIV-01, DELIV-02 and DELIV-03 are declared by sibling plans of this phase without a SUMMARY (06-12); requirements.ready-ids decides in the state step

coverage:
  - id: D1
    description: "make deliverables regenerates what is missing and rebuilds slides and informe; two consecutive runs leave informe.html and the 42 slide files byte-identical; a dry run on the populated tree never lists a slow driver"
    requirement: "DELIV-03"
    verification:
      - kind: integration
        ref: "task 1 automated verify (DELIVERABLES_REPRODUCIBLE, NO_SLOW_RERUN)"
        status: pass
    human_judgment: false
  - id: D2
    description: "README.md with one row per manifest figure (command, config, seed), main tables, no-uv path, measured make results time, how to force a step and the manual publish steps of both Artifacts; CLAUDE.md in the TP3 shape"
    requirement: "DELIV-03"
    verification:
      - kind: integration
        ref: "task 2 automated verify (DOCS_WRITTEN) and analysis/tests/test_repro_docs.py#test_real_readme_has_a_row_with_the_make_target_for_every_manifest_figure"
        status: pass
    human_judgment: true
    rationale: "Tests check presence, targets and rows; whether the Spanish prose and the pending items read right needs the author"
  - id: D3
    description: "make test fails when a reproduction document is missing or near empty, names a missing make target, lacks a figure row, or a slides export lands in docs/"
    requirement: "DELIV-03"
    verification:
      - kind: unit
        ref: "analysis/tests/test_repro_docs.py (22 tests)"
        status: pass
      - kind: integration
        ref: "make test: 473 passed, 1282 checks, 0 failed"
        status: pass
    human_judgment: false
  - id: D4
    description: "The manual publish steps (Slides and HTML Artifact) are written for both Artifacts as recorded in 06-ARTIFACT-FORMAT.md"
    requirement: "DELIV-01"
    verification: []
    human_judgment: true
    rationale: "Executors have no Artifact tool: the steps are documented from the probe and are exercised for real only in 06-12"

duration: 8min
completed: 2026-10-26
status: complete
---

# Phase 6 Plan 11: deliverables target and reproduction docs Summary

**`make deliverables` now regenerates only what is missing (results plus one slide-figure sentinel per figure script), then rebuilds the 24-slide deck and the informe byte-for-byte reproducibly, and README.md (31 figure rows), CLAUDE.md and DECISIONS.md are guarded by 22 tests so the TP3 delivery-day deletion cannot repeat silently.**

## Performance

- **Duration:** about 8 min (start time not recorded; estimated from the 06-10 state update at 02:49Z to the last task commit at 02:56Z)
- **Tasks:** 3 (2 auto, 1 tdd)
- **Files:** 5 (3 created, 2 modified)
- **Commits:** 3 measured (`cf987ad`, `7be2466`, `7b11a7d`)

## Accomplishments

- **Makefile.** Phony `slides` (`analysis/slides.py`) and `deliverables: results $(SLIDE_SENTINELS)`, whose recipe runs `slides.py` and then `informe.py $(INFORME_FLAGS)`. `SLIDE_SENTINELS` has 7 entries, one per figure script, each the last slide figure the script writes (confirmed by reading each script's call order: pca audited `biplot`, som-figures `stage1_curves`, som-profiles `pc_planes`, oja `oja_vs_pc1`, campaigns `shortlists_som`, hopfield-figures `spurious`, hopfield-qr-figures `majority`). Dry run on the populated tree lists only `slides.py` and `informe.py`; with the oja slide folder moved away, it lists `oja.py` first and nothing slow, which is the repair path of a results tree built before the slide variants.
- **Reproducibility.** Two consecutive `make deliverables` runs give identical `shasum -a 256` lists for `informe.html` and the 42 files under `analysis/results/slides` (`DELIVERABLES_REPRODUCIBLE`).
- **README.md.** Title and the two exercises, requisitos with the no-uv commands, quick start, measured run time (653 s for the 12 missing steps, SOM already done), how to force a step by deleting a results folder (with the sentence that a guard refusal is a discussion, never an edit of the rule or the hash), the "Figuras" table generated from `FIGURES` (31 rows with command, config, seed), the "Tablas" table (9 main tables with their commands), "Slides e informe" with the manual publication of both Artifacts from 06-ARTIFACT-FORMAT.md, "Entrega" and links.
- **CLAUDE.md.** TP3 shape: contexto vivo, annotated tree of neuron/, analysis/, scripts/, datos/, deliverables/, docs/, what the enunciado asks per exercise, closed decisions pointing to DECISIONS.md, delivery state, pending items (publication, Phase 3 UAT with 3 pending tests, open review findings, Phase 2 validation draft), reproduction, known traps and conventions. `.planning/config.json` `claude_md_path` is `./CLAUDE.md`.
- **Tests.** `analysis/tests/test_repro_docs.py` (22 tests): presence and minimum lines (60, 40, 200), every `make <target>` named in README.md or CLAUDE.md defined in the Makefile, a README line with the path and `make <make_target>` for each of the 31 figures, a `### F<n> D-` heading for n 1 to 6, no home path or e-mail, no `Slides_TP4*` or `.pptx` in docs/, and no line describing an informe PDF/Word export or the Docs type. The failing cases run on scratch copies of the real files.

## Task Commits

1. **Task 1: slides and deliverables targets** - `cf987ad` (feat)
2. **Task 2: README.md, CLAUDE.md and claude_md_path** - `7be2466` (docs)
3. **Task 3: reproduction-docs tests** - `7b11a7d` (test)

**Plan metadata:** recorded in the docs commit that follows this file.

## TDD Gate Compliance

`workflow.tdd_mode` is off and the plan type is `execute`, so `gsd check tdd-red-evidence` was not run. The plan orders the documents (Task 2) before their test (Task 3), so the RED step on the real tree is impossible by construction: the first run of the new file was green (22 passed). No separate RED commit exists; the plan's single `test(06-11)` commit holds the whole test.

- **Failing-evidence substitute:** the same checks fail on scratch copies of the real files (14 mutation cases assert the exact message: a document deleted or near empty, an undefined `make` target, a removed Makefile target, a missing figure row, a wrong make target on a row, a missing `### F3 D-` heading, a home path and an e-mail, a slides PDF and a `.pptx`, an informe export line). On the real tree, moving CLAUDE.md out of the folder made `test_real_documents_exist_and_are_not_near_empty` fail (1 failed, 6 passed); the file was restored before the commit.
- **GREEN:** 22 passed in test_repro_docs.py; `make test` 473 passed (451 before plus 22) and 1282 checks, 0 failed.
- **REFACTOR:** none.

## Verification

| Check | Result |
|-------|--------|
| Task 1: DELIVERABLES_REPRODUCIBLE (43 files hashed, two runs equal) | pass |
| Task 1: NO_SLOW_RERUN (`.PHONY` has slides and deliverables, dry run has no som_stage, hopfield_qr or hopfield_letters) | pass |
| Task 1 acceptance: 7 `SLIDE_SENTINELS` entries; `INFORME_FLAGS` empty, matching `notes_supported: true` | pass |
| Task 2: DOCS_WRITTEN (README 133 non-empty-line file, CLAUDE.md, config value) | pass |
| Task 2 acceptance: 31 figure rows, Tablas table, no-uv commands and measured time in README; the seven CLAUDE.md sections | pass |
| Task 3: PYTEST_OK and MAKE_TEST_OK | pass (473 passed, 1282 checks, 0 failed) |
| `git status`: only `.planning/milestone.lock` untracked; no `TP4/.git` | pass |

## Decisions Made

See `key-decisions`. For 06-12: the notes annex is off in the informe. If the top-level session wants the presenter script in the informe too (06-ARTIFACT-FORMAT.md section 4 recommends keeping the D-06 fallback because the deck is shared as a PDF and the PDF may not carry the notes), change `INFORME_FLAGS :=` in the Makefile to `--notes analysis/results/slides/notes.md`; `deliverables` already builds the slides first.

## Deviations from Plan

### Auto-fixed Issues

None for Rules 1-3.

### Notes on interpretation (no behavior change from the plan)

- **INFORME_FLAGS.** The plan says empty when `notes_supported: true`, and the orchestrator brief says "wire INFORME_FLAGS here". Followed the plan literally (empty, with a Spanish comment that names the probe file and the one-line switch). The recommendation in 06-ARTIFACT-FORMAT.md to also keep the annex is surfaced above as a decision for the top-level session.
- **Slide sentinel prerequisites.** The plan lists "the results sentinels that script reads"; each slide rule instead waits order-only for the results sentinel the same script writes (and that one waits for its own inputs). On a fresh tree this runs each script once; on a stale one it repairs only the slide variants.
- **The `informe` target** was left untouched (no `$(INFORME_FLAGS)`); `INFORME_FLAGS` applies to `deliverables`. With the flags empty both produce the same file.
- **Test ordering.** The RED evidence is on mutated copies, not on the real tree (see TDD Gate Compliance).
- **Portability.** In zsh a bare `echo =====` is an `=` expansion error; used quoted separators. No `grep $(...)` verify misbehaved on ugrep.

**Total deviations:** 0 auto-fixed. **Impact:** none.

## Issues Encountered

- `make deliverables` rebuilds the slides with local `../../assets/<name>.png` srcs, so a deck rebuilt after publication would no longer carry the `/_blob/<id>` urls. README.md and CLAUDE.md both say to rerun `slides.py --asset-map` before publishing; 06-12 must do that as its last build step.
- The Spanish prose of README.md and CLAUDE.md was not read by a second person (coverage D2 marked for human judgment). Phase 3 UAT (3 tests) and the open review findings are listed as pending, not resolved.

## Known Stubs

None. No placeholder text or empty data source in the files changed; the "Entrega" sections say that the published links are added after publication, which is the stated plan for 06-12, not a stub.

## Threat Flags

None. The plan adds no endpoint, auth path or file access; the docs are scanned by the tests for home paths and e-mails (T-06-28) and for documented targets and figure rows (T-06-29). No package was installed (T-06-SC). The docs only describe forcing a step by deleting a results folder (T-06-27).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 06-12 can publish: `make deliverables` produced `analysis/results/slides/` (24 slides, 15 PNGs, `notes.md`) and `analysis/results/informe/informe.html`. Upload the PNGs, write `asset_map.json`, rebuild with `--asset-map`, then publish both Artifacts and add the links to README.md and CLAUDE.md (the tests keep both documents valid).
- No blockers.

---
*Phase: 06-slides-e-informe*
*Completed: 2026-10-26*

## Self-Check: PASSED

- Makefile, README.md, CLAUDE.md and analysis/tests/test_repro_docs.py exist; `SLIDE_SENTINELS` has 7 `.svg` entries; README.md has 31 figure rows; `claude_md_path` is `./CLAUDE.md`.
- Commits cf987ad, 7be2466 and 7b11a7d are ancestors of HEAD; `git rev-list --count f4ac958..HEAD` is 3 at the time of writing.
- All acceptance criteria of the three tasks re-run after the last commit: DELIVERABLES_REPRODUCIBLE, NO_SLOW_RERUN, DOCS_WRITTEN, PYTEST_OK, MAKE_TEST_OK; no `TP4/.git`.
