# Phase 1: Fundación, auditoría de datos y PCA - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-20
**Phase:** 1-Fundación, auditoría de datos y PCA
**Areas discussed:** Parser JSON en C, Regla de variables, Transformaciones y z-score, Criterio de PCA, Modelo trivial e2e, Layout y entorno

---

## Parser JSON en C
| Option | Selected |
|--------|----------|
| cJSON vendored | ✓ |
| Parser plano de TP3 | |
| Plano de TP3 extendido | |

Validación: error y sale ante claves desconocidas/faltantes ✓ (vs. defaults para opcionales).

## Regla de variables
Conjunto: quitar las 5 redundantes ✓ (vs. dejar 31, vs. ponderar). Casi-redundantes: solo documentar ✓ (usuario aclaró: `estimated_argentina_reach` y pares |r|>0.9 con followers se documentan; `total_engagement_per_1000` se elimina con las redundantes). Qué sacar de topics/content: regla fija por grupo ✓.

## Transformaciones y z-score
z-score directo ✓ (vs. log1p, vs. winsorizar).

## Criterio de PCA
Matriz de correlación + regla (80% y Kaiser) fijada antes ✓. Rol: diagnóstico, SOM/Oja sobre variables completas ✓.

## Modelo trivial e2e
Stubs deterministas por modelo ✓. I/O: `results/<ts>/` + input CSV ✓.

## Layout y entorno
Como TP3 pero sin pandas (respuesta libre del usuario). Tests: C + Python (loader/scaler) ✓.

## Claude's Discretion
Desempate de variable a sacar en topics/content, claves de metrics de los stubs, figuras del EDA.

## Deferred Ideas
log1p como sensibilidad; SOM sobre k PCs.
