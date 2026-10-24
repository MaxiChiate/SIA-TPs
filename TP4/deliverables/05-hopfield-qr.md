# Fase 5 — Hopfield: QR

Las secciones 1, 2 y 4 en adelante se escriben después de las corridas; la sección 3 se fijó antes de correr la red sobre los 5 códigos QR.

## 1. Algoritmo y salidas

*(Se completa en el Plan 05, después de correr la red sobre los QR.)*

## 2. Los 5 QR y su preparación

*(Se completa en los Planes 03-05: matriz de solapamientos 5×5, fracción de píxeles idénticos y distancia mínima de Hamming entre pares, a partir de `datos/prepared/qr_pm1.csv` generado por `scripts/qr.py`, HOP-04.)*

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

*(Se completa en el Plan 03/05, siguiendo el protocolo de la sección 3.)*

## 5. Pseudo-inversa frente a Hebb y a la línea base de Hamming

*(Se completa en el Plan 04/05, siguiendo el protocolo de la sección 3.)*

## 6. Limitaciones del caso de uso

*(Se completa en el Plan 05: correlación entre QR, sensibilidad a corrimientos, equivalencia con lookup, corrección de errores del QR en texto, HOP-07.)*

## 7. Cómo reproducir

*(Se completa en el Plan 05.)*
