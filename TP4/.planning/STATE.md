---
gsd_state_version: "1.0"
current_phase: 05
current_phase_name: Hopfield con QR
status: verifying
stopped_at: Completed 05-05-PLAN.md
last_updated: "2026-10-25T02:53:09.577Z"
last_activity: 2026-10-24
last_activity_desc: Phase 05 execution started
progress:
  total_phases: 6
  completed_phases: 3
  total_plans: 33
  completed_plans: 33
  percent: 50
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-21)

**Core value:** Interpretar correctamente los resultados de los métodos no supervisados para tomar decisiones de campaña fundamentadas en evidencia
**Current focus:** Phase 05 — Hopfield con QR

## Current Position

Phase: 05 (Hopfield con QR) — EXECUTING
Plan: 6 of 6
Status: Phase complete — ready for verification
Last activity: 2026-10-24 — Phase 05 execution started

Progress: [█████░░░░░] 50%

## Performance Metrics

**Velocity:**
- Total plans completed: 22
- Average duration: - min
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 8 | - | - |
| 02 | 6 | - | - |
| 4 | 8 | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 02 P03 | 25 min | 3 tasks | 4 files |
| Phase 02 P01 | 4 min | 2 tasks | 6 files |
| Phase 02 P02 | 8min | 3 tasks | 5 files |
| Phase 02 P04 | 4 min | 3 tasks | 5 files |
| Phase 02 P05 | 25 min | 2 tasks | 5 files |
| Phase 02 P06 | 6 min | 3 tasks | 5 files |
| Phase 03 P01 | 10 min | 2 tasks | 8 files |
| Phase 03 P02 | 25 min | 3 tasks | 3 files |
| Phase 03 P03 | 8 min | 2 tasks | 4 files |
| Phase 03 P04 | 8 min | 2 tasks | 3 files |
| Phase 03 P05 | 9 min | 3 tasks | 4 files |
| Phase 03 P06 | 25 min | 2 tasks | 5 files |
| Phase 05 P01 | 46 min | 2 tasks | 8 files |
| Phase 05 P06 | 12 min | 1 tasks | 3 files |
| Phase 05 P02 | 25 min | 2 tasks | 2 files |
| Phase 05 P03 | 70min | 3 tasks | 4 files |
| Phase 05 P04 | 80min | 3 tasks | 3 files |
| Phase 05 P05 | 25min | 3 tasks | 5 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: 6 fases; Oja se pliega con las decisiones de campaña (Phase 3) para respetar la granularidad standard; Hopfield queda en dos fases (letras antes que QR)
- [Roadmap]: Ejercicio 2 (Fases 4-5) depende solo de la Fase 1 y puede intercalarse con el Ejercicio 1
- [Research]: Fijar por escrito la regla de elección de grilla del SOM y el criterio de éxito de Hopfield antes de mirar resultados
- [Research]: Registrar energía, solapamiento y trayectorias desde la primera implementación en C
- [Research]: Selección auditada de variables = conjunto "todas"; las 31 columnas con z-score corren como sensibilidad etiquetada
- [Phase 02]: 02-03: Task 1 answered approve; terms 1-10 of the grid rule committed verbatim, no edits
- [Phase 02]: 02-03: rule commit ea7a0b1 holds rule text, som_select.py and stage-1 series; select_grid has only chosen and no_eligible_grid outcomes (occupancy never relaxed, D-14)
- [Phase 02]: 02-01: step neighborhood uses d2 <= R^2 (D-01), so R = 1 updates the four adjacent cells and not the diagonals; radius clamped to radius_final
- [Phase 02]: 02-01: grid_k 2..32 with no dependency on n (D-07); pick_prototypes reshuffles at every wrap of i % n so k^2 > n repeats samples and never over-reads
- [Phase 02]: 02-02: run_loo clears stale loo CSVs and reports the first failure in (variant, seed, fold) order; read_run also checks sample and neuron numbering
- [Phase 02]: 02-04: Stage 1 under the committed rule chose k = 5 (step) by QE-LOO; tie band holds only k = 5
- [Phase 02]: 02-04: Stage 2 verdict is no robusta (TE > 0,05 in radius0-5, eta0-0.25, eta0-0.9, epochs-50, epochs-520; occupancy passes everywhere); k not re-selected
- [Phase 02]: 02-05: stability SD in stage-1 curves computed from stability.csv (ddof 1, 45 pairs); empty neurons hatched in z planes as well as raw planes; section 5 reads the figure run only, regions and PCA contrast left to 02-06
- [Phase 02]: 02-06: the committed region rule yields one region (R1, 50 creators) on the k = 5 map; reported as is, percentile untouched
- [Phase 02]: 02-06: map layout follows PC1 (R2 0,961, p = 0,001) but not PC2 (R2 0,055, p = 0,267); Mantel grid vs plane rho 0,599
- [Phase 03]: 03-01: Oja example config eta0 0.001 / eta_final 0.0001 / epochs 500 needed no change; pivot average_caption_words for seeds 1-3, eta0 x max|x|^2 = 0.0573
- [Phase 03]: 03-01: Oja orientation (largest-|w| positive, lowest index on tie) lives in C as exported oja_orient; no commits made in this plan per user preference
- [Phase 03]: 03-02: campaign rule terms 1-10 approved as written; rule committed once in a6212e8 with campaigns_select.py and tests (D-07)
- [Phase 03]: 03-02: rule_identity guards the pre-registration: rule text and campaigns_select.py added in one commit, code unchanged since, marker digest equal to that commit's
- [Phase 03]: Oja vs PC1: Python never re-orients a run; all 10 seeds carry the PCA orientation (pivot average_caption_words, abs(cos) >= 0.9999993) — D-02 convention applied in C, only checked in Python; the pivot margin of 0.00275 is the documented limit
- [Phase 03]: 03-04: section 3 answers No to choosing the Oja maximum; the maximum is INF031 (perros, 17062 followers) with the D-02 sign and INF045 (fútbol, 493194 followers) with the opposite sign, and the index correlates -0,879 (Pearson) with followers
- [Phase 03]: 03-04: sign_flipped = 1 in all 10 seeds (C reverses the trained vector to apply D-02); cause not verified, stated as such in section 1
- [Phase 03]: 03-05: football recommendation is profundidad educativa first, descubrimiento second, alcance masivo last, a judgment resting on five stated assumptions, with no outcome claims
- [Phase 03]: 03-05: lists reported as they came out; @makeupconsejos and @vidaperruna sit in the football discovery list by raw topic share and are flagged for a human look, rule untouched
- [Phase 03]: 03-05: make campaigns records rule_commit a6212e89, rule_sha256 and select_sha256 in selection_identity.json; no exact tie occurred so the Oja index never decided a list
- [Phase 03]: 03-06: the synthetic median creator (SYN001) lands at BMU (3, 1), distance 1,329 under the training maximum 3,651, so the drift check says no retraining; it demonstrates the mechanism only
- [Phase 03]: 03-06: the synthetic index is ranked against the 50 training indices without joining them (place 24 of 1..51)
- [Phase 05]: 05-01: hopfield_pinv (C) assembles W = X^T Ginv X via its own malloc'd p x n temp buffer (O(p^2 n + p n^2)) rather than a second caller scratch array; Gram inversion by Gauss-Jordan with partial pivoting, singular below a fixed pivot tolerance
- [Phase 05]: 05-01: analysis/hopfield.py computes fields/energy/is_fixed/margins in float64 throughout (no int64/float64 dtype branch) since N<=2048 magnitudes stay inside float64's exact-integer range for both hebb and pinv
- [Phase 05]: 05-01: pinv config example shipped as a new sibling file neuron/config.json.hopfield_pinv.example (not loaded by any code), following the existing hopfield_capacity.example convention
- [Phase 05]: 05-06: SOURCES fixed explicit tuple of the five real QR filenames under datos/hopfield resolved in this order (what Plan 02 guard hashes and Plans 03-05 index by subset [0,1,2,3,4]); polarity dark(0)=+1/light(255)=-1 documented in meta, display-only (Hebb's W invariant to global flip)
- [Phase 05]: 05-02: D-01/D-02/D-03/D-05 frozen exactly as proposed (literal hypothesis, 11-level 0-0.5 noise grid, 30 trials, seeds 1-10, exact-match success with continuous |m| also reported, Hebb fails <100%/pinv works ==100% at noise 0); user approved verbatim at the Task 1 checkpoint, no edits
- [Phase 05]: 05-02: deliverable RULE_FILE excluded from rule_guard's porcelain-clean set, checked by marker digest only, so Plans 03-05 write result sections outside the markers without a new commit while any edit to the frozen protocol text itself refuses
- [Phase 05]: 05-03: energy_trace.csv has no seed column; the driver captures ONE fixed seed (hopfield_qr_select.SEEDS[0]) per (source, noise) cell, not all 10 - mixing seeds under the same key interleaves independent async sequences and can look non-monotonic even though each run's own energy never rises (caught by the plan's own verify script before commit)
- [Phase 05]: 05-03: Hebb's measured async noise-0 exact recovery is 0% over the five real QR (verdict.json hebb_fails=true, derived from the frozen D-02 rule, matching PITFALLS.md Pitfall 1 independently); max|overlap|=0.86, 69.8% pixels identical in all five, min pairwise Hamming=96 (HOP-04)
- [Phase 05]: 05-04: pinv_works=true measured from the frozen D-02 rule - all five real QR are exact fixed points under pinv at noise 0 (recall.csv/verdict.json), holding 100% exact recovery through noise 0.30 and 97.3% at 0.40, matching PITFALLS.md's prior independent measurement
- [Phase 05]: 05-04: Hamming 1-NN baseline (numpy-only, matched noise grid/k/trials/seeds, independent RNG from neuron/rng.c) tracks pinv closely through noise 0.40 (98.5% vs 97.3%) then diverges faster at 0.45-0.50 - quantitative evidence a trivial lookup nearly matches pinv except at the highest noise, feeding HOP-07's limitations section
- [Phase 05]: 05-05: the Hebb majority attractor differs from every one of the five QR by 71-225 pixels (of 1369), matching mean_final_overlap=0.791 exactly when averaged - confirms it is the single common attractor Hebb's dynamics collapses to regardless of noise or which QR was queried
- [Phase 05]: 05-05: a 1-2 px shift of a stored QR moves 51-54% of its 1369 pixels (more than any i.i.d. noise level tested) and pinv's recovered state lands even FARTHER from the source (75-88%) than the shifted query itself - the by-hand async runner was sanity-checked first to keep an unshifted stored QR fixed (0 flips)
- [Phase 05]: 05-05: the Hamming 1-NN lookup equals or exceeds pinv's exact-recovery rate at the two highest noise levels (81.5% vs 69.4% at 0.45; 16.7% vs 0% at 0.50) - reported honestly as the lookup actually winning, not just tracking closely, sharpening the D-11c equivalence-with-lookup limitation
- [Phase 05]: 05-05: Phase 5 complete - HOP-04 through HOP-07 all marked complete; deliverables/05-hopfield-qr.md has no remaining placeholder sections and the frozen protocol (section 3) is unchanged from the Plan 02 commit

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 2]: 02-REVIEW-DISPOSITION.md deja 11 hallazgos de code review abiertos; cualquier arreglo que toque la regla de grilla (p. ej. WR-01) pasa por /gsd-discuss-phase, no por edición in situ (rule_digest d1c69242…)
- [Phase 2]: 02-VALIDATION.md sigue en draft (auditoría Nyquist sin correr: /gsd-validate-phase 2)
- [Phase 4]: Hopfield síncrono (curso) vs asíncrono (energía monótona): implementar ambos, asíncrono como referencia
- [Phase 5]: Sin verificar la pseudo-inversa bajo ruido alto ni la existencia de un decodificador de QR (HOP-09 está en v2)
- [Phase 6]: Sin verificar el formato de Slides en Artifacts ni si plotly JS corre dentro de Artifacts
- [Phase 5] 05-01: pre-existing CRLF in datos/letters/alphabet_5x5.txt (Phase 4 data file) fails 6 unrelated pytest tests (test_hopfield_select.py, test_letters.py) under this environment's core.autocrlf=input; logged in .planning/phases/05-hopfield-con-qr/deferred-items.md, not fixed (out of 05-01 scope)

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| *(none)* | | | | |

## Session Continuity

Last session: 2026-10-25T02:53:02.113Z
Stopped at: Completed 05-05-PLAN.md
Resume file: None
