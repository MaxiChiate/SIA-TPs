# Phase 2: Kohonen SOM - Context

**Gathered:** 2026-10-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Reemplazar el stub `neuron/models/kohonen_stub.c` por un SOM real en C (grilla k×k, vecindad y η decrecientes, inicialización con muestras) que reporta QE, TE y ocupación por neurona; correr un barrido multi-seed en dos etapas; elegir la grilla con una regla multicriterio escrita y commiteada antes de mirar resultados; y, para la grilla elegida, producir mapa de hits, matriz U, planos de componentes, perfiles por región y el contraste con PC1/PC2 del biplot, con la respuesta escrita a qué indica una distancia alta en la matriz U (SOM-01..05). No incluye Oja ni las decisiones de campaña (Fase 3), ni la grilla hexagonal (SOM-06, v2).

</domain>

<decisions>
## Implementation Decisions

### Algoritmo y vecindad (C)
- **D-01:** Vecindad configurable por clave en la config: **escalón del curso** (camino principal) y **gaussiana** (variante). Escalón: se actualizan las neuronas con distancia en la grilla `||n − n_k|| ≤ R(t)`, con `≤` (no el `<` estricto de las slides) para que R=1 actualice los 4 vecinos pegados y no solo la ganadora; R(0) configurable y decrece hasta 1 inclusive. Gaussiana: `h = exp(−d²/2σ²)` con σ decreciente y un piso > 0 (nunca 0). La regla de Kohonen es `W_j += η(t)·h_j·(x − W_j)` (h ∈ {0,1} en escalón). — **Reversibility:** costly — las claves de config, las series y el texto del informe dependen de los dos modos.
- **D-02:** η decrece **exponencialmente** de η0 a ηf: `η(t) = η0·(ηf/η0)^(t/T)`, con η0 < 1 y ηf en la config (baseline 0,5 → 0,01).
- **D-03:** Entrenamiento por **épocas barajadas**: cada época recorre los 50 creadores en un orden barajado con el `Rng` de la seed (splitmix64, Fase 1); T = épocas · n pasos. Baseline del orden del 500·N del curso (N = 26 ⇒ ~13 000 pasos ≈ 260 épocas).
- **D-04:** Adyacencia de **4 vecinos** (R=1 del curso) para el TE y para la matriz U. TE = fracción de creadores cuya primera y segunda BMU no son 4-vecinas. Matriz U = promedio de la distancia euclídea entre el prototipo de cada neurona y los de sus 4-vecinos (los bordes promedian los vecinos que existen).
- **D-05:** Inicialización con muestras del conjunto de entrenamiento (SOM-01, recomendación de las slides para evitar unidades muertas). Distancia euclídea sobre las 26 variables auditadas con z-score.

### Diseño del barrido
- **D-06:** Barrido en **dos etapas**. Etapa 1: k ∈ {2,…,8} × vecindad ∈ {escalón, gaussiana} con un schedule baseline fijo (R0 ≈ k/2 o su equivalente σ0, η 0,5 → 0,01, ~260 épocas); la regla de D-10..D-14 elige k. Etapa 2: sobre la k elegida (vecindad escalón) se varían R0, η0 y épocas **de a uno** para mostrar que la elección es robusta. Las series usan `sweep.py` existente (`vary`/`values` o `variants` con varias claves). — **Reversibility:** reversible.
- **D-07:** Rango k = 2 a 8. Incluye grillas con más neuronas que creadores (8×8 = 64 > 50) a propósito: la curva debe mostrar que el QE baja siempre mientras la ocupación colapsa. Hay que **levantar el tope k² ≤ n** que tiene hoy `read_grid_k` en el stub.
- **D-08:** **10 seeds** por configuración; se reporta media ± desvío, no la mejor seed.
- **D-09:** QE leave-one-out calculado **en Python** como k-fold con **k = n = 50** (LOO exacto, cumple SOM-03 tal como está escrito): por cada seed y configuración, 50 entrenamientos con un creador excluido y la distancia del excluido a su BMU; QE-LOO = promedio. El binario de C no gana un modo LOO; Python arma los CSV de entrenamiento y orquesta las corridas.

### Regla de elección de grilla (fijada antes de ver resultados)
- **D-10:** La regla se escribe en el fragmento de la Fase 2 (estilo `deliverables/01-datos-pca.md` §5) y se **commitea antes de correr el barrido de la etapa 1**; el commit es la evidencia de SOM-03. — **Reversibility:** one-way — una vez vistos los resultados, cambiar la regla invalida la afirmación "fijada de antemano" del informe.
- **D-11:** Forma = **filtros + desempate**, aplicada solo sobre las corridas con **vecindad escalón**; la gaussiana se reporta al lado como comparación y no participa de la elección.
  1. Se descartan las k con TE medio > 0,05 o con ocupación insuficiente (D-12).
  2. Entre las que quedan gana el **menor QE-LOO medio**.
  3. Si otra k sobreviviente está a menos de 1 desvío (entre seeds) del QE-LOO ganador, gana la **más estable entre seeds** (D-13); si siguen empatadas, la **k más chica**.
- **D-12:** Ocupación suficiente = las dos condiciones sobre la media entre seeds: **≤ 20 % de neuronas vacías** y **≥ 2 creadores por neurona ocupada** en promedio.
- **D-13:** Estabilidad entre seeds = para cada seed, matriz 50×50 de distancias en la grilla entre las BMU de cada par de creadores; estabilidad = promedio del **Spearman** entre las matrices de todos los pares de seeds (45 pares con 10 seeds). Invariante a rotación y reflexión del mapa, comparable entre k.
- **D-14:** Si ninguna k pasa los filtros: se **quita solo el filtro de TE**, se aplica el resto de la regla sin cambios y el informe dice explícitamente que ninguna grilla cumplió TE ≤ 0,05. La ocupación no se relaja nunca.
- **D-15:** QE (de entrenamiento) se reporta y se grafica contra k, pero no decide: el texto dice que por QE solo ganaría la grilla más grande (fuera de alcance en REQUIREMENTS: "Elegir la grilla del SOM por menor QE").

### Claude's Discretion
- Forma del decaimiento de R (escalón) y de σ (gaussiana) entre R0/σ0 y su final, mientras R termine en 1 y σ tenga piso > 0; nombres de las claves nuevas de la config y de `metrics.json` (validación estricta como en Fase 1 D-02).
- Traza por época (QE/TE contra época) para mostrar que el entrenamiento se aplanó: recomendada por la investigación, formato a criterio.
- Cómo obtiene Python la distancia del creador excluido en LOO (p. ej., leyendo `prototypes.csv` de la corrida y calculando la BMU en Python, o una entrada de test en C); el resultado debe ser el mismo.
- Valores concretos de la etapa 2 (R0, η0, épocas) y del baseline exacto, siempre que se fijen en la serie antes de correrla.
- Regiones y contraste con PCA (área no discutida): seguir `.planning/research/PITFALLS.md` Pitfall 6 — hit map + matriz U + planos juntos; perfiles con medias des-estandarizadas de los creadores asignados (unidades originales), marcando neuronas con < 2 miembros; contraste con PC1/PC2 cuantificado (p. ej., PC1/PC2 medios por neurona o proyección de los prototipos sobre el biplot), no a ojo; no afirmar que los temas "validan" los clusters (son entradas); seed fija para las figuras y la aclaración de que la orientación del mapa es arbitraria. Planos de las variables excluidas (en particular `topic_art_pct`) como promedio de la variable cruda por neurona (Fase 1 D-09).
- Corrida de sensibilidad con las 31 columnas para el SOM: opcional, solo si es barata; no entra a la regla.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requisitos y alcance
- `.planning/ROADMAP.md` §Phase 2 — objetivo y criterios de éxito 1-4
- `.planning/REQUIREMENTS.md` — SOM-01..05 (y Out of Scope: no elegir por menor QE; SOM-06 hexagonal en v2)
- `.planning/PROJECT.md` — restricciones (C + Python, sin librerías de ML para Kohonen, reproducibilidad)
- `.planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-CONTEXT.md` — D-01 (cJSON), D-02 (validación estricta), D-04 (convención de corrida), D-06 (sin pandas, matplotlib), D-08/D-09 (26 variables; planos de variables excluidas), D-13 (SOM sobre las 26 variables z-scored, no sobre PCs)

### Teoría y enunciado
- `docs/Kohonen Model.pdf` — algoritmo del curso: vecindad `||n − n_k|| < R(i)`, R(0) → 1, η(i) → 0 (ej. 1/i), 500·N iteraciones, inicialización con muestras, grilla rectangular 4/8 vecinos, matriz U (promedio de distancias a vecinos), plano de una variable
- `docs/Archivo SIATP 42026.pdf` — enunciado (Ejercicio 1, punto de Kohonen: variar hiperparámetros, justificar con performance, matriz U, perfiles por región, contraste con PC1/PC2)

### Investigación
- `.planning/research/PITFALLS.md` — Pitfall 5 (no elegir por QE; QE medido por k), Pitfall 6 (lectura de matriz U, hits y regiones), Pitfall 7 (schedules de η y radio)
- `.planning/research/FEATURES.md` §Exercise 1 - Kohonen — table stakes y diferenciadores

### Resultados de la Fase 1 que consume esta fase
- `deliverables/01-datos-pca.md` — §3 auditoría (26 variables), §5 formato de "regla fijada antes" a imitar, §6 PCA (PC1 ≈ tamaño, 53,2 %; PC1+PC2 61,7 %; convención de signo)
- `datos/prepared/creadores_zscore.csv` y `datos/prepared/creadores_zscore.meta.json` — entrada del SOM y scaler (generados por `make prepare`)
- `analysis/results/pca/audited/` — scores y loadings para el contraste con PC1/PC2 (generados por `make pca`)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `neuron/models/kohonen_stub.c`: ya tiene `pick_prototypes` (inicialización con muestras barajadas por el Rng), `nearest` (BMU con desempate por índice menor), `write_prototypes` (`prototypes.csv`: neuron, row, col, features) y `write_assignments` (`assignments.csv`: sample, bmu, row, col, distance) con `occupied_neurons` y `mean_bmu_distance`. Se reemplaza el cuerpo y se conservan los escritores.
- `neuron/io/config.c/h`: tablas `KeySpec` por modelo (KEY_INT, KEY_NUMBER, KEY_STRING, KEY_OBJECT, KEY_NUMBER_ARRAY); una clave nueva es una fila más. `KEY_STRING` sirve para el selector de vecindad.
- `neuron/io/matrix.c/h`, `neuron/io/results.c/h` (`results_write_table`, `results_write_metrics` con `Metric`), `neuron/rng.c/h` (`rng_shuffle`).
- `analysis/sweep.py`: series con `base_config`, `set`, `vary`/`values` o `variants` (varias claves), `seeds`, `workers`; escribe `summary.csv` con las claves de `metrics.json` y las variadas.
- `analysis/plots_style.py`, `analysis/pca.py` (scores/loadings y convención de signo), `scripts/creadores.py` (loader 50×33).

### Established Patterns
- Una carpeta de resultados por corrida, sin timestamp dentro de los archivos (Fase 1 D-04): misma seed ⇒ `diff -r` limpio.
- Validación estricta de config: clave desconocida, faltante o de tipo incorrecto aborta.
- Fragmento de entregable por fase en `deliverables/` con la regla escrita antes de los resultados.
- `make test` con tests de C (`neuron/tests/test_main.c`) y pytest (`analysis/tests/`).

### Integration Points
- `neuron/models/models.c` despacha `"kohonen"` → `run_kohonen`; `neuron/config.json.kohonen.example` y `analysis/series_smoke_kohonen.json` se actualizan con las claves nuevas.
- `read_grid_k` limita hoy k² ≤ n: hay que levantarlo para k hasta 8 (D-07).
- Salidas consumidas por la Fase 3 (región SOM de cada creador para las campañas) y la Fase 6 (figuras y texto del fragmento).

</code_context>

<specifics>
## Specific Ideas

- El usuario eligió LOO en Python y no un modo LOO en C, con k = 50 folds para que siga siendo leave-one-out exacto.
- La vecindad escalón usa `≤ R` para resolver la ambigüedad de R=1 en las slides (pendiente anotado en STATE.md para la Fase 2).
- La gaussiana se mantiene como variante comparativa, no como candidata de la regla.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (Grilla hexagonal ya figura como SOM-06 en v2.)

</deferred>

---

*Phase: 2-Kohonen SOM*
*Context gathered: 2026-10-21*
