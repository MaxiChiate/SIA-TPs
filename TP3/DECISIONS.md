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
