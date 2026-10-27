---
phase: 06-slides-e-informe
plan: 09
subsystem: docs
tags: [informe, python-markdown, glossary, jargon-links, drift-gate, artifact-page, facts]

requires:
  - phase: 06-slides-e-informe
    provides: "06-03 DECISIONS.md heading grammar, 06-04 informe tracer, 06-08 manifest (25 checked questions, 31 figures), facts and 68 drift pins"
provides:
  - "analysis/informe.py: the whole hybrid report (summary of findings, question table, method, Ejercicio 1 and 2, glossary annex, optional presenter-script annex)"
  - "parse_glossary, link_jargon, glossary_section, notes_section, typed_numbers, Finding/FINDINGS, GlossaryEntry, EMBED_SVG_MAX, EXERCISES"
  - "build keywords questions_checked, pins, glossary_path, notes_path, findings; CLI flag --notes"
  - "make informe -> analysis/results/informe/informe.html (6.9 MB, 31 figure cards, 154 jargon links)"
affects: [06-10, 06-11, 06-12]

actuals:
  tokens: 12100
  tasks: 2
  commits: 3
plan_head_before: 645a24376bcb666b0577700f48c90a6977dc4834
plan_head_after: ebfb25c4c21e5f2f09114cb34066e34acb9d1fa8

tech-stack:
  added: []
  patterns:
    - "The generated front section is a tuple of Finding(topic, text, anchor, unfavorable) templates filled by facts.fill with the data-fact wrap; build refuses any typed decimal or percentage (typed_numbers)"
    - "Jargon links are a render-time pass over the HTML text nodes (tag split, depth counter for code/pre/a); attribute values are never rewritten and the fragments and DECISIONS.md are only read"
    - "Build gates in order: questions_checked flags (read at call time), glossary present, facts, drift pins, no typed numbers, anchors and internal href targets, size, leaks"

key-files:
  created: []
  modified:
    - analysis/informe.py
    - analysis/tests/test_informe.py

key-decisions:
  - "questions_checked defaults to None and the manifest flags are read at call time, so a test or a later edit of the flags is honored (a def-time default would freeze them at import)"
  - "The page scan for home paths and e-mails runs on the page with base64 data URIs removed, because the figures are scanned decoded; scanning the multi-megabyte base64 runs made the e-mail regex quadratic"
  - "Requirement entries of DECISIONS.md have no Que line: their glossary text is the first paragraph line with Markdown links reduced to text (the repo paths would be dead links in a self-contained page); KD entries are skipped"
  - "In 'Fase M (D-NN, D-MM' every ID of the parenthesis keeps phase M; a lettered ID or Pitfall without its own entry (D-11a, Pitfall 14b) links to its parent"

patterns-established:
  - "Findings carry the section they summarize as an anchor and the build verifies every internal href target exists"

requirements-completed: []  # DELIV-02 is declared by sibling plans of this phase with no SUMMARY yet; requirements.ready-ids blocks it, so it is not marked here

coverage:
  - id: D1
    description: "make informe builds the whole report: 14 findings (5 flagged unfavorable) from fact placeholders, the 25-question table with links, method block, Ejercicio 1 and 2 with all 31 figure cards, 6.9 MB"
    requirement: "DELIV-02"
    verification:
      - kind: integration
        ref: "task 1 automated verify (INFORME_FULL_OK 6880356) and analysis/tests/test_informe.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Build refuses to run on unchecked question texts, unconfirmed answering sections, a drifted fragment number, a typed number in the generated text, or a dangling internal link"
    requirement: "DELIV-02"
    verification:
      - kind: unit
        ref: "analysis/tests/test_informe.py#test_build_stops_when_the_questions_were_not_checked_and_names_the_pdf"
        status: pass
      - kind: unit
        ref: "analysis/tests/test_informe.py#test_build_with_a_drifted_pin_stops_and_names_the_phrase"
        status: pass
    human_judgment: false
  - id: D3
    description: "Glossary annex from DECISIONS.md and jargon links: 154 links resolving to 65 annex entries, no unlinked ID left outside code, unknown IDs stop the build"
    requirement: "DELIV-02"
    verification:
      - kind: integration
        ref: "task 2 automated verify (JARGON_LINKED 154, SOURCES_UNTOUCHED)"
        status: pass
      - kind: unit
        ref: "analysis/tests/test_informe.py#test_every_jargon_id_of_the_real_fragments_resolves_in_the_real_decisions_file"
        status: pass
    human_judgment: false
  - id: D4
    description: "Presenter-script annex via --notes (D-06 fallback)"
    requirement: "DELIV-02"
    verification:
      - kind: unit
        ref: "analysis/tests/test_informe.py#test_build_with_notes_appends_the_script_annex_without_clashing_ids"
        status: pass
    human_judgment: false
  - id: D5
    description: "The wording of the summary of findings states the unfavorable results plainly and makes no ROI, 'mejor' or scannable-QR claim"
    requirement: "DELIV-02"
    verification:
      - kind: unit
        ref: "analysis/tests/test_informe.py#test_findings_never_call_the_oja_index_better_nor_claim_roi_or_a_scannable_qr"
        status: pass
    human_judgment: true
    rationale: "A test can only check the absence of forbidden words; whether the Spanish reads faithfully to each fragment's conclusion needs a reader (the section was read once in full at build time)"

duration: 14min
completed: 2026-10-25
status: complete
---

# Phase 6 Plan 09: Whole informe Summary

**`make informe` now builds the full DELIV-02 report: a 14-bullet "Qué encontramos" made only of data-fact numbers with the unfavorable results up front, the 25-question table, the method block, all five fragments under Ejercicio 1 and 2 with 31 figure cards, 154 clickable decision/Pitfall/requirement IDs resolving to a glossary annex generated from DECISIONS.md, and an optional `--notes` presenter-script annex, behind a build that stops on drift, unchecked questions or typed numbers.**

## Performance

- **Duration:** about 14 min (start time was not recorded; estimated from the previous plan's last commit at 23:17 to the final commit at 23:31)
- **Tasks:** 2 (1 auto, 1 tdd)
- **Files:** 2 modified (analysis/informe.py, analysis/tests/test_informe.py; 972 insertions, 57 deletions)
- **Commits:** 3 measured (429a7e1 feat, 4891235 test RED, ebfb25c feat GREEN)

## Accomplishments

- **Whole report.** Fragments 1-3 sit under `<h2 id="ej1">`, 4-5 under `<h2 id="ej2">`, each with its figure cards from FIGURES (31 cards, page 6 924 391 bytes against the 12 000 000 ceiling). `figure_card` embeds a PNG sibling when the SVG exceeds `EMBED_SVG_MAX` (1 500 000); no real figure needs it today.
- **Qué encontramos.** 14 `Finding` templates cover PCA, SOM, Oja, campañas, letras and QR; every number is a `{group.key}` placeholder (62 data-fact spans in the section, 0 typed numbers). Five are flagged "Resultado desfavorable": one SOM region from the fixed rule, stage 2 not robust (5 variants), Hebb 0 % exact recovery even without noise, the Hamming lookup 81,5 % against the pseudo-inverse 69,4 % at noise 0,45, and the 1-pixel shift plus decoding never verified. Each bullet ends with a link to the section it summarizes.
- **Question table and method.** 25 rows with a header row per exercise (id, quoted text with enunciado section, one "Fase N, §a.b" link per anchor); "Cómo trabajamos" states the pre-registered rules guarded by sha256, seeds and permutations from facts, and the rebuild commands.
- **Drift gate and guards.** `build` raises SystemExit, before rendering, when `QUESTIONS_CHECKED_AGAINST_PDF` or `ANSWER_SECTIONS_CHECKED` is not True (message names `docs/Archivo SIATP 42026.pdf`); then runs `facts.check_fragment_numbers` with `pins=facts.DRIFT_PINS` and lists every failing pin; rejects a typed decimal or percentage in the generated front section; and checks that every internal `href="#..."` has a target.
- **Glossary and jargon.** `parse_glossary` reads the 94 entries of DECISIONS.md; `link_jargon` produced 154 links (65 distinct anchors) in the five fragments, with `title` attributes escaped, and no unlinked D-NN, Pitfall or DATA/HOP ID remains outside code and pre. The annex lists only referenced entries (decisions by phase, then Pitfalls, then requirements), each `<dt id>` equal to its anchor.
- **Presenter script.** `--notes PATH` appends `<h2 id="guion">Guion de la presentación</h2>` rendered without the toc extension (no ids, headings demoted, tables in a scroll box); verified with a scratch notes file on the real data.

## Task Commits

1. **Task 1: whole report, findings, question table, method, drift gate** - `429a7e1` (feat)
2. **Task 2 RED: failing tests for glossary, jargon links, notes annex** - `4891235` (test)
3. **Task 2 GREEN: glossary annex, jargon links, `--notes`** - `ebfb25c` (feat)

**Plan metadata:** recorded in the docs commit that follows this file.

## TDD Gate Compliance

`workflow.tdd_mode` is off and the plan type is `execute`, so `gsd check tdd-red-evidence` was not run; the cycle was followed by hand.

- **RED (`4891235`):** 31 new tests failed, the 45 existing ones kept passing. Failure reasons from the run: 22 `AttributeError: module 'informe' has no attribute 'parse_glossary'` (the tests call it or `link_jargon` inside the test body, never in a fixture, so none is a setup error), 8 `TypeError: build() got an unexpected keyword argument 'glossary_path'` and 1 argparse `unrecognized arguments: --notes`. Semantic assessment: every target test executed and failed because the planned API did not exist yet, which is the intended reason; no syntax, collection or unrelated failures.
- **GREEN (`ebfb25c`):** 77 passed in test_informe.py; `make test` 398 passed, 1282 checks, 0 failed.
- **REFACTOR:** none needed.

## Verification

| Check | Result |
|-------|--------|
| Task 1 verify: `make informe` line, INFORME_FULL_OK (size, anchors, figure cards, no typed numbers, at least 8 facts) | pass (6 880 356 bytes at that run, 31 cards) |
| Task 1 and 2 PYTEST_OK | pass (77 tests) |
| Task 2 verify: JARGON_LINKED | pass (154 links, all resolve) |
| SOURCES_UNTOUCHED (`git diff --quiet -- deliverables/ DECISIONS.md`) | pass |
| `grep -c 'id="ej2"'` | 1 |
| `make test` | 398 passed, 1282 checks, 0 failed (342 before this plan) |
| Summary read once in full for the four unfavorable results | pass (one region, not robust, Hebb 0 %, lookup 81,5 % vs 69,4 %) |

## Decisions Made

See `key-decisions` above. The notable one for later plans: `build(..., notes_path=...)` and the `--notes` flag exist, but nothing in the Makefile passes them yet; 06-11 wires `INFORME_FLAGS`, and 06-10/06-12 decide whether the Slides type carries notes or this annex is the delivery of the script.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The leak scan went quadratic on the full page**
- **Found during:** Task 1 (first `make informe` with all 31 figures)
- **Issue:** `_check_page` ran the e-mail regex over the whole page; the base64 data URIs are multi-megabyte runs of `[A-Za-z0-9+/=]` and the pattern rescans such a run from every start position, so the build did not finish in 120 s (with two figures it had been instant).
- **Fix:** the page-level scan now runs on the page with `data:image/...;base64,...` replaced by `data:`; the SVGs were already scanned decoded, so no coverage is lost for them. PNG blobs are not scanned (matplotlib PNGs carry no path; none is embedded today).
- **Files modified:** analysis/informe.py (new `DATA_URI`)
- **Verification:** `make informe` takes under a second; the leak tests (`test_build_stops_on_a_leak`) still pass.
- **Committed in:** 429a7e1

**2. [Rule 2 - Missing critical] Runtime guards behind the T-06-22 mitigation**
- **Found during:** Task 1
- **Issue:** the plan verifies "no typed numbers in the summary" and anchor presence only in the verify script, so a later edit of the findings would pass the build and fail only the verify.
- **Fix:** `build` itself rejects a typed decimal or percentage in the generated front section and any internal `href="#..."` whose target is absent; both are tested.
- **Files modified:** analysis/informe.py, analysis/tests/test_informe.py
- **Committed in:** 429a7e1

**3. [Rule 1 - Bug] `typed_numbers` reported "53,2 %" as "53,2"**
- **Found during:** Task 1 (test of the typed-number guard)
- **Issue:** with the regex copied from the verify (`\d+,\d+|\d+ ?%`) the decimal alternative wins and the percent sign is dropped from the report.
- **Fix:** `TYPED_NUMBER = \d+(?:,\d+)?[  ]?%|\d+,\d+`, a superset of what the verify catches that reports the whole token.
- **Committed in:** 429a7e1

**4. Plan interface adjustments (no behavior change)**
- `questions_checked` defaults to `None` and resolves the manifest flags at call time instead of at definition time (see key-decisions). `figure_card` gained a `png_only` keyword so `Figure.embed == "png"` is honored. The `Finding` dataclass holds the findings so the tests can swap them for fixture ones (`findings=`). The question table has three columns (id, text with section, links).

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 missing critical) plus interface adjustments
**Impact on plan:** all necessary for correctness or for keeping the plan's own guarantees at build time; no scope creep.

## Issues Encountered

- The "Cómo trabajamos" block names `make deliverables`, which does not exist until 06-11 (the plan asked for exactly that sentence). Until 06-11 lands, the sentence points to a target that is not yet in the Makefile.
- The informe has no way to prove that the Spanish of the 14 findings matches each fragment beyond the tests of forbidden words and the fact placeholders; the section was read once in full against the fragments' conclusions (coverage D5, marked for human judgment).

## Known Stubs

None. No placeholder text or empty data source in the files changed.

## Threat Flags

None. The change adds no endpoint, auth path or file access beyond reading versioned repo text; the new `--notes` file is repo text rendered like the fragments (T-06-21, accepted) and the page-level script/home-path/e-mail checks apply to it.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 06-10 (slides) can reuse `notes_section` through `--notes` if the Slides type has no notes (D-06 fallback), and 06-11 must wire `INFORME_FLAGS` and `make deliverables`.
- 06-12 publishes `analysis/results/informe/informe.html` (6.9 MB, under the 16 MB limit).
- No blockers.

---
*Phase: 06-slides-e-informe*
*Completed: 2026-10-25*

## Self-Check: PASSED

- analysis/informe.py and analysis/tests/test_informe.py exist and contain `parse_glossary`, `link_jargon`, `typed_numbers`, `EMBED_SVG_MAX`, `questions_checked`, `--notes`.
- Commits 429a7e1, 4891235 and ebfb25c are ancestors of HEAD; `git rev-list --count 645a243..HEAD` is 3 at the time of writing.
- All acceptance criteria of both tasks re-run after the last commit: INFORME_FULL_OK, JARGON_LINKED, SOURCES_UNTOUCHED, PYTEST_OK, `id="ej2"` count 1; `make test` 398 passed, 1282 checks.
