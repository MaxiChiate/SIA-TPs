# Fase 2 — Mapa de Kohonen (SOM) de los 50 creadores

## 1. Algoritmo y salidas

El modelo es un mapa autoorganizado de Kohonen con grilla rectangular de k × k neuronas. Cada neurona tiene un vector de pesos en las 7 primeras componentes principales de la PCA de las 17 variables que quedan con el umbral de correlación (sección 6.2 de `deliverables/01-datos-pca.md`): los scores sin reescalar, en `datos/prepared/creadores_pca_scores.csv`, que escribe `make pca`. La distancia entre un creador y una neurona es la euclídea en ese espacio (D-05). La distancia en la grilla entre dos neuronas es la euclídea entre sus posiciones (fila, columna). El código está en C (`neuron/models/kohonen.c`), sin librerías de aprendizaje automático, y lo corre `neuron/build/neuron` con una config estricta de siete claves: `grid_k`, `neighborhood`, `radius0`, `radius_final`, `eta0`, `eta_final` y `epochs`.

**Inicialización.** Los pesos de cada neurona arrancan como una copia de un creador elegido al azar del conjunto de entrenamiento, que es la recomendación de las slides para evitar unidades muertas (D-05). Con k² mayor que 50 creadores (k = 8 tiene 64 neuronas) el orden de creadores se vuelve a barajar cada vez que se agota.

**Orden y cantidad de pasos.** El entrenamiento va por épocas. En cada época se recorren los 50 creadores en un orden barajado con el generador de la seed de la corrida (splitmix64 de la Fase 1), de modo que la misma seed da los mismos bytes. El total de pasos es T = épocas × n (D-03). El baseline de 260 épocas da unos 13 000 pasos, del orden de los 500·N del curso con N = 26.

**Tasa de aprendizaje.** η decrece exponencialmente de η0 a ηf: η(t) = η0 · (ηf / η0)^(t / (T − 1)), con η0 < 1 (D-02).

**Vecindad.** Hay dos modos, elegidos por la clave `neighborhood` (D-01). El radio R (en el modo escalón) y σ (en el gaussiano) decrecen con la misma forma exponencial que η, desde `radius0` hasta `radius_final`, y nunca bajan de `radius_final`.

- *Escalón* (camino principal, el del curso). Se actualizan las neuronas cuya distancia en la grilla a la ganadora cumple `||n − n_k|| ≤ R(t)`. Las slides del curso escriben N_k(i) = {n / ||n − n_k|| < R(i)} con `<` estricto (p. 26) y fijan R = 1 para la grilla rectangular de 4 vecinos (p. 15); con el `<` estricto, R = 1 deja solo a la ganadora. Este TP usa `≤` a propósito (D-01), para que R = 1 actualice a la ganadora y a sus cuatro vecinas pegadas; las diagonales (a distancia √2) entran recién cuando R ≥ √2. R(0) es configurable y baja hasta 1 inclusive.
- *Gaussiano* (variante de comparación). El peso de una neurona a distancia d de la ganadora es h = exp(−d² / 2σ²), con σ decreciente y un piso mayor que 0, nunca 0.

**Regla de actualización.** Para cada creador x con ganadora n_k, todas las neuronas j se actualizan con W_j ← W_j + η(t) · h_j · (x − W_j), con h_j ∈ {0, 1} en el modo escalón y h_j = exp(−d² / 2σ²) en el gaussiano.

**Salidas de cada corrida.**

- **QE** (error de cuantización): distancia euclídea media de cada creador a su neurona ganadora (BMU), en unidades de score (las de las componentes principales).
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
- **Estabilidad.** Para cada seed se arma el vector de las 1225 distancias en la grilla entre las BMU de cada par de creadores (50 · 49 / 2 pares), con distancia euclídea entre las coordenadas (fila, columna) de las BMU. La estabilidad es el promedio de la correlación de Pearson entre esos vectores, sobre los 45 pares de seeds (D-13). Los pares de seeds con correlación indefinida (NaN, por ejemplo si todos los creadores caen en una neurona) se descartan del promedio y se cuentan; si todos los pares son NaN, la estabilidad vale 0.
- **Si ninguna grilla pasa.** Si ninguna k de escalón pasa los tres filtros, se quita solo el filtro de TE, se aplica el resto de la regla sin cambios y el informe dice que ninguna grilla cumplió TE ≤ 0,05 (D-14). La ocupación no se relaja nunca. Si ninguna k pasa los dos filtros de ocupación ni siquiera sin el de TE, no se elige ninguna grilla: el informe lista el filtro que falla en cada k, no se producen figuras de mapa, regiones ni contraste con la PCA, y la fase se detiene hasta que una nueva discusión decida cómo seguir.
- **QE de entrenamiento.** Se reporta y se grafica contra k, pero nunca decide (D-15). Por QE de entrenamiento solo ganaría la grilla más grande, porque con más neuronas el error siempre baja; por eso la elección usa el QE-LOO y los filtros.
- **Gaussiana.** Se corre con el mismo R0 = σ0 y el mismo piso (`radius_final` = 1) que el escalón, de modo que solo cambia la forma del núcleo. Se reporta al lado como comparación y no entra en la elección, ni siquiera con un QE-LOO menor.
- **Corridas fallidas.** Cualquier corrida fallida, o cualquier entrenamiento fallido del leave-one-out, detiene la selección: no se elige nada con datos parciales.
- **Consecuencia aritmética.** Si todas las seeds tuvieran la misma ocupación, k ≥ 6 no podría pasar D-12: al menos 2 creadores por neurona ocupada exige a lo sumo 25 neuronas ocupadas, y a lo sumo 20 % de vacías exige al menos 0,8 k² ocupadas; las dos juntas solo valen si k² ≤ 31,25. Con k = 5 solo pasaría con entre 20 y 25 neuronas ocupadas. Como el filtro promedia cocientes por seed, seeds muy distintas podrían igual dejar pasar una k mayor; por eso la regla se aplica a k = 6, 7 y 8 como a las demás, y esas filas dibujan además la curva de QE contra ocupación (D-07).
- **Advertencias del QE-LOO.** El z-score se ajustó con los 50 creadores, el excluido incluido (una fuga leve, declarada y no corregida). Cada fold conserva la seed y las épocas de la corrida, por lo que T = épocas × 49.
- **Semilla de las figuras.** Entre las 10 seeds de la k elegida, la semilla de las figuras es el medoide de estabilidad: la de mayor correlación media con las otras nueve, la menor seed si hay empate. La orientación del mapa es arbitraria (rotación y reflexión no cambian nada de lo medido).
- **Regiones.** Las regiones son las componentes conexas, con adyacencia de 4, de las neuronas ocupadas, después de cortar toda arista de 4 vecinos cuya distancia entre prototipos supere el percentil 75 de las distancias entre prototipos de todas las aristas de 4 vecinos del mapa. Las regiones con menos de 2 creadores se rotulan "no interpretable". Los perfiles se calculan en unidades originales con los valores crudos de los creadores de cada región; las neuronas con menos de 2 creadores se marcan. Los temas son entradas del mapa y nunca "validan" una región.
- **Contraste con PC1/PC2.** Los estadísticos se declaran ahora. R² de PC1 y de PC2 regresados sobre la (fila, columna) de la BMU, con un nulo de 1000 permutaciones. Correlación de Pearson (tipo Mantel) entre las distancias en la grilla y las distancias en el plano PC1-PC2, con la distancia en el espacio z de las variables que quedan como referencia. Correlación de Pearson por aristas entre las aristas de la matriz U y las diferencias de PC1 y de PC2 entre las medias por neurona. El generador de permutaciones se siembra con 2026.
- **Etapa 2.** Sobre la k elegida, en el modo escalón, el baseline (R0 = max(1, k/2), η0 = 0,5, 260 épocas) más un cambio a la vez, 10 seeds: R0 en {max(1, k/4), k}, η0 en {0,1; 0,25; 0,9}, épocas en {50, 130, 520, 1040}; se descarta todo valor igual al del baseline. `analysis/series_som_stage2.json` se genera de esta lista con `analysis/som_stage.py` (plan 02-04) para la k elegida y se commitea antes de correr.
- **Criterio de robustez.** La elección es robusta si la k elegida pasa los mismos filtros en cada variante de la etapa 2. La etapa 2 nunca vuelve a elegir k. Si en la etapa 1 se quitó el filtro de TE, la robustez revisa solo los filtros de ocupación.
- **Control.** `analysis/som_stage.py` se niega a correr mientras este archivo, `analysis/som_select.py` (la regla como código: umbrales, filtros, `select_grid` y escaleras) o el archivo de la serie estén sin trackear o con cambios sin commitear. `selection.json` registra el hash del commit y el sha256 del texto entre los marcadores, más el hash del commit y el sha256 de `analysis/som_select.py`, y los pasos posteriores se niegan a correr si cambia cualquiera de los dos sha256.
<!-- regla:fin -->

### 2.1 Reaplicación de la regla sobre las componentes principales

El 2026-11-01 el mapa se volvió a entrenar sobre los scores de las 7 primeras componentes de la PCA de las 17 variables que quedan con |r| < 0,8 (sección 6.2 de `deliverables/01-datos-pca.md`), que juntan el 83,4 % de la varianza, en lugar de las 26 variables con z-score. La regla de la sección 2 no cambió: el texto entre los marcadores y `analysis/som_select.py` son los mismos, con los mismos umbrales, filtros, desempate y escaleras de la etapa 2. Lo único que cambia es el dato de entrada, que quedó escrito en el archivo de la serie (`analysis/series_som_stage1.json`, clave `input`) y en el config base, y se commiteó antes de correr las etapas.

Un segundo cambio de ese día: la estabilidad entre seeds y los contrastes con PC1 y PC2 de la sección 2 se calculaban con una correlación de rangos, y se pasaron a la correlación de Pearson porque la de rangos no se vio en clase. El texto de la regla cambió solo en ese punto (la definición del estadístico), se commiteó antes de volver a correr las etapas, y la elección de la grilla (los filtros y el QE-LOO) no depende de ese estadístico.

Los scores no se reescalan: la distancia entre dos creadores en esas 7 columnas es la del espacio de las 17 variables proyectado sobre las 7 componentes, de modo que PC1 pesa más que PC7 en proporción a su varianza (sus autovalores). La advertencia del QE-LOO de la sección 2 se agranda: tanto el z-score como la PCA y el umbral de correlación se ajustaron con los 50 creadores, el excluido incluido, y cada fold del leave-one-out no los reajusta. Es una fuga leve, declarada y no corregida, y los QE-LOO nuevos no son comparables con los del mapa de 26 variables (la unidad cambió).



## 3. Etapa 1: resultados y grilla elegida

Las cifras salen de `analysis/results/som/series_som_stage1/` (`aggregate.csv`, `selection.json`), que escribe `make som-stage1`. La regla de la sección 2 se aplicó sin cambios sobre los scores de las 7 componentes (sección 2.1): el comando se negaría a correr con el texto de la regla, `analysis/som_select.py` o la serie de la etapa 1 sin commitear, y `selection.json` guarda el commit que agregó la regla y el sha256 de su texto y de su código. Son 14 configuraciones × 10 seeds = 140 corridas y 7 000 entrenamientos de leave-one-out (50 por corrida); ninguno falló. Todas las cifras son media ± desvío (ddof 1) sobre las 10 seeds, nunca una seed sola (D-08); la estabilidad es un promedio sobre pares de seeds. QE y QE-LOO están en unidades de score (las de las componentes principales), así que no se comparan con los del mapa de las 26 variables.

**Escalón (camino de la elección).** La columna "filtros" dice cuáles de los tres filtros de la sección 2 (TE ≤ 0,05, vacías ≤ 20 %, creadores por neurona ocupada ≥ 2) pasa la media de cada k.

| k | QE | QE-LOO | TE | % de neuronas vacías | creadores por neurona ocupada | estabilidad | filtros |
|---|---|---|---|---|---|---|---|
| 2 | 2,904 ± 0,002 | 3,012 ± 0,003 | 0,180 ± 0,000 | 0,0 ± 0,0 | 12,50 ± 0,00 | 0,984 | falla TE |
| 3 | 2,496 ± 0,006 | 2,709 ± 0,015 | 0,164 ± 0,013 | 0,0 ± 0,0 | 5,56 ± 0,00 | 0,926 | falla TE |
| 4 | 2,146 ± 0,012 | 2,483 ± 0,020 | 0,070 ± 0,038 | 0,0 ± 0,0 | 3,12 ± 0,00 | 0,732 | falla TE |
| 5 | 1,904 ± 0,031 | 2,341 ± 0,028 | 0,064 ± 0,040 | 7,2 ± 1,7 | 2,16 ± 0,04 | 0,644 | falla TE |
| 6 | 1,679 ± 0,030 | 2,294 ± 0,028 | 0,026 ± 0,030 | 21,7 ± 3,9 | 1,78 ± 0,09 | 0,695 | falla vacías y creadores |
| 7 | 1,448 ± 0,051 | 2,213 ± 0,030 | 0,050 ± 0,027 | 33,9 ± 6,5 | 1,56 ± 0,15 | 0,572 | falla vacías y creadores |
| 8 | 1,252 ± 0,053 | 2,162 ± 0,027 | 0,010 ± 0,011 | 43,8 ± 5,0 | 1,40 ± 0,12 | 0,515 | falla vacías y creadores |

**Gaussiana (comparación, no entra en la elección, D-11).** Mismo R0 = σ0, mismo piso y mismas seeds. La columna "filtros" es solo informativa: la regla no la usa.

| k | QE | QE-LOO | TE | % de neuronas vacías | creadores por neurona ocupada | estabilidad | filtros |
|---|---|---|---|---|---|---|---|
| 2 | 3,092 ± 0,001 | 3,190 ± 0,001 | 0,110 ± 0,011 | 0,0 ± 0,0 | 12,50 ± 0,00 | 1,000 | falla TE |
| 3 | 2,608 ± 0,002 | 2,811 ± 0,004 | 0,106 ± 0,010 | 5,6 ± 5,9 | 5,90 ± 0,37 | 0,933 | falla TE |
| 4 | 2,339 ± 0,012 | 2,609 ± 0,004 | 0,084 ± 0,013 | 4,4 ± 3,0 | 3,27 ± 0,10 | 0,914 | falla TE |
| 5 | 2,095 ± 0,012 | 2,469 ± 0,012 | 0,072 ± 0,029 | 15,2 ± 4,1 | 2,36 ± 0,11 | 0,816 | falla TE |
| 6 | 1,921 ± 0,010 | 2,368 ± 0,013 | 0,022 ± 0,022 | 30,3 ± 2,0 | 1,99 ± 0,06 | 0,964 | falla vacías y creadores |
| 7 | 1,784 ± 0,007 | 2,287 ± 0,019 | 0,040 ± 0,028 | 39,2 ± 3,6 | 1,68 ± 0,10 | 0,838 | falla vacías y creadores |
| 8 | 1,672 ± 0,014 | 2,250 ± 0,016 | 0,024 ± 0,013 | 48,9 ± 2,4 | 1,53 ± 0,08 | 0,875 | falla vacías y creadores |

**Cómo siguió la regla.** Con el escalón, **ninguna k pasa los tres filtros**. k = 2, 3, 4 y 5 ocupan bien sus neuronas (como máximo 7,2 % de vacías y al menos 2,16 creadores por neurona ocupada) pero quedan fuera por TE (0,180, 0,164, 0,070 y 0,064, contra el máximo de 0,05); k = 6, 7 y 8 pasan TE pero quedan fuera por la ocupación (21,7 %, 33,9 % y 43,8 % de neuronas vacías, y 1,78, 1,56 y 1,40 creadores por neurona ocupada). Como no sobrevivió ninguna, se aplicó el paso de D-14: la regla quita solo el filtro de TE, aplica el resto sin cambios y el informe dice que **ninguna grilla cumplió TE ≤ 0,05**. Sin el filtro de TE sobreviven k = 2, 3, 4 y 5 por ocupación, y entre ellas gana la de menor QE-LOO medio, k = 5 (2,341 contra 2,483 de k = 4). La banda de desempate es la ganadora más toda k sobreviviente a menos de un desvío del QE-LOO por seed de la ganadora (0,028): k = 4 está a 0,142, más de cinco desvíos, así que la banda tiene solo a k = 5 y decide el QE-LOO, sin pasar por la estabilidad. La estabilidad de k = 5 (0,644) es menor que la de k = 4 (0,732), la de k = 3 (0,926) y la de k = 2 (0,984); la regla fijada antes de mirar no la usa fuera de la banda, y se informa como una limitación de la elegida. Otra limitación: k = 5 no cumple el TE (0,064, con 6 de las 10 seeds por encima de 0,05) y pasa por poco el mínimo de creadores por neurona ocupada (2,16 contra 2). La etapa 2 mide cuánto de esto depende del schedule.

- Grilla elegida: k = 5
- Commit de la regla: ea7a0b11202d
- Por QE de entrenamiento solo se elegiría: k = 8
- Semilla de las figuras: 10

El QE de entrenamiento no decide (D-15): baja siempre al agrandar la grilla y por sí solo elegiría k = 8, que deja 43,8 % de neuronas vacías y 1,40 creadores por neurona ocupada. La semilla de las figuras es el medoide de estabilidad de k = 5 (sección 2), y la orientación del mapa es arbitraria.

## 4. Etapa 2: robustez del schedule

Las cifras salen de `analysis/results/som/series_som_stage2/` (`aggregate.csv`, `robustness.csv`, `robustness.json`), que escribe `make som-stage2` sobre `analysis/series_som_stage2.json`. Ese archivo lo generó `analysis/som_stage.py write-stage2` a partir de la k elegida (k = 5) y de las escaleras de la sección 2, y se commiteó antes de correr: sale idéntico al de la corrida anterior porque la k elegida es la misma. Sobre k = 5 con el escalón se cambia una cosa a la vez respecto del baseline (R0 = 2,5; η0 = 0,5; 260 épocas): R0 en {1,25; 5}, η0 en {0,1; 0,25; 0,9} y épocas en {50; 130; 520; 1040}, con 10 seeds cada variante (10 variantes × 10 seeds = 100 corridas y 5 000 entrenamientos de leave-one-out; ninguno falló, D-06). Todas las cifras son media ± desvío (ddof 1) sobre las 10 seeds. La fila `base` repite la fila k = 5 de la sección 3. Como en la etapa 1 se quitó el filtro de TE, la robustez revisa solo los filtros de ocupación (sección 2, **Criterio de robustez.**); el TE se informa pero no decide.

| variante | R0 | η0 | épocas | TE | % de neuronas vacías | creadores por neurona ocupada | pasa los filtros de ocupación | QE-LOO | estabilidad |
|---|---|---|---|---|---|---|---|---|---|
| base | 2,5 | 0,5 | 260 | 0,064 ± 0,040 | 7,2 ± 1,7 | 2,16 ± 0,04 | sí | 2,341 ± 0,028 | 0,644 |
| radius0-1.25 | 1,25 | 0,5 | 260 | 0,056 ± 0,018 | 4,4 ± 4,0 | 2,10 ± 0,09 | sí | 2,334 ± 0,024 | 0,537 |
| radius0-5 | 5 | 0,5 | 260 | 0,070 ± 0,019 | 8,4 ± 2,3 | 2,18 ± 0,05 | sí | 2,348 ± 0,019 | 0,831 |
| eta0-0.1 | 2,5 | 0,1 | 260 | 0,068 ± 0,021 | 8,8 ± 4,5 | 2,20 ± 0,11 | sí | 2,372 ± 0,035 | 0,679 |
| eta0-0.25 | 2,5 | 0,25 | 260 | 0,056 ± 0,034 | 7,6 ± 4,0 | 2,17 ± 0,10 | sí | 2,346 ± 0,025 | 0,586 |
| eta0-0.9 | 2,5 | 0,9 | 260 | 0,066 ± 0,027 | 7,2 ± 4,1 | 2,16 ± 0,10 | sí | 2,352 ± 0,039 | 0,650 |
| epochs-50 | 2,5 | 0,5 | 50 | 0,066 ± 0,040 | 10,8 ± 4,6 | 2,25 ± 0,12 | sí | 2,356 ± 0,027 | 0,576 |
| epochs-130 | 2,5 | 0,5 | 130 | 0,062 ± 0,033 | 8,8 ± 2,5 | 2,19 ± 0,06 | sí | 2,353 ± 0,030 | 0,630 |
| epochs-520 | 2,5 | 0,5 | 520 | 0,074 ± 0,027 | 8,0 ± 3,3 | 2,18 ± 0,08 | sí | 2,356 ± 0,018 | 0,616 |
| epochs-1040 | 2,5 | 0,5 | 1040 | 0,068 ± 0,023 | 8,0 ± 1,9 | 2,17 ± 0,04 | sí | 2,340 ± 0,026 | 0,704 |

**Cómo se mueven QE-LOO y estabilidad.** El QE-LOO casi no se mueve: va de 2,334 (radius0-1.25) a 2,372 (eta0-0.1), una franja de 0,038, del orden de dos desvíos del baseline (0,028). La estabilidad se mueve más, entre 0,537 (radius0-1.25) y 0,831 (radius0-5), con un baseline de 0,644; con una dispersión entre pares de seeds de ese tamaño, esas diferencias no sostienen ordenar los schedules.

**Qué pasa con los filtros.** Los dos filtros de ocupación pasan en las 10 variantes: neuronas vacías entre 4,4 % y 10,8 % (máximo 20 %) y creadores por neurona ocupada entre 2,10 y 2,25 (mínimo 2). El TE medio queda entre 0,056 y 0,074 en las 10, siempre sobre el máximo de 0,05, que es lo mismo que mostró la etapa 1 para k = 5 (0,064): no depende del schedule, es una propiedad de esta grilla con estos datos.

- Veredicto de robustez: robusta (las 10 variantes pasan los filtros de ocupación; el TE no se revisa porque la etapa 1 lo quitó)

La etapa 2 no vuelve a elegir k (sección 2, **Criterio de robustez.**): k = 5 sigue siendo la grilla elegida, y el veredicto dice que su ocupación se sostiene al mover R0, η0 o las épocas.

## 5. Mapa de la grilla elegida

Las figuras salen de `analysis/results/som/figures/`, que escribe `make som-figures` (necesita el `selection.json` de `make som-stage1`; se niega a correr si el sha256 de la regla cambió o si no hay grilla elegida). Se dibuja una sola corrida: la de k = 5 (`k5-step`), con seed 10, que es el medoide de estabilidad entre las 10 seeds (sección 2), no la que mejor se vea. La orientación del mapa es arbitraria: rotarlo o reflejarlo no cambia ninguna medida, así que "arriba" o "a la izquierda" solo describen estas figuras. Las posiciones se nombran (fila, columna) con la fila 0 arriba. Volver a correr `make som-figures` da SVG idénticos byte a byte; `hits_members.csv` lista los creadores de cada neurona.

**`map.svg`: creadores por neurona y matriz U, lado a lado.** A la izquierda, el número de creadores cuya mejor neurona (BMU) es cada celda; las celdas rayadas son neuronas vacías. Hay 2 neuronas vacías de 25 ((1,3) y (3,3)), 6 con un solo creador ((0,0), (1,1), (2,0), (2,4), (3,0) y (3,2)) y el máximo es 5 creadores en (4,0); los 50 creadores se reparten en 23 neuronas ocupadas (8 % vacías, 2,17 creadores por neurona ocupada en esta corrida). Una neurona con un solo creador es un caso aislado, no un grupo, y se lee con cautela. A la derecha, la matriz U: cada celda es la distancia media (en unidades de score) entre el prototipo de la neurona y los de sus vecinos de 4, con la escala completa de 0,95 a 2,09 sin recortar. Un valor alto es un salto entre prototipos vecinos; uno bajo, prototipos parecidos. Los valores más bajos están en (4,0) 0,95, (1,0) 1,32, (2,1) 1,39 y (3,4) 1,39 y los más altos en (1,3) 2,09, (2,4) 2,01 y (0,1) 1,94, y la arista más larga entre neuronas ocupadas, (2,0)-(3,0), mide 2,64. Las 2 neuronas vacías caen en los lugares 1 y 5 de 25 en U, y 2 de las seis aristas más largas tocan una neurona vacía ((1,2)-(1,3) con 2,50 y (3,2)-(3,3) con 2,33): ese muro es interpolación (el prototipo de una neurona vacía queda entre los de sus vecinos porque ningún creador lo reclama) y no un límite entre dos grupos de creadores. Solo un salto entre neuronas ocupadas apoya una frontera.

**`planes_main.svg`: planos de variables principales.** El mapa se entrena con los scores de las componentes, no con las variables, así que cada celda de estos planos es la media cruda de la variable entre los creadores de la neurona (en blanco rayado donde la neurona está vacía), con su propia escala. Las variables son las 4 de mayor |carga| en PC1 y las 4 siguientes distintas de mayor |carga| en PC2 de la PCA de las 17 variables, con la orientación de signos de la Fase 1; se fijaron por esa regla antes de mirar el mapa. En esta corrida: `followers` va de 15 556 en (2,0) a 645 048 en (1,4); `saves_per_1000` va de 6 en (1,4) a 22 en (4,1); `profile_visits_per_1000` va de 9 en (0,1) a 26 en (2,0); `likes_per_1000` va de 31 en (4,0) a 51 en (0,4); `sponsored_posts_pct` va de 3,4 en (4,3) a 54,4 en (1,0); `argentina_audience_pct` va de 26,0 en (0,2) a 89,4 en (0,0); `topic_football_pct` va de 7,7 en (2,3) a 80,2 en (0,1); `topic_dogs_pct` va de 6,0 en (0,1) a 72,8 en (4,1). Los dos planos de abajo, `topic_art_pct` y `content_showcase_pct`, son las variables que salieron por ser combinación exacta de otras. Como cada media sale de 1 a 5 creadores, una media cruda de una neurona con un solo creador es el valor de ese creador.

**`planes_appendix.svg`: planos de todas las componentes y las variables.** Las 7 componentes con las que se entrenó el mapa, como peso del prototipo (cada una con su escala centrada en 0), y las 31 variables de `datos/creadores.csv` como media cruda de los creadores de cada neurona. Sirve para buscar una variable que no entró en el plano principal; no se eligió ninguna por cómo se ve, y qué regiones se forman y cómo se parecen a PC1 y PC2 es la sección 6, no esta.

**`stage1_curves.svg`: por qué el QE solo no decide.** Seis paneles contra k (2 a 8), media ± desvío entre las 10 seeds, escalón y gaussiana: QE de entrenamiento, QE-LOO, TE, % de neuronas vacías, creadores por neurona ocupada y estabilidad, con los umbrales de la regla (TE 0,05; 20 % de vacías; 2 creadores por neurona ocupada), la k elegida marcada y el mínimo del QE de entrenamiento anotado. El QE de entrenamiento del escalón baja sin parar con k, de 2,904 (k = 2) a 1,252 (k = 8), y por sí solo elegiría k = 8 (D-07, D-15); en el mismo tramo las neuronas vacías suben de 0 % a 43,8 % y los creadores por neurona ocupada bajan de 12,5 a 1,40, o sea que la grilla grande baja el error repartiendo los 50 creadores en neuronas casi individuales. El QE-LOO baja mucho menos de k = 5 en adelante (2,341 en k = 5; 2,294 en k = 6) y la estabilidad cae con k. Los umbrales de la regla valen para el escalón; la gaussiana se muestra como comparación. La elección sale de los filtros de ocupación más el QE-LOO (el TE se quitó porque ninguna grilla lo cumple), no de esta curva.

**`trace.svg`: entrenamiento de la corrida dibujada.** QE (eje izquierdo) y TE (eje derecho) en cada una de las 260 épocas. En la primera época el TE vale 0,90 y el QE 1,33; en la última valen 0,10 y 1,93. En las primeras 60 épocas el TE tiene un máximo de 0,90, y en el último 10 % de las épocas el QE varía entre 1,9326 y 1,9361 y el TE entre 0,10 y 0,12, o sea que las dos medidas quedan casi planas. QE y TE finales de la corrida dibujada (1,933 y 0,10) se comparan con lo que muestran las 10 seeds de la sección 3 (QE de entrenamiento medio 1,904; TE medio 0,064): el TE de esta seed supera el máximo de 0,05, como el promedio.

## 6. Regiones, perfiles y contraste con PC1/PC2

Las cifras salen de `analysis/results/som/profiles/` (`regions.csv`, `region_profiles.csv`, `neuron_profiles.csv`, `pca_contrast.json`, `high_u_edges.csv`, `disagreements.csv`), que escribe `make som-profiles` sobre la misma corrida de la sección 5 (k = 5, `k5-step`, seed 10). El script se niega a correr si el sha256 de la regla cambió desde la etapa 1 o si no hay grilla elegida. La regla de regiones y los estadísticos del contraste son los de la sección 2, aplicados sin cambios: no se tocó el percentil, el mínimo de 2 creadores, el número de permutaciones (1000) ni la semilla (2026) después de ver el resultado.

### 6.1 Regiones

El percentil 75 de las 40 distancias entre prototipos de neuronas vecinas de la grilla vale 1,95, y esa es la distancia de corte (`pca_contrast.json`, `threshold`). Superan el umbral 10 aristas. 4 de ellas tocan una neurona vacía ((1,2)-(1,3), (3,2)-(3,3), (3,3)-(4,3), (1,3)-(2,3)) y no separan nada: una neurona vacía no pertenece a ninguna región. Las otras 6 unen neuronas ocupadas: (2,0)-(3,0) con 2,64, (4,1)-(4,2) con 2,38, (0,1)-(1,1) con 2,37, (1,4)-(2,4) con 2,30, (0,0)-(0,1) con 2,12, (2,3)-(2,4) con 2,07. Con esos cortes, las 23 neuronas ocupadas siguen conectadas entre sí por aristas que no se cortaron, así que la regla da **una sola región, R1, con los 50 creadores**, que es interpretable (50 creadores, más de 2). No hay regiones ni neuronas rotuladas "no interpretable" por tamaño de región.

Este es el resultado de la regla fijada de antemano y se informa como salió: con la regla de la sección 2, el mapa de 5 × 5 no se parte en grupos de creadores. Cambiar el percentil para obtener más regiones sería elegir la regla mirando el mapa, que es lo que la sección 2 prohíbe. La figura es `analysis/results/som/profiles/regions.svg` (celdas con su región y su número de creadores, neuronas vacías rayadas, las aristas cortadas como líneas gruesas). Ninguna de las aristas cortadas entre neuronas ocupadas deja una neurona ocupada aislada.

### 6.2 Perfiles por región

Perfil de R1 en unidades originales, con las medias crudas de los 50 creadores (`region_profiles.csv` trae las 31 columnas de `datos/creadores.csv`). La última columna es la participación de cada tema dominante, solo descriptiva: los temas pesan en las componentes de entrada del mapa y su reparto no valida ninguna región.

| Región | Creadores | Seguidores | Alcance en Argentina | Audiencia argentina (%) | Engagement por 1000 | Precio (USD) | Patrocinados (%) | Fútbol (%) | Maquillaje (%) | Perros (%) | Arte (%) | Tema dominante |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 (23 neuronas) | 50 | 221 587 | 43 984 | 52,6 | 68,3 | 1 701 | 27,4 | 27,0 | 24,2 | 27,0 | 21,8 | fútbol (15 de 50) |

Como R1 es todo el mapa, su perfil es el del creador promedio y no distingue grupos. Para leer cómo cambian los perfiles dentro del mapa se dan también los perfiles de las neuronas con al menos 2 creadores (`neuron_profiles.csv`). Son neuronas, no regiones: describen dónde está cada tipo de creador sobre la grilla y no son grupos validados.

| Neurona (fila, col) | Creadores | Seguidores | Alcance en Argentina | Audiencia argentina (%) | Engagement por 1000 | Precio (USD) | Patrocinados (%) | Fútbol (%) | Maquillaje (%) | Perros (%) | Arte (%) | Tema dominante |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| (0, 1) | 2 | 233 923 | 34 794 | 37,6 | 71,7 | 3 201 | 44,1 | 80,2 | 7,5 | 6,0 | 6,3 | fútbol (2 de 2) |
| (0, 2) | 2 | 304 512 | 35 536 | 26,0 | 74,2 | 3 998 | 30,2 | 64,3 | 11,5 | 13,3 | 10,9 | fútbol (2 de 2) |
| (0, 3) | 3 | 408 473 | 85 797 | 57,7 | 70,6 | 3 335 | 41,5 | 64,6 | 11,1 | 11,9 | 12,3 | fútbol (3 de 3) |
| (0, 4) | 2 | 563 174 | 197 462 | 80,7 | 78,2 | 4 059 | 31,5 | 47,0 | 9,7 | 8,9 | 34,4 | empate: fútbol y arte (1 de 2 cada uno) |
| (1, 0) | 3 | 49 115 | 8 821 | 38,8 | 70,7 | 506 | 54,4 | 62,0 | 10,2 | 12,3 | 15,5 | fútbol (3 de 3) |
| (1, 2) | 2 | 289 048 | 28 045 | 33,6 | 73,3 | 1 973 | 31,9 | 9,2 | 14,7 | 13,9 | 62,2 | arte (2 de 2) |
| (1, 4) | 3 | 645 048 | 201 066 | 80,3 | 66,0 | 4 357 | 10,8 | 13,6 | 46,1 | 30,5 | 9,8 | maquillaje (2 de 3) |
| (2, 1) | 3 | 114 457 | 7 281 | 39,1 | 63,5 | 599 | 43,3 | 12,6 | 31,9 | 15,3 | 40,2 | arte (2 de 3) |
| (2, 2) | 3 | 191 684 | 34 328 | 42,6 | 67,2 | 1 586 | 48,9 | 12,9 | 14,7 | 13,3 | 59,1 | arte (3 de 3) |
| (2, 3) | 2 | 413 492 | 43 331 | 34,6 | 62,9 | 2 272 | 50,2 | 7,7 | 76,6 | 9,5 | 6,2 | maquillaje (2 de 2) |
| (3, 1) | 2 | 53 530 | 8 696 | 58,2 | 64,9 | 380 | 4,3 | 30,7 | 15,9 | 15,9 | 37,5 | empate: fútbol y arte (1 de 2 cada uno) |
| (3, 4) | 3 | 370 777 | 24 048 | 31,1 | 75,4 | 1 566 | 6,3 | 12,6 | 67,0 | 11,2 | 9,2 | maquillaje (3 de 3) |
| (4, 0) | 5 | 21 612 | 3 448 | 73,6 | 59,7 | 175 | 15,9 | 8,7 | 11,1 | 69,4 | 10,8 | perros (5 de 5) |
| (4, 1) | 2 | 40 253 | 5 790 | 60,9 | 68,1 | 223 | 11,3 | 9,2 | 11,3 | 72,8 | 6,8 | perros (2 de 2) |
| (4, 2) | 2 | 55 676 | 6 196 | 36,7 | 69,0 | 354 | 14,9 | 12,4 | 10,1 | 67,2 | 10,4 | perros (2 de 2) |
| (4, 3) | 3 | 59 081 | 14 080 | 56,2 | 69,5 | 589 | 3,4 | 8,0 | 10,5 | 51,6 | 30,0 | perros (2 de 3) |
| (4, 4) | 2 | 209 063 | 45 734 | 69,5 | 67,7 | 1 197 | 10,3 | 13,8 | 33,6 | 11,8 | 40,8 | empate: maquillaje y arte (1 de 2 cada uno) |

Las 6 neuronas con un solo creador ((0,0), (1,1), (2,0), (2,4), (3,0) y (3,2)) están marcadas con `flag_lt2` en `neuron_profiles.csv` y no se leen como grupo: su "perfil" es el de ese creador. Cada fila de la tabla sale de 2 a 5 creadores, así que una diferencia entre dos filas vecinas puede ser de un solo creador.

### 6.3 Lectura para la agencia

La regla fijada no ofrece regiones separadas que interpretar: hay una sola, R1, y su perfil es el del conjunto (221 587 seguidores, 52,6 % de audiencia argentina, USD 1 701 de precio medio, 27,4 % de publicaciones patrocinadas). La lectura útil para la agencia es entonces la de un continuo sobre el mapa, apoyada en los perfiles de neurona de 6.2 y siempre como descripción de perfiles. Las recomendaciones de campaña y la comparación contra seguidores son de la Fase 3.

- **Tamaño y precio forman el eje principal del mapa.** En el extremo inferior izquierdo, (4,0), (4,1), (1,0) y (3,1) reúnen creadores chicos y baratos (de 21 612 a 53 530 seguidores; de USD 175 a USD 506). En el extremo superior derecho, (1,4), (0,4), (2,3) y (0,3) reúnen creadores grandes y caros (de 408 473 a 645 048 seguidores; de USD 2 272 a USD 4 357). El engagement por mil se mueve poco entre las neuronas de la tabla (de 59,7 a 78,2).
- **Audiencia argentina.** La proporción más alta está en (0,4) (80,7 %), (1,4) (80,3 %) y (4,0) (73,6 %). La más baja, en (0,2) (26,0 %), (3,4) (31,1 %) y (1,2) (33,6 %): son creadores con la mayor parte de su audiencia fuera de Argentina.
- **Patrocinados.** La proporción de publicaciones patrocinadas es mayor en (1,0) (54,4 %), (2,3) (50,2 %) y (2,2) (48,9 %), y menor, entre las neuronas de la tabla, en (4,3) (3,4 %) y (3,1) (4,3 %): hay perfiles que ya están acostumbrados a la publicidad y otros que casi no la hacen.
- **Temas, solo como descripción.** Los temas pesan en las componentes con las que se entrena el mapa y por eso es esperable que ordenen los lugares; no es una confirmación independiente. Por tema dominante: perros en (4,0), (4,1), (4,2) y (4,3), arte en (1,2), (2,1) y (2,2), fútbol en (0,1), (0,2), (0,3) y (1,0), maquillaje en (1,4), (2,3) y (3,4). Esos lugares se leen como zonas donde el mapa junta creadores con el mismo tema dominante; no como regiones del mapa según la regla, que no los separó.

### 6.4 ¿Coinciden las regiones con PC1 y PC2 (biplot)?

Se usa la lectura de la sección 6.2 de `deliverables/01-datos-pca.md`: PC1 (40,0 % de la varianza) opone `followers`, `likes_per_1000` y `non_follower_reach_pct` a `saves_per_1000`, `profile_visits_per_1000`, `comments_per_1000` y `content_tutorial_pct`; PC2 (11,7 %) opone `sponsored_posts_pct` y `topic_football_pct` a `argentina_audience_pct` y `topic_dogs_pct`. Los estadísticos son los declarados en la sección 2, con 1000 permutaciones de un generador sembrado con 2026; los p son de una cola (cuántas permutaciones igualan o superan lo observado, sumando la observada) y 0,001 es el mínimo posible con 1000 permutaciones. Las figuras son `analysis/results/som/profiles/pc_planes.svg` (media de PC1 y de PC2 de los creadores de cada neurona) y, para compararla, `analysis/results/pca/pruned/biplot.svg`. Como el mapa se entrena con los scores de las 7 primeras componentes, PC1 y PC2 son dos de sus siete entradas: que la grilla las siga es esperable y no una validación independiente.

- R² de PC1 sobre la grilla: 0,938 (p = 0,001)
- R² de PC2 sobre la grilla: 0,439 (p = 0,001)
- Mantel grilla vs plano PC1-PC2: rho = 0,697 (p = 0,001)
- Mantel grilla vs distancia en las 17 variables (referencia): rho = 0,686

Por aristas, la distancia entre prototipos de neuronas ocupadas vecinas se correlaciona con la diferencia de PC1 entre sus medias con rho de Spearman -0,017 y con la de PC2 con 0,080 (32 aristas; las otras 8 tocan una neurona vacía y se excluyen). La regla no declaró un nulo de permutaciones para este estadístico, por eso no lleva p: se informa como descriptivo, y con 32 aristas es un valor poco preciso.

**Respuesta.** Sí para PC1 y también para PC2. El mapa sigue a PC1 de forma casi exacta: la posición (fila, columna) de la mejor neurona explica el 93,8 % de la variación de PC1 entre los 50 creadores, y ninguna de las 1000 permutaciones lo alcanza (p = 0,001). Con PC2 la coincidencia es menor pero clara: R² de 0,439 y p = 0,001. Lo ve `pc_planes.svg`: la media de PC1 por neurona va de -4,40 en (4,0) a 4,06 en (0,4), y la de PC2 de -2,60 en (1,4) a 2,37 en (1,0). Esto describe una dependencia lineal en (fila, columna); es una lectura de la figura, no un estadístico declarado. En conjunto, el orden entre distancias de grilla y distancias en el plano PC1-PC2 coincide moderadamente (rho 0,697, p = 0,001), casi tanto como con las distancias en las 17 variables (0,686), y el patrón por aristas es nulo para PC1 y débil para PC2: las paredes altas de la matriz U no coinciden con saltos de PC1 ni de PC2. Como las regiones de la regla son una sola, la comparación es entre el layout del mapa y los ejes, no entre regiones y ejes.

**Dónde mapa y plano discrepan** (`disagreements.csv`). Cerca en el plano y lejos en la grilla: @futbolcononda (neurona (0,0)) y @rinconcreativo ((4,4)), a 0,69 en el plano y a 5,66 en la grilla; @futbolcononda (neurona (0,0)) y @brochasymates ((4,4)), a 1,78 en el plano y a 5,66 en la grilla; @futbolcononda (neurona (0,0)) y @cosmeticaconsciente ((3,4)), a 0,62 en el plano y a 5,00 en la grilla. Lejos en el plano y vecinos en la grilla: @futbolcononda ((0,0)) y @pasionalbirroja ((1,0)), a 4,00 en el plano; @golconmate ((0,4)) y @crearenreels ((1,4)), a 3,73 en el plano; @patitasenred ((3,2)) y @pasiondepotrero ((3,1)), a 3,65 en el plano. Un mapa no lineal puede separar lo que PC1 y PC2 mezclan porque usa las 7 componentes y el plano PC1-PC2 retiene el 51,7 % de la varianza: el resto, en las otras cinco componentes, puede alejar dos creadores que el plano muestra juntos, y a la inversa una vecindad de la grilla no garantiza cercanía en el plano porque dos neuronas vecinas pueden tener prototipos a hasta 2,64 de distancia en unidades de score (sección 5).

### 6.5 ¿Qué indica una distancia alta entre neuronas vecinas en la matriz U?

Dos neuronas vecinas en la grilla con una distancia alta entre sus prototipos tienen perfiles lejanos en las 7 componentes de entrada (y por eso en las 17 variables que ellas resumen): la distancia alta es un límite entre perfiles distintos, y una zona de valores bajos es una zona homogénea, donde los prototipos vecinos se parecen (es la lectura de la matriz U de las slides del curso). La matriz U no dice cuál es la diferencia; para eso se llevan los prototipos de vuelta al espacio de las variables (con los autovectores de las 7 componentes) y se miran las que más cambian a lo largo de la arista (`high_u_edges.csv`, las 3 aristas más altas entre neuronas ocupadas y sus 3 variables de mayor |delta z|; el delta va de la neurona de menor número a la de mayor).

- **(2,0) a (3,0), distancia 2,64 (la más alta del mapa entre neuronas ocupadas).** `sponsored_posts_pct` baja 1,34 en z (26,1 en unidades originales); `topic_dogs_pct` sube 1,17 en z (29,9 en unidades originales); `argentina_audience_pct` sube 1,06 en z (23,7 en unidades originales). Las dos neuronas tienen 1 y 1 creador.
- **(4,1) a (4,2), distancia 2,38.** `likes_per_1000` sube 0,99 en z (6,8 en unidades originales); `shares_per_1000` sube 0,92 en z (4,3 en unidades originales); `content_review_pct` baja 0,87 en z (8,3 en unidades originales). Las dos neuronas tienen 2 y 2 creadores.
- **(0,1) a (1,1), distancia 2,37.** `non_follower_reach_pct` baja 0,96 en z (17,0 en unidades originales); `monthly_posts` baja 0,88 en z (5,7 en unidades originales); `topic_football_pct` baja 0,83 en z (21,4 en unidades originales). Las dos neuronas tienen 2 y 1 creador.

Las tres aristas más altas se deben a variables distintas: la primera a patrocinio, tema y audiencia argentina, la segunda a engagement y tipo de contenido y la tercera a alcance a no seguidores, frecuencia de publicación y tema fútbol; ninguna a `followers` ni a `price_usd`. En 2 de las tres hay en una punta una neurona con un solo creador, así que ese salto puede ser el de un caso suelto. Y una precaución general: una pared al lado de una neurona vacía es interpolación, no un límite entre grupos de creadores. 2 de las seis aristas más largas del mapa tocan una neurona vacía ((1,2)-(1,3) con 2,50 y (3,2)-(3,3) con 2,33) y por eso no figuran en `high_u_edges.csv` ni sostienen una frontera. Solo un salto entre neuronas ocupadas, como los tres de arriba, la apoya, y aun así con cautela por el tamaño de las neuronas.

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
