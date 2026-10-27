# Phase 3: Oja y decisiones de campaña - Context

**Gathered:** 2026-10-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Reemplazar `neuron/models/oja_stub.c` por la regla de Oja real en C (una neurona, sobre las 26 variables auditadas con z-score), generar el índice de los 50 creadores con evidencia de convergencia y compararlo contra la proyección sobre PC1 (OJA-01, OJA-02); interpretar el índice y responder con evidencia por qué elegir el máximo para cualquier campaña es incorrecto (OJA-03); recomendar una shortlist por campaña (fútbol, perros, maquillaje, arte) con una regla fijada y commiteada antes de calcularla, comparada contra elegir solo por `followers` con el mismo k (CAMP-01, CAMP-02); y responder el mantenimiento del sistema (CAMP-03). No incluye Sanger/PC2 por red, un recomendador, presupuestos ni afirmaciones de ROI, ni nada de Hopfield (Fases 4-5).

</domain>

<decisions>
## Implementation Decisions

### Oja: entrenamiento, signo y validación
- **D-01:** Oja de una neurona en C sobre `datos/prepared/creadores_zscore.csv` (26 variables, ya centradas; F1 D-13), con η chico y decreciente, épocas barajadas con el `Rng` de la seed y **número fijo de épocas** (sin parada por tolerancia). Al final se renormaliza w a norma 1. La convergencia se demuestra con una traza por época (`trace.csv`): C registra |w| y ‖Δw‖ por época, y Python agrega |cos(w, PC1)| leyendo los w por época (el coseno no se calcula en C, ver D-05). Para eso `trace.csv` guarda también w al final de cada época. Valores de η0, ηf y épocas a criterio del planner/researcher, dentro del rango estable del Pitfall 8 (η·|x|² ≪ 1; con 26 variables, |x|² ≈ 26).
- **D-02:** **Convención de signo igual a la de la PCA de la Fase 1**: después de renormalizar, w se orienta de modo que su coeficiente de mayor |valor| sea positivo (`deliverables/01-datos-pca.md` §5). Hoy eso es `average_caption_words` (+0,94 en PC1), así que un índice alto = creador chico, de epígrafes largos, tutorial y con más perros; un índice bajo = grande, caro, de video corto. La convención se aplica en C (para que `index.csv` ya salga orientado) y se documenta en el fragmento. — **Reversibility:** costly — las tablas de Oja vs PC1, la tabla de evidencia del máximo y el texto del informe se leen con este signo.
- **D-03:** **10 seeds** (como F2 D-08). Se reporta la dispersión entre seeds una vez fijado el signo (|cos| entre los w de distintas seeds, rango del índice por creador). Una seed fija produce las tablas y figuras.
- **D-04:** Salidas de la corrida: `weights.csv` (w final orientado), `index.csv` (sample, index), `trace.csv` (época, |w| antes de renormalizar, ‖Δw‖, η), `metrics.json` plano (w_norm_final, delta_w_final, épocas, etc.). Validación estricta de claves nuevas como el resto (F1 D-02).
- **D-05:** La comparación Oja vs PC1 se calcula **en Python**: lee `weights.csv` e `index.csv` y las cargas/scores de `analysis/results/pca/audited/`, y reporta |cos| y cos con signo entre w y v1, Pearson y **Spearman** entre el índice y el score de PC1, y overlap@5 y overlap@10. Un **pytest** exige |cos(w, v1)| > 0,99 en la corrida smoke. No hay eigen-solver en C.

### Respuesta a "¿elegir el máximo para cualquier campaña?"
- **D-06:** Se responde con una **tabla de evidencia**: las cargas de w (ordenadas por |valor|), la correlación del índice con `followers` y con cada uno de los 4 `topic_*_pct` crudos (incluido `topic_art_pct`, que no entra al entrenamiento, F1 D-09), y cuántos de los top-10 de cada tema dominante caen en el top-10 del índice, **con los dos signos** (el de D-02 y el opuesto) para mostrar que "el máximo" depende de una convención. El texto empieza por la respuesta ("no") y sigue con la evidencia. No se usa la palabra "mejor" para el índice.

### Regla de selección por campaña (fijada antes de calcular)
- **D-07:** La regla se escribe en el fragmento de la Fase 3 (`deliverables/03-oja-campanas.md` o similar), entre marcadores tipo `<!-- regla:inicio -->`/`<!-- regla:fin -->`, y se **commitea con guardia sha256** antes de calcular las shortlists, igual que la regla de grilla de la F2 (`analysis/som_select.py`: `rule_digest`, `rule_guard`). El script de campañas se niega a correr si la regla cambió o no está commiteada. Conviene un checkpoint de decisión en el que el usuario apruebe el texto de la regla antes del commit (como en 02-03). — **Reversibility:** one-way — una vez vistas las shortlists, cambiar la regla invalida la afirmación "fijada de antemano".
- **D-08:** Forma = **filtro por tema + ranking**. Filtro: entra el creador cuyo **tema dominante** (argmax de los 4 `topic_*_pct` crudos de `datos/creadores.csv`) es el de la campaña, la misma etiqueta del biplot y de la F2. Ranking: un criterio por campaña (D-10, D-11). Sin score ponderado general ni Oja restringido por campaña.
- **D-09:** **k = 5** por campaña y por lista, el mismo para la estrategia propia y para las de followers. Si un filtro deja menos de 5 creadores, se informan los que haya (la regla lo dice de antemano).
- **D-10:** **Fútbol: 3 listas + recomendación.** Una shortlist de 5 por objetivo: **alcance masivo** (`estimated_argentina_reach`), **descubrimiento** (`non_follower_reach_pct`, con `trend_posts_pct` como apoyo) y **profundidad educativa** (`content_tutorial_pct`, `saves_per_1000`, `average_watch_time_seconds`). Después, una recomendación escrita de qué objetivo conviene al cliente (ropa de entrenamiento de fútbol), con los supuestos explícitos.
- **D-11:** **Perros, maquillaje y arte: un objetivo por cliente**, escrito como supuesto en la regla:
  - Perros (refugios, poco presupuesto, alcance local) → menor **costo por mil argentinos alcanzados** (`price_usd / estimated_argentina_reach · 1000`).
  - Maquillaje (marca de belleza) → **profundidad**: saves, tutorial, watch time.
  - Arte (materiales de arte, nicho) → **engagement por 1000** + profundidad.
  Para los criterios con varias variables (profundidad, engagement + profundidad), el planner propone la combinación exacta (por ejemplo, la media de los z de cada variable) y se aprueba en el checkpoint de D-07.
- **D-12:** El precio **no entra a la regla** como tope: se reporta el costo total del top-5 y el costo por mil argentinos de cada lista. El enunciado no da presupuestos.
- **D-13:** Si hay un empate exacto en el criterio de ranking, desempata el índice de Oja con el signo de D-02 y, después, `creator_id`. Oja y PCA no filtran ni ordenan fuera de ese desempate.

### Rol del SOM, Oja y PCA en la recomendación
- **D-14:** El SOM es **solo descriptivo** en las campañas: se indica en qué neurona cae cada elegido (fila, col) y se puede marcar en el mapa de hits, pero la neurona no cambia la selección ni impone diversificación. Coherente con la F2: la regla de regiones dio una sola región (R1 = 50) y no se inventan regiones.
- **D-15:** Oja y PCA dan la **lectura**: se reporta el índice de Oja de cada elegido para mostrar que la shortlist no coincide con el top del índice, y PC1/PC2 ubican cada lista en el biplot (escala vs nicho; audiencia argentina). Así se cumple "justificada con Kohonen, Oja y PCA" (CAMP-01) sin que ninguno de los tres sea el criterio de selección.

### Comparación contra solo `followers`
- **D-16:** **Dos baselines**, ambos con k = 5: (a) el top-5 **global** por `followers`, que es la estrategia ingenua del enunciado, y (b) el top-5 por `followers` **dentro del mismo filtro de tema**, para aislar el efecto del criterio de ranking. Esto evita la comparación de hombre de paja (Pitfall 10).
- **D-17:** Métricas de la tabla, por campaña y por lista: overlap@5 contra cada baseline, proporción del tema de la campaña, alcance argentino total, costo total, costo por mil argentinos y la métrica objetivo de la campaña. Se listan también las **ventajas de followers** (simple, estable, sin modelo que mantener, correlacionado con alcance). No hay afirmaciones de ROI, ventas ni conversión, y se dice explícitamente que sin datos de resultado no se pueden hacer.

### Mantenimiento
- **D-18:** Respuestas escritas y concretas para: campaña nueva (no se re-entrena, es una regla nueva sobre el mismo filtro + ranking); creadores nuevos (se estandarizan con el scaler guardado, se les asigna BMU e índice, y se re-entrena si su distancia a la BMU supera la distribución del QE de entrenamiento); variables nuevas (se rehace la auditoría, se re-estandariza y se re-entrena desde cero porque cambia la dimensión); actualización mensual (seed fija, scaler y codebook versionados, perfiles rotulados por contenido y no por posición, y la convención de signo de D-02 para Oja).
- **D-19:** **Demo chica**: un creador nuevo **sintético, marcado como tal** se mapea con `scripts/map_creator.py` y el `.meta.json`, se le asigna BMU en el SOM de la F2 (k = 5, `k5-step`, seed de las figuras) e índice de Oja con el w guardado, y su distancia a la BMU se compara contra la distribución del QE de entrenamiento como chequeo de drift. No hay una simulación completa de un "mes nuevo".

### Claude's Discretion
- Valores de η0, ηf, épocas y la forma del decaimiento de η para Oja (dentro del rango estable).
- Nombres exactos de las claves de config y de `metrics.json`, y de los CSV.
- Combinación exacta de las variables de los criterios compuestos (D-11), sujeta a la aprobación del checkpoint de D-07.
- Figuras (convergencia por época con las 10 seeds, índice vs PC1, shortlists en el biplot y en el mapa) y nombre del fragmento y de los targets del Makefile (por ejemplo `make oja`, `make campaigns`).
- Valores del creador sintético de la demo.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requisitos y alcance
- `.planning/ROADMAP.md` §Phase 3: objetivo y criterios de éxito 1-5
- `.planning/REQUIREMENTS.md`: OJA-01..03, CAMP-01..03 (Out of Scope: análisis de marketing exhaustivo, librerías de ML para Oja)
- `.planning/PROJECT.md`: restricciones (C + Python, sin librerías de ML para Oja, reproducibilidad) y Key Decisions (reglas fijadas de antemano, reportar el resultado tal cual)
- `.planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-CONTEXT.md`: D-02 (validación estricta), D-04 (convención de corrida), D-06 (sin pandas, matplotlib), D-08/D-09 (26 variables; `topic_art_pct` fuera del entrenamiento pero en el CSV crudo), D-13 (Oja sobre la matriz z-scored completa, no sobre PCs)
- `.planning/phases/02-kohonen-som/02-CONTEXT.md`: D-08 (10 seeds), D-10 (regla commiteada antes) y el patrón de guardia

### Teoría y enunciado
- `docs/Regla de Oja y Sanger.pdf`: regla de Oja del curso (actualización, η, convergencia a PC1)
- `docs/Archivo SIATP 42026.pdf`: enunciado (Ejercicio 1: índice con Oja, "¿sería correcto elegir automáticamente al creador con el valor más alto para cualquier campaña?", comparación con PC1; decisiones de campaña: alcance masivo vs descubrimiento vs profundidad para fútbol, comparación contra solo followers, mantenimiento)

### Investigación
- `.planning/research/PITFALLS.md`: Pitfall 8 (centrado, η estable, norma y signo de Oja), Pitfall 9 (el índice no es un puntaje universal; tabla de evidencia), Pitfall 10 (baseline de followers justo y sin ROI), Pitfall 20 (respuestas de mantenimiento)
- `.planning/research/FEATURES.md` §Exercise 1 - Oja and campaign decisions: table stakes y diferenciadores

### Resultados de fases anteriores que consume esta fase
- `deliverables/01-datos-pca.md`: §5 (convención de signo: mayor |coef| positivo), §6 (PC1 53,2 %: +epígrafes/tutorial/guardados, −followers/alcance/precio; PC2 8,5 %: audiencia argentina; temas en PC3/PC4)
- `deliverables/02-kohonen.md`: §2 (formato de "regla fijada antes" con marcadores), §6.2-6.3 (perfiles por neurona; una sola región R1), §7 (cómo reproducir)
- `datos/prepared/creadores_zscore.csv` y `datos/prepared/creadores_zscore.meta.json`: entrada de Oja y scaler (`make prepare`)
- `analysis/results/pca/audited/` (`loadings.csv`, scores): referencia PC1 (`make pca`)
- `analysis/results/som/` (corrida de figuras k = 5 `k5-step`): neurona de cada creador para D-14 y D-19 (`make som-stage1` y siguientes)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `neuron/models/oja_stub.c`: ya tiene `norm`, `random_unit_vector` (inicio desde el `Rng`), `project` (índice = x·w), `mean_and_std` y `write_outputs` (`weights.csv`, `index.csv`, `metrics.json`). Se reemplaza el cuerpo del entrenamiento y se conservan los escritores.
- `neuron/io/config.c`: tabla `OJA_KEYS` (hoy model, seed, input); las claves nuevas (η0, ηf, épocas) son filas nuevas de `KeySpec`.
- `neuron/rng.c/h` (`rng_shuffle` para las épocas barajadas), `neuron/io/results.c/h` (`results_write_table`, `results_write_metrics`).
- `analysis/sweep.py`: 10 seeds con `seeds`; `analysis/series_smoke_oja.json` existe y se actualiza con las claves nuevas.
- `analysis/som_select.py`: `rule_digest` y `rule_guard` (marcadores `<!-- regla:inicio -->`/`<!-- regla:fin -->`, sha256 y chequeo de commit en git) para reusar en la regla de campañas; `analysis/som_stage.py`: `require_same_rule`.
- `analysis/pca.py` (scores, loadings, convención de signo), `scripts/creadores.py` (loader 50×33 con los topics crudos), `scripts/map_creator.py` (mapeo de un creador nuevo con el `.meta.json`), `analysis/plots_style.py`.

### Established Patterns
- Una carpeta por corrida y la misma seed dan `diff -r` limpio; no hay timestamps dentro de los archivos (F1 D-04).
- La validación estricta de config aborta ante una clave desconocida, faltante o de tipo incorrecto.
- Hay un fragmento de entregable por fase en `deliverables/`, con la regla entre marcadores commiteada antes de los resultados y una sección "Cómo reproducir".
- `make test` = tests de C (`neuron/tests/test_main.c`) + pytest (`analysis/tests/`). Python sin pandas.

### Integration Points
- `neuron/models/models.c` despacha `"oja"` → `run_oja`; se actualiza `neuron/config.json.oja.example`.
- El script de campañas lee `datos/creadores.csv` (crudo, para temas, precio y alcance), el índice de Oja, los scores de PCA y las asignaciones del SOM de la F2.
- Las salidas las consume la Fase 6 (slides e informe: tabla de evidencia del máximo, tablas de campañas, mantenimiento).

</code_context>

<specifics>
## Specific Ideas

- Con la convención de la PCA, el "máximo" del índice es un creador chico de nicho (tutorial, perros), no uno grande. El usuario prefirió esa convención porque hace más visible el contraejemplo y no hace falta traducir el signo entre Oja y PC1.
- El usuario quiere que la regla de campañas siga el mismo patrón de rigor que la regla de grilla de la F2: commit y guardia sha256 antes de ver las shortlists.
- El SOM se deja deliberadamente como solo descriptivo en las campañas. Eso es coherente con haber reportado una sola región tal como salió en la F2.

</specifics>

<deferred>
## Deferred Ideas

None. La discusión no salió del alcance de la fase. (Sanger/PC2 por red y el índice condicionado por tema quedan como diferenciadores no requeridos de FEATURES.md, sin agregarse al roadmap.)

</deferred>

---

*Phase: 3-Oja y decisiones de campaña*
*Context gathered: 2026-10-21*
