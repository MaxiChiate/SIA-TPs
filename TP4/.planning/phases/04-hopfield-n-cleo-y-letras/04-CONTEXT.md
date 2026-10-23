# Phase 4: Hopfield núcleo y letras - Context

**Gathered:** 2026-10-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Reemplazar `neuron/models/hopfield_stub.c` por una red de Hopfield discreta real en C (W entera con diagonal cero, actualización síncrona y asíncrona, energía por paso, detección de ciclos y clasificación del estado final: almacenado, inverso, mezcla o espurio), HOP-01. Validarla con letras de 5×5 (N = 25): 4 letras almacenadas y recuperadas a partir de consultas con ruido, con análisis de ortogonalidad (matriz de solapamientos) y de capacidad sobre varios subconjuntos de letras (HOP-02), y un patrón muy ruidoso que converge a un estado espurio identificado y clasificado (HOP-03). El núcleo tiene que servir sin cambios de interfaz para los QR de 37×37 (N = 1369) de la Fase 5, pero esta fase no incluye nada de QR, ni pseudo-inversa, ni línea base de Hamming, ni limitaciones del caso de uso: todo eso es de la Fase 5.

Se ejecuta en la rama `dev-tp4-hopfield`, separada de `dev-tp4`, porque la Fase 3 todavía no terminó. No debe tocar archivos de la Fase 3 (Oja, campañas).

</domain>

<decisions>
## Implementation Decisions

### Alfabeto y bitmaps de letras
- **D-01:** Se dibuja un **abecedario completo propio de 26 letras (A-Z) de 5×5** en un archivo de texto versionado y legible (una letra por bloque, filas con `*` = +1 y `.` = -1, en orden row-major), por ejemplo `datos/letters/alphabet_5x5.txt`. Un script de Python lo convierte a una matriz ±1 (una fila por letra, 25 columnas) que lee el binario de C. La **J del enunciado** (`docs/Archivo SIATP 42026.pdf`, §2.2) se transcribe tal cual y un pytest verifica que la codificación coincide con la matriz del enunciado (Pitfall 14). — **Reversibility:** costly — los solapamientos, la regla de selección de D-03, el barrido de capacidad y las figuras dependen de estos bitmaps. Una vez commiteada la regla, cambiar un bitmap obliga a rehacerla.
- **D-02:** El conversor valida que haya 26 letras, que cada una tenga exactamente 5 filas de 5 caracteres en `{*, .}` y que no haya dos letras idénticas. Falla con un error claro si algo no se cumple.

### Selección del set principal de 4 letras
- **D-03:** Se muestran **dos sets de 4 letras lado a lado**: (a) el set **separado**, que es el subconjunto de 4 del alfabeto con **menor max |solapamiento|** fuera de la diagonal (solapamiento = ξ^a·ξ^b / N), y (b) el set **correlacionado**, el subconjunto con **mayor max |solapamiento|**, que se espera que falle y sirve para explicar el término de cruce. Las dos reglas, con un desempate escrito (por ejemplo, menor media de |solapamiento| y después orden alfabético), se evalúan sobre los C(26,4) = 14950 subconjuntos y dependen solo de los bitmaps, no de la red. El set separado es el "set principal" de la demo de recuperación y del estado espurio. Con N impar no existe ortogonalidad exacta (Pitfall 14b): se habla de "|solapamiento| chico".
- **D-04:** La regla de D-03 se **fija y se commitea antes de correr Hopfield**, con el mismo patrón de rigor de la F2 (D-10/D-14) y la F3 (D-07): el texto de la regla va en el fragmento de la fase (`deliverables/04-hopfield-letras.md` o similar) entre marcadores `<!-- regla:inicio -->`/`<!-- regla:fin -->`, y la guardia sha256 + commit (reusar `rule_digest`/`rule_guard` de `analysis/som_select.py`) impide que el script de letras corra si la regla cambió o no está commiteada. Antes del commit hay un checkpoint de decisión en el que el usuario aprueba el texto de la regla. Los bitmaps de D-01 entran en la guardia (por ejemplo, el digest incluye el archivo del alfabeto), para que tampoco se puedan retocar después de ver resultados. — **Reversibility:** one-way — una vez vistos los resultados de la red, cambiar la regla o los bitmaps invalida la afirmación "elegido de antemano".

- **D-04b (agregada en la planificación, 2026-10-23):** La investigación dibujó un abecedario borrador y corrió la red sobre él, así que **ese borrador queda descartado** como abecedario pre-registrado. En el checkpoint de la regla se dibuja un **abecedario nuevo** (lo propone Claude sin ejecutar ningún código de red sobre él, o lo dibuja el usuario) y el usuario lo aprueba glifo por glifo. Los desempates se fijan **por principio, no por resultado**: el set separado minimiza max |d| y desempata por menor suma de |d|; el set correlacionado maximiza max |d| y desempata por **mayor** suma de |d| (simétrico). Todo se compara con productos punto enteros. Ningún número de la red sobre el abecedario nuevo se calcula ni se muestra antes del commit de la regla. — **Reversibility:** one-way — misma razón que D-04.

### Capacidad y ortogonalidad
- **D-05:** El análisis de capacidad es **exhaustivo para p = 4**: los 14950 subconjuntos de 4 letras se almacenan (Hebb, W entera) y para cada uno se mide la fracción de patrones que son puntos fijos estables (y, a un nivel de ruido fijo, la tasa de recuperación). Se grafica contra el max |solapamiento| del subconjunto. Para **p = 1..8** (confirmado por el usuario en la planificación; si la estabilidad no cae a ~0 en p = 8, se extiende con una regla escrita en la regla de D-04, no a mano) se toma una **muestra al azar con seed** de subconjuntos por p y se grafica la fracción estable contra p, marcando 0,138N ≈ 3,45 **solo como orden de magnitud** (Pitfall 26), nunca como umbral.
- **D-06:** La matriz de solapamientos de 4×4 y el término de cruce de cada patrón se reportan para **los dos sets** de D-03, y además el histograma de max |solapamiento| sobre los 14950 sets de 4 ubica a ambos dentro de la distribución.

### Claude's Discretion
El usuario eligió discutir solo letras y alfabeto. Lo que sigue queda a criterio del researcher/planner, partiendo de los defaults de `.planning/research/PITFALLS.md` (Pitfalls 11, 12, 14 y 26):
- **Dinámica:** el modo asíncrono con una permutación aleatoria nueva por barrido (`Rng` de la seed) es la **referencia**, y el síncrono (`s = sign(W s)`, como el curso) queda como comparación etiquetada con detección de ciclos de período 2 (comparar con el estado en t-2). Si h_i = 0, la neurona mantiene su estado (así lo dice el curso). W entera = Σ ξξᵀ con diagonal 0 (el 1/N es opcional y no cambia la dinámica), con chequeo de simetría. La parada es un barrido completo sin cambios o un tope de barridos.
- **Energía e iteraciones:** E = -½ sᵀ W s. Se registra por actualización de neurona (asíncrono) y por paso (síncrono) en un CSV de traza, y se reportan las dos cuentas (actualizaciones y barridos). Hay un test de C que exige energía no creciente en el modo asíncrono (tolerancia 1e-9) y otro que recalcula E desde cero contra la versión incremental.
- **Clasificación del estado final:** se calculan los solapamientos m_μ = ξ^μ·s / N. El estado es "almacenado" si m = +1 para algún μ, "inverso" si m = -1, "mezcla" si coincide con sign(±ξ^a ± ξ^b ± ξ^c) para alguna terna (probado explícitamente) y "espurio (otro)" en cualquier otro caso. El vector de solapamientos se guarda siempre. El criterio de éxito de recuperación (match exacto vs |m| ≥ umbral) se fija antes de correr y se escribe en la regla de D-04.
- **Estado espurio (HOP-03):** se busca con consultas muy ruidosas sobre el set principal (por ejemplo, entre 40 % y 50 % de píxeles invertidos, con seeds barridas). Se guarda la seed y la consulta que lo producen, y se muestran el estado, sus solapamientos, su clasificación y la energía del espurio comparada con la de los almacenados.
- **Ruido y ensayos:** niveles de ruido, número de ensayos por nivel (al menos 30, alineado con HOP-05), 10 seeds como en F2/F3, claves exactas de config y de `metrics.json`, nombres de CSV y de targets del Makefile (por ejemplo `make letters`, `make hopfield-letters`), y figuras (letras, matriz de solapamientos, curvas de energía, recuperación vs ruido, capacidad).
- **Interfaz para la Fase 5:** el núcleo lee una matriz ±1 genérica (P × N) y no asume N = 25. La regla de pseudo-inversa puede dejarse prevista como valor de una clave `rule`, pero se implementa en la Fase 5.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requisitos y alcance
- `.planning/ROADMAP.md` §Phase 4: objetivo y criterios de éxito 1-4
- `.planning/REQUIREMENTS.md`: HOP-01, HOP-02, HOP-03 (HOP-04..07 son de la Fase 5)
- `.planning/PROJECT.md`: restricciones (C + Python, sin librerías que implementen Hopfield, reproducibilidad) y Key Decisions (reglas fijadas de antemano, reportar el resultado tal cual)
- `.planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-CONTEXT.md`: validación estricta de config, convención de corrida (una carpeta por corrida, `metrics.json` plano, `diff -r` limpio con la misma seed), sin pandas, matplotlib para figuras estáticas
- `.planning/phases/02-kohonen-som/02-CONTEXT.md`: D-08 (10 seeds) y D-10/D-14 (regla commiteada antes de los resultados, con guardia)
- `.planning/phases/03-oja-y-decisiones-de-campa-a/03-CONTEXT.md`: D-07 (patrón de regla con marcadores, checkpoint de aprobación y guardia sha256)

### Teoría y enunciado
- `docs/Modelo de Hopfield.pdf`: modelo del curso (neuronas ±1, sin autoconexiones, h_i = Σ w_ij s_j, si h_i = 0 se mantiene el estado, W por regla de Hebb, estado estable/atractor, energía)
- `docs/Archivo SIATP 42026.pdf` §2.2: letras 5×5 con 1/-1, matriz de la J de ejemplo, consignas "Almacenar 4 patrones de letras", "análisis de ortogonalidad y de la capacidad de almacenamiento", "Ingresar un patrón muy ruidoso e identificar un estado espúreo"

### Investigación
- `.planning/research/PITFALLS.md`: Pitfall 11 (energía, orden de actualización, empates, diagonal, definición de iteración), Pitfall 12 (inversos, mezclas, espurios, criterio de éxito fijado antes), Pitfall 14 (capacidad y ortogonalidad con letras 5×5; N impar, varios subconjuntos, chequeo con la J), Pitfall 26 (0,138N como orden de magnitud), Performance Traps (energía incremental, W construida una vez)
- `.planning/research/SUMMARY.md` §Phase 5 (numeración vieja: corresponde a esta Fase 4) y §Gaps (modo de actualización: implementar ambos, asíncrono como referencia)
- `.planning/research/FEATURES.md`: features de Hopfield (table stakes y diferenciadores, catálogo de espurios)
- `.planning/research/ARCHITECTURE.md`: despacho por `model`, salidas por corrida

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `neuron/models/hopfield_stub.c`: ya tiene `is_pm_one` (validación ±1), `read_noise_levels` (`noise_levels` en [0, 1]), `corrupt` (invierte k píxeles elegidos con `rng_shuffle`), `overlap` y el escritor de `queries.csv` y de `metrics.json`. Se reemplaza el stub por la red real y se conservan las piezas útiles.
- `neuron/io/config.c`: tabla `HOPFIELD_KEYS` (hoy solo `noise_levels`). Las claves nuevas (modo de actualización, ensayos, tope de barridos, etc.) son filas nuevas de `KeySpec`, con la misma validación estricta.
- `neuron/io/matrix.c/h` (`matrix_load` de CSV con encabezado), `neuron/io/results.c/h` (`results_write_table`, `results_write_metrics`), `neuron/rng.c/h` (`rng_shuffle`).
- `neuron/tests/test_main.c` y `neuron/tests/fixtures/patterns_small.csv` (letras ±1 de 25 columnas usadas por el smoke test).
- `analysis/sweep.py` (series multi-seed → `summary.csv`), `analysis/series_smoke_hopfield.json` (se actualiza con las claves nuevas), `analysis/plots_style.py`.
- `analysis/som_select.py`: `rule_digest` y `rule_guard` para la guardia de D-04, y `analysis/som_stage.py`: `require_same_rule`.

### Established Patterns
- Una carpeta por corrida y la misma seed dan `diff -r` limpio, sin timestamps dentro de los archivos.
- La validación estricta de config aborta ante una clave desconocida, faltante o de tipo incorrecto.
- Hay un fragmento de entregable por fase en `deliverables/` (hoy `01-datos-pca.md` y `02-kohonen.md`), con la regla entre marcadores commiteada antes de los resultados y una sección "Cómo reproducir".
- `make test` = tests de C bajo ASan/UBSan + pytest (`analysis/tests/`). Python sin pandas; figuras con matplotlib.

### Integration Points
- `neuron/models/models.c` despacha `"hopfield"` → `run_hopfield`; se actualiza `neuron/config.json.hopfield.example`.
- Script de preparación de letras (`scripts/`) → matriz ±1 en `datos/` → binario de C → `analysis/` (solapamientos, selección de sets con guardia, capacidad, espurio, figuras).
- La Fase 5 reutiliza el mismo núcleo con los QR (N = 1369) y le agrega la pseudo-inversa. La Fase 6 consume el fragmento y las figuras.

</code_context>

<specifics>
## Specific Ideas

- El usuario quiere que la elección de letras no parezca hecha para que la demo salga linda: por eso hay dos sets elegidos por regla (separado y correlacionado) y la regla se commitea con guardia antes de correr la red, igual que en F2 y F3.
- El abecedario completo es la base de todo el análisis de capacidad, así que tiene que quedar versionado y ser legible a simple vista (`*`/`.`).

</specifics>

<deferred>
## Deferred Ideas

None. La discusión no salió del alcance de la fase.

</deferred>

---

*Phase: 4-Hopfield núcleo y letras*
*Context gathered: 2026-10-23*
