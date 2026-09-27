# TP3 SIA — Perceptrón simple y multicapa

Contexto vivo del TP3: **dónde está el TP hoy**. Se sobrescribe, y arranca cada sesión nueva
desde acá — así se puede limpiar el chat sin perder lo decidido.

Materia: Sistemas de Inteligencia Artificial (ITBA), 2° cuatrimestre 2026, Grupo 9.
Enunciado: `docs/Enunciado TP3 - 2Q 2026.pdf`.

## Estado

**Primera neurona en C.** Perceptrón simple que entrena y valida sobre CSVs; sin tests ni
multicapa todavía. Lo que existe:

```
docs/Enunciado TP3 - 2Q 2026.pdf
neuron/                          # C11 + make; README.md explica cómo correrlo
  main.c                         # carga config y datasets, entrena, valida
  neuron.c/h                     # la neurona: pesos dimensionados en runtime (n_inputs + 1)
  activation/                    # sign, lineal, tanh (θ y θ'), elegidas por nombre
  io/                            # config.json (JSON plano) y datasets CSV
  config.json.example            # se versiona este; config.json está gitignoreado
```

`n_inputs` no es global: lo trae cada neurona, y se deduce de las columnas del CSV (entradas
primero, ζ en la última). Así la misma neurona sirve de bloque para el multicapa. `build/` y
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

- **Diseñar el multicapa**: backpropagation y las arquitecturas `[2,2,1]` y `[2,3,2,1]`. El
  pseudocódigo actual cubre únicamente el perceptrón simple.
- **Llevar a `neuron/` lo decidido que falta**: `batch_size`, rosenblatt vs. gradiente según la
  activación, guardar el mejor error, criterio de convergencia, métricas por época, `logistic`.
  Hoy `neuron_train_by_epoch` corre `epochs` épocas online fijas.
- La seed se usa con `srand`/`rand` en `main.c`, no con un RNG inyectado como pide la convención.
- **Conseguir los datasets**: `transactions.csv`, `digits.csv`, `digits_test.csv` no están en
  el repo.
- Ejercicio 1 y Ejercicio 2 completos (son los entregables).
- Presentación.

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
