# Phase 5: Hopfield con QR - Context

**Gathered:** 2026-10-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Almacenar los **5 QR de 37×37 (N = 1369, ±1)** en la red de Hopfield ya construida en la Fase 4 y consultarlos bajo ruido, para explicar con evidencia por qué la regla de Hebb falla sobre patrones correlacionados y qué muestran la pseudo-inversa y una línea base de Hamming. Entrega:

- **HOP-04:** preparación de los 5 PNG a vectores ±1 de 1369 con una aserción de que los PNG son 0/255 puros; matriz de solapamientos 5×5.
- **HOP-05:** regla de Hebb — test de estabilidad a ruido cero y curva de ruido i.i.d. (≥8 niveles, ≥30 ensayos por nivel) con energía e iteraciones por paso; si Hebb falla, el fallo se reporta como hallazgo.
- **HOP-06:** regla de pseudo-inversa comparada contra Hebb y contra la línea base de Hamming al patrón almacenado más cercano, en los mismos niveles de ruido.
- **HOP-07:** limitaciones del caso de uso explicadas con evidencia (correlación entre QR, sensibilidad a corrimientos, corrección de errores propia del QR, equivalencia con una tabla de búsqueda).

**No incluye:** nada de letras 5×5 (eso fue la Fase 4). El núcleo C ya existe y es genérico (lee cualquier matriz P×N de ±1); esta fase reusa ese núcleo con N = 1369 y le agrega la regla de pseudo-inversa. No se agregan dependencias nuevas de Python (sin decodificador de QR — ver D-10). El daño estructurado queda fuera de alcance como experimento (ver Deferred Ideas).

</domain>

<decisions>
## Implementation Decisions

### Pre-registro y guardia (área: Pre-registro para QR)
- **D-01:** A diferencia de la Fase 4 (donde la guardia protegía la *regla de selección de letras*), acá **los 5 QR son fijos y dados** — no hay selección. Lo que se pre-registra y commitea con guardia sha256 antes de correr la red es el **protocolo del experimento** entre marcadores `<!-- regla:inicio -->`/`<!-- regla:fin -->` en `deliverables/05-hopfield-qr.md`: criterio de éxito, niveles de ruido, nº de ensayos, seeds, métricas reportadas, y la **hipótesis literal** ("Hebb no estabiliza los 5 QR correlacionados; la pseudo-inversa es el remedio"). La guardia incluye el **hash de los 5 PNG** (reusar `rule_digest`/`rule_guard` de `analysis/som_select.py`), para que ni el protocolo ni las imágenes se puedan retocar después de ver resultados. — **Reversibility:** one-way — una vez vistos los resultados de la red, cambiar el protocolo o los PNG invalida la afirmación "fijado de antemano".
- **D-02:** El protocolo incluye **umbrales de veredicto numéricos explícitos** de qué cuenta como "Hebb falló" y "pinv funciona" (p. ej. "Hebb falla si la recuperación exacta a ruido 0 es < 100 %"), fijados antes de correr, para que el veredicto no se ajuste después de ver la curva. — **Reversibility:** one-way — misma razón que D-01.
- **D-03:** El **criterio de éxito** es **match exacto de los 1369 píxeles** (|m| = 1 con el objetivo) como veredicto binario, y además se reporta la **curva continua del solapamiento final |m| promedio** por nivel de ruido, para ver qué tan cerca queda Hebb aunque nunca acierte exacto. Este criterio entra en el protocolo de D-01.

### Modelo de ruido (área: Modelo de ruido y daño)
- **D-04:** La corrupción es **sólo flips i.i.d. de píxeles** (una familia de ruido), cumpliendo HOP-05 al pie de la letra. El daño estructurado (oclusión de bloque, rayón, manchas) **no** se corre como experimento; se puede nombrar como limitación/idea diferida pero no genera figuras. — **Reversibility:** reversible.
- **D-05:** Resolución de la curva de ruido: **11 niveles de 0 a 0,5 en pasos de 0,05** (el nivel 0 es la estabilidad a ruido cero de HOP-05), **30 ensayos por nivel** y **10 seeds** (consistente con F2 D-08 / F3 / F4). Supera cómodo el piso de HOP-05 (≥8 niveles × ≥30 ensayos). Las tres reglas (Hebb, pinv, Hamming) se evalúan en esta misma grilla.

### Pseudo-inversa y línea base de Hamming (área: Pinv y base de Hamming)
- **D-06:** La regla de **pseudo-inversa** `W = Xᵀ(X Xᵀ)⁻¹ X` se implementa **en C**, despachada por la clave `rule = "pinv"` que la Fase 4 ya dejó prevista en `HOPFIELD_KEYS`. Requiere invertir la matriz de Gram de 5×5 (X Xᵀ). La dinámica, energía y clasificación del estado final reusan sin cambios el código del núcleo (asíncrono referencia, síncrono etiquetado). — **Reversibility:** costly — mover la construcción de W a Python más tarde parte el cómputo del modelo entre dos lenguajes.
- **D-07:** En la pinv se deja **la diagonal de W no nula** (pseudo-inversa pura / regla de proyección). Es la propiedad que garantiza que los 5 QR sean **puntos fijos exactos**, que es justo el remedio que se quiere mostrar frente al fallo de Hebb. No se anula la diagonal como en Hebb.
- **D-08:** La **línea base de Hamming** es un clasificador de **vecino más cercano (1-NN) sin dinámica**: toma la consulta ruidosa y devuelve el QR almacenado de menor distancia de Hamming. Se grafica su tasa de acierto superpuesta con Hebb y pinv en la **misma grilla de D-05**, más una tabla de recuperación exacta por nivel. Demuestra que un lookup trivial ya resuelve el problema (insumo de la limitación de D-09).
- **D-09:** Para **Hebb y pinv** se reporta, además de la tasa de acierto, **energía final e iteraciones (barridos) por nivel de ruido**, para contrastar el costo dinámico de la red contra el lookup instantáneo de Hamming.

### Limitaciones (área: Evidencia de limitaciones — HOP-07)
- **D-10:** **No se corre un decodificador de QR** (pyzbar/OpenCV) sobre las imágenes recuperadas. La limitación de la corrección de errores propia del QR (Reed-Solomon L/M/Q/H ≈ 7/15/25/30 %) y de que un recuperado pixel-exacto podría igual no decodificar se **argumenta en texto**, declarando explícitamente que la decodificación **no se verificó**. Evita una dependencia nueva y un spike; alineado con el blocker del STATE ("decodificador de QR sin verificar, HOP-09 en v2"). — **Reversibility:** reversible — agregar el decodificador después es aditivo.
- **D-11:** Se **demuestran empíricamente** (figura/número, además del texto) estas tres limitaciones: (a) **correlación entre QR** — matriz de solapamientos 5×5 (ya es HOP-04), fracción de píxeles idénticos en los 5 y distancia mínima de Hamming entre pares, como causa raíz del fallo de Hebb; (b) **sensibilidad a corrimientos** — mover un QR 1–2 píxeles y mostrar que la recuperación pixel-wise se rompe (tríptico antes/desplazado/recuperado); (c) **equivalencia con lookup** — ya cubierta por la curva de Hamming de D-08. La corrección propia del QR (D-10) queda sólo en texto.

### Claude's Discretion
El usuario discutió pre-registro, ruido, pinv/Hamming y limitaciones. Lo que sigue queda a criterio del researcher/planner, partiendo de los defaults de `.planning/research/PITFALLS.md` y de las decisiones del núcleo ya fijadas en la Fase 4:
- **Preparación de los PNG (HOP-04):** umbral y polaridad (dark = +1 o −1). La polaridad no cambia la dinámica de Hebb (W es invariante al flip global de un patrón) pero importa para mostrar imágenes; elegir una convención y documentarla. Aserción de valores en {0, 255} sin resampling (los PNG ya son 37×37 grayscale 0/255).
- **Claves exactas de config** (`rule`, `update`, `max_sweeps`, `trials`, `noise_levels`, nuevas si hacen falta para pinv/Hamming), claves de `metrics.json`, nombres de CSV de traza y de targets del Makefile (p. ej. `make hopfield-qr`, `make qr`, `make hopfield-qr-figures`), siguiendo el patrón de los targets de letras de la Fase 4.
- **Figuras:** QR almacenados, matriz de solapamientos, curvas de recuperación vs ruido con las tres reglas superpuestas, curvas de |m| continuo, energía/iteraciones por nivel, tríptico de corrimiento, y el estado atractor común de Hebb (la mayoría pixel-wise medida por la investigación).
- **Inversión de la Gram 5×5 en C:** método numérico y chequeo de independencia lineal / condicionamiento; cómo se reporta si la Gram es singular.
- **Detalle de la estabilidad a ruido cero (HOP-05):** verificar explícitamente que los 5 QR son (o no son) puntos fijos antes de agregar ruido, para Hebb y para pinv.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requisitos y alcance
- `.planning/ROADMAP.md` §Phase 5 — objetivo y criterios de éxito 1-4
- `.planning/REQUIREMENTS.md` — HOP-04, HOP-05, HOP-06, HOP-07
- `.planning/PROJECT.md` — restricciones (C + Python, sin librerías que implementen Hopfield, reproducibilidad, resultados generados no versionados) y Key Decisions (reglas fijadas de antemano, reportar el resultado tal cual aunque sea poco favorable)
- `.planning/phases/04-hopfield-n-cleo-y-letras/04-CONTEXT.md` — núcleo Hopfield (W entera, asíncrono referencia / síncrono etiquetado con ciclo 2, energía por paso, clasificación almacenado/inverso/mezcla/espurio, criterio de éxito fijado antes); interfaz genérica P×N prevista para los QR; `rule` previsto como clave de config para la pseudo-inversa
- `.planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-CONTEXT.md` — validación estricta de config por modelo, una carpeta por corrida, `metrics.json` plano, `diff -r` limpio con la misma seed, sin pandas, figuras matplotlib
- `.planning/phases/02-kohonen-som/02-CONTEXT.md` — D-08 (10 seeds), D-10/D-14 (regla commiteada antes de los resultados con guardia)
- `.planning/phases/03-oja-y-decisiones-de-campa-a/03-CONTEXT.md` — D-07 (patrón de regla con marcadores, checkpoint de aprobación y guardia sha256)

### Teoría y enunciado
- `docs/Modelo de Hopfield.pdf` — modelo del curso (neuronas ±1, sin autoconexiones en Hebb, h_i = Σ w_ij s_j, si h_i = 0 se mantiene el estado, energía)
- `docs/Archivo SIATP 42026.pdf` — consigna de los 5 QR de 37×37: almacenar, consultar con distintos niveles de ruido, analizar iteraciones y energía por paso, explicar limitaciones del caso de uso

### Investigación (ya midió el comportamiento esperado — reproducir honestamente, no "descubrir")
- `.planning/research/PITFALLS.md` — **Pitfall 1** (Hebb sobre los 5 QR da 0 % de recuperación; solapamientos 0,58–0,86; 69,8 % de píxeles idénticos en los 5; distancia mínima 96/1369; cross-talk del tamaño de la señal; 0,138N no aplica a patrones correlacionados; fix medido = pseudo-inversa `W = Xᵀ(XXᵀ)⁻¹X`, 100 % hasta 30 % de ruido, 96 % a 40 %), **Pitfall 12** (clasificación del estado final, criterio de éxito fijado antes, atractor mayoría pixel-wise), **Pitfall 21** (≥30 ensayos, graficar 0–0,5, seeds en la salida), **Pitfall 22** (PNG ya 0/255, sin resampling, polaridad para display), **Pitfall 16** (limitaciones defendibles: correlación, corrimiento/escala, lookup 1-NN equivalente, Reed-Solomon, espurios/inversos, costo N²), **Pitfall 27** (0,138N asintótico; pinv eleva el techo a N para patrones linealmente independientes), tablas de decisión (Hebb-only aceptable sólo como primer experimento + pinv + texto de limitación honesto)
- `.planning/research/SUMMARY.md` §Phase 6 (numeración vieja: corresponde a esta Fase 5) y §Gaps/Deferred — Hebb falla, pinv como remedio planificado, línea base de Hamming, decodificador de QR no verificado
- `.planning/research/ARCHITECTURE.md` — despacho por `model`, salidas por corrida
- `.planning/research/FEATURES.md` — features de Hopfield, catálogo de espurios

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `neuron/models/hopfield.c`, `neuron/models/hopfield_core.c/.h` — red de Hopfield real de la Fase 4: W entera de Hebb, asíncrono (referencia) y síncrono con detección de ciclo 2, energía por paso, clasificación del estado final, lectura de matriz ±1 genérica P×N (no asume N = 25). El núcleo corre tal cual con N = 1369; se le agrega la rama `rule = "pinv"`.
- `neuron/io/config.c` — `HOPFIELD_KEYS` ya incluye `task`, `rule`, `update`, `max_sweeps`, `trials`, `noise_levels`, `subset`, `trace_trials`, `p`, `n_subsets`. Las claves nuevas para pinv/Hamming son filas nuevas de `KeySpec` con la misma validación estricta.
- `neuron/io/matrix.c/.h` (`matrix_load` de CSV con encabezado), `neuron/io/results.c/.h` (`results_write_table`, `results_write_metrics`), `neuron/rng.c/.h` (`rng_shuffle`, para los flips i.i.d. con seed).
- `analysis/som_select.py` — `rule_digest` y `rule_guard` para la guardia de D-01 (ahora sobre el protocolo + hash de los PNG); `analysis/som_stage.py` — `require_same_rule`.
- `analysis/hopfield.py`, `analysis/hopfield_select.py`, `analysis/hopfield_letters.py`, `analysis/hopfield_figures.py` — recomputación en numpy de dinámica/energía/clasificación y estilo de figuras (adaptables a QR).
- `scripts/prepare_letters.py` — patrón del conversor de bitmaps a matriz ±1 CSV; el conversor de PNG a ±1 de los QR (HOP-04) sigue el mismo molde.
- `analysis/sweep.py`, `analysis/series_smoke_hopfield.json`, `analysis/plots_style.py`.

### Established Patterns
- Una carpeta por corrida y la misma seed dan `diff -r` limpio, sin timestamps en los archivos.
- Validación estricta de config: aborta ante clave desconocida, faltante o de tipo incorrecto.
- Fragmento de entregable por fase en `deliverables/` (hoy 01→04), con la regla/protocolo entre marcadores commiteado antes de los resultados y una sección "Cómo reproducir".
- `make test` = tests de C bajo ASan/UBSan + pytest (`analysis/tests/`). Python sin pandas; figuras matplotlib.
- Recomputación independiente en numpy de todas las salidas del binario de C, verificada contra un fixture.

### Integration Points
- `neuron/models/models.c` despacha `"hopfield"` → `run_hopfield`; la rama `rule = "pinv"` se agrega dentro del modelo hopfield, no como modelo nuevo. Se actualiza `neuron/config.json.hopfield.example`.
- Script de preparación de QR (`scripts/`) → matriz ±1 de 5×1369 en `datos/` → binario de C → `analysis/` (solapamientos, curvas de ruido Hebb/pinv/Hamming con guardia, limitaciones, figuras).
- La Fase 6 consume el fragmento `deliverables/05-hopfield-qr.md` y las figuras.

</code_context>

<specifics>
## Specific Ideas

- El usuario quiere que la narrativa "Hebb falla → pseudo-inversa remedia" quede **pre-registrada con umbrales de veredicto** antes de correr, para que el hallazgo (que la investigación ya predijo) no parezca ajustado a posteriori — mismo rigor que las reglas commiteadas de F2/F3/F4, pero sobre el protocolo del experimento en vez de una selección de patrones.
- La pseudo-inversa es la pieza central del remedio, así que se implementa **en C** (coherente con "los algoritmos a mano en C") y con **diagonal no nula** para preservar la propiedad de punto fijo exacto.
- La equivalencia con una tabla de búsqueda no es sólo texto: la **curva de Hamming 1-NN superpuesta** es la evidencia de que un lookup trivial resuelve el mismo problema.

</specifics>

<deferred>
## Deferred Ideas

- **Daño estructurado sobre los QR** (oclusión de bloque, rayón de línea, manchas) como experimento con figuras propias — la investigación lo recomienda por el caso de uso, pero el usuario lo dejó fuera de alcance de esta fase (se corre sólo ruido i.i.d.). Se puede nombrar como limitación en texto; si se quisiera medir, sería su propia extensión.
- **Decodificador de QR real** (pyzbar/OpenCV) sobre las imágenes recuperadas para verificar si decodifican a su URL — fuera de alcance (D-10); el STATE lo marca como HOP-09 en v2. Requeriría una dependencia sólo-análisis y probablemente un spike previo.

</deferred>

---

*Phase: 5-Hopfield con QR*
*Context gathered: 2026-10-24*
