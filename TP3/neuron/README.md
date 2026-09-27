# Neurona

Perceptrón simple en C: entrena una neurona sobre un dataset y la valida sobre otro. Los pesos se
dimensionan en runtime según la cantidad de entradas del dataset, así que la misma neurona sirve de
bloque para el multicapa.

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
| `weights.csv`     | Pesos iniciales y finales, una fila cada uno (`w0` es el bias)       |
| `predictions.csv` | Por muestra de validación: entradas (`x1`…`xn`), `zeta`, `prediction` |

`results/` está gitignoreado.

## Configuración

`config.json` es un objeto JSON con todas estas claves (ninguna es opcional):

| Clave                | Tipo   | Descripción                                        |
|----------------------|--------|----------------------------------------------------|
| `train_dataset`      | string | CSV de entrenamiento                               |
| `validation_dataset` | string | CSV de validación                                  |
| `activation`         | string | `sign`, `lineal` o `tanh`                          |
| `eta`                | número | Tasa de aprendizaje, mayor a 0                     |
| `epochs`             | entero | Épocas de entrenamiento, mayor a 0                 |
| `seed`               | entero | Semilla de los pesos iniciales (uniformes en [-0.5, 0.5]) |

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
