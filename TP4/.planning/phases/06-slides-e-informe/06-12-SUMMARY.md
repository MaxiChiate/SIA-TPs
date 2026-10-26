---
phase: 06-slides-e-informe
plan: 12
subsystem: deliverables-publication
tags: [artifacts, slides, informe, publication, waivers, readme, claude-md, deliv-01, deliv-02, deliv-03]

requires:
  - phase: 06-slides-e-informe
    provides: "06-11 make deliverables and reproduction docs; 06-08 question and answer-section flags; 06-09 informe.py; 06-10 slides.py; 06-ARTIFACT-FORMAT.md"
provides:
  - "Published Slides Artifact (24 slides, private) and HTML Artifact for the informe (private), both URLs recorded under Entrega in README.md and CLAUDE.md"
  - "Phase 3 and Phase 2 waivers recorded in CLAUDE.md Pendientes before the final build"
  - "Informe built with the presenter-script annex (INFORME_FLAGS in the Makefile), user-directed"
affects: [phase-verification]

actuals:
  tokens: 1600
  tasks: 3
  commits: 3
plan_head_before: 24f432f16bea706ac52c226984502b14eb2afee0
plan_head_after: 559848a3a7788776707d085517ade4ca53c88fbc

tech-stack:
  added: []
  patterns:
    - "Publication through the top-level session: executors have no Artifact tool, so the Slides type is filled from analysis/results/slides with an asset map (not versioned) and the informe file is published as HTML"

key-files:
  created: []
  modified:
    - CLAUDE.md
    - README.md
    - Makefile

key-decisions:
  - "Fase 3: p3-waive. The campaign numbers (slides E1-10 to E1-13, fragment 03 sections 5 and 6) are published with Phase 3 unverified; the waiver is a dated line in CLAUDE.md Pendientes"
  - "Fase 2: p2-waive. The SOM numbers and the D-03 pre-registration claim are published with the 11 review findings open; the waiver naming the IDs is a dated line in CLAUDE.md Pendientes; no Phase 2 file was edited"
  - "The informe carries the presenter script as an annex: INFORME_FLAGS := --notes analysis/results/slides/notes.md (user-directed, replaces the empty value 06-11 left)"
  - "Both Artifacts stay private; the deck is delivered as its exported PDF (not versioned in docs/, D-14); sharing the informe link is the user's call from the Share menu"

requirements-completed: [DELIV-01, DELIV-02, DELIV-03]

coverage:
  - id: D1
    description: "Phase 3 and Phase 2 open items settled by the user's decision before the numbers were frozen; final build guarded and byte-stable, drift check passing, make test green"
    requirement: "DELIV-03"
    verification:
      - kind: integration
        ref: "task 2 automated verify: QUESTIONS_CHECKED_OK, PHASE3_SETTLED_OK testing, PHASE2_SETTLED_OK, PHASE2_FILES_UNTOUCHED, FINAL_BUILD_OK, MAKE_TEST_OK (473 passed)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Slides published as a Slides Artifact with one section per exercise and presenter notes; informe published as an HTML Artifact (not Docs); neither exported to PDF/Word in the repo"
    requirement: "DELIV-01"
    verification:
      - kind: integration
        ref: "analysis/tests/test_repro_docs.py (no slides export in docs/, no informe export described) inside make test: 473 passed"
        status: pass
    human_judgment: true
    rationale: "The published pages exist only on claude.ai; the user stepped through them and replied 'published' with both URLs"
  - id: D3
    description: "README.md and CLAUDE.md each hold one '- Slides: https://' line and one '- Informe: https://' line under Entrega"
    requirement: "DELIV-03"
    verification:
      - kind: integration
        ref: "grep count per file (1 and 1) and make test: 473 passed"
        status: pass
    human_judgment: false

duration: not recorded (spans a decision checkpoint and a human-action checkpoint)
completed: 2026-10-26
status: complete
---

# Phase 6 Plan 12: Publish Slides and Informe Summary

**The 24-slide deck and the informe are published as private Artifacts (Slides type and HTML), built byte-stably from the final results with the Phase 3 and Phase 2 open items waived and recorded, and both URLs are listed under Entrega in README.md and CLAUDE.md.**

## Published Artifacts

- Slides: https://claude.ai/artifact/9YjSxsDcVYSwvnXaD5JVy1
- Informe: https://claude.ai/artifact/32SjYXD12gS2Lh6vY22jyM

Both are private. The deck's exported PDF is what gets submitted; whether to share the informe link is the user's call from the Share menu (a step only the owner can do).

## Task 1 checkpoint log (decision, recorded verbatim)

The user answered **"Fase 3: p3-waive"** and **"Fase 2: p2-waive"**.

State at build time:

- `03-VERIFICATION.md` status: `human_needed` (5/5 must-haves, 2 human items).
- `03-UAT.md` status: `testing`.
- `02-REVIEW-DISPOSITION.md`: all 11 findings open: WR-01, WR-02, WR-03, WR-04, IN-01, IN-02, IN-03, IN-04, IN-05, IN-06, IN-07. The five touching the grid rule and its guard are WR-01 to WR-04 and IN-01.

Both waiver lines, dated 2026-10-26, are in CLAUDE.md Pendientes (`- Fase 3 (decisión 06-12): publicado con la Fase 3 sin verificar ...` and `- Fase 2 (decisión 06-12): publicado con hallazgos abiertos: ...`). No Phase 2 file was edited.

## Task 2: final build (commit 4347076)

`plan_head_before` 24f432f16bea706ac52c226984502b14eb2afee0. All guards printed: QUESTIONS_CHECKED_OK, PHASE3_SETTLED_OK (testing, waived), PHASE2_SETTLED_OK (waived), PHASE2_FILES_UNTOUCHED, FINAL_BUILD_OK (two `make deliverables` runs identical, DRIFT_OK), MAKE_TEST_OK (473 passed).

## Task 3: publication by the top-level session

- Created the Slides artifact from the Slides type and uploaded the 15 PNGs in `analysis/results/slides/assets/` as assets. The asset map `analysis/results/slides/asset_map.json` is not versioned; the deck was rebuilt with `.venv/bin/python analysis/slides.py --asset-map analysis/results/slides/asset_map.json`. It then published `project/deck.json` plus the 24 `project/slides/*.html`; the slide files now carry `/_blob` srcs.
- After commit 4347076 it rebuilt the informe from the clean tree with `.venv/bin/python analysis/informe.py --notes analysis/results/slides/notes.md` (footer "Generado desde commit 4347076."), `notes.md` byte-identical (sha256 6febb9a9...), and published `informe.html` as an HTML Artifact.
- Published hashes:
  - `informe.html` sha256 `73535142c19150479fc6fb3c0efd9d4dece048bf2f6a9a6e75745293e219c24c`, 6,938,280 bytes.
  - Root `deck.json` sha256 `d9a8c6d55a2a9602f08b49780e2cd4d0f2d24e33a1cd4779ab4ee94b8d1374bf`.
  - `project/deck.json` sha256 `c6a74fc7d6ab56bc96056e9461e927166009015b63c1e99b623f6b1d0458e1bc`.
- The user replied `published` with both URLs.

## Commits

| Commit | What |
| ------ | ---- |
| `4347076` | final build with Phase 3 and Phase 2 waivers recorded and presenter-script annex in the informe (CLAUDE.md, Makefile, README.md) |
| `c948341` | both URLs under Entrega in README.md and CLAUDE.md, privacy and PDF line |
| `559848a` | replaced the stale "Publicar" Pendientes item in CLAUDE.md with the share step |

## Deviations from Plan

### User-directed

**1. [User decision] Presenter-script annex in the informe**
- **Found during:** Task 2 checkpoint.
- **Change:** `INFORME_FLAGS := --notes analysis/results/slides/notes.md` in the Makefile (06-11 had left it empty), with README.md and CLAUDE.md sentences about the annex. `make informe` alone still builds the informe without it.
- **Files modified:** Makefile, README.md, CLAUDE.md. **Commit:** 4347076.

### Auto-fixed Issues

**2. [Rule 1 - Bug] Stale "Publicar" item in CLAUDE.md Pendientes**
- **Found during:** Task 3 verification.
- **Issue:** After the URLs were recorded, Pendientes still said the slides and the informe were to be published.
- **Fix:** Replaced it with the remaining share step. A first wording mentioned a PDF export near "informe" and tripped `check_no_informe_export` in `make test`; reworded, 473 passed.
- **Files modified:** CLAUDE.md. **Commit:** 559848a.

## Auth gates

None.

## Known Stubs

None.

## Threat Flags

None. Both Artifacts are private (T-06-30); the Phase 3 and Phase 2 decisions were taken at a blocking-human checkpoint and recorded (T-06-31, T-06-34).

## Residual risk (waived, recorded)

The published campaign numbers rest on a Phase 3 whose UAT is still in `testing`, and the SOM numbers rest on a rule whose 11 review findings are open. If either changes a result, regenerate with `make deliverables`, update `DECISIONS.md` and CLAUDE.md, and republish to the same URL.

## Self-Check: PASSED

- README.md and CLAUDE.md: FOUND, each with one `- Slides: https://` and one `- Informe: https://` line.
- No file under docs/ matches `Slides_TP4*`; no `.pptx`, `.docx`, slides PDF or informe PDF tracked in git.
- Commits 4347076, c948341, 559848a: all ancestors of HEAD; measured count from the ledger base is 3.
- `make test`: 473 passed, 1282 checks, 0 failed.
