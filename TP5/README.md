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
  scripts/noisy_font.py       dataset de denoising: letras con ruido de entrada y la letra limpia como ζ
  scripts/study_1b.py         estudio de 1.b (latente, ruido de entrenamiento, test final)
  scripts/denoise_figure.py   figura de 1.b: limpia, entrada ruidosa y salida (docs/denoising.png)
  scripts/digits_to_csv.py    dígitos de TP3 (28x28) -> CSV de autoencoder, para el VAE (ejercicio 2)
  scripts/study_vae.py        barrido de β y épocas del VAE (docs/estudio_vae.csv)
  scripts/vae_figures.py      figuras del VAE: latente, imágenes nuevas, reconstrucciones (docs/vae_*.png)
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

## Denoising autoencoder (1.b)

Es la misma red y el mismo binario, con otros datos: la entrada es la letra con ruido y la ζ es la letra limpia
(`scripts/noisy_font.py`). El ruido invierte cada píxel con probabilidad p, de forma independiente. Los números salen de
`scripts/study_1b.py` y quedan en `docs/estudio_1b.csv`; se mide cuántos píxeles de la salida (binarizada en 0,5)
difieren de la letra limpia, contra los que ya diferían en la entrada. Entrenamiento, validación y test usan
realizaciones de ruido distintas (semillas 1, 1000 y 2000): se eligió con validación y el test se corrió una sola vez.

**Arquitectura.** Encoder 35-20, latente de 10, decoder espejo (35-20-**10**-20-35), `tanh`, Adam con η = 0,001, 300 épocas
con batches de 32 sobre 3200 muestras ruidosas (100 por letra), 3 semillas por fila (validación, p = 0,1):

| Latente | 2 | 5 | 10 | 20 | 35 |
|---|---|---|---|---|---|
| Píxeles mal en la salida (la entrada tiene 3,58) | 1,61 | 0,98 | 0,85 | 0,75 | 0,69 |

Con un latente de 2, que alcanzaba en 1.a para memorizar las 32 letras, no alcanza para limpiar ruido: queda en 1,61. A
partir de 10 la mejora es chica (0,16 píxeles entre 10 y 35), así que se eligió 10, que sigue comprimiendo (10 < 20) y
obliga a la red a aprender la forma de las letras en lugar de copiar la entrada. Es una elección de criterio: 20 y 35
dieron algo mejor.

**Ruido de entrenamiento** (validación, latente 10, 3 semillas; píxeles mal en la salida):

| Entrenado con | p = 0,05 | 0,1 | 0,2 | 0,3 |
|---|---|---|---|---|
| entrada sin limpiar | 1,76 | 3,60 | 6,90 | 10,43 |
| p = 0,05 | 0,23 | 1,49 | 6,16 | 11,72 |
| p = 0,1 | 0,16 | 0,83 | 4,30 | 9,66 |
| p = 0,2 | 0,29 | 0,71 | 3,24 | 7,60 |
| mezcla 0,05 / 0,1 / 0,2 | 0,17 | 0,81 | 3,73 | 8,78 |

Entrenar con un solo nivel especializa a la red. La mezcla queda cerca del mejor en cada columna y es la que se eligió; con
p = 0,2 se gana a ruido alto (0,2 y 0,3) pero se pierde a ruido bajo.

**Test** (semilla de ruido 2000, 640 muestras por nivel, 5 semillas de entrenamiento). El control es la misma red entrenada
solo con letras limpias (30000 épocas):

| p | Entrada | Denoising: píxeles mal | letras perfectas | Control: píxeles mal | letras perfectas |
|---|---|---|---|---|---|
| 0 | 0 | 0,00 | 100% | 0,01 | 99% |
| 0,05 | 1,67 | 0,14 | 97% | 6,50 | 22% |
| 0,1 | 3,43 | 0,69 | 88% | 9,76 | 6% |
| 0,15 | 5,19 | 1,96 | 72% | 12,13 | 3% |
| 0,2 | 7,03 | 3,91 | 53% | 13,60 | 2% |
| 0,3 | 10,53 | 8,82 | 21% | 16,26 | 1% |
| 0,4 | 13,92 | 12,54 | 7% | 18,35 | 1% |

El denoising limpia bien hasta p = 0,1 (88% de las letras sin ningún píxel mal), a p = 0,2 recupera algo más de la mitad
y a p = 0,3 casi no ayuda. El control, que nunca vio ruido, deja *más* píxeles mal que la entrada: con el cuello de botella
reconstruye letras del conjunto, no la que le llega. `docs/denoising.png` (`.venv/bin/python scripts/denoise_figure.py`)
muestra algunos ejemplos.

Límites: el ruido de entrenamiento son 100 realizaciones fijas por letra y la red las sobreajusta (el MSE de train es mucho
menor que el de validación); no se probó generar ruido nuevo en cada época, otro tipo de ruido (gaussiano) ni otras
arquitecturas que la de encoder 35-20.

## VAE sobre los dígitos (ejercicio 2)

**Datos.** `digits.csv` de TP3 solo no sirve: no tiene ningún 8 y casi no tiene 5. Se une con `more_digits.csv`
(comparten 3689 imágenes) y quedan 24501 únicas, aunque el 8 (585) y el 5 (785) siguen siendo pocos contra ~2800 de cada
uno de los demás. `scripts/digits_to_csv.py --val-n 500 --val-out neuron/data/digits_val.csv --balanced` aparta 500
imágenes de ese pozo para validación y arma un train con 577 de cada dígito (5770). `digits_test.csv` queda sin tocar,
para una evaluación final que todavía no se hizo.

**Modelo.** `variational_beta` en el config (ver `neuron/config.json.vae.example`) vuelve variacional al autoencoder:
la capa del medio da L medias y L log-varianzas, z = media + exp(log-varianza / 2)·ε con ε ~ N(0, 1) y el error es
½·Σ(ζ − O)² + β·KL, con KL = −½·Σ(1 + log-varianza − media² − exp(log-varianza)). La retropropagación a través del
muestreo está verificada contra el gradiente numérico (`make -C neuron test`). En un VAE se guardan los pesos de la
última época, no los de menor MSE, porque ese MSE no incluye el KL.

**β** (784-128-L-128-784, L = 2, tanh, Adam, 30 épocas, 1 semilla; predecir siempre la imagen media da MSE 0,0680):

| β | 0 | 0,01 | 0,1 | 1 |
|---|---|---|---|---|
| MSE de validación | 0,0509 | 0,0504 | 0,0507 | 0,0549 |
| KL por imagen | 27,6 | 12,9 | 5,7 | 1,9 |

β ≤ 0,1 rinde casi igual y con β = 1 el latente no colapsa. Se usó β = 0,1: reconstruye como los β más chicos y deja el
latente más cerca de una normal.

**Latente de 2 y de 10, con y sin KL** (`scripts/vae_figures.py`, 100 épocas, β = 0,1 o 0, 1 semilla, validación):

| Modelo | MSE de validación | KL por imagen |
|---|---|---|
| VAE, latente 2 | 0,0480 | 5,6 |
| VAE, latente 10 | 0,0359 | 15,1 |
| Sin KL (β = 0), latente 2 | 0,0491 | 27,7 |
| Sin KL (β = 0), latente 10 | 0,0373 | 204,3 |

- `docs/vae_reconstructions.png`: con latente 10 se reconocen la mayoría de los dígitos; con 2 varios salen de otra
  clase (el 2 como 7, el 3 como 8) porque en el plano los dígitos se solapan (`docs/vae_latent.png`). El KL no empeora la
  reconstrucción, pero con una semilla las diferencias de MSE entre VAE y sin KL no son concluyentes.
- `docs/vae_latent.png`: con KL los códigos de 2 dimensiones quedan en unos ±3, como una normal; sin KL llegan a ±10. La
  grilla decodificada pasa suavemente entre 0, 6, 9, 7, 1, 3, 5, 8 y 2.
- `docs/vae_samples.png` (z ~ N(0, I) decodificado): el VAE con latente 10 da dígitos reconocibles con algo de ruido (1,
  0, 8, 3, 9, 4, 6); el modelo sin KL con latente 10 da **solo ruido**, porque la normal cae lejos de donde su decoder
  aprendió. Es lo que el término KL resuelve (2.b). Con latente 2 el modelo sin KL también da dígitos borrosos, porque su
  rango de códigos alcanza a cubrir la normal. Que una muestra sea un dígito se juzga a ojo, no hay otra medida.

Un autoencoder no variacional con `tanh` en la capa latente **no sirve como control** acá: con 784 entradas satura esa
capa (el 100% de los códigos en ±1) y no entrena, cae al MSE de la imagen media. Por eso el control es el mismo VAE con
β = 0 (que sigue inyectando el ruido ε y por lo tanto no es un autoencoder determinista).

## Evaluación final del VAE sobre `digits_test.csv` (protocolo fijado antes de correr)

Una sola corrida, con los modelos y la configuración ya elegidos con la validación, sin tocarlos después de ver estos
números (`scripts/final_eval_vae.py`):

- Modelos: VAE con β = 0,1 y el mismo modelo sin KL (β = 0), cada uno con latente 2 y 10; encoder 784-128, tanh, Adam,
  η = 0,001, 100 épocas, train de 5770 imágenes balanceado. Semillas 1, 2 y 3.
- Datos: las 2497 imágenes de `digits_test.csv` (de `digits.csv` y `more_digits.csv` no comparte ninguna).
- Medidas: MSE de reconstrucción con z = media, total y por dígito, y KL por imagen; referencia: predecir siempre la
  imagen media del train.
- Predicción: el MSE de test queda cerca del de validación (0,048 con latente 2 y 0,036 con latente 10), salvo que
  `digits_test.csv` venga de otra distribución. Si queda más de un 20% por encima, se informa así y no se reajusta nada.

**Resultado** (una sola corrida, `docs/evaluacion_final_vae.csv`; media y desvío de las 3 semillas; referencia: predecir
siempre la imagen media del train, MSE 0,0676):

| Modelo | MSE de test | contra la validación | KL por imagen |
|---|---|---|---|
| VAE, latente 2 | 0,0492 ± 0,0001 | +2% | 5,5 |
| VAE, latente 10 | 0,0371 ± 0,0006 | +3% | 14,9 |
| Sin KL (β = 0), latente 2 | 0,0498 ± 0,0003 | +1% | 28,3 |
| Sin KL (β = 0), latente 10 | 0,0376 ± 0,0004 | +1% | 200,5 |

MSE por dígito, VAE con latente 2 y con latente 10 (referencia entre paréntesis):

| Dígito | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| latente 2 | 0,053 | 0,021 | 0,067 | 0,054 | 0,050 | 0,058 | 0,051 | 0,042 | 0,057 | 0,043 |
| latente 10 | 0,041 | 0,019 | 0,046 | 0,039 | 0,038 | 0,044 | 0,040 | 0,033 | 0,043 | 0,033 |
| referencia | 0,091 | 0,050 | 0,077 | 0,070 | 0,064 | 0,068 | 0,071 | 0,063 | 0,068 | 0,058 |

- La predicción se cumplió: el MSE de test queda entre 1% y 3% por encima del de validación (el criterio era 20%), así que
  `digits_test.csv` no trae un corrimiento de distribución que se note en la reconstrucción.
- El latente de 10 reconstruye mejor que el de 2 (0,037 contra 0,049) y las dos mejoran la referencia (0,068).
- El VAE y el modelo sin KL reconstruyen casi igual: con latente 10 la diferencia (0,0005) es menor que la variación entre
  semillas, y con latente 2 (0,0006) está en el borde. Lo que el KL cambia es la escala del latente (KL de 15 contra 200
  con latente 10) y con ella la calidad de las imágenes nuevas, que no se mide acá.
- Por dígito, el 1 es el que más mejora respecto de la referencia (−58% con latente 2) y el 2, el 5 y el 8 los que menos
  (entre −12% y −16% con latente 2). El 8 y el 5, que en el train se balancearon a la fuerza, no salen peor que el resto
  en términos absolutos.
- Esto mide solo la reconstrucción de imágenes de test. La calidad de las imágenes nuevas (2.c) se sigue juzgando a ojo.

## Muestras nuevas del VAE (2.c, protocolo fijado antes de correr)

El enunciado pide una muestra nueva que se pueda juzgar como parte del dataset. Para no elegir a ojo la que mejor
se ve, se fija un criterio antes de generar (`scripts/new_samples.py`, una sola corrida):

- Se generan 300 muestras z ~ N(0, I) con cada VAE (latente 2 y latente 10, β = 0,1, 100 épocas, semilla 1, como en las
  figuras), con una semilla fija.
- Pertenece a la clase d si un clasificador de dígitos (784-64-10, logistic, Adam, 30 épocas, entrenado con el mismo
  train de 5770 imágenes) da salida máxima ≥ 0,8 para d y la segunda mayor ≤ 0,2.
- Es nueva (no una copia del train) si su distancia euclídea al píxel más cercano del train es al menos la del percentil
  5 de las distancias al train de las 500 imágenes de validación, que son reales y no se vieron.
- Referencia: qué fracción de esas 500 imágenes reales pasa el criterio de pertenecer (y lo hace con la clase correcta).
- Se muestra, por clase, la muestra que cumple ambas con mayor margen. Nada se reajusta después de ver el resultado.

**Resultado** (una sola corrida; `docs/muestras_2c.csv` y `docs/vae_muestras_2c.png`):

| | Pertenecen (de 300) | Nuevas (de 300) | Ambas | Clases sin ninguna |
|---|---|---|---|---|
| VAE, latente 2 | 95 (32%) | 300 | 95 | 5, 9 |
| VAE, latente 10 | 72 (24%) | 300 | 72 | ninguna |
| imágenes reales de validación (referencia) | 79% con la clase correcta | | | |

El clasificador acierta el 94,4% de la validación, pero con el criterio exigente (≥ 0,8 y segunda ≤ 0,2) solo el 79% de
las imágenes reales lo pasa con su clase.

- **Pocas muestras del prior pasan el criterio.** El 32% (latente 2) y el 24% (latente 10), contra el 79% de las
  imágenes reales. La mayoría de las muestras z ~ N(0, I) no se reconocen como un dígito con esa exigencia.
- **El criterio de "nueva" no discrimina:** las 300 muestras de ambos modelos lo cumplen. Son borrosas y quedan lejos
  de cualquier imagen nítida del train, así que "no es una copia" se cumple sin que eso diga mucho. La imagen más
  cercana del train suele ser de otro dígito (la "2" de latente 2 tiene como más cercana un "1"), o sea que la
  distancia en píxeles es una medida pobre.
- **Con latente 2 las que pasan se concentran:** 44 de las 95 son 8, y no hay ningún 5 ni 9. Una mancha borrosa tiende
  a leerse como un 8, así que el criterio puede estar sobreestimando la calidad de ese modelo.
- **Con latente 10 pasan menos, pero hay de todas las clases** y se ven más variadas y más nítidas; el clasificador
  descarta más las que tienen ruido.
- **El margen del clasificador no es lo mismo que reconocer un dígito a ojo.** En `docs/vae_muestras_2c.png`, de las
  elegidas: se leen bien el 0, 6 y 7 de latente 2 y el 3, 4 y 6 de latente 10; son dudosas la "2" y la "3" de latente 2
  (parecen un 7 y un 8) y la "7" y la "8" de latente 10. Ese es el juicio de quien escribe esto: el enunciado pide
  el de ustedes sobre la figura.

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
- Ejercicio 2 (VAE): las comparaciones de β, de latente 2 y 10 y con o sin KL son de una sola semilla (la evaluación final
  usa 3, para reconstrucción); falta probar más épocas y otras arquitecturas, y que ustedes juzguen y elijan la muestra
  del 2.c sobre `docs/vae_muestras_2c.png`.
