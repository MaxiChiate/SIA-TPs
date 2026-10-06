# TP3 SIA — Perceptrón simple y multicapa

Contexto vivo del TP3: **dónde está el TP hoy**. Se sobrescribe, y arranca cada sesión nueva
desde acá — así se puede limpiar el chat sin perder lo decidido.

Materia: Sistemas de Inteligencia Artificial (ITBA), 2° cuatrimestre 2026, Grupo 9.
Enunciado: `docs/Enunciado TP3 - 2Q 2026.pdf`.

## Estado técnico (código)

**Multicapa en C con backpropagation.** Entrena y valida sobre CSVs; tests con `make test` (en `neuron/tests/`). XOR con
`[2,2,1]` y `tanh` (GD, η 0.1, online, 1000 épocas) converge en 2 de 6 seeds (4/6 caen en una meseta
o un mínimo local); con `[2,3,2,1]` convergió en las 6 (medido el 4/10). Lo que existe:

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
  prepare_digits_ex3.py          # Ejercicio 3: unión, validación apartada, centrado y aumento de datos
  perturb_dataset.py             # ruido gaussiano (y clip) sobre las entradas de cualquier CSV preparado, con seed
  run_error.py                   # métricas de error de una corrida
  run_report.py                  # report.html de la corrida (lo llama make run): curva, gráficos, tablas
  report_server.py               # make serve: reporte de la última corrida en localhost, se recarga solo
analysis/                        # README.md explica cómo correrlo
  sweep.py                       # serie de corridas variando un parámetro × seeds, en paralelo -> summary.csv
  sweep_report.py                # report.html de la serie: curvas promedio por variante, resultado final por seed
  series_*.json                  # una serie por pregunta (fraude, optimizadores, arquitectura, Ejercicio 3); la tabla está en analysis/README.md
  fraud_threshold.py             # métricas (precisión, recall, PR-AUC) y umbral del TinyModel, elegido en validación
  fraud_calibration.py           # calibración (Platt, isotónica) de la salida del TinyModel contra flagged_fraud
  fraud_split_variability.py     # cuánto cambian el umbral y las métricas con otros splits
  digits_ensemble.py             # accuracy del promedio de las salidas de varias redes de dígitos (o de un modelo)
  model.py                       # modelo = red o ensemble ya entrenado (models/*.json): forward en Python y evaluación en C (epochs 0)
  models/                        # ex2_single, ex2_ensemble, ex3_single, ex3_ensemble: qué corridas forman cada modelo
  robustness.py                  # accuracy de modelos con ruido gaussiano sobre un dataset (σ × seeds de ruido) -> robustness.csv
  paired_stats.py                # test de permutación pareado, bootstrap y Holm (stdlib; lo usan plots_compare y robustness)
  attribution.py                 # mapas de atribución (saliency, grad×input, integrated gradients, oclusión) -> attributions.csv
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

**Ejercicio (validación)** — el enunciado dice que **no se presenta**, pero fija el contrato de cada módulo. Los cuatro
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

**Ejercicio 2 — Dígitos manuscritos.** Clasificación 0–9 con perceptrón multicapa. `digits.csv` para
aprendizaje y `digits_test.csv` para generalización. Preguntas: (a) ¿cómo evalúo el desempeño del sistema?,
(b) ¿qué variantes hago para encontrar la solución? Como **mínimo**: variantes de tasa de aprendizaje, de
arquitectura y de mecanismos de optimización (y otros hiperparámetros si se quiere). **Aclaración: `digits.csv`
se usa tanto para ajustar parámetros como hiperparámetros; `digits_test.csv` es el «mundo real» (equivale a poner
el modelo en producción) y no se usa para elegir nada.** Lo mismo vale para el Ejercicio 3.

**Ejercicio 3 — Más datos, meta 98 %.** La primera iteración no fue satisfactoria: el cliente pide **accuracy
≥ 98 %** y pone a disposición `more_data_digits.csv` (en el repo, `more_digits.csv`, el que sí tiene 8).
(a) ¿Cuál es el mejor resultado con el dataset nuevo? (b) ¿Qué técnicas se usaron para mejorar respecto del caso
anterior? (c) Además de las técnicas propias, ¿qué otros factores influyeron en el cambio de rendimiento entre
este ejercicio y el anterior?

**Opcionales** (no arrancar antes de tener lo obligatorio). *Ejercicio 1:* ReLU en el no lineal y su efecto en
las conclusiones (práctico); feature engineering sobre el dataset de fraude: qué otros features construir y
cuáles descartar (teórico); calibración de probabilidades (teórico). *Ejercicios 2 y 3:* robustez al ruido, p. ej.
ruido gaussiano sobre las imágenes de generalización (práctico); interpretabilidad de la red con métodos de
atribución (práctico).

**Recomendaciones del enunciado** (no obligatorias): operaciones matriciales para el rendimiento; reportar
progreso al correr; configuración extensible y guardada; guardar y levantar un modelo para seguir entrenando
(`initial_weights`); separar la información de cada experimento del análisis (gráficos, tablas).

## Diseño de la red — lo cerrado (el detalle y el porqué están en `DECISIONS.md`)

- **Una sola implementación para los cuatro perceptrones**: capas de neuronas en C (`network.c`, `neuron.c`); el simple es
  `hidden_layers: []`. **Una sola activación para toda la red** (`sign`, `lineal`, `tanh`, `logistic`, `relu`): por eso ReLU en
  las ocultas con salida logistic no se puede combinar.
- **El bias es `weights[0]`**, con entrada fija 1: se actualiza con la misma fórmula que el resto. Convención `w += Δw`.
- **Backprop acumula `d = −∂E/∂w` sin η** (primero todos los δ, después los pesos) y **el optimizador decide el paso**
  (`optimizer/`: `gd`, `momentum`, `rmsprop`, `adam`, `adaptive_eta`; genérico, uno por neurona). El escalón no tiene rama
  aparte: `sign_prime` devuelve 1 y la regla delta da exactamente la de Rosenblatt.
- **`batch_size` unifica online (1), mini-batch y batch completo (N)** en un solo camino. `shuffle` por época es opcional.
- **Se guarda la mejor época de train, no la última**; convergencia: cero mal clasificadas con `sign`, `tolerance` opcional con el resto.
- **El error se mide en una pasada aparte al final de cada época** (MSE, MAE y máx |e|; E = ½·Σ(ζ − O)²); validación y train son dos curvas.
- **Hiperparámetros del optimizador sin default** en el config: cada `config.json` de corrida dice con qué valores entrenó.
- Pesos iniciales aleatorios uniformes en [−0.5, 0.5] con el RNG propio inyectado (una instancia por corrida).

## Estado de la entrega

**Los tres ejercicios están resueltos; la presentación está armada. Lo que queda es opcional o de revisión.** Los números
de cada resultado, con su porqué, están en `DECISIONS.md` (una entrada por decisión). Resumen:

- **Ejercicio 1** (fraude, `neuron/data/fraud_dataset.csv`, el `transactions.csv` del enunciado): exploración
  (`scripts/explore_fraud_dataset.py`); parte 1 con todo el dataset: la logistic (R² 0.881) gana al lineal (0.714) y
  una capa oculta casi no suma; ReLU sin capa oculta rinde como el lineal. Parte 2: split estratificado 70/15/15,
  6 entradas (sin `timestamp`, `device_screen_resolution`, `time_since_last_login_s`), **umbral 0.78** (mediana de
  10 splits; el 0.82 del split 1 era frágil), calibración (Platt/isotónica: ECE de 0.31 a ≤ 0.02). Opcional que falta:
  feature engineering (teórico: qué features construir).
- **Ejercicio 2** (solo `digits.csv`; el enunciado reserva `digits_test.csv` como «mundo real»): η por optimizador,
  cinco optimizadores con 10 seeds (GD, momentum y η adaptativo se igualan y superan a RMSProp y Adam), arquitectura
  `[64]`. En test 86.3 ± 0.2 %: el 8 no está en `digits.csv`.
- **Ejercicio 3** (`more_digits.csv` = el `more_data_digits.csv` del enunciado): **98.7 % en test** (meta 98 %) con la
  unión de `digits.csv` + `more_digits.csv`, `[512]`, aumento de datos (desplazamientos ±2 px, rotaciones ±10°) y
  ensemble de 9 redes. Búsqueda con una validación apartada de la unión; **test mirado una sola vez**.
- **Presentación**: Artifact https://claude.ai/artifact/NpkJsGnWfG1tzxKzwyiywZ (privado), una sección por ejercicio
  más un anexo con la validación (el enunciado dice que esa no se presenta). **La fuente es el Artifact**: se lee con la
  herramienta Artifact (`action: read`) y se republica con la misma `url`; los gráficos los genera
  `analysis/plots_presentation.py` como HTML de diapositiva y se pegan en los archivos de cada slide. Hay una copia vieja
  en Google Slides del usuario que **no se puede editar** desde acá (no hay conector de edición); si se entrega desde
  Drive hay que volver a exportar desde el Artifact. **Ojo:** desde la cuenta de Magdalena ese Artifact figura como de
  otra organización y no se puede editar (6/10); lo tiene otra persona del equipo.
- **Opcionales de los Ejercicios 2 y 3 (hechos)**: robustez al ruido gaussiano y atribución, con los cuatro modelos de
  `analysis/models/`. Resultados en `DECISIONS.md` («Robustez al ruido», «Interpretabilidad»); plan y estado en
  `docs/digits_optionals_roadmap.md`. Diapositivas con notas para el orador en un deck aparte, con el mismo estilo:
  https://claude.ai/artifact/7ZPzZRoJbMGLBHiLLpgNPH (privado, cuenta de Magdalena), 8 diapos pensadas como 26–33 de la
  presentación (entre «Las tres preguntas» y «Conclusiones»).

## Pendiente

- **Pasar las 8 diapos de los opcionales a la presentación principal** (lo hace quien tenga acceso de edición), y al
  hacerlo: agregar «Opcionales: ruido e interpretabilidad» a la agenda, renumerar desde Conclusiones (pasa a 34) y sacar
  de las notas de Conclusiones la frase «Pendientes del enunciado: los opcionales de robustez al ruido e
  interpretabilidad».
- Opcional del Ejercicio 1: feature engineering (teórico).
- Extensión posible de la robustez: ruido como aumento de datos (σ elegido con una validación con ruido, nunca con el
  test); el hallazgo de los unos que van a 8 lo motiva.
- **Revisión visual de la presentación**: nunca se renderizó ni se miró; la hace el usuario. Las diapositivas más cargadas
  son la 10, 11, 17 y 22.
- Cualquier cambio de resultados: actualizar `DECISIONS.md`, este archivo y el Artifact a la vez.

## Cómo reproducir (los resultados no se versionan)

`analysis/results/` y `neuron/results/` están gitignoreados: **los números de `DECISIONS.md` y de la presentación salen de
corridas que hay que repetir si se pierden**. Todo es determinista (misma seed y config, mismo resultado). Con el binario
compilado (`cd neuron && make`) y `python3` sin dependencias (solo `plots_main.py` pide plotly):

1. Datos (a `neuron/data/`, gitignoreado): `python3 scripts/prepare_fraud_dataset.py`; `python3 scripts/prepare_digits_dataset.py`;
   `python3 scripts/prepare_fraud_split.py --seed 1 --name fraud_drop3 --drop timestamp device_screen_resolution time_since_last_login_s`
   (y las variantes de `analysis/README.md`); `python3 scripts/prepare_digits_ex3.py --name ex3_base --seed 1`
   (más `ex3_c --center`, `ex3_a2 --augment 2`, `ex3_ca2 --center --augment 2`, `ex3_a4 --augment 4`).
2. Series: `python3 analysis/sweep.py analysis/series_<nombre>.json --no-run-reports` (la tabla de series está en
   `analysis/README.md`). Tiempos: las de fraude, segundos; las de optimizadores en dígitos, ~1 min; las del Ejercicio 3
   con `[256]` o más y datos aumentados, **10 a 17 min por corrida** (9 en paralelo).
3. Evaluación y gráficos: `analysis/fraud_threshold.py`, `fraud_calibration.py`, `fraud_split_variability.py`,
   `digits_ensemble.py`, `plots_presentation.py` (ver `--help` de cada uno).

## Trampas conocidas

- **`sweep.py`: el `set` de una variante pisa el `set` de la serie.** Una vez se evaluó el «test» sobre la validación por
  eso. Antes de leer números de una evaluación final, comprobar el `validation_dataset` de cada `config.json`.
- `sweep.py` admite como máximo 8 variantes por serie. Un config no puede tener `validation_split` y `validation_dataset`.
- **`digits_test.csv` no se usa para elegir nada** (Ejercicios 2 y 3): hiperparámetros con validación apartada del
  entrenamiento, test una sola vez al final. Las series viejas de dígitos (`series_eta`, `series_architecture`, etc.)
  usan `digits_test` como validación: sirven para explorar, no para elegir.
- Los scripts de `scripts/` y `analysis/` usan solo la librería estándar de Python (plotly solo para `plots_main.py`): no hace falta instalar nada. Los comandos de ejemplo de este archivo son de un shell POSIX; si algo no se comporta igual en otro shell, usar Python o comillas explícitas.
- La carpeta de trabajo del Artifact está en un directorio temporal que no sobrevive: no es fuente de verdad.
- Otras personas del equipo empujan a la misma rama (`dev-perceptron`): hacer `git fetch` y `git pull --rebase` antes de pushear.

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
- Commits chicos y atómicos, con mensaje de una sola línea y el trailer `Co-Authored-By` que indique la sesión.
- **Nunca `git push` sin confirmación explícita, cada vez** (el usuario suele confirmar con «dale, pusheá»).
- No se trabaja en `main`: rama `dev-perceptron`.
