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

Hasta 8 variantes por serie (un color cada una). Se puede variar cualquier clave del config.

Las series son sobre dígitos, con `neuron/config.json.digits.example` de base: train
`more_digits_prepared.csv`, validación `digits_test_prepared.csv`, `logistic` (ζ one-hot en 0/1),
`[64]`, η = 0.01 online, 50 épocas, 3 seeds. Para entrenar con `digits_prepared.csv`, pisar
`train_dataset` en el `set` de la serie (ojo: no tiene ningún 8).

- `series_eta.json`: tasa de aprendizaje.
- `series_architecture.json`: `hidden_layers`.
- `series_batch_size.json`: online y mini-batch de 32 y 256 (con η dividido por `batch_size`, porque Δw se suma).
- `series_train_dataset.json`: `digits_prepared` contra `more_digits_prepared`.

Sobre fraude (base `neuron/config.json.fraud.example`; antes hay que correr
`python3 scripts/prepare_fraud_dataset.py`; train y validación son el dataset completo):

- `series_fraud_activation.json`: perceptrón lineal contra logistic, con varios η.
- `series_fraud_capacity.json`: logistic sin y con capas ocultas, para ver si el perceptrón simple
  ya agotó su capacidad.

Una serie de 15 corridas tarda ~1.5 min con 20 cores y ocupa ~270 MB (cada corrida de dígitos deja
~18 MB, igual que con `make run`; ~6 MB es su `report.html`).

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
