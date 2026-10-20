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

## 5. PCA: regla de decisión (fijada antes de mirar el scree)

Esta sección fija la regla; los resultados se agregan después y no figuran acá. Las decisiones D-12 y D-13 están escritas en `.planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-CONTEXT.md` antes de que existiera ninguna salida de la PCA.

- **Método.** PCA sobre la matriz de correlación (igual a la covarianza de la matriz con z-score y n − 1), por autovalores, verificada con `np.linalg.eigh`.
- **Cantidad de componentes.** k es el menor número de componentes cuya varianza acumulada alcanza 80 %.
- **Control.** El criterio de Kaiser (autovalor > 1) se usa como control. Si ambos criterios difieren, se reporta la discrepancia y no se resuelve por preferencia.
- **Signo de los componentes.** Cada autovector se orienta de modo que su coeficiente de mayor magnitud sea positivo.
- **Rol.** La PCA es diagnóstica (D-13): dice si la dimensionalidad se podría reducir y cómo leer PC1 y PC2 (biplot). Kohonen y Oja corren sobre la matriz completa con z-score del conjunto auditado (26 variables), como pide el enunciado; no se agrega una corrida del SOM sobre k componentes.

## 8. Cómo reproducir

Desde `TP4/`:

```
make venv      # crea .venv e instala analysis/requirements.txt (versiones fijadas)
make prepare   # escribe datos/prepared/: matriz auditada y de 31 columnas con sus .meta.json
make eda       # escribe analysis/results/eda/: figuras, tablas CSV y audit_table.md
```

`make prepare` es determinista (mismo sha256 en reejecuciones) y `datos/prepared/` y `analysis/results/` no se versionan: se regeneran.
