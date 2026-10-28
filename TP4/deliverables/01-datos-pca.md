# Fase 1 — Datos, auditoría de variables y PCA

Fragmento de la Fase 1 del informe del TP4. Las cifras de este documento salen de los archivos generados por `make eda` en `analysis/results/eda/` y del archivo `datos/prepared/creadores_zscore.meta.json`; cada sección indica el comando que las regenera. Las decisiones de las secciones 3, 4 y 5 quedaron fijadas antes de calcular ninguna PCA (ver `.planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-CONTEXT.md`, decisiones D-08 a D-13).

## 1. Carga y verificación

`datos/creadores.csv` tiene 50 creadores y 33 columnas: `creator_id`, `name` y 31 variables numéricas. La última línea del archivo no termina en salto de línea, por lo que las filas se cuentan parseando el archivo y no con `wc -l`. `load_creadores` (`scripts/creadores.py`) falla con un error explícito si el archivo no es de 50 × 33, si una fila tiene otra cantidad de campos o si una celda no es un número finito, indicando línea, columna y texto (DATA-01). Regenera: `make prepare`.

## 2. Exploración (EDA)

Figuras (se regeneran con `make eda`):

- `analysis/results/eda/distributions.svg` (y `.png`): histogramas de las 31 variables en unidades originales, con la asimetría de cada una en el título.
- `analysis/results/eda/correlation.svg` (y `.png`): matriz de correlación de Pearson de 31 × 31.

Tablas: `summary_stats.csv` (media, desvío con ddof = 1, mínimo, mediana, máximo y asimetría de Fisher-Pearson) y `strong_correlations.csv` (los pares con |r| ≥ 0,8).

**Distribuciones.** Las variables más asimétricas son `estimated_argentina_reach` (asimetría 1,97), `topic_makeup_pct` (1,38), `topic_art_pct` (1,32), `price_usd` (1,17), `topic_dogs_pct` (1,09) y `topic_football_pct` (1,04). Las de tamaño `followers`, `average_reach`, `average_impressions` y `average_video_views` rondan 0,94 a 0,96: muchos creadores chicos y pocos grandes. Los temas tienen una masa cerca de 5 a 20 % y una cola de creadores especializados con 60 a 80 % en un solo tema. El resto de las variables está entre −0,8 y 0,6.

**Correlaciones.** El bloque de tamaño (`followers`, `average_reach`, `average_impressions`, `average_video_views`) tiene correlaciones entre 0,91 y 0,997; el par más fuerte entre variables distintas es `average_reach` con `average_video_views` (0,997). `price_usd` se mueve con ese bloque (0,82 con `followers`, 0,91 con `average_impressions`). `video_posts_pct`, `short_form_posts_pct` y `trend_posts_pct` forman otro bloque (0,95 a 0,97) y `likes_per_1000` se les acerca (0,90 con `short_form_posts_pct`). `average_caption_words` correlaciona negativamente con el tamaño (entre −0,82 y −0,86). Dentro de las composiciones, las correlaciones negativas (por ejemplo `content_tutorial_pct` con `content_entertainment_pct`, −0,84, y las seis de `topic_*`, entre −0,27 y −0,44) son en parte un efecto aritmético de que los porcentajes suman 100, no una relación de contenido.

## 3. Auditoría de variables

### 3.1 Dependencias lineales exactas

Cinco relaciones se cumplen con residuo máximo por debajo de 1e-6 (`analysis/results/eda/exact_dependencies.csv`, D-08):

| Relación | Residuo máximo |
|---|---|
| `price_ars = 1500 · price_usd` | 9,3e-10 |
| `organic_posts_pct = 100 − sponsored_posts_pct` | 0 |
| `total_engagement_per_1000 = likes_per_1000 + comments_per_1000 + saves_per_1000 + shares_per_1000` | 1,4e-14 |
| suma de `topic_*` = 100 | 1,4e-14 |
| suma de `content_*` = 100 | 1,4e-14 |

Con las 31 columnas la matriz de correlación es singular (rango 26): cinco autovalores prácticamente nulos. La PCA, el SOM y la regla de Oja trabajarían sobre direcciones sin información.

### 3.2 Regla de selección

La regla se fijó de antemano (D-09) y `audit_variables` la aplica sobre los datos en cada corrida:

1. Salen `price_ars`, `organic_posts_pct` y `total_engagement_per_1000`, que son función exacta de otras variables.
2. De `topic_*` y de `content_*` sale el miembro con menor varianza en unidades originales (antes del z-score), porque es el que menos información propia aporta a una composición que suma 100. Las varianzas medidas (ddof = 1) son: `topic_football_pct` 667,2; `topic_makeup_pct` 561,2; `topic_dogs_pct` 658,1; `topic_art_pct` 457,8; `content_tutorial_pct` 350,9; `content_review_pct` 90,7; `content_entertainment_pct` 864,7; `content_showcase_pct` 81,9. Salen `topic_art_pct` y `content_showcase_pct`.

El conjunto auditado queda en 26 variables. Las variables que salen se conservan en el CSV crudo y se pueden reconstruir con las restantes (la fórmula está en cada fila de la tabla 3.4 y en `datos/prepared/creadores_zscore.meta.json`). Los cuatro temas siguen disponibles para las campañas: en la Fase 2, el plano de componentes de cada variable que no entra al entrenamiento (en particular `topic_art_pct`) se calcula como el promedio de esa variable cruda entre los creadores asignados a cada neurona, de modo que las cuatro campañas tienen su plano aunque el SOM se entrene con tres temas.

### 3.3 Casi redundantes (se documentan, no se eliminan)

`analysis/results/eda/near_redundant.csv` (D-10). Quedan en el conjunto porque no son exactas y porque su efecto se discute en la PCA (PC1 se espera como tamaño):

| Variable | r con `followers` | Error máximo frente a la fórmula |
|---|---|---|
| `average_reach` | 0,918 | |
| `average_impressions` | 0,912 | |
| `average_video_views` | 0,906 | |
| `estimated_argentina_reach` | 0,798 | 0,499 |

`estimated_argentina_reach` es una aproximación de `average_reach · argentina_audience_pct / 100` con error máximo 0,499 (redondeo a entero), por eso no es una dependencia exacta.

### 3.4 Tabla de auditoría

Generada por `make eda` (analysis/results/eda/audit_table.md).

| Variable | Grupo | Relación | Decisión | Motivo |
|---|---|---|---|---|
| `followers` | tamaño y alcance |  | entra | variable original |
| `average_reach` | tamaño y alcance | casi redundante (se documenta, no se elimina) | entra | casi redundante: r = 0.918 con followers |
| `average_impressions` | tamaño y alcance | casi redundante (se documenta, no se elimina) | entra | casi redundante: r = 0.912 con followers |
| `average_video_views` | tamaño y alcance | casi redundante (se documenta, no se elimina) | entra | casi redundante: r = 0.906 con followers |
| `monthly_posts` | actividad |  | entra | variable original |
| `argentina_audience_pct` | audiencia |  | entra | variable original |
| `estimated_argentina_reach` | tamaño y alcance | casi redundante (se documenta, no se elimina) | entra | aproximación no exacta, error máx 0.499 frente a average_reach · argentina_audience_pct / 100 |
| `non_follower_reach_pct` | audiencia |  | entra | variable original |
| `likes_per_1000` | engagement por 1000 | total_engagement_per_1000 = likes + comments + saves + shares (por 1000) | entra | base de la relación total_engagement_per_1000 = likes + comments + saves + shares (por 1000) |
| `comments_per_1000` | engagement por 1000 | total_engagement_per_1000 = likes + comments + saves + shares (por 1000) | entra | base de la relación total_engagement_per_1000 = likes + comments + saves + shares (por 1000) |
| `saves_per_1000` | engagement por 1000 | total_engagement_per_1000 = likes + comments + saves + shares (por 1000) | entra | base de la relación total_engagement_per_1000 = likes + comments + saves + shares (por 1000) |
| `shares_per_1000` | engagement por 1000 | total_engagement_per_1000 = likes + comments + saves + shares (por 1000) | entra | base de la relación total_engagement_per_1000 = likes + comments + saves + shares (por 1000) |
| `total_engagement_per_1000` | engagement por 1000 | total_engagement_per_1000 = likes + comments + saves + shares (por 1000) | sale (reconstruible) | dependencia lineal exacta: suma de las cuatro interacciones por mil; total_engagement_per_1000 = likes_per_1000 + comments_per_1000 + saves_per_1000 + shares_per_1000 |
| `profile_visits_per_1000` | engagement por 1000 |  | entra | variable original |
| `price_usd` | precio | price_ars = 1500 · price_usd | entra | base de la relación price_ars = 1500 · price_usd |
| `price_ars` | precio | price_ars = 1500 · price_usd | sale (reconstruible) | dependencia lineal exacta con price_usd; price_ars = 1500 · price_usd |
| `sponsored_posts_pct` | patrocinio | organic_posts_pct = 100 − sponsored_posts_pct | entra | base de la relación organic_posts_pct = 100 − sponsored_posts_pct |
| `organic_posts_pct` | patrocinio | organic_posts_pct = 100 − sponsored_posts_pct | sale (reconstruible) | dependencia lineal exacta con sponsored_posts_pct; organic_posts_pct = 100 − sponsored_posts_pct |
| `topic_football_pct` | temas (composición) | suma de topic_* = 100 | entra | base de la relación suma de topic_* = 100 |
| `topic_makeup_pct` | temas (composición) | suma de topic_* = 100 | entra | base de la relación suma de topic_* = 100 |
| `topic_dogs_pct` | temas (composición) | suma de topic_* = 100 | entra | base de la relación suma de topic_* = 100 |
| `topic_art_pct` | temas (composición) | suma de topic_* = 100 | sale (reconstruible) | composición que suma 100: menor varianza del grupo; 100 − (suma de los otros tres) |
| `content_tutorial_pct` | tipo de contenido (composición) | suma de content_* = 100 | entra | base de la relación suma de content_* = 100 |
| `content_review_pct` | tipo de contenido (composición) | suma de content_* = 100 | entra | base de la relación suma de content_* = 100 |
| `content_entertainment_pct` | tipo de contenido (composición) | suma de content_* = 100 | entra | base de la relación suma de content_* = 100 |
| `content_showcase_pct` | tipo de contenido (composición) | suma de content_* = 100 | sale (reconstruible) | composición que suma 100: menor varianza del grupo; 100 − (suma de los otros tres) |
| `average_caption_words` | formato y estilo |  | entra | variable original |
| `average_watch_time_seconds` | formato y estilo |  | entra | variable original |
| `video_posts_pct` | formato y estilo |  | entra | variable original |
| `short_form_posts_pct` | formato y estilo |  | entra | variable original |
| `trend_posts_pct` | formato y estilo |  | entra | variable original |

## 4. Estandarización

Se aplica z-score directo con ddof = 1, sin transformación logarítmica ni winsorizado (D-11). La asimetría máxima medida es 1,97 (`estimated_argentina_reach`); `followers`, alcance y precio rondan 1. Con una asimetría de ese orden y n = 50, se prefiere no deformar la escala; el logaritmo queda mencionado solo como sensibilidad opcional, fuera del camino principal.

El scaler (`features`, `mean`, `std` y `ddof`) se guarda en `datos/prepared/creadores_zscore.meta.json`, junto con las variables eliminadas y sus fórmulas. La variante de 31 columnas `datos/prepared/creadores_zscore_all31.csv` existe solo para la corrida de sensibilidad etiquetada (DATA-05) y no es el conjunto auditado.

Para mapear un creador nuevo alcanza con el archivo meta, sin releer `datos/creadores.csv`:

```
.venv/bin/python scripts/map_creator.py --meta datos/prepared/creadores_zscore.meta.json --input nuevos.csv
```

Mapear `datos/creadores.csv` con ese mismo comando reproduce la matriz `datos/prepared/creadores_zscore.csv` byte a byte (DATA-03). Regenera: `make prepare`; dos corridas seguidas dan el mismo sha256 en los cuatro archivos de `datos/prepared/`.

## 5. PCA: regla de decisión (fijada antes de mirar los autovalores)

Esta sección fija la regla; los resultados se agregan después y no figuran acá. Las decisiones D-12 y D-13 están escritas en `.planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-CONTEXT.md` antes de que existiera ninguna salida de la PCA.

- **Método.** PCA sobre la matriz de correlación (igual a la covarianza de la matriz con z-score y n − 1), por autovalores, verificada con `np.linalg.eigh`.
- **Cantidad de componentes.** k es el menor número de componentes cuya varianza acumulada alcanza 80 %.
- **Umbral.** El 80 % es una convención del equipo: la teoría del curso da la proporción de varianza de cada componente, pero no fija un umbral.
- **Signo de los componentes.** Cada autovector se orienta de modo que su coeficiente de mayor magnitud sea positivo.
- **Rol.** La PCA es diagnóstica (D-13): dice si la dimensionalidad se podría reducir y cómo leer PC1 y PC2 (biplot). Kohonen y Oja corren sobre la matriz completa con z-score del conjunto auditado (26 variables), como pide el enunciado; no se agrega una corrida del SOM sobre k componentes.

## 6. PCA: resultados e interpretación

Las cifras salen de `analysis/results/pca/audited/` (`eigenvalues.csv`, `loadings.csv`, `decision.json`), que escribe `make pca`. La PCA se hizo por autovalores de la matriz de correlación de las 26 variables auditadas, con la regla de la sección 5 aplicada sin cambios. La suma de los 26 autovalores da 26 (dentro de 1e-9), como corresponde a una matriz de correlación.

| Componente | Autovalor | % de varianza | % acumulado |
|---|---|---|---|
| PC1 | 13,84 | 53,2 | 53,2 |
| PC2 | 2,21 | 8,5 | 61,7 |
| PC3 | 1,86 | 7,1 | 68,9 |
| PC4 | 1,49 | 5,7 | 74,6 |
| PC5 | 1,17 | 4,5 | 79,1 |
| PC6 | 1,04 | 4,0 | 83,1 |
| PC7 | 0,78 | 3,0 | 86,1 |

- Componentes para el 80 % de la varianza: 6

El umbral queda justo: con 5 componentes se llega a 79,1 %, a menos de un punto del 80 %. Con otros datos el k podría haber dado 5 o 7.

**Cómo se leen PC1 y PC2.** Las cargas son las correlaciones entre cada variable y cada componente (`loadings.csv`). Cada autovector está orientado con la convención de la sección 5 (su coeficiente de mayor magnitud es positivo), por eso el signo de un componente es una convención y lo que informa es qué variables quedan en el mismo extremo y cuáles en el opuesto.

- **PC1 (53,2 %)** opone dos grupos. En el extremo positivo: `average_caption_words` (+0,94), `saves_per_1000` (+0,84), `comments_per_1000` y `profile_visits_per_1000` (+0,77), `content_tutorial_pct` y `average_watch_time_seconds` (+0,73). En el extremo negativo: `average_impressions` (−0,93), `average_video_views` (−0,92), `average_reach` (−0,92), `trend_posts_pct` (−0,90), `followers` (−0,88), `video_posts_pct` (−0,88), `price_usd` (−0,87) y `short_form_posts_pct` (−0,87). Es un eje de escala y formato: tamaño, alcance y precio, junto con contenido de video corto y de tendencia, de un lado; epígrafes largos, contenido tutorial y respuesta que se guarda, comenta o lleva al perfil, del otro. Un creador grande y caro queda a la izquierda del biplot.
- **PC2 (8,5 %)** se apoya en la audiencia argentina: `argentina_audience_pct` (+0,73), `estimated_argentina_reach` (+0,51) y `topic_dogs_pct` (+0,42) del lado positivo; `monthly_posts` (−0,38), `likes_per_1000` (−0,36) y `sponsored_posts_pct` (−0,35) del negativo.
- Para tener presente: PC3 (7,1 %) la dominan `sponsored_posts_pct` (+0,73) y `topic_football_pct` (+0,60), y PC4 (5,7 %) `topic_makeup_pct` (+0,83) contra `topic_football_pct` (−0,52). Los temas, que no pesan en PC1, aparecen recién en esos componentes.

**Cómo se lee el biplot** (`analysis/results/pca/audited/biplot.svg`). Los puntos son los 50 creadores en PC1 y PC2, coloreados por su tema dominante (el mayor de los cuatro porcentajes de tema originales, incluido `topic_art_pct`, que se eliminó del conjunto auditado). Las flechas son las cargas de cada variable en PC1 y PC2 multiplicadas por el factor de escala `s` que figura en el subtítulo (6,43), solo para que se vean junto a los puntos; la longitud de una flecha mide cuán bien esa variable queda representada en el plano, y dos flechas casi paralelas indican variables correlacionadas. Se etiquetan las 8 con mayor norma. Dos creadores cercanos se parecen solo dentro del plano PC1-PC2, que retiene 61,7 % de la varianza (`cumulative_pc2`); el 38,3 % restante no se ve en la figura. La dirección de `topic_dogs_pct` (+0,48 en PC1 y +0,42 en PC2) es coherente con que los creadores de perros queden hacia la derecha y arriba.

Figuras de esta sección: `analysis/results/pca/audited/eigenvalues_variance.svg` (autovalores arriba, varianza acumulada abajo con la línea de 80 %, y la barra del sexto componente resaltada), `analysis/results/pca/audited/loadings.svg` (cargas de PC1 a PC6 con dos decimales) y `analysis/results/pca/audited/biplot.svg`.

### 6.1 ¿Se reduce la dimensionalidad?

La PCA muestra que 6 componentes de 26 retendrían 83,1 % de la varianza (el menor k que supera 80 %), de modo que para describir los datos una reducción sería posible. Pero la PCA es diagnóstica (D-13): Kohonen (Fase 2) y Oja (Fase 3) corren sobre las 26 variables auditadas con z-score, como pide el enunciado, y no sobre los 6 componentes. PC1 y PC2 sirven para leer el mapa de Kohonen y como referencia de Oja, con la misma convención de signo de la sección 5.

## 7. Sensibilidad: las 31 columnas

Corrida de sensibilidad (DATA-05): no es el conjunto auditado. Es la misma PCA sobre las 31 columnas con z-score (`datos/prepared/creadores_zscore_all31.csv`), que incluyen las 5 dependencias lineales exactas. Los números salen de `analysis/results/pca/sensitivity.json` y se repiten en `analysis/results/pca/sensitivity.md`; las figuras están en `analysis/results/pca/all31_sensitivity/` y llevan en el título la leyenda SENSIBILIDAD.

| Medida | Auditado | 31 columnas |
|---|---|---|
| Variables | 26 | 31 |
| Autovalores nulos | 0 | 5 |
| Componentes para el 80 % | 6 | 6 |
| % de varianza de PC1 | 53,2 | 48,0 |
| % de varianza de PC2 | 8,5 | 9,8 |

Sobre las 26 variables comunes (autovectores de 31 columnas restringidos y renormalizados):

| Componente | abs(cos) de los autovectores | Pearson de scores | Spearman de scores |
|---|---|---|---|
| PC1 | 0,99998 | −0,9992 | −0,9982 |
| PC2 | 0,9680 | 0,9217 | 0,8925 |

Qué cambian las 5 dependencias exactas:

- **Autovalores nulos.** La matriz de correlación de 31 columnas tiene rango 26, por eso aparecen exactamente 5 autovalores nulos (el menor vale −3,2e-16, ruido numérico). Esa matriz es singular y no sirve para nada que la invierta.
- **Los conteos.** El criterio de 80 % no se mueve (6 y 6). La suma de autovalores también cambia (31 en vez de 26), por lo que los porcentajes de varianza no son directamente comparables entre una y otra corrida.
- **Cuánto se mueven los componentes principales.** PC1 casi no cambia como dirección (abs(cos) 0,99998) ni como orden de los creadores (Spearman en valor absoluto 0,9982). El signo opuesto del Pearson y del Spearman de PC1 no es una diferencia de resultado: en la corrida de 31 columnas el coeficiente de mayor magnitud de PC1 pertenece a otra variable, y la convención de orientación elige el signo contrario. PC2 se mueve más (abs(cos) 0,968, Spearman 0,89): el orden de los creadores en PC2 depende algo del conjunto de variables.

El conjunto auditado es el que usan los modelos porque su matriz de correlación es regular (ningún autovalor nulo, el menor es 0,00046 según `decision.json`) y ninguna variable entra repetida: lo que cambia entre los dos conjuntos es el peso de la información duplicada, no la estructura principal de los datos.

## 8. Cómo reproducir

Desde `TP4/`:

```
make venv      # crea .venv e instala analysis/requirements.txt (versiones fijadas)
make prepare   # escribe datos/prepared/: matriz auditada y de 31 columnas con sus .meta.json
make eda       # escribe analysis/results/eda/: figuras, tablas CSV y audit_table.md
make pca       # escribe analysis/results/pca/: para audited/ y all31_sensitivity/ los autovalores,
               # autovectores, cargas, scores, eigenvalues plot, loadings, biplot y decision.json; y la
               # comparación sensitivity.json y sensitivity.md
make test      # 3 tests de C y 6 de Python (incluye el de la PCA)
```

`make prepare` es determinista (mismo sha256 en reejecuciones) y `datos/prepared/` y `analysis/results/` no se versionan: se regeneran.
