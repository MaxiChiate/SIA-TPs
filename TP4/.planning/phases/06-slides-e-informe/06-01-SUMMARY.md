---
phase: 06-slides-e-informe
plan: 01
subsystem: infra
tags: [make, venv, pip, python-markdown, file-sentinels, reproducibility]

requires:
  - phase: 02-som
    provides: SOM stage 1 and 2 results, figures and profiles under analysis/results/som (kept, not rerun)
  - phase: 05-hopfield-qr
    provides: pre-registered Hopfield QR drivers and guards that make results only calls
provides:
  - "Markdown==3.11 pinned in analysis/requirements.txt and installed in .venv after human approval"
  - "make venv works without uv (python3.12 -m venv plus pip fallback)"
  - "make results regenerates only the Phase 1-5 steps whose sentinel file is missing (17 sentinels)"
  - "analysis/results/ and datos/prepared/ fully populated on this machine for later Phase 6 plans"
affects: [06-04, 06-08, 06-09, 06-11, slides, informe, drift pins]

actuals:
  tokens: 1430
  tasks: 3
  commits: 2
plan_head_before: f16d8f041f14da0efe6bdb062f06f90fe9d15f7d
plan_head_after: 182cc5b053cc9ce88b25973b8c4a659c10d6ccd6

tech-stack:
  added: [Markdown==3.11]
  patterns:
    - "File-sentinel make targets: each rule calls its driver directly, prerequisites are order-only (after |)"
    - "Pip fallback in the venv recipe selected by command -v $(UV)"

key-files:
  created: []
  modified: [Makefile, analysis/requirements.txt]

key-decisions:
  - "Pinned Markdown==3.11 (not 3.11.2): the seam flagged SUS on the 6-day-old release date; 3.11 is about 30 days old, pure-Python wheel"
  - "Sentinel recipes call the driver scripts, never a phony target, so campaigns and maintenance do not drag som-stage1 (140 runs) along"
  - "No neuron/build/neuron rule: sweep.py builds the binary itself and it already exists"

patterns-established:
  - "make results is idempotent: a second make -n results lists no analysis/*.py or scripts/*.py command"
  - "A stale sentinel is not detected by design; force a step with rm -rf analysis/results/<step> then make results (to be documented in README by 06-11)"

requirements-completed: [DELIV-02, DELIV-03]

coverage:
  - id: D1
    description: "Markdown==3.11 is pinned and importable from .venv, installed only after the blocking-human legitimacy checkpoint answered approved"
    requirement: DELIV-03
    verification:
      - kind: other
        ref: ".venv/bin/python -c 'importlib.metadata.version(\"Markdown\") == \"3.11\"; import markdown' prints MARKDOWN_OK"
        status: pass
    human_judgment: false
  - id: D2
    description: "make venv works on a machine without uv through the python3.12 -m venv plus pip fallback, and make -n venv is empty afterwards"
    requirement: DELIV-03
    verification:
      - kind: other
        ref: "make venv (took the fallback branch, installed Markdown-3.11); make -n venv prints 'Nothing to be done'"
        status: pass
      - kind: unit
        ref: ".venv/bin/python -m pytest analysis/tests -q (230 passed)"
        status: pass
    human_judgment: false
  - id: D3
    description: "make results regenerated every missing Phase 1-5 result from file sentinels and is idempotent on the populated tree"
    requirement: DELIV-02
    verification:
      - kind: other
        ref: "SENTINELS_OK loop over the 14 analysis/results sentinels (all non-empty); make -n results -> 'Nothing to be done for results'"
        status: pass
    human_judgment: false
  - id: D4
    description: "Package legitimacy of Python-Markdown judged by a human before install"
    verification: []
    human_judgment: true
    rationale: "Task 1 is a blocking-human checkpoint; trust in a third-party package is a human decision, answered 'approved'"

duration: 20min
completed: 2026-10-25
status: complete
---

# Phase 6 Plan 1: Markdown pin, no-uv venv and make results Summary

**Markdown==3.11 pinned after a human legitimacy check, make venv with a python3.12 -m venv plus pip fallback, and an idempotent make results built from 17 file sentinels that regenerated the 12 missing Phase 1-5 steps in 10 min 53 s.**

## Performance

- **Duration:** about 20 min of continuation work (this agent: 21:43:02Z to the SUMMARY); `make results` alone 653 s
- **Started (this continuation):** 2026-10-25T21:43:02Z
- **Completed:** 2026-10-25T21:56Z
- **Tasks:** 3 (1 checkpoint, 2 auto)
- **Files modified:** 2 (Makefile, analysis/requirements.txt)

## Task 1 checkpoint log

Task 1 (`checkpoint:human-verify`, `gate="blocking-human"`) stopped the previous executor with nothing installed. The human verified Markdown 3.11 on PyPI (pure-Python `py3-none-any` wheel, `requires_python >=3.11`, repository Python-Markdown) and answered **"approved"**. That answer is the resume signal that satisfied Task 2's precondition. No package was installed before it.

## Accomplishments

- `analysis/requirements.txt` ends with `Markdown==3.11`; `.venv` has Markdown 3.11 (`importlib.metadata.version` returns `3.11`, `import markdown` works).
- `.venv/.installed` recipe: `if command -v $(UV) ...; then <uv path> else <python3.12 -m venv + .venv/bin/python -m pip install -r analysis/requirements.txt> fi`, then `touch $@`. uv is absent here, so the fallback branch ran. Full suite: 230 passed (same as baseline).
- `make results`: `RES`, `PREP`, `RESULTS_SENTINELS` (17 paths), one Spanish-commented file rule per sentinel with order-only prerequisites, phony `results` (also added to `.PHONY`).
- First full run populated `analysis/results/` and `datos/prepared/`; `make -n results` now prints only "Nothing to be done for `results'".

## make results run (resolves research assumption A5)

- **Command:** `nohup make results > make-results.log` from TP4/, background, one run.
- **Start:** 2026-10-25T21:44:32Z. **Exit:** about 21:55:25Z (last log write). **Wall time: 653 s (10 min 53 s).**
- **Steps executed (12), in order:** `analysis/eda.py`, `analysis/pca.py`, `analysis/oja.py`, `analysis/campaigns.py`, `analysis/maintenance_demo.py`, `scripts/prepare_letters.py`, `analysis/hopfield_letters.py`, `analysis/hopfield_figures.py`, `scripts/prepare_qr.py`, `analysis/hopfield_qr.py`, `analysis/hopfield_qr_limits.py`, `analysis/hopfield_qr_figures.py`.
- **Skipped (sentinel already existed, 5):** `prepare_creadores`, SOM stage 1, SOM stage 2, SOM figures, SOM profiles.
- No driver guard refused; the log has no error, traceback or refusal line. QR verdict from the run: Hebb fails (0.00% exact recovery, noise 0, async), pinv works (100.00%).
- This is far below the "about an hour" the plan assumed (one `make hopfield-qr` took about 46 min in Phase 5): on this machine the whole missing chain took under 11 minutes, so the README run-time note (06-11) can say "about 11 minutes on this machine for the missing steps; a full rebuild including SOM stage 1 takes longer".

## Task Commits

1. **Task 1: Human verifies the Python-Markdown package** - no commit (checkpoint, answered "approved")
2. **Task 2: Pin Markdown==3.11 and no-uv fallback** - `1b232cf` (feat)
3. **Task 3: make results from file sentinels** - `182cc5b` (feat); the run itself produces untracked, git-ignored output only

**Plan metadata:** committed with this SUMMARY (docs: complete plan).

## Files Created/Modified

- `Makefile` - `.venv/.installed` with the uv/pip branch and comment above `venv:`; sentinel block and `results` target; `results` in `.PHONY`
- `analysis/requirements.txt` - `Markdown==3.11`

## Decisions Made

- Pin `Markdown==3.11` rather than 3.11.2 (see key-decisions).
- Sentinel rules call drivers directly and use order-only prerequisites, per research Pattern 5 and Pitfall 1.
- Did not add an order-only `neuron/build/neuron` rule; `make -C neuron` is a no-op (binary built) and `sweep.py` builds it when missing.

## Deviations from Plan

None - plan executed exactly as written, with two notes that changed no file beyond the plan:

- The plan said to "update the Spanish comment above `venv:`", but no comment existed there; one was added (Spanish, one line) stating the uv / `python3.12 -m venv` plus pip behavior.
- The plan's second Task 2 `<automated>` check uses `grep -q 'command -v $(UV)'`. The `grep` on this machine (ugrep) reads `$(UV)` as a regular expression, so the literal command prints nothing even though the text is present (line 33 of Makefile). The same check with `grep -F` prints `PIN_AND_FALLBACK_OK`; the other two greps in that command pass as written. Verification outcome is a pass; the plan's command is just not portable to this grep.

**Total deviations:** 0 auto-fixed.

## Issues Encountered

None. A foreground wait loop exceeded its tool timeout once and was moved to the background by the harness; it did not affect the `make results` process, which was polled until exit.

## Authentication Gates

None. Task 1 was a planned human checkpoint, not an auth gate.

## Known Stubs

None. No files with placeholder data were created or modified.

## Threat Flags

None. No new network endpoints, auth paths or trust-boundary file access beyond the plan's threat model. T-06-SC (PyPI install) mitigated by Task 1; T-06-01 mitigated: `git status --porcelain -- deliverables analysis/som_select.py analysis/campaigns_select.py analysis/hopfield_select.py analysis/hopfield_qr_select.py` prints nothing after the run.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Wave 1 prerequisite met: `analysis/results/**` and `datos/prepared/**` hold every Phase 1-5 result, and Markdown 3.11 is available for the informe converter (06-04, 06-08, 06-09).
- 06-11 should document: `rm -rf analysis/results/<step>` then `make results` to force a step; stale sentinels are not detected; measured run time above.

## Self-Check: PASSED

- `Makefile`, `analysis/requirements.txt`: FOUND and committed.
- Commits `1b232cf` and `182cc5b`: FOUND in HEAD history.
- 14 analysis/results sentinels non-empty (`SENTINELS_OK`); `make -n results` lists no Python step; `NO_PHONY_DRAG` passes; 230 tests pass; no guarded file modified.

---
*Phase: 06-slides-e-informe*
*Completed: 2026-10-25*
