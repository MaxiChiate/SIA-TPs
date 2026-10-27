# Phase 2: Kohonen SOM - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-21
**Phase:** 2-Kohonen SOM
**Areas discussed:** Algoritmo y vecindad, Diseño del barrido, Regla de elección de grilla

---

## Algoritmo y vecindad

| Pregunta | Opciones | Elegida |
|----------|----------|---------|
| Función de vecindad | Escalón del curso / Gaussiana / Ambas, configurables | Ambas, configurables |
| Decaimiento de η | Exponencial η0→ηf / Lineal η0→ηf / 1/i como el curso | Exponencial η0→ηf |
| Unidad de entrenamiento | Épocas barajadas / Iteraciones con reposición | Épocas barajadas |
| Adyacencia para TE y matriz U | 4-vecinos / 8-vecinos / Reportar ambos TE | 4-vecinos |

**Notes:** El usuario pasó a la siguiente área sin cerrar el decaimiento de R/σ, la inicialización ni la traza por época; quedan a criterio de Claude (inicialización con muestras ya la fija SOM-01).

---

## Diseño del barrido

| Pregunta | Opciones | Elegida |
|----------|----------|---------|
| Estructura | Dos etapas / Factorial chico / De a uno sobre un baseline | Dos etapas |
| Rango de k | 2 a 8 / 3 a 6 / 2 a 10 | 2 a 8 |
| Seeds | 10 / 5 / 20 | 10 |
| Dónde se calcula QE-LOO | En C con flag / En C una corrida por creador / k-fold en Python | k-fold en Python |
| Cantidad de folds (seguimiento) | 50 folds = LOO / 10 folds / 5 folds | 50 folds = LOO |

**Notes:** Al elegir k-fold en Python se preguntó por la cantidad de folds porque SOM-03 dice "leave-one-out"; con 50 folds el requisito no cambia.

---

## Regla de elección de grilla

| Pregunta | Opciones | Elegida |
|----------|----------|---------|
| Forma de la regla | Filtros + desempate / Frente de Pareto / Puntaje ponderado | Filtros + desempate |
| Ocupación suficiente | ≤ 20 % vacías y ≥ 2 por ocupada / Solo ≤ 20 % vacías / Solo ≥ 2 por ocupada | ≤ 20 % vacías y ≥ 2 por ocupada |
| Estabilidad entre seeds | Correlación de distancias en grilla / ARI de asignaciones / Co-vecindad ajustada | Correlación de distancias |
| ¿La regla elige la vecindad? | Solo k con escalón / Par (k, vecindad) / k con cada vecindad | Solo k, con escalón |
| Sin ganador | Relajar TE y reportar / k con menos violaciones / Detener y decidir aparte | Relajar TE y reportar |

---

## Claude's Discretion

- Decaimiento de R y σ, claves de config y de `metrics.json`, traza por época.
- Mecanismo con el que Python obtiene la distancia del creador excluido en LOO.
- Valores concretos del baseline y de la etapa 2 (fijados en la serie antes de correr).
- Regiones y contraste con PCA (área no seleccionada para discutir): seguir PITFALLS.md Pitfall 6.
- Sensibilidad del SOM con 31 columnas: opcional.

## Deferred Ideas

Ninguna.
