---
gsd_state_version: "1.0"
current_phase: 3
current_phase_name: Oja y decisiones de campaña
status: planning
stopped_at: Phase 3 context gathered
last_updated: "2026-10-21T23:58:18.066Z"
last_activity: 2026-10-21
last_activity_desc: Phase 02 complete, transitioned to Phase 3
progress:
  total_phases: 6
  completed_phases: 2
  total_plans: 14
  completed_plans: 14
  percent: 33
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-21)

**Core value:** Interpretar correctamente los resultados de los métodos no supervisados para tomar decisiones de campaña fundamentadas en evidencia
**Current focus:** Phase 3 — Oja y decisiones de campaña

## Current Position

Phase: 3 — Oja y decisiones de campaña
Plan: Not started
Status: Ready to plan
Last activity: 2026-10-21 — Phase 02 complete, transitioned to Phase 3

Progress: [███░░░░░░░] 33%

## Performance Metrics

**Velocity:**
- Total plans completed: 14
- Average duration: - min
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 8 | - | - |
| 02 | 6 | - | - |

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

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 2]: 02-REVIEW-DISPOSITION.md deja 11 hallazgos de code review abiertos; cualquier arreglo que toque la regla de grilla (p. ej. WR-01) pasa por /gsd-discuss-phase, no por edición in situ (rule_digest d1c69242…)
- [Phase 2]: 02-VALIDATION.md sigue en draft (auditoría Nyquist sin correr: /gsd-validate-phase 2)
- [Phase 4]: Hopfield síncrono (curso) vs asíncrono (energía monótona): implementar ambos, asíncrono como referencia
- [Phase 5]: Sin verificar la pseudo-inversa bajo ruido alto ni la existencia de un decodificador de QR (HOP-09 está en v2)
- [Phase 6]: Sin verificar el formato de Slides en Artifacts ni si plotly JS corre dentro de Artifacts

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| *(none)* | | | | |

## Session Continuity

Last session: 2026-10-21T23:58:18.009Z
Stopped at: Phase 3 context gathered
Resume file: .planning/phases/03-oja-y-decisiones-de-campa-a/03-CONTEXT.md
