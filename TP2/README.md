# TP2 · Algoritmos Genéticos — aproximación de imagen con triángulos

Motor de Algoritmos Genéticos genérico (implementación propia, sin DEAP/pygad)
que aproxima una imagen dibujando `T` triángulos translúcidos de color
uniforme sobre un canvas. Enunciado en
[`docs/SIA - TP2 - 2026 2Q.pdf`](docs/SIA%20-%20TP2%20-%202026%202Q.pdf).
El detalle de cada decisión de diseño está en [`CLAUDE.md`](CLAUDE.md).

```
run.py                  CLI: python run.py [config.json]
config.json.example     config de referencia (copiar a config.json)
requirements.txt        pillow, numpy, pytest (el core de ga/ no los usa)
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
  triangles/               plug-in de dominio (Pillow/numpy viven solo acá)
    genotype.py             alelos [0,1] <-> Triangle, GeneSchema (10 genes/triángulo)
    renderer.py               pinta triángulos translúcidos sobre un canvas
    fitness.py                 1 - MSE normalizado contra la imagen objetivo
    problem.py                  TrianglesProblem(Problem)
    export.py                    render full-res + enumeración JSON + native_resolution
images/                   imágenes de referencia (argentina.png, starry_night.png)
tests/                    tests unitarios de los operadores (pytest, deterministas)
```

## Arranque rápido

```bash
python3 -m venv .venv                 # crear un entorno virtual
source .venv/bin/activate             # activarlo (Windows: .venv\Scripts\activate)
pip install -r requirements.txt       # pillow, numpy, pytest

cp config.json.example config.json    # ajustá imagen, triangle_count, operadores, etc.
python run.py                         # usa ./config.json
python run.py otra_config.json
```

`python run.py` a secas escribe la imagen final y las métricas, nada más. Para
que la corrida genere **todo** — snapshots intermedias y el gif del proceso
incluidos — hay que pedirle las snapshots:

```bash
python run.py config.json --out results/prueba \
  --snapshot-every 25 --export-width 600 --export-height 475
```

Cada corrida escribe en un directorio de resultados
(`results/<config>_<timestamp>/` por default, o `--out DIR`):

- `final.png` — mejor individuo, renderizado a la resolución nativa de la
  imagen fuente (o `--export-width`/`--export-height`).
- `snapshots/gen_NNNNN.png` — solo si se pasa `--snapshot-every N`.
- `progress.gif` — animación del proceso: un frame por snapshot más
  `final.png` al cierre, sostenido unos segundos antes de que el loop vuelva a
  empezar. Se arma solo cuando hay snapshots; `--no-gif` lo desactiva y
  `--gif-frame-ms` / `--gif-hold-ms` ajustan los tiempos (default 120 ms por
  frame, 3000 ms de cierre).
- `triangles.json` — triángulos del mejor individuo (vértices + color RGBA).
- `history.csv` / `history.json` — una fila por generación: fitness
  mejor/promedio/desvío/peor, diversidad genotípica, evaluaciones y tiempo
  acumulados.
- `summary.json` — fitness final, generación en que apareció, criterio de
  corte que disparó, evaluaciones/tiempo totales, config completo + seed, y un
  bloque `problem` con lo que **realmente** corrió: `work_resolution` resuelta,
  backend elegido, flags con los que se compiló y threads. `config` es lo que se
  pidió; `problem` es lo que pasó, y difieren en todo lo que sea `"auto"` o
  `"native"`.

Imprime el fitness mejor/promedio de cada generación a medida que corre, y
deja los siete artefactos en `results/prueba/`.

Sobre `--export-width`/`--export-height`: sin ellos cada snapshot se renderiza a
la resolución nativa de la imagen fuente, y en un gif de 20 frames eso se nota
(`images/starry_night.png` es 1200×950 → gif de varios MB). Achicar el export
no toca la evaluación, que corre a `work_resolution` y es otra cosa.

### Correr con el backend nativo (Rust)

Opcional, pero es ~10× más rápido (ver [Backend de render](#backend-de-render)).
Como el default es `"renderer": "auto"`, alcanza con compilar la extensión una
vez: el `config.json` no cambia y `python run.py` pasa a usarla sola.

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh   # una sola vez
. "$HOME/.cargo/env"                   # rustup no toca el PATH de la shell ya abierta
source .venv/bin/activate              # maturin compila contra el venv activo
pip install maturin
cd rust && maturin develop --release   # desde rust/ y con --release: las dos cosas importan
cd .. && python run.py                 # "auto" ahora resuelve a rust
```

Para confirmar que quedó compilada, y con qué flags:

```bash
python -c "import triangles_native as n; print(n.version(), n.build_info())"
```

Sin toolchain de Rust no hay nada que hacer: `python run.py` sigue funcionando
con Pillow. Para fijar el backend en vez de depender de `auto`, poné
`"renderer": "rust"` (o `"pillow"`) en `problem.params`.

## `config.json`

```json
{
  "seed": 42,
  "engine": {
    "n": 100,
    "k": 100,
    "pc": 0.85,
    "pm": 0.05,
    "max_generations": 500,
    "processes": 1
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
      "params": {"b": 2.0}
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
      "triangle_count": 50,
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
  `pm`, `max_generations` (tope duro, además de cualquier `stopping`),
  `processes` (opcional, default `1`) — cantidad de procesos en paralelo para
  evaluar los individuos de una generación; cada individuo sin fitness
  cacheado se renderiza y evalúa en su propio proceso worker, y el engine
  espera a que termine toda la tanda antes de avanzar a la siguiente
  generación. Con `1` corre todo en el proceso principal, sin overhead de
  `multiprocessing`.
- **`operators.{parent_selection,crossover,mutation,survival}`**: `name` +
  `params` propios de ese operador, resueltos por nombre vía `ga/registry.py`.
  Los `params` de las cuatro categorías se mergean en un único dict que el
  engine le pasa a cada operador junto con `generation`/`max_generations`/
  `history` — por eso `boltzmann` puede leer `t0`/`tmin`/`tau` sin que el
  engine sepa nada de annealing.
- **`stopping`**: lista de criterios adicionales, evaluados en orden y
  combinados por OR entre sí y con `max_generations`.
- **`problem`**: `type` (hoy solo `"triangles"`) + `params` — `image_path`,
  `triangle_count`, `work_resolution` (resolución chica para evaluar fitness;
  el genotipo es independiente de la resolución), `background_rgb`,
  `color_space` (opcional, default `"rgb"`), `initial_alpha` (opcional,
  default `1.0`; ver "El piso de fitness") y `renderer` / `threads`
  (opcionales; ver "Backend de render").

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

Lo cual tiene sentido: reescalar el target a 128×80 lo *borronea*, y un target
borroso es justo lo que 50 triángulos planos pueden aproximar. A resolución
nativa el fitness persigue detalle que la representación no puede representar.
`"native"` empieza a valer la pena cuando hay triángulos de sobra — es la opción
honesta para una corrida final, no para iterar.

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

## Backend de render

Rasterizar y comparar píxeles es ~90% del tiempo de una corrida, así que es el
único lugar donde hay más de una implementación. Se elige con
`problem.params.renderer` y nada aguas arriba se entera:

| `renderer` | Qué usa |
|---|---|
| `"auto"` (default) | `rust` si la extensión está compilada, `pillow` si no. |
| `"pillow"` | La implementación original. Es el **oráculo de referencia** contra el que se valida Rust, y el fallback que no necesita toolchain. |
| `"rust"` | La extensión nativa `triangles_native`. Falla con un error claro si no está compilada. |

`problem.params.threads` (default `0` = uno por core) son los threads de rayon
que usa el backend nativo. Cuando corre Rust, el motor **no** abre su pool de
procesos: el backend declara que ya se hace cargo del paralelismo, y apilar
procesos sobre threads solo sobre-suscribe la CPU. O sea: `engine.processes`
manda con `pillow`, `problem.params.threads` manda con `rust`.

### Compilar el backend nativo

Los comandos están en
[Arranque rápido](#correr-con-el-backend-nativo-rust). Dos cosas que arruinan el
build en silencio:

- **`--release` no es opcional.** Un build de debug del kernel es más lento que
  el Pillow que reemplaza; `build_info()` arranca con `debug` o `release` según
  cuál quedó instalado.
- **Hay que correrlo desde `rust/`.** Cargo busca `.cargo/config.toml` desde su
  directorio de trabajo hacia arriba, no desde el manifest, así que
  `maturin develop -m rust/Cargo.toml` compila **sin** `target-cpu=x86-64-v3`.
  `build_info()` reporta las features realmente compiladas: si no dice
  `avx2`, el flag no se aplicó.

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
CARGO_BUILD_JOBS=20 maturin develop --profile parallel   # 20 = hilos de la máquina
```

`CARGO_BUILD_JOBS` es opcional: Cargo ya lanza un job por CPU lógica. Los flags
de [`rust/.cargo/config.toml`](rust/.cargo/config.toml) (`target-cpu`) aplican
igual, porque no dependen del perfil.

Medido en el mismo Ryzen AI 9 365 (20 hilos), recompilando solo el crate:
**3,4 s con `--release`** (un core ocupado) contra **2,3 s con `parallel`**
(~4 cores). Es un crate de cuatro archivos: la diferencia es de ~1,5x, no de un
orden de magnitud.

El binario que sale puede ser algo más lento que el de `--release`, y
`build_info()` no los distingue (dice `release` en los dos, porque solo mira
`debug_assertions`). Para medir tiempos o generar números de informe, compilá
con `--release`.

### Equivalencia entre backends

Los dos rasterizadores **no** dan los mismos píxeles: `ImageDraw.polygon` pinta
el contorno además del interior, así que cubre entre 7% y 30% más área por
triángulo que una regla top-left estándar. Son dos funciones objetivo parecidas
pero distintas, y `tests/test_native_parity.py` mide la diferencia en vez de
disimularla:

- **Decodificación de color: exacta.** Los tres espacios coinciden bit a bit con
  la implementación Python sobre todo el cubo de alelos (`==`, sin tolerancia).
- **Puntajes: estadística.** Sobre 120 genomas por espacio, el error cuadrático
  difiere como máximo 3%, con sesgo medio de −0,4% a −0,9% (Rust cubre un poco
  menos), y la **correlación de rangos es 0,997–0,999**. Eso último es lo que
  importa: la selección solo consume el *orden* de los fitness.
- **Prueba end-to-end.** Misma seed y mismo presupuesto: el mejor individuo que
  encuentra el motor con Rust, puntuado con el oráculo Pillow, da **0,895**
  contra **0,879** del que encuentra Pillow — igual de bueno o mejor bajo la
  métrica original, en 9,5× menos tiempo.
- **Invariancia de threads: exacta.** El paralelismo es solo *entre* individuos
  y el kernel por individuo es secuencial, así que el resultado no depende de
  `threads`. La reproducibilidad por seed se mantiene.

Los fitness de las dos implementaciones no son comparables entre sí: hay que
generar todo el material de un informe con un solo backend. El bloque `problem`
de `summary.json` registra cuál corrió, con qué flags y con cuántos threads.

### Rendimiento medido

25 generaciones, `n=k=100`, resolución de trabajo 128×80, en un Ryzen AI 9 365
(10 núcleos / 20 hilos):

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

- **`pillow` con 10 procesos puede ser más lento que con 1.** Con triángulos
  chicos el costo de `spawn` y de picklear individuos supera lo que gana.
- **El cuello de botella se movió.** Con Rust, evaluar pasó de 89,7% a 16% del
  tiempo, y ahora domina la mutación `non_uniform` (53%), que hace ~55.000
  llamadas a `rng.random()` por generación en Python puro. Moverla a Rust
  exigiría replicar el Mersenne Twister de CPython para no romper la
  reproducibilidad por seed; queda fuera de alcance a propósito.

## Espacio de color (`problem.params.color_space`)

Los 3 genes de color de cada triángulo (más el alpha, que siempre es lineal) se
interpretan según el espacio elegido. **El genotipo no cambia**: sigue siendo el
mismo vector plano de `10*T` alelos en `[0,1]` y ningún operador se entera. Lo
que cambia es la *geometría* del espacio de búsqueda — qué colores quedan cerca
entre sí bajo mutación y cruza.

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

Es transversal a la exportación e importación: `triangles.json` siempre guarda
colores RGB, así que un export hecho con un espacio se puede importar con otro y
se re-renderiza idéntico píxel a píxel. Un config sin `color_space` se comporta
exactamente igual que antes de que existiera la opción.

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
