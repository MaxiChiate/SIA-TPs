---
phase: 05-hopfield-con-qr
plan: 02
subsystem: pre-registration
tags: [qr, hopfield, guard, pre-registration, hop-05, d-01, d-02]
dependency-graph:
  requires:
    - scripts/qr.py (05-06)
    - datos/hopfield/*.png (five QR, committed before this phase)
  provides:
    - deliverables/05-hopfield-qr.md section 3 (frozen protocol between regla:inicio/regla:fin)
    - analysis/hopfield_qr_select.py (rule_identity, require_same_rule, report, NOISE_LEVELS, TRIALS, SEEDS, HEBB_FAIL_RECALL_AT_ZERO, PINV_WORK_RECALL_AT_ZERO)
  affects:
    - 05-03..05-05 (drivers must call hopfield_qr_select.rule_identity before any QR network run)
tech-stack:
  added: []
  patterns:
    - mirrors analysis/hopfield_select.py rule_identity exactly, but splits the guarded set in two
      tiers: porcelain-clean (SELECT_FILE, QR_FILE, PNG_FILES) vs marker-digest-only (RULE_FILE)
key-files:
  created:
    - deliverables/05-hopfield-qr.md
    - analysis/hopfield_qr_select.py
  modified: []
decisions:
  - "D-01/D-02/D-03/D-05 frozen exactly as proposed in 05-CONTEXT.md: literal hypothesis, 11-level 0-0.5 noise grid (30 trials, seeds 1-10), exact 1369-pixel success criterion with continuous |m| also reported, and the two numeric verdict thresholds (Hebb fails if exact recovery at noise 0 < 100%, pinv works if == 100%). User approved verbatim at the Task 1 checkpoint (resumed as 'approved' by the orchestrator); no edits requested."
  - "The deliverable (RULE_FILE) is deliberately excluded from rule_guard's porcelain-clean set; only its marker-text digest is checked against the rule commit. This lets Plans 03-05 write result sections (1, 2, 4-7) outside the markers without any new commit or guard failure, while any edit to the frozen protocol text itself changes the digest and refuses (D-01)."
  - "PNG_FILES is a literal tuple of the five datos/hopfield/*.png paths in scripts/qr.py SOURCES order (not imported from qr.py), so the guard's own constant is self-contained and does not depend on qr.py internals beyond the file path."
metrics:
  duration: 25 min
  completed: 2026-10-24
actuals:
  tokens: 4600
  tasks: 2
  commits: 1
  plan_head_before: e9314916b95b0402b55b238139714d80613e47f0
  plan_head_after: 03a2cb37628155015a9343af5cc2ba39cdbc48fa
status: complete
---

# Phase 5 Plan 02: Freeze the QR experiment protocol and verdict thresholds Summary

Pre-registered the QR experiment protocol (hypothesis, noise grid, success criterion, and the two numeric verdict thresholds for "Hebb failed" / "pinv works") between commit-guarded markers in `deliverables/05-hopfield-qr.md`, with a sha256 guard in `analysis/hopfield_qr_select.py` that freezes the protocol text, itself, `scripts/qr.py` and the five QR PNGs together — before any network ever runs on the QR.

## What Was Built

- **Task 1 (checkpoint:decision, blocking-human):** resolved in a prior dispatch of this plan, which returned the checkpoint without committing anything. The orchestrator relayed the user's explicit decision — "approved" — to freeze the protocol, noise grid, success criterion and verdict thresholds exactly as proposed in `05-CONTEXT.md` D-01/D-02/D-03/D-05. This run proceeded straight to Task 2 on that basis; no further human interaction occurred.
- **`deliverables/05-hopfield-qr.md`** — new file. Intro line matching the Phase 4 pattern (sections 1/2/4+ written after the runs, section 3 fixed before). Placeholder headings for sections 1 (algoritmo y salidas), 2 (los 5 QR y su preparación), 4 (Hebb), 5 (pseudo-inversa vs Hamming), 6 (limitaciones), 7 (cómo reproducir) — all marked `(Se completa en el Plan ...)`, no results written. Section 3 contains exactly one `<!-- regla:inicio -->` / `<!-- regla:fin -->` pair with 13 bullets in Spanish (one bolded concept per bullet, mirroring `deliverables/04-hopfield-letras.md` section 3 style): Hipótesis (literal D-01 string), Patrones, Reglas de la red (Hebb + pinv with non-zero diagonal, D-07), Dinámica, Modelo de ruido (D-04), Grilla de ruido (D-05, literal levels 0 to 0,50), Éxito (D-03), Umbrales de veredicto (D-02, both thresholds spelled out at 100%), Línea base de Hamming (D-08), Energía e iteraciones (D-09), Limitaciones a demostrar (D-10/D-11), Guardia, Divulgación (honest disclosure that PITFALLS.md Pitfall 1 already measured the Hebb-fails/pinv-works outcome before this protocol).
- **`analysis/hopfield_qr_select.py`** — new file, mirroring `analysis/hopfield_select.py`. Design constants: `HYPOTHESIS` (literal D-01 string), `NOISE_LEVELS` (11-tuple, `round(k * 0.05, 2)` for k in 0..10, giving 0.0..0.5), `TRIALS = 30`, `SEEDS = tuple(range(1, 11))`, `UPDATES = ("async", "sync")`, `SUBSET = (0, 1, 2, 3, 4)`, `SUCCESS` string (D-03), `HEBB_FAIL_RECALL_AT_ZERO = 1.0` / `PINV_WORK_RECALL_AT_ZERO = 1.0` (D-02, both reference the noise-0 recovery rate with the comparison operator spelled out in `report()`), `HAMMING_TIE_BREAK = "lowest index"` (D-08). `RULE_FILE`/`SELECT_FILE`/`QR_FILE`/`PNG_FILES` constants (the five PNGs as a literal tuple in `scripts/qr.py` SOURCES order). `report()` prints the frozen facts only (hypothesis, noise grid, trials, seeds, updates, subset, success, both verdict-threshold lines worded legibly, Hamming tie-break, and the five PNG sha256) — no network quantity is computed. `rule_identity(repo_dir)` reuses `som_select.rule_guard`/`rule_digest`: `rule_guard` (porcelain-clean) runs over exactly `[SELECT_FILE, QR_FILE, *PNG_FILES]` — `RULE_FILE` is deliberately excluded from that porcelain-clean set; separately requires `RULE_FILE` and `SELECT_FILE` added in the same commit, `QR_FILE` and the five PNGs in that commit or an ancestor, nothing guarded changed after the rule commit, and the deliverable's current marker digest equal to the digest recorded at the rule commit (via `git show {commit}:RULE_FILE`). Returns `{rule_commit, rule_sha256, select_sha256, qr_sha256, png_sha256}`. `require_same_rule(selection_path, repo_dir)` for downstream drivers (Plans 03-05) to pin against a recorded identity JSON. `main()` dispatches `report` / `identity` subcommands.
- Both files committed together in a single commit (`03a2cb3`), confirming `scripts/qr.py` and the five `datos/hopfield/*.png` were already committed ancestors (from Plan 06 and earlier), so `rule_identity` passes immediately after the commit.

## Verification Results

All four automated `<verify>` checks from the plan passed:
- `MARKERS_OK` — exactly one `regla:inicio` and one `regla:fin` in the deliverable.
- `PROTOCOL_TEXT_OK` — the literal hypothesis phrase and the `0.5` upper noise bound are both present.
- `REPORT_OK` — `.venv/bin/python analysis/hopfield_qr_select.py report` prints the hypothesis, `0.50` in the noise grid, the trial count `30`, the Hebb-fails line (`< 100%`), and the pinv-works line (`== 100%`).
- `GUARD_PASSES_AFTER_COMMIT` — after the commit, `identity` exits 0 and both files are tracked by git.

Additionally verified (not in the plan's automated checks, but load-bearing for the design's key claim): `identity` correctly refuses *before* the commit (porcelain-clean guard trips), and after the commit it keeps exiting 0 even with an uncommitted edit appended to the deliverable *outside* the markers — confirming the split between the porcelain-clean set (code + PNGs) and the marker-digest-only check (the deliverable) behaves exactly as designed, so Plans 03-05 can write result sections without a new commit.

## Deviations from Plan

None — plan executed exactly as written, using the protocol, grid and thresholds the user approved verbatim at the Task 1 checkpoint (no edits requested).

## Known Stubs

None. The placeholder headings in `deliverables/05-hopfield-qr.md` (sections 1, 2, 4, 5, 6, 7) are explicitly out of this plan's scope per the plan's own `<action>` spec ("results do not go between the markers... to be written in Plan 05") and are marked as such in the text, not silently empty.

## Threat Flags

None — the two threats in this plan's threat model (T-05-04 protocol/PNG tampering, T-05-05 guard bypass) are exactly what `rule_identity` mitigates; no new surface was introduced beyond what the plan anticipated.

## Self-Check: PASSED

- FOUND: deliverables/05-hopfield-qr.md
- FOUND: analysis/hopfield_qr_select.py
- FOUND commit 03a2cb3 (docs(05-02): freeze the QR experiment protocol and verdict thresholds) as ancestor of HEAD
