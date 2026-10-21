# Phase 3: Oja y decisiones de campaña - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-21
**Phase:** 3-Oja y decisiones de campaña
**Areas discussed:** Signo y lectura del índice, Regla de selección por campaña, Rol del SOM con una sola región, Baseline followers y mantenimiento

---

## Signo y lectura del índice

| Option | Description | Selected |
|--------|-------------|----------|
| Igual que la PCA | Mayor \|coef\| positivo; comparable con PC1 sin traducir; el máximo es un creador chico/tutorial/perros | ✓ |
| followers positivo | Lectura intuitiva, pero con signo opuesto a PC1 de la F1 | |
| Reportar ambos signos | Uno fijo para tablas y top-k con los dos signos | |

| Option | Description | Selected |
|--------|-------------|----------|
| Tabla de evidencia | Cargas, correlación con followers y los 4 temas, overlap del top-10 por tema con los dos signos | ✓ |
| Tabla + contraejemplo por campaña | Agrega el creador de índice máximo con su % por tema | |
| Solo texto con cifras clave | Un párrafo | |

| Option | Description | Selected |
|--------|-------------|----------|
| 10 seeds, traza por época | \|w\|, \|cos(w, PC1)\|, Δw; dispersión entre seeds después de fijar el signo | ✓ |
| 1 seed + traza | Mínimo suficiente | |
| Barrido de η además | Muestra dónde diverge | |

| Option | Description | Selected |
|--------|-------------|----------|
| Épocas fijas + reporte | Renormalización final; convergencia demostrada en la traza | ✓ |
| Parada por tolerancia | Δw < tol con tope | |
| Lo decidís vos | Discreción del planner | |

| Option | Description | Selected |
|--------|-------------|----------|
| Python + test pytest | numpy eigh; pytest \|cos\| > 0,99 | ✓ |
| También un eigen-solver en C | Método de potencias en C | |

---

## Regla de selección por campaña

| Option | Description | Selected |
|--------|-------------|----------|
| Filtro por tema + ranking | Filtro de tema y después un criterio por campaña | ✓ |
| Score ponderado | Suma ponderada en z | |
| Oja/PCA restringido | Índice condicionado por tema | |

| Option | Description | Selected |
|--------|-------------|----------|
| k = 5 | Shortlist realista | ✓ |
| k = 10 | Overlap más estable, contraste diluido | |
| k = 5 y k = 10 | Ambos reportados | |

| Option | Description | Selected |
|--------|-------------|----------|
| 3 listas + recomendación | Alcance / descubrimiento / profundidad, más una recomendación escrita | ✓ |
| 1 lista con objetivo elegido | Los otros dos en texto | |
| Mix | Cupos por objetivo | |

| Option | Description | Selected |
|--------|-------------|----------|
| Sí, commit + guardia | Como la F2, sha256 y negativa a correr | ✓ |
| Sí, solo escrita | Sin guardia | |
| No | Definida mirando los datos | |

| Option | Description | Selected |
|--------|-------------|----------|
| Tema dominante | argmax de los 4 topic_*_pct | ✓ |
| Umbral fijo ≥ 40 % | Umbral absoluto | |
| Top-15 por % del tema | Mismo tamaño de pool | |

| Option | Description | Selected |
|--------|-------------|----------|
| Un objetivo por cliente | Perros: costo por mil argentinos; maquillaje: profundidad; arte: engagement + profundidad | ✓ |
| Mismo criterio para todos | Costo por mil argentinos | |
| Vos proponés en la regla | El planner redacta y se aprueba en un checkpoint | |

| Option | Description | Selected |
|--------|-------------|----------|
| Solo como métrica reportada | Costo total y costo por mil, sin tope | ✓ |
| Tope de presupuesto supuesto | Optimizar dentro de un presupuesto | |

---

## Rol del SOM con una sola región

| Option | Description | Selected |
|--------|-------------|----------|
| Diversificación por neurona | A lo sumo 2 por neurona en el top-5 | |
| Lookalikes / reemplazos | Neurona y 4 vecinas como alternativas | |
| Solo descripción | Ubicar a cada elegido en el mapa y el biplot, sin afectar la regla | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| Desempate + lectura | Oja no filtra ni ordena; se reporta el índice de cada elegido; PC1/PC2 ubican las listas | ✓ |
| Oja como criterio de alcance | Índice invertido como criterio de alcance en fútbol | |

**Notes:** El "desempate" se registró como desempate de empates exactos en el ranking (D-13).

---

## Baseline followers y mantenimiento

| Option | Description | Selected |
|--------|-------------|----------|
| Las dos | Top-5 global por followers y top-5 por followers dentro del tema | ✓ |
| Solo global | Lectura literal | |
| Solo dentro del tema | La comparación más exigente | |

| Option | Description | Selected |
|--------|-------------|----------|
| Las de CAMP-02 + objetivo | overlap@5, proporción de tema, alcance argentino, costo, costo por mil, métrica objetivo y ventajas de followers | ✓ |
| Solo las de CAMP-02 | overlap@5, proporción de tema, costo por alcance | |

| Option | Description | Selected |
|--------|-------------|----------|
| Texto + demo chica | Creador sintético mapeado con map_creator.py, BMU, índice y chequeo de drift contra el QE | ✓ |
| Solo texto | Sin código nuevo | |
| Demo completa de drift | Simular un mes nuevo | |

---

## Claude's Discretion

- η0, ηf, épocas y decaimiento de Oja
- Nombres de claves de config, de metrics.json y de los CSV
- Combinación exacta de los criterios compuestos (aprobada en el checkpoint de la regla)
- Figuras, nombre del fragmento y targets del Makefile
- Valores del creador sintético

## Deferred Ideas

None.
