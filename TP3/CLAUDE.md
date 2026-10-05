# TP3 SIA — Perceptrón simple y multicapa

Contexto vivo del TP3: **dónde está el TP hoy**. Se sobrescribe, y arranca cada sesión nueva
desde acá — así se puede limpiar el chat sin perder lo decidido.

Materia: Sistemas de Inteligencia Artificial (ITBA), 2° cuatrimestre 2026, Grupo 9.
Enunciado: `docs/Enunciado TP3 - 2Q 2026.pdf`.

## Estado

**Multicapa en C con backpropagation.** Entrena y valida sobre CSVs; tests con `make test` (en `neuron/tests/`). XOR con
`[2,2,1]` y `tanh` (GD, η 0.1, online, 1000 épocas) converge en 2 de 6 seeds (4/6 caen en una meseta
o un mínimo local); con `[2,3,2,1]` convergió en las 6 (medido el 4/10 sobre `4259949`). Lo que existe:

```
docs/Enunciado TP3 - 2Q 2026.pdf
neuron/                          # C11 + make; README.md explica cómo correrlo
  main.c                         # carga config y datasets, arma la red, entrena, valida
  rng.c/h                        # RNG propio (splitmix64) y shuffle; uno por corrida para pesos y shuffle, otro para el split
  network.c/h                    # capas de neuronas: forward, backprop, loop por batch
  neuron.c/h                     # la neurona: pesos (n_inputs + 1) y Δw pendiente
  activation/                    # sign, lineal, tanh, logistic, relu (θ y θ'), elegidas por nombre
  optimizer/                     # gd, momentum, rmsprop, adam y adaptive_eta (η por época); genérico, no conoce la red
  io/                            # config.json (JSON plano), datasets CSV y results/ de cada corrida
  config.json.example            # se versiona este; config.json está gitignoreado
scripts/
  prepare_fraud_dataset.py       # fraude crudo -> CSV de la red (z-score) + labels aparte (parte 1, dataset completo)
  prepare_fraud_split.py         # fraude: split estratificado train/validación/test, z-score solo de train, variantes de entradas
  explore_fraud_dataset.py       # exploración del fraude: limpieza, rangos, composición, correlaciones
  prepare_digits_dataset.py      # dígitos crudos -> x1..x784 + zeta_0..zeta_9 (one-hot)
  run_error.py                   # métricas de error de una corrida
  run_report.py                  # report.html de la corrida (lo llama make run): curva, gráficos, tablas
  report_server.py               # make serve: reporte de la última corrida en localhost, se recarga solo
analysis/                        # README.md explica cómo correrlo
  sweep.py                       # serie de corridas variando un parámetro × seeds, en paralelo -> summary.csv
  sweep_report.py                # report.html de la serie: curvas promedio por variante, resultado final por seed
  series_*.json                  # series sobre dígitos (more_digits vs digits_test): eta, hidden_layers, batch_size, train
  fraud_threshold.py             # métricas (precisión, recall, PR-AUC) y umbral del TinyModel, elegido en validación
  fraud_calibration.py           # calibración (Platt, isotónica) de la salida del TinyModel contra flagged_fraud
  fraud_split_variability.py     # cuánto cambian el umbral y las métricas con otros splits
  plots_presentation.py          # gráficos de la presentación como HTML de diapositiva (solo stdlib)
  plots_main.py                  # gráficos de plotly de cada serie + index.html (como TP2); necesita plotly
  plots_data.py / plots_compare.py / plots_index.py / plots_style.py   # carga y bandas, estadística pareada, índice con modales (i), paleta
```

Cada corrida guarda `epochs.csv`: E y MSE de train y validación después de cada época, y los
segundos de entrenamiento acumulados (`elapsed_s`). Corta antes si converge (`sign`: cero mal
clasificadas; resto: MSE de train < `tolerance`, opcional) y la red queda con los pesos de la
mejor época de train, no de la última. El progreso sale por stderr (stdout es solo la
ruta, que lee `make run`). `initial_weights` (opcional) sigue entrenando desde los pesos finales de
otra corrida. `shuffle` (opcional) mezcla las muestras en cada época; `validation_split` + `split_seed`
(opcionales) arman la validación como una parte al azar de `train_dataset`, en lugar de un
`validation_dataset`.

`n_inputs` no es global: lo trae cada neurona, y se deduce de las columnas del CSV (entradas
primero, ζ al final). Las ζ son las últimas columnas del encabezado que se llaman `zeta*` (si no hay
ninguna, solo la última), y hay una neurona de salida por cada una. La red es
`{n_inputs, hidden_layers..., n_outputs}`; con `hidden_layers: []` y una ζ es el perceptrón simple y
da exactamente lo mismo que la neurona sola. `build/` y
`data/` están gitignoreados.

Se trabaja en la rama `dev-perceptron`.

## Qué pide el enunciado

Cuatro herramientas: perceptrón simple **escalón**, **lineal** y **no lineal**, y perceptrón
**multicapa**.

**Ejercicio (validación)** — no se presenta, pero fija el contrato de cada módulo. Los cuatro
casos: AND lógico con escalón, ~50 muestras
de `y = x` con el lineal, ~50 de `y = tanh(x)` con el no lineal, y XOR multicapa con
arquitecturas `[2,2,1]` y `[2,3,2,1]` (conviene hacer las cuentas a mano).

**Ejercicio 1 — Knowledge distillation.** `TinyModel` que iguale la performance de `BigModel`
estimando la probabilidad de que una transacción sea fraudulenta (0 = 0%, 1 = 100%), sobre
`transactions.csv`. Dos partes:

1. Comparar aprendizaje del perceptrón lineal vs. el no lineal: ¿underfitting?, ¿saturación de
   capacidades?, y elegir uno según su potencial de aprendizaje. Esta comparación usa **todas**
   las muestras del dataset.
2. Con el elegido, estudio de generalización: qué métricas y por qué, qué estrategia de
   manipulación del dataset, cómo se elige el mejor conjunto de entrenamiento, y cuál es el
   mejor modelo para el cliente — **incluyendo una recomendación de umbral de detección**.

La activación del no lineal tiene que ser adecuada al problema: la salida es una probabilidad,
así que el rango útil es `(0, 1)` → `logistic`, no `tanh`.

El enunciado insiste en explorar el dataset antes de modelar: documentación de cada columna,
rangos, composición, datos limpios o no.

**Ejercicio 2 — Dígitos manuscritos.** Clasificación 0–9 con perceptrón multicapa.
`digits.csv` para aprendizaje, `digits_test.csv` para generalización. Primera pregunta del
enunciado: cómo evaluar el desempeño del sistema.

**Opcionales** (no arrancar antes de tener lo obligatorio): ReLU en el no lineal y su efecto en
las conclusiones; feature engineering sobre el dataset de fraude; calibración de probabilidades.

## Diseño del perceptrón simple — decisiones tomadas

El pseudocódigo original se borró; lo cerrado queda acá, para no volver a discutirlo. La neurona
en C todavía no cubre todo (ver Pendiente).

- **Cuatro módulos**, frontera clara entre ellos: `activations` (θ, θ', rango), `update_rules`
  (Δw), `model` (pesos y predicción), `trainer` (loop de entrenamiento).
- **El bias va en `weights[0]`**, con entrada fija `x0 = 1` agregada por `with_bias`. Así el
  bias se actualiza con la misma fórmula que el resto de los pesos, sin caso especial.
- **Convención de update**: `w_nuevo = w_viejo + Δw`. El menos del gradiente ya está adentro
  de Δw.
- **Única bifurcación entre el escalón y el resto**: el flag `uses_gradient` de la activación
  elige entre `rosenblatt_update` y `gradient_update`. La regla del escalón **no** sale de
  derivar el error — θ' = 0 daría Δw = 0 siempre; se justifica porque mueve `h` hacia el lado
  correcto de la frontera.
- **`batch_size` unifica los tres regímenes** en un solo camino de código: 1 = online (N
  updates por época), N = batch full (1 update por época), intermedio = mini-batch. Un solo
  update por batch, acumulando Δw.
- **El trainer guarda el mejor error visto, no el último**: el error no baja monótonamente,
  una corrección puede romper otra muestra.
- **Criterio de convergencia según la activación**: `misclassified == 0` si es discreta
  (escalón), `error < tolerance` si no (con floats un 0 exacto nunca pasa).
- **Métricas por época sobre todo el dataset**, con los pesos ya actualizados, guardadas en un
  `EpochRecord` (época, error, mal clasificadas, pesos, cantidad de updates).
- `load_weights` existe para retomar un entrenamiento sin arrancar de cero.
- `decision_boundary` solo tiene sentido con 2 entradas; devuelve la recta `h = 0`.

## Pendiente

- **Dígitos**: `scripts/prepare_digits_dataset.py` los deja en one-hot (`x1..x784,zeta_0..zeta_9`) y
  la red ya entrena con 10 salidas; el reporte muestra aciertos por argmax. El reporte ya trae matriz de
  confusión y aciertos/precisión por clase (probada solo con datos sintéticos). `digits.csv` no tiene ningún 8 y tiene pocos 5 (271);
  `more_digits.csv` sí tiene 8.
- **Datasets**: ya están en `neuron/data/` (gitignoreado): `fraud_dataset.csv` (7500 filas, el
  `transactions.csv` del enunciado), `digits.csv`, `digits_test.csv`, `more_digits.csv` y
  `fraud_dataset_documentation.pdf`. `scripts/explore_fraud_dataset.py` es la exploración del
  fraude (resultados en `DECISIONS.md`).
- **Ejercicio 1**: hecho, con los opcionales de ReLU y calibración: parte 1 (lineal vs. logistic vs. ReLU) y
  parte 2 (split estratificado 70/15/15, 6 entradas, **umbral 0.78**, que depende del split: ver
  `DECISIONS.md`). Falta, si se quiere: el feature engineering (opcional).
- **Ejercicio 2**: hecho (etapas 1 y 2 con 10 seeds, ver `DECISIONS.md` y `docs/optimizers_roadmap.md`):
  GD, momentum y η adaptativo no se distinguen y superan a RMSProp y Adam; test 95.5 ± 0.4 % con η adaptativo.
- **Presentación**: Artifact con gráficos (https://claude.ai/artifact/NpkJsGnWfG1tzxKzwyiywZ); hay que
  mantenerla alineada con este archivo y con `DECISIONS.md`. Hoy no le quedan resultados pendientes; la revisión visual la hace quien la presenta.

## Convenciones

- **Todo identificador en inglés**: variables, funciones, clases, nombres de archivo y de
  directorio. La prosa (README, este archivo, docs) en español.
- Nombres de archivo descriptivos, no numerados ni abreviados.
- Los algoritmos se implementan **a mano**: nada de scikit-learn, Keras ni equivalentes para
  el perceptrón. Librerías externas solo para I/O, arrays y gráficos.
- La neurona está en C (C11, `make`): módulos por directorio, `main` corto que llama función por
  función, validaciones en helpers aparte.
- Python (si se usa, p. ej. análisis y gráficos) con type hints y dataclasses, `from __future__ import annotations`, funciones cortas,
  sin herencia profunda.
- `seed` obligatorio en todo lo que use aleatoriedad (inicialización de pesos, shuffle, splits):
  misma seed + mismo config ⇒ mismo resultado. Una sola instancia de RNG inyectada por
  parámetro; nadie llama a `random` directo.
- Resultados, CSVs e imágenes generadas van gitignoreados; se versiona el `*.example` del
  config.

## Método de trabajo

- Frenar entre bloques para revisión. Justificar cada decisión de diseño en una línea.
- **`DECISIONS.md`**: revisarlo y completarlo cada vez que se tome una decisión que puedan
  preguntar en la defensa. Una entrada por decisión, concisa y concreta: **Qué** + **Por qué**.
- Si algo tiene más de una forma razonable de resolverse, plantear las opciones en vez de
  elegir solo.
- Commits chicos y atómicos, con mensaje de una sola línea.
- **Nunca `git push` sin confirmación explícita, cada vez.**
- No se trabaja en `main`: rama `dev-perceptron`.
