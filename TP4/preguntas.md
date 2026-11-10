# Preguntas y respuestas del TP4

Resumen corto de lo que se decidió, una entrada por pregunta. El detalle y el porqué están en `DECISIONS.md` y `deliverables/`.

Formato de cada entrada:

**P:** la pregunta
**R:** lo decidido, en pocas líneas

---

## Ej. 1.1 — ¿Qué variables se usaron y cuáles no?

**R:** se usaron **26 de las 31 variables**. Se descartaron 5 porque no aportan información nueva: se calculan exactamente a partir de otras.

**No se usaron (5)**

| Variable | Por qué | Se reconstruye con |
|---|---|---|
| `price_ars` | es lo mismo que `price_usd` en otra moneda | 1500 · `price_usd` |
| `organic_posts_pct` | complemento de los patrocinados | 100 − `sponsored_posts_pct` |
| `total_engagement_per_1000` | es la suma de las cuatro interacciones | likes + comments + saves + shares (por 1000) |
| `topic_art_pct` | los 4 temas suman 100; sale el de menor varianza | 100 − los otros 3 temas |
| `content_showcase_pct` | los 4 tipos de contenido suman 100; sale el de menor varianza | 100 − los otros 3 tipos |

**Sí se usaron (26)**: todas las demás, incluso las muy parecidas entre sí (`average_reach`, `average_impressions`, `average_video_views`, `estimated_argentina_reach`), porque no son duplicados exactos.

**Por qué se descartan solo esas 5**: con duplicados exactos la matriz de correlación queda singular (rango 26 de 31, 5 autovalores nulos) y la PCA, el SOM y Oja trabajarían sobre direcciones sin información. Con las 26 la matriz es regular.

**Cómo se eligió**: con una regla fijada antes de correr la PCA. Se sacan las funciones exactas de otras, y de cada grupo que suma 100 sale la variable de menor varianza.

**Otros detalles**
- Se estandarizan con z-score, sin logaritmo.
- No se reduce a componentes principales: los modelos usan las 26 variables.

Detalle: `deliverables/01-datos-pca.md` §3 y `DECISIONS.md` (F1 D-08 a D-10).

### ¿Qué análisis del EDA justificó sacarlas?

No fue un umbral de correlación sino una **prueba de dependencia lineal exacta**: se buscó qué variables se podían reconstruir a partir de otras y se midió el residuo máximo de cada relación, que dio prácticamente cero (`price_ars = 1500 · price_usd`: 9,3e-10; `organic_posts_pct = 100 − sponsored_posts_pct`: 0; `total_engagement_per_1000` = suma de las cuatro interacciones: 1,4e-14; suma de `topic_*` = 100 y suma de `content_*` = 100: 1,4e-14). La matriz de correlación lo confirma: con las 31 columnas tiene rango 26, o sea 5 autovalores nulos, uno por relación. Por eso la correlación sola no habría servido: en las composiciones las correlaciones son moderadas (entre −0,27 y −0,44 en los temas; −0,84 entre `content_tutorial_pct` y `content_entertainment_pct`) porque es un efecto aritmético de que suman 100, y aun así la dependencia es total. En cambio las variables con correlación alta pero no exacta (`average_reach`, `average_impressions` y `average_video_views` con r ≈ 0,91 con `followers`, y `estimated_argentina_reach`, con error de redondeo hasta 0,499) se dejaron.

## Ej. 1.2 — Kohonen: hiperparámetros y modelo final

### ¿Qué hiperparámetros se modificaron?

Se hizo en dos etapas, con 10 seeds por configuración y la regla de elección escrita y commiteada antes de ver resultados. En la **etapa 1** se varió el **tamaño de la grilla k** (de 2×2 a 8×8) y el **tipo de vecindad** (escalón, que es la del curso, contra gaussiana, que se reporta solo como comparación): 14 configuraciones × 10 seeds = 140 corridas. En la **etapa 2**, ya con la k elegida, se movió **de a un parámetro por vez** respecto del baseline: el **radio inicial R0** (1,25 y 5), la **tasa de aprendizaje inicial η0** (0,1; 0,25 y 0,9) y las **épocas** (50, 130, 520 y 1040). Quedaron fijos el radio final (1), la tasa final (0,01), la distancia euclídea sobre las 26 variables en z-score y la inicialización con creadores al azar. Las métricas fueron el error de cuantización con leave-one-out (QE-LOO), el error topográfico (TE), la fracción de neuronas vacías y los creadores por neurona ocupada.

### ¿Qué modelo final se utilizó?

**Grilla 5×5 con vecindad escalón, R0 = 2,5 (baja hasta 1), η de 0,5 a 0,01 y 260 épocas** (seed 4 para las figuras, la más representativa entre las 10). La regla descartó las grillas con TE > 0,05 (k = 2 y 3), con más de 20 % de neuronas vacías (k = 7 y 8) o con menos de 2 creadores por neurona ocupada (k = 6, 7 y 8). Sobrevivieron k = 4 y k = 5, y ganó k = 5 por menor QE-LOO (3,295 contra 3,422). El QE de entrenamiento solo habría elegido k = 8, porque baja siempre al agrandar la grilla, pero lo hace dejando 48 % de neuronas vacías. Se reporta lo desfavorable: k = 5 pasa el TE por poco (0,046 contra 0,05), la etapa 2 da veredicto **"no robusta"** (en 5 de las 9 variantes el TE queda apenas sobre 0,05, entre 0,052 y 0,060) y el mapa resultante forma **una sola región** con los 50 creadores.

### ¿Por qué son un problema las neuronas vacías si el QE es menor con 8×8?

El QE de entrenamiento mide qué tan cerca queda cada creador de su neurona, y eso baja siempre al agregar neuronas, aunque el mapa no aprenda nada útil. Con 50 creadores y 64 neuronas, cada creador termina casi con su propia neurona (1,51 creadores por neurona ocupada) y el 48 % de las neuronas quedan vacías: el mapa memoriza a los creadores en vez de agruparlos, y se pierde el objetivo del SOM, que es resumir y encontrar grupos. Que el error "mejore" es un efecto de tener más neuronas que datos, no de un mejor modelo. Para verificarlo se usó el QE con leave-one-out (se saca un creador, se entrena y se mide su distancia a la neurona ganadora): ahí la ventaja casi desaparece (3,295 con k = 5 contra 3,213 con k = 8, mientras el QE de entrenamiento pasa de 2,732 a 1,918). Las neuronas vacías además hacen más difícil leer el mapa, porque los saltos entre neuronas vecinas dejan de ser comparables. Por eso la regla pide al menos 2 creadores por neurona ocupada y como máximo 20 % de neuronas vacías, y recién entre las grillas que cumplen eso compara el QE.

## Ej. 1.2 — Matriz U y distribución de los creadores (grilla 5×5, seed 4)

### ¿Cómo se distribuyen los creadores en la grilla?

Los 50 creadores caen en **22 de las 25 neuronas** (3 vacías: (0,3), (1,2) y (3,3)), con 2,27 creadores por neurona ocupada. Hay **7 neuronas con un solo creador**, que se leen como casos aislados y no como grupo, y el máximo es **5 creadores en (0,0)**. El mapa ordena a los creadores por **tamaño y precio**: arriba a la izquierda quedan los chicos y baratos (de 21 612 a 61 015 seguidores; USD 175 a 440) y abajo a la derecha los grandes y caros (hasta 674 103 seguidores y USD 5 197). Los temas aparecen como zonas: perros en (0,0), maquillaje en (2,4) y (3,4), arte en (3,0), (4,0) y (4,1), fútbol en (1,1), (2,2), (4,2) y (4,3). Es esperable, porque los temas son entradas del modelo, así que no confirman nada de forma independiente.

### ¿Qué muestra la matriz U?

La matriz U da, para cada neurona, la **distancia media entre su prototipo y los de sus 4 vecinas** (en unidades z de las 26 variables). Un valor alto es un salto entre prototipos vecinos (posible frontera) y uno bajo es una zona homogénea. Va de 1,59 a 2,97: los valores más bajos están en las esquinas ((4,4) 1,59; (3,4) 1,68; (0,4) 1,72; (0,0) 1,75) y los más altos en la zona central y derecha, con el máximo en (2,4). La arista más larga entre neuronas ocupadas es (1,4)-(2,4), con 3,67. **Cuidado al leerla**: cuatro de las seis aristas más largas tocan una neurona vacía, y ese "muro" es interpolación (el prototipo de una neurona vacía queda entre los de sus vecinos porque ningún creador lo reclama), no un límite entre grupos. Solo los saltos entre neuronas ocupadas, como (1,4)-(2,4), apoyan una frontera real.

### ¿Qué conclusión se saca?

Aplicando la regla fijada de antemano (cortar las aristas por encima del percentil 75, es decir 2,60), las 22 neuronas ocupadas siguen conectadas y el mapa da **una sola región con los 50 creadores**. Se reporta así, sin cambiar el percentil para obtener más regiones. La lectura útil es un **continuo** de chicos y baratos a grandes y caros, y no grupos separados.

### ¿Está bien que dé una sola región? ¿Tiene sentido con lo pedido?

**Es un resultado legítimo pero débil frente a lo que pide el enunciado.** El enunciado pregunta "¿qué perfiles reúne cada región de la grilla?", que da por hecho que hay varias. La regla (cortar las aristas de la matriz U por encima del percentil 75 y tomar las componentes conexas) se fijó antes de ver resultados y dio una sola región. Se mantuvo para no elegir la regla mirando el mapa, y es honesto reportarlo así. Pero tiene dos limitaciones: (1) el percentil 75 es arbitrario, y de las 10 aristas que lo superan, 5 tocan neuronas vacías y no separan nada, así que en la práctica solo hay 5 cortes reales y no alcanzan para partir el mapa; (2) con 50 creadores y una grilla de 5×5, el mapa tiene poca resolución para formar grupos. Como el enunciado igual pide perfiles, se complementó **sin tocar la regla** con **zonas** por neurona (slide `som-zonas`, F6 D-16): tema dominante, mediana de seguidores y de precio por neurona, y el continuo de chicos y baratos a grandes y caros. Para la defensa, la postura es: "la regla conservadora no encontró fronteras fuertes; los datos son un continuo de tamaño, y lo mostramos con zonas, aclarando que no son regiones de la regla".

## ¿Qué son PC1 y PC2?

Son las dos primeras **componentes principales** de la PCA: nuevos ejes que combinan las 26 variables para resumir lo más posible de cómo se diferencian los creadores. **PC1** es la dirección en la que los creadores más varían (53,2 % de la varianza) y **PC2** la segunda, perpendicular a la primera (8,5 %). Juntas retienen 61,7 %, por eso se dibujan los 50 creadores en un plano (el biplot). Cada creador tiene un puntaje en cada eje, y cada variable una carga que dice cuánto pesa en él.

- **PC1 = escala y formato.** De un lado, tamaño, alcance, precio y video corto; del otro, epígrafes largos, tutoriales, guardados y comentarios. Un creador grande y caro queda de un lado y uno chico de epígrafes largos del otro.
- **PC2 = audiencia argentina** (`argentina_audience_pct` +0,73).

El signo de cada eje es una convención: lo que importa es qué variables quedan juntas y cuáles opuestas.

## Ej. 1.2 — ¿Por qué se eligió la grilla 5×5 mirando esas seis métricas?

Porque es la mejor de las que pasan los filtros. La regla, fijada antes de ver resultados, funciona en dos pasos: primero **filtros** (TE, neuronas vacías y creadores por neurona ocupada) y, entre las que sobreviven, **gana el menor QE-LOO**.

| k | TE (máx 0,05) | % vacías (máx 20 %) | creadores/neurona (mín 2) | QE-LOO | ¿Pasa? |
|---|---|---|---|---|---|
| 2 | 0,180 | 0 | 12,50 | 3,944 | no, TE |
| 3 | 0,190 | 0 | 5,56 | 3,638 | no, TE |
| 4 | 0,030 | 1,2 | 3,17 | 3,422 | sí |
| **5** | **0,046** | **15,6** | **2,39** | **3,295** | **sí, gana** |
| 6 | 0,016 | 17,2 | 1,68 | 3,253 | no, creadores |
| 7 | 0,006 | 41,4 | 1,75 | 3,226 | no, vacías y creadores |
| 8 | 0,002 | 48,1 | 1,51 | 3,213 | no, vacías y creadores |

- **Las chicas (2 y 3) fallan por TE:** el mapa es muy chico y no conserva la vecindad (TE de 0,18 y 0,19, contra un máximo de 0,05).
- **Las grandes (6, 7 y 8) fallan por ocupación:** tienen más neuronas que datos y cada creador queda casi con su neurona propia. Su QE de entrenamiento es el más bajo (hasta 1,918), pero solo porque memorizan.
- **Quedan k = 4 y 5.** Entre ellas decide el QE-LOO: 3,295 contra 3,422. La diferencia (0,127) es de más de cinco desvíos entre seeds (0,023), así que no es ruido y no hace falta mirar la estabilidad.
- **El QE de entrenamiento no decide:** baja siempre con k y por sí solo elegiría k = 8.
- **La estabilidad no entra en la decisión** salvo en un desempate que no se activó. La de k = 5 (0,672) es menor que la de k = 4 (0,791) y cae con k en general. Se reporta como limitación.
- **Limitación del TE:** k = 5 pasa por poco (0,046 en promedio y 3 de las 10 seeds por encima de 0,05). Por eso la etapa 2 da "no robusta".

## Ej. 2.2 — Letras: qué son las curvas sep y corr

Son los **dos sets de letras**, con la actualización síncrona de la teórica. En cada uno se toma una letra almacenada, se le invierten k píxeles (de 0 a 12 de 25) y se mide cuántas veces la red vuelve exactamente a la letra original (30 ensayos por letra y nivel, 10 seeds).

- **Set separado (sep): G, R, T, V.** Letras muy distintas entre sí (|d| = 1 entre pares, producto escalar normalizado 0,04), elegidas con una regla fijada antes de correr nada. Es el caso "bueno".
- **Set correlacionado (corr): H, M, N, W.** Letras muy parecidas (d de 17 a 21, producto escalar normalizado 0,68 a 0,84). Es el caso "malo".
- **Actualización:** síncrona, todas las neuronas a la vez (diapositiva 23). Puede caer en ciclos de período 2, que no cuentan como recuperación. Antes usábamos además la asíncrona; la sacamos porque no es la de la teórica, y el cambio está declarado en el informe.

**Qué se toma de eso**
- **sep:** recupera todo hasta k = 3 y cae de forma gradual: con k = 6 recupera 90,4 %, con k = 9 un 33,6 % y con k = 12 casi nada. Con ruido alto muchos ensayos caen en ciclos (27,7 % con k = 9).
- **corr:** nunca pasa de 25 %, ni siquiera sin ruido. Solo la N es punto fijo; H, M y W caen siempre sobre la N. **La ortogonalidad (o su falta) es lo que limita la capacidad**, no el ruido.
- **Criterio de éxito:** solo cuenta el match exacto con la letra original. Que la energía baje o que la red converja no alcanza: otra letra almacenada o un inverso terminan en la misma energía mínima (−264) que la letra.

## Ej. 2.2 — Método, red y actualización síncrona

- **Red:** Hopfield discreta de **25 neuronas** (una por píxel de la letra 5×5), con estados ±1, implementada a mano en C.
- **Método (aprendizaje):** **regla de Hebb**. Los pesos son W = Σ ξ·ξᵀ sobre las 4 letras guardadas, con diagonal en cero y sin dividir por N (quedan enteros exactos).
- **Recuperación:** se parte de una letra con k píxeles invertidos y se deja evolucionar la red hasta que no cambie. La energía es E = −½ sᵀWs.
- **Regla de una neurona:** calcula su campo h = Σ w·s. Pasa a +1 si h > 0, a −1 si h < 0 y mantiene su estado si h = 0.
- **Síncrona (la de la teórica):** actualiza **las 25 neuronas a la vez**: s(t+1) = sign(W·s(t)), usando todos los valores del paso anterior. Se frena si un paso no cambia nada, o si s(t+1) = s(t−1), que es un ciclo de período 2. Ese ciclo no cuenta como convergencia ni como recuperación. El tope es 100 pasos.

## Diapositiva — Arquitectura de la red (Hopfield, letras 5×5)

- **Red:** Hopfield discreta, recurrente y de una sola capa, implementada a mano en C.
- **Neuronas:** 25, una por píxel de la letra 5×5, con estados +1 o −1.
- **Conexiones:** todas con todas, simétricas y sin autoconexión (diagonal en cero).
- **Aprendizaje:** regla de Hebb, W = Σ ξ·ξᵀ sobre las 4 letras guardadas.
- **Actualización:** cada neurona toma el signo de su campo h = Σ w·s y mantiene su estado si h = 0.
- **Dinámica:** síncrona, todas las neuronas a la vez (la de la teórica, diapositiva 23).
- **Energía:** E = −½ sᵀWs. En síncrono la teoría no garantiza que no suba, pero en nuestras corridas no subió nunca; la red converge a un punto fijo o cae en un ciclo de período 2.

## ¿Hebb y pseudo-inversa se vieron en la teórica?

- **Hebb: sí** (`docs/Modelo de Hopfield.pdf`, diapositivas 18 a 30). Los pesos suman el producto de los patrones: w_ij = (1/N) Σ ξ_i ξ_j, con w_ii = 0 y w_ij = w_ji. En forma matricial es W = K·Kᵀ con los patrones en columnas de K. Sube el peso entre dos neuronas cuando ambas están activas o ambas inactivas. En el TP se omite el 1/N para que los pesos sean enteros; no cambia el signo del campo, así que la dinámica es la misma.
- **Pseudo-inversa: no aparece** en esas diapositivas. La teórica solo da Hebb, y de sus limitaciones menciona que los patrones deben ser "más o menos" ortogonales (el crosstalk es cero solo si lo son) y que p ≤ 0,15·N. La pseudo-inversa se agregó en el TP como remedio cuando Hebb falla con patrones correlacionados (los 5 QR).

**Pseudo-inversa, W = Xᵀ(X Xᵀ)⁻¹ X** (X tiene los p patrones en filas):
- Es la proyección sobre el espacio que generan los patrones. Así, cada patrón guardado cumple W·ξ = ξ exactamente, aunque estén correlacionados. Hebb solo lo logra si son ortogonales.
- Requiere invertir la matriz de Gram X Xᵀ (de p × p, 5 × 5 en los QR).
- Se deja la diagonal de W sin anular, a diferencia de Hebb.
- Resultado en los QR: Hebb recupera 0 % incluso sin ruido; la pseudo-inversa recupera 100 % sin ruido y lo sostiene hasta ruido 0,30.

## Guion oral — Slide "Tres modelos: Kohonen agrupa, Oja resume en un eje y Hopfield recupera patrones"

- **Idea general:** usamos tres modelos, cada uno para una tarea distinta, y los tres implementados a mano en C.
- **Kohonen (agrupa):** para cada creador gana la neurona más parecida, y ella y sus vecinas (a distancia ≤ R) se acercan al dato. La tasa η y el radio R van bajando, así que el mapa primero se ordena y después se afina.
- **Oja (resume en un eje):** una sola neurona lineal con la regla w += η·y·(x − y·w). Con los datos estandarizados converge a PC1, o sea un índice que resume al creador en un número.
- **Hopfield (recupera patrones):** guarda los patrones con la regla de Hebb y, ante una consulta con ruido, actualiza una neurona por vez hasta llegar a un punto fijo, que es el patrón recuperado.
- **Cierre:** los dos primeros son aprendizaje no supervisado sobre los creadores (Ejercicio 1) y el tercero es memoria asociativa sobre letras y QR (Ejercicio 2).

## Script hablado — Slide "Elegimos 5×5: con grillas más grandes quedan menos de 2 creadores"

"Para elegir el tamaño del mapa probamos grillas de 2×2 hasta 8×8 y miramos seis métricas. En azul está la vecindad que usamos para decidir y en naranja una variante que solo mostramos de comparación.

El primer gráfico es el error de entrenamiento: baja siempre al agrandar la grilla, así que por sí solo elegiría la más grande. Pero eso engaña, porque con más neuronas que creadores el mapa simplemente memoriza. Por eso miramos el error dejando un creador afuera, que casi deja de mejorar a partir de 5×5.

Después ponemos filtros. Las grillas chicas, de 2 y 3, fallan en el error topográfico: no conservan la vecindad. Las grandes, de 6 en adelante, fallan en ocupación: quedan neuronas vacías y menos de 2 creadores por neurona.

Solo pasan los filtros 4×4 y 5×5, y entre las dos elegimos 5×5 porque tiene el menor error. Como limitación, es un poco menos estable entre seeds y pasa el error topográfico por poco."

## Script hablado — Slide "El mapa coincide con PC1 (R² 0,961, p = 0,001) pero no con PC2 (R² 0,055)"

"Acá comparamos el mapa con la PCA. PC1 y PC2 son los dos ejes principales que resumen las variables: PC1 es el eje en el que más se diferencian los creadores, y mide sobre todo el tamaño, con alcance y precio de un lado y epígrafes largos y tutoriales del otro. PC2 es el segundo eje y tiene que ver con la audiencia argentina.

Mostramos el mismo mapa pintado dos veces. Cada celda es una neurona, y el color es el valor medio de PC1 o de PC2 de esos creadores. Las rayadas son celdas vacías.

A la izquierda, con PC1, el color cambia de forma ordenada de una esquina a la opuesta: los creadores chicos y baratos quedan de un lado y los grandes y caros del otro. A la derecha, con PC2, los colores están mezclados y no siguen ningún orden.

Es decir que el mapa, sin que se lo pidiéramos, aprendió solo el eje más importante, el tamaño, pero no refleja PC2. No es una contradicción: el mapa usa todas las variables y PC1 y PC2 son apenas un resumen."

## Guion oral — Slide "Probamos la red para el caso del abecedario"

- **Objetivo:** probar si una red de Hopfield puede guardar letras y recuperarlas cuando llegan con ruido.
- **Red:** Hopfield, recurrente (la salida vuelve como entrada) y de una sola capa, implementada a mano en C.
- **Neuronas:** 25, una por cada píxel de la letra 5×5, con estado +1 (encendido) o −1 (apagado). Una letra es un vector de 25 valores.
- **Actualización:** cada neurona suma lo que le llega de las demás, h = Σ w·s, y toma el signo. Si h = 0 mantiene su estado. Se repite hasta que nada cambia: ese estado estable es la letra recuperada.
- **Pesos:** vienen de la regla de Hebb sobre las 4 letras guardadas (se explica en la siguiente slide).

## Script hablado — Slide "Solo por followers suele salir más barato por mil, pero ignora tema y objetivo"

d

Elegir por followers tiene ventajas reales: es simple y estable. Pero si la marca busca tema y profundidad, conviene nuestro criterio; si busca costo y alcance, followers alcanza. Además, no afirmamos retorno comercial, porque los datos no tienen ventas."

## Guion oral — Slide "Un lookup de Hamming iguala o supera a la pseudo-inversa con ruido alto"

- **Contexto:** son los 5 QR de 37×37 (1369 neuronas). Se les agrega ruido de 0 a 0,5 (fracción de píxeles invertidos) y se compara cómo los recupera Hebb, la pseudo-inversa (pinv) y una línea base trivial: el lookup de Hamming.
- **Lookup de Hamming:** no es una red. Compara la consulta con los 5 QR guardados y devuelve el de menor distancia de Hamming (el que difiere en menos píxeles). Sin dinámica, sin energía y sin pasos.
- **Panel izquierdo (recuperación exacta):** Hebb queda en 0 % incluso sin ruido, porque los 5 QR están muy correlacionados (producto escalar normalizado medio 0,67). La pseudo-inversa sostiene 100 % hasta ruido 0,30 y cae después. Hamming la sigue de cerca hasta 0,40.
- **Panel central (cercanía continua):** el producto escalar normalizado final con el patrón correcto confirma lo mismo. Hebb se queda siempre en un atractor común (la mayoría píxel a píxel de los 5 QR), con producto escalar normalizado 0,79.
- **Panel derecho (costo):** pinv necesita 1 a 3 pasos y tiene energía propia. Hamming no tiene ninguno de los dos: es un lookup instantáneo.
- **Dato clave:** con ruido alto (0,45), Hamming recupera 81,5 % y pinv 61 %. Con 0,50, Hamming 16,7 % y pinv 0 %.
- **Lectura:** para 5 patrones fijos y conocidos de antemano, una tabla de búsqueda resuelve el problema igual o mejor que una red de 1369² pesos. Ahí la ventaja de Hopfield no está en la tasa de acierto, y por eso es una limitación del caso de uso.
- **Honestidad:** es un resultado desfavorable para la red y lo reportamos como salió. Hebb solo funciona bien si los patrones son casi ortogonales; la pseudo-inversa es el remedio, pero no supera al lookup.

## ¿El lookup de Hamming se explica en la teórica?

**No.** Ni "Hamming" ni "lookup" ni "vecino más cercano" aparecen en ninguno de los PDF de `docs/`, ni en el enunciado. Es una **línea base que agregamos nosotros** (F5 D-08), no algo pedido. Lo que sí dice la teórica de Hopfield (diapositiva 10) es el planteo del problema: "encontrar el patrón almacenado más cercano" a la consulta. El lookup resuelve exactamente eso sin red: calcula la distancia de Hamming (cantidad de píxeles distintos) a cada uno de los 5 QR y devuelve el menor. Se usa para mostrar que, con 5 patrones fijos, la red no aporta ventaja de acierto. Conviene presentarlo así en la defensa: como un control propio, no como un método de la materia.

## Script hablado — Slide "El set separado resiste el ruido; el correlacionado nunca pasa de 25,0 %"

"Acá medimos qué tan bien la red recupera una letra a la que le invertimos algunos píxeles. Probamos dos sets de cuatro letras. El **separado** son letras bien distintas entre sí, G, R, T y V. El **correlacionado** son letras muy parecidas, H, M, N y W. La red se actualiza como en la teórica, con todas las neuronas a la vez.

Eso da dos curvas. **Sep** es el set separado: recupera todo con poco ruido y va cayendo de a poco. Con 3 píxeles invertidos recupera 100 %, con 6 un 90,4 % y con 9 un 33,6 %. **Corr** es el set correlacionado: quedan clavadas en 25 %, aun sin ruido, porque solo la N se mantiene estable y las otras tres letras terminan cayendo sobre ella.

Los gráficos de la derecha muestran en qué se equivoca la red: en el separado, a medida que sube el ruido, termina en otra letra, en su inverso, en una mezcla o en un ciclo de período 2; en el correlacionado, casi siempre en la N.

Conclusión: lo que limita a la red no es solo el ruido, es qué tan parecidas son las letras guardadas."


## Script hablado — Slide "Hiperparámetros del SOM"

"Esta slide resume cómo configuramos la red de Kohonen y por qué elegimos cada valor.

Arrancamos por la **inicialización**. Los pesos de cada neurona los inicializamos con creadores elegidos al azar de los datos de entrenamiento. Así todas las neuronas empiezan ya dentro de la zona donde están los datos.

Después, un **criterio para descartar grillas**. Descartamos las que tienen más de 20 % de neuronas vacías o menos de 2 creadores por neurona ocupada. Con 50 creadores, una grilla muy grande tiene más neuronas que datos. Cada creador queda casi con su propia neurona y el mapa memoriza en vez de agrupar.

Ahora, **el radio y la tasa de aprendizaje**. El radio define hasta dónde llega la influencia de la neurona ganadora, medido sobre la grilla: la ganadora y todas las neuronas a una distancia menor o igual al radio se acercan al creador. Con radio 1 son la ganadora y sus 4 vecinas pegadas. Empieza grande, para que se muevan muchas neuronas juntas y el mapa se ordene en conjunto, y baja hasta 1, donde solo se actualizan las vecinas pegadas y el mapa se afina. La tasa de aprendizaje hace lo mismo: empieza alta y baja hasta 0,01. Los dos decaen de forma exponencial. En la iteración *t*, el radio es R(0) por (1 sobre R(0)) elevado a *t* sobre (T menos 1), donde T es el total de iteraciones. La tasa se actualiza igual.

Y en la tabla están los valores que usamos.

- **k = 5.** No la elegimos a mano. La eligió la regla que fijamos antes de ver los resultados: es la grilla más grande entre las que cumplen la ocupación.
- **Radio inicial 2,5.** Cubre casi la mitad de la grilla de 5×5, y es la mitad de k. Es un baseline que fijamos de antemano, y probamos otros valores sin que la elección cambie.
- **η(0) = 0,5.** Tiene que ser menor que 1. Probamos de 0,1 a 0,9 y la elección tampoco cambia.
- **260 épocas.** También es un baseline fijado de antemano. Probamos entre 50 y 1040 épocas y la ocupación no se degrada.

En resumen, el único hiperparámetro que decide el resultado es el tamaño de la grilla. Los otros tres los movimos de a uno y la elección se sostiene."

**Notas para la defensa**
- Radio final 1 y tasa final 0,01 quedaron fijos en todas las corridas; no se variaron.
- El error topográfico no figura en esta slide. k = 5 lo pasa por poco y la etapa 2 da "no robusta" (en 5 de las 9 variantes el TE queda apenas sobre 0,05): presentarlo como limitación.
- La slide dice "iteración" y no "época". Verificar en `neuron/models/kohonen.c` qué es T exactamente antes de afirmarlo.
- **Qué está en la teórica** (`docs/Kohonen Model.pdf`, diapositivas 24 a 31): inicializar con muestras al azar de los datos (para evitar unidades muertas), R(0) como dato de entrada, η(0) < 1, vecindario = neuronas a distancia menor que R(i) de la ganadora, R(i) → 1 y η(i) → 0, y "R(0) puede ser el tamaño total de la grilla y va decreciendo hasta R = 1, donde solo se actualizan las vecinas pegadas". También define 4-vecinos como R = 1 y 8-vecinos como R = √2.
- **Qué NO está en la teórica (es nuestro):** la forma exponencial de la fórmula del radio y de la tasa (la teórica solo pide que tiendan a 1 y a 0, con η = 1/i como ejemplo), R(0) = k/2, el radio final 1 y la tasa final 0,01 como valores concretos, y la explicación de "ordenar en conjunto primero y afinar después" (es una interpretación nuestra del decrecimiento). Decirlo así si preguntan.
- Diferencia menor con la teórica: la diapositiva 26 escribe el vecindario con "<" y el código usa "≤" (con "<", R = 1 no alcanzaría a las 4 vecinas pegadas).

## Script hablado — Slide "El mapa ordena a los creadores igual que PC1 y, en menor medida, PC2"

"Acá comparamos el mapa de Kohonen con la PCA. PC1 y PC2 son los dos ejes principales que resumen las variables: PC1 es el eje en el que más se diferencian los creadores, con el tamaño, los seguidores y los likes de un lado, y los guardados, comentarios y visitas al perfil del otro. PC2 es el segundo eje y opone, por un lado, publicaciones patrocinadas y fútbol y, por el otro, audiencia argentina y perros.

Mostramos el mismo mapa de 5×5 pintado dos veces con la PCA. Cada celda es una neurona, y el color es el valor medio de PC1 o de PC2 de los creadores que cayeron en ella. Las rayadas son las dos neuronas vacías.

A la izquierda, con PC1, el color cambia de forma ordenada de una esquina a la opuesta: de la esquina inferior izquierda, con los valores más bajos, a la superior derecha, con los más altos. Dicho de otra manera, el mapa tiene un gradiente claro. Lo medimos: la posición de la neurona explica el 94 % de la variación de PC1.

A la derecha, con PC2, también hay un orden, pero más débil: los valores altos se juntan hacia la izquierda y arriba, y los bajos hacia abajo y a la derecha, con más mezcla en el medio. Ahí la posición explica el 44 %.

Es decir que el mapa, sin que se lo pidiéramos, ordenó a los creadores principalmente por PC1, y en parte por PC2. Una aclaración importante: el mapa se entrenó justamente con las componentes principales, así que PC1 y PC2 son dos de sus entradas. Que las siga es esperable, no una validación independiente."

**Notas para la defensa**
- Cifras (`deliverables/02-kohonen.md`, §6.2): R² de PC1 sobre la posición en la grilla 0,938 y de PC2 0,439. Las dos neuronas vacías son (1,3) y (3,3). La media de PC1 por neurona va de −4,40 en (4,0) a 4,06 en (0,4), y la de PC2 de −2,60 en (1,4) a 2,37 en (1,0).
- Honestidad: el SOM se entrena con los scores de PC1 a PC7, sin reescalar. Por eso no es un resultado independiente. Decirlo antes de que lo pregunten.
- No está en la teórica: el R² de la posición contra PC1/PC2, las permutaciones con p-valor (0,001) y la correlación tipo Mantel. Se dejó solo el R² como descripción, sin p; decidir con el usuario si se saca o se defiende.
- El signo de PC1 y PC2 es una convención: lo que importa es qué variables quedan juntas y cuáles opuestas, no cuál extremo es "positivo".
- Una sola región en la matriz U: el mapa es un continuo de tamaño, no grupos separados (ver "¿Está bien que dé una sola región?").

## Script hablado — Slide "Pesos que dejan estable cada QR"

"Esta slide explica cómo calculamos los pesos de la red para los 5 QR. Con Hebb no alcanzaba, y usamos esta fórmula, la pseudo-inversa: W es igual a P transpuesta, por la inversa de P por P transpuesta, por P. P es la matriz con los 5 QR, uno por fila.

¿Qué hace? Hebb suma el producto de cada patrón consigo mismo, y eso solo deja estable a cada patrón si los patrones son casi ortogonales, o sea muy distintos entre sí. Los 5 QR son muy parecidos: comparten los tres cuadrados de las esquinas y el patrón de alineación. Entonces los patrones se interfieren y Hebb no recupera ninguno, ni siquiera sin ruido. La pseudo-inversa descuenta ese parecido: el término del medio, P por P transpuesta, mide cuánto se parecen los QR entre sí, y al invertirlo se lo saca. El resultado es que cada QR guardado cumple W por ξ igual a ξ de forma exacta: queda estable aunque se parezca a los demás.

¿Para qué nos sirve? Para guardar QR muy parecidos sin cambiar la red. La red sigue siendo la misma, con 1369 neuronas y la misma dinámica, y lo único que cambia son los pesos. Con esto, la recuperación pasa de 0 % con Hebb a 100 % sin ruido, y se sostiene hasta un 30 % de píxeles invertidos."

**Notas para la defensa**
- **No se vio en la teórica.** La teórica (`docs/Modelo de Hopfield.pdf`) solo da Hebb. La pseudo-inversa la agregamos nosotros como remedio cuando Hebb falla con patrones correlacionados. Decirlo así, y que es el planteo estándar de proyección sobre el espacio de los patrones. El usuario quiere justificarla bien o sacarla.
- **Por qué funciona:** W es la proyección sobre el espacio que generan los 5 patrones. Cualquier combinación de ellos queda igual y todo lo demás se anula. Por eso W ξ = ξ para cada QR, aunque estén correlacionados.
- **Qué hay que invertir:** la matriz de Gram P Pᵀ, de 5 × 5 (no de 1369 × 1369). Es invertible mientras los 5 QR sean linealmente independientes.
- **Diferencia con Hebb:** la diagonal de W se deja como sale, sin anularla. Hebb sí la anula.
- **Límite honesto:** el lookup de Hamming iguala o supera a la pseudo-inversa con ruido alto (con 0,45 de ruido, 81,5 % contra 61 %). Para 5 patrones fijos y conocidos, una tabla de búsqueda resuelve igual o mejor; es una limitación del caso de uso (ver el guion de esa slide).
- Pendiente sin verificar: la pseudo-inversa con ruido muy alto (más allá de 0,30 de la zona estable).

## Script hablado — Slide "Las grillas con menor error topográfico dejan demasiadas neuronas vacías"

"Esta slide muestra por qué no pudimos elegir la grilla mirando solo el error topográfico.

Primero, qué es. Para cada creador miramos cuáles son su neurona más cercana y su segunda más cercana. Si en la grilla no son vecinas, el mapa rompió la vecindad para ese creador. El error topográfico es la fracción de creadores donde pasa eso, sobre el total. Es una medida de si el mapa conserva la vecindad, que es justo lo que busca Kohonen: que datos parecidos queden en neuronas cercanas. Cuanto más bajo, mejor.

El gráfico muestra el error para grillas de 2×2 a 8×8. Cada barra es la media de 10 entrenamientos con distinta seed, y las líneas negras son el desvío entre seeds. La línea punteada es el límite de 0,05 que habíamos fijado de antemano. Debajo de cada k está el porcentaje de neuronas vacías.

Las barras azules cumplen los límites de ocupación y las grises no. El patrón es claro. Las grillas chicas, de 2 a 5, ocupan bien sus neuronas, con como máximo 7 % de vacías, pero tienen un error topográfico alto: 0,18 en la de 2×2 y 0,06 en la de 5×5, por encima del 0,05. Las grandes, de 6 a 8, bajan el error hasta 0,01 pero a costa de dejar entre 22 % y 44 % de neuronas vacías, y casi un creador por neurona.

Es decir que el error topográfico mejora justamente cuando el mapa se agranda más de lo que los 50 creadores pueden llenar, igual que pasa con el error de cuantización. Por eso ninguna grilla cumple todos los límites a la vez. Aplicamos la regla sin el filtro del error topográfico, y de las que ocupan bien elegimos la más grande: la 5×5. Lo decimos como limitación: su error topográfico es 0,064, por encima del máximo, y no lo ocultamos."

**Notas para la defensa**
- **Cifras** (`deliverables/02-kohonen.md`, §3): TE por k = 2 a 8: 0,180; 0,164; 0,070; 0,064; 0,026; 0,050; 0,010. Neuronas vacías: 0,0; 0,0; 0,0; 7,2; 21,7; 33,9 y 43,8 %. Con k = 5, 6 de las 10 seeds quedan por encima de 0,05 (la barra de k = 5 trae un desvío grande).
- **Por qué se sacó el filtro de TE:** la regla fijada de antemano exige pasar los tres filtros; como ninguna k los pasa, se aplicó el paso D-14, que quita solo el de TE y deja los de ocupación sin cambios. Entre k = 2 a 5 (las que cumplen la ocupación) gana la más grande, k = 5. El informe dice explícitamente que ninguna grilla cumplió TE ≤ 0,05.
- **El TE no está en la teórica** (`docs/Kohonen Model.pdf`): es una medida que sumamos porque mide si el mapa conserva la vecindad, que es el objetivo del SOM. Decirlo así.
- **Cuidado con la barra de k = 7:** el TE medio es 0,050, justo en el límite (la regla deja pasar la igualdad); no se lee como "por encima" ni "por debajo".
- **Etapa 2:** el TE de k = 5 queda entre 0,056 y 0,074 en las 10 variantes de hiperparámetros, siempre sobre 0,05. No depende del schedule: es una propiedad de esta grilla con estos datos.
- **Relación con otras slides:** esta es la cara del TE de la slide "Elegimos 5×5"; ver también el guion de esa slide, que habla de las seis métricas con la regla anterior.

## Script hablado — Slide "El set separado resiste el ruido; el correlacionado nunca pasa de 25,0 %" (curva de recuperación)

"Acá medimos qué tan bien la red recupera una letra a la que le invertimos algunos píxeles. En el eje horizontal está la cantidad de píxeles invertidos, de 0 a 12 sobre los 25 de la letra, y arriba la misma cantidad como fracción de ruido. En el eje vertical, la tasa de recuperación exacta: cuántas veces la red vuelve exactamente a la letra original.

Probamos dos sets de cuatro letras. El **separado** son letras bien distintas entre sí, G, R, T y V, y es la curva azul. El **correlacionado** son letras muy parecidas, H, M, N y W, y es la verde. La banda alrededor de la azul es el desvío entre seeds.

La azul se mantiene casi en 100 % con poco ruido y después cae de a poco. Con 3 píxeles invertidos recupera 99,7 %, con 6 un 84,7 % y con 9 un 32,3 %. Con 12 casi no recupera nada.

La verde está clavada en 25 %, con cualquier cantidad de ruido, incluso con cero. Eso no depende del ruido: de las cuatro letras guardadas, solo la N queda como punto estable, y las otras tres terminan cayendo sobre ella. Por eso 1 de 4 da 25 %. Recién con mucho ruido, 11 y 12 píxeles, baja un poco.

Curiosamente, con 10 píxeles o más el correlacionado queda por encima del separado. No es que lo haga mejor: es que el separado ya perdió casi todo, y el correlacionado conserva ese 25 % que le da la N.

Conclusión: lo que limita a la red no es solo el ruido, es qué tan parecidas son las letras guardadas."

**Notas para la defensa**
- **Discrepancia a resolver antes de presentar:** la slide dice 99,7 %, 84,7 % y 32,3 % (k = 3, 6 y 9), pero `analysis/results/hopfield/letters/recall.csv` en esta máquina da 100 %, 90,4 % y 33,6 %. Probablemente el CSV es de una corrida anterior a que se cambiara la función de ruido (ahora invierte k píxeles distintos al azar, ver CLAUDE.md) o la slide se editó a mano. Rehacer con `make results` el paso de las letras y confirmar cuál vale; hasta entonces, el script usa los números de la slide.
- **Éxito = match exacto** con la letra original. Que la energía baje o que la red converja no alcanza: otra letra o un inverso terminan en la misma energía mínima (−264).
- **Actualización síncrona** (la de la teórica): todas las neuronas a la vez. Un ciclo de período 2 no cuenta como recuperación.
- **Qué hace la red cuando falla** (se ve en los paneles de la derecha del slide original): en el separado, otra letra, el inverso, una mezcla o un ciclo de período 2; en el correlacionado, casi siempre la N.
- **Los valores del correlacionado con 11 y 12 píxeles** (alrededor de 23 % y 16 % en la slide) los leí del gráfico, no de una tabla; confirmar antes de decirlos.
- **Ortogonalidad:** separado con producto escalar normalizado cercano a 0,04 entre pares; correlacionado entre 0,68 y 0,84.

## ¿Cómo deshace la pseudo-inversa los parecidos y por qué Hebb no?

Sea P la matriz con los patrones en las filas. P Pᵀ (Gram) tiene en el lugar (i, j) el producto escalar ξᵢ · ξⱼ: N en la diagonal y el parecido entre i y j afuera de ella.

**Hebb (W = Pᵀ P, sin 1/N):** al aplicarla a un patrón guardado,
W ξᵢ = N ξᵢ + Σ(j≠i) (ξⱼ · ξᵢ) ξⱼ.
El primer término es el patrón; el segundo es la interferencia de los otros, proporcional a su parecido. Solo desaparece si los patrones son ortogonales. Con QR parecidos la interferencia pesa tanto como el patrón y Hebb no lo deja estable.

**Pseudo-inversa (W = Pᵀ (P Pᵀ)⁻¹ P):** P ξᵢ es la columna i de P Pᵀ, es decir (P Pᵀ) eᵢ. Entonces
W ξᵢ = Pᵀ (P Pᵀ)⁻¹ (P Pᵀ) eᵢ = Pᵀ eᵢ = ξᵢ.
La inversa cancela exactamente la mezcla que mete el parecido, y cada patrón queda estable (W ξ = ξ) aunque estén correlacionados.

**En una línea:** Hebb deja la interferencia; la pseudo-inversa la cancela. Si los patrones fueran ortogonales, las dos darían lo mismo.

**Condición:** P Pᵀ tiene que ser invertible, o sea los patrones linealmente independientes.
