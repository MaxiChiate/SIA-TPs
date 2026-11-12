# TP5 SIA: Deep Learning

Autoencoders sobre las 32 letras de 7×5 de `src/font.h` (enunciado en `docs/SIATP5.pdf`). Por ahora está hecho el
ejercicio 1.a.1: la red con encoder, código latente y decoder, configurable desde un JSON. El perceptrón multicapa, la
retropropagación y los optimizadores son los de `neuron/` (en C, sin dependencias); no hay un tipo de red aparte para el
autoencoder, es un multicapa que se entrena para devolver su entrada.

```
TP5/
  docs/SIATP5.pdf             enunciado
  src/font.h                  las 32 letras
  scripts/font_to_csv.py      font.h -> neuron/data/font.csv
  scripts/wrong_pixels.py     píxeles incorrectos por letra de una corrida
  scripts/latent_plot.py      gráfico del espacio latente de una corrida (latent.png y .svg)
  scripts/seed_sweep.py       un config con varias semillas: cuántas cumplen el objetivo y el MSE
  scripts/generate_letters.py letras nuevas decodificando puntos entre dos letras (generated.png y .svg)
  neuron/                     la red; su README documenta todas las claves del config
```

## Requisitos

`gcc` (o `clang`), `make` y `python3`. La red y `font_to_csv.py`/`wrong_pixels.py` no necesitan paquetes extra; los
gráficos usan `matplotlib` (fijado en `requirements.txt`):

```sh
python3.12 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt
```

Todo desde `TP5/`.

## Cómo correrlo

```sh
# 1. CSV de entrenamiento: 35 píxeles de entrada + los mismos 35 como zeta_* (neuron/data/font.csv)
python3 scripts/font_to_csv.py

# 2. Compilar
make -C neuron

# 3. Entrenar con la configuración de ejemplo (unos 10 s) y ver cuántos píxeles falla cada letra
cd neuron
./build/neuron config.json.autoencoder.example
cd ..
python3 scripts/wrong_pixels.py
```

El binario imprime el progreso por stderr y, por stdout, la carpeta de la corrida
(`neuron/results/<fecha>_<hora>_logistic/`). Con el ejemplo y `seed: 1`, el MSE de train termina cerca de 0,004 y las 32 letras
salen con a lo sumo 1 píxel incorrecto, que es el objetivo del enunciado:

```
píxeles incorrectos por letra: [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1]
letras con a lo sumo 1 píxel incorrecto: 32/32
```

**Ojo con la semilla.** Ese 32/32 es el de `seed: 1`. Con 10 semillas (`python3 scripts/seed_sweep.py <config>`, 30000
épocas, Adam, η = 0,001) `logistic` cumple el objetivo en 3 de 10 corridas (MSE medio 0,040, entre 0,003 y 0,132).
`neuron/config.json.autoencoder_tanh.example` es el mismo ejemplo con `tanh`: cumple en 9 de 10 (MSE medio 0,0013,
entre 0,00001 y 0,0045; la que falla deja una letra con 2 píxeles mal). Además `tanh` reparte las letras por todo el
cuadrado [-1, 1]² del espacio latente, en vez de apretarlas contra los bordes como `logistic`.

Cada corrida guarda en su carpeta el config usado, `weights.csv`, `epochs.csv` (error por época),
`predictions.csv`, `predictions_by_epoch.csv` y, si es un autoencoder, `latent.csv` (código latente de cada letra); `results/` no se versiona. `make run` de `neuron/` también quiere armar
un reporte HTML con `../scripts/run_report.py`, que todavía no está en TP5: usá el binario directo, como arriba.

## Espacio latente (1.a.3)

```sh
.venv/bin/python scripts/latent_plot.py [neuron/results/<corrida>]   # sin argumento, la última corrida
```

Lee `latent.csv` y escribe `latent.png` y `latent.svg` en la carpeta de la corrida: un punto por letra en el plano 2D,
con el nombre de la letra tomado de los comentarios de `src/font.h`.

## Letras nuevas (1.a.4)

```sh
.venv/bin/python scripts/generate_letters.py [--run neuron/results/<corrida>] [--steps 7] [o,e u,w ...]
```

Para cada par de letras decodifica puntos equiespaciados sobre el segmento que une sus códigos latentes. Los extremos
reproducen las letras originales (el script lo comprueba) y los intermedios son entradas que la red nunca vio. Por
dentro usa el binario en modo evaluación (`epochs: 0` + `initial_weights`) con `--decode puntos.csv`, que pasa cada
punto del espacio latente por el decoder y guarda `generated.csv` en la corrida. Se puede usar a mano:
`./build/neuron config.json --decode puntos.csv`, con `latent_0,latent_1` en la cabecera.

## Estudio de arquitecturas y optimizadores (1.a.2)

`python3 scripts/study_1a2.py optimizers|architectures` repite lo de abajo y agrega filas a `docs/estudio_1a2.csv`. Parte
de `config.json.autoencoder_tanh.example` (tanh, Adam, η = 0,001, 30000 épocas, batch completo, 35-35-20-10-**2**) y
cambia una cosa por vez. "Cumplen" = corridas donde las 32 letras quedan con a lo sumo 1 píxel incorrecto; las semillas
son 1, 2, ... en cada fila, así que las filas son comparables entre sí. El η de cada optimizador se eligió mirando las
mismas 32 letras que se usan para medir (no hay validación aparte: la tarea es memorizarlas).

**Arquitectura** (10 semillas; el número es lo que hay entre la entrada de 35 y el latente de 2, el decoder es el espejo):

| Capas | Cumplen | MSE medio | Peor letra | s/corrida |
|---|---|---|---|---|
| 35-2 (sin ocultas) | 0/10 | 0,1375 | 12 px | 0,4 |
| 35-10-2 | 0/10 | 0,0508 | 11 px | 1,1 |
| 35-35-2 | 5/10 | 0,0047 | 2 px | 2,8 |
| 35-20-10-2 | 6/10 | 0,0058 | 2 px | 2,4 |
| 35-35-20-10-2 (base) | 9/10 | 0,0013 | 2 px | 5,4 |
| 35-35-35-20-10-2 | 9/10 | 0,0010 | 2 px | 9,3 |

**Optimizador** (5 semillas, arquitectura base):

| Optimizador | η | Cumplen | MSE medio |
|---|---|---|---|
| gd | 0,001 / 0,01 / 0,1 | 4/5 / 0/5 / 0/5 | 0,0027 / 0,067 / 0,568 |
| momentum (α = 0,9) | 0,0003 / 0,001 / 0,01 | 2/5 / 4/5 / 0/5 | 0,0022 / 0,0018 / 0,525 |
| rmsprop (γ = 0,9) | 0,0001 / 0,001 / 0,01 | 4/5 / 5/5 / 5/5 | 0,0038 / 0,0016 / 0,0026 |
| adam | 0,0003 / 0,001 / 0,003 | 5/5 / 5/5 / 5/5 | 0,0011 / 0,0005 / 0,0013 |

Lo que se puede decir: con un latente de 2 hace falta profundidad. Sin capas o con una de 10 neuronas ninguna semilla
llega, y la base llega en 9 de 10; una capa más no mejora el cumplimiento y casi duplica el tiempo. GD y momentum solo
funcionan con η chico y divergen con η grande; RMSProp y Adam aguantan un rango de η más ancho. Adam dio el menor MSE medio
(0,0005 con η = 0,001) y cumplió con sus tres η. Con 5 semillas, 5/5 contra 4/5 no es una diferencia que se pueda sostener.

## Arquitectura del autoencoder

Se define en el JSON con dos claves:

```json
"encoder_layers": [35, 20, 10],
"latent_dim": 2
```

`encoder_layers` son las neuronas de cada capa entre las entradas y el código latente (`[]` si no hay), y `latent_dim` las
del latente. El decoder es el espejo del encoder. Con las letras (35 píxeles) eso da la red
35-35-20-10-**2**-10-20-35-35. Para probar otra arquitectura se cambian esas dos claves; el resto del config
(`activation`, `optimizer`, `eta`, `epochs`, `batch_size`, `seed`...) es el del perceptrón de `neuron/`. Hay una sola
`activation` para toda la red: con `logistic` la salida queda en (0, 1) como los píxeles. Ver `neuron/README.md`
(sección Autoencoder y Configuración).

Para correr con otro config sin tocar el ejemplo:

```sh
cp neuron/config.json.autoencoder.example neuron/mi_config.json   # editar encoder_layers, eta, etc.
(cd neuron && ./build/neuron mi_config.json)
python3 scripts/wrong_pixels.py
```

## Tests

```sh
make -C neuron test
```

Cubre, además de la red y los optimizadores, la lectura de `encoder_layers`/`latent_dim` (incluidos los errores) y que un
autoencoder chico aprende a reconstruir su entrada.

## Qué falta

- 1.a.2: el estudio de arriba cubre arquitectura y optimizador sobre `tanh`. No se probó el tamaño del latente (el
  enunciado fija 2), `batch_size` ni `adaptive_eta` con `tanh`, y el único η de las arquitecturas es 0,001.
- 1.b (denoising) y el ejercicio 2 (VAE).
