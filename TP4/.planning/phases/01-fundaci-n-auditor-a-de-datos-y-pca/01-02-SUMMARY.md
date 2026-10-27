---
phase: 01-fundaci-n-auditor-a-de-datos-y-pca
plan: 02
subsystem: infra
tags: [python, uv, venv, makefile, numpy, matplotlib, pillow, pytest]

requires: []
provides:
  - "analysis/requirements.txt with the four exact pins (numpy 2.5.4, matplotlib 3.11.2, Pillow 13.0.0, pytest 9.1.1)"
  - "TP4/Makefile root entry point with PY/UV variables and the venv target (stamp .venv/.installed)"
  - ".venv (Python 3.12.13, not versioned) usable by data prep, EDA, PCA and pytest plans"
affects: [01-04, 01-06, 01-07, 01-08]

actuals:
  tokens: 160       # chars/4 over the files written (641 chars)
  tasks: 2
  commits: 1
plan_head_before: 97ad919a4ba3da24005bca31add415e44a46c54b
plan_head_after: 778197978f80defa3b0deed62ece167a0574b9de

tech-stack:
  added: ["numpy 2.5.4", "matplotlib 3.11.2", "Pillow 13.0.0", "pytest 9.1.1"]
  patterns:
    - "Environment created by uv into .venv; nothing installed in the Homebrew or global Python"
    - "Stamp-file Makefile target (.venv/.installed depends on analysis/requirements.txt) so editing the pins re-installs"
    - "Root Makefile only holds targets that already work; later plans add the rest"

key-files:
  created:
    - TP4/analysis/requirements.txt
    - TP4/Makefile
  modified: []

key-decisions:
  - "Installed exactly the four pins as written in the plan after the user approved the PyPI legitimacy gate (Task 1); no replacements were requested"
  - "No dataframe library and no plotly in the environment (D-06); transitive dependencies (contourpy, cycler, fonttools, kiwisolver, packaging, pluggy, pygments, pyparsing, python-dateutil, six, iniconfig) come only from matplotlib and pytest"

patterns-established:
  - "make venv is idempotent: a second run prints 'Nothing to be done'"

requirements-completed: [INFRA-04]

status: complete
duration: 5min
completed: 2026-10-20
---

# Phase 01 Plan 02: Pinned Python environment Summary

**Reproducible `.venv` from one command (`make venv`) with numpy 2.5.4, matplotlib 3.11.2, Pillow 13.0.0 and pytest 9.1.1, plus the root Makefile that later plans extend.**

## Performance

- **Duration:** about 5 min (resume after the legitimacy checkpoint)
- **Tasks:** 2 (Task 1 was the blocking human checkpoint, approved by the user; Task 2 automated)
- **Files created:** 2

## Accomplishments

- `analysis/requirements.txt` holds exactly the four approved pins plus the one comment line (D-06).
- `TP4/Makefile` defines `PY ?= .venv/bin/python`, `UV ?= uv` and `venv` as the first target, written for GNU make 3.81 (D-05). It has no recipe that calls `neuron/` or any script that does not exist yet.
- `make venv` created `.venv` with Python 3.12.13 through uv and installed the pins; a second `make venv` does nothing.

## Task Commits

1. **Task 1: Package legitimacy gate** - no commit (human checkpoint; user approved the four pins as written before any install ran).
2. **Task 2: make venv creates the pinned .venv** - `7781979` (chore)

## Verification

- `make venv && .venv/bin/python -c "import numpy, matplotlib, PIL, pytest; ..."` printed `2.5.4 3.11.2 13.0.0 9.1.1` and `VENV_OK`.
- Requirements diff against the four pins empty, `PY ?= .venv/bin/python` present, no `-C neuron` in the Makefile: `PINS_OK`.
- `git status --short` shows nothing for `.venv` (already gitignored).

## Deviations from Plan

None - plan executed exactly as written.

## Authentication Gates

None. Task 1 was a package legitimacy checkpoint, resolved by explicit user approval.

## Threat Flags

None. The only new surface is PyPI to `.venv` (T-01-SC), mitigated as planned: exact pins, human legitimacy check before install, installs only inside `.venv` through uv.

## Known Stubs

None.

## Next Phase Readiness

Plans 01-04, 01-06, 01-07 and 01-08 can use `PY` from the root Makefile and run Python and pytest inside `.venv`. Plan 01-06 and later add the prepare/eda/pca/test/clean/all targets.

## Self-Check: PASSED

- FOUND: TP4/analysis/requirements.txt
- FOUND: TP4/Makefile
- FOUND: commit 7781979
