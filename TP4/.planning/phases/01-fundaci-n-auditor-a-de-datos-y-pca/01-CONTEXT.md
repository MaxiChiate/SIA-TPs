# Phase 1: Fundación, auditoría de datos y PCA - Context

**Gathered:** 2026-10-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Dejar lista la base técnica compartida (un binario C que despacha por `model`, `sweep.py`, `.venv`, `make test`) y decidir las variables de `creadores.csv`: loader con verificación 50×33, EDA, tabla de auditoría, z-score con scaler guardado, PCA por autovalores con decisión escrita y corrida de sensibilidad con las 31 columnas. No incluye los algoritmos reales de Kohonen, Oja ni Hopfield (Fases 2-5).

</domain>

<decisions>
## Implementation Decisions

### Infraestructura C
- **D-01:** Parser JSON = cJSON v1.7.19 vendored en `neuron/vendor/cjson/` (compilado sin `-Wextra -Wpedantic` por archivo). Resuelve la contradicción entre STATE.md ("plano por defecto") y CLAUDE.md; gana cJSON porque las configs de fases siguientes son anidadas (grilla, schedules, listas de ruido). — **Reversibility:** costly — todas las configs y `config.c` de las Fases 2-5 dependen del formato.
- **D-02:** Validación estricta estilo TP3: clave desconocida, faltante o de tipo incorrecto aborta con mensaje claro. Sin defaults silenciosos.
- **D-03:** "Modelo trivial e2e" = stubs deterministas por cada clave `model` (kohonen/oja/hopfield). Cada uno lee su input real (CSV z-scored o patrones), usa el RNG splitmix64 con seed, y escribe `metrics.json` plano + un CSV tipo. Prueba dispatch, config, RNG, escritura y reproducibilidad byte a byte; las Fases 2-5 reemplazan el cuerpo.
- **D-04:** Convención de corrida: Python escribe el input (`datos/prepared/creadores_zscore.csv` + `.meta.json`); la config apunta al input; C escribe `results/<timestamp>_<model>_seed<N>/` con copia de `config.json`, `metrics.json` plano y CSVs. Igual que TP3. El timestamp aparece solo en el nombre de la carpeta de resultados y nunca dentro de ningún archivo (`metrics.json`, CSV, `config.json` copiada, sin rutas absolutas), para que `diff -r` entre dos corridas con la misma seed sirva como prueba de reproducibilidad.
- **D-05:** Layout `neuron/`, `analysis/`, `scripts/` como TP3. Se copia tal cual `rng.c/h`, Makefile 3.81-safe (`-MMD -MP`), `results.c`, `sweep.py` y runner de tests; se rehacen config (cJSON) y metrics. Prep de datos en `scripts/`, EDA/PCA/plots en `analysis/`. `.venv` con `uv`, `Makefile` usa `PY ?= .venv/bin/python`.
- **D-06:** Python **sin pandas** (decisión del usuario, anula la mención de pandas en CLAUDE.md): `csv` stdlib + numpy para EDA/PCA/z-score; matplotlib para figuras (camino por defecto; plotly solo si hace falta algún gráfico interactivo); Pillow para QR más adelante. Requirements pineados en `analysis/requirements.txt`.
- **D-07:** `make test` cubre C (config rechaza claves desconocidas, misma seed ⇒ mismos bytes, dispatch por `model`) y Python con pytest, menos de 10 tests en total: loader falla si no 50×33; z-score invertible desde `.meta.json`; creador nuevo mapeado usando solo el scaler; (a) los autovalores de la matriz de correlación suman el número de variables y proyectar/reconstruir con todas las PCs devuelve los datos; (b) las variables eliminadas son exactamente las 5 acordadas en D-08/D-09 y la matriz resultante tiene rango completo. Chequeo de la auditoría: con las 31 columnas, la matriz de correlación tiene 5 autovalores prácticamente cero.

### Auditoría de variables
- **D-08:** El conjunto auditado que entra a PCA/SOM/Oja **quita las 5 dependencias lineales exactas** (verificadas: `price_ars = 1500·price_usd`, `organic = 100 − sponsored`, `total_engagement = likes+comments+saves+shares`, los 4 `topic_*` suman 100, los 4 `content_*` suman 100). Conjunto auditado ≈ 26 variables de las 31; las 31 con z-score corren como sensibilidad etiquetada (DATA-05).
- **D-09:** Regla fija por grupo escrita en la tabla de auditoría: se saca `price_ars`, `organic_posts_pct`, `total_engagement_per_1000`, y de `topic_*` y `content_*` se saca la de menor varianza medida en escala original (antes del z-score). Las variables sacadas se pueden reconstruir desde las restantes y se conservan en el CSV crudo para reportar (en particular los 4 topics para las campañas). El plano de componentes de cada variable que no entra al entrenamiento (en particular la de `topic_*` que se saque) se calcula en la Fase 2 como el promedio de esa variable entre los creadores asignados a cada neurona, de modo que las 4 campañas tengan su plano aunque el SOM se entrene con 3 topics.
- **D-10:** Casi-redundantes (no exactas) solo se documentan, no se eliminan: `estimated_argentina_reach` (≈ `average_reach × argentina_audience_pct/100`, error ≤ 0.5 por redondeo) y los pares con |r|>0.9 con `followers` (reach, impressions, views). Quedan en el conjunto; se discuten en PCA (PC1 ≈ tamaño).

### Transformaciones y PCA
- **D-11:** Z-score directo, sin log ni winsorizar (sesgo máximo ≈ 2 en `estimated_argentina_reach`; followers/reach/precio ≈ 1). Se documenta el sesgo en el EDA; el log queda como sensibilidad opcional, no como camino principal. Scaler (media, desvío) guardado en `.meta.json`.
- **D-12:** PCA sobre matriz de correlación (= covarianza del z-score) por autovalores, verificada con `np.linalg.eigh`. Regla de decisión escrita antes de mirar el scree: el criterio de 80% de varianza acumulada fija k; Kaiser (autovalor >1) funciona como control; si difieren, se reporta la discrepancia.
- **D-13:** La PCA es diagnóstica: justifica por escrito si se podría reducir y cómo leer PC1/PC2 (biplot), pero Kohonen y Oja corren sobre la matriz z-scored completa del conjunto auditado, como pide el enunciado. No se agrega una corrida del SOM sobre k PCs.

### Claude's Discretion
- Nombres de claves de `metrics.json` de los stubs, formato de los CSV tipo y detalle del Makefile.
- Elección de figuras del EDA (histogramas, matriz de correlación) y estilo (reusar `plots_style.py` de TP3).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requisitos y alcance
- `.planning/ROADMAP.md` §Phase 1 — criterios de éxito 1-5
- `.planning/REQUIREMENTS.md` — INFRA-01..04, DATA-01..05
- `.planning/PROJECT.md` — restricciones (C + Python, sin librerías de ML, reproducibilidad)
- `CLAUDE.md` (`.claude/CLAUDE.md`) — stack recomendado (versiones, cJSON, qué no usar)
- `.planning/research/` — investigación del stack y pitfalls

### Teoría y enunciado
- `docs/Archivo SIATP 42026.pdf` — enunciado
- `docs/PCA Sistemas de Inteligencia Artificial.pdf` — PCA por autovalores
- `docs/Autovalores y Autovectores.pdf` — autovalores y autovectores
- `docs/Introducción Aprendizaje No Supervisado.pdf`

### Datos
- `datos/creadores.csv` — 50 filas, 33 columnas (`creator_id`, `name` + 31 variables)

### Referencia TP3
- `../TP3/neuron/` (Makefile, `rng.c/h`, `io/results.c`, `io/config.c`) — infraestructura a copiar/adaptar
- `../TP3/analysis/sweep.py`, `plots_style.py`, `requirements.txt`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- TP3 `rng.c/h` (splitmix64), `io/results.c` (mkdir, clock_gettime, `_POSIX_C_SOURCE`), `Makefile`, `analysis/sweep.py` (ThreadPoolExecutor, series JSON con `base_config`/`vary`/`values`/`seeds`), `plots_style.py`, runner de tests en C.

### Established Patterns
- Un directorio de resultados por corrida con copia de la config; series versionadas (`series_*.json`), resultados generados no versionados.
- `.venv/` ya está en `.gitignore`; make instalado es 3.81 (sin sintaxis de make 4).

### Integration Points
- TP4 no tiene código todavía (solo `docs/` y `datos/`); todo se crea en esta fase.
- Salida de Fase 1 consumida por Fases 2-3 (z-scored + scaler + decisión PCA) y por Fases 4-5 (binario y sweep).

</code_context>

<specifics>
## Specific Ideas

- El usuario pidió explícitamente Python sin pandas.
- Verificado en esta discusión: las 5 dependencias lineales son exactas (error ≤ 1e-13) y `estimated_argentina_reach` no lo es.

</specifics>

<deferred>
## Deferred Ideas

- Sensibilidad con log1p a las variables de escala (opcional, fuera del camino principal).
- Corrida del SOM sobre k PCs (descartada para no ampliar Fase 2).

</deferred>

---

*Phase: 1-Fundación, auditoría de datos y PCA*
*Context gathered: 2026-10-20*
