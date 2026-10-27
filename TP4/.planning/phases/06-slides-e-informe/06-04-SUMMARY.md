---
phase: 06-slides-e-informe
plan: 04
subsystem: docs
tags: [informe, facts, python-markdown, artifact-page, svg-data-uri, anchors, tracer]

requires:
  - phase: 06-slides-e-informe
    provides: "06-01: Markdown==3.11 in .venv, make results regenerated analysis/results/**"
  - phase: 02-kohonen-som
    provides: "deliverables/02-kohonen.md (fragment), SOM JSON results and figures"
provides:
  - "analysis/facts.py: the only number formatter (dec, pct, integer), SOURCES, read_source, load_facts, fill"
  - "analysis/deliverables_manifest.py: Question, Figure, FRAGMENTS, QUESTIONS (4 SOM questions), FIGURES (map, pc planes)"
  - "analysis/informe.py: builder (make_slugify, render_fragment, figure_card, question_table, stamp, build, main)"
  - "make informe -> analysis/results/informe/informe.html (not versioned)"
  - "Anchor scheme f<n>, f<n>-s<a>-<b>; ids resumen, preguntas, metodo, ej1; classes fact, fig, table-wrap; attribute data-fact"
affects: [06-05, 06-08, 06-09]

actuals:
  tokens: 8500
  tasks: 2
  commits: 3
plan_head_before: eca96a863288fc55de2f91a89be2b414d1b19fce
plan_head_after: 4ef4c07dc70317b61aa1898c8c581548fc9a0e7d

tech-stack:
  added: []
  patterns:
    - "Numbers in generated text are {group.key} tokens filled by facts.fill with a wrap that emits <span class=fact data-fact=KEY>; never typed"
    - "Figures embedded as <img data:image/svg+xml;base64> on a figure card whose background is plots_style.SURFACE in both themes"
    - "Fragments rendered read-only with Python-Markdown (toc slugify gives number-based anchors); every change happens at render time"
    - "Build asserts: question anchors present, no unresolved token, no script element, size ceiling, no home path or email (page and decoded SVGs)"

key-files:
  created:
    - analysis/facts.py
    - analysis/deliverables_manifest.py
    - analysis/informe.py
    - analysis/tests/test_facts.py
    - analysis/tests/test_informe.py
  modified:
    - Makefile

key-decisions:
  - "The top heading of a fragment drops its own leading 'Fase n — ' when it gets the 'Detalle técnico (Fase n): ' prefix, so the page does not read 'Fase 2: Fase 2 — ...'"
  - "informe.fact_span (the data-fact wrapper) is public so the facts tests exercise the same callback the builder passes to facts.fill"
  - "The build also scans the decoded embedded SVGs for home paths and emails, since base64 hides them from a text scan of the page"

requirements-completed: []  # DELIV-02 is declared by sibling plans of this phase with no SUMMARY yet (requirements.ready-ids: blocked); not marked complete here

coverage:
  - id: D1
    description: "make informe builds the SOM slice end to end: facts from results JSON, fragment 02 with number-based anchors, two figure cards, linked question table"
    requirement: "DELIV-02"
    verification:
      - kind: integration
        ref: "task 1 automated verify (TRACER_OK, FRAGMENTS_UNTOUCHED) re-run after make informe"
        status: pass
    human_judgment: false
  - id: D2
    description: "Artifact page contract (title and style first, no skeleton tags, token blocks, safe-area gutters, tables in scroll boxes)"
    requirement: "DELIV-02"
    verification:
      - kind: unit
        ref: "analysis/tests/test_informe.py#test_build_writes_a_contract_page"
        status: pass
    human_judgment: true
    rationale: "Rendering at about 400 px and in both themes needs the page opened in the Artifact viewer; no automated check renders it"
  - id: D3
    description: "facts formatters, slug scheme, figure embedding and build-time failures covered on synthetic fixtures"
    requirement: "DELIV-02"
    verification:
      - kind: unit
        ref: "analysis/tests/test_facts.py and analysis/tests/test_informe.py (32 tests)"
        status: pass
    human_judgment: false

duration: 17min
completed: 2026-10-25
status: complete
---

# Phase 6 Plan 04: Informe tracer (SOM slice) Summary

**One `make informe` turns SOM results JSON plus deliverables/02-kohonen.md into a self-contained Artifact-contract HTML page: facts-sourced `data-fact` numbers, number-based anchors (f2-s6-4), SVG figures as data URIs on a light card, and a question table that links to those anchors.**

## Performance

- **Duration:** about 17 min (start time was not recorded; estimated from the previous commit)
- **Tasks:** 2 (1 tracer, 1 tdd)
- **Files:** 5 created, 1 modified (853 insertions)
- **Commits:** 333efd9 (feat, tracer), dbc7728 (refactor), 4ef4c07 (test)

## Accomplishments

- **facts.py** is the only formatter: `dec` (decimal comma, NaN gives n/d), `pct` (`97,3 %`), `integer`; `load_facts` reads three SOM JSONs and a missing file stops with `run \`make results\` (step som-profiles)`. `fill` raises on an unknown key and, with a wrap callback, emits `<span class="fact" data-fact="som.r2_pc1">0,961</span>`.
- **informe.py** renders fragment 02 with Python-Markdown (`tables`, `fenced_code`, `toc` with a custom slugify and baselevel 3). Real ids produced: f2, f2-s1 to f2-s7, f2-s6-1 to f2-s6-5; the `_1` suffix for duplicates is covered by a test. The `regla:inicio/fin` comments are stripped, tables wrapped in `div.table-wrap`, and the two figure cards land at the end of sections f2-s5 and f2-s6-4.
- The page is 291 KB, starts with `<title>Informe TP4 SIA</title>` and the `claude:viewport-fit-sides` meta, has no skeleton tag and no script, redefines the colour tokens in both dark blocks, and `--figure-surface` is `#fcfcfb` (imported from `plots_style.SURFACE`) in all three blocks.
- The question table maps Q1.4 to Q1.7 to f2-s5, f2-s6-1..3, f2-s6-4 and f2-s6-5, all present in the page (the build asserts it).

## Task Commits

1. **Task 1: tracer, SOM slice end to end** - `333efd9` (feat) - facts.py, deliverables_manifest.py, informe.py, Makefile
2. **Task 2: fixture tests** - `dbc7728` (refactor: `fact_span` made public) then `4ef4c07` (test) - test_facts.py, test_informe.py

Tracer gate: auto mode off, `human_verify_mode` end-of-phase and the tracer `<verify>` is automated-only, so the verify was re-run after the build (TRACER_OK, FRAGMENTS_UNTOUCHED) and execution continued. `fragments untouched`: `git diff --quiet -- deliverables/` passes.

## Verification

| Check | Result |
|-------|--------|
| `make informe` prints `informe -> analysis/results/informe/informe.html` | pass |
| Task 1 verify (TRACER_OK, FRAGMENTS_UNTOUCHED) | pass |
| `grep -c 'def dec\|def pct\|def integer\|def load_facts\|def fill' analysis/facts.py` | 5 |
| test_facts.py + test_informe.py | 32 passed |
| `pytest analysis/tests` (SUITE_OK) | 262 passed (230 before) |
| `make test` | 262 passed, 1282 checks, 0 failed |
| No test opens analysis/results | pass (only the module docstring mentions the path) |

## TDD Gate Compliance

Task 2 is `tdd="true"` but the plan orders it after the tracer that implements the code under test, so there was no failing-first state: the 32 tests passed on their first run (an unexpected GREEN under the fail-fast rule). The investigation conclusion is that this is by design (tests-after on an already written tracer), not a wrong test. To show the tests have teeth, a temporary mutation run (slug number kept dotted, decimal comma removed, script check disabled) made 11 tests fail; the originals were restored byte for byte and the suite is green again. There is therefore no RED `test(...)` commit preceding a `feat(...)` commit for this plan; the single `test(06-04)` commit follows `feat(06-04)`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] CSS template used `%` formatting and crashed on import**
- **Found during:** Task 1 (first `make informe`)
- **Issue:** `STYLE = """...%(surface)s...""" % {...}` raised `TypeError: not enough arguments` because the CSS contains literal `%` (`max-width: 100%`).
- **Fix:** placeholder `__SURFACE__` replaced with `str.replace`.
- **Files modified:** analysis/informe.py
- **Commit:** 333efd9 (fixed before the first commit)

### Plan interpretation choices

**2. [Minor] Top heading prefix drops the redundant "Fase n — "**
- The plan says to prefix the top heading with "Detalle técnico (Fase n): "; applied literally the heading would read "Detalle técnico (Fase 2): Fase 2 — Mapa de Kohonen ...". The leading "Fase n — " is removed, giving "Detalle técnico (Fase 2): Mapa de Kohonen (SOM) de los 50 creadores". The slug (id="f2") is unaffected. Commit 333efd9.

**3. [Minor] `_wrap_fact` renamed `fact_span`**
- Needed so the facts test can pass the same wrapper to `facts.fill`. Commit dbc7728.

**4. [Minor] Extra build-time checks beyond the plan**
- The build also rejects any `<script` in the page (fragments are raw Markdown and could carry one) and scans the base64-decoded SVGs for home paths and emails. Both support T-06-09 and T-06-10.

**Total deviations:** 1 auto-fixed bug, 3 minor choices. **Impact:** none on the contract.

## Issues Encountered

- `root-pin.sh` prints nothing on success (it only prints `FATAL` and exits 1 on mismatch), while the dispatch says it must print `PIN_OK`. I treated exit 0 with no output as a pass and appended `&& echo PIN_OK` myself from the second use on.
- One long ad hoc inspection command (a `grep -o` over the 291 KB page, whose base64 lines are very long, under ugrep) exceeded the 120 s foreground limit and was moved to the background; it finished with the expected results. The plan's own verify commands run in about a second. Not a plan defect.

## Items for a human

- **Question texts need comparison against the enunciado PDF.** The four SOM question texts in `analysis/deliverables_manifest.py` come from 06-RESEARCH "Literal Questions" with reconstructed accents (assumption A6). The success criterion says "literal"; compare each against `docs/Archivo SIATP 42026.pdf` before publishing.
- **Visual check of the page** at about 400 px width and in both themes is not automated (coverage D2). It belongs to the publish checkpoint of the phase.

## Known Stubs

None. No hardcoded empty values, placeholders or mock data flow into the page.

## Threat Flags

None. No new network endpoint, auth path or file access beyond the plan's threat model; the mitigations T-06-08 to T-06-11 are implemented (html.escape on every interpolated value, `<b>` test; img data URIs only; stamp is short HEAD plus a dirty flag; MAX_BYTES 12 000 000) and tested.

## Next Phase Readiness

The architecture is proven on real data for exercise 1, fragment 02. 06-05 can regenerate the SOM SVGs (the page only reads them and imports `plots_style.SURFACE`); 06-08 and 06-09 widen `FRAGMENTS`, `QUESTIONS`, `FIGURES` and `load_facts` to every phase and add the glossary and the remaining exercise section. DELIV-02 stays open: sibling plans declare it and have no SUMMARY yet.

## Self-Check: PASSED

- FOUND: analysis/facts.py, analysis/deliverables_manifest.py, analysis/informe.py, analysis/tests/test_facts.py, analysis/tests/test_informe.py
- FOUND commits: 333efd9, dbc7728, 4ef4c07 (all ancestors of HEAD); `commits: 3` measured with `git rev-list --count eca96a8..HEAD`
- Acceptance criteria of both tasks re-run: pass. Plan verification (TRACER_OK, FRAGMENTS_UNTOUCHED, PYTEST_OK, SUITE_OK) pass.
