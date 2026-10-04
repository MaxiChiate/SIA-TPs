# Decisiones — TP3

Decisiones que nos pueden preguntar en la defensa. Cada una dice qué hicimos y por qué.

## Normalización de entradas (fraude): z-score sobre cada columna

**Qué:** `scripts/prepare_fraud_dataset.py` lleva cada input a `(x − media) / desvío`. El
target (`big_model_fraud_probability`) no se toca, porque ya está en `[0, 1]`. `flagged_fraud`
va a un archivo aparte y no entra al entrenamiento.

**Por qué:**
- Las escalas van de ~10 a ~1.7e9 (`timestamp`). Sin normalizar, `h` es enorme, la
  activación se satura y θ' ≈ 0: la neurona no aprende.
- Z-score y no min-max: centra las entradas en la zona útil de logistic y tanh, y un valor
  extremo no aplasta al resto contra 0, cosa que sí pasa con min-max en columnas con cola
  larga como `amount_usd` (media 109, máximo 2000).
- La media y el desvío salen solo del conjunto de entrenamiento. En la parte 1 es el dataset
  completo; en la parte 2, solo el split de train, para no filtrar información del test.

## Exploración del fraude: qué se encontró y qué se hace con eso

**Qué:** `scripts/explore_fraud_dataset.py` describe el dataset antes de modelar. Hallazgos: 7500
filas sin nulos ni duplicados; 11.6 % con `flagged_fraud = 1`; `timestamp`,
`device_screen_resolution` y `time_since_last_login_s` tienen correlación ≈ 0 con la
probabilidad de BigModel (|r| < 0.03), las otras seis entre 0.33 y 0.59 en valor absoluto; y
`flagged_fraud = 1` coincide exactamente con probabilidad ≥ 0.85 (el fraude de menor
probabilidad tiene 0.850089 y el no fraude de mayor tiene 0.849891).

**Por qué importa:**
- Las tres columnas sin correlación son candidatas a descartar. No se descartan por la
  exploración sola: la correlación de Pearson no ve relaciones no lineales, así que se confirma
  entrenando con y sin ellas.
- `amount_usd` tiene cola larga (mediana 63, p99 862, máximo 2000): se prueba `log(amount)`
  además del z-score.
- La probabilidad de BigModel llega a 1.0 exacto en 43 filas y la logistic solo lo alcanza en el
  límite, así que el error de esas muestras no baja a 0.
- Con 11.6 % de fraudes, el split de la parte 2 se estratifica por `flagged_fraud`, para que
  validación no se quede con pocos positivos.
- Umbral: BigModel separa perfecto en 0.85, pero el TinyModel imita la probabilidad con error, así
  que su umbral óptimo puede correrse. Se elige con `flagged_fraud` sobre validación, no se
  asume 0.85.

## Elección del TinyModel (fraude, parte 1): perceptrón logistic

**Qué:** series `analysis/series_fraud_activation.json` y `series_fraud_capacity.json` sobre el
dataset completo (train = validación, como pide el enunciado), online, 1000 épocas, 3 seeds. MSE
y R² = 1 − MSE / varianza del objetivo (0.0915):

| Modelo | MSE | R² |
|---|---|---|
| lineal (η 0.0001 y 0.001) | 0.0261 | 0.715 |
| logistic (η 0.001 y 0.01) | 0.0109 | 0.881 |
| logistic con `[4]` | 0.0106 | 0.884 |
| logistic con `[16]` y `[16, 8]` | 0.0105 | 0.886 |

**Por qué logistic:**
- El lineal tiene underfitting: la relación entre las entradas y la probabilidad no es una
  combinación lineal, y no baja de 0.026 por más épocas ni con otro η (ya está en su óptimo).
- La logistic reduce el error 2.4 veces con la misma cantidad de pesos y su salida vive en (0, 1).
- Saturación de capacidad: agregar capas ocultas solo baja el MSE de 0.0109 a 0.0105. Un perceptrón
  simple ya capta casi todo lo que dan estas entradas; el resto no se arregla con más neuronas.
- La diferencia entre seeds es menor a 0.0001 y η casi no importa (0.001 a 0.1): el problema
  es de un mínimo único.
- Límite de esta conclusión: es error de entrenamiento sobre todo el dataset. Qué tan bien
  generaliza se estudia en la parte 2.

## Pesos iniciales: aleatorios uniformes en [−0.5, 0.5]

**Qué:** `main` crea un único `Rng` (`neuron/rng.c`, splitmix64) con la `seed` del `config.json` y
lo pasa a `network_new`; `random_weight` (`neuron/main.c`) asigna a cada peso de cada neurona
`uniforme[0,1) − 0.5`, bias incluido (`weights[0]`).

**Por qué:**
- Aleatorios: si todas las neuronas de una capa arrancan igual, reciben el mismo gradiente y
  nunca se diferencian (simetría). Por eso hay una sola instancia de RNG compartida y no una
  por neurona: con la misma seed en cada una, todas arrancarían con los mismos pesos.
- RNG propio e inyectado y no `rand()`: es estado global, y su secuencia cambia según la libc,
  así que la misma seed no daba lo mismo en otra máquina.
- Chicos y centrados en 0: `h` arranca cerca de 0, donde θ' es máxima; así no se arranca con
  la activación saturada.
- Con seed fija: misma seed y mismo config dan el mismo resultado, y las corridas se pueden
  comparar.

## Activación del no lineal (fraude): logistic, no tanh

**Qué:** θ(h) = 1 / (1 + e^(−h)), θ'(h) = θ(h)·(1 − θ(h)). Está en `neuron/activation/`.

**Por qué:**
- La salida es una probabilidad y ζ vive en [0, 1]. La imagen de la logistic es (0, 1), la
  de tanh es (−1, 1): con tanh la neurona puede predecir probabilidades negativas y la mitad
  de su rango queda en valores imposibles.
- Resultado sobre el dataset completo (η = 0.001 y 1000 épocas para lineal y logistic;
  η = 0.0001 para tanh): MSE lineal 0.026 (su óptimo teórico), tanh 0.015, logistic 0.011.
- θ' sale de θ misma, sin otra exponencial.
- Se implementa partida por signo de h para que `exp` no desborde con |h| grande.

## Actualización de pesos: online, batch y mini-batch con `batch_size`

**Qué:** cada muestra calcula su Δw = η·δ·x y lo suma a un acumulador de la neurona; los pesos
cambian recién cuando se completa el batch. `batch_size = 1` es online, `≥ N` es batch, en el
medio mini-batch. Las muestras van en el orden del CSV.

**Por qué:**
- Un solo camino de código: los tres regímenes se comparan cambiando un número del config.
- Se suma, no se promedia, porque así es la regla (ΔW = Σ Δw). La contra: con batch más grande
  el paso es más grande, así que η se ajusta según `batch_size`.
- El último batch de la época puede quedar incompleto y se aplica igual, para no descartar
  muestras.

> **Sin decidir:** promediar en vez de sumar, y mezclar las muestras en cada época (hoy los
> mini-batches son siempre los mismos).

## Backpropagation: primero todos los δ, después los pesos

**Qué:** por muestra, forward guardando h y V de cada capa; δ de salida `(ζ − O)·θ'(h)`; δ de
cada oculta, de atrás hacia adelante, `θ'(h_j)·Σ_k w_kj·δ_k`; y recién ahí se acumula Δw en
todas las neuronas.

**Por qué:**
- El δ de una oculta usa los pesos de la capa siguiente. Si esos pesos cambiaran antes, el error
  se propagaría con pesos distintos de los que produjeron la salida.
- Todas las capas usan la misma activación y tiene que ser derivable (`tanh`, `logistic`): con
  escalón θ' = 0 y a las ocultas no les llega error.
- Con `hidden_layers: []` queda la regla del perceptrón simple. Verificado: mismos pesos y
  predicciones que la neurona sola.

## Medición del error: una pasada aparte al final de cada época

**Qué:** al terminar cada época se hace un forward de todo el train y de toda la validación, sin
tocar los pesos, y se guarda el error de cada uno en `epochs.csv`. La época 0 es la red sin
entrenar.

**Por qué:**
- No se acumula el error durante la época: en online y mini-batch cada muestra se mediría con
  pesos distintos, y el número no sería el de ningún modelo. Así cada punto es el error de la red
  que se tiene al final de esa época.
- Cuesta un forward extra por muestra: con fraude (7500 muestras), 300 épocas pasan de 0.80 s a
  1.45 s.

## Métricas de error: MSE para comparar, MAE y máx |e| para interpretar

**Qué:** de la misma pasada salen cuatro números; el reporte grafica MSE por defecto.

**Por qué cada uno:**
- **E = ½·Σ(ζ − O)²**: es lo que minimiza la regla (Δw = −η·∂E/∂w; el ½ cancela el 2 de la
  derivada). Crece con N, así que no sirve para comparar conjuntos de distinto tamaño.
- **MSE = Σ(ζ − O)² / N = 2E / N**: el principal. Es E por muestra, así que se puede comparar
  train contra validación.
- **MAE = Σ|ζ − O| / N**: error medio en las unidades de ζ (en fraude, puntos de probabilidad).
  Un error grande pesa menos que en el MSE.
- **máx |e|**: la peor muestra. Muestra si queda algún caso sin aprender aunque el promedio sea
  bajo.

## Train y validación: dos curvas

**Qué:** el error se mide sobre `train_dataset` (lo que ve el entrenamiento) y sobre
`validation_dataset` (muestras que no ve), los dos definidos en el config.

**Por qué:**
- Si train baja y validación sube, hay overfitting; con una sola curva no se ve.
- Si con la curva de validación se elige algo (época, η, arquitectura), ese conjunto deja de ser
  un test honesto: la evaluación final tiene que hacerse sobre otro conjunto, sin tocar.

## Fin del entrenamiento: mejor error visto y convergencia

**Qué:** después de cada época `main` compara el MSE de train con el mejor visto y, si es menor,
copia los pesos. Al terminar (o al converger) la red queda con los pesos de la mejor época, no de
la última. Se corta antes de tiempo si: activación discreta (`sign`) → cero muestras mal
clasificadas; el resto → MSE de train `< tolerance` (opcional en el config; 0 = nunca corta).

**Por qué:**
- El error no baja monótonamente (una corrección puede romper otra muestra), así que el último
  estado puede ser peor que uno anterior.
- Con floats un error exactamente 0 nunca se alcanza, por eso la tolerancia; en el escalón sí
  tiene sentido contar errores, porque la salida es ±1.
- El criterio de mejor es el error de **train**, no el de validación: elegir por validación la
  convertiría en parte del entrenamiento. Si hace falta, se elige la época a mano mirando las curvas.
- La regla de Rosenblatt no necesita rama aparte: `sign_prime` devuelve 1 y la regla delta
  genérica η·(ζ − O)·x da exactamente la de Rosenblatt.

## Shuffle por época (opcional)

**Qué:** con `"shuffle": true`, `network_train` mezcla el orden de las muestras al empezar cada
época (Fisher-Yates, `rng_shuffle`) con el mismo `Rng` de los pesos iniciales. Se mezcla un
arreglo de índices, no el dataset. Sin la clave (o con `false`) siguen en el orden del CSV.

**Por qué:**
- Sin mezclar, los mini-batches son siempre los mismos y el online ve las muestras en el orden del
  archivo; si el CSV viene ordenado (por clase, por fecha) cada época arrastra la red hacia lo
  último que vio.
- El batch completo no cambia: suma Δw sobre todas las muestras, el orden no importa (hay un test).
- Mismo `Rng` y no uno nuevo: una sola instancia por corrida, inyectada. Se arranca después de
  sortear los pesos, así `initial_weights` no altera el orden de las muestras.
- Apagado por defecto: así los configs y las series que ya existen dan lo mismo que antes.

## Validación a partir de un solo CSV: `validation_split` + `split_seed`

**Qué:** en lugar de `validation_dataset`, el config puede traer `validation_split` (parte de
`train_dataset` que se aparta, entre 0 y 1) y `split_seed`. Exactamente una de las dos fuentes;
`split_seed` es obligatoria con el split y no puede ir sin él. El split se hace una vez, antes de
entrenar (`dataset_split`): se mezclan los índices con su propio `Rng` y los primeros
`round(N·fracción)` (al menos 1, dejando al menos 1 en train) son validación. Cada lado conserva el
orden del CSV. No es estratificado.

**Por qué:**
- El dataset de fraude es un solo archivo, y el enunciado pide estudiar generalización.
- `split_seed` aparte de `seed`: al barrer `seed` (pesos iniciales, shuffle) el split no se mueve,
  así la variación entre corridas no mezcla dos fuentes de azar. Obligatoria por la convención del
  TP: toda aleatoriedad lleva seed explícita.
- Mantener el orden del CSV en cada lado: `predictions.csv` queda alineado con el archivo y el
  shuffle por época se ocupa de mezclar el entrenamiento.
- Sin estratificar: la ζ del fraude es una probabilidad continua, no una clase. Con dígitos, un
  split al azar de miles de muestras por clase es bastante parejo.
- Vale lo de «Train y validación: dos curvas»: si con la validación se elige algo, ese pedazo ya no
  es un test honesto.

## ReLU: `max(0, h)` con θ'(0) = 0

**Qué:** `relu` es una activación más (`activation/activation.c`): θ(h) = max(0, h), θ'(h) = 1 si
h > 0 y 0 si no.

**Por qué:**
- Es el opcional del enunciado (efecto de ReLU en las conclusiones del no lineal).
- En h = 0 no es derivable; se elige 0 (convención usual) y el test de la derivada numérica
  salta ese punto.
- Su salida no está acotada: en fraude (salida en (0, 1)) `logistic` sigue siendo la adecuada para
  la salida. Como la activación es una sola para toda la red, ReLU en las ocultas y `logistic` en la
  salida todavía no se puede combinar.

## Gráficos de las series: plotly, pareado por seed y plotly.js compartido

**Qué:** `analysis/plots_main.py` arma, por serie, curvas de MSE (train, validación y la brecha) y
gráficos de comparación (puntos por seed, boxplot, diferencia pareada o puesto por seed, velocidad,
costo contra calidad, generalización) más un `index.html`. Es el esquema de TP2 llevado a la red. Las
tablas traen test de permutación pareado, IC95% bootstrap y corrección de Holm contra la mejor variante.

**Por qué:**
- Es la misma pregunta que en TP2: una curva dice qué pasó, pero no si dos variantes realmente
  difieren. Todas las variantes corren las mismas seeds y una seed fija los pesos iniciales (y el
  shuffle), así que las corridas están pareadas y se comparan sin gastar resolución en la dispersión
  entre seeds. Con pocas seeds el test exacto (2^n signos) es barato y no supone normalidad; con 3 seeds
  el p mínimo es 0.25, y la tabla lo muestra en vez de esconderlo.
- Acá el error se **minimiza** (en TP2 el fitness se maximizaba): cada `Metric` dice hacia dónde es
  mejor y todo el ranking y el pareado lo leen de ahí.
- La velocidad usa como umbral el error de validación más exigente que alcanzan *todas* las corridas;
  con el mejor error de la ganadora, las variantes más débiles nunca llegarían y el gráfico quedaría vacío.
- Una corrida que corta antes (por `tolerance`) conserva su último valor en las curvas: el entrenamiento
  terminó ahí, y promediar menos seeds hacia el final sesgaría la curva.
- `plotly.min.js` se escribe una vez por serie (`include_plotlyjs="directory"`): funciona sin internet
  como un plotly embebido, y la serie pesa ~4 MB en lugar de ~4 MB por gráfico.
- `sweep.py` y su `report.html` siguen sin dependencias; plotly solo se pide para `plots_main.py`.
