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
  corte que disparó, evaluaciones/tiempo totales, config completo + seed.

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
      "color_space": "rgb"
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
  `color_space` (opcional, default `"rgb"`) y `renderer` / `threads`
  (opcionales; ver "Backend de render").

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
generar todo el material de un informe con un solo backend. `summary.json`
registra cuál corrió.

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
