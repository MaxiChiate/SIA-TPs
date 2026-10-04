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

Compila el binario si hace falta. Solo usa la biblioteca estándar de Python.

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

"Convergió" es que cumplió el criterio de corte (`tolerance`, o cero mal clasificadas con `sign`); sin
criterio en el config queda vacío. Una corrida que cortó antes queda en las curvas con su último valor.
