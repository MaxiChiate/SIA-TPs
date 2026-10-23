# Phase 4: Hopfield núcleo y letras - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-23
**Phase:** 4-Hopfield núcleo y letras
**Areas discussed:** Letras y alfabeto

Áreas ofrecidas y no elegidas (quedan a criterio de Claude): Dinámica y energía, Éxito y clasificación, Capacidad y espurio.

---

## Letras y alfabeto

### ¿De dónde salen los bitmaps 5×5?

| Option | Description | Selected |
|--------|-------------|----------|
| Abecedario completo propio | 26 letras en un archivo de texto versionado (`*`/`.`), con la J del enunciado; un script las pasa a ±1 | ✓ |
| Solo un puñado de letras | 8-10 letras a mano; quedan pocos subconjuntos | |
| Fuente de terceros | Font 5×5 existente, citado | |

### ¿Cómo se eligen las 4 letras del set principal?

| Option | Description | Selected |
|--------|-------------|----------|
| Dos sets: separado y correlacionado | Menor max \|solapamiento\| por regla + un set muy correlacionado que falla | ✓ |
| Solo el más ortogonal | Un único set; la capacidad se analiza aparte | |
| Letras elegidas a mano | Por ejemplo, las iniciales del grupo | |

### ¿La regla de selección se fija y se commitea antes de correr Hopfield?

| Option | Description | Selected |
|--------|-------------|----------|
| Sí, con guardia | Marcadores + checkpoint de aprobación + sha256, como F2/F3 | ✓ |
| No, basta con documentarla | Depende solo de los bitmaps | |

### ¿Qué subconjuntos entran en el análisis de capacidad?

| Option | Description | Selected |
|--------|-------------|----------|
| Exhaustivo para p=4, muestra para el resto | 14950 sets de 4 + muestra con seed para p=1..8 | ✓ |
| Solo muestras al azar | 100-200 por p | |
| Unos pocos sets nombrados | 5-10 subconjuntos | |

**User's choice:** todas las opciones recomendadas; después, "Escribir CONTEXT".

---

## Claude's Discretion

- Dinámica (asíncrono como referencia, síncrono con detección de ciclos, h=0 mantiene el estado, W entera con diagonal 0)
- Energía e iteraciones (E por actualización, dos cuentas, tests de monotonía)
- Clasificación del estado final (almacenado/inverso/mezcla de 3/otro, con solapamientos) y criterio de éxito fijado en la regla
- Búsqueda y presentación del estado espurio
- Niveles de ruido, ensayos, seeds, claves de config, nombres de archivos, targets y figuras

## Deferred Ideas

Ninguna.
