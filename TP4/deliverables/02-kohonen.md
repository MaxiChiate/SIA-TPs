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
