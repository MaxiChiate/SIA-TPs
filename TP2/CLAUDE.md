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
  `problems/triangles/`, y solo para I/O de imágenes (abrir el target, export, GIF) y arrays -
  rasterizar y puntuar corren enteramente en `rust/`, no en Python. Nada del dominio
  "imagen/triángulo" puede aparecer dentro de `ga/`. El backend nativo (`rust/`) también vive
  detrás de esa frontera: solo lo importa `problems/triangles/renderers.py`, y el crate no
  contiene **nada** de AG — ni RNG, ni selección, ni cruza, ni mutación. El enunciado permite
  librerías externas para manejo de imágenes, no para el algoritmo genético.
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
  triangles/            # genotype, renderers (delega a rust/), colorspace, problem, export  [Pillow: solo I/O]
rust/                   # crate PyO3 del backend nativo: color, raster, score  (obligatorio, no opcional)
run.py                  # (pendiente) CLI: python TP2/run.py [config.json]
config.json.example     # (pendiente)
requirements.txt        # pillow, numpy, pytest, maturin  (el core no los usa)
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
- **El render corre solo en Rust, sin alternativa en Python.** Empezó como backend
  intercambiable (`problem.params.renderer`: `pillow`/`rust`/`auto`) mientras se migraba,
  validado contra el oráculo Pillow (correlación de rangos 0,997–0,999; medido 9,4×–13,2×
  end-to-end, evaluación de 89,7% a 16% del perfil). Una vez probada la migración, se sacó
  `PillowRenderer`, `renderer.py` (`ImageDraw.polygon`) y `fitness.py` (MSE en numpy) del todo
  en vez de mantenerlos como segunda implementación del mismo hot path — el `problem.params.
  renderer` de config también desapareció, no queda ninguna opción que elegir. La costura con
  `ga/` (`Problem.evaluate_batch` + `owns_parallelism`) no cambió: sigue siendo la única forma
  en que el engine sabe que una generación entera se resuelve en una llamada. `colorspace.py`
  sí sigue en Python (decodifica color para `export.py`/`individual_from_export`, caminos fríos
  que no compiten en el hot path), y `tests/test_native_parity.py` lo sigue validando bit a bit
  contra `triangles_native.to_rgb`.
- **Piso de fitness y `initial_alpha`**: `pixel_similarity` recorta en 0 todo lo que sea peor
  que el canvas vacío, y una población inicial de triángulos opacos al azar cae entera abajo de
  ese piso (medido: 0/50 con fitness > 0 en argentina/50/RGB y en argentina/200/HCL). Con todos
  empatados en 0 la selección no ordena nada y la corrida se queda quieta hasta que una mutación
  cruza de casualidad — o muere por `stagnation`. Se corrigió **sesgando solo la generación 0**
  (`problem.params.initial_alpha`, default `1.0` = sin sesgo) y no tocando la métrica: cambiar
  la normalización volvería incomparables todos los fitness ya medidos. El sesgo se aplica
  después de sortear el vector, así que la misma seed conserva coordenadas y colores.
- **`work_resolution` acepta `"native"`**: el fitness compara contra la imagen a resolución
  original, sin reescalado intermedio. Es un sentinel en el config y no un flag aparte porque
  el parámetro que ya existía es exactamente el que se está eligiendo. `describe()` reporta la
  resolución **resuelta**, y `run.py` vuelca ese `describe()` en `summary.json` (bloque
  `problem`, al lado del `config` crudo): una corrida tiene que registrar lo que corrió, no lo
  que se pidió, o sus números no se pueden reproducir ni comparar. Medido: el costo crece con
  los píxeles pero mucho más despacio (20× de resolución = 2,3× de tiempo) porque con el kernel
  nativo el cuello de botella son los operadores en Python; recién a resolución nativa vuelve a
  mandar el render.
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
