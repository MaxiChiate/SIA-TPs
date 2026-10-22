# Fase 3 — Regla de Oja y decisiones de campaña

## 3. ¿Qué representa el índice? ¿Sería correcto elegir el máximo para cualquier campaña?

**No.** El índice de Oja es la proyección de cada creador sobre PC1 (sección 2): un eje de escala y formato que retiene el 53,2 % de la varianza de las 26 variables y que casi no mira los temas: la Fase 1 ubicó fútbol y maquillaje en PC3 y PC4 y perros en PC2, no en PC1 (secciones 6 de `deliverables/01-datos-pca.md` y 6.4 de `deliverables/02-kohonen.md`). El creador con el valor más alto es el que está más lejos en un extremo de ese eje, y cuál extremo es "el máximo" lo decide una convención de signo; ni una ni otra cosa dice nada sobre el tema o el objetivo de una campaña.

**Qué representa y cómo se lee.** Con la convención D-02 (el coeficiente de mayor valor absoluto, `average_caption_words`, es positivo; sección 1) un índice alto es un creador chico, de epígrafes largos, con más contenido tutorial y de reseña y más guardados, comentarios y visitas al perfil por mil; un índice bajo es un creador grande y caro, con más followers, alcance, impresiones y precio y más video corto y de tendencia. La tabla ordena las 26 variables por el valor absoluto de su coeficiente en `w` (semilla 1, la de las figuras); las cuatro de tamaño y alcance más los formatos de video ocupan el lado negativo, y los epígrafes, los guardados y los comentarios el positivo.

| Variable | w (convención D-02) |
|---|---|
| average_caption_words | +0,2521 |
| average_impressions | -0,2494 |
| average_video_views | -0,2482 |
| average_reach | -0,2474 |
| trend_posts_pct | -0,2413 |
| followers | -0,2364 |
| video_posts_pct | -0,2353 |
| price_usd | -0,2349 |
| short_form_posts_pct | -0,2337 |
| saves_per_1000 | +0,2255 |
| likes_per_1000 | -0,2115 |
| content_entertainment_pct | -0,2101 |
| profile_visits_per_1000 | +0,2074 |
| comments_per_1000 | +0,2063 |
| estimated_argentina_reach | -0,2022 |
| non_follower_reach_pct | -0,1983 |
| average_watch_time_seconds | +0,1977 |
| content_tutorial_pct | +0,1952 |
| shares_per_1000 | -0,1786 |
| content_review_pct | +0,1756 |
| topic_dogs_pct | +0,1290 |
| topic_football_pct | -0,0641 |
| topic_makeup_pct | -0,0630 |
| monthly_posts | -0,0355 |
| argentina_audience_pct | +0,0247 |
| sponsored_posts_pct | -0,0140 |

**Con qué se correlaciona.** Las correlaciones son entre el índice (con cada signo) y los valores crudos de `datos/creadores.csv`: `followers` y los cuatro porcentajes de tema, `topic_art_pct` incluido aunque quedó fuera del entrenamiento en la Fase 1. Con el signo de D-02 el índice baja casi en bloque con el tamaño (Pearson -0,879 y Spearman -0,921 con `followers`); con el signo opuesto sube con él. Los temas tienen una relación mucho más débil y despareja: perros es la única que pasa de 0,4 en valor absoluto (+0,480 con el signo de D-02; su coeficiente en `w`, +0,1290, es también el mayor de los tres temas del entrenamiento), fútbol y maquillaje rondan 0,23 de Pearson y arte es prácticamente nula.

| Variable cruda | Pearson (D-02) | Spearman (D-02) | Pearson (signo opuesto) | Spearman (signo opuesto) |
|---|---|---|---|---|
| followers | -0,879 | -0,921 | +0,879 | +0,921 |
| topic_football_pct | -0,239 | -0,229 | +0,239 | +0,229 |
| topic_makeup_pct | -0,234 | -0,122 | +0,234 | +0,122 |
| topic_dogs_pct | +0,480 | +0,483 | -0,480 | -0,483 |
| topic_art_pct | -0,029 | +0,022 | +0,029 | -0,022 |

**Los diez primeros según el índice.** Hay dos maneras de preguntar si el top 10 del índice coincide con "los top 10 de cada tema dominante", y se muestran las dos con ambos signos. La primera es el solapamiento del top 10 del índice con el top 10 de cada porcentaje de tema crudo (los empates de la frontera se resuelven por orden de fila). La segunda es la composición del top 10 del índice: cuántos de sus diez creadores tienen cada tema como dominante. Con el signo de D-02, siete de los diez primeros son de perros y ninguno es de arte; con el opuesto, cinco son de fútbol, tres de maquillaje, y de perros solo uno. El índice favorece un tema en cada extremo, y el arte queda casi afuera en ambos.

| Tema | Top 10 por porcentaje en común con el top 10 del índice (D-02) | Top 10 por porcentaje en común con el top 10 del índice (signo opuesto) | Creadores del top 10 del índice con ese tema dominante (D-02) | Creadores del top 10 del índice con ese tema dominante (signo opuesto) |
|---|---|---|---|---|
| fútbol | 1 de 10 | 4 de 10 | 2 de 10 | 5 de 10 |
| maquillaje | 1 de 10 | 3 de 10 | 1 de 10 | 3 de 10 |
| perros | 5 de 10 | 1 de 10 | 7 de 10 | 1 de 10 |
| arte | 0 de 10 | 1 de 10 | 0 de 10 | 1 de 10 |

**El máximo bajo cada signo.** Es el mismo modelo, los mismos datos y la misma semilla; solo cambia el signo, y el creador que sale primero es otro, de otro tema y de otro tamaño:

- Máximo con el signo de D-02: INF031 (@mundoanimal.ar), tema dominante perros, 17062 followers, índice +6,70.
- Máximo con el signo opuesto: INF045 (@futbolsinvueltas), tema dominante fútbol, 493194 followers, índice +6,26.

**Conclusión.** Elegir automáticamente al creador con el valor más alto del índice no es correcto para cualquier campaña, por tres razones que salen de las tablas de arriba. Primero, "el máximo" depende de una convención: la de D-02 fija el signo para que `w` sea reproducible (sección 1), y dar vuelta el signo da el creador del extremo opuesto; el margen que la sostiene es de apenas 0,00275 (sección 1), así que con otros datos la convención podría elegir la otra variable y también invertir el índice. Segundo, ninguno de los dos máximos es neutral: bajo D-02 sale un creador de perros de 17 mil followers, y bajo el signo opuesto uno de fútbol de casi 500 mil, y en el top 10 de cada signo un tema domina y arte casi no aparece. Tercero, el índice es en lo esencial una forma de ordenar por tamaño (|Spearman| de 0,921 con `followers`) y no sabe cuál es el tema de la campaña ni qué se busca con ella: ni alcance masivo, ni descubrimiento, ni costo por mil, ni profundidad. Una campaña debe entonces filtrar primero por su tema y ordenar por su propio objetivo, que es la regla de la sección 4; el índice de Oja queda como descripción de cada lista y como desempate de empates exactos, sin decidir quién entra.

## 4. Regla de selección por campaña (fijada antes de calcular las listas)

<!-- regla:inicio -->
Esta sección fija la regla; los resultados se agregan después y no figuran acá. Las decisiones D-07 a D-17 están en `.planning/phases/03-oja-y-decisiones-de-campa-a/03-CONTEXT.md` y los términos que dejaban abiertos se fijaron en el checkpoint del plan 03-02. Al commitear esta sección no existía `analysis/campaigns.py` ni se había calculado ninguna lista de campaña, propia ni por followers.

- **Alcance.** Seis listas calculadas sobre los valores crudos de `datos/creadores.csv`: fútbol tiene tres, y perros, maquillaje y arte una cada uno. Cada lista es un filtro por tema más un único criterio de ranking; no hay un score ponderado general (D-08).
- **Tema dominante y filtro.** El tema dominante de un creador es el argmax de los cuatro `topic_*_pct` crudos de `datos/creadores.csv`; un empate exacto va al primero de fútbol, maquillaje, perros, arte (el orden de la etiqueta del biplot de la Fase 1 y de la Fase 2). El filtro de una campaña deja a los creadores cuyo tema dominante es el de la campaña.
- **k.** k = 5 por lista y por estrategia (D-09). Un filtro con menos de 5 creadores da todos sus miembros en el orden del ranking, nunca completados con creadores de otros temas; un filtro sin miembros da una lista vacía.
- **Fútbol.** Tres listas, una por objetivo (D-10). *Alcance masivo*: `estimated_argentina_reach`, de mayor a menor. *Descubrimiento*: `non_follower_reach_pct`, de mayor a menor; `trend_posts_pct` se informa al lado como apoyo y es la segunda clave, de modo que solo decide un empate exacto de `non_follower_reach_pct`. *Profundidad educativa*: el puntaje de profundidad, que es la media de z(`content_tutorial_pct`), z(`saves_per_1000`) y z(`average_watch_time_seconds`), de mayor a menor.
- **Perros.** Supuesto del cliente (D-11): refugios, con poco presupuesto y alcance local. El criterio es el costo por mil argentinos alcanzados = price_usd / estimated_argentina_reach × 1000, de menor a mayor; un alcance argentino de cero cuenta como costo infinito y queda último.
- **Maquillaje.** Supuesto del cliente (D-11): una marca de belleza, que busca profundidad. El criterio es el puntaje de profundidad definido en Fútbol (media de z(`content_tutorial_pct`), z(`saves_per_1000`) y z(`average_watch_time_seconds`)), de mayor a menor.
- **Arte.** Supuesto del cliente (D-11): materiales de arte, un nicho que busca engagement por 1000 y profundidad. El puntaje es 1/2 z(`total_engagement_per_1000`) + 1/2 × el puntaje de profundidad, de mayor a menor: el engagement pesa la mitad y las tres variables de profundidad la otra mitad. `saves_per_1000` forma parte también de `total_engagement_per_1000`, y esta regla lo asume.
- **Puntajes compuestos.** Los z de los puntajes compuestos se calculan sobre los 50 creadores, con desvío muestral ddof = 1, a partir de los valores crudos, y no dentro del filtro. Para las tres variables de profundidad coincide con el escalador guardado de `datos/prepared/creadores_zscore.meta.json`; `total_engagement_per_1000` salió del conjunto auditado de la Fase 1 (D-09) pero sigue en el CSV crudo y recibe la misma fórmula.
- **Desempate.** Un empate exacto en el criterio (y en la segunda clave, en descubrimiento) lo gana el creador con mayor índice de Oja, con el signo de D-02 de la corrida de la semilla de las figuras 1 (`analysis/results/oja/index.csv`); si el índice de Oja también es igual, gana el `creator_id` menor (D-13). Las dos líneas base por followers usan el mismo desempate.
- **Precio.** El precio no filtra ni topea ninguna lista (D-12). El informe da, para cada lista, el costo total (suma de `price_usd`) y el costo por mil argentinos alcanzados.
- **Líneas base por followers.** Dos líneas base, ambas con k = 5 (D-16): (a) los 5 creadores con más `followers` entre los 50; (b) los 5 creadores con más `followers` dentro del filtro de tema de la campaña, que aísla el efecto del criterio de ranking. Ambas usan el desempate de arriba, y la (b) con menos de 5 miembros da todos los que haya.
- **Métricas de comparación.** Por campaña y por lista (cada lista propia y las dos líneas base), según D-17: el overlap@5 con cada línea base, que es la cantidad de `creator_id` compartidos; la proporción de la lista cuyo tema dominante es el de la campaña, más la media de la lista del porcentaje crudo del tema de la campaña; el alcance argentino total (suma de `estimated_argentina_reach`); el costo total (suma de `price_usd`); el costo por mil argentinos de la lista = costo total / alcance argentino total × 1000 (cociente de sumas); y la métrica objetivo = la media de la lista del criterio en sus propias unidades y la media de cada variable cruda que usa el criterio.
- **Kohonen, Oja y PCA.** El SOM es solo descriptivo (D-14): se informa la neurona de cada creador elegido y se puede marcar en el mapa de hits. El índice de Oja de cada elegido y su posición en PC1/PC2 describen la lista (D-15). Ninguno de los tres cambia quién entra a una lista; el índice de Oja solo desempata empates exactos.
- **Recomendación de fútbol.** Después de que existan las tres listas de fútbol se escribe una recomendación como juicio, con los supuestos explícitos sobre el cliente (una marca de ropa de entrenamiento de fútbol) (D-10). La regla no elige el objetivo.
- **Resultados comerciales.** Los datos no contienen ventas, adopciones ni conversiones, por lo que no se afirma que ninguna de las dos estrategias recupere la inversión (D-17). El informe lista también las ventajas de la estrategia por followers: es simple, estable, no requiere un modelo que mantener y está correlacionada con el alcance.
- **Control.** `analysis/campaigns.py` llama primero a `rule_identity` y se niega a correr salvo que este archivo y `analysis/campaigns_select.py` se hayan agregado en un mismo commit, el código no haya cambiado desde entonces y el texto entre estos marcadores tenga el mismo sha256 que en ese commit; registra el commit y los dos sha256.
<!-- regla:fin -->
