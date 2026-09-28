# Neurona

Perceptrón en C: entrena una red sobre un dataset y la valida sobre otro. Puede ser un perceptrón
simple o multicapa según `hidden_layers` (ver [Arquitectura](#arquitectura)).

## Arquitectura

La red tiene tres partes, y solo una se configura:

- **Entradas**: tantas como columnas de entrada tenga el dataset (todas menos la última). No se
  configuran.
- **Capas ocultas**: `hidden_layers` es una lista con la cantidad de neuronas de cada capa oculta, en
  orden desde las entradas hacia la salida. Su largo es la cantidad de capas ocultas.
- **Salida**: siempre **una sola neurona**, porque el dataset tiene una sola columna ζ. No se
  configura.

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

`make run` compila si hace falta y ejecuta con `config.json`. Para usar otro archivo:

```sh
make run CONFIG=otro_config.json
# o directamente
./build/neuron otro_config.json
```

Otros targets: `make` solo compila (objetos y binario en `build/`), `make clean` borra `build/`.

## Salida

Cada corrida escribe en su propia carpeta, `results/<fecha>_<hora>_<activación>/`, y por consola
solo imprime esa ruta. Si dos corridas caen en el mismo segundo, la segunda lleva sufijo `_2`.

| Archivo           | Contenido                                                            |
|-------------------|----------------------------------------------------------------------|
| `config.json`     | Copia exacta del config con el que se corrió                         |
| `weights.csv`     | Una fila por peso: `layer`, `neuron`, `weight` (0 es el bias), `initial`, `final` |
| `predictions.csv` | Por muestra de validación: entradas (`x1`…`xn`), `zeta`, `prediction` |

Las capas y neuronas se numeran desde 1 (la capa 0 son las entradas). Es una fila por peso porque
cada capa tiene una cantidad distinta de entradas.

`results/` está gitignoreado.

## Configuración

`config.json` es un objeto JSON con todas estas claves (ninguna es opcional):

| Clave                | Tipo   | Descripción                                        |
|----------------------|--------|----------------------------------------------------|
| `train_dataset`      | string | CSV de entrenamiento                               |
| `validation_dataset` | string | CSV de validación                                  |
| `activation`         | string | `sign`, `lineal`, `tanh` o `logistic`              |
| `eta`                | número | Tasa de aprendizaje, mayor a 0                     |
| `epochs`             | entero | Épocas de entrenamiento, mayor a 0                 |
| `batch_size`         | entero | Muestras por update: 1 online, ≥ N batch, en el medio mini-batch |
| `hidden_layers`      | lista  | Neuronas por capa oculta, p. ej. `[2]`; `[]` es perceptrón simple |
| `seed`               | entero | Semilla de los pesos iniciales (uniformes en [-0.5, 0.5]) |

Todas las capas usan la misma `activation`. Para el multicapa tiene que ser derivable (`tanh` o
`logistic`): con `sign` el error no se propaga a las capas ocultas.

Se versiona solo `config.json.example`; `config.json` está gitignoreado.

## Formato de los datasets

CSV con una muestra por fila: primero las entradas y en la última columna el valor esperado (ζ).
La primera fila puede ser un encabezado, y las filas vacías se ignoran. La cantidad de entradas se
deduce de la cantidad de columnas, y entrenamiento y validación tienen que coincidir.

```
x1,x2,zeta
0.445,0.669,1.0
0.349,0.692,1.0
```

Los datasets van en `data/`, que está gitignoreado.
