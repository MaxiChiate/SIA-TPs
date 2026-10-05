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

**Dígitos** (Ejercicio 2). Base: `neuron/config.json.digits.example`, es decir train `more_digits_prepared.csv`,
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

**Fraude** (Ejercicio 1, parte 1). Base: `neuron/config.json.fraud.example`, es decir `logistic`, η = 0.001, 1000 épocas,
online, sin capas ocultas, train = validación = dataset completo. Antes hay que correr
`python3 scripts/prepare_fraud_dataset.py`.

| Serie | Qué varía | Pregunta |
|---|---|---|
| `series_fraud_activation` | lineal (η 0.0001, 0.001) contra logistic (η 0.001, 0.01, 0.1) | ¿Hay underfitting en el lineal? ¿Cuál elegir? |
| `series_fraud_capacity` | `hidden_layers`: `[]`, `[4]`, `[16]`, `[16, 8]` | ¿El perceptrón simple ya agotó su capacidad? |
| `series_fraud_relu` (10) | lineal, logistic y ReLU, sin capa oculta y con `[16]` (cada una con su η) | ¿Cambian las conclusiones con ReLU? |

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
