---
phase: 06-slides-e-informe
plan: 03
subsystem: docs
tags: [decisions, glossary, deliverables, spanish]

requires:
  - phase: 01-fundaci-n-auditor-a-de-datos-y-pca
    provides: "01-CONTEXT.md decisions F1 D-01..D-13"
  - phase: 02-kohonen-som
    provides: "02-CONTEXT.md decisions F2 D-01..D-15"
  - phase: 03-oja-y-decisiones-de-campa-a
    provides: "03-CONTEXT.md decisions F3 D-01..D-19"
  - phase: 04-hopfield-n-cleo-y-letras
    provides: "04-CONTEXT.md decisions F4 D-01..D-06 and D-04b"
  - phase: 05-hopfield-con-qr
    provides: "05-CONTEXT.md decisions F5 D-01..D-11"
provides:
  - "DECISIONS.md at the TP4 root: 6 Key Decisions, 80 phase decisions (F1-F6), 6 cited pitfalls and 8 cited requirement IDs, each with Que / Por que / Donde"
  - "Fixed heading grammar that the informe glossary parser (06-09) reads"
affects: [06-09, 06-11, 06-12]

actuals:
  tokens: 16100
  tasks: 2
  commits: 2
plan_head_before: 1c195db471dd19ce42a7e65bdb0f5c2a368ba7bc
plan_head_after: b6400b4a674fe05a61beb1f0eadb37cec1310a87

tech-stack:
  added: []
  patterns:
    - "One heading per decision: '### F<n> D-<nn> — ', '### KD-<n> — ', '### Pitfall <n> — ', '### <REQ-ID> — '"
    - "Every entry links its CONTEXT.md and, when applied, the fragment section"

key-files:
  created:
    - DECISIONS.md
  modified: []

key-decisions:
  - "F4 D-04b gets its own entry (its CONTEXT.md lists it as a separate decision); F5 D-11 names its sub-items D-11a..D-11d inside the parent entry"
  - "Each decision is quoted from its CONTEXT.md line; no wording of a locked decision was softened or re-scoped"

requirements-completed: [DELIV-03, DELIV-02]

coverage:
  - id: D1
    description: "DECISIONS.md consolidates every D-xx decision of Phases 1-6 and the 6 PROJECT.md Key Decisions with Que / Por que / Donde and links to CONTEXT.md and fragments"
    requirement: "DELIV-03"
    verification:
      - kind: other
        ref: "task 2 automated check (DECISIONS_COVER_OK 80): heading ID set equals the CONTEXT.md D-ID set for phases 1-6"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every Pitfall N and requirement ID cited in deliverables/0X-*.md has a DECISIONS.md heading, so no glossary link dangles"
    requirement: "DELIV-02"
    verification:
      - kind: other
        ref: "task 2 automated check: pits <= headings and reqs <= headings"
        status: pass
    human_judgment: false
  - id: D3
    description: "Fidelity of each Que line to its CONTEXT.md line and Spanish rioplatense prose"
    requirement: "DELIV-03"
    verification: []
    human_judgment: true
    rationale: "No test can assert that a paraphrase did not soften a locked decision; a reader has to compare against the CONTEXT.md lines"

duration: 55min
completed: 2026-10-25
status: complete
---

# Phase 6 Plan 03: DECISIONS.md Summary

**DECISIONS.md at the TP4 root: 80 decisions of Phases 1-6, the 6 Key Decisions, 6 cited pitfalls and 8 cited requirement IDs, each with Que / Por que / Donde and a fixed heading grammar the informe glossary parser reads.**

## Performance

- **Duration:** 55 min
- **Started:** 2026-10-25T22:38:47Z
- **Completed:** 2026-10-25T23:34:00Z
- **Tasks:** 2
- **Files modified:** 1 (created)

## Accomplishments

- `DECISIONS.md` with `# Decisiones del TP4`, `## Índice`, `## Decisiones del proyecto` (KD-1 to KD-6, table order), `## Fase 1` to `## Fase 6`, `## Pitfalls citados en los fragmentos` and `## Requisitos citados en los fragmentos`.
- The `### F<n> D-<nn> — ` heading set equals the D-ID set of every phase's CONTEXT.md: F1 13, F2 15, F3 19, F4 7 (D-04b as its own entry), F5 11, F6 15 (80 total).
- Pitfalls 1, 8, 14, 15, 22, 26 and requirement IDs DATA-01, DATA-03, DATA-05, HOP-03 to HOP-07 all have an entry, so every jargon link in the informe can resolve.
- All relative links in the file resolve to existing files.

## Task Commits

1. **Task 1: skeleton, Key Decisions and Phases 1-3** - `845b335` (docs)
2. **Task 2: Phases 4-6, pitfalls and requirement IDs** - `b6400b4` (docs)

**Plan metadata:** recorded in the final docs commit for this plan.

## Files Created/Modified

- `DECISIONS.md` - consolidated decisions and the glossary source of the informe

## Decisions Made

- F4 D-04b has its own heading right after F4 D-04, as its CONTEXT.md lists it separately.
- F5 D-11 names D-11a to D-11d in its Que line. The CONTEXT.md labels no sub-items; it lists three empirical limitations (correlation, shifts, lookup) and closes by saying the QR's own error correction stays in text only (F5 D-10). The entry states that D-11d is that fourth point and that the CONTEXT does not letter it.
- Heading grammar uses an em dash with one space on each side, as 06-09 expects.

## Deviations from Plan

None - plan executed exactly as written.

Two wording choices worth knowing (not deviations): the F6 D-06 and D-14 "Por que" lines cite what the later Slides format probe found (`06-ARTIFACT-FORMAT.md`: notes supported but not private; the user will submit the exported PDF), without changing the CONTEXT.md wording in the Que line. The F3 D-06 Que line contains the word «mejor» only to say it is not used for the Oja index; the other hit is "la mejor seed" in F2 D-08.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None.

## Threat Flags

None. The file contains course data only (no paths, emails or credentials).

## Next Phase Readiness

- 06-09 can parse the headings (`^### F[1-6] D-\d+[a-z]? — `) and link `D-NN`, `Pitfall N` and requirement IDs. A lettered ID with no entry of its own (`D-11a`) links to its parent (`F5 D-11`).
- 06-11 can add the test for DECISIONS.md; the verify one-liners of this plan are a ready base for it.

## Self-Check: PASSED

- FOUND: DECISIONS.md
- FOUND: 845b335, b6400b4 (ancestors of HEAD)
- DECISIONS_COVER_OK 80 re-run after the last edit
