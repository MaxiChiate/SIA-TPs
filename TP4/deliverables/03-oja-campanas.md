# Fase 3 — Regla de Oja y decisiones de campaña

## 1. Regla de Oja: algoritmo, parámetros y convergencia

**Datos.** La neurona entrena sobre las 26 variables auditadas de la Fase 1 con z-score (`datos/prepared/creadores_zscore.csv`, 50 creadores). Como cada columna tiene media 0 (lo comprueba `test_input_is_centered`, con medias de valor absoluto menores que 1e-12), la regla converge al primer componente principal de la matriz de covarianza; con datos sin centrar convergería a otra dirección, dominada por las medias.

**Algoritmo.** Para cada creador `x` se calcula `y = w · x` y se actualiza `w ← w + η y (x − y w)` (regla de Oja, slides del curso p. 16). `w` arranca con cada componente uniforme en [0, 1) (con la semilla de la corrida) y escalado a longitud 1. Cada época recorre los 50 creadores una vez, en un orden barajado distinto cada vez. La tasa η decae exponencialmente de η0 a ηf a lo largo de todas las actualizaciones, y el número de épocas es fijo: no hay parada por tolerancia. Al terminar se renormaliza `w` a longitud 1 y se le aplica la convención de signo D-02. El índice de cada creador es `x · w`.

**Parámetros.** `neuron/config.json.oja.example`: η0 = 0,001 (el valor del curso, slides p. 15), ηf = 0,0001 y 500 épocas. η0 es chico a propósito: la regla es estable cuando η0 · máx ‖x‖² es mucho menor que 1, y acá vale 0,0573, de modo que ni los creadores más alejados del centro llevan a `w` a divergir (Pitfall 8 de la investigación, y el binario se niega a correr con un producto de 1 o más). Se corren 10 seeds (1 a 10); la seed 1 es la de las figuras y la de las tablas.

**Signo (D-02).** `w` está definido salvo por el signo: `-w` es igual de buena como solución. La convención de D-02 la fija en C, para que la corrida sea reproducible: el coeficiente de mayor valor absoluto (el pivote) queda positivo, la misma regla con la que la Fase 1 orienta los componentes (sección 5 de `deliverables/01-datos-pca.md`). En las 10 seeds, `seeds.csv` marca `sign_flipped = 1`: el vector entrenado salió del lado opuesto al pivote positivo y C lo dio vuelta. No se verificó la causa; una lectura plausible es que el arranque, con todas las componentes positivas, queda más cerca del lado de las variables de tamaño, que en PC1 son negativas. Python nunca reorienta una corrida: la compara tal como la escribió C.

**Convergencia.** Estas son las líneas del informe de convergencia (`report_convergence.md`), con la seed 1 salvo donde se indica:

- Parámetros: η0 = 0,001, ηf = 0,0001, 500 épocas (25000 actualizaciones: 500 × 50 creadores).
- Cota de estabilidad: η0 · máx ‖x‖² = 0,0573 (debe ser menor que 1).
- Seed 1 al final del entrenamiento: |w| = 1,00032 antes de renormalizar y ‖Δw‖ = 1,4e-04 en la última época.
- Peor seed (6): 1 − |cos(w, v1)| = 2,5e-07.
- Seed 1: primera época con 1 − |cos(w_e, v1)| < 1e-3: época 8.
- Margen del pivote: los dos mayores coeficientes de PC1 son average_caption_words (+0,2521) y average_impressions (-0,2493), con un margen de 0,00275 en valor absoluto: es el límite de la convención de signo, que con otros datos podría elegir la otra variable e invertir w y el índice.

**Qué muestra la figura.** `analysis/results/oja/convergence.svg` tiene tres paneles sobre el eje de épocas, con la seed 1 en color y las otras 9 en gris. Arriba, 1 − |cos(w_e, v1)| en escala logarítmica, donde `w_e` es el vector sin normalizar al final de la época `e` y `v1` el primer autovector de la PCA: baja de 0,8 en la época 0 a menos de 1e-3 en la época 8 (seed 1), queda en el orden de 1e-4 hasta la época 20 aproximadamente y después sigue bajando, con ruido, a medida que η decrece, hasta 1,7e-7 en la época 500. En el medio, |w| antes de renormalizar: sube hasta 1,004 en las primeras épocas y vuelve hacia 1 hasta 1,0003, y las 10 seeds casi coinciden. Abajo, ‖Δw‖ de cada época, que cae de unos 0,3 a 1,4e-4. Como no hay parada por tolerancia, el entrenamiento no "termina" en un punto: el vector sigue moviéndose a escala de ‖Δw‖ ≈ 1e-4, y la alineación con PC1 que se mide en la sección 2 es la del vector final.

**Qué implica el margen del pivote.** Los coeficientes de la viñeta son los de PC1 (`v1`), no los de `w`, que difieren en la cuarta decimal (sección 3). Los dos más grandes de PC1 difieren en 0,00275 en valor absoluto: con un `w` menos convergido la convención podría tomar `average_impressions` como pivote y dar vuelta todo el índice. Por eso se corren y se verifican las 10 seeds (todas con el mismo pivote, `average_caption_words`, sección 2), y no una sola.

## 2. Índice de Oja frente a la proyección sobre PC1

El índice de Oja de un creador es la proyección de su vector z sobre `w`; el score de PC1 es la proyección sobre `v1`, el primer autovector de la PCA de `make pca`. Si `w` coincide con `v1`, los dos números coinciden creador por creador. La tabla compara las dos cantidades en la seed 1, y las cuatro líneas siguientes resumen las 10 seeds:

| Medida (seed 1) | Valor |
|---|---|
| abs(cos(w, v1)) | 1,000000 |
| cos(w, v1) con la convención de signo | 1,000000 |
| Pearson índice vs score de PC1 | 1,0000 |
| Spearman índice vs score de PC1 | 1,0000 |
| overlap@5 | 5 de 5 |
| overlap@10 | 10 de 10 |
| mayor abs(índice − score PC1) | 2,0e-03 |

- Seeds con abs(cos(w, v1)) > 0,99: 10 de 10.
- Seeds con la orientación de PCA (w · v1 > 0): 10 de 10; pivote de todas: average_caption_words.
- abs(cos) entre pares de seeds: mínimo 0,9999993, media 0,9999998.
- Rango del índice por creador entre seeds: máximo 3,1e-03, media 1,5e-03.

**Cómo leerlo.** abs(cos) mide el ángulo entre las dos direcciones sin mirar el signo; el `cos` con signo, positivo, dice que las dos tienen además la misma orientación. Las dos columnas valen 1,000000 porque la tabla redondea a 6 decimales: el valor es 0,9999998 (la peor seed, la 6, queda a 2,5e-07 de 1, sección 1). El Pearson y el Spearman entre el índice y el score de PC1 miden si los dos ordenan a los creadores igual, y valen 1,0000 con 4 decimales; que el overlap@5 y el overlap@10 sean completos (5 de 5 y 10 de 10) dice que los mismos 5 y los mismos 10 creadores encabezan las dos listas. La mayor diferencia entre el índice y el score de un mismo creador es 2,0e-03, contra scores que van de unos -6 a unos +7. En conjunto: Oja aprendió PC1, y el índice y el score ordenan a los creadores del mismo modo, salvo por el error de convergencia; el índice no agrega información que PC1 no tenga.

**Entre seeds.** Las 10 seeds terminan con abs(cos) mayor que 0,99 respecto de PC1, la orientación de PCA y el mismo pivote, y entre sí con abs(cos) de al menos 0,9999993. El índice de un creador cambia entre seeds en 3,1e-03 como máximo, un orden parecido a la diferencia con PC1 (2,0e-03), de modo que elegir otra seed no cambia la lectura del índice.

**Figura.** `analysis/results/oja/oja_vs_pc1.svg` grafica el score de PC1 (eje x) contra el índice de Oja de la seed 1 (eje y), un punto por creador, con la recta identidad y los estadísticos de la tabla. Los 50 puntos caen sobre la recta, y el color, que marca el tema dominante, no los separa: el índice es una proyección de las 26 variables y no sabe a qué tema pertenece el creador, que es lo que se retoma en la sección 3.

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

## 5. Recomendación por campaña y comparación con elegir solo por followers

Las listas de esta sección salen de la regla de la sección 4 aplicada tal como se commiteó, con `analysis/campaigns.py` (`make campaigns`). El programa llama primero a `rule_identity` y se niega a correr, sin escribir nada, si el texto entre los marcadores o `analysis/campaigns_select.py` cambiaron desde el commit de la regla; la identidad que usó quedó en `analysis/results/campaigns/selection_identity.json` y es la que repite la primera línea de `report_campaigns.md`:

- Commit de la regla: a6212e89cdc6 (sha256 del texto entre marcadores: 90113af5bf39)

Cada lista se informa como salió: después de ver los resultados no se tocó ningún filtro, criterio, ponderación ni desempate. Las listas, las tablas y las medias de abajo son las líneas de `analysis/results/campaigns/report_campaigns.md` y `analysis/results/campaigns/report_reading.md`, pegadas sin cambios; la prosa que las rodea las lee. En cada tabla, `overlap@5` cuenta los creadores que la lista comparte con la línea base, la proporción es la parte de la lista cuyo tema dominante es el de la campaña, y el costo por mil es el costo total sobre el alcance argentino total por mil (un cociente de sumas, no un promedio de costos por creador). Son 50 creadores y un solo corte de datos: las diferencias entre listas se describen, no se prueban estadísticamente.

### 5.1 Fútbol: alcance masivo, descubrimiento o profundidad educativa

El filtro de fútbol deja a 15 de los 50 creadores, así que las tres listas propias y las dos líneas base tienen 5 creadores. Las tres listas propias usan el mismo filtro y cambian solo el criterio; las dos líneas base por followers son las mismas para los tres objetivos.

- fútbol / alcance — propia: @golconmate, @tribunacreativa, @futbolcononda, @lookdecancha, @futbolsinvueltas
- fútbol / alcance — followers global: @mateconideas, @golconmate, @brillourbano, @maquillajereal, @crearenreels
- fútbol / alcance — followers en el tema: @golconmate, @futbolsinvueltas, @tribunacreativa, @vidaperruna, @tacticavisual
- fútbol / descubrimiento — propia: @tribunacreativa, @lookdecancha, @makeupconsejos, @futbolcononda, @vidaperruna
- fútbol / descubrimiento — followers global: @mateconideas, @golconmate, @brillourbano, @maquillajereal, @crearenreels
- fútbol / descubrimiento — followers en el tema: @golconmate, @futbolsinvueltas, @tribunacreativa, @vidaperruna, @tacticavisual
- fútbol / profundidad — propia: @futbolentrepases, @pasiondepotrero, @reelconideas, @pasionalbirroja, @canchaaldia
- fútbol / profundidad — followers global: @mateconideas, @golconmate, @brillourbano, @maquillajereal, @crearenreels
- fútbol / profundidad — followers en el tema: @golconmate, @futbolsinvueltas, @tribunacreativa, @vidaperruna, @tacticavisual

Los tres objetivos eligen casi a gente distinta: alcance y descubrimiento comparten 3 creadores (@tribunacreativa, @lookdecancha y @futbolcononda), profundidad no comparte ninguno con las otras dos y en total son 12 creadores distintos.

| Campaña / objetivo | Lista | n | overlap@5 con followers global | overlap@5 con followers en el tema | Proporción con el tema como dominante | Media del share del tema (%) | Alcance argentino total | Costo total (USD) | USD por mil argentinos | Criterio (media de la lista) |
|---|---|---|---|---|---|---|---|---|---|---|
| fútbol / alcance | propia | 5 | 1 | 3 | 100,0 % | 69,9 | 545192 | 14714 | 26,99 | 109038,400 |
| fútbol / alcance | followers global | 5 | 5 | 1 | 20,0 % | 26,9 | 881361 | 22657 | 25,71 | 176272,200 |
| fútbol / alcance | followers en el tema | 5 | 1 | 5 | 100,0 % | 71,5 | 471762 | 19348 | 41,01 | 94352,400 |
| fútbol / descubrimiento | propia | 5 | 0 | 2 | 100,0 % | 66,5 | 349509 | 14803 | 42,35 | 79,658 |
| fútbol / descubrimiento | followers global | 5 | 5 | 1 | 20,0 % | 26,9 | 881361 | 22657 | 25,71 | 66,820 |
| fútbol / descubrimiento | followers en el tema | 5 | 1 | 5 | 100,0 % | 71,5 | 471762 | 19348 | 41,01 | 72,422 |
| fútbol / profundidad | propia | 5 | 0 | 0 | 100,0 % | 51,2 | 28873 | 1367 | 47,35 | 0,883 |
| fútbol / profundidad | followers global | 5 | 5 | 1 | 20,0 % | 26,9 | 881361 | 22657 | 25,71 | -1,108 |
| fútbol / profundidad | followers en el tema | 5 | 1 | 5 | 100,0 % | 71,5 | 471762 | 19348 | 41,01 | -1,063 |

Las medias de las variables crudas que usa cada criterio, en las unidades originales:

- fútbol / alcance — propia, medias del criterio: estimated_argentina_reach 109038,400
- fútbol / alcance — followers global, medias del criterio: estimated_argentina_reach 176272,200
- fútbol / alcance — followers en el tema, medias del criterio: estimated_argentina_reach 94352,400
- fútbol / descubrimiento — propia, medias del criterio: non_follower_reach_pct 79,658; trend_posts_pct 53,400
- fútbol / descubrimiento — followers global, medias del criterio: non_follower_reach_pct 66,820; trend_posts_pct 54,070
- fútbol / descubrimiento — followers en el tema, medias del criterio: non_follower_reach_pct 72,422; trend_posts_pct 54,836
- fútbol / profundidad — propia, medias del criterio: content_tutorial_pct 40,764; saves_per_1000 19,306; average_watch_time_seconds 31,120
- fútbol / profundidad — followers global, medias del criterio: content_tutorial_pct 13,482; saves_per_1000 6,510; average_watch_time_seconds 13,856
- fútbol / profundidad — followers en el tema, medias del criterio: content_tutorial_pct 8,080; saves_per_1000 8,656; average_watch_time_seconds 14,158

**Alcance masivo.** La lista propia suma 545192 argentinos alcanzados por USD 14714 (USD 26,99 por mil) y es, por construcción, la de los cinco creadores de fútbol con más alcance argentino. Contra la línea base dentro del tema comparte 3 de 5 y le gana en alcance (545192 frente a 471762) y en costo por mil (USD 26,99 frente a USD 41,01). Contra la línea base global comparte 1 de 5 (@golconmate): esa lista alcanza más (881361) y cuesta menos por mil (USD 25,71), pero solo 1 de sus 5 creadores tiene fútbol como tema dominante (20,0 %); los otros 4 son de otros temas.

**Descubrimiento.** La lista propia tiene una media de 79,658 de alcance de no seguidores (`non_follower_reach_pct`), contra 66,820 de la línea base global y 72,422 de la línea base dentro del tema; alcanza 349509 argentinos por USD 14803 (USD 42,35 por mil), más caro por mil que las dos líneas base. La señal de apoyo `trend_posts_pct` no es más alta en la lista propia (53,400 frente a 54,070 y 54,836): la regla solo la usa como segunda clave de un empate exacto, así que no era de esperar. Dos de los cinco creadores de esta lista, @makeupconsejos y @vidaperruna, tienen fútbol como tema dominante por sus porcentajes crudos (59,1 % y 69,5 % en `datos/creadores.csv`) aunque el nombre del perfil sugiera otro tema. La regla usa el porcentaje y no el nombre, y la lista se informa como salió; conviene que una persona mire el contenido de esos dos perfiles antes de contactarlos.

**Profundidad educativa.** La lista propia tiene una media de 40,764 de contenido tutorial (`content_tutorial_pct`), 19,306 guardados por mil y 31,120 segundos de visualización media, contra 13,482, 6,510 y 13,856 de la línea base global, y 8,080, 8,656 y 14,158 de la línea base dentro del tema; no comparte ningún creador con ninguna de las dos. El costo es alcance: son creadores chicos (entre 15556 y 60817 followers) que suman 28873 argentinos alcanzados por USD 1367, con USD 47,35 por mil, el costo por mil más alto de las tres listas de fútbol.

**Recomendación.** Para una marca de ropa de entrenamiento de fútbol se recomienda empezar por la lista de profundidad educativa, dejar la de descubrimiento como segunda opción y considerar la de alcance masivo la menos conveniente de las tres. Es un juicio y no un resultado de la regla, que no elige el objetivo, y se apoya en tres cosas de las tablas. Primero, es el objetivo en el que elegir por criterio y elegir por followers dan listas más distintas: la lista de profundidad no comparte ningún creador con ninguna línea base y su contenido tutorial medio es 40,764 contra 8,080 de los más seguidos del tema, mientras que la lista de alcance comparte 3 de 5 con esa línea base y agrega poco sobre elegir por followers dentro del tema. Segundo, bajo el supuesto (1) de abajo, la ropa de entrenamiento es un producto que se elige viéndolo en uso, y los tutoriales, los guardados y el tiempo de visualización son el tipo de contenido donde eso ocurre. Tercero, es la lista más barata en total (USD 1367 contra USD 14714 y USD 14803). Su límite es el volumen: 28873 argentinos alcanzados en total, que no alcanzan si lo que se necesita es llegar a mucha gente.

**Supuestos.** (1) La marca vende ropa de entrenamiento y no ropa deportiva de consumo masivo: una compra que se piensa, en un público que entrena y para el que ver la prenda en uso importa. (2) El público que interesa es el argentino y la marca todavía no lo tiene saturado; si fuera una marca nueva que necesita darse a conocer, el objetivo a elegir pasa a ser descubrimiento. (3) El enunciado no da presupuesto, por eso el precio informa y no filtra (D-12); con un presupuesto grande y la prioridad en el volumen, el objetivo sería alcance masivo. (4) Las variables son indicadores indirectos: `content_tutorial_pct`, `saves_per_1000` y `average_watch_time_seconds` miden cuánto contenido didáctico publica el creador y cuánto lo guarda y lo mira su audiencia, no cuánto compra esa audiencia; `non_follower_reach_pct` mide qué parte del alcance viene de gente que no sigue al creador, no si esa gente es público de la marca. (5) Si cambia cualquiera de estos supuestos puede cambiar el objetivo recomendado; la regla no lo decide por nadie.

### 5.2 Perros (refugios)

Supuesto del cliente (D-11): refugios de animales, con poco presupuesto y alcance local; el criterio es el costo por mil argentinos alcanzados, de menor a mayor. El filtro de perros deja 13 creadores.

- perros / costo_por_mil — propia: @crearenreels, @huellasyconsejos, @consejoscaninos, @huellasargentinas, @guiadehuellas
- perros / costo_por_mil — followers global: @mateconideas, @golconmate, @brillourbano, @maquillajereal, @crearenreels
- perros / costo_por_mil — followers en el tema: @crearenreels, @patitasenred, @patitascontentas, @estiloydetalle, @huellasargentinas

| Campaña / objetivo | Lista | n | overlap@5 con followers global | overlap@5 con followers en el tema | Proporción con el tema como dominante | Media del share del tema (%) | Alcance argentino total | Costo total (USD) | USD por mil argentinos | Criterio (media de la lista) |
|---|---|---|---|---|---|---|---|---|---|---|
| perros / costo_por_mil | propia | 5 | 1 | 2 | 100,0 % | 71,0 | 264906 | 4752 | 17,94 | 25,511 |
| perros / costo_por_mil | followers global | 5 | 5 | 1 | 20,0 % | 21,3 | 881361 | 22657 | 25,71 | 34,191 |
| perros / costo_por_mil | followers en el tema | 5 | 1 | 5 | 100,0 % | 68,1 | 339675 | 7812 | 23,00 | 39,281 |

- perros / costo_por_mil — propia, medias del criterio: price_usd 950,340; estimated_argentina_reach 52981,200
- perros / costo_por_mil — followers global, medias del criterio: price_usd 4531,424; estimated_argentina_reach 176272,200
- perros / costo_por_mil — followers en el tema, medias del criterio: price_usd 1562,314; estimated_argentina_reach 67935,000

La lista propia suma USD 4752 para 264906 argentinos alcanzados (USD 17,94 por mil). Es la única de las seis listas propias que sale más barata por mil que la línea base global (USD 25,71), y también más barata que la línea base dentro del tema (USD 23,00, con USD 7812 para 339675 argentinos). Comparte 2 de 5 con la línea base dentro del tema (@crearenreels y @huellasargentinas) y 1 de 5 con la global (@crearenreels), y los cinco tienen perros como tema dominante (100,0 %, contra 20,0 % de la global). La lista es desigual: @crearenreels, primero con USD 16,31 por mil, tiene 551553 followers y aporta USD 3814 de los USD 4752 y 233828 de los 264906 argentinos; los otros cuatro suman USD 938 y 31078 argentinos, y son perfiles de entre 9604 y 64874 followers.

**Recomendación.** Con refugios de poco presupuesto, la lista propia de perros, y dentro de ella los cuatro creadores chicos como núcleo: @crearenreels es una decisión aparte, porque absorbe cerca del 80 % del costo de la lista aunque dé el menor costo por mil. El enunciado no dice cuánto dispone cada refugio, y los datos tienen alcance argentino pero no por ciudad, así que lo "local" queda como supuesto y no como algo medido.

### 5.3 Maquillaje (marca de belleza)

Supuesto del cliente (D-11): una marca de belleza que busca profundidad (guardados, tutoriales, tiempo de visualización). El filtro de maquillaje deja 11 creadores.

- maquillaje / profundidad — propia: @reelargentino, @brochasymates, @cosmeticaconsciente, @brochasycolor, @tallerurbano
- maquillaje / profundidad — followers global: @mateconideas, @golconmate, @brillourbano, @maquillajereal, @crearenreels
- maquillaje / profundidad — followers en el tema: @mateconideas, @brillourbano, @maquillajereal, @brilloytendencia, @tallerurbano

| Campaña / objetivo | Lista | n | overlap@5 con followers global | overlap@5 con followers en el tema | Proporción con el tema como dominante | Media del share del tema (%) | Alcance argentino total | Costo total (USD) | USD por mil argentinos | Criterio (media de la lista) |
|---|---|---|---|---|---|---|---|---|---|---|
| maquillaje / profundidad | propia | 5 | 0 | 1 | 100,0 % | 61,6 | 108520 | 3696 | 34,06 | 0,379 |
| maquillaje / profundidad | followers global | 5 | 5 | 3 | 60,0 % | 42,9 | 881361 | 22657 | 25,71 | -1,108 |
| maquillaje / profundidad | followers en el tema | 5 | 3 | 5 | 100,0 % | 65,1 | 495545 | 18112 | 36,55 | -0,795 |

- maquillaje / profundidad — propia, medias del criterio: content_tutorial_pct 38,224; saves_per_1000 14,270; average_watch_time_seconds 27,454
- maquillaje / profundidad — followers global, medias del criterio: content_tutorial_pct 13,482; saves_per_1000 6,510; average_watch_time_seconds 13,856
- maquillaje / profundidad — followers en el tema, medias del criterio: content_tutorial_pct 8,036; saves_per_1000 8,350; average_watch_time_seconds 20,838

La lista propia tiene medias de 38,224 de contenido tutorial, 14,270 guardados por mil y 27,454 segundos de visualización, contra 13,482, 6,510 y 13,856 de la línea base global y 8,036, 8,350 y 20,838 de la línea base dentro del tema. No comparte ningún creador con la global y comparte 1 de 5 con la de dentro del tema (@tallerurbano). Aquí la línea base global ya cae sobre todo en el tema (60,0 % de maquillaje), así que la diferencia que aporta el filtro es menor que en fútbol o en arte. El costo de la profundidad es alcance: la lista propia llega a 108520 argentinos por USD 3696 (USD 34,06 por mil) y los más seguidos del tema llegan a 495545 por USD 18112 (USD 36,55 por mil); la propia cuesta algo más de una quinta parte y alcanza algo más de una quinta parte, con un costo por mil parecido.

**Recomendación.** Para una marca de belleza que busca que la audiencia guarde, mire y aprenda del contenido, la lista propia de maquillaje. Si la marca necesitara sobre todo volumen, los más seguidos del tema son una alternativa legítima: el costo por mil es parecido y el alcance es algo más de cuatro veces y media mayor, a cambio de contenido menos didáctico (8,036 de tutorial medio contra 38,224).

### 5.4 Arte (materiales de arte)

Supuesto del cliente (D-11): materiales de arte, un nicho que busca engagement por mil y profundidad; el puntaje es mitad engagement y mitad profundidad (sección 4). El filtro de arte deja 11 creadores.

- arte / engagement_profundidad — propia: @galeriacotidiana, @trazosyreels, @entrelienzos, @colorenmovimiento, @creatividadaldia
- arte / engagement_profundidad — followers global: @mateconideas, @golconmate, @brillourbano, @maquillajereal, @crearenreels
- arte / engagement_profundidad — followers en el tema: @galeriacotidiana, @pincelcotidiano, @artequeinspira, @entrelienzos, @artealpaso

| Campaña / objetivo | Lista | n | overlap@5 con followers global | overlap@5 con followers en el tema | Proporción con el tema como dominante | Media del share del tema (%) | Alcance argentino total | Costo total (USD) | USD por mil argentinos | Criterio (media de la lista) |
|---|---|---|---|---|---|---|---|---|---|---|
| arte / engagement_profundidad | propia | 5 | 0 | 2 | 100,0 % | 60,9 | 237482 | 8761 | 36,89 | 0,420 |
| arte / engagement_profundidad | followers global | 5 | 5 | 0 | 0,0 % | 8,8 | 881361 | 22657 | 25,71 | -0,667 |
| arte / engagement_profundidad | followers en el tema | 5 | 0 | 5 | 100,0 % | 63,2 | 323086 | 12565 | 38,89 | 0,082 |

- arte / engagement_profundidad — propia, medias del criterio: total_engagement_per_1000 75,286; content_tutorial_pct 25,084; saves_per_1000 12,870; average_watch_time_seconds 25,230
- arte / engagement_profundidad — followers global, medias del criterio: total_engagement_per_1000 66,430; content_tutorial_pct 13,482; saves_per_1000 6,510; average_watch_time_seconds 13,856
- arte / engagement_profundidad — followers en el tema, medias del criterio: total_engagement_per_1000 73,458; content_tutorial_pct 20,268; saves_per_1000 9,686; average_watch_time_seconds 21,214

La lista propia tiene 75,286 de engagement por mil, contra 73,458 de la línea base dentro del tema y 66,430 de la global, y 25,084, 12,870 y 25,230 en tutorial, guardados y visualización, contra 20,268, 9,686 y 21,214 de la de dentro del tema. Comparte 0 de 5 con la global y 2 de 5 con la de dentro del tema (@galeriacotidiana y @entrelienzos). Gran parte de la diferencia contra la global viene del filtro de tema (la global tiene 0 de 5 con arte como tema dominante y 8,8 de porcentaje medio de arte); contra la de dentro del tema el criterio compuesto agrega poco en engagement y algo más en profundidad. Cuesta USD 8761 por 237482 argentinos (USD 36,89 por mil), contra USD 12565 por 323086 (USD 38,89 por mil). Como el precio no filtra (D-12), la lista incluye a @entrelienzos y a @creatividadaldia, que salen a USD 109,35 y USD 127,75 por mil argentinos (cálculo por creador en `analysis/results/campaigns/shortlists.csv`).

**Recomendación.** Para materiales de arte, la lista propia de arte, con la reserva de que su ventaja sobre los más seguidos del arte es chica en engagement. Quien quiera acotar el gasto puede mirar el costo por mil de cada creador en `shortlists.csv` antes de contratar a los dos más caros por mil; esa decisión no la toma la regla.

### 5.5 Comparación con la estrategia solo por followers

Las dos líneas base usan k = 5 igual que las listas propias (D-16): la global es la estrategia ingenua del enunciado, los 5 creadores con más followers de los 50, y la de dentro del tema reparte el mismo criterio de followers pero solo entre los creadores del tema de la campaña, de modo que aísla el efecto del criterio de ranking del efecto del filtro de tema.

- **overlap@5.** Con la línea base global, las listas propias comparten a lo sumo 1 creador de 5: 1 en fútbol/alcance y en perros, y 0 en las otras cuatro. Con la línea base dentro del tema comparten entre 0 y 3: 3 en fútbol/alcance, 2 en fútbol/descubrimiento, 0 en fútbol/profundidad, 2 en perros, 1 en maquillaje y 2 en arte. El criterio propio cambia la lista, pero en los objetivos de volumen (alcance) se parece bastante a ordenar por followers dentro del tema.
- **Proporción con el tema de la campaña.** Las seis listas propias tienen 100,0 % de creadores con el tema dominante de la campaña. La línea base global tiene 20,0 % en fútbol y en perros, 60,0 % en maquillaje y 0,0 % en arte: son los mismos cinco creadores para las cuatro campañas, y por eso casi no tocan el tema. La línea base dentro del tema tiene 100,0 % por construcción, así que contra ella el tema no distingue.
- **Costo por mil argentinos.** La línea base global es la más barata por mil en cinco de las seis comparaciones (USD 25,71); solo en perros la lista propia la supera (USD 17,94). Contra la línea base dentro del tema, la lista propia es más barata en cuatro (alcance, perros, maquillaje y arte) y más cara en dos (descubrimiento, USD 42,35 contra 41,01, y profundidad, USD 47,35 contra 41,01).
- **Métrica objetivo.** En cada objetivo la lista propia supera a las dos líneas base en la media de su criterio (en perros, con el valor más bajo, porque el costo por mil se ordena de menor a mayor), salvo alcance masivo contra la línea base global, que alcanza más porque sus cinco creadores son los más grandes de los 50 (media de alcance argentino de 176272 contra 109038).

**Ventajas de elegir solo por followers.** Es simple (ordenar una columna), se supone estable de un mes al otro porque el número de seguidores cambia despacio (los datos son de un solo corte y esto no se puede comprobar con ellos), no hay un modelo que mantener ni una regla que recalibrar, y está correlacionado con el alcance: la línea base global tiene el mayor alcance argentino total de la tabla (881361) y, frente a las listas propias, el menor costo por mil en cinco de las seis. La evidencia de la sección 3 muestra cuánto ya recoge `followers`: el índice de Oja, que es la proyección sobre PC1, la dirección de mayor varianza de las 26 variables (sección 2), se ordena casi como el tamaño (Spearman de -0,921 con `followers` con el signo de D-02).

**Desventajas.** La línea base global es la misma para las cuatro campañas e ignora el tema (20,0 %, 20,0 %, 60,0 % y 0,0 % de la lista con el tema de la campaña), e ignora el objetivo: en profundidad su contenido tutorial medio es 13,482 contra 40,764 de la lista propia de fútbol, en descubrimiento su alcance de no seguidores medio es 66,820 contra 79,658, y concentra el presupuesto en los creadores más grandes (USD 22657 por los cinco contra USD 1367 a USD 14803 de las listas propias de fútbol). Dentro del tema, elegir por followers es una línea base razonable si lo que se busca es volumen (en alcance, y en maquillaje por el alcance que consigue), pero queda lejos en profundidad (8,080 de tutorial medio en fútbol contra 40,764) y no mira el costo por mil.

Sin datos de resultado (ventas, adopciones o conversiones) no se puede afirmar nada sobre el retorno de la inversión de ninguna de las dos estrategias. Lo que esta sección compara son las variables que sí están en los datos (tema, alcance argentino, costo por mil, engagement, profundidad y alcance de no seguidores) y que cada lista cumple de manera distinta; que esas diferencias tengan efecto en el negocio de un cliente es algo que estos datos no pueden decir.

### 5.6 Lectura con Kohonen, Oja y PCA

Kohonen, Oja y PCA no eligieron a nadie: describen dónde cae cada lista, y la selección es la de la sección 4. En ninguna de las 18 listas hubo un empate exacto en el criterio ni en `followers`, así que ni siquiera el desempate por índice de Oja (D-13) decidió quién entra. Cada bullet de abajo es una lista propia (seis) o la línea base global de una campaña (cuatro; es la misma lista de cinco creadores en las cuatro).

- fútbol / alcance: 0 de 5 en el top 5 del índice de Oja; rangos del índice (1 = máximo): 47, 43, 27, 37, 50; PC1 media -4,00; PC2 media 0,37; neuronas (fila, col): (4, 4), (4, 3), (2, 2), (3, 2), (4, 3)
- fútbol / descubrimiento: 0 de 5 en el top 5 del índice de Oja; rangos del índice (1 = máximo): 43, 37, 42, 27, 41; PC1 media -3,12; PC2 media -0,73; neuronas (fila, col): (4, 3), (3, 2), (4, 2), (2, 2), (4, 2)
- fútbol / profundidad: 0 de 5 en el top 5 del índice de Oja; rangos del índice (1 = máximo): 11, 8, 16, 7, 20; PC1 media 3,25; PC2 media -1,24; neuronas (fila, col): (1, 1), (1, 1), (2, 0), (1, 1), (2, 1)
- perros / costo_por_mil: 2 de 5 en el top 5 del índice de Oja; rangos del índice (1 = máximo): 48, 3, 2, 23, 9; PC1 media 2,19; PC2 media 2,27; neuronas (fila, col): (4, 4), (0, 0), (0, 0), (1, 3), (0, 1)
- maquillaje / profundidad: 0 de 5 en el top 5 del índice de Oja; rangos del índice (1 = máximo): 6, 25, 24, 12, 35; PC1 media 1,14; PC2 media -0,10; neuronas (fila, col): (1, 0), (0, 4), (0, 4), (2, 0), (1, 3)
- arte / engagement_profundidad: 0 de 5 en el top 5 del índice de Oja; rangos del índice (1 = máximo): 49, 15, 31, 21, 19; PC1 media -0,36; PC2 media -0,68; neuronas (fila, col): (4, 4), (0, 2), (4, 1), (0, 4), (3, 0)
- fútbol, línea base followers global: 0 de 5 en el top 5 del índice de Oja; rangos del índice (1 = máximo): 46, 47, 45, 44, 48; PC1 media -5,69; PC2 media 2,27; neuronas (fila, col): (3, 4), (4, 4), (3, 4), (3, 4), (4, 4)
- perros, línea base followers global: 0 de 5 en el top 5 del índice de Oja; rangos del índice (1 = máximo): 46, 47, 45, 44, 48; PC1 media -5,69; PC2 media 2,27; neuronas (fila, col): (3, 4), (4, 4), (3, 4), (3, 4), (4, 4)
- maquillaje, línea base followers global: 0 de 5 en el top 5 del índice de Oja; rangos del índice (1 = máximo): 46, 47, 45, 44, 48; PC1 media -5,69; PC2 media 2,27; neuronas (fila, col): (3, 4), (4, 4), (3, 4), (3, 4), (4, 4)
- arte, línea base followers global: 0 de 5 en el top 5 del índice de Oja; rangos del índice (1 = máximo): 46, 47, 45, 44, 48; PC1 media -5,69; PC2 media 2,27; neuronas (fila, col): (3, 4), (4, 4), (3, 4), (3, 4), (4, 4)

Lo que muestran las tres lecturas:

- **Mapa SOM.** La Fase 2 dio una sola región (R1 = 50), así que las neuronas se leen como posiciones sobre un continuo y no como segmentos (D-14). Según la lectura de `deliverables/02-kohonen.md` (6.3), la zona inferior derecha del mapa reúne creadores grandes y caros y la superior izquierda creadores chicos y baratos, y la línea base global cae en (3, 4) y (4, 4), en la primera. La lista de profundidad de fútbol cae en (1, 1), (2, 0) y (2, 1), y las dos primeras están entre las neuronas de creadores chicos y baratos; la de perros pone dos creadores en (0, 0), donde 6.3 ubica creadores chicos y baratos de perros, y a @crearenreels en (4, 4). Las listas de alcance y descubrimiento de fútbol quedan sobre todo en las filas 2 a 4, la de maquillaje en las filas 0 a 2 y la de arte aparece en esquinas opuestas, de (0, 2) a (4, 4). La orientación del mapa es arbitraria; la figura es `analysis/results/campaigns/shortlists_som.svg`.
- **Índice de Oja.** Solo la lista de perros tiene creadores en el top 5 del índice (2 de 5, rangos 2 y 3); las otras cinco listas propias tienen 0 de 5, y la línea base global ocupa los puestos 44 a 48 (el índice con el signo de D-02 ordena a los grandes al final, sección 3). Es lo que se quería mostrar (D-15): elegir por el índice no daría ninguna de estas listas, y coincide con el "No" de la sección 3.
- **PC1 y PC2.** La línea base global y las listas de alcance y descubrimiento de fútbol caen en el lado negativo de PC1 (medias de -5,69, -4,00 y -3,12), el lado de los creadores grandes de la figura, y la lista de profundidad de fútbol (3,25), la de perros (2,19) y la de maquillaje (1,14) en el positivo; la de arte queda cerca del origen (-0,36). En PC2, la lista de perros y la línea base global tienen medias altas (2,27 las dos) y las demás quedan entre -1,24 y 0,37. Son lecturas de posición en un plano que explica 53,2 % y 8,5 % de la varianza, no una razón para estar en la lista; la figura es `analysis/results/campaigns/shortlists_biplot.svg`.

## 6. Mantenimiento del sistema

Cuatro preguntas del enunciado (qué pasa con una campaña nueva, con creadores nuevos, con variables nuevas y en la actualización mensual) tienen una respuesta concreta cada una; la última se acompaña de una demo chica con un creador sintético.

**Campaña nueva.** No se re-entrena nada. Una campaña nueva es una regla nueva sobre el mismo filtro de tema más un criterio de ranking: se escribe y se commitea antes de calcular su lista, como la sección 4, y se aplica sobre los mismos datos. El SOM, el vector `w` de Oja y la PCA quedan como están; solo se agrega un criterio y, si el tema es uno de los cuatro, un filtro que ya existe.

**Creadores nuevos.** Se estandarizan con el scaler guardado (`datos/prepared/creadores_zscore.meta.json`, con `scripts/map_creator.py`, que no vuelve a leer los datos de entrenamiento), se les asigna la neurona ganadora (BMU) en el mapa guardado y su índice de Oja es `x · w` con el `w` guardado y el signo de D-02. Se re-entrena solo cuando la distancia del creador nuevo a su BMU supera la distribución de las distancias de entrenamiento, es decir, cuando es mayor que la mayor distancia al BMU entre los 50 creadores de entrenamiento: ahí el mapa no representa bien al recién llegado. Mientras no la supere, el mapa y el índice se siguen usando tal cual.

**Variables nuevas.** Cambia la dimensión de la entrada, así que no hay nada que reutilizar del modelo: se rehace la auditoría de la Fase 1 (relaciones exactas y redundancias), se vuelve a estandarizar y se vuelve a entrenar el SOM y Oja desde cero, porque el libro de códigos y `w` tienen una componente por variable; también se rehace la PCA de referencia, de la que depende el signo y la comparación de la sección 2.

**Actualización mensual.** Se fija la seed y se versionan, por mes, el scaler y el libro de códigos junto con el `w` de Oja. Al re-entrenar la orientación del mapa puede cambiar, así que las neuronas y las regiones se rotulan por su contenido (el perfil en unidades originales) y no por su posición, y el `w` de Oja se orienta siempre con la convención de signo de D-02 para que el índice conserve su significado (un índice alto sigue siendo un creador chico). Antes de re-entrenar, el chequeo del mes es el de arriba: la distancia al BMU de los creadores del mes sobre el mapa anterior, contra la distribución de entrenamiento; solo si la supera se re-entrena.

**Demo con un creador sintético.** Para mostrar el mecanismo se arma un creador sintético (`SYN001`, `@sintetico_demo`) con las medianas de las 31 columnas de `datos/creadores.csv`, con las cinco relaciones exactas restauradas; no es un creador real, vive solo en `analysis/results/maintenance/` y nunca entra a `datos/creadores.csv` ni a ninguna lista. `make maintenance` lo mapea con `scripts/map_creator.py` y el scaler guardado, lo ubica en el mapa de la Fase 2 (k = 5, `k5-step`, seed de las figuras), calcula su índice de Oja con el `w` guardado y compara su distancia al BMU con la de los 50 creadores de entrenamiento. Estas son las líneas de `report_demo.md`:

- El creador sintético (SYN001, @sintetico_demo) se arma con las medianas de las 31 columnas de datos/creadores.csv; no es un creador real y no está en ninguna lista.
- Su neurona ganadora en el mapa k5-step (seed 4) es (fila 3, col 1) a distancia 1,329 de su vector.
- Distancias de entrenamiento al BMU: QE media 2,724, máximo 3,651, percentil 95 3,545; el 0,0 % de esas distancias es menor o igual que la del creador sintético.
- Veredicto de deriva: no hace falta re-entrenar (la distancia del creador sintético no supera el máximo de entrenamiento).
- El creador sintético tiene índice de Oja 0,249 con el w guardado y ocuparía el lugar 24 entre los 50 creadores (1 = índice más alto, 51 = más bajo que los 50).

El veredicto significa que, con la regla D-18, este creador, que tiene valores típicos por construcción (las medianas), no obliga a re-entrenar: su distancia al BMU no supera la mayor de entrenamiento. Es una demostración del mecanismo y no una prueba de que los creadores reales de un mes nuevo vayan a pasar el chequeo; un creador con valores lejos de los 50 sí lo dispararía.

## 7. Cómo reproducir

Desde `TP4/`, en un clone nuevo:

```
make venv         # crea .venv e instala analysis/requirements.txt (versiones fijadas); sin uv: python3.12 -m venv .venv,
                  # .venv/bin/pip install -r analysis/requirements.txt y touch .venv/.installed
make prepare      # escribe datos/prepared/: matriz auditada de 26 variables y de 31 columnas con sus .meta.json
make pca          # PCA de la matriz de correlación; escribe analysis/results/pca/ (la lee Oja)
make som-stage1   # 140 corridas del SOM; escribe analysis/results/som/series_som_stage1/ con selection.json
                  # (se niega a correr si la regla de la Fase 2 no está commiteada y sin cambios)
make oja          # Oja en C con 10 seeds, comparación con PC1, convergencia y evidencia del máximo; escribe analysis/results/oja/
make campaigns    # listas por campaña, líneas base por followers, métricas y dos figuras; escribe analysis/results/campaigns/
                  # (se niega a correr si la regla de la sección 4 y analysis/campaigns_select.py no están commiteadas y sin cambios)
make maintenance  # demo del creador sintético y chequeo de deriva; escribe analysis/results/maintenance/
make test         # tests de C y de Python (incluye los de Oja, las campañas y la demo)
```

`analysis/results/` no se versiona: cada número y cada figura de este fragmento se regenera con estos comandos, byte a byte para las mismas seeds (salvo `runs.json` y los nombres de las carpetas de cada sweep, que llevan la fecha).
