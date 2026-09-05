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
analysis/                runner de experimentos (corre muchas configs y compara)
  main.py                 CLI: python3 analysis/main.py [sweep.json]
  config.py                SweepConfig + overrides por ruta con puntos
  runner.py                 orquestador paralelo (un proceso por corrida)
  records.py                 esquema de summary.csv e history.csv
  sweep.json                  serie A de ejemplo: los 7 métodos de selección
  plots_data.py                carga de los CSVs y promedio por seed
  plots_style.py                paleta validada + layout base
  plots_main.py                  CLI de los gráficos
  results/                        CSVs y HTMLs generados (gitignoreados)
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

Cada corrida escribe en un directorio de resultados
(`results/<config>_<timestamp>/` por default, o `--out DIR`):

- `final.png` — mejor individuo, renderizado a la resolución nativa de la
  imagen fuente (o `--export-width`/`--export-height`).
- `snapshots/gen_NNNNN.png` — solo si se pasa `--snapshot-every N`.
- `triangles.json` — triángulos del mejor individuo (vértices + color RGBA).
- `history.csv` / `history.json` — una fila por generación: fitness
  mejor/promedio/desvío/peor, diversidad genotípica, evaluaciones y tiempo
  acumulados.
- `summary.json` — fitness final, generación en que apareció, criterio de
  corte que disparó, evaluaciones/tiempo totales, config completo + seed.

```bash
python run.py config.json --out results/prueba --snapshot-every 25 \
  --export-width 800 --export-height 500
```

Imprime el fitness mejor/promedio de cada generación a medida que corre.

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
      "background_rgb": [255, 255, 255]
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
  el genotipo es independiente de la resolución) y `background_rgb`.

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

## Tandas de experimentos

`run.py` corre **una** config. Para comparar métodos entre sí hace falta correr
muchas y juntar los resultados, y de eso se encarga `analysis/`:

```bash
python3 analysis/main.py                    # usa analysis/sweep.json
python3 analysis/main.py serie_cruza.json
python3 analysis/main.py --dry-run          # valida y muestra el plan, sin correr
```

El `analysis/sweep.json` que viene es la **serie A**: los 7 métodos de selección,
3 seeds cada uno, todo lo demás fijo. Un sweep declara una config base, qué
pisarle, y con qué seeds repetir:

```json
{
  "base_config": "config.json",
  "overrides": {"stopping": [], "engine.max_generations": 150},
  "seeds": [1, 2, 3],
  "workers": 4,
  "sweep": {
    "path": "operators.crossover.name",
    "values": ["one_point", "two_point", "uniform", "ring"]
  }
}
```

- **`overrides`**: se aplican a todas las variantes. Las claves son rutas con
  puntos hacia el config base (`engine.max_generations`,
  `operators.mutation.params`). Si la ruta no existe, falla al cargar.
- **`sweep`**: atajo para variar **una** perilla; genera una variante por valor.
- **`variants`**: la forma general, para cuando una variante necesita cambiar
  varias claves a la vez (ver `analysis/sweep.json`). Va `sweep` **o**
  `variants`, no los dos.
- **`seeds`**: cada variante corre una vez por seed. Con una sola seed no podés
  distinguir una diferencia real del azar.
- **`workers`**: corridas en paralelo. Cada corrida usa un proceso propio, así
  que el runner fuerza `engine.processes = 1` para no anidar pools.

Antes de correr nada valida **todas** las variantes contra `ga.config`, así un
nombre de operador mal escrito falla en el segundo cero y no a los 40 minutos.

Cada tanda escribe en `analysis/results/<sweep_id>/`:

- `summary.csv` — **una fila por corrida**: variante, seed, fitness final,
  generación en que apareció, criterio de corte, evaluaciones, tiempo,
  diversidad final. Es el CSV para comparar variantes entre sí.
- `history.csv` — **una fila por generación**, en formato largo, con
  `(variant, seed)` como identificador. Es el CSV para las curvas de fitness y
  diversidad a lo largo del tiempo.
- `resolved.json` — el config completo que efectivamente corrió cada variante,
  para poder reproducir la tanda desde su propia salida.

Los CSVs se van escribiendo a medida que terminan las corridas, así que una
tanda interrumpida igual deja datos usables.

## Gráficos

Los CSVs de una tanda se dibujan con:

```bash
python3 analysis/plots_main.py                                  # la tanda más reciente
python3 analysis/plots_main.py analysis/results/20260905T0251Z  # una en particular
```

Deja tres HTML autocontenidos (plotly embebido, abren sin internet) al lado de
los CSVs de esa tanda:

- `fitness.html` — mejor fitness por generación, una línea por variante.
- `diversity.html` — diversidad genotípica por generación. Es el gráfico que
  muestra la **convergencia prematura**: si la curva se va a cero antes de que
  el fitness llegue a algo aceptable, la población se homogeneizó.
- `comparison.html` — fitness final por variante, con un círculo por seed y un
  rombo en la media.

Las seeds se promedian por generación, así que una variante es una línea. En
`comparison.html` no se promedian: se muestran una por una a propósito, porque
**si las seeds de una variante se dispersan más que la distancia entre dos
variantes, esa distancia no es un resultado**.

Ese gráfico es un dot plot y no barras por una razón: el fitness vive en una
franja angosta cerca de 1, así que un gráfico de barras necesitaría un eje
truncado para mostrar alguna diferencia — y una barra truncada miente sobre la
magnitud, porque el largo de la barra *es* el valor. Los puntos codifican
posición, así que un eje con zoom es honesto.

La paleta (`analysis/plots_style.py`) está validada para daltonismo: los colores
se asignan en orden fijo y cada variante conserva el suyo en los tres gráficos.
Pasadas 8 variantes conviene partir la tanda en vez de inventar un color nuevo.

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
