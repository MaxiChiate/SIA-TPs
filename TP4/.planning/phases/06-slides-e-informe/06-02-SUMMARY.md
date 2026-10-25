---
phase: 06-slides-e-informe
plan: 02
subsystem: deliverables
tags: [artifacts, slides, probe, png, speaker-notes]

requires:
  - phase: 06-slides-e-informe
    provides: "06-RESEARCH.md assumptions A1, A2, A8 about the Slides Artifact type (plan 02 has no depends_on)"
provides:
  - "06-ARTIFACT-FORMAT.md: observed Slides Artifact contract (14 frontmatter keys, 8 sections) for 06-05 and 06-10"
  - "Private smoke deck 'Prueba de formato TP4' at https://claude.ai/artifact/3J6BXCDx8XMprfLBKE5Y3s"
affects: [06-05, 06-09, 06-10, 06-11, 06-12]

actuals:
  tokens: 2044
  tasks: 2
  commits: 1
plan_head_before: 98ed44424976416b1974c35a0cd26d9af71eee98
plan_head_after: cddd44651f4dc491bdc1c6b3a079ea1caf9cfed8

tech-stack:
  added: []
  patterns:
    - "Slide = project/slides/<id>.html with one <section>; order in project/deck.json (v4)"
    - "Slide figures are PNG assets referenced by /_blob/<id>; never SVG with raster <image>"

key-files:
  created:
    - .planning/phases/06-slides-e-informe/06-ARTIFACT-FORMAT.md
  modified: []

key-decisions:
  - "Slide figures must be PNG uploaded as assets: uploaded SVGs lose their embedded raster payloads (the SOM map rendered striped); affects 06-05 (slide figure variant outputs PNG) and 06-10"
  - "share_mode = the exported presentation PDF is submitted; the artifact stays private, so no share link is needed"
  - "Speaker notes work via <aside> but are visible to anyone who opens the deck; keep the D-06 fallback (analysis/results/slides/notes.md + informe annex 'Guion de la presentación') as well"
  - "Canvas is fixed 1920x1080 (figure area about 1664x630 below a 72 px title); final deck is new versions of one artifact (redeploy keeps the URL)"

patterns-established:
  - "Executors have no Artifact tool: every upload and publish is a top-level session step"

requirements-completed: [DELIV-01]

coverage:
  - id: D1
    description: "06-ARTIFACT-FORMAT.md records the Slides Artifact contract from a real probe, with all 14 frontmatter keys and sections 1-8"
    requirement: "DELIV-01"
    verification:
      - kind: other
        ref: "Task 2 automated check (.venv/bin/python frontmatter/section assertions) prints FORMAT_DOC_OK"
        status: pass
    human_judgment: false
  - id: D2
    description: "Smoke deck published privately and the embedding, notes and PDF export behaviour observed by the user"
    requirement: "DELIV-01"
    verification: []
    human_judgment: true
    rationale: "Visual rendering of the published deck was judged by the user; no test asserts it"

duration: 5min
completed: 2026-10-25
status: complete
---

# Phase 6 Plan 02: Slides Artifact format probe Summary

**Probed the real Slides Artifact type with a 2-slide smoke deck and recorded its contract (1920x1080 canvas, one-section-per-file, PNG-only figures, `<aside>` notes, PDF as the submitted deliverable) in 06-ARTIFACT-FORMAT.md.**

## Performance

- **Duration:** 5 min (continuation agent; Task 1 ran in the top-level session)
- **Started:** 2026-10-25T22:35:00Z
- **Completed:** 2026-10-25T22:41:00Z
- **Tasks:** 2 (Task 1 human-action checkpoint, Task 2 auto)
- **Files modified:** 1 (created)

## Accomplishments

- Closed the STATE.md blocker "Sin verificar el formato de Slides en Artifacts" with an observed answer, not an assumption.
- Found that uploaded SVGs lose embedded raster `<image>` payloads (the SOM map showed striped), so every slide figure must be a PNG asset. This sets the rule for 06-05 and 06-10.
- Recorded the content contract (`deck.json` v4 plus one `<section>` file per slide, closed inline-CSS subset, 24 px minimum font), the fixed canvas and figure area, redeploy behaviour (same URL) and private-by-default visibility.
- Recorded `share_mode`: the exported presentation PDF is submitted and the artifact stays private. PDF export was verified by the user ("PDF extraction is perfect").

## Task Commits

1. **Task 1: Top-level session probes the Slides Artifact type** - no commit (human-action checkpoint, done by the top-level session; the file it wrote was committed in Task 2)
2. **Task 2: Check and commit the recorded Slides contract** - `cddd446` (docs)

**Plan metadata:** recorded in the final docs commit (SUMMARY, STATE, ROADMAP).

## Files Created/Modified

- `.planning/phases/06-slides-e-informe/06-ARTIFACT-FORMAT.md` - Slides Artifact contract (frontmatter keys read by 06-05 and 06-10, eight numbered sections)

## Decisions Made

- PNG-only slide figures (see key-decisions): uploaded SVG keeps 4 `<image>` tags but 0 `data:image` payloads, so raster cells are lost.
- `share_mode` is the PDF submission; 06-11 and 06-12 should add the exported PDF to the deliverables and keep the artifact private.
- Notes are not presenter-only, so the D-06 fallback (notes.md and informe annex) stays recommended even though `notes_supported` is true. This is a recommendation for 06-09/06-10, not a forced fallback.

## Deviations from Plan

None - plan executed exactly as written. Task 1 was the planned human-action checkpoint; its answers were not edited. One observation for the record: the plan's smoke test asked for a `data:` URI mode, but the type forbids it, so that mode was not tried (documented in section 3 of the format file). The user's note that the PDF includes notes was not checked in the probe.

## Authentication Gates

None. The checkpoint in Task 1 was a planned human-action step (the executor lacks the Artifact tool), not an auth gate.

## Issues Encountered

- `gsd_run` is not a shell function in this environment; STATE/ROADMAP queries were run through `node ~/.claude/gsd-core/bin/gsd-tools.cjs` instead. No effect on results.
- `requirements.ready-ids` reports DELIV-01 as blocked: six sibling plans (06-05, 06-06, 06-07, 06-10, 06-11, 06-12) also declare it and have no SUMMARY yet, so it was not marked complete here (shared-ID gate, #2388).

## Threat Flags

None. T-06-04 mitigated: the smoke deck stayed at the default private visibility. T-06-05 accepted: it holds only the aggregate SOM map and a cover title.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 06-05 can read `figure_area` (about 1664x630, or 816x454 per figure when two sit side by side) and must make its slide figure variant produce PNG.
- 06-10 can read `content_unit`, `image_embed: relative-file`, `notes_supported: true` and the `asset_map.json` option for blob URLs.
- Open for 06-09/06-10: whether the PDF export carries the `<aside>` notes (not checked), and the PPTX export (not exercised, not on the critical path).

---
*Phase: 06-slides-e-informe*
*Completed: 2026-10-25*

## Self-Check: PASSED
