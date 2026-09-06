# TP2 · Algoritmos Genéticos — aproximación de imagen con triángulos

Motor de Algoritmos Genéticos genérico (implementación propia, sin DEAP/pygad)
que aproxima una imagen dibujando `T` triángulos translúcidos de color
uniforme sobre un canvas. Enunciado en
[`docs/SIA - TP2 - 2026 2Q.pdf`](docs/SIA%20-%20TP2%20-%202026%202Q.pdf).
El detalle de cada decisión de diseño está en [`CLAUDE.md`](CLAUDE.md).

```
build.py                CLI: compila rust/ (maturin develop) y verifica el resultado
simulate.py             CLI: corre el AG y escribe solo datos — no dibuja nada
render_final.py         CLI: dibuja final.png desde un directorio de resultados
render_snapshots.py     CLI: dibuja snapshots/ + progress.gif desde ese directorio
run.py                  CLI: las tres etapas juntas — python run.py [config.json]
pipeline.py             las etapas, implementadas una sola vez; los CLI son finitos
config.json.example     config de referencia (copiar a config.json)
requirements.txt        pillow, numpy, pytest, maturin (el core de ga/ no usa nada de esto)
ga/                      motor genérico — solo stdlib
  core/
    rng.py               Rng = random.Random ; make_rng(seed)
    gene.py              Gene(name, lower, upper, kind) + GeneSchema(genes, block_size)
    individual.py        Individual: alleles + schema + fitness cacheado
    population.py        Population(individuals, generation)
    problem.py            ABC Problem: schema / random_individual / evaluate / describe
    engine.py              Evaluator (memo + contador), EngineConfig, Engine.run -> RunResult
  operators/
    selection.py           elite, roulette, universal, boltzmann, torneo (det./prob.), ranking
    crossover.py            one_point, two_point, uniform, ring (granularidad block/allele)
    mutation.py              gene, multigene, uniform, non_uniform
    survival.py               additive (mu+lambda), exclusive (mu,lambda)
    stopping.py                target_fitness, stagnation
  registry.py             nombre (config) -> callable, por categoría
  config.py                parseo/validación de config.json -> ConfigError
  metrics.py                GenerationRecord + mean/std/diversidad genotípica
problems/
  triangles/               plug-in de dominio (Pillow solo para I/O de imágenes; el
                            render+score en sí corre en rust/, no acá)
    genotype.py             alelos [0,1] <-> Triangle, GeneSchema (10 genes/triángulo)
    colorspace.py             RGB/HSV/HCL — decodificación de color, en Python puro
    renderers.py               RustRenderer: sube el target a triangles_native una vez
                                por corrida y le delega rasterizar + puntuar
    problem.py                  TrianglesProblem(Problem)
    export.py                    render full-res + enumeración JSON + native_resolution
rust/                     crate PyO3 obligatorio: rasteriza + decodifica color + puntúa
                          (ver "El backend nativo" más abajo; sin esto no corre nada)
images/                   imágenes de referencia (argentina.png, starry_night.png)
tests/                    tests unitarios de los operadores (pytest, deterministas)
```

## Arranque rápido

Corre sobre la extensión nativa de `rust/`: no hay un camino en Python puro
para rasterizar y puntuar, así que compilarla es parte del setup, no un paso
opcional de rendimiento (ver ["El backend nativo"](#el-backend-nativo-rust) más
abajo para el detalle y el porqué).

```bash
python3 -m venv .venv                 # crear un entorno virtual
source .venv/bin/activate             # activarlo (Windows: .venv\Scripts\activate)
pip install -r requirements.txt       # pillow, numpy, pytest, maturin

curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh   # una sola vez
. "$HOME/.cargo/env"                   # rustup no toca el PATH de la shell ya abierta

cd TP2
python build.py                       # compila rust/ y reporta con qué flags quedó

[ -f config.json ] || cp config.json.example config.json   # no pisa el tuyo si ya existe
python run.py                                             # usa ./config.json
```

Ajustá `config.json` a gusto (imagen, `shape_count`, operadores). Para correr
otro archivo, pasáselo como argumento: `python run.py otra_config.json`.

Sin el toolchain de Rust compilado, `import problems.triangles` funciona igual
(así que, por ejemplo, `pytest tests/test_colorspace.py` sigue en verde), pero
construir un `TrianglesProblem` — y por lo tanto cualquier corrida — falla con
un error claro pidiendo el `python build.py` de arriba.

## Los cinco scripts

Una corrida son tres etapas separables, más el build. Están implementadas una
sola vez en [`pipeline.py`](pipeline.py); los scripts son CLIs finitos sobre
esas funciones, así que el camino de un comando no puede divergir del camino
por partes.

| script | qué hace | escribe |
|---|---|---|
| `build.py` | compila el kernel nativo de `rust/` | la extensión, en el venv activo |
| `simulate.py` | corre el AG. **No dibuja nada** | `history.csv`/`.json`, `summary.json`, `best.json`, `figures.json`, `checkpoints.jsonl` |
| `render_final.py` | dibuja el mejor individuo | `final.png` |
| `render_snapshots.py` | dibuja la evolución | `snapshots/gen_*.png`, `progress.gif` |
| `run.py` | las tres etapas de un saque | todo lo de arriba |

```bash
python build.py                       # o --profile parallel mientras iterás
python build.py --check               # no compila: dice qué extensión hay instalada

# analizar números, sin pagar un solo píxel
python simulate.py config.json --out results/prueba/0003 --quiet

# y después, cuando quieras verlo
python render_final.py     results/prueba/0003
python render_snapshots.py results/prueba/0003
```

**Por qué separados**: `on_generation` renderizaba un PNG a resolución nativa
*adentro* del loop cronometrado, así que el `elapsed_seconds` de `summary.json`
incluía trabajo que no es del algoritmo. Hoy `simulate.py` solo guarda el
genotipo del mejor de cada N generaciones (una referencia, no una copia: los
operadores nunca mutan in place, así que al loop no le cuesta nada) y los
vuelca recién al terminar. Medido con `starry_night`, 2000 triángulos, 300
generaciones y `--snapshot-every 10`: la simulación son 31,7 s y dibujar esas
31 snapshots a 1200×950 otros 5,9 s — un 19% que antes se contaba como tiempo
de AG. `--progress-every N` (o `--quiet`) hace lo mismo con los prints, que a
30.000 generaciones también suman.

Las etapas de render no necesitan el `config.json`: reconstruyen el problema
desde el bloque `config` de `summary.json`, para que la imagen la dibuje el
mismo kernel, espacio de color, tipo y cantidad de formas que la puntuó. Se pueden
correr días después, en otra máquina. Los `image_path` del config son
relativos, así que hay que correrlas desde `TP2/`.

### Qué escribe una corrida

Cada corrida escribe en un directorio de resultados
(`results/<config>_<timestamp>/` por default, o `--out DIR`):

- `history.csv` / `history.json` — una fila por generación: fitness
  mejor/promedio/desvío/peor, diversidad genotípica, evaluaciones y tiempo
  acumulados.
- `summary.json` — fitness final, generación en que apareció, criterio de
  corte que disparó, evaluaciones/tiempo totales, config completo + seed, y un
  bloque `problem` con lo que **realmente** corrió: `work_resolution` resuelta,
  flags con los que se compiló el backend nativo y threads usados. `config` es
  lo que se pidió; `problem` es lo que pasó, y difieren en todo lo que sea
  `"native"`.
- `best.json` — el genotipo ganador, alelos crudos en `[0,1]` a precisión
  completa. Vuelve a puntuar bit a bit idéntico al `best_fitness` del summary.
- `figures.json` — las mismas formas en espacio de píxeles (vértices o
  centro+radios+ángulo según el tipo, + color RGBA), que es el formato que pide
  el enunciado (con `shape_type: "triangle"`) y el que lee `import`. Cada
  entrada lleva un campo `"type"` (`"triangle"` u `"oval"`).
- `checkpoints.jsonl` — solo con `--snapshot-every N`: una línea por snapshot
  con el genotipo del mejor de esa generación, redondeado a 8 decimales (a
  4096 px de export eso es 4e-5 de un píxel). Es de lo que dibuja
  `render_snapshots.py`.
- `final.png` — mejor individuo a la resolución nativa de la imagen fuente (o
  `--export-width`/`--export-height`).
- `snapshots/gen_NNNNN.png` y `progress.gif` — la animación: un frame por
  checkpoint más `final.png` al cierre, sostenido unos segundos. `--no-gif` lo
  desactiva y `--gif-frame-ms` / `--gif-hold-ms` ajustan los tiempos (default
  120 ms por frame, 3000 ms de cierre).

Sobre `--export-width`/`--export-height`: sin ellos cada snapshot se renderiza a
la resolución nativa de la imagen fuente, y en un gif de 20 frames eso se nota
(`images/starry_night.png` es 1200×950 → gif de varios MB). Achicar el export
no toca la evaluación, que corre a `work_resolution` y es otra cosa.

## `config.json`

```json
{
  "seed": 42,
  "engine": {
    "n": 100,
    "k": 100,
    "pc": 0.85,
    "pm": 0.05,
    "max_generations": 500
  },
  "operators": {
    "parent_selection": {
      "name": "tournament_deterministic",
      "params": {"tournament_size": 3}
    },
    "crossover": {
      "name": "one_point",
      "params": {}
    },
    "mutation": {
      "name": "non_uniform",
      "params": {"b": 2.0, "mutations_per_child": 25}
    },
    "survival": {
      "name": "additive",
      "params": {"selection_method": "elite"}
    }
  },
  "stopping": [
    {"name": "target_fitness", "params": {"threshold": 0.98}},
    {"name": "stagnation", "params": {"generations": 50}}
  ],
  "problem": {
    "type": "triangles",
    "params": {
      "image_path": "images/argentina.png",
      "shape_count": 50,
      "shape_type": "triangle",
      "work_resolution": [128, 80],
      "background_rgb": [255, 255, 255],
      "color_space": "rgb",
      "initial_alpha": 0.2
    }
  }
}
```

- **`seed`**: entero obligatorio — misma seed + mismo config ⇒ mismo
  resultado siempre.
- **`engine`**: `n` (tamaño de población), `k` (hijos por generación), `pc`,
  `pm`, `max_generations` (tope duro, además de cualquier `stopping`).
- **`engine.processes`** existe pero **no está en el config de referencia, a
  propósito**. Es la cantidad de procesos en paralelo con la que el motor
  evalúa una generación, y es un knob **genérico del motor, no del problema
  triangles**: `TrianglesProblem.owns_parallelism()` siempre da `True` (el
  renderer nativo ya reparte la corrida entre sus propios threads, ver más
  abajo), así que acá el engine nunca abre ese pool y el valor no tiene ningún
  efecto. Ponerlo en `1` no era más honesto que omitirlo — era ruido que se
  leía como si estuviera configurando algo. Sigue aceptándose para un `Problem`
  distinto que no paralelice por su cuenta, y pedir más de 1 en un problema que
  sí lo hace ahora **avisa** en vez de degradar en silencio:

  ```
  UserWarning: engine.processes=8 ignored: this problem parallelises
  internally, and stacking processes on its threads would only oversubscribe
  the CPU
  ```

  El número que sí gobierna el paralelismo de una corrida de triangles es
  `problem.params.threads`.
- **`operators.{parent_selection,crossover,mutation,survival}`**: `name` +
  `params` propios de ese operador, resueltos por nombre vía `ga/registry.py`.
  `mutation.params.mutations_per_child` reemplaza a `engine.pm` con una tasa
  que no depende del largo del genoma (ver "Carga de mutación").
  Los `params` de las cuatro categorías se mergean en un único dict que el
  engine le pasa a cada operador junto con `generation`/`max_generations`/
  `history` — por eso `boltzmann` puede leer `t0`/`tmin`/`tau` sin que el
  engine sepa nada de annealing.
- **`stopping`**: lista de criterios adicionales, evaluados en orden y
  combinados por OR entre sí y con `max_generations`.
- **`problem`**: `type` (hoy solo `"triangles"`) + `params` — `image_path`,
  `shape_count`, `shape_type` (opcional, default `"triangle"`: `"triangle"`,
  `"oval"` o `"both"` — en `"both"` cada figura es triángulo u óvalo según un
  gen discreto que la mutación cambia sola, generación a generación), `work_resolution`
  (resolución chica para evaluar fitness; el genotipo es independiente de la
  resolución), `background_rgb`, `color_space` (opcional, default `"rgb"`),
  `initial_alpha` (opcional, default `1.0`; ver "El piso de fitness") y
  `threads` (opcional, default `0` = uno por core; ver
  ["El backend nativo"](#el-backend-nativo-rust)).

## Resolución de evaluación (`problem.params.work_resolution`)

El fitness no se calcula sobre la imagen entera: se calcula sobre el target
reescalado a `work_resolution`. El genotipo es independiente de la resolución
(alelos en `[0,1]`), así que subirla no cambia nada del AG — solo cambia cuánto
detalle *ve* la función objetivo, y cuánto sale cada evaluación.

Medido con el backend Rust (500 generaciones, 50 triángulos, `starry_night.png`,
20 hilos):

| `work_resolution` | píxeles | ms/generación |
|---|---|---|
| `[128, 80]` | 10.240 (1×) | 7,5 |
| `[320, 253]` | 80.960 (7,9×) | 11,4 |
| `[512, 405]` | 207.360 (20×) | 17,3 |
| `[800, 633]` | 506.400 (50×) | 34,4 |
| `[1200, 950]` (nativo) | 1.140.000 (111×) | 114 |

**El costo crece mucho más despacio que los píxeles**: 20× de resolución cuesta
2,3× de tiempo. Con el rasterizador nativo el cuello de botella ya no es
rasterizar, son los operadores en Python — `non_uniform` hace ~55.000 llamadas a
`rng.random()` por generación y eso no depende de la resolución. Recién a
resolución nativa vuelve a mandar el render.

O sea que **píxel por píxel es viable**: evaluar a `[1200, 950]` son ~57 s por
cada 500 generaciones. Lo que no compra es calidad — entre `[128, 80]` y
`[512, 405]` el RMSE final se mueve dentro del ruido entre seeds. Con 50
triángulos el techo lo pone la representación, no lo que la métrica alcanza a
ver. Subir la resolución sirve para que el fitness mida *lo que vas a mirar*:
a 128×80 el AG puede dejar artefactos que a tamaño de export se notan y la
métrica nunca penalizó.

Conviene respetar el aspecto de la imagen, para que el muestreo sea parejo en
los dos ejes: `argentina.png` es 2560×1600 (1,600 → `[128, 80]`, `[512, 320]`),
`starry_night.png` es 1200×950 (1,263 → `[512, 405]`).

### Píxel por píxel: `"work_resolution": "native"`

En vez de `[ancho, alto]`, `work_resolution` acepta el string `"native"`: el
fitness compara contra la imagen **a su resolución original**, sin reescalar
nada en el medio. Es lo más fiel que la función objetivo puede ser, y también lo
más caro — el aspecto lo hereda de la imagen, así que tampoco hay que calcularlo.

```json
"problem": {
  "type": "triangles",
  "params": {
    "image_path": "images/argentina.png",
    "work_resolution": "native"
  }
}
```

El bloque `problem` de `summary.json` guarda la resolución ya resuelta
(`[2560, 1600]`, no el string), así que una corrida siempre dice contra cuántos
píxeles se puntuó.

Los tres casos, con Rust, sobre `argentina.png` (2560×1600), 50 triángulos, 500
generaciones, seed 42. La columna que compara es el RMSE: son las tres imágenes
finales re-puntuadas contra el mismo target a 640×400, porque **el fitness no es
comparable entre resoluciones** (cada una tiene su propio `baseline_mse`).

| `work_resolution` | píxeles | tiempo | ms/gen | fitness | RMSE @640×400 |
|---|---|---|---|---|---|
| `[128, 80]` | 10.240 | 3,8 s | 7,6 | 0,9765 | 20,14 |
| `[512, 320]` | 163.840 | 7,2 s | 14,4 | 0,9256 | 22,62 |
| `"native"` | 4.096.000 | 208,3 s | 416,7 | 0,9322 | 19,94 |

Antes de leer esa última columna hace falta el control: repitiendo con 5 seeds,
`[128, 80]` da **20,84 ± 1,45** y `[512, 320]` da **21,74 ± 1,49**. Los tres
RMSE de la tabla caen adentro de ese ruido. Con 50 triángulos, entonces, la
resolución de evaluación **no cambia la calidad final de forma medible**, y
`"native"` cuesta 55× el tiempo para llegar al mismo lugar.

> **Los fitness y RMSE de esta sección se midieron antes de `6c9f297`** ("fix
> engine requesting more parents than breeding needs"), que bajó los padres
> pedidos por generación de `2k` a `k` y con eso cambió cuántos draws consume
> el RNG. Volver a correr con la misma seed hoy da otros dígitos (medido:
> 0,864040 → 0,844010 en una corrida de control de 60 generaciones). Las
> *conclusiones* no se mueven — la comparación entre resoluciones sigue
> cayendo dentro del ruido entre seeds — pero los números exactos son
> pre-fix. Lo mismo aplica a la tabla de "Rendimiento medido"; la de
> `initial_alpha` no, porque solo muestrea `random_individual` y no pasa por
> selección de padres.

Lo cual tiene sentido: reescalar el target a 128×80 lo *borronea*, y un target
borroso es justo lo que 50 triángulos planos pueden aproximar. A resolución
nativa el fitness persigue detalle que la representación no puede representar.
`"native"` empieza a valer la pena cuando hay triángulos de sobra — es la opción
honesta para una corrida final, no para iterar.

## Carga de mutación (`mutations_per_child`)

`pm` es la probabilidad de **cada tirada**, y salvo `gene`, todos los operadores
de mutación tiran una vez **por locus** (o por bloque). O sea que el número
esperado de mutaciones por hijo es `pm × largo del genoma` — y el genotipo de
este problema mide `10 × shape_count` en modo triángulo. Subir los triángulos sin tocar `pm`
multiplica la violencia de la mutación sin que se note en el config:

| triángulos | alelos | mutaciones/hijo con `pm=0.05` |
|---|---|---|
| 50 | 500 | 25 |
| 200 | 2000 | 100 |
| 500 | 5000 | 250 |

Y eso arruina el resultado, porque un hijo que difiere del padre en 250 lugares
no le da a la selección nada que pueda atribuir: ve el neto de 250 cambios,
no cuál sirvió. Medido con `argentina.png`, 1000 generaciones, RMSE contra el
mismo target a 640×400:

| triángulos | `pm` | mutaciones/hijo | RMSE |
|---|---|---|---|
| 50 | `0.05` | 25 | 16,69 |
| 200 | `0.05` | 100 | 16,61 |
| 200 | `0.0125` | 25 | **15,71** |
| 500 | `0.05` | 250 | 18,59 |
| 500 | `0.005` | 25 | **15,29** |

Con `pm` fijo, **más triángulos daba peor** (500 triángulos es la peor fila de
la tabla). Escalándolo, el orden se endereza y la capacidad extra rinde:
50 → 200 → 500 mejora siempre.

`mutations_per_child` dice lo mismo sin la cuenta a mano: es el número esperado
de mutaciones, y el operador lo convierte a probabilidad por tirada contra el
largo real del genoma. Cambiás `shape_count` y no tenés que re-tunear nada.

```json
"mutation": {"name": "non_uniform", "params": {"b": 2.0, "mutations_per_child": 25}}
```

Detalles: gana sobre `pm` si están los dos (pedir un número exacto es más
específico que pedir una probabilidad); la unidad es lo que ese operador
sortea, o sea un locus para `multigene`/`non_uniform` y un **bloque entero**
para `uniform`; y `gene` no lo usa, porque muta un solo locus por construcción
y no tiene nada que normalizar.

## El piso de fitness (`problem.params.initial_alpha`)

El fitness es `1 - mse/baseline` **recortado en 0**: todo lo que sea peor que el
canvas vacío vale exactamente 0. Con triángulos opacos al azar eso no es un caso
borde, es el arranque típico — 50 triángulos opacos sobre la bandera argentina
dan MSE 1,04x-1,76x el del canvas blanco, o sea **toda** la generación 0 empatada
en 0. Y con la población entera empatada, la selección no tiene nada que
ordenar: el "mejor" es el primero de la lista, no cambia nunca, y todas las
snapshots salen idénticas hasta que una mutación cruza el piso de casualidad.
Si además hay `stagnation`, la corrida se muere ahí.

`initial_alpha` acota el alpha **solo de la generación 0**: arranca casi
transparente, del lado útil del piso. No lo ve ningún operador ni ninguna
generación posterior — el alpha puede volver a subir a 1 por mutación — y como
se aplica después de sortear el vector, la misma seed sigue dando las mismas
coordenadas y colores.

Cuánto hace falta depende de la imagen y de cuántos triángulos haya. Individuos
aleatorios con fitness > 0, sobre 50 muestras:

| `initial_alpha` | argentina, 50 tri / RGB | argentina, 200 tri / HCL | starry_night, 50 tri / RGB |
|---|---|---|---|
| `1.0` (sin sesgo) | 0/50 | 0/50 | 50/50 |
| `0.2` | 50/50 | 4/50 | 50/50 |
| `0.1` | 50/50 | 39/50 | 50/50 |
| `0.05` | 50/50 | 50/50 | 50/50 |

Por eso el default es `1.0` (sin sesgo) y no un valor bajo: `starry_night` es
oscura y saturada, el canvas blanco es un baseline pésimo, y ahí los triángulos
opacos ya arrancan arriba del piso — bajarle el alpha solo empeora el punto de
partida (mejor individuo inicial: 0,585 con `1.0` contra 0,153 con `0.05`).
Regla práctica: si la generación 0 imprime `best=0.000000`, bajalo; si no,
dejalo en `1.0`.

## El backend nativo (Rust)

Rasterizar y comparar píxeles es ~90% del tiempo de una corrida, y corre
enteramente en la extensión nativa `triangles_native` (`rust/`). No es un
backend intercambiable entre varios — es el único, y compilarlo
(`cd rust && maturin develop --release`) es un requisito para correr el
problema `triangles`, no una opción de rendimiento. `problems/triangles/`
solo usa Pillow para I/O de imágenes (abrir el target, guardar exports y el
gif); nada de rasterizar ni de sumar error cuadrático corre en Python.

`problem.params.threads` (default `0` = uno por core) son los threads de rayon
que usa el kernel. `TrianglesProblem.owns_parallelism()` siempre da `True`
(el kernel ya reparte la corrida entre esos threads), así que el motor
**nunca** abre su propio pool de procesos para este problema — apilar
procesos sobre threads solo sobre-suscribiría la CPU. `engine.processes`
(la perilla genérica del motor) no tiene efecto acá; el único número que
gobierna el paralelismo real de una corrida es `threads`. Un valor mayor a la
cantidad de CPUs lógicas se acepta pero avisa: sobre-suscribir agrega cambios
de contexto a un kernel que ya está limitado por memoria.

#### Cuántos threads conviene pedir

`0` (uno por core) no es lo mismo que el máximo aprovechable. El paralelismo es
**estrictamente entre individuos**: el kernel por individuo es secuencial, así
que un batch de `k` individuos es todo lo que hay para repartir. Medido en un
Ryzen AI 9 365 (10 cores físicos, 20 lógicos), `starry_night` a 512×320, 2000
triángulos:

| threads | batch=25 | speedup | batch=100 | speedup |
|---|---|---|---|---|
| 1 | 319,9 ms | 1,0× | 1292,9 ms | 1,0× |
| 4 | 104,5 ms | 3,1× | 373,8 ms | 3,5× |
| 8 | 72,5 ms | 4,4× | 221,3 ms | 5,8× |
| 10 | 61,2 ms | 5,2× | 188,9 ms | 6,8× |
| **12** | **52,0 ms** | **6,2×** | 187,1 ms | 6,9× |
| 16 | 52,0 ms | 6,2× | 176,9 ms | 7,3× |
| 20 | 49,2 ms | 6,5× | 167,7 ms | 7,7× |

**Los últimos 8 threads compran 0,3×.** De 10 a 20 hay 1,25×, que es lo que
suele rendir SMT — los 20 lógicos son 10 físicos. La ineficiencia real está
antes: 5,2× sobre 10 cores físicos con `k=25`, porque 25 ítems sobre 10 threads
son 3 tandas (10+10+5, 83% de ocupación) y el resto es tráfico de memoria. Con
`k` chico, entonces, `threads: 12` da prácticamente el mismo throughput que
`20` y deja 8 CPUs libres para otra cosa.

No es el working set del canvas: barriendo la resolución con 20 threads y
batch 25, el escalado **mejora** hasta 512×320 (5,6×) y 800×500 (5,6×), y recién
se cae a 1200×750 (3,8×), donde 20 canvases de 3,5 MB no entran en los 24 MB de
L3. Abajo de 256×160 el trabajo por ítem es muy chico para amortizar el
overhead (3,1× a 128×80).

Importar el paquete no necesita la extensión compilada — `import
problems.triangles` (y por lo tanto `pytest tests/test_colorspace.py`) anda
igual sin ella — pero *construir* un `TrianglesProblem` sí, y ahí es donde
falla con un error claro si no está.

### Compilar el backend nativo

`python build.py` es el camino corto, y existe porque hay dos cosas que
arruinan el build en silencio:

- **`--release` no es opcional.** Un build de debug de este kernel es más
  lento que cualquier alternativa en Python puro alguna vez lo fue;
  `build_info()` arranca con `debug` o `release` según cuál quedó instalado.
- **Hay que correrlo desde `rust/`.** Cargo busca `.cargo/config.toml` desde su
  directorio de trabajo hacia arriba, no desde el manifest, así que
  `maturin develop -m rust/Cargo.toml` compila **sin** `target-cpu=x86-64-v3`.
  `build_info()` reporta las features realmente compiladas: si no dice
  `avx2`, el flag no se aplicó.

`build.py` hace las dos (`release` por default, siempre desde `rust/`), deriva
`VIRTUAL_ENV` de su propio intérprete para no exigir que el venv esté activado,
y al terminar importa la extensión recién compilada **en un subproceso** — el
proceso padre puede tener una vieja cargada — para reportar `build_info()` y
`schema_version()`. Si el binario perdió el `avx2` o quedó en `debug`, lo dice
ahí y no a las cuatro horas de corrida. `python build.py --check` hace solo esa
verificación, sin compilar:

```bash
$ python build.py --check
build_info      release [sse4.2,avx,avx2,fma]
schema_version  1
module          .../site-packages/triangles_native/__init__.py
```

#### Compilar más rápido mientras se itera

`release` está al máximo de optimización a propósito (`opt-level = 3`, LTO
*fat*, una sola unidad de codegen), y esa última parte es **secuencial**: rustc
termina fundiendo todo en un único módulo LLVM, así que sobre el final del build
queda un solo core trabajando. El perfil `parallel` de
[`rust/Cargo.toml`](rust/Cargo.toml) mantiene `opt-level = 3` y reparte la
optimización global: ThinLTO sobre 16 unidades, que se optimizan en paralelo (un
poco menos de inlining entre módulos que el LTO *fat*, a cambio de usar todos
los cores):

```bash
cd rust
CARGO_BUILD_JOBS=$(nproc) maturin develop --profile parallel
```

`CARGO_BUILD_JOBS` es opcional: Cargo ya lanza un job por CPU lógica, así que
`$(nproc)` es lo mismo que omitirlo — queda explícito acá por si alguna vez
hace falta pedir menos. Los flags de
[`rust/.cargo/config.toml`](rust/.cargo/config.toml) (`target-cpu`) aplican
igual, porque no dependen del perfil.

Medido en un Ryzen AI 9 365 (20 hilos), recompilando solo el crate:
**3,4 s con `--release`** (un core ocupado) contra **2,3 s con `parallel`**
(~4 cores). Es un crate de cuatro archivos: la diferencia es de ~1,5x, no de un
orden de magnitud.

El binario que sale puede ser algo más lento que el de `--release`, y
`build_info()` no los distingue (dice `release` en los dos, porque solo mira
`debug_assertions`). Para medir tiempos o generar números de informe, compilá
con `--release`.

### Por qué Rust reemplaza a Pillow

La implementación original rasterizaba con `ImageDraw.polygon` y sumaba el
error con numpy — esa fue la referencia contra la que se validó Rust mientras
existieron los dos, y una vez validado, el camino Python se sacó por completo
en vez de mantenerse como una segunda implementación del mismo hot path. Lo
que sigue son los números de esa migración, medidos entonces:

- **Decodificación de color: exacta.** Los tres espacios coincidían bit a bit
  con la implementación Python sobre todo el cubo de alelos (`==`, sin
  tolerancia) — y esto sigue siendo cierto y sigue estando probado
  (`tests/test_native_parity.py`), porque `colorspace.py` no se fue: todavía
  decodifica color para `export.py` y para importar un `figures.json`.
- **Puntajes: estadística.** `ImageDraw.polygon` pinta el contorno además del
  interior, así que cubre entre 7% y 30% más área por triángulo que la regla
  top-left del rasterizador propio — son dos funciones objetivo parecidas
  pero no idénticas. Sobre 120 genomas por espacio, el error cuadrático
  difería como máximo 3%, con sesgo medio de −0,4% a −0,9% (Rust cubría un
  poco menos), y la correlación de rangos era 0,997–0,999 — lo que importa,
  porque la selección solo consume el *orden* de los fitness.
- **Prueba end-to-end.** Misma seed y mismo presupuesto: el mejor individuo
  que encontraba el motor con Rust, puntuado con el oráculo Pillow, daba
  **0,895** contra **0,879** del que encontraba Pillow — igual de bueno o
  mejor bajo la métrica original, en 9,5× menos tiempo.
- **Invariancia de threads: exacta**, y esto también sigue probado — el
  paralelismo es solo *entre* individuos y el kernel por individuo es
  secuencial, así que el resultado no depende de `threads`. La
  reproducibilidad por seed se mantiene.

El bloque `problem` de `summary.json` registra qué build corrió (flags,
threads) para que un resultado quede atado a cómo se generó, aunque hoy solo
exista un backend posible.

### Rendimiento medido

25 generaciones, `n=k=100`, resolución de trabajo 128×80, en un Ryzen AI 9 365
(10 núcleos / 20 hilos) — la comparación que motivó la migración:

| Backend | 50 triángulos / RGB | 200 triángulos / HCL |
|---|---|---|
| pillow, 1 proceso | 2,05 s | 11,62 s |
| pillow, 10 procesos | 3,00 s | 5,85 s |
| rust, 1 thread | 0,32 s | 1,27 s |
| rust, 20 threads | **0,22 s (9,4×)** | **0,88 s (13,2×)** |

Una corrida completa de 500 generaciones pasó de **52,9 s a 4,57 s**, y con
mejor fitness (0,976 contra 0,946) porque el rasterizador propio cubre el
triángulo y no su contorno.

Dos notas honestas sobre estos números:

- **`pillow` con 10 procesos podía ser más lento que con 1.** Con triángulos
  chicos el costo de `spawn` y de picklear individuos superaba lo que ganaba.
- **El cuello de botella se movió.** Con Rust, evaluar pasó de 89,7% a 16% del
  tiempo, y ahora domina la mutación `non_uniform` (53%), que hace ~55.000
  llamadas a `rng.random()` por generación en Python puro. Moverla a Rust
  exigiría replicar el Mersenne Twister de CPython para no romper la
  reproducibilidad por seed; queda fuera de alcance a propósito.

## Espacio de color (`problem.params.color_space`)

Los 3 genes de color de cada figura (más el alpha, que siempre es lineal) se
interpretan según el espacio elegido, sin importar si la figura es un
triángulo o un óvalo. **El genotipo no cambia**: sigue siendo el mismo vector
plano en `[0,1]` (con el tamaño de bloque que le toque a `shape_type`) y ningún
operador se entera. Lo que cambia es la *geometría* del espacio de búsqueda —
qué colores quedan cerca entre sí bajo mutación y cruza.

| `color_space` | Genes | Qué mueve una mutación |
|---|---|---|
| `"rgb"` (default) | `r, g, b` | Los tres primarios por separado. |
| `"hsv"` | `h, s, v` | Tono / saturación / valor. Todo el cubo es válido. |
| `"hcl"` | `h, c, l` | Tono / colorido / luminosidad **perceptuales**: cambiar el tono no altera la luminosidad que el triángulo ya había encontrado. |

`hcl` es CIE LCh(ab) (forma polar de CIELAB con blanco D65, igual que `lch()` de
CSS Color 4). Como ~40% de la caja `H x C x L` cae fuera del gamut sRGB, esos
colores se traen **bajando el croma** a tono y luminosidad constantes (bisección),
en vez de clampear los canales RGB: clampear distorsiona los tres ejes a la vez y
colapsa regiones grandes de la caja en el mismo color, aplanando el fitness en
`H`, `C` y `L` por igual; bajar el croma deja la meseta confinada al eje `C`.

Es transversal a la exportación e importación: `figures.json` siempre guarda
colores RGB, así que un export hecho con un espacio se puede importar con otro y
se re-renderiza idéntico píxel a píxel. Un config sin `color_space` se comporta
exactamente igual que antes de que existiera la opción.

## Formas (`problem.params.shape_type`)

Opcional, default `"triangle"` (lo de siempre, sin cambios). Los otros dos
valores:

| `shape_type` | Genes por figura | Qué es cada una |
|---|---|---|
| `"triangle"` (default) | 10: `x1,y1,x2,y2,x3,y3, r,g,b, a` | Sin cambios respecto de antes de esta opción. |
| `"oval"` | 9: `cx,cy,rx,ry,θ, r,g,b, a` | Una elipse. |
| `"both"` | 11: `kind, p0..p5, r,g,b, a` | Cada figura es triángulo u óvalo según el gen discreto `kind` (0/1). |

En `"both"`, `kind` es un gen más — lo mutan los mismos operadores que mutan
cualquier otro gen discreto (`gene`, `multigene`, `uniform`, `non_uniform`), sin
ningún operador nuevo. Qué proporción de triángulos y óvalos termina teniendo
el mejor individuo lo decide la búsqueda, generación a generación, no un ratio
fijo del config. `p0..p5` son 6 slots genéricos: un bloque `kind=0` los lee
como los 6 vértices del triángulo; un bloque `kind=1` los lee como
`cx,cy,rx,ry,θ` (el sexto slot queda sin usar mientras el bloque sea un óvalo,
pero sigue mutando — no se congela). El alpha es siempre el último gen del
bloque en los tres modos, así que `initial_alpha` funciona igual sin saber qué
hay en el resto del bloque.

`θ` se lee como `[0, π)`, no `[0, 2π)`: una elipse es igual a sí misma rotada
180°, así que el giro completo desperdiciaría la mitad del rango de mutación en
duplicados visuales. `rx`/`ry` escalan igual que cualquier coordenada
(`allele * ancho` / `allele * alto`) en vez de tener un tope propio.

Cruza y selección no cambian nada: cortan en múltiplos de `block_size` e
intercambian bloques enteros, así que en `"both"` ya intercambian "una figura
completa, con su tipo incluido" sin ningún caso especial. `figures.json` marca
cada figura con `"type": "triangle"` o `"type": "oval"`; `import` acepta un
export con cualquier mezcla de los dos si la corrida usa `shape_type: "both"`,
y exige que todas las figuras sean del tipo correspondiente si usa `"triangle"`
u `"oval"` a secas.

## Tests

```bash
python -m pytest tests/ -v
```

40 tests sobre los operadores de `ga/operators/` (selección, cruza, mutación,
supervivencia, corte). Son deterministas: en vez de sembrar un `random.Random`
real y comprobar una distribución, usan un stub de `Rng` con valores
pre-programados (`tests/conftest.py::ScriptedRandom`) que además registra con
qué argumentos fue llamado — así cada test verifica un resultado exacto
(p. ej. los *weights* que `boltzmann`/`ranking` le pasan a `rng.choices`, o
que un bloque nunca se parte a mitad en `crossover` con granularidad
`"block"`) sin depender de la suerte de una semilla.

Los otros 73 cubren el plug-in `triangles`: espacios de color, export, engine y
métricas. Tres archivos (`test_renderers.py`, `test_problem.py`,
`test_native_parity.py` — 34 tests) necesitan la extensión nativa compilada y se
**saltean** en bloque si no está, en vez de romper: sin ella la suite corre
79 passed, 3 skipped.

## Agregar un operador nuevo

Cada operador se registra con un decorador en su propio módulo — no hay que
tocar `ga/config.py` ni `ga/registry.py`:

```python
# ga/operators/mutation.py
@register("mutation", "mi_mutacion")
def mi_mutacion(individual: Individual, rng: Rng, params: dict) -> Individual:
    ...
```

Dado de alta ahí, queda disponible en `config.json` como
`"operators.mutation.name": "mi_mutacion"` sin tocar nada más.
