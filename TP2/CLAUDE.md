# TP2 SIA — Motor de Algoritmos Genéticos (aproximación de imagen con triángulos)

Materia: Sistemas de Inteligencia Artificial (ITBA). Enunciado en `docs/SIA - TP2 - 2026 2Q.pdf`.

## Objetivo

Motor de AG **genérico** que recibe una imagen y una cantidad `T` de triángulos y busca la
mejor aproximación a esa imagen dibujando `T` triángulos de color uniforme, translúcidos
(RGBA), sobre un canvas blanco (configurable).

## Restricciones duras

- **La implementación de Algoritmos Genéticos es propia.** Nada de DEAP, pygad ni similares:
  selección, cruza, mutación, reemplazo y corte se escriben a mano.
- **Core del AG (`ga/`) con stdlib solamente.** Pillow y numpy únicamente en
  `problems/triangles/` (render y fitness). Nada del dominio "imagen/triángulo" puede aparecer
  dentro de `ga/`. El backend nativo (`rust/`) también vive detrás de esa frontera: solo lo
  importa `problems/triangles/renderers.py`, y el crate no contiene **nada** de AG — ni RNG, ni
  selección, ni cruza, ni mutación. El enunciado permite librerías externas para manejo de
  imágenes, no para el algoritmo genético.
- Identificadores, nombres de archivo y **comentarios en inglés**. Type hints y dataclasses.
  `from __future__ import annotations`. Funciones cortas, sin herencia profunda.
- `seed` obligatorio: misma seed + mismo config ⇒ mismo resultado, siempre. Una sola instancia
  de `Rng` (`random.Random`) inyectada por parámetro a engine y a todos los operadores; nadie
  llama al módulo `random` directo.
- No `git push` sin pedirlo explícitamente. Commits chicos y atómicos. Se trabaja en la rama
  `dev-ag`, no en `main`.

## Arquitectura

Motor genérico; el problema entra como plug-in vía la interfaz `ga.core.problem.Problem`
(expone el schema de genes, genera individuos aleatorios válidos, evalúa fitness). El engine
no sabe nada más.

```
ga/                     # motor genérico — solo stdlib
  core/
    rng.py              # Rng = random.Random ; make_rng(seed)
    gene.py             # Gene(name, lower, upper, kind) + GeneSchema(genes, block_size)
    individual.py       # Individual: alleles: list[float] + schema + fitness cacheado
    population.py       # Population(individuals, generation) — contenedor fino
    problem.py          # ABC Problem: schema / random_individual / evaluate / describe
    engine.py           # Evaluator (memo + contador), EngineConfig, Engine.run, RunResult, StopContext
  operators/            # (pendiente) selection, crossover, mutation, replacement, stopping
  registry.py           # (pendiente) nombre en config -> implementación
  config.py             # (pendiente) parseo + validación -> ConfigError
  metrics.py            # GenerationRecord + mean / std / genotypic_diversity + record_for
problems/
  triangles/            # genotype, renderer(s), fitness, colorspace, problem, export  [Pillow/numpy]
rust/                   # crate PyO3 del backend nativo: color, raster, score  (solo pixeles)
run.py                  # (pendiente) CLI: python TP2/run.py [config.json]
config.json.example     # (pendiente)
requirements.txt        # pillow, numpy, pytest  (el core no los usa)
```

## Genotipo (problema triangles)

Individuo = lista fija de `T` triángulos, cada uno 10 genes `x1,y1,x2,y2,x3,y3` + 3 canales
de color + `A`. Genotipo plano de `10*T` alelos. **Todos los alelos normalizados a `[0,1]`**; el renderer
escala a la resolución de trabajo (genotipo independiente de la resolución). El `GeneSchema`
del problema declara `block_size = 10`.

## Decisiones de diseño tomadas

- **RNG**: `Rng = random.Random` sin wrapper; ya trae `random/uniform/gauss/choice/sample/shuffle`.
- **Alelos en `[0,1]`** (coords + RGBA); el dominio discreto/continuo lo marca `Gene.kind` y
  `Gene.clamp` redondea si es `discrete`.
- **`GeneSchema.block_size`**: unidad de cruza. Por defecto **bloque-triángulo** (cortes en
  múltiplos de 10, preserva vértices+color juntos); modo `allele` (cortes en cualquier locus)
  configurable. Implementado una sola vez parametrizando el tamaño de bloque.
- **Individuos inmutables por convención**: los operadores devuelven uno nuevo con
  `fitness=None`; así el memo por genotipo nunca queda stale.
- **Fitness cacheado en dos niveles** (`Evaluator`): campo `fitness` del individuo +
  `dict[tuple, float]` compartido. `Evaluator.count` sube solo en llamadas reales a
  `problem.evaluate`. El render es el cuello de botella → además se trabaja sobre la imagen
  reescalada a una resolución chica configurable.
- **`params` por generación** que arma el engine (`generation`, `max_generations`, `history`):
  canal para Boltzmann y mutación no uniforme sin acoplar el engine a ellos.
- **`max_generations`** es tope duro en el engine, además del predicado `stopping` configurable
  (criterios combinables por OR: generaciones, tiempo, fitness aceptable, estructura, contenido).
- **Diversidad genotípica** = media de los desvíos estándar por locus (O(N·L), comparable
  entre corridas porque los alelos viven en `[0,1]`).
- **Backend de render intercambiable** (`problem.params.renderer`: `auto` default, `pillow`,
  `rust`) en `problems/triangles/renderers.py`, con la costura en la ABC `Problem`
  (`evaluate_batch` + `owns_parallelism`): el engine entrega una generación entera en una
  llamada y `ga/` no importa nada nuevo. Pillow queda como **oráculo de referencia**, no como
  camino co-mantenido. Medido: 9,4×–13,2× end-to-end, y la evaluación pasó de 89,7% a 16% del
  perfil (ahora domina la mutación).
- **Los dos rasterizadores no son equivalentes bit a bit** y no se pretende que lo sean:
  `ImageDraw.polygon` pinta el contorno además del interior. La equivalencia se defiende con
  correlación de rangos (0,997–0,999) y con una prueba end-to-end que puntúa al ganador de Rust
  con el oráculo Pillow. Los fitness de ambos backends no son comparables entre sí.
- **Espacio de color configurable** (`problem.params.color_space`: `rgb` default, `hsv`, `hcl`)
  en `problems/triangles/colorspace.py`: cambia cómo se leen los 3 genes de color, no el
  genotipo ni ningún operador — sirve para comparar geometrías del espacio de búsqueda. `hcl`
  es CIE LCh(ab)/D65; lo que cae fuera del gamut sRGB se resuelve **bajando el croma** a tono
  y luminosidad constantes (bisección), no clampeando canales, para no aplanar el fitness en
  los tres ejes a la vez. Conversiones en float escalar sin numpy, portables a C tal cual.

## Estado

- **Bloque 1 (Core)**: hecho. `ga/core/*`, `ga/metrics.py`, `requirements.txt`.
- Pendientes: 2) config + registry + validación + `config.json.example`; 3) operadores
  (selección → supervivencia → cruza → mutación → corte); 4) plug-in `triangles`; 5) tests
  unitarios de operadores; 6) `run.py` + salida de métricas.

## Método de trabajo

Frenar entre cada bloque para revisión. Justificar cada decisión de diseño en una línea. Si
algo tiene más de una forma razonable de resolverse, plantear las opciones en vez de elegir
solo.

## Cómo correr

Todavía no hay `run.py` (bloque 6). Por ahora:

```bash
cd TP2 && ../.venv/bin/python -c "import ga.core; print('ok')"   # el core importa (solo stdlib)
```

Uso del motor como librería: instanciar un `Problem`, un `EngineConfig` con los callables de
selección/cruza/mutación/supervivencia + `Pc`/`Pm`/`max_generations`, un `Rng` con
`make_rng(seed)`, y llamar `Engine(problem, config, rng).run()` → `RunResult` (mejor
individuo, generación en que apareció, criterio de corte, evaluaciones, tiempo, `history` de
`GenerationRecord`).

Tests (bloque 5, pendiente): `../.venv/bin/python -m pytest` desde `TP2/`.
Dependencias del dominio y tests: `../.venv/bin/pip install -r requirements.txt`.

## Importar un individuo inicial

El config admite un campo opcional de nivel raíz `"import"`: la ruta a un
`triangles.json` de un run previo (mismo `triangle_count`). Si se completa, ese
individuo reemplaza a uno de los `n` individuos aleatorios de la generación 0
(`EngineConfig.seed_individual`, `ga/core/engine.py`); vacío o ausente (`""`)
deshabilita la importación. La decodificación (`TrianglesProblem.
individual_from_export`, `problems/triangles/problem.py`) normaliza los
vértices en píxeles contra la resolución **nativa** de `image_path` — el
tamaño con el que `run.py` exporta por defecto. Un `triangles.json` exportado
con `--export-width`/`--export-height` explícitos no decodifica bien.

## Salida esperada (bloque 6)

`run.py` corre una config y emite en un directorio de resultados: imagen final (+ snapshots
opcionales cada X generaciones, y un `progress.gif` armado con esos snapshots + la imagen
final sostenida unos segundos), enumeración de triángulos del mejor individuo (vértices +
color) en JSON, log por generación en CSV/JSON (generación, mejor/promedio/desvío/peor
fitness, diversidad, evaluaciones acumuladas, tiempo acumulado), y un resumen final (mejor
fitness, generación en que apareció, criterio de corte que disparó, config completo + seed).
