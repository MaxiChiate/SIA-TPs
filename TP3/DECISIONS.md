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

## Generalización del fraude (parte 2): split, entradas, tamaño de train y umbral

**Qué:** `scripts/prepare_fraud_split.py --seed 1` parte el dataset en train / validación / test
70/15/15 (5250 / 1125 / 1125), estratificado por `flagged_fraud` (609, 130 y 130 fraudes: 11.6 % en cada
parte). El z-score usa media y desvío solo de train. `flagged_fraud` va a un archivo de labels aparte.
`analysis/fraud_threshold.py` calcula métricas y elige el umbral. Series: `series_fraud_features.json`,
`series_fraud_train_size.json` y `series_fraud_final.json` (logistic, η 0.01, 200 épocas online con
shuffle, 5 seeds).

**Resultados (validación):**
- Entradas: 9 entradas MSE 0.0107 y PR-AUC 0.962; 6 entradas (sin `timestamp`, `device_screen_resolution` ni
  `time_since_last_login_s`) MSE 0.0108 y PR-AUC 0.962; con `log(amount)` MSE 0.0156 y PR-AUC 0.956.
- Tamaño del train: con 262 muestras (5 %) MSE 0.0112 y con 5250 (100 %) 0.0108.
- Final: 6 entradas, monto sin transformar, train completo. Train 0.0109 y validación 0.0108: sin sobreajuste.

**Umbral:** el más alto con recall ≥ 95 % en validación, redondeado hacia abajo a 0.01 (en el split 1 el exacto
es 0.8248, y 0.825 ya no llega al 95 %). En el split 1 da 0.82: validación precisión 0.810 y recall 0.954; test
(1125 transacciones) precisión 0.762, recall 0.962, F1 0.850, TP 125, FP 39, FN 5, TN 956, PR-AUC 0.956.
**Pero depende del split** (`analysis/fraud_split_variability.py`, 10 splits, la seed de la red fija): el umbral
elegido va de 0.77 a 0.84 (0.793 ± 0.022), la precisión en test es 0.736 ± 0.038 y el recall 0.962 ± 0.022 (bajo
0.95 en 1 de 10). Con un umbral fijo, evaluado en el test de los 10 splits:

| Umbral | Precisión | Recall | Splits con recall < 0.95 |
|---|---|---|---|
| 0.75 | 0.672 | 0.982 | 0 de 10 |
| 0.78 | 0.713 | 0.968 | 0 de 10 |
| 0.80 | 0.751 | 0.962 | 3 de 10 |
| 0.82 | 0.777 | 0.945 | 6 de 10 |
| 0.85 | 0.805 | 0.898 | 10 de 10 |

**Se recomienda 0.78**, la mediana de los umbrales elegidos en validación: recall mínimo 0.954 en los 10 tests
y precisión 0.713. El 0.82 del split 1 era de los altos y deja el recall bajo 0.95 en 6 de 10 splits.

**Por qué:**
- Estratificado: con 11.6 % de fraudes, un split al azar puede dejar pocos positivos en validación.
- Métricas: precisión, recall y PR-AUC contra `flagged_fraud`. El accuracy no sirve (decir siempre «no
  fraude» acierta 88.4 %); el MSE y el MAE miden qué tan bien imita a BigModel.
- Se descartan las tres columnas porque no aportan: mismo error con menos pesos (7 contra 10). Se confirmó
  entrenando, no solo con la correlación de Pearson.
- `log(amount)` empeora, así que el monto crudo ajusta mejor; no se usa.
- Con pocos datos ya se llega al mismo error: el modelo tiene 7 pesos, el límite no son los datos.
- Umbral por recall mínimo: en fraude un caso que se escapa suele costar más que una compra legítima
  revisada. El 95 % es una elección nuestra; el cliente puede pedir otro, y en test el recall mueve
  casi un punto por cada fraude (130 en total).
- El test se usó una sola vez, para reportar el umbral ya elegido.
- Límites: las diferencias entre variantes de entradas y de tamaño de train son de milésimas y se midieron con
  seeds distintas sobre un solo split. Los 10 splits del umbral se arman con los mismos 7500 datos y no son
  independientes (los tests se solapan).

## Calibración de probabilidades del fraude (opcional)

**Qué:** `analysis/fraud_calibration.py`. Se mide qué tan cerca está la salida del TinyModel de
P(fraude | salida) usando `flagged_fraud`, y se prueban dos calibraciones ajustadas en validación y medidas en
test (split 1, 1125 transacciones, 130 fraudes): Platt (sigmoide de la salida, dos parámetros, Newton) y
regresión isotónica (pool adjacent violators).

| Salida | Brier | Log loss | ECE |
|---|---|---|---|
| BigModel (probabilidad original) | 0.160 | 0.468 | 0.307 |
| TinyModel sin calibrar | 0.156 | 0.476 | 0.308 |
| TinyModel + Platt (σ(22.6·salida − 19.7)) | 0.023 | 0.074 | 0.021 |
| TinyModel + isotónica | 0.021 | 0.073 | 0.008 |

**Por qué importa:**
- La probabilidad de BigModel no es probabilidad de fraude: `flagged_fraud` es 1 exactamente cuando pasa 0.85,
  así que la relación real es un escalón. Una salida de 0.55 corresponde a 0 % de fraudes (0 de 101 en test).
  El TinyModel hereda eso porque imita a BigModel.
- Calibrar baja el ECE de 0.31 a 0.02 o menos. La isotónica queda apenas mejor, pero con 130 fraudes en
  validación puede sobreajustar; Platt tiene dos parámetros.
- Con la salida calibrada, el umbral puede expresarse como probabilidad de fraude.
- Límite: un solo split; los intervalos intermedios del diagrama de confiabilidad tienen 6 a 19 muestras.

## ReLU en fraude (opcional): sin capa oculta no suma, con capa oculta iguala a logistic

**Qué:** `analysis/series_fraud_relu.json`, 10 seeds, dataset completo, 1000 épocas online. R² (MSE):
lineal 0.714 (0.0262), ReLU 0.717 (0.0259), logistic 0.881 (0.0109), ReLU con `[16]` 0.883 (0.0107),
logistic con `[16]` 0.886 (0.0105).

**Por qué importa:**
- ReLU sin capa oculta es una sola neurona con `max(0, h)`: rinde como el lineal. La mejora de la
  logistic no viene de "no ser lineal" a secas, sino de acotar la salida a (0, 1).
- Con `[16]` ReLU llega al nivel de la logistic, pero la salida (también ReLU, hay una sola activación
  para toda la red) no está acotada: puede predecir probabilidades fuera de [0, 1]. Para este problema
  se mantiene logistic.

## Optimizadores (Ej. 2), etapa 2: resultados y evaluación final sobre `digits_test.csv`

**Qué:** la etapa 1 se amplió hacia arriba hasta encontrar el pico de cada optimizador
(`series_eta_edges.json`, `series_eta_edges_high.json`, `series_eta_edges_higher.json`): con la grilla
original GD y η adaptativo tenían el mejor valor en el borde (η 0.05, 96.0 %) y siguieron subiendo. Mejor
η (accuracy de validación, 3 seeds): GD 0.5 (96.57 %; el 1.0 da 96.57 pero ya queda pegado a donde cae,
η 2 da 93.7 % y η 5 diverge), η adaptativo 0.5 (96.57 %), momentum 0.05 (96.57 %; 0.5 diverge, 16 %),
RMSProp 0.001 (96.14 %) y Adam 0.0005 (96.45 %). Etapa 2: `series_optimizer.json` (validación, 20 % de
`digits.csv`) y `series_optimizer_test.json` (entrenando con `more_digits.csv`, evaluando sobre
`digits_test.csv`), **10 seeds**, `[64]` logistic, online con shuffle, 50 épocas.

| Optimizador | Validación | Test | Segundos por corrida |
|---|---|---|---|
| η adaptativo | 96.57 ± 0.15 | 95.47 ± 0.38 | 22 |
| GD | 96.56 ± 0.19 | 95.41 ± 0.23 | 23 |
| Momentum | 96.48 ± 0.14 | 95.68 ± 0.25 | 37 |
| Adam | 96.14 ± 0.27 | 95.01 ± 0.16 | 46 |
| RMSProp | 96.10 ± 0.26 | 95.16 ± 0.25 | 50 |

**Conclusiones** (test de permutación exacto pareado por seed, corrección de Holm):
- GD, momentum y η adaptativo no se distinguen. RMSProp y Adam quedan 0.4 a 0.7 puntos por debajo del
  mejor en las dos particiones: en validación η adaptativo contra RMSProp p = 0.029 y contra Adam 0.023; en
  test momentum contra RMSProp 0.012 y contra Adam 0.008 (momentum contra GD 0.074 y contra η adaptativo 0.20).
- Con 5 seeds no se había encontrado ninguna diferencia (el p mínimo posible era 0.0625): era falta de
  potencia, no ausencia de diferencia. Con 10 el p mínimo es 0.002.
- El mejor cambia entre validación (η adaptativo) y test (momentum), pero entre los tres de arriba no hay
  diferencia significativa.
- Lo que más importa es el η: el mismo optimizador pasa de 90 % a 96.6 % según η.
- Todos bajan de MSE de validación 0.010 en 2 o 3 épocas y después casi no mejoran; η adaptativo sube hacia
  el final (0.0060 a la época 25 y 0.0070 a la 50) y no se investigó la causa.
- GD y η adaptativo cuestan la mitad de tiempo por corrida que Adam y RMSProp.
- GD con η 0.5 y momentum con η 0.05 rinden igual: es el paso η/(1−α) con α = 0.9.
- Alcance: la variación que se prueba es la de pesos iniciales y shuffle, con una sola partición de datos.

**Elección y evaluación final:** el ganador por validación es η adaptativo (η 0.5). Se usa en las dos
evaluaciones finales, y cada una responde a un ejercicio (ver la entrada siguiente).

**Por qué:**
- El accuracy global no alcanza: oculta que una clase entera falle. Por eso el reporte trae matriz de
  confusión y aciertos y precisión por clase.
- `digits_test.csv` se usa solo en la evaluación final.
- Límites: validación con una sola partición (`split_seed` 1); 50 épocas sin `tolerance`.

## Ejercicios 2 y 3: qué datos se usan en cada uno, y arquitectura

**Qué:** el enunciado dice que `digits.csv` se usa para ajustar parámetros e hiperparámetros, que `digits_test.csv`
es el «mundo real» (no se usa para elegir nada), y que el Ejercicio 3 agrega `more_data_digits.csv` (en el
repo, `more_digits.csv`) con la meta de accuracy ≥ 98 %. Por eso:
- **Ejercicio 2** = solo `digits.csv`. Hiperparámetros con una validación de 20 % de `digits.csv`
  (`validation_split`). Evaluación final: entrenar con `digits.csv` y medir en `digits_test.csv`
  (`series_optimizer_digits_test.json`, 10 seeds): η adaptativo 86.26 ± 0.22 %, momentum 86.08, GD 86.07, Adam
  85.98, RMSProp 85.13. El 8, que no está en `digits.csv`, tiene 0 % de aciertos y es el 9.7 % del test, así que
  el techo es ≈ 90 %; en los otros 9 dígitos da 95.6 % (seed 4). Es el resultado «no satisfactorio» que
  motiva el Ejercicio 3.
- **Ejercicio 3**: ver la entrada siguiente (la meta de 98 % se cumple con una búsqueda propia).
- **Arquitectura** (`series_architecture_digits.json`, η adaptativo, validación de `digits.csv`, 5 seeds):
  sin capa oculta 92.79 %, `[16]` 94.22, `[32]` 95.65, `[64]` 96.62, `[128]` 96.83, `[64, 32]` 96.37. `[128]` suma
  0.2 puntos y cuesta el doble (41 s contra 22 s por corrida), y dos capas no mejoran a una: se usa `[64]` por
  costo contra beneficio (la diferencia de 0.2 no se probó estadísticamente).

**Por qué:**
- Es lo que pide el enunciado, y evita elegir hiperparámetros mirando el test.
- Las series viejas de dígitos (`series_eta`, `series_architecture`, `series_batch_size`, `series_train_dataset`,
  `series_activation`, `series_shuffle`, `series_depth`) usan `more_digits` para entrenar y `digits_test` como
  validación: sirven para explorar, pero no para elegir hiperparámetros del Ejercicio 2 según esta aclaración.
  Las de optimizadores y arquitectura que se usan en la presentación parten de `digits.csv` con
  `validation_split`.
- Opcionales sin hacer (Ejercicios 2 y 3): robustez al ruido gaussiano e interpretabilidad con métodos de
  atribución.

## Ejercicio 3: cómo se llegó a 98,7 % en test

**Qué:** meta del cliente accuracy ≥ 98 %. `digits.csv` y `more_digits.csv` comparten 3689 imágenes (la unión sin
repetidos tiene 24 501) y ninguno comparte imágenes con `digits_test.csv`. `scripts/prepare_digits_ex3.py --seed 1`
aparta una validación de 4900 imágenes (20 % de la unión) y arma los entrenamientos sin ellas. Todo se elige con
esa validación; `digits_test.csv` se evalúa **una sola vez**, al final. Series: `series_ex3_step1.json`,
`step2` y `step3` (3 seeds), η adaptativo (η 0.5), online con shuffle, 50 épocas.

| Paso | Validación |
|---|---|
| `[64]` con `more_digits` | 96.22 |
| + unión de datos | 96.41 |
| + `[256]` | 97.63 (`[128]` 97.30, `[512]` 97.88, `[256, 128]` 97.77) |
| + aumento ×3 (2 copias por imagen, desplazamiento ±2 px, rotación ±10°) | 98.13 (×5: 98.24) |
| + `[512]` | 98.40 |
| ensemble de 9 redes (`[512]`, `[256, 128]` con ×3 y `[256]` con ×5; 3 seeds cada una) | 98.90 |

No ayudaron: centrar por centro de masa (97.44 contra 97.63; con aumento 98.26, sin diferencia clara con 98.13),
100 épocas (97.69), η 0.2 (97.56) y η 1.0 (97.20).

**Resultado en test** (una evaluación, 2497 imágenes, protocolo fijado con la validación): ensemble de las 9
redes **98.72 %** (32 errores; el 98 % admite 50); ensemble de las 3 `[512]` 98.40; redes individuales `[512]`
98.29 ± 0.05, `[256, 128]` 97.93 ± 0.30, `[256]` con ×5 97.70 ± 0.14. La validación sobreestimó el test en 0.2
puntos (98.90 contra 98.72). Aciertos por clase entre 96.9 % (el 5) y 100 %.

**Por qué:**
- La capacidad es lo que más sube (+1.2 de `[64]` a `[256]`) y después el aumento (+0.5); la unión de datos suma 0.2.
- El aumento solo se aplica al entrenamiento; validación y test no se tocan.
- El ensemble (promedio de las salidas) suma 0.5 puntos sobre la mejor red y es otra técnica que no cambia el
  código en C: `analysis/digits_ensemble.py`.
- El centrado no aporta (no se investigó por qué).
- Costo: cada red tarda unos 17 minutos (entrenamiento en línea, un núcleo) contra 25 segundos de la `[64]`.
- Un primer intento de evaluar sobre el test salió mal por un error de configuración (las variantes de la serie
  pisaban el `validation_dataset` de la serie y se evaluó otra vez sobre la validación). Se detectó porque los números
  coincidían con los de validación (y confirmó que el entrenamiento es determinista) y se repitió bien: el test no
  se había mirado. Lección: verificar el `validation_dataset` del `config.json` de cada corrida antes de leer números.
- Límites: una sola partición de validación y una sola evaluación en test (con 2497 imágenes, 98.7 tiene ±0.2 de
  incertidumbre). No se probó regularización ni otras activaciones (una sola activación para toda la red).

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

**Qué:** cada muestra calcula su δ·x y lo suma a un acumulador de la neurona; cuando se completa el
batch, el optimizador convierte esa suma en el paso de los pesos (con `gd`, Δw = η·Σ δ·x; ver
«Optimizadores»). `batch_size = 1` es online, `≥ N` es batch, en el medio mini-batch. Las muestras van
en el orden del CSV, salvo con `shuffle`.

**Por qué:**
- Un solo camino de código: los tres regímenes se comparan cambiando un número del config.
- Se suma, no se promedia, porque así es la regla (ΔW = Σ Δw). La contra: con batch más grande
  el paso es más grande, así que η se ajusta según `batch_size`.
- El último batch de la época puede quedar incompleto y se aplica igual, para no descartar
  muestras.

> **Sin decidir:** promediar en vez de sumar. (Mezclar las muestras ya está: ver «Shuffle por época».)
> Con RMSProp y Adam importa menos, porque su paso no depende de la escala del gradiente.

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

## Optimizadores: un módulo aparte que no conoce la red

**Qué:** `neuron/optimizer/` implementa `gd`, `momentum`, `rmsprop`, `adam` y `adaptive_eta` (se elige
con `optimizer` en el config). Backprop acumula en cada neurona d = Σ δ·x (= −∂E/∂w, sin η) y, al cerrar
el batch, `optimizer_step(pesos, d)` decide el paso. El optimizador trabaja sobre un arreglo de números:
no incluye nada de neuronas, redes ni datasets. Cada neurona tiene su propio optimizador.

**Por qué:**
- Antes η estaba dentro del acumulador (se sumaba η·δ·x): así RMSProp y Adam no pueden reescalar cada
  peso por separado. Backprop da el gradiente; qué hacer con él es otro problema (clase 12.1).
- Genérico: si cambia el problema, el optimizador no se toca. Por eso se puede testear sin red
  (minimizan f(w) = ½(w − 3)²).
- Uno por neurona porque los pesos viven en cada neurona; uno solo para toda la red obligaba a juntarlos
  en un arreglo, un refactor mucho más grande, con el mismo resultado. `t` de Adam cuenta actualizaciones
  (batches), no épocas.
- Con `gd` la red da idéntico a antes del cambio: se verificó comparando `epochs.csv` de XOR (`[2,2,1]` y
  `[2,3,2,1]`, 6 seeds) y fraude, antes y después.
- Limitación: con `initial_weights` el estado del optimizador (m, v, S, Δw anterior) arranca en 0; retomar
  con Adam no es exactamente seguir la misma corrida.

## Signo de los pasos: d = −∂E/∂w, así que todo suma

**Qué:** momentum Δw = α·Δw_prev + η·d; RMSProp S = γS + (1−γ)d², Δw = η·d/√(S+ε); Adam con m y v de d y
corrección de sesgo, Δw = η·m̂/(√v̂+ε). Todos se suman a los pesos.

**Por qué:** el paper de Adam resta porque usa g = +∂E/∂w. Con d = −g, m cambia de signo y v no (está al
cuadrado), así que el paso queda con +. Es el error más fácil de cometer: hay un test que pide que con
d > 0 el peso suba, y otros con los números de la clase (momentum 0.1, 0.19, 0.271…; primer paso de Adam =
η para gradientes de 100, 1 y 0.01).

## η adaptativo: quinto optimizador, sobre el E de train

**Qué:** `adaptive_eta` da el paso de `gd`, y una vez por época `optimizer/eta_schedule.c` mira el E de
train: tras `eta_patience_up` épocas seguidas bajando, η += `eta_increase`; tras `eta_patience_down`
subiendo, η ×= (1 − `eta_decrease`). Un E igual al anterior corta las dos rachas. `epochs.csv` guarda en
la columna `eta` el η con el que se entrenó cada época.

**Por qué:**
- Sube sumando y baja multiplicando (clase 12.1): un η demasiado grande puede divergir, uno chico solo
  es lento.
- E de train, no de validación: si η se ajustara mirando validación, la validación pasaría a ser parte del
  entrenamiento. Se mide sobre todo el train al final de cada época (ya se calculaba), no muestra a
  muestra, que en online oscila sola.
- "Igual" no cuenta como subir: en la meseta del XOR, GD repite E exacto cientos de épocas, y contarlo
  como subida partiría η a la mitad una y otra vez hasta casi 0.
- En fraude llega al plateau en 24 épocas contra 68 de GD con η fijo (mismo error final); en el plateau η
  oscila solo entre ~0.001 y ~0.002.

## Hiperparámetros del optimizador: obligatorios, sin default

**Qué:** cada optimizador exige exactamente sus claves (`momentum`; `rmsprop_decay` y
`optimizer_epsilon`; `adam_beta1`, `adam_beta2` y `optimizer_epsilon`; `eta_increase`, `eta_decrease`,
`eta_patience_up` y `eta_patience_down`). Si falta una, el error sugiere el valor típico de la clase
(0.9, 0.999, 1e-8, 0.5, 5); una clave de otro optimizador es un error. Sin `optimizer` es `gd`, así que
los configs viejos andan igual.

**Por qué:**
- Un default en 0 sería un error silencioso (momentum con α = 0 es GD). Un default "de la clase"
  correría, pero el `config.json` de la corrida no diría con qué valores entrenó.
- La tabla de qué clave va con qué optimizador vive en `io/config.c`, no en `optimizer/`: los nombres de
  las claves del JSON son cosa del config; si no, el optimizador dejaría de ser genérico. Un test chequea
  que los nombres de las dos listas coincidan.

## Comparación de optimizadores (Ej. 2): cada uno con su mejor η

**Qué:** etapa 1, una serie de η por optimizador (`analysis/series_eta_*.json`, 4 valores × 3 seeds),
con grillas a la escala de cada uno: GD 0.001–0.05, momentum 10 veces más chica, RMSProp y Adam alrededor
de 0.001. Etapa 2, los cinco con su mejor η. `analysis/plots_eta_sensitivity.py` grafica accuracy de
validación contra η, una línea por optimizador, y elige el mejor η de cada uno.

**Por qué:**
- El mismo η no significa lo mismo: en GD el paso es η × gradiente, en momentum (α = 0.9) crece hasta
  ×10 y en Adam/RMSProp cada peso se mueve ≈ η. Con un único η se compararía el η, no el método.
- Mejor η por accuracy de validación (clasificación, y lo que pide el Ej. 3), con la validación separada
  de `digits.csv`: `digits_test.csv` no se usa para elegir nada. Empate: el η más chico. Si el mejor es el
  borde de la grilla, se agrega un valor más allá.
- Fijo en todas: datos, `[64]` logistic, online con shuffle, 50 épocas sin `tolerance` (mismo trabajo
  para todos) y las mismas seeds (mismos pesos iniciales). Solo se busca η; el resto, típicos de la clase.
- El gráfico de sensibilidad dice además qué tan delicado es elegir η en cada optimizador.
- Ya se vio: momentum con α = 0.9 da casi lo mismo que GD con η 10 veces más grande (el paso η/(1−α)):
  en dígitos el gradiente es suave y momentum solo acelera. En XOR `[2,2,1]` (`series_optimizer_xor.json`, 6 seeds,
  medido el 4/10 sobre `4259949`) convergen GD 2, momentum 5, RMSProp 3 y Adam 3. GD queda en una meseta
  (MSE ≈ 1, contesta 0 a todo) en 4 de 6 seeds; RMSProp cae en una meseta una vez, y los demás fallos
  son un mínimo local (MSE ≈ 0.5), del que ningún optimizador garantiza salir.
