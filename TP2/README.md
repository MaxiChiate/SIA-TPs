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

```bash
python run.py config.json --out results/prueba --snapshot-every 25 \
  --export-width 800 --export-height 500
```

Imprime el fitness mejor/promedio de cada generación a medida que corre, y
deja el `progress.gif` de esa corrida en `results/prueba/`.

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
  el genotipo es independiente de la resolución), `background_rgb` y
  `color_space` (opcional, default `"rgb"`; ver abajo).

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
