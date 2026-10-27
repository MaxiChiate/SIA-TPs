# Fase 2 — Mapa de Kohonen (SOM) de los 50 creadores

## 1. Algoritmo y salidas

El modelo es un mapa autoorganizado de Kohonen con grilla rectangular de k × k neuronas. Cada neurona tiene un vector de pesos en las 26 variables auditadas con z-score (`datos/prepared/creadores_zscore.csv`, sección 4 de `deliverables/01-datos-pca.md`), y la distancia entre un creador y una neurona es la euclídea en ese espacio (D-05). La distancia en la grilla entre dos neuronas es la euclídea entre sus posiciones (fila, columna). El código está en C (`neuron/models/kohonen.c`), sin librerías de aprendizaje automático, y lo corre `neuron/build/neuron` con una config estricta de siete claves: `grid_k`, `neighborhood`, `radius0`, `radius_final`, `eta0`, `eta_final` y `epochs`.

**Inicialización.** Los pesos de cada neurona arrancan como una copia de un creador elegido al azar del conjunto de entrenamiento, que es la recomendación de las slides para evitar unidades muertas (D-05). Con k² mayor que 50 creadores (k = 8 tiene 64 neuronas) el orden de creadores se vuelve a barajar cada vez que se agota.

**Orden y cantidad de pasos.** El entrenamiento va por épocas. En cada época se recorren los 50 creadores en un orden barajado con el generador de la seed de la corrida (splitmix64 de la Fase 1), de modo que la misma seed da los mismos bytes. El total de pasos es T = épocas × n (D-03). El baseline de 260 épocas da unos 13 000 pasos, del orden de los 500·N del curso con N = 26.

**Tasa de aprendizaje.** η decrece exponencialmente de η0 a ηf: η(t) = η0 · (ηf / η0)^(t / (T − 1)), con η0 < 1 (D-02).

**Vecindad.** Hay dos modos, elegidos por la clave `neighborhood` (D-01). El radio R (en el modo escalón) y σ (en el gaussiano) decrecen con la misma forma exponencial que η, desde `radius0` hasta `radius_final`, y nunca bajan de `radius_final`.

- *Escalón* (camino principal, el del curso). Se actualizan las neuronas cuya distancia en la grilla a la ganadora cumple `||n − n_k|| ≤ R(t)`. Las slides del curso escriben N_k(i) = {n / ||n − n_k|| < R(i)} con `<` estricto (p. 26) y fijan R = 1 para la grilla rectangular de 4 vecinos (p. 15); con el `<` estricto, R = 1 deja solo a la ganadora. Este TP usa `≤` a propósito (D-01), para que R = 1 actualice a la ganadora y a sus cuatro vecinas pegadas; las diagonales (a distancia √2) entran recién cuando R ≥ √2. R(0) es configurable y baja hasta 1 inclusive.
- *Gaussiano* (variante de comparación). El peso de una neurona a distancia d de la ganadora es h = exp(−d² / 2σ²), con σ decreciente y un piso mayor que 0, nunca 0.

**Regla de actualización.** Para cada creador x con ganadora n_k, todas las neuronas j se actualizan con W_j ← W_j + η(t) · h_j · (x − W_j), con h_j ∈ {0, 1} en el modo escalón y h_j = exp(−d² / 2σ²) en el gaussiano.

**Salidas de cada corrida.**

- **QE** (error de cuantización): distancia euclídea media de cada creador a su neurona ganadora (BMU), en unidades z.
- **TE** (error topográfico): fracción de creadores cuya primera y segunda BMU no son vecinas de 4 (D-04). Una diagonal cuenta como error, por lo que en una grilla de 2 × 2 el TE puede ser mayor que 0.
- **Ocupación por neurona** (`occupancy.csv`): cantidad de creadores que caen en cada neurona, con fila y columna. De ahí salen las neuronas ocupadas, la fracción de neuronas vacías, los creadores por neurona ocupada y las neuronas con un solo creador.
- **Traza por época** (`trace.csv`): η, R, QE y TE al final de cada época, para ver si el entrenamiento se aplanó.
- Además, `prototypes.csv` (pesos de cada neurona), `assignments.csv` (BMU y segunda BMU de cada creador, con su distancia) y `metrics.json`.

## 2. Regla de elección de grilla (fijada antes de mirar resultados)

<!-- regla:inicio -->
Esta sección fija la regla; los resultados se agregan después y no figuran acá. Las decisiones D-10 a D-15 están en `.planning/phases/02-kohonen-som/02-CONTEXT.md` y los términos que dejaban abiertos se fijaron en el checkpoint del plan 02-03, antes de que existiera ninguna corrida de la etapa 1. Al momento de commitear esta sección no se había corrido ningún SOM entrenado sobre los datos de los creadores: el modelo de Kohonen de la Fase 1 era un stub sin entrenamiento, y el SOM entrenado (plan 02-01) se construye después de este commit.

- **Barrido (etapa 1).** k de 2 a 8 × {escalón, gaussiana}, seeds 1 a 10, R0 = σ0 = max(1, k/2), `radius_final` 1 en los dos modos, η 0,5 → 0,01, 260 épocas; el archivo es `analysis/series_som_stage1.json` (D-06, D-07, D-08). Son 14 configuraciones × 10 seeds = 140 corridas.
- **Medidas por seed.** Para cada corrida se toman TE, la fracción de neuronas vacías = 1 − ocupadas / k² y los creadores por neurona ocupada = 50 / ocupadas. Cada filtro lee la media sobre las 10 seeds de esos valores por seed (la media de los cocientes por seed, no 50 / media de ocupadas). A eso se suma el QE-LOO por seed = promedio sobre los 50 folds (leave-one-out exacto, 50 entrenamientos con un creador excluido y la distancia del excluido a su BMU) y, por configuración, la media y el desvío (ddof 1) de los 10 valores por seed (D-09).
- **Filtros.** Solo sobre las corridas de escalón (D-11, D-12). Se descarta una k si el TE medio es > 0,05, si la fracción media de neuronas vacías es > 20 % o si la media de creadores por neurona ocupada es < 2. La igualdad pasa: un TE medio de exactamente 0,05, un 20 % exacto de vacías y exactamente 2 creadores por neurona ocupada no excluyen.
- **Ganadora y desempate.** Entre las k que pasan los tres filtros gana la de menor QE-LOO medio; si dos tienen exactamente el mismo QE-LOO medio, la k más chica. La banda de desempate es la ganadora más toda k sobreviviente cuyo QE-LOO medio supera al de la ganadora en estrictamente menos que el desvío (ddof 1) de los 10 QE-LOO por seed de la ganadora. Dentro de la banda gana la de mayor estabilidad media entre seeds; si la estabilidad es exactamente igual, la k más chica (D-11, pasos 2 y 3). Si el desvío de la ganadora es 0, la banda tiene solo a la ganadora.
- **Estabilidad.** Para cada seed se arma el vector de las 1225 distancias en la grilla entre las BMU de cada par de creadores (50 · 49 / 2 pares), con distancia euclídea entre las coordenadas (fila, columna) de las BMU. La estabilidad es el promedio del Spearman con rangos promedio para los empates entre esos vectores, sobre los 45 pares de seeds (D-13). Los pares de seeds con Spearman indefinido (NaN, por ejemplo si todos los creadores caen en una neurona) se descartan del promedio y se cuentan; si todos los pares son NaN, la estabilidad vale 0.
- **Si ninguna grilla pasa.** Si ninguna k de escalón pasa los tres filtros, se quita solo el filtro de TE, se aplica el resto de la regla sin cambios y el informe dice que ninguna grilla cumplió TE ≤ 0,05 (D-14). La ocupación no se relaja nunca. Si ninguna k pasa los dos filtros de ocupación ni siquiera sin el de TE, no se elige ninguna grilla: el informe lista el filtro que falla en cada k, no se producen figuras de mapa, regiones ni contraste con la PCA, y la fase se detiene hasta que una nueva discusión decida cómo seguir.
- **QE de entrenamiento.** Se reporta y se grafica contra k, pero nunca decide (D-15). Por QE de entrenamiento solo ganaría la grilla más grande, porque con más neuronas el error siempre baja; por eso la elección usa el QE-LOO y los filtros.
- **Gaussiana.** Se corre con el mismo R0 = σ0 y el mismo piso (`radius_final` = 1) que el escalón, de modo que solo cambia la forma del núcleo. Se reporta al lado como comparación y no entra en la elección, ni siquiera con un QE-LOO menor.
- **Corridas fallidas.** Cualquier corrida fallida, o cualquier entrenamiento fallido del leave-one-out, detiene la selección: no se elige nada con datos parciales.
- **Consecuencia aritmética.** Si todas las seeds tuvieran la misma ocupación, k ≥ 6 no podría pasar D-12: al menos 2 creadores por neurona ocupada exige a lo sumo 25 neuronas ocupadas, y a lo sumo 20 % de vacías exige al menos 0,8 k² ocupadas; las dos juntas solo valen si k² ≤ 31,25. Con k = 5 solo pasaría con entre 20 y 25 neuronas ocupadas. Como el filtro promedia cocientes por seed, seeds muy distintas podrían igual dejar pasar una k mayor; por eso la regla se aplica a k = 6, 7 y 8 como a las demás, y esas filas dibujan además la curva de QE contra ocupación (D-07).
- **Advertencias del QE-LOO.** El z-score se ajustó con los 50 creadores, el excluido incluido (una fuga leve, declarada y no corregida). Cada fold conserva la seed y las épocas de la corrida, por lo que T = épocas × 49.
- **Semilla de las figuras.** Entre las 10 seeds de la k elegida, la semilla de las figuras es el medoide de estabilidad: la de mayor Spearman medio con las otras nueve, la menor seed si hay empate. La orientación del mapa es arbitraria (rotación y reflexión no cambian nada de lo medido).
- **Regiones.** Las regiones son las componentes conexas, con adyacencia de 4, de las neuronas ocupadas, después de cortar toda arista de 4 vecinos cuya distancia entre prototipos supere el percentil 75 de las distancias entre prototipos de todas las aristas de 4 vecinos del mapa. Las regiones con menos de 2 creadores se rotulan "no interpretable". Los perfiles se calculan en unidades originales con los valores crudos de los creadores de cada región; las neuronas con menos de 2 creadores se marcan. Los temas son entradas del mapa y nunca "validan" una región.
- **Contraste con PC1/PC2.** Los estadísticos se declaran ahora. R² de PC1 y de PC2 regresados sobre la (fila, columna) de la BMU, con un nulo de 1000 permutaciones. Spearman con rangos promedio (tipo Mantel) entre las distancias en la grilla y las distancias en el plano PC1-PC2, con la distancia z de 26 dimensiones como referencia. Spearman por aristas entre las aristas de la matriz U y las diferencias de PC1 y de PC2 entre las medias por neurona. El generador de permutaciones se siembra con 2026.
- **Etapa 2.** Sobre la k elegida, en el modo escalón, el baseline (R0 = max(1, k/2), η0 = 0,5, 260 épocas) más un cambio a la vez, 10 seeds: R0 en {max(1, k/4), k}, η0 en {0,1; 0,25; 0,9}, épocas en {50, 130, 520, 1040}; se descarta todo valor igual al del baseline. `analysis/series_som_stage2.json` se genera de esta lista con `analysis/som_stage.py` (plan 02-04) para la k elegida y se commitea antes de correr.
- **Criterio de robustez.** La elección es robusta si la k elegida pasa los mismos filtros en cada variante de la etapa 2. La etapa 2 nunca vuelve a elegir k. Si en la etapa 1 se quitó el filtro de TE, la robustez revisa solo los filtros de ocupación.
- **Control.** `analysis/som_stage.py` se niega a correr mientras este archivo, `analysis/som_select.py` (la regla como código: umbrales, filtros, `select_grid` y escaleras) o el archivo de la serie estén sin trackear o con cambios sin commitear. `selection.json` registra el hash del commit y el sha256 del texto entre los marcadores, más el hash del commit y el sha256 de `analysis/som_select.py`, y los pasos posteriores se niegan a correr si cambia cualquiera de los dos sha256.
<!-- regla:fin -->


## 3. Etapa 1: resultados y grilla elegida

Las cifras salen de `analysis/results/som/series_som_stage1/` (`aggregate.csv`, `selection.json`), que escribe `make som-stage1`. La regla de la sección 2 se aplicó sin cambios: el comando se negaría a correr con el texto de la regla, `analysis/som_select.py` o la serie de la etapa 1 sin commitear, y `selection.json` guarda el commit que agregó la regla y el sha256 de su texto y de su código. Son 14 configuraciones × 10 seeds = 140 corridas y 7 000 entrenamientos de leave-one-out (50 por corrida); ninguno falló. Todas las cifras son media ± desvío (ddof 1) sobre las 10 seeds, nunca una seed sola (D-08); la estabilidad es un promedio sobre pares de seeds, por lo que su desvío es el de los 45 pares. QE y QE-LOO están en unidades z.

**Escalón (camino de la elección).** La columna "filtros" dice cuáles de los tres filtros de la sección 2 (TE ≤ 0,05, vacías ≤ 20 %, creadores por neurona ocupada ≥ 2) pasa la media de cada k.

| k | QE | QE-LOO | TE | % de neuronas vacías | creadores por neurona ocupada | estabilidad | filtros |
|---|---|---|---|---|---|---|---|
| 2 | 3,802 ± 0,003 | 3,944 ± 0,004 | 0,180 ± 0,000 | 0,0 ± 0,0 | 12,50 ± 0,00 | 0,993 ± 0,013 | falla TE |
| 3 | 3,318 ± 0,011 | 3,638 ± 0,009 | 0,190 ± 0,082 | 0,0 ± 0,0 | 5,56 ± 0,00 | 0,766 ± 0,212 | falla TE |
| 4 | 3,012 ± 0,011 | 3,422 ± 0,017 | 0,030 ± 0,039 | 1,2 ± 2,6 | 3,17 ± 0,09 | 0,791 ± 0,160 | los tres |
| 5 | 2,732 ± 0,033 | 3,295 ± 0,023 | 0,046 ± 0,034 | 15,6 ± 7,9 | 2,39 ± 0,25 | 0,672 ± 0,182 | los tres |
| 6 | 2,510 ± 0,022 | 3,253 ± 0,023 | 0,016 ± 0,018 | 17,2 ± 4,5 | 1,68 ± 0,09 | 0,624 ± 0,124 | falla creadores |
| 7 | 2,165 ± 0,080 | 3,226 ± 0,025 | 0,006 ± 0,010 | 41,4 ± 3,5 | 1,75 ± 0,10 | 0,576 ± 0,167 | falla vacías y creadores |
| 8 | 1,918 ± 0,064 | 3,213 ± 0,015 | 0,002 ± 0,006 | 48,1 ± 2,7 | 1,51 ± 0,08 | 0,573 ± 0,143 | falla vacías y creadores |

**Gaussiana (comparación, no entra en la elección, D-11).** Mismo R0 = σ0, mismo piso y mismas seeds. La columna "filtros" es solo informativa: la regla no la usa.

| k | QE | QE-LOO | TE | % de neuronas vacías | creadores por neurona ocupada | estabilidad | filtros |
|---|---|---|---|---|---|---|---|
| 2 | 4,123 ± 0,001 | 4,253 ± 0,002 | 0,160 ± 0,000 | 0,0 ± 0,0 | 12,50 ± 0,00 | 0,992 ± 0,008 | falla TE |
| 3 | 3,449 ± 0,003 | 3,683 ± 0,005 | 0,358 ± 0,006 | 10,0 ± 3,5 | 6,18 ± 0,22 | 0,968 ± 0,060 | falla TE |
| 4 | 3,159 ± 0,005 | 3,502 ± 0,006 | 0,200 ± 0,028 | 8,8 ± 3,2 | 3,43 ± 0,12 | 0,877 ± 0,077 | falla TE |
| 5 | 2,935 ± 0,008 | 3,401 ± 0,015 | 0,128 ± 0,041 | 17,6 ± 3,9 | 2,43 ± 0,12 | 0,881 ± 0,105 | falla TE |
| 6 | 2,758 ± 0,011 | 3,300 ± 0,009 | 0,074 ± 0,025 | 29,7 ± 5,6 | 1,99 ± 0,15 | 0,823 ± 0,109 | falla TE y vacías y creadores |
| 7 | 2,594 ± 0,014 | 3,272 ± 0,015 | 0,032 ± 0,021 | 39,6 ± 1,7 | 1,69 ± 0,05 | 0,767 ± 0,148 | falla vacías y creadores |
| 8 | 2,442 ± 0,019 | 3,226 ± 0,017 | 0,022 ± 0,015 | 46,4 ± 1,8 | 1,46 ± 0,05 | 0,780 ± 0,148 | falla vacías y creadores |

**Cómo siguió la regla.** Con el escalón, k = 2 y k = 3 quedan fuera por TE (0,180 y 0,190, contra el máximo de 0,05) aunque ocupan todas sus neuronas; k = 6 pasa TE y vacías pero queda en 1,68 creadores por neurona ocupada (mínimo 2); k = 7 y k = 8 quedan fuera por las dos medidas de ocupación (41,4 % y 48,1 % de neuronas vacías). Sobrevivieron k = 4 y k = 5, de modo que el filtro de TE no se quitó (el paso de D-14 no hizo falta). Entre ellas gana la de menor QE-LOO medio, k = 5 (3,295 contra 3,422 de k = 4). La banda de desempate es la ganadora más toda k sobreviviente a menos de un desvío del QE-LOO por seed de la ganadora (0,023): k = 4 está a 0,127, más de cinco desvíos, así que la banda tiene solo a k = 5 y decide el QE-LOO, sin pasar por la estabilidad. La estabilidad de k = 5 (0,672) es menor que la de k = 4 (0,791); la regla fijada antes de mirar no la usa fuera de la banda, y se informa como una limitación de la elegida. Otra limitación: k = 5 pasa TE por poco en promedio (0,046) y con un desvío de 0,034 entre seeds (3 de las 10 seeds quedan por encima de 0,05); también pasa por poco el mínimo de creadores por neurona ocupada (2,39 contra 2). La etapa 2 mide cuánto de esto depende del schedule.

- Grilla elegida: k = 5
- Commit de la regla: ea7a0b11202d
- Por QE de entrenamiento solo se elegiría: k = 8
- Semilla de las figuras: 4

El QE de entrenamiento no decide (D-15): baja siempre al agrandar la grilla y por sí solo elegiría k = 8, que deja 48,1 % de neuronas vacías y 1,51 creadores por neurona ocupada. La semilla de las figuras es el medoide de estabilidad de k = 5 (sección 2), y la orientación del mapa es arbitraria.


## 4. Etapa 2: robustez del schedule

Las cifras salen de `analysis/results/som/series_som_stage2/` (`aggregate.csv`, `robustness.csv`, `robustness.json`), que escribe `make som-stage2` sobre `analysis/series_som_stage2.json`. Ese archivo lo generó `analysis/som_stage.py write-stage2` a partir de la k elegida (k = 5) y de las escaleras de la sección 2, y se commiteó antes de correr. Sobre k = 5 con el escalón se cambia una cosa a la vez respecto del baseline (R0 = 2,5; η0 = 0,5; 260 épocas): R0 en {1,25; 5}, η0 en {0,1; 0,25; 0,9} y épocas en {50; 130; 520; 1040}, con 10 seeds cada variante (10 variantes × 10 seeds = 100 corridas y 5 000 entrenamientos de leave-one-out; ninguno falló, D-06). Todas las cifras son media ± desvío (ddof 1) sobre las 10 seeds; en la estabilidad, sobre los 45 pares de seeds. La fila `base` repite la fila k = 5 de la sección 3.

| variante | R0 | η0 | épocas | TE | % de neuronas vacías | creadores por neurona ocupada | pasa los filtros | QE-LOO | estabilidad |
|---|---|---|---|---|---|---|---|---|---|
| base | 2,5 | 0,5 | 260 | 0,046 ± 0,034 | 15,6 ± 7,9 | 2,39 ± 0,25 | sí | 3,295 ± 0,023 | 0,672 ± 0,182 |
| radius0-1.25 | 1,25 | 0,5 | 260 | 0,034 ± 0,030 | 7,2 ± 4,1 | 2,16 ± 0,10 | sí | 3,334 ± 0,020 | 0,607 ± 0,113 |
| radius0-5 | 5 | 0,5 | 260 | 0,056 ± 0,023 | 14,4 ± 8,0 | 2,36 ± 0,24 | no (TE) | 3,293 ± 0,011 | 0,603 ± 0,174 |
| eta0-0.1 | 2,5 | 0,1 | 260 | 0,046 ± 0,038 | 14,0 ± 6,9 | 2,34 ± 0,21 | sí | 3,336 ± 0,016 | 0,589 ± 0,161 |
| eta0-0.25 | 2,5 | 0,25 | 260 | 0,060 ± 0,021 | 14,4 ± 4,7 | 2,34 ± 0,12 | no (TE) | 3,305 ± 0,015 | 0,693 ± 0,156 |
| eta0-0.9 | 2,5 | 0,9 | 260 | 0,052 ± 0,017 | 9,2 ± 3,8 | 2,21 ± 0,09 | no (TE) | 3,300 ± 0,020 | 0,612 ± 0,150 |
| epochs-50 | 2,5 | 0,5 | 50 | 0,056 ± 0,028 | 12,0 ± 6,5 | 2,28 ± 0,18 | no (TE) | 3,299 ± 0,025 | 0,565 ± 0,099 |
| epochs-130 | 2,5 | 0,5 | 130 | 0,042 ± 0,027 | 12,4 ± 8,5 | 2,31 ± 0,26 | sí | 3,307 ± 0,015 | 0,621 ± 0,138 |
| epochs-520 | 2,5 | 0,5 | 520 | 0,056 ± 0,016 | 12,8 ± 3,2 | 2,30 ± 0,08 | no (TE) | 3,299 ± 0,014 | 0,623 ± 0,151 |
| epochs-1040 | 2,5 | 0,5 | 1040 | 0,050 ± 0,017 | 16,4 ± 6,1 | 2,41 ± 0,20 | sí | 3,288 ± 0,013 | 0,642 ± 0,192 |

**Cómo se mueven QE-LOO y estabilidad.** El QE-LOO casi no se mueve: va de 3,288 (1040 épocas) a 3,336 (η0 = 0,1), una franja de 0,05 que es del orden de dos desvíos del baseline (0,023). Con más épocas queda plano (3,299; 3,307; 3,295; 3,299; 3,288 para 50, 130, 260, 520 y 1040), y un R0 más chico (1,25) o un η0 más bajo (0,1) lo suben algo (3,334 y 3,336), mientras que R0 = 5 y η0 = 0,25 o 0,9 quedan junto al baseline. La estabilidad se mueve más: el baseline (0,672) es de las más altas, solo η0 = 0,25 la supera (0,693), y las demás variantes quedan entre 0,565 (50 épocas) y 0,642 (1040 épocas); con las épocas sube de 50 a 130 y 1040 pero no de forma monótona (0,565; 0,621; 0,672; 0,623; 0,642). Con un desvío de unos 0,15 a 0,20 entre pares de seeds, estas diferencias son chicas frente a la dispersión y no sostienen ordenar los schedules.

**Qué falla.** Los dos filtros de ocupación pasan en las 10 variantes (neuronas vacías entre 7,2 % y 16,4 %, creadores por neurona ocupada entre 2,16 y 2,41). Lo que falla es el TE: en cinco variantes (R0 = 5, η0 = 0,25, η0 = 0,9, 50 épocas y 520 épocas) el TE medio queda entre 0,052 y 0,060, apenas sobre el máximo de 0,05, con desvíos de 0,016 a 0,028. El baseline ya estaba pegado al borde (0,046), así que la conclusión es que el TE de k = 5 depende del schedule en esa franja, y no que la ocupación se degrade. No hay una tendencia clara: 520 y 1040 épocas dan 0,056 y 0,050.

- Veredicto de robustez: no robusta (radius0-5, eta0-0.25, eta0-0.9, epochs-50, epochs-520)

La etapa 2 no vuelve a elegir k (sección 2, **Criterio de robustez.**): k = 5 sigue siendo la grilla elegida, y el veredicto dice cuánto de su cumplimiento del filtro de TE se sostiene al mover R0, η0 o las épocas.

## 5. Mapa de la grilla elegida

Las figuras salen de `analysis/results/som/figures/`, que escribe `make som-figures` (necesita el `selection.json` de `make som-stage1`; se niega a correr si el sha256 de la regla cambió o si no hay grilla elegida). Se dibuja una sola corrida: la de k = 5 (`k5-step`), con seed 4, que es el medoide de estabilidad entre las 10 seeds (sección 2), no la que mejor se vea. La orientación del mapa es arbitraria: rotarlo o reflejarlo no cambia ninguna medida, así que "arriba" o "a la izquierda" solo describen estas figuras. Las posiciones se nombran (fila, columna) con la fila 0 arriba. Volver a correr `make som-figures` da SVG idénticos byte a byte; `hits_members.csv` lista los creadores de cada neurona.

**`map.svg`: creadores por neurona y matriz U, lado a lado.** A la izquierda, el número de creadores cuya mejor neurona (BMU) es cada celda; las celdas rayadas son neuronas vacías. Hay 3 neuronas vacías de 25 ((0,3), (1,2) y (3,3)), 7 con un solo creador ((0,1), (1,0), (1,4), (2,1), (2,3), (3,1) y (3,2)) y el máximo es 5 creadores en (0,0); los 50 creadores se reparten en 22 neuronas ocupadas (12 % vacías, 2,27 creadores por neurona ocupada en esta corrida). Una neurona con un solo creador es un caso aislado, no un grupo, y se lee con cautela. A la derecha, la matriz U: cada celda es la distancia media (en unidades z de las 26 variables) entre el prototipo de la neurona y los de sus vecinos de 4, con la escala completa de 1,59 a 2,97 sin recortar. Un valor alto es un salto entre prototipos vecinos; uno bajo, prototipos parecidos. Los valores más bajos están en las esquinas ((4,4) 1,59; (3,4) 1,68; (0,4) 1,72; (0,0) 1,75) y los más altos en la zona central y derecha, con el máximo en (2,4) (2,97), una neurona ocupada por 2 creadores cuya arista a (1,4) mide 3,67, la más larga del mapa y entre dos neuronas ocupadas. Las tres neuronas vacías caen en los lugares 2, 3 y 8 de 25 en U (2,81; 2,72 y 2,45), y cuatro de las seis aristas más largas tocan una neurona vacía (3,63; 3,59; 3,47 y 3,20): ese muro es interpolación (el prototipo de una neurona vacía queda entre los de sus vecinos porque ningún creador lo reclama) y no un límite entre dos grupos de creadores. Solo un salto entre neuronas ocupadas, como (1,4)-(2,4), apoya una frontera.

**`planes_main.svg`: planos de componentes principales.** Cada celda de un plano muestra el valor de una variable en el prototipo de la neurona; las ocho primeras comparten una sola escala en z centrada en 0 (rojo: por encima del promedio de los 50 creadores, azul: por debajo). Las variables son las 4 de mayor |carga| en PC1 (`average_caption_words`, `average_impressions`, `average_video_views`, `average_reach`) y las 4 siguientes distintas de mayor |carga| en PC2 (`argentina_audience_pct`, `estimated_argentina_reach`, `topic_dogs_pct`, `monthly_posts`), con la orientación de signos de la Fase 1; se fijaron por esa regla antes de mirar el mapa. En esta corrida, `average_impressions`, `average_video_views`, `average_reach` y `estimated_argentina_reach` son altas en la esquina inferior derecha ((4,4), (3,4), (4,3); hasta 1,82 a 1,91 en z) y bajas en la esquina superior izquierda ((0,0), (0,1), (1,0); entre -0,68 y -0,95); `average_caption_words` va al revés (1,47 en (0,0); -1,24 en (3,4)). `topic_dogs_pct` es alta a lo largo de la fila superior ((0,0), (0,1), (0,2); hasta 1,35) y baja hacia el centro y la derecha, por ejemplo en (2,2) y (2,4). `monthly_posts` es alta en (0,4), (0,2) y (4,1) (hasta 0,94) y baja en la columna izquierda ((0,0), (1,0), (2,0); hasta -0,83). `argentina_audience_pct` es alta en (0,0) (0,93), también en (4,4) y (2,2), y baja en la fila inferior ((4,1), (4,0), (4,2); hasta -0,78). Los dos planos de abajo, `topic_art_pct` y `content_showcase_pct`, no se entrenaron (están excluidos por sumar 100 con los otros de su grupo): se muestran como la media cruda, en %, de los creadores de cada neurona, con su propia escala, y en blanco rayado donde la neurona está vacía. `topic_art_pct` llega a 65,2 % en (4,0) y también es alta en (4,1) y (1,4), y baja (4,3 %) en el centro ((2,3), (2,2), (2,4)); `content_showcase_pct` llega a 29,6 % en (4,1), (2,1) y (4,0), y baja a 2,3 % en (4,3). Como cada media sale de 1 a 5 creadores, una media cruda de una neurona con un solo creador es el valor de ese creador.

**`planes_appendix.svg`: planos de todas las variables.** Mismo dibujo, con las 26 variables entrenadas en z (escala común centrada en 0) y las 5 excluidas (`price_ars`, `organic_posts_pct`, `total_engagement_per_1000`, `topic_art_pct`, `content_showcase_pct`) como media cruda con su unidad (ARS, %, por 1000). Sirve para buscar una variable que no entró en el plano principal y para ver qué variables se mueven juntas sobre el mapa; no se eligió ninguna por cómo se ve, y qué regiones se forman y cómo se parecen a PC1 y PC2 es la sección 6, no esta.

**`stage1_curves.svg`: por qué el QE solo no decide.** Seis paneles contra k (2 a 8), media ± desvío entre las 10 seeds, escalón y gaussiana: QE de entrenamiento, QE-LOO, TE, % de neuronas vacías, creadores por neurona ocupada y estabilidad, con los umbrales de la regla (TE 0,05; 20 % de vacías; 2 creadores por neurona ocupada), la k elegida marcada y el mínimo del QE de entrenamiento anotado. El QE de entrenamiento del escalón baja sin parar con k, de 3,802 (k = 2) a 1,918 (k = 8), y por sí solo elegiría k = 8 (D-07, D-15); en el mismo tramo las neuronas vacías suben de 0 % a 48,1 % y los creadores por neurona ocupada bajan de 12,5 a 1,51, o sea que la grilla grande baja el error repartiendo los 50 creadores en neuronas casi individuales. El QE-LOO baja mucho menos de k = 5 en adelante (3,295 en k = 5; 3,253 en k = 6) y la estabilidad cae con k. Los umbrales de la regla valen para el escalón; la gaussiana se muestra como comparación. La elección sale de los filtros de ocupación y TE más el QE-LOO, no de esta curva.

**`trace.svg`: entrenamiento de la corrida dibujada.** QE (eje izquierdo) y TE (eje derecho) en cada una de las 260 épocas. Las dos medidas oscilan mucho al principio (en las primeras 60 épocas el TE llega a 0,68 y el QE a 3,95 en la época 7); el TE cae a entre 0,02 y 0,20 desde la época 65 y vale 0,06 sin cambios desde la época 175, y el QE queda entre 2,85 y 3,00 hasta la época 160 y baja a 2,72 hacia la 180. En el último 10 % de las épocas (de la 235 a la 260) las dos medidas quedan planas: el QE varía entre 2,7224 y 2,7239 y el TE vale 0,06 en todas. QE y TE finales de la corrida dibujada (2,724 y 0,06) quedan cerca de lo que muestran las 10 seeds de la sección 3 (QE de entrenamiento medio 2,732; TE medio 0,046 ± 0,034): esta seed no es un caso extremo en esas dos medidas.

## 6. Regiones, perfiles y contraste con PC1/PC2

Las cifras salen de `analysis/results/som/profiles/` (`regions.csv`, `region_profiles.csv`, `neuron_profiles.csv`, `pca_contrast.json`, `high_u_edges.csv`, `disagreements.csv`), que escribe `make som-profiles` sobre la misma corrida de la sección 5 (k = 5, `k5-step`, seed 4). El script se niega a correr si el sha256 de la regla cambió desde la etapa 1 o si no hay grilla elegida. La regla de regiones y los estadísticos del contraste son los de la sección 2, aplicados sin cambios: no se tocó el percentil, el mínimo de 2 creadores, el número de permutaciones (1000) ni la semilla (2026) después de ver el resultado.

### 6.1 Regiones

El percentil 75 de las 40 distancias entre prototipos de neuronas vecinas de la grilla vale 2,60, y esa es la distancia de corte (`pca_contrast.json`, `threshold`). Superan el umbral 10 aristas. Cinco de ellas tocan una neurona vacía ((0,3)-(1,3), (1,2)-(1,3), (1,2)-(2,2), (2,3)-(3,3) y (3,2)-(3,3)) y no separan nada: una neurona vacía no pertenece a ninguna región. Las otras cinco unen neuronas ocupadas: (1,4)-(2,4) con 3,67, (2,3)-(2,4) con 2,99, (2,1)-(2,2) con 2,98, (2,1)-(3,1) con 2,88 y (3,1)-(3,2) con 2,66. Con esos cortes, las 22 neuronas ocupadas siguen conectadas entre sí por aristas que no se cortaron, así que la regla da **una sola región, R1, con los 50 creadores**, que es interpretable (50 creadores, más de 2). No hay regiones ni neuronas rotuladas "no interpretable" por tamaño de región.

Este es el resultado de la regla fijada de antemano y se informa como salió: con la regla de la sección 2, el mapa de 5 × 5 no se parte en grupos de creadores. Cambiar el percentil para obtener más regiones sería elegir la regla mirando el mapa, que es lo que la sección 2 prohíbe. La figura es `analysis/results/som/profiles/regions.svg` (celdas con su región y su número de creadores, neuronas vacías rayadas, las aristas cortadas como líneas gruesas). Ninguna de las cinco aristas cortadas entre neuronas ocupadas deja una neurona ocupada aislada.

### 6.2 Perfiles por región

Perfil de R1 en unidades originales, con las medias crudas de los 50 creadores (`region_profiles.csv` trae las 31 columnas de `datos/creadores.csv`). La última columna es la participación de cada tema dominante, solo descriptiva: los temas son entradas del mapa y su reparto no valida ninguna región.

| Región | Creadores | Seguidores | Alcance en Argentina | Audiencia argentina (%) | Engagement por 1000 | Precio (USD) | Patrocinados (%) | Fútbol (%) | Maquillaje (%) | Perros (%) | Arte (%) | Tema dominante |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 (22 neuronas) | 50 | 221 587 | 43 984 | 52,6 | 68,3 | 1 701 | 27,4 | 27,0 | 24,2 | 27,0 | 21,8 | fútbol (15 de 50) |

Como R1 es todo el mapa, su perfil es el del creador promedio y no distingue grupos. Para leer cómo cambian los perfiles dentro del mapa se dan también los perfiles de las neuronas con al menos 2 creadores (`neuron_profiles.csv`). Son neuronas, no regiones: describen dónde está cada tipo de creador sobre la grilla y no son grupos validados.

| Neurona (fila, col) | Creadores | Seguidores | Alcance en Argentina | Audiencia argentina (%) | Engagement por 1000 | Precio (USD) | Patrocinados (%) | Fútbol (%) | Maquillaje (%) | Perros (%) | Arte (%) | Tema dominante |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| (0, 0) | 5 | 21 612 | 3 448 | 73,6 | 59,7 | 175 | 15,9 | 8,7 | 11,1 | 69,4 | 10,8 | perros (5 de 5) |
| (0, 2) | 4 | 49 736 | 7 201 | 48,2 | 67,8 | 349 | 11,6 | 11,4 | 10,4 | 56,7 | 21,4 | perros (3 de 4) |
| (0, 4) | 4 | 175 422 | 25 097 | 54,3 | 71,6 | 880 | 7,5 | 8,4 | 38,4 | 26,4 | 26,8 | maquillaje (2 de 4) |
| (1, 1) | 3 | 25 456 | 4 516 | 43,0 | 64,3 | 247 | 31,9 | 56,9 | 17,0 | 13,1 | 12,9 | fútbol (3 de 3) |
| (1, 3) | 2 | 245 618 | 19 767 | 54,4 | 73,3 | 748 | 5,8 | 14,7 | 29,6 | 45,6 | 10,1 | empate: maquillaje y perros (1 de 2 cada uno) |
| (2, 0) | 4 | 61 015 | 8 615 | 43,4 | 68,5 | 440 | 47,8 | 35,2 | 26,8 | 14,2 | 23,8 | fútbol (2 de 4) |
| (2, 2) | 2 | 158 348 | 51 736 | 67,5 | 70,4 | 1 262 | 24,4 | 76,3 | 8,9 | 7,2 | 7,5 | fútbol (2 de 2) |
| (2, 4) | 2 | 330 724 | 39 794 | 26,0 | 66,1 | 2 853 | 23,2 | 7,8 | 76,0 | 8,4 | 7,7 | maquillaje (2 de 2) |
| (3, 0) | 2 | 164 860 | 16 617 | 37,0 | 67,1 | 1 161 | 47,6 | 17,4 | 11,3 | 17,9 | 53,4 | arte (2 de 2) |
| (3, 4) | 3 | 674 103 | 146 513 | 60,7 | 62,5 | 5 197 | 15,2 | 12,5 | 66,2 | 11,8 | 9,4 | maquillaje (3 de 3) |
| (4, 0) | 2 | 237 253 | 40 032 | 36,7 | 66,8 | 1 876 | 49,6 | 8,0 | 16,2 | 10,6 | 65,2 | arte (2 de 2) |
| (4, 1) | 2 | 289 048 | 28 045 | 33,6 | 73,3 | 1 973 | 31,9 | 9,2 | 14,7 | 13,9 | 62,2 | arte (2 de 2) |
| (4, 2) | 3 | 319 437 | 38 999 | 27,2 | 73,3 | 4 443 | 36,5 | 70,0 | 9,5 | 10,7 | 9,8 | fútbol (3 de 3) |
| (4, 3) | 2 | 477 543 | 90 442 | 47,7 | 71,5 | 3 731 | 42,7 | 62,2 | 11,6 | 12,9 | 13,3 | fútbol (2 de 2) |
| (4, 4) | 3 | 559 301 | 209 584 | 83,4 | 77,2 | 3 977 | 21,6 | 36,3 | 9,8 | 28,2 | 25,7 | empate: fútbol, perros y arte (1 de 3 cada uno) |

Las 7 neuronas con un solo creador ((0,1), (1,0), (1,4), (2,1), (2,3), (3,1) y (3,2)) están marcadas con `flag_lt2` en `neuron_profiles.csv` y no se leen como grupo: su "perfil" es el de ese creador. Cada fila de la tabla sale de 2 a 5 creadores, así que una diferencia entre dos filas vecinas puede ser de un solo creador.

### 6.3 Lectura para la agencia

La regla fijada no ofrece regiones separadas que interpretar: hay una sola, R1, y su perfil es el del conjunto (221 587 seguidores, 52,6 % de audiencia argentina, USD 1 701 de precio medio, 27,4 % de publicaciones patrocinadas). La lectura útil para la agencia es entonces la de un continuo sobre el mapa, apoyada en los perfiles de neurona de 6.2 y siempre como descripción de perfiles. Las recomendaciones de campaña y la comparación contra seguidores son de la Fase 3.

- **Tamaño y precio forman el eje principal del mapa.** En la mitad superior izquierda, (0,0), (0,2), (1,1) y (2,0) reúnen creadores chicos y baratos (de 21 612 a 61 015 seguidores; de USD 175 a USD 440). En la mitad inferior derecha, (3,4), (4,4), (4,3) y (4,2) reúnen creadores grandes y caros (de 319 437 a 674 103 seguidores; de USD 3 731 a USD 5 197). En el medio hay perfiles intermedios, como (1,3) con 245 618 seguidores y USD 748, o (4,0) con 237 253 seguidores y USD 1 876. El engagement por mil se mueve poco entre las neuronas de la tabla (de 59,7 a 77,2).
- **Audiencia argentina.** La proporción más alta está en (4,4) (83,4 %, con el mayor alcance argentino, 209 584 por creador), en (0,0) (73,6 %, con alcance chico, 3 448) y en (2,2) (67,5 %). La más baja, en (2,4) (26,0 %), (4,2) (27,2 %) y (4,1) (33,6 %): son creadores con la mayor parte de su audiencia fuera de Argentina, y en (2,4) y (4,2) con precios de USD 2 853 y USD 4 443.
- **Patrocinados.** La proporción de publicaciones patrocinadas es mayor en (4,0) (49,6 %), (2,0) (47,8 %) y (3,0) (47,6 %), y menor, entre las neuronas de la tabla, en (1,3) (5,8 %) y (0,4) (7,5 %): hay perfiles que ya están acostumbrados a la publicidad y otros que casi no la hacen.
- **Temas, solo como descripción.** Los cuatro temas son entradas del mapa y por eso es esperable que ordenen los lugares; no es una confirmación independiente. Los 5 creadores de (0,0) tienen perros como tema dominante, (2,4) y (3,4) maquillaje, (3,0), (4,0) y (4,1) arte, y (1,1), (2,2), (4,2) y (4,3) fútbol. Esos lugares se leen como zonas donde el mapa junta creadores con el mismo tema dominante; no como regiones del mapa según la regla, que no los separó.

### 6.4 ¿Coinciden las regiones con PC1 y PC2 (biplot)?

Se usa la lectura de la sección 6 de `deliverables/01-datos-pca.md`: PC1 (53,2 % de la varianza) es el eje de escala y formato, con tamaño, alcance y precio (`followers`, `average_reach`, `price_usd`) del lado negativo y epígrafes largos, contenido tutorial y respuesta (guardados, comentarios) del lado positivo; PC2 (8,5 %) se apoya en la audiencia argentina (`argentina_audience_pct`, `estimated_argentina_reach`, `topic_dogs_pct`). Los estadísticos son los declarados en la sección 2, con 1000 permutaciones de un generador sembrado con 2026; los p son de una cola (cuántas permutaciones igualan o superan lo observado, sumando la observada) y 0,001 es el mínimo posible con 1000 permutaciones. Las figuras son `analysis/results/som/profiles/pc_planes.svg` (media de PC1 y de PC2 de los creadores de cada neurona) y, para compararla, `analysis/results/pca/audited/biplot.svg`.

- R² de PC1 sobre la grilla: 0,961 (p = 0,001)
- R² de PC2 sobre la grilla: 0,055 (p = 0,267)
- Mantel grilla vs plano PC1-PC2: rho = 0,599 (p = 0,001)
- Mantel grilla vs distancia en las 26 variables (referencia): rho = 0,635

Por aristas, la distancia entre prototipos de neuronas ocupadas vecinas se correlaciona con la diferencia de PC1 entre sus medias con rho de Spearman 0,481 y con la de PC2 con 0,271 (29 aristas; las otras 11 tocan una neurona vacía y se excluyen). La regla no declaró un nulo de permutaciones para este estadístico, por eso no lleva p: se informa como descriptivo, y con 29 aristas es un valor poco preciso.

**Respuesta.** Sí para PC1, no para PC2. El mapa sigue a PC1 de forma casi exacta: la posición (fila, columna) de la mejor neurona explica el 96,1 % de la variación de PC1 entre los 50 creadores, y ninguna de las 1000 permutaciones lo alcanza (p = 0,001). Lo ve `pc_planes.svg`: PC1 baja en diagonal desde la esquina superior izquierda (5,74 en (0,0)) hasta la inferior derecha (-6,04 en (4,4)), que es el mismo eje de tamaño y precio de 6.3 (21 612 seguidores en (0,0) contra 559 301 en (4,4)). Con PC2 no hay coincidencia lineal: R² de 0,055 y p = 0,267, es decir que una variación así de chica es habitual si se reparten al azar las posiciones. Esto describe una dependencia lineal en (fila, columna); en `pc_planes.svg` PC2 es alta en dos esquinas opuestas, (0,0) (2,02) y (4,4) (2,28), cosa que una recta sobre la grilla no puede representar. Es una lectura de la figura, no un estadístico declarado. En conjunto, el orden entre distancias de grilla y distancias en el plano PC1-PC2 coincide moderadamente (rho 0,599, p = 0,001), casi tanto como con las distancias en las 26 variables (0,635), y el patrón por aristas es moderado para PC1 y débil para PC2. Como las regiones de la regla son una sola, la comparación es entre el layout del mapa y los ejes, no entre regiones y ejes.

**Dónde mapa y plano discrepan** (`disagreements.csv`). Cerca en el plano y lejos en la grilla: @artealpaso (neurona (4,0)) y @patitascontentas ((0,4)), a 0,59 en el plano y a 5,66 en la grilla (esquinas opuestas); @artequeinspira (4,0) y @brochasymates (0,4), a 1,60 en el plano; @artealpaso y @cosmeticaconsciente (0,4), a 1,71. @artealpaso y @patitascontentas se parecen en PC1 y PC2 y no en lo que esos dos ejes no ven: uno es de arte (60,2 % arte) con 229 624 seguidores y el otro de perros (68,6 % perros) con 72 459. Lejos en el plano y vecinos en la grilla: @mateconideas ((3,4)) y @bellezasimple ((2,4)), a 4,47 en el plano (PC2 de 3,07 contra -0,73: 83,2 % de audiencia argentina contra 23,8 %) aunque los dos tienen maquillaje como tema dominante; @patitasenred ((3,1)) y @creatividadaldia ((3,0)), a 3,86 (PC1 de -1,45 contra 2,03); @patitasenred y @canchaaldia ((2,1)), a 3,77. Un mapa no lineal puede separar lo que PC1 y PC2 mezclan porque usa las 26 variables y el plano retiene el 61,7 % de la varianza (sección 6 de la Fase 1): el 38,3 % restante, donde la Fase 1 ubicó a los temas (PC3 y PC4), puede alejar dos creadores que el plano muestra juntos, y a la inversa una vecindad de la grilla no garantiza cercanía en el plano porque dos neuronas vecinas pueden tener prototipos a hasta 3,67 de distancia en z (sección 5).

### 6.5 ¿Qué indica una distancia alta entre neuronas vecinas en la matriz U?

Dos neuronas vecinas en la grilla con una distancia alta entre sus prototipos tienen perfiles lejanos en las 26 variables en z: la distancia alta es un límite entre perfiles distintos, y una zona de valores bajos es una zona homogénea, donde los prototipos vecinos se parecen (es la lectura de la matriz U de las slides del curso). La matriz U no dice cuál es la diferencia; para eso se miran las variables que más cambian a lo largo de la arista (`high_u_edges.csv`, las 3 aristas más altas entre neuronas ocupadas y sus 3 variables de mayor |delta z|; el delta va de la neurona de menor número a la de mayor).

- **(1,4) a (2,4), distancia 3,67 (la más alta del mapa entre neuronas ocupadas).** `price_usd` sube 1,22 en z (USD 2 116), `followers` 1,21 (251 127 seguidores) y `average_reach` 1,19 (97 110). Es un salto de escala y precio entre un creador aislado, el de (1,4), y los 2 de (2,4).
- **(2,3) a (2,4), distancia 2,99.** `price_usd` sube 1,04 en z (USD 1 804), `average_reach` 1,00 (81 579) y `followers` 0,98 (204 239): otra vez tamaño y precio.
- **(2,1) a (2,2), distancia 2,98.** Cambia el formato: `content_entertainment_pct` sube 1,17 en z (34,4 puntos porcentuales), `content_review_pct` baja 1,09 (10,4 puntos) y `average_caption_words` baja 0,88 (43,2 palabras).

Dos de las tres aristas más altas separan por tamaño y precio, que es el eje de PC1 (6.4), y la tercera por el tipo de contenido. Las tres tienen en una punta una neurona con un solo creador ((1,4), (2,3) y (2,1)), así que cada salto puede ser el de un caso suelto. Y una precaución general: una pared al lado de una neurona vacía es interpolación, no un límite entre grupos de creadores. Cuatro de las seis aristas más largas del mapa tocan una neurona vacía ((1,2)-(1,3) con 3,63, (2,3)-(3,3) con 3,59, (3,2)-(3,3) con 3,47 y (1,2)-(2,2) con 3,20) y por eso no figuran en `high_u_edges.csv` ni sostienen una frontera. Solo un salto entre neuronas ocupadas, como los tres de arriba, la apoya, y aun así con cautela por el tamaño de las neuronas.

## 7. Cómo reproducir

Desde `TP4/`, en un clone nuevo:

```
make venv         # crea .venv e instala analysis/requirements.txt (versiones fijadas); sin uv: python3.12 -m venv .venv,
                  # .venv/bin/pip install -r analysis/requirements.txt y touch .venv/.installed
make prepare      # escribe datos/prepared/: matriz auditada de 26 variables y de 31 columnas con sus .meta.json
make som-stage1   # 140 corridas, QE-LOO y estabilidad; escribe analysis/results/som/series_som_stage1/ con selection.json
                  # (se niega a correr si la regla de la sección 2 no está commiteada y sin cambios)
make som-stage2   # robustez del schedule sobre la k elegida; escribe analysis/results/som/series_som_stage2/
make som-figures  # mapa de hits y matriz U, planos de componentes, curvas de la etapa 1 y traza; escribe analysis/results/som/figures/
make som-profiles # regiones, perfiles, contraste con PC1/PC2, aristas altas y discrepancias, más regions y pc_planes;
                  # escribe analysis/results/som/profiles/
make test         # tests de C y de Python (incluye los del SOM)
```

`analysis/results/` no se versiona: cada número y cada figura de este fragmento se regenera con estos comandos, y cada corrida es reproducible byte a byte para sus seeds (los CSV, los JSON y los SVG de `som-figures` y `som-profiles` salen idénticos en reejecuciones).
