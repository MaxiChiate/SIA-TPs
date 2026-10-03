# Neurona

Perceptrón en C: entrena una red sobre un dataset y la valida sobre otro. Puede ser un perceptrón
simple o multicapa según `hidden_layers` (ver [Arquitectura](#arquitectura)).

## Arquitectura

La red tiene tres partes, y solo una se configura:

- **Entradas**: tantas como columnas de entrada tenga el dataset (todas menos las ζ). No se
  configuran.
- **Capas ocultas**: `hidden_layers` es una lista con la cantidad de neuronas de cada capa oculta, en
  orden desde las entradas hacia la salida. Su largo es la cantidad de capas ocultas.
- **Salida**: **una neurona por columna ζ** del dataset: una sola en general, 10 en dígitos (ver
  [Formato de los datasets](#formato-de-los-datasets)). No se configura.

Ejemplos con un dataset de 2 entradas (`x1,x2,zeta`):

| `hidden_layers` | Red resultante                                             | Notación |
|-----------------|------------------------------------------------------------|----------|
| `[]`            | Sin capas ocultas: una neurona que recibe las 2 entradas (perceptrón simple) | 2-1   |
| `[3]`           | 1 capa oculta de 3 neuronas → 1 neurona de salida          | 2-3-1    |
| `[2, 3]`        | 1ª capa oculta de 2 neuronas → 2ª de 3 → 1 neurona de salida | 2-2-3-1 |

La notación lista las neuronas por capa: entradas, ocultas y salida.

## Requisitos

`gcc` y `make`.

## Uso

```sh
cp config.json.example config.json   # la primera vez
make run
```

`make run` compila si hace falta, ejecuta con `config.json` y arma el reporte HTML de la corrida
(ver [Salida](#salida); necesita `python3`, sin dependencias). Para usar otro archivo:

```sh
make run CONFIG=otro_config.json
# o directamente
./build/neuron otro_config.json
```

Para seguir las corridas en el navegador, en otra terminal:

```sh
make serve              # http://localhost:8000; otro puerto: make serve PORT=8080
```

`/` muestra el reporte de la última corrida terminada y se recarga solo cuando termina una nueva
(pregunta cada 2 s). `/run/<carpeta>` muestra una corrida puntual, sin recargarse. El reporte se arma
desde los CSVs en cada pedido, así que también aparecen las corridas hechas con `./build/neuron`.
Escucha solo en `127.0.0.1`.

Otros targets: `make` solo compila (objetos y binario en `build/`), `make clean` borra `build/`.

## Salida

Cada corrida escribe en su propia carpeta, `results/<fecha>_<hora>_<activación>/`, y por stdout
solo imprime esa ruta. Si dos corridas caen en el mismo segundo, la segunda lleva sufijo `_2`.

Mientras entrena, el progreso va por stderr, a lo sumo una línea por segundo más la última época:

```
epoch 3/5 ( 60%)  train MSE 0.007156  validation MSE 0.02374  1.3s, ~0.8s left
```

| Archivo           | Contenido                                                            |
|-------------------|----------------------------------------------------------------------|
| `config.json`     | Copia exacta del config con el que se corrió                         |
| `weights.csv`     | Una fila por peso: `layer`, `neuron`, `weight` (0 es el bias), `initial`, `final` |
| `predictions.csv` | Por muestra de validación: entradas (`x1`…`xn`), `zeta`, `prediction` (con varias salidas, `zeta_0`… y `prediction_0`…) |
| `epochs.csv`      | Por época: `epoch` y, para `train_` y `validation_`, `error`, `mse`, `mae`, `max_error` (época 0 = pesos iniciales), y `elapsed_s` |
| `predictions_by_epoch.csv` | Por muestra de validación: `zeta` y la predicción en 11 épocas (`epoch_0` … `epoch_<epochs>`, cada 10%; con varias salidas, `epoch_<e>_<salida>`) |
| `report.html`     | Resumen para abrir en el navegador: config, curva de aprendizaje, error de validación, gráficos, pesos y predicciones |

`report.html` lo escribe `scripts/run_report.py` (lo llama `make run`; corriendo el binario directo
no se genera). Para regenerarlo: `python3 ../scripts/run_report.py [results/<corrida>]`, sin
argumento usa la última. Muestra las mismas métricas que `run_error.py`, los aciertos si ζ toma dos
valores (con varias salidas, por argmax: la salida más alta contra la ζ más alta), la curva de aprendizaje (train y validación por época, eligiendo el error), predicción vs. ζ
con un slider por época, el histograma
del error y, con una sola entrada, la curva aprendida.

En `epochs.csv`, `error` es E = ½·Σ(ζ − O)², lo que minimiza el entrenamiento; `mse` es 2E / N,
E por muestra, que es lo que se compara entre train y validación; `mae` es Σ|ζ − O| / N y
`max_error` es el peor |ζ − O|. Con varias salidas, N cuenta muestras × salidas. Se miden después de cada
época con los pesos ya actualizados (ver `DECISIONS.md`). `elapsed_s` son los segundos de
entrenamiento acumulados hasta esa época, sin contar el cálculo de estos errores.

Las capas y neuronas se numeran desde 1 (la capa 0 son las entradas). Es una fila por peso porque
cada capa tiene una cantidad distinta de entradas.

`results/` está gitignoreado.

## Configuración

`config.json` es un objeto JSON con estas claves; todas son obligatorias salvo las marcadas como
opcionales, y una clave desconocida es un error:

| Clave                | Tipo   | Descripción                                        |
|----------------------|--------|----------------------------------------------------|
| `train_dataset`      | string | CSV de entrenamiento                               |
| `validation_dataset` | string | CSV de validación                                  |
| `activation`         | string | `sign`, `lineal`, `tanh` o `logistic`              |
| `eta`                | número | Tasa de aprendizaje, mayor a 0                     |
| `epochs`             | entero | Épocas de entrenamiento, mayor a 0                 |
| `batch_size`         | entero | Muestras por update: 1 online, ≥ N batch, en el medio mini-batch |
| `hidden_layers`      | lista  | Neuronas por capa oculta, p. ej. `[2]`; `[]` es perceptrón simple |
| `tolerance`          | número | Opcional. Corta el entrenamiento cuando el MSE de train baja de este valor; sin ella (o 0) corre todas las épocas. Con `sign` se corta solo al clasificar bien todo el train |
| `seed`               | entero | Semilla de los pesos iniciales (uniformes en [-0.5, 0.5]) |
| `initial_weights`    | string | Opcional. Carpeta de una corrida anterior (o su `weights.csv`) para seguir entrenando desde sus pesos finales; sin ella, pesos al azar |

Al terminar, la red queda con los pesos de la época de menor MSE de train (no los de la última), y
`epochs.csv` llega solo hasta la última época entrenada.

Con `initial_weights`, la arquitectura (entradas, `hidden_layers` y salidas) tiene que ser la
misma que la de esa corrida. La corrida nueva numera sus épocas desde 0 (la época 0 es donde
terminó la anterior), y su `weights.csv` tiene como `initial` los pesos cargados, así que se puede
encadenar. Para agregar una clave opcional: el campo en `Config` y una fila en `FIELDS`
(`io/config.c`) con `optional` en 1; si falta, queda en cero / `""`.

Todas las capas usan la misma `activation`. Para el multicapa tiene que ser derivable (`tanh` o
`logistic`): con `sign` el error no se propaga a las capas ocultas.

Se versiona solo `config.json.example`; `config.json` está gitignoreado.

## Formato de los datasets

CSV con una muestra por fila: primero las entradas y al final el valor esperado (ζ).
La primera fila puede ser un encabezado, y las filas vacías se ignoran. Entrenamiento y validación
tienen que coincidir en la cantidad de entradas y de ζ.

```
x1,x2,zeta
0.445,0.669,1.0
0.349,0.692,1.0
```

Las ζ se deducen del encabezado: son las **últimas columnas cuyo nombre empieza con `zeta`**, y hay
una neurona de salida por cada una. Sin encabezado, o si ninguna columna se llama así, la ζ es solo la
última columna. Así se arma, por ejemplo, el one-hot de dígitos:

```
x1,...,x784,zeta_0,...,zeta_9
0,...,0.34,...,0,0,0,0,0,0,0,1,0,0
```

`scripts/prepare_digits_dataset.py` pasa `digits.csv`, `digits_test.csv` y `more_digits.csv` a este
formato (`data/<nombre>_prepared.csv`).

Los datasets van en `data/`, que está gitignoreado.

## Tests

`make test` compila `tests/test_main.c` contra todo menos `main.c` y lo corre (sin dependencias). Cubre
el RNG, las activaciones y sus derivadas, el forward y la actualización a mano, backprop contra el
gradiente numérico, full batch independiente del orden, AND/`y = x`/XOR `[2,3,2,1]`, corte por
callback, y la lectura de datasets y config.
