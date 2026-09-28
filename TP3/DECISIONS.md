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
