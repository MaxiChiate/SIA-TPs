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
  operators/            # selection, crossover, mutation, survival, stopping
  registry.py           # nombre en config -> implementación
  config.py             # parseo + validación -> ConfigError
  metrics.py            # GenerationRecord + mean / std / genotypic_diversity + record_for
problems/
  triangles/            # genotype, renderers (delega a rust/), colorspace, problem, export  [Pillow: solo I/O]
rust/                   # crate PyO3 del backend nativo: color, raster, score  (obligatorio, no opcional)
build.py                # CLI: compila rust/ y verifica el binario resultante
simulate.py             # CLI: corre el AG, escribe solo datos (no dibuja)
render_final.py         # CLI: final.png desde un directorio de resultados
render_snapshots.py     # CLI: snapshots/ + progress.gif desde ese directorio
run.py                  # CLI: las tres etapas juntas
pipeline.py             # las etapas, implementadas una sola vez
config.json.example
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
- **Tasa de mutación invariante al largo del genoma** (`mutations_per_child` en
  `operators.mutation.params`): `pm` es la probabilidad por tirada y todos los operadores salvo
  `gene` tiran una vez por locus, así que las mutaciones esperadas por hijo son
  `pm × 10 × triangle_count` — subir los triángulos multiplicaba la mutación sin que se viera en
  el config. Medido (argentina, 1000 generaciones, RMSE @640×400): con `pm=0.05` fijo, 500
  triángulos daba **peor** que 50 (18,59 contra 16,69); fijando 25 mutaciones/hijo el orden se
  endereza y 500 pasa a ser el mejor (15,29). La normalización vive en `_rate()`
  (`ga/operators/mutation.py`) y es genérica — divide por la cantidad de tiradas que ese
  operador va a hacer (loci, o bloques para `uniform`), sin saber nada de triángulos, así que la
  frontera `ga/` ↔ dominio se mantiene.
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

Los seis bloques están hechos: core, config+registry, operadores, plug-in `triangles`, tests
(118 pasando) y la salida de métricas. El backend nativo de `rust/` reemplazó al camino
Pillow del todo.

## Método de trabajo

Frenar entre cada bloque para revisión. Justificar cada decisión de diseño en una línea. Si
algo tiene más de una forma razonable de resolverse, plantear las opciones en vez de elegir
solo.

## Cómo correr

```bash
cd TP2
../.venv/bin/python build.py                      # compila rust/ y verifica el binario
../.venv/bin/python run.py config.json            # simular + dibujar, de un saque
```

Una corrida son tres etapas separables (ver "Etapas separadas" abajo):
`simulate.py` (solo datos), `render_final.py`, `render_snapshots.py`.

Uso del motor como librería: instanciar un `Problem`, un `EngineConfig` con los callables de
selección/cruza/mutación/supervivencia + `Pc`/`Pm`/`max_generations`, un `Rng` con
`make_rng(seed)`, y llamar `Engine(problem, config, rng).run()` → `RunResult` (mejor
individuo, generación en que apareció, criterio de corte, evaluaciones, tiempo, `history` de
`GenerationRecord`).

Tests: `../.venv/bin/python -m pytest` desde `TP2/` (118 casos, deterministas).
Dependencias del dominio y tests: `../.venv/bin/pip install -r requirements.txt`.

## Importar un individuo inicial

El config admite un campo opcional de nivel raíz `"import"`: la ruta a un
`triangles.json` de un run previo (mismo `triangle_count`). Si se completa, ese
individuo reemplaza a uno de los `n` individuos aleatorios de la generación 0
(`EngineConfig.seed_individual`, `ga/core/engine.py`); vacío o ausente (`""`)
deshabilita la importación. La decodificación (`TrianglesProblem.
individual_from_export`, `problems/triangles/problem.py`) normaliza los
vértices en píxeles contra la resolución **nativa** de `image_path` — el
tamaño con el que las etapas de render exportan por defecto. Un `triangles.json` exportado
con `--export-width`/`--export-height` explícitos no decodifica bien.

## Perillas que no hacen nada (y por qué no están en el config)

- **`engine.processes` salió de `config.json` y de `config.json.example`.** Sigue existiendo
  en `EngineConfig.workers` porque es genérico del motor, pero para `triangles` no puede
  hacer nada: `owns_parallelism()` da `True` y el `Evaluator` nunca abre el pool. Tenerlo en
  `1` no era más honesto que omitirlo — se leía como si estuviera configurando algo. Pedir
  más de 1 en un problema que paraleliza solo ahora **avisa** (`UserWarning`) en vez de
  degradar en silencio: una config que pide paralelismo que no va a recibir tiene que decirlo
  antes de la corrida, no después.
- **`problem.params.threads` sí gobierna el paralelismo real** (default `0` = uno por core).
  Se valida en el dominio (`_threads`, `problems/triangles/problem.py`) para que un valor malo
  nombre la clave del config en vez de tirar el error crudo de PyO3, y pedir más threads que
  CPUs lógicas avisa: sobre-suscribir agrega cambios de contexto a un kernel ya limitado por
  memoria. Medido en 10 cores físicos / 20 lógicos con `k=25`: 12 threads dan 6,2× y 20 dan
  6,5×, así que los últimos 8 compran 0,3%.
- **`engine.pm` queda inerte cuando `mutation.params.mutations_per_child` está puesto**
  (`_rate()` le da prioridad). Ese sí sigue en el config porque otros operadores de mutación
  (`gene`) lo leen.

## Etapas separadas (`pipeline.py`)

Una corrida se divide en tres etapas, implementadas una sola vez en `pipeline.py`; los cinco
scripts de `TP2/` son CLIs finitos sobre esas funciones, así que el camino de un comando no
puede divergir del camino por partes.

- `build.py` — `maturin develop` desde `rust/`, siempre `--release`, con `VIRTUAL_ENV`
  derivado del intérprete; después importa la extensión **en un subproceso** (el padre puede
  tener una vieja cargada) y reporta `build_info()`/`schema_version()`. `--check` solo verifica.
- `simulate.py` — corre el AG y escribe `history.csv`/`.json`, `summary.json`, `best.json`,
  `triangles.json` y, con `--snapshot-every N`, `checkpoints.jsonl`. **No dibuja nada.**
- `render_final.py` / `render_snapshots.py` — leen el directorio de resultados y dibujan.

**Por qué se separó**: `on_generation` renderizaba un PNG a resolución nativa *adentro* del
loop cronometrado, así que `elapsed_seconds` incluía trabajo ajeno al algoritmo (medido:
31,7 s de AG contra 5,9 s de dibujar 31 snapshots, un 19%). Hoy `simulate.py` solo guarda una
**referencia** al mejor individuo de cada N generaciones — los operadores nunca mutan in
place, así que checkpointear no le cuesta nada al loop — y las vuelca al terminar.
`--progress-every N` / `--quiet` hace lo mismo con los prints.

**`checkpoints.jsonl` guarda alelos crudos, no el export de `triangles.json`**: ese export
normaliza vértices contra la resolución nativa y solo decodifica exacto para un export de
tamaño default, mientras que los alelos en `[0,1]` son independientes de la resolución por
construcción. Se redondean a 8 decimales (a 4096 px de export son 4e-5 de un píxel) porque
existen para dibujarse; `best.json` va a precisión completa porque es el resultado de la
corrida y puede volver a entrar por `import`.

**Las etapas de render no necesitan el config**: reconstruyen el problema desde el bloque
`config` de `summary.json`, para que la imagen la dibuje el mismo kernel, espacio de color y
`triangle_count` que la puntuó.
