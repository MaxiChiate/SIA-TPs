# Análisis: series de corridas

Corre la misma red variando un parámetro, con varias seeds por variante, y arma un reporte que las
compara. Cada corrida es una corrida normal de `neuron/build/neuron`, con su propio `report.html`.

```sh
python3 analysis/sweep.py analysis/series_eta.json             # desde TP3/
python3 analysis/sweep.py analysis/series_eta.json --dry-run   # solo muestra el plan
python3 analysis/sweep.py analysis/series_eta.json --workers 4 # corridas en paralelo (default: todos los cores)
python3 analysis/sweep.py analysis/series_eta.json --no-run-reports  # sin el report.html de cada corrida
python3 analysis/sweep_report.py [analysis/results/<serie>]    # regenera el reporte (default: la última)
```

Compila el binario si hace falta. `sweep.py` solo usa la biblioteca estándar de Python.

## La serie

Un JSON por serie. Las claves que empiezan con `_` se ignoran (sirven de comentario).

| Clave         | Descripción |
|---------------|-------------|
| `base_config` | Config de la red, relativo al JSON de la serie (p. ej. `../neuron/config.json.xor.example`). Los datasets se resuelven contra `neuron/`, como en `make run` |
| `set`         | Opcional. Claves del config que se pisan en todas las corridas |
| `vary` + `values` | La clave que varía y sus valores: una variante por valor |
| `variants`    | En lugar de `vary`: lista de `{"label", "set"}`, para variantes que cambian más de una clave (p. ej. `batch_size` junto con `eta`) |
| `seeds`       | Seeds de cada variante; todas las variantes usan las mismas, así la diferencia no son los pesos iniciales |
| `workers`     | Opcional. Corridas en paralelo |
| `title`       | Opcional. Cómo nombran los gráficos a la serie; sin él lo deducen de lo que varía, y con dos perillas a la vez (η junto con `batch_size`) deducen mal |

Hasta 8 variantes por serie (un color cada una). Se puede variar cualquier clave del config.

## Series existentes

Las primeras series con 3 seeds; las marcadas con (10) usan 10 seeds.

**Dígitos** (Ejercicios 2 y 3). Ojo: las series de esta tabla hasta `series_depth` parten de `more_digits` y usan `digits_test` como validación (sirven para explorar, no para elegir hiperparámetros del Ejercicio 2: el enunciado reserva `digits_test` como «mundo real»). Base: `neuron/config.json.digits.example`, es decir train `more_digits_prepared.csv`,
validación `digits_test_prepared.csv`, `logistic`, `[64]`, η = 0.01 online, 50 épocas.

| Serie | Qué varía | Pregunta |
|---|---|---|
| `series_eta` | η: 0.001, 0.005, 0.01, 0.05, 0.1 | ¿Qué tasa de aprendizaje converge mejor? |
| `series_architecture` | `hidden_layers`: `[16]`, `[32]`, `[64]`, `[128]`, `[64, 32]` | ¿Más neuronas ayudan? ¿Una capa ancha o dos? |
| `series_batch_size` | online, mini-batch de 32 y de 256 (η dividido por `batch_size`, porque Δw se suma) | ¿Cuánto cambia el régimen de actualización? |
| `series_train_dataset` | train: `digits_prepared` o `more_digits_prepared` (el primero no tiene ningún 8) | ¿Cuánto afecta el dataset de entrenamiento? |
| `series_activation` (10) | logistic (η 0.01), tanh (η 0.01) y lineal (η 0.001); sin ReLU: con una sola activación para toda la red no aprende en dígitos | ¿Cuánto importa la no linealidad? |
| `series_shuffle` (10) | online y mini-batch de 32, con y sin `shuffle` | ¿Cambia algo mezclar las muestras en cada época? |
| `series_depth` (10) | `hidden_layers`: `[96]`, `[64, 32]`, `[48, 32, 16]`, `[32, 32, 32]` | ¿Qué pasa con las mismas neuronas repartidas en más capas? |
| `series_eta_{gd,adaptive,momentum,rmsprop,adam}` y `series_eta_edges*` | η de cada optimizador, ampliando la grilla hasta el pico (base `neuron/config.json.digits_optimizers.example`: validación = 20 % de `digits_prepared`) | ¿Cuál es el mejor η de cada optimizador? |
| `series_optimizer` y `series_optimizer_test` (10 seeds) | los cinco optimizadores, cada uno con su mejor η; la segunda entrena con `more_digits` y evalúa sobre `digits_test` (`neuron/config.json.digits_test.example`) | ¿Hay un optimizador mejor? |
| `series_optimizer_digits_test` (10 seeds) | igual que `series_optimizer`, pero entrenando solo con `digits_prepared` y evaluando sobre `digits_test` (`neuron/config.json.digits_only_test.example`) | Ejercicio 2: ¿cuánto rinde en el «mundo real» sin el 8? |
| `series_architecture_digits` (5 seeds) | `hidden_layers`: `[]`, `[16]`, `[32]`, `[64]`, `[128]`, `[64, 32]`, con η adaptativo; validación = 20 % de `digits_prepared` | Ejercicio 2: ¿qué arquitectura? |
| `series_ex3_step1`, `step2`, `step3` y `series_ex3_final` (3 seeds) | Ejercicio 3: unión de datos y capacidad; centrado, aumento, épocas y η; capacidad con aumento; evaluación final en test. Antes: `python3 scripts/prepare_digits_ex3.py --name ex3_base --seed 1` (y `ex3_c --center`, `ex3_a2 --augment 2`, `ex3_ca2`, `ex3_a4 --augment 4`; base `neuron/config.json.digits_ex3.example`). Con `digits_ensemble.py` se promedian las salidas de varias corridas (o de un modelo de `models/`). Cuidado: el `set` de una variante pisa el de la serie (por eso `series_ex3_final` repite `validation_dataset` en cada variante) | ¿Cómo llegar al 98 %? |

**Fraude** (Ejercicio 1, parte 1). Base: `neuron/config.json.fraud.example`, es decir `logistic`, η = 0.001, 1000 épocas,
online, sin capas ocultas, train = validación = dataset completo. Antes hay que correr
`python3 scripts/prepare_fraud_dataset.py`.

| Serie | Qué varía | Pregunta |
|---|---|---|
| `series_fraud_activation` | lineal (η 0.0001, 0.001) contra logistic (η 0.001, 0.01, 0.1) | ¿Hay underfitting en el lineal? ¿Cuál elegir? |
| `series_fraud_capacity` | `hidden_layers`: `[]`, `[4]`, `[16]`, `[16, 8]` | ¿El perceptrón simple ya agotó su capacidad? |
| `series_fraud_relu` (10) | lineal, logistic y ReLU, sin capa oculta y con `[16]` (cada una con su η) | ¿Cambian las conclusiones con ReLU? |

**Fraude, parte 2** (generalización). Antes hay que generar el split estratificado 70/15/15
(`python3 scripts/prepare_fraud_split.py --seed 1 --name fraud_drop3 --drop timestamp device_screen_resolution time_since_last_login_s`,
y las variantes `fraud_all`, `fraud_all_log`, `fraud_drop3_log` y `fraud_drop3_f{5,10,25,50}` con `--train-fraction`).
Todas con 5 seeds, `logistic` η = 0.01, 200 épocas con shuffle, sin capas ocultas.

| Serie | Qué varía | Pregunta |
|---|---|---|
| `series_fraud_features` | 9 o 6 entradas, con y sin `log(amount)` | ¿Qué entradas usar? |
| `series_fraud_train_size` | 5, 10, 25, 50 y 100 % del train | ¿Cuántos datos hacen falta? |
| `series_fraud_final` | validación y test con el modelo elegido (6 entradas, train completo) | ¿Cómo generaliza? Se evalúa con `python3 analysis/fraud_threshold.py` |

Dos scripts más sobre ese modelo: `python3 analysis/fraud_calibration.py` (calibración de las probabilidades; mismos
argumentos que `fraud_threshold.py`) y `python3 analysis/fraud_split_variability.py --seeds 1 2 3 4 5 6 7 8 9 10 --fixed 0.78 0.80 0.82`
(repite todo con otros splits: genera `data/fraud_split<N>_*.csv` y entrena solo, sin dejar carpetas en `results/`).

Una serie de 15 corridas tarda ~1.5 min con 20 cores y ocupa ~270 MB (cada corrida de dígitos deja
~18 MB, igual que con `make run`; ~6 MB es su `report.html`). Las de dígitos con 10 seeds son 30 a 40
corridas: ~540 a 720 MB, o ~12 MB menos por corrida con `--no-run-reports`.

## Salida

`analysis/results/<serie>_<fecha>_<hora>/` (gitignoreado):

| Archivo        | Contenido |
|----------------|-----------|
| `series.json`, `plan.json` | La serie tal como se escribió, y resuelta (config base, variantes, seeds) |
| `configs/`     | El config exacto de cada corrida |
| `runs/<corrida>/` | Los archivos de siempre de una corrida, más su `report.html` |
| `summary.csv`  | Una fila por corrida: épocas, mejor época, si convergió, MSE de train y validación, MAE, máx \|e\|, aciertos y tiempo |
| `report.html`  | La comparación |

El reporte trae una tabla por variante (promedio ± desvío entre seeds, cuántas convergieron), las curvas
de aprendizaje de cada variante (promedio de las seeds, train o validación, con el rango entre seeds
opcional), el resultado final por variante con un punto por seed, y la lista de corridas con link a
cada reporte. Zoom en los gráficos arrastrando un rectángulo (en el de resultado final, solo en y); doble
clic vuelve.

## Modelos: redes ya entrenadas (`models/` y `model.py`)

Para los opcionales de los Ejercicios 2 y 3 (robustez al ruido, atribución), un **modelo** es una red o un ensemble
de redes ya entrenadas, descripto en `models/<nombre>.json`:

```json
{ "label": "Ej. 3 — ensemble de 9", "runs": ["series_ex3_final/000_a2-512_seed1", "..."] }
```

Cada corrida es `<serie>/<corrida>`: se toma la ejecución más reciente de esa serie en `results/` que la tenga, así
que el JSON sigue sirviendo cuando se repite la serie (también acepta la ruta a una carpeta de corrida). La salida
del modelo es el promedio de las salidas de sus redes; una red sola es un ensemble de 1.

| Modelo | Corridas | Serie que hay que haber corrido |
|---|---|---|
| `ex2_single` | `[64]`, η adaptativo, seed 1 | `series_optimizer_digits_test` |
| `ex2_ensemble` | las 10 seeds de η adaptativo | ídem |
| `ex3_single` | `a2 [512]`, seed 1 | `series_ex3_final` |
| `ex3_ensemble` | las 9 del resultado final | ídem |

`model.py` los carga (pesos, `hidden_layers` y `activation` del `config.json` de cada corrida) y ofrece `predict`
(forward en Python, para pocas muestras) y `evaluate` (el binario con `epochs: 0`, una vez por red y en paralelo, para
un CSV entero). No sabe de dígitos: entradas son las columnas `x*`, salidas las `zeta*`. Como script, chequea un
modelo sobre un dataset: accuracy de cada red y del ensemble, la evaluación en C contra el `predictions.csv` de cada
corrida (si fue sobre ese dataset) y el forward en Python contra el C:

```bash
python3 analysis/model.py analysis/models/ex2_ensemble.json --dataset data/digits_test_prepared.csv
```

`digits_ensemble.py` promedia con lo mismo, a partir de `predictions.csv` o de un modelo:

```bash
python3 analysis/digits_ensemble.py --model analysis/models/ex3_ensemble.json --dataset data/ex3_base_test.csv  # 98.72 %
```

### Robustez al ruido (`robustness.py`)

`scripts/perturb_dataset.py` suma ruido gaussiano N(0, σ²) a las entradas de cualquier CSV preparado (nunca a las
`zeta_*`), con `--seed` obligatoria y `--clip MIN MAX` opcional. Con la misma seed, todos los σ usan las mismas normales
estándar: el ruido de una seed a σ 0.2 es el de σ 0.1 multiplicado por 2. `robustness.py` lo usa una vez por σ y seed
de ruido y evalúa encima cada modelo (cada red una sola vez aunque esté en dos modelos):

```bash
python3 analysis/robustness.py --models ex2_single ex2_ensemble ex3_single ex3_ensemble \
    --dataset data/digits_test_prepared.csv --gaussian 0 0.05 0.1 0.2 0.3 0.5 --noise-seeds 1-10 --clip 0 1   # ~5 min
```

Escribe `results/robustness_<fecha>_<hora>/`: `robustness.csv` (`model, label, sigma, noise_seed, accuracy,
accuracy_0..accuracy_9`: una fila por modelo × σ × seed; σ 0 una sola vez, como seed 0) y `run.json` (los argumentos).
Imprime la media ± desvío entre seeds y, en cada σ, la diferencia entre cada par de modelos con el test de permutación
pareado por seed de ruido (`paired_stats.py`, el mismo de `plots_compare.py`). Los gráficos (`robustness_curve`,
`noise_examples`, `robustness_by_class`) los arma `plots_presentation.py` a partir de la última corrida.

### Atribución (`attribution.py`)

Mapas de qué entradas pesaron en la clase que predice el modelo: `saliency`, `grad_input`, `integrated` (integrated
gradients) y `occlusion` (parches con `--input-shape 28x28`). Forward y backward en Python sobre los pesos de
`model.py`. **Antes de mirar mapas, `--self-check`**: compara el forward con el C, el gradiente con diferencias
finitas y la suma de integrated gradients con O_k(x) − O_k(0).

```bash
python3 analysis/attribution.py --models ex2_single ex2_ensemble ex3_single ex3_ensemble --dataset data/digits_test_prepared.csv --self-check
python3 analysis/attribution.py --models ex2_single ex2_ensemble ex3_single ex3_ensemble --dataset data/digits_test_prepared.csv \
    --samples per-class:1 --input-shape 28x28 --name per_class                                  # ~40 s
python3 analysis/attribution.py ... --samples per-class:50 --methods saliency grad_input --name class_means
python3 analysis/attribution.py ... --samples errors:10 --input-shape 28x28 --name errors
```

Escribe `results/attribution_<name>_<fecha>_<hora>/attributions.csv` (`model, sample, true, predicted, method,
a1..a784`) y `run.json`. `plots_presentation.py` toma la última de cada nombre: `attribution_methods` y
`attribution_models` (de `per_class`), `attribution_class_means`, `attribution_errors` y `first_layer_weights` (pesos
de la primera capa de `ex2_single`, sin corrida previa).

## Gráficos de las series

Además de ese `report.html`, `plots_main.py` arma los gráficos de plotly de las series, como en TP2: una
página por gráfico y un `index.html` que los reúne. Necesita plotly (`pip install -r analysis/requirements.txt`).

```sh
python3 analysis/plots_main.py                         # todas las series de analysis/results
python3 analysis/plots_main.py analysis/results/<serie> --tablas   # una sola, y las tablas por terminal
python3 analysis/plots_main.py --x elapsed_s --abrir   # además contra segundos de entrenamiento; abre el índice
```

Escribe en la carpeta de cada serie, más `analysis/results/index.html` (la portada con todas las series). Se
saltea las series cuyo índice ya es más nuevo que sus CSVs (`--force` las redibuja). Las explicaciones están
detrás de botones (i) en el índice.

| Archivo | Qué muestra |
|---|---|
| `validation.html`, `train.html` | MSE por época de cada variante, promedio de las seeds con barras de rango min-max |
| `gap.html` | validación menos train: la brecha de generalización |
| `compare_final.html`, `compare_distribution.html` | MSE de validación final: un punto por seed, y el boxplot |
| `compare_paired.html` / `compare_ranking.html` | con 2 variantes, la diferencia pareada por seed; con 3 o más, el puesto de cada una dentro de cada seed |
| `compare_speed.html` | épocas hasta un error de validación que todas las corridas alcanzan |
| `compare_tradeoff.html` | segundos de entrenamiento contra MSE de validación |
| `compare_generalization.html` | MSE de train contra MSE de validación, sobre la diagonal |
| `compare_accuracy.html` | aciertos de validación, si la serie los tiene |
| `plotly.min.js` | el plotly.js que comparten los gráficos (un solo archivo por serie, no uno por gráfico) |

Las curvas se leen de `runs/<corrida>/epochs.csv`, así que borrar `runs/` para ahorrar disco también borra las
curvas. Una corrida que cortó antes de tiempo se completa con su último valor. Las tablas del índice (y de
`--tablas`) traen media, desvío y puesto por variante, la velocidad, y la comparación de cada variante contra
la mejor con test de permutación pareado, IC95% bootstrap y corrección de Holm.

Para agregar una prueba nueva: un `series_*.json` (ver arriba), `sweep.py` y `plots_main.py`. Si la serie
varía una clave que no tiene nombre en `KNOB_NAMES` (`plots_data.py`), el título usa la clave tal cual; se
puede poner un `"title"` en el JSON de la serie.

"Convergió" es que cumplió el criterio de corte (`tolerance`, o cero mal clasificadas con `sign`); sin
criterio en el config queda vacío. Una corrida que cortó antes queda en las curvas con su último valor.

## Gráficos para la presentación

`python3 analysis/plots_presentation.py --out <carpeta> [--confusion <predictions.csv>] [--recall <predictions.csv de digits> <predictions.csv de more_digits>]`
genera fragmentos de HTML (barras, mapa de calor y líneas, solo biblioteca estándar) a partir de las últimas series y de los
datos; se pegan en las diapositivas.
