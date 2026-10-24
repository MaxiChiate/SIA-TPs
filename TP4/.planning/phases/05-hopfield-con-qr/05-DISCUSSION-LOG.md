# Phase 5: Hopfield con QR - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-24
**Phase:** 5-Hopfield con QR
**Areas discussed:** Pre-registro para QR, Modelo de ruido y daño, Pinv y base de Hamming, Evidencia de limitaciones

---

## Selección de áreas

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-registro para QR | Qué se pre-registra/commitea con guardia (no hay selección de patrones) | ✓ |
| Modelo de ruido y daño | i.i.d. vs daño estructurado; resolución de la curva | ✓ |
| Pinv y base de Hamming | Pinv en C/Python, diagonal, definición de la base 1-NN | ✓ |
| Evidencia de limitaciones | Decodificador de QR; qué se demuestra vs se argumenta | ✓ |

**User's choice:** las cuatro áreas.

---

## Pre-registro para QR

### Objeto pre-registrado

| Option | Description | Selected |
|--------|-------------|----------|
| Protocolo del experimento | Texto entre marcadores: criterio de éxito, ruido, ensayos, seeds, métricas, hipótesis; guardia con hash de PNG | |
| Protocolo + umbrales de veredicto | Lo anterior más umbrales numéricos de "Hebb falló" / "pinv funciona" fijados antes | ✓ |
| Sin guardia, sólo seeds | Omitir el ritual de regla commiteada; sólo seeds/config versionadas | |

**User's choice:** Protocolo + umbrales de veredicto → D-01, D-02.

### Criterio de éxito

| Option | Description | Selected |
|--------|-------------|----------|
| Match exacto de los 1369 píxeles | |m|=1 bit a bit; criterio de la investigación | |
| Exacto + curva de |m| continua | Veredicto binario exacto, más la curva continua de solapamiento final | ✓ |
| Umbral |m| ≥ 0,95 | Permisivo; riesgo de que no decodifique igual | |

**User's choice:** Exacto + curva de |m| continua → D-03.

---

## Modelo de ruido y daño

### Tipos de corrupción

| Option | Description | Selected |
|--------|-------------|----------|
| i.i.d. + daño estructurado | Flips i.i.d. más oclusión/rayón/manchas (recomendado por la investigación) | |
| Sólo flips i.i.d. | Una sola familia de ruido; cumple HOP-05 literal | ✓ |
| i.i.d. + sólo oclusión de bloque | Punto medio: un tipo estructurado extra | |

**User's choice:** Sólo flips i.i.d. → D-04. El daño estructurado pasa a Deferred Ideas.

### Resolución de la curva

| Option | Description | Selected |
|--------|-------------|----------|
| 11 niveles × 30 ensayos × 10 seeds | 0–0,5 paso 0,05, incluye ruido 0; supera el piso | ✓ |
| Piso exacto: 8 × 30 × 10 | Mínimo de HOP-05 | |
| Densa: 11 × 50 × 10 | Más ensayos; más cómputo marginal | |

**User's choice:** 11 × 30 × 10 → D-05.

---

## Pinv y base de Hamming

### Dónde se implementa la pinv

| Option | Description | Selected |
|--------|-------------|----------|
| En C, clave rule="pinv" | Núcleo C invierte la Gram 5×5; reusa dinámica/energía/clasificación | ✓ |
| En Python, W inyectada | Python arma W; C sólo corre dinámica | |
| Que decidas vos | A criterio del planner | |

**User's choice:** En C, rule="pinv" → D-06.

### Línea base de Hamming y métricas de comparación

| Option | Description | Selected |
|--------|-------------|----------|
| Vecino más cercano, misma curva | 1-NN sin dinámica, superpuesto en la misma grilla | |
| Vecino más cercano + energético | Lo anterior más energía e iteraciones por nivel para Hebb/pinv | ✓ |
| Que decidas vos | A criterio del planner | |

**User's choice:** Vecino más cercano + energético → D-08, D-09.

### Diagonal de W en la pinv

| Option | Description | Selected |
|--------|-------------|----------|
| Diagonal no cero (pinv pura) | Garantiza puntos fijos exactos (proyección) | ✓ |
| Diagonal a cero | Comparable con Hebb en forma; rompe el punto fijo exacto | |
| Reportar ambas | Dos curvas documentando el efecto de la autoconexión | |

**User's choice:** Diagonal no cero (pinv pura) → D-07.

---

## Evidencia de limitaciones

### Decodificador de QR

| Option | Description | Selected |
|--------|-------------|----------|
| No; se declara no testeado | Argumentar Reed-Solomon en texto; sin dependencia nueva | ✓ |
| Sí, con pyzbar/OpenCV | Testear decodificación; suma dependencia y spike | |
| Que decidas vos | A criterio del planner | |

**User's choice:** No; se declara no testeado → D-10.

### Limitaciones demostradas empíricamente (multiSelect)

| Option | Description | Selected |
|--------|-------------|----------|
| Correlación entre QR | Matriz de solapamientos + píxeles idénticos + distancia mínima | ✓ |
| Sensibilidad a corrimientos | Mover 1–2 píxeles y mostrar que se rompe (tríptico) | ✓ |
| Equivalencia con lookup | Ya cubierta por la curva de Hamming 1-NN | ✓ |
| Corrección propia del QR | Reed-Solomon; queda en texto (sin decodificador no se mide) | |

**User's choice:** Correlación entre QR + Sensibilidad a corrimientos + Equivalencia con lookup → D-11. La corrección propia del QR queda sólo en texto.

---

## Claude's Discretion

El usuario dejó a criterio del researcher/planner: preparación de los PNG (umbral, polaridad), claves exactas de config/`metrics.json`, nombres de CSV y de targets del Makefile, figuras, método de inversión de la Gram 5×5 en C y su chequeo de condicionamiento, y el detalle del test de estabilidad a ruido cero.

## Deferred Ideas

- Daño estructurado sobre los QR (oclusión de bloque, rayón, manchas) como experimento con figuras propias.
- Decodificador de QR real (pyzbar/OpenCV) sobre las imágenes recuperadas (HOP-09 en v2 según STATE).
