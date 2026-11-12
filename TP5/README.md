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
(`neuron/results/<fecha>_<hora>_logistic/`). Con el ejemplo, el MSE de train termina cerca de 0,004 y las 32 letras
salen con a lo sumo 1 píxel incorrecto, que es el objetivo del enunciado:

```
píxeles incorrectos por letra: [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1]
letras con a lo sumo 1 píxel incorrecto: 32/32
```

Cada corrida guarda en su carpeta el config usado, `weights.csv`, `epochs.csv` (error por época),
`predictions.csv`, `predictions_by_epoch.csv` y, si es un autoencoder, `latent.csv` (código latente de cada letra); `results/` no se versiona. `make run` de `neuron/` también quiere armar
un reporte HTML con `../scripts/run_report.py`, que todavía no está en TP5: usá el binario directo, como arriba.

## Espacio latente (1.a.3)

```sh
.venv/bin/python scripts/latent_plot.py [neuron/results/<corrida>]   # sin argumento, la última corrida
```

Lee `latent.csv` y escribe `latent.png` y `latent.svg` en la carpeta de la corrida: un punto por letra en el plano 2D,
con el nombre de la letra tomado de los comentarios de `src/font.h`.

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

- 1.a.2: comparar arquitecturas y optimizadores. Con este ejemplo ya se llega a 32/32, pero depende de la elección:
  con Adam y η = 0,005 la red se vuelve inestable y con `adaptive_eta` (GD) llega a 24/32 en 100000 épocas.
- 1.a.4: generar letras nuevas. `Network` ya expone `network_decode` para decodificar un punto 2D; falta una forma de
  correrlo desde un `weights.csv` y dibujar el resultado.
- 1.b (denoising) y el ejercicio 2 (VAE).
