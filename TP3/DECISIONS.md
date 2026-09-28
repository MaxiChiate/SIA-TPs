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

## Pesos iniciales: aleatorios uniformes en [−0.5, 0.5]

**Qué:** `main` hace `srand(seed)` una sola vez y `random_weight` (`neuron/main.c`) asigna a cada
peso de cada neurona `rand() / RAND_MAX − 0.5`, bias incluido (`weights[0]`). La `seed` viene del
`config.json`.

**Por qué:**
- Aleatorios: si todas las neuronas de una capa arrancan igual, reciben el mismo gradiente y
  nunca se diferencian (simetría). Por eso `srand` va una sola vez y no por neurona: con la
  misma seed en cada una, todas arrancarían con los mismos pesos.
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

## Online, batch y mini-batch: un solo parámetro, `batch_size`

> **A revisar:** suma vs. promedio del Δw del batch, y si se mezclan las muestras en cada época.

**Qué:** cada muestra suma su Δw = η·δ·x a un acumulador de la neurona, y los pesos cambian
recién cuando se completa el batch. `batch_size = 1` es online, `≥ N` es batch, en el medio
mini-batch. Se suma, no se promedia.

**Por qué:**
- Un solo camino de código para los tres regímenes: se comparan cambiando un número del config.
- Suma y no promedio porque así lo define la regla (ΔW = Σ Δw). La contra: con batch más grande
  el paso es más grande, así que η hay que ajustarlo según `batch_size`.
- El último batch de la época puede quedar incompleto y se aplica igual, para no descartar
  muestras.

## Backpropagation: todos los δ antes de tocar un peso

**Qué:** por muestra, forward (guarda h y V de cada capa), δ de salida
`(ζ − O)·θ'(h)`, δ de las ocultas de atrás hacia adelante `θ'(h_j)·Σ_k w_kj·δ_k`, y recién
después se acumula Δw en todas las neuronas.

**Por qué:**
- El δ de una capa oculta usa los pesos de la capa siguiente. Si se actualizaran antes, el error
  se propagaría con pesos que no son los que produjeron la salida.
- Con el acumulador esto sale solo: los pesos no cambian hasta el final del batch.
- Todas las capas usan la misma activación; tiene que ser derivable (`tanh`, `logistic`). Con
  escalón, θ' = 0 y no llega error a las ocultas.
- Con `hidden_layers: []` la red es una neurona sola y la regla queda igual a la del perceptrón
  simple: verificado, mismas predicciones y pesos que la versión anterior.

## Curva de aprendizaje: E, MSE, MAE y máx |e| por época, sobre train y validación

> **A confirmar:** medir con una pasada aparte (y no acumulando durante la época), MSE como
> error principal para comparar train y validación, y medir en todas las épocas y no cada k.

**Qué:** al terminar cada época (con el último batch ya aplicado) se hace un forward de todo el
train y de toda la validación, sin tocar los pesos, y se guardan E, MSE, MAE y máx |e| de cada uno
en `epochs.csv` (salen de la misma pasada). El reporte deja elegir cuál graficar; por defecto MSE. La época 0 es la red sin entrenar. `network_train` recibe un callback por época;
la medición la hace `main`, así la red no sabe que existe un conjunto de validación.

- **E = ½·Σ(ζ − O)²**: la función que minimiza la regla (Δw = −η·∂E/∂w); el ½ cancela el 2 de
  la derivada. Crece con la cantidad de muestras.
- **MSE = Σ(ζ − O)² / N = 2E / N**: E por muestra; es el que se compara entre train y
  validación, porque tienen distinto N.
- **MAE = Σ|ζ − O| / N**: error medio en las unidades de ζ; un error grande pesa menos que en
  el MSE. **máx |e|**: la peor muestra; muestra si queda algún caso sin aprender aunque el
  promedio sea bajo.
- **Train**: error sobre `train_dataset`, lo que el entrenamiento ve. **Validación**: sobre
  `validation_dataset`, muestras que no ve. Si train baja y validación sube, hay overfitting.
  Si con esta curva se elige algo (época, η, arquitectura), ese conjunto deja de ser de test:
  el test final tiene que ser otro, sin tocar.

**Por qué:**
- Pasada aparte y no acumular el error durante la época: en online y mini-batch cada muestra se
  mediría con pesos distintos, y el número no correspondería a ningún modelo. Así cada punto es
  el error de la red que se tiene al final de esa época.
- El costo es un forward extra por muestra de train y de validación por época: con fraude
  (7500 muestras, mismo dataset para las dos) pasa de 0.80 s a 1.45 s en 300 épocas.
- Sin threads: el entrenamiento es secuencial (cada update depende del anterior), así que solo
  se podría paralelizar la medición, y con datasets de 4 a 7500 muestras la sincronización por
  época come la ganancia. Para usar los núcleos conviene correr varias configs o seeds en
  procesos separados.

## Dígitos: píxeles sin normalizar y label en one-hot

**Qué:** `scripts/prepare_digits_dataset.py` escribe cada imagen como `x1..x784` (los píxeles
tal cual vienen) seguido de `zeta_0..zeta_9`, el label en one-hot: una columna ζ por neurona de
salida.

**Por qué:**
- Los píxeles ya están todos en `[0, 1]`, en la misma escala, así que no hay columnas que
  saturen la activación. Con z-score, los bordes (siempre negros) tendrían desvío 0.
- One-hot y no una sola salida con el dígito como número: 0–9 no es una magnitud ordenada (un 7
  no está "más cerca" de un 8 que de un 1). Con 10 salidas, cada neurona aprende "¿es este
  dígito?" y la clase predicha es el argmax.
- ζ en {0, 1}, que es el rango de `logistic`.

## Varias neuronas de salida: las ζ se leen del encabezado

**Qué:** la cantidad de neuronas de salida es la cantidad de columnas finales del CSV cuyo nombre
empieza con `zeta` (`zeta_0 … zeta_9` en dígitos). Si no hay encabezado o ninguna se llama así, es una
sola: la última columna. No hay clave en el config.

**Por qué:**
- La salida la define el problema, no es un hiperparámetro: sale del dataset igual que `n_inputs`.
  Una clave `n_outputs` en el config podría contradecir al CSV.
- Los datasets que ya había (`zeta`, `big_model_fraud_probability`) siguen dando una salida, sin
  cambios: corrimos XOR antes y después y los archivos de resultados son idénticos byte a byte.
- E, MSE y MAE se promedian sobre muestras × salidas, así que el reporte cuenta cada (muestra,
  salida) como un valor. Para clasificar, además, aciertos por argmax.
