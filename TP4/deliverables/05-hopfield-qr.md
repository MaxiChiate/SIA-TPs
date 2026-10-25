# Fase 5 — Hopfield: QR

Las secciones 1, 2 y 4 en adelante se escriben después de las corridas; la sección 3 se fijó antes de correr la red sobre los 5 códigos QR.

## 1. Algoritmo y salidas

El modelo es la misma red de Hopfield discreta de la Fase 4 (núcleo en `neuron/models/hopfield_core.c`, sin librerías de aprendizaje automático), ahora con N = 1369 (cada QR de 37 × 37 es un vector de 1369 valores ±1, sección 2) en vez de N = 25: el núcleo recibe cualquier matriz P × N y nunca supone N = 25, así que la Fase 5 lo reusa sin cambios salvo la regla nueva. `neuron/build/neuron` corre con la misma config estricta (`task`, `rule`, `update`, `max_sweeps`, `trials`, `noise_levels`, `subset`, `trace_trials`).

**Pesos.** Dos reglas construyen W: **Hebb**, W = Σ ξξᵀ con la diagonal en cero (igual que la Fase 4, todo entero exacto); y **pseudo-inversa** (D-06), W = Xᵀ(XXᵀ)⁻¹X, nueva en esta fase, implementada en C (`hopfield_pinv`, Gauss-Jordan con pivoteo parcial sobre la Gram 5 × 5) con la **diagonal no anulada** (D-07): es la propiedad de proyección que vuelve a cada patrón almacenado un punto fijo exacto. W tiene 1369² = 1 874 161 entradas; con pinv son reales (no enteras), así que `analysis/hopfield.py` se extendió (05-01) para trabajar en float64 con tolerancia (`ENERGY_TOLERANCE`) en vez de castear a enteros, sin tocar la aritmética de Hebb.

**Dinámica, ruido, clasificación y energía.** Sin cambios respecto de la Fase 4: asíncrona de referencia (una permutación nueva por barrido), síncrona etiquetada con detección de ciclo de período 2; si el campo de una neurona es 0 se mantiene su estado; se invierten exactamente k = lround(nivel × 1369) píxeles distintos; la clasificación del estado final y la energía E = −½ sᵀWs son las mismas de la sección 3.

**Control en Python.** `analysis/hopfield.py` recalcula W, `stored.csv`, los solapamientos y, para los ensayos trazados, campos/energías/estado final paso a paso — igual que en la Fase 4, pero ahora también para pinv (`hopfield.pinv`, un control independiente vía `numpy.linalg.inv`, no una implementación de Hopfield: PROJECT.md prohíbe librerías que resuelvan Kohonen, Oja o Hopfield, no álgebra lineal genérica). `analysis/hopfield_qr.py` aplica este control a cada corrida de C antes de agregar; si algo no coincide, no deja ninguna salida.

**Salidas.** `make hopfield-qr` escribe `analysis/results/hopfield/qr/` (no versionado): `overlaps.json` / `qr_facts.json` (sección 2), `recall.csv` y `recovery_table.csv` (secciones 4-5), `energy_trace.csv` (energía por paso, HOP-05), `protocol.json` / `verdict.json` (los veredictos de D-02 aplicados a lo medido) y `run.json`. `make hopfield-qr-limits` (nuevo en este plan, HOP-07) escribe `analysis/results/hopfield/qr_limits/`: `majority.json` (atractor mayoría de Hebb) y `shift.json` (sensibilidad a corrimientos), más su propio `run.json` — un directorio separado que `make hopfield-qr` nunca borra, así una corrida de recuperación nunca elimina la evidencia de limitaciones. `make hopfield-qr-figures` dibuja seis figuras (`qr`, `overlaps`, `recovery`, `energy_trace`, `shift`, `majority`) en `analysis/results/hopfield/qr/figures/`.

## 2. Los 5 QR y su preparación

Los 5 QR de 37 × 37 de `datos/hopfield/*.png` (beverages, dessert, food, specials, wine, el orden fijo de `scripts/qr.py` SOURCES) son grises de solo 0/255 sin remuestreo (Pitfall 22); `scripts/qr.py` los lee, verifica forma y valores, y los codifica a ±1 con polaridad oscuro (0) = +1, claro (255) = −1 (solo para mostrar: la dinámica de Hebb es invariante al flip global de un patrón). `make qr` escribe `datos/prepared/qr_pm1.csv` (5 × 1369) y su `.meta.json` con el sha256 de cada PNG.

**`overlaps.svg`: matriz de solapamientos 5 × 5.** De `overlaps.json`: el máximo |solapamiento| entre pares es 0,86 (food–wine, producto escalar entero 1177 de 1369) y la media es 0,67; todos los pares quedan entre 0,58 y 0,86, lejos de la ortogonalidad. De `qr_facts.json`: el 69,8 % de los 1369 píxeles es idéntico en los 5 QR a la vez, y la distancia de Hamming mínima entre un par es 96 (el mismo par food–wine, 7,0 % de los píxeles). Estos tres números son la causa raíz, medida sobre los datos reales, del fallo de Hebb que reporta la sección 4 (HOP-04, D-11a).

## 3. Protocolo del experimento e hipótesis (fijado antes de correr la red)

<!-- regla:inicio -->
Esta sección fija el protocolo del experimento; los resultados se agregan después y no figuran acá. Las decisiones D-01 a D-11 están en `.planning/phases/05-hopfield-con-qr/05-CONTEXT.md`. A diferencia de la Fase 4 (donde la guardia protegía una *selección* de letras), acá los 5 QR son fijos y dados: no hay selección, y lo que se congela es el protocolo del experimento. Al commitear esta sección no se había calculado ninguna cantidad de la red (pesos de Hebb o de pseudo-inversa, campos, energías, puntos fijos ni recuperación) sobre los QR reales.

- **Hipótesis.** "Hebb no estabiliza los 5 QR correlacionados; la pseudo-inversa es el remedio" (D-01). La investigación (`.planning/research/PITFALLS.md`, Pitfall 1) ya midió este comportamiento antes de este protocolo; se reproduce honestamente, no se "descubre" (ver Divulgación).
- **Patrones.** Los 5 QR de 37×37 (N = 1369) convertidos por `scripts/qr.py` desde los PNG de `datos/hopfield/`, polaridad fija oscuro (0) = +1 y claro (255) = −1 (display; la dinámica de Hebb es invariante al flip global de un patrón). Se usa el subconjunto `[0, 1, 2, 3, 4]` en el orden fijo de `SOURCES` de `scripts/qr.py` (beverages, dessert, food, specials, wine). El sha256 de cada uno de los 5 PNG queda congelado por la guardia.
- **Reglas de la red.** Hebb entera con diagonal en cero, W = Σ ξξᵀ sin el factor 1/N (igual que la Fase 4); y pseudo-inversa, W = Xᵀ(XXᵀ)⁻¹X, con la diagonal **no** anulada (D-07), que es la propiedad que vuelve a los 5 QR puntos fijos exactos.
- **Dinámica.** La asíncrona es la referencia, con una permutación nueva por barrido; la síncrona es la comparación etiquetada, con detección de ciclo de período 2 (s(t+1) = s(t−1), nunca cuenta como convergido). Si el campo de una neurona es 0 se mantiene su estado. La parada es un barrido (o paso síncrono) sin cambios, con un tope de `max_sweeps`.
- **Modelo de ruido.** Solo flips i.i.d. de píxeles, una sola familia de ruido (D-04): se invierten exactamente k = lround(nivel × 1369) píxeles distintos elegidos con distribución uniforme. El daño estructurado (oclusión de bloque, rayón, manchas) no se corre como experimento; puede nombrarse como limitación en el texto pero no genera figuras.
- **Grilla de ruido.** 11 niveles de 0 a 0,5 en pasos de 0,05 (0; 0,05; 0,10; 0,15; 0,20; 0,25; 0,30; 0,35; 0,40; 0,45; 0,50), 30 ensayos por nivel y seeds 1 a 10 (D-05). El nivel 0 es la estabilidad a ruido cero (HOP-05): verifica explícitamente si los 5 QR son o no son puntos fijos antes de agregar ruido, para Hebb y para pinv. Las tres reglas (Hebb, pinv, Hamming) se evalúan en esta misma grilla.
- **Éxito.** Solo el match exacto de los 1369 píxeles (|m| = 1 con el objetivo) como veredicto binario (D-03); además se reporta, sin umbral, la curva continua del solapamiento final |m| promedio por nivel de ruido, para ver qué tan cerca queda Hebb aunque nunca acierte exacto.
- **Umbrales de veredicto.** Fijados antes de correr, para que no se ajusten después de ver la curva (D-02): **Hebb falla** si la recuperación exacta a ruido 0 es menor que 100 %; **pinv funciona** si los 5 QR son puntos fijos exactos, es decir si la recuperación exacta a ruido 0 es igual a 100 %.
- **Línea base de Hamming.** Clasificador de vecino más cercano (1-NN) sin dinámica: la consulta ruidosa se asigna al QR almacenado de menor distancia de Hamming, con empates resueltos por el índice más bajo (D-08). Se grafica superpuesta con Hebb y pinv en la misma grilla de ruido, más una tabla de recuperación exacta por nivel.
- **Energía e iteraciones.** Para Hebb y para pinv se reporta, además de la tasa de acierto, la energía final y el número de iteraciones (barridos) por nivel de ruido, para contrastar el costo dinámico de la red contra el lookup instantáneo de Hamming (D-09).
- **Limitaciones a demostrar.** (a) Correlación entre los 5 QR: matriz de solapamientos 5×5, fracción de píxeles idénticos en los 5 y distancia mínima de Hamming entre pares, como causa raíz del fallo de Hebb; (b) sensibilidad a corrimientos: desplazar un QR 1–2 píxeles y mostrar que la recuperación pixel-wise se rompe (tríptico antes/desplazado/recuperado); (c) equivalencia con una tabla de búsqueda: la curva de Hamming 1-NN de arriba. La corrección de errores propia del QR (Reed-Solomon) se argumenta solo en texto, declarando explícitamente que la decodificación **no se verificó** (D-10, D-11).
- **Guardia.** El sha256 del texto entre estos marcadores más el commit; `datos/hopfield/*.png` (los 5 QR), `scripts/qr.py` y `analysis/hopfield_qr_select.py` quedan congelados con él. `rule_identity` de `analysis/hopfield_qr_select.py` hace que los drivers de la red se nieguen a correr en cualquier otro caso (D-01).
- **Divulgación.** La investigación de la fase ya midió, antes de este protocolo, que Hebb da 0 % de recuperación sobre los 5 QR y que la pseudo-inversa es el remedio (`.planning/research/PITFALLS.md`, Pitfall 1). Este protocolo se reproduce honestamente a partir de esa medición, no se "descubre" mirando resultados nuevos; los umbrales de veredicto se fijan igual, antes de correr, para que el hallazgo no parezca ajustado a posteriori. El código de la red (núcleo en C, drivers y control en numpy) no forma parte de este preregistro: queda identificado por separado como `code_identity` (commit, indicador `dirty` y sha256 de los archivos de código), igual que en la Fase 4.
<!-- regla:fin -->

## 4. Hebb: estabilidad y curva de ruido

El criterio de éxito es el de la sección 3: solo cuenta el match exacto de los 1369 píxeles. El veredicto registrado en `verdict.json`, aplicando el umbral D-02 a la recuperación medida, es `hebb_fails = true`: «Hebb fails if exact recovery at noise 0 (async) < 100% (D-02); measured 0.00%» — y de hecho la tasa exacta es 0 % en los 11 niveles de ruido y en los dos modos (`recall.csv`, `recovery_table.csv`), incluido el nivel 0: los 5 QR **no son puntos fijos de Hebb ni sin ruido**. Con la consulta sin ruido, el modo asíncrono igual ejecuta 2 barridos y 143 actualizaciones en promedio (`mean_flips` = 143,0 de `recall.csv`) antes de converger.

**El atractor común.** El estado final no depende del nivel de ruido: `mean_final_overlap` (0,791) y `mean_final_energy` (−2 974 672) son los mismos en los 11 niveles y en los dos modos, y el 100 % de los ensayos termina clasificado como «otro» (`other_rate` = 1,0 en toda la grilla) — nunca almacenado, inverso ni mezcla. `qr_limits/majority.json` (figura `majority.svg`) identifica ese atractor: es la mayoría píxel a píxel de los 5 QR (signo de la suma por píxel), y difiere de los 5 QR almacenados por una distancia de Hamming siempre positiva — 225 píxeles de beverages y de dessert, 103 de specials, 91 de wine y 71 de food (de 1369) — nunca cero. El promedio de |0,671; 0,671; 0,896; 0,8495; 0,867| (los solapamientos de ese atractor con cada QR) da 0,791, el mismo número que `mean_final_overlap`: confirma de forma independiente que la red converge siempre a este único atractor, sin importar cuál de los 5 QR ni cuánto ruido tenga la consulta.

**Energía por paso (HOP-05).** `energy_trace.svg` traza la energía asíncrona paso a paso de un ensayo fijo por QR y nivel (0; 0,25; 0,50); en los 20 ensayos trazados la energía nunca sube (comprobado por el control de `analysis/hopfield.py`, igual que en la Fase 4), consistente con que cada corrida igual converge — solo que al atractor común, no al QR consultado.

**Costo dinámico.** El número de barridos (asíncrono) crece poco con el ruido, de 2,0 (nivel 0) a 2,9 (nivel 0,50); los flips promedio sí crecen, de 143 a 689, porque hay más píxeles que corregir desde una consulta más lejana del atractor. El modo síncrono tarda un poco más en el extremo de ruido alto (3,13 barridos y 874 flips en el nivel 0,50) por los ciclos de período 2, aunque el criterio de éxito es el mismo en los dos modos (match exacto) y ninguno lo logra nunca.

## 5. Pseudo-inversa frente a Hebb y a la línea base de Hamming

`verdict.json` registra `pinv_works = true`: «pinv works if exact recovery at noise 0 (async) == 100% (D-02); measured 100.00%» — los 5 QR son puntos fijos exactos de pseudo-inversa (`pinv_stored_fixed_noise0_async = 5`); con la consulta sin ruido el modo asíncrono converge en 1 barrido y 0 flips (`recall.csv`, `mean_sweeps` = 1,0, `mean_flips` = 0,0), muy distinto de los 143 flips de Hebb en el mismo nivel.

**`recovery.svg` y `recovery_table.csv`: recuperación exacta por nivel, las 3 reglas.**

| Nivel de ruido | hebb | pinv | hamming |
|---|---:|---:|---:|
| 0,00 | 0% | 100% | 100% |
| 0,05 | 0% | 100% | 100% |
| 0,10 | 0% | 100% | 100% |
| 0,15 | 0% | 100% | 100% |
| 0,20 | 0% | 100% | 100% |
| 0,25 | 0% | 100% | 100% |
| 0,30 | 0% | 100% | 100% |
| 0,35 | 0% | 99,9% | 100% |
| 0,40 | 0% | 97,3% | 98,5% |
| 0,45 | 0% | 69,4% | 81,5% |
| 0,50 | 0% | 0% | 16,7% |

pinv sostiene el 100 % de recuperación exacta hasta el nivel 0,30, cae apenas a 99,9 % en 0,35, a 97,3 % en 0,40, a 69,4 % en 0,45 y colapsa a 0 % en 0,50 — el mismo orden de magnitud que midió la investigación de la fase antes de esta corrida (`.planning/research/PITFALLS.md`, Pitfall 1). La línea base de Hamming (1-NN sin dinámica, D-08) sigue a pinv de cerca hasta el nivel 0,40 (98,5 % contra 97,3 %) y en los dos últimos niveles queda **por encima** de pinv, no por debajo: 81,5 % contra 69,4 % en el nivel 0,45, y 16,7 % contra 0 % en el nivel 0,50 — un lookup trivial sin dinámica iguala o incluso supera a la red dinámica en todo el rango de ruido evaluado (D-08, D-11).

**Energía y costo (D-09).** La energía final media de pinv es mucho menor en magnitud que la de Hebb (−684,5 en el nivel 0 contra −2 974 672: son escalas distintas, pinv no suma sobre N = 1369 enteros) y crece apenas con el ruido, hasta −668,8 en el nivel 0,50, mientras la tasa de recuperación cae de 100 % a 0 % en el mismo rango — la energía final por sí sola no distingue un estado recuperado de uno que no lo es. El número de barridos de pinv crece de 1,0 (nivel 0) a 2,8 (nivel 0,50), similar al de Hebb; los flips, de 0 a 674. Hamming no tiene barridos ni energía: es un lookup instantáneo (`recall.csv`, columnas `mean_sweeps` / `mean_final_energy` vacías en sus filas), la comparación de costo que ya adelanta la limitación de la sección 6.

## 6. Limitaciones del caso de uso

Las cuatro facetas de HOP-07, con evidencia medida y nunca forzada por la corrida (D-02, D-11):

**(a) Correlación entre los 5 QR, causa raíz del fallo de Hebb.** La sección 2 ya mostró que los 5 QR están lejos de ser ortogonales (máximo |solapamiento| 0,86, media 0,67, 69,8 % de píxeles idénticos en los 5, distancia mínima de Hamming 96 de 1369) y la sección 4 mostró que Hebb converge siempre al mismo atractor — la mayoría píxel a píxel de los 5 QR — que difiere de cada uno de ellos por entre 71 y 225 píxeles (`majority.svg`). Con N = 1369 y solo p = 5 patrones muy correlacionados, el remedio clásico de Hebb (0,138·N patrones no correlacionados, Pitfall 26) no aplica aquí: lo que falla no es la capacidad sino la correlación.

**(b) Sensibilidad a corrimientos (`shift.svg`, `qr_limits/shift.json`).** Se desplazó el QR de beverages 1 y 2 píxeles (relleno en cero, el borde vacante claro = −1) y se evolucionó cada consulta bajo la W de pseudo-inversa con una corrida asíncrona propia (no una traza de C: una implementación numpy a mano de la misma dinámica, saneada antes contra un QR sin desplazar, que queda fijo con 0 flips — de acuerdo con `stored.csv` fixed = 1). Los números, medidos y reportados tal cual salen, sin forzar la rotura que predice la investigación: con 1 píxel de corrimiento la distancia de Hamming de la consulta a la fuente ya es 741 de 1369 (54,1 %, más que cualquier nivel de ruido i.i.d. evaluado en la sección 5) y el estado recuperado por pinv queda a 1034 píxeles (75,5 %) — **más lejos** de la fuente que la propia consulta desplazada, en 2 barridos y 607 flips; con 2 píxeles, 699 (51,1 %) de consulta y 1198 (87,5 %) recuperado. Un corrimiento de apenas 1-2 píxeles ya mueve más de la mitad del QR porque su patrón fino (módulos de 1 píxel) no tiene ninguna redundancia espacial, y la dinámica de pinv — entrenada para los QR sin desplazar — no solo no corrige el corrimiento sino que aleja más el estado final. Esto confirma, con números y no solo en texto, la predicción de Pitfall 15: la recuperación píxel a píxel de Hopfield no tolera corrimientos ni cambios de escala, a diferencia del ruido i.i.d. de la sección 5.

**(c) Equivalencia con una tabla de búsqueda (D-08, D-11).** La curva de Hamming 1-NN de la sección 5 iguala o supera a pinv en los 11 niveles de ruido evaluados, sin ninguna dinámica ni energía: un lookup de 5 distancias de Hamming (`hamming_classify`, numpy puro) resuelve el mismo problema cerrado — reconocer cuál de 5 QR fijos corresponde a una consulta ruidosa — igual de bien o mejor que la red completa de 1369² pesos. La ventaja de Hopfield frente a un lookup trivial, en este caso de uso con solo 5 patrones conocidos de antemano, no está en la tasa de acierto.

**(d) Corrección de errores propia del QR — decodificación NO verificada (D-10).** El formato QR ya incluye su propia corrección Reed-Solomon (niveles L/M/Q/H, aproximadamente 7 %, 15 %, 25 % y 30 % de los módulos dañados según el nivel elegido al generar el código), independiente de cualquier red de Hopfield: en principio un QR real podría seguir escaneando con un porcentaje de píxeles mal incluso sin alcanzar el match exacto de la sección 5, y a la inversa, un estado recuperado píxel-exacto por pinv **no garantiza** que decodifique si, por ejemplo, el corrimiento de (b) desalineó los patrones de localización del QR. Esta fase **no corrió ningún decodificador de QR** (pyzbar, OpenCV u otro) sobre ninguna imagen recuperada: la decodificación real **no se verificó**, y cualquier afirmación sobre si un QR recuperado escanea o no queda fuera del alcance de este informe (D-10; el STATE del proyecto ya lo señala como un ítem abierto para una v2).

**Costo cuadrático y reentrenamiento.** W tiene N² = 1 874 161 entradas (1369 × 1369) para solo 5 patrones útiles; agregar un sexto QR exige reconstruir W entera (para pinv, además reinvertir la Gram) — no hay actualización incremental — mientras que el lookup de Hamming de (c) solo agrega una fila. El costo dinámico (barridos, energía) de la sección 5 tampoco compite con la consulta instantánea del lookup.

**Fuera de alcance.** El daño estructurado (oclusión de bloque, rayón, manchas) no se corrió como experimento en esta fase (D-04): el modelo de ruido es solo flips i.i.d. de píxeles (sección 3) y el corrimiento de (b); el daño estructurado queda nombrado aquí como una limitación más del caso de uso, no medida.

## 7. Cómo reproducir

Desde `TP4/`, en un clone nuevo:

```
make venv
make qr
make hopfield-qr
make hopfield-qr-limits
make hopfield-qr-figures
make test
```

- **`make venv`.** Crea `.venv` e instala `analysis/requirements.txt` (versiones fijadas); sin `uv`: `python3.12 -m venv .venv`, `.venv/bin/pip install -r analysis/requirements.txt` y `touch .venv/.installed`.
- **`make qr`.** Convierte los 5 QR de `datos/hopfield/*.png` a `datos/prepared/qr_pm1.csv` (±1) y su `.meta.json`; no corre la red (sección 2).
- **`make hopfield-qr`.** Corre Hebb y pseudo-inversa sobre los 5 QR fijados en la sección 3 (HOP-05, HOP-06); escribe `analysis/results/hopfield/qr/`. Se niega a correr si el protocolo, `scripts/qr.py` o los 5 PNG no están commiteados o cambiaron (D-01).
- **`make hopfield-qr-limits`.** Atractor mayoría de Hebb y sensibilidad a corrimientos de 1-2 píxeles bajo pinv (HOP-07, sección 6); escribe `analysis/results/hopfield/qr_limits/`, un directorio que `make hopfield-qr` nunca borra. Se niega a correr si el protocolo cambió.
- **`make hopfield-qr-figures`.** Seis figuras SVG y PNG (`qr`, `overlaps`, `recovery`, `energy_trace`, `shift`, `majority`); escribe `analysis/results/hopfield/qr/figures/`. Se niega a dibujar si el protocolo, el código de la red o el código de las limitaciones (`LIMITS_CODE_FILES`) cambiaron desde la corrida.
- **`make test`.** Tests de C (ASan/UBSan) y de Python (incluye los de Hopfield sobre QR, `analysis/tests/test_hopfield_qr.py`).

`analysis/results/` no se versiona: cada número y cada figura de este fragmento se regenera con estos comandos, y cada corrida, CSV, JSON y SVG es idéntico byte a byte en una reejecución para sus seeds. La verificación de que el protocolo de la sección 3 no cambió es `.venv/bin/python analysis/hopfield_qr_select.py identity`, que termina con código 0 mientras el texto entre los marcadores, `scripts/qr.py`, `analysis/hopfield_qr_select.py` y los 5 PNG sean los del commit de la regla.

**Qué fija la guardia y qué no.** La guardia (D-01) fija el protocolo del experimento, `scripts/qr.py` y los 5 PNG. El código de la red (el núcleo en C, los drivers y el control en numpy, incluido `analysis/hopfield_qr_limits.py` de este plan) no forma parte del preregistro: su identidad queda registrada por separado en `code_identity` de `run.json` (recall) y de `qr_limits/run.json` (limitaciones) — commit, indicador `dirty` y sha256 de cada archivo — y `make hopfield-qr-figures` se niega a dibujar si alguno cambió desde la corrida que informa este fragmento.
