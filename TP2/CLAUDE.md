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
analysis/               # runner de experimentos + gráficos — capa por encima de run.py
  config.py             # SweepConfig + overrides por ruta con puntos
  runner.py             # orquestador paralelo (un proceso por corrida)
  records.py            # esquema de summary.csv (1 fila/corrida) e history.csv (1 fila/generación)
  main.py               # CLI: corre una serie
  plots_*.py            # CLI + datos + estilo de los tres gráficos
  serie_*.json          # una receta por serie (selección, cruza, mutación, ...)
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

Individuo = lista fija de `T` figuras. `problem.params.shape_type` (default `"triangle"`)
decide qué es cada figura y cuántos genes tiene su bloque — **todos los alelos normalizados a
`[0,1]`** en los tres modos; el renderer escala a la resolución de trabajo (genotipo
independiente de la resolución):

| `shape_type` | `block_size` | Layout |
|---|---|---|
| `triangle` (default) | 10 | `x1,y1,x2,y2,x3,y3, c1,c2,c3, a` |
| `oval` | 9 | `cx,cy,rx,ry,θ, c1,c2,c3, a` |
| `both` | 11 | `kind, p0..p5, c1,c2,c3, a` |

En `both`, `kind` es un gen discreto (0=triángulo, 1=óvalo) y `p0..p5` son 6 slots genéricos:
si `kind=0` se leen como los 6 vértices del triángulo; si `kind=1`, los primeros 5 como
`cx,cy,rx,ry,θ` (`p5` queda sin usar pero sigue mutando). El alpha es siempre el último gen
del bloque, en los tres modos — ver la entrada de diseño más abajo.

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
  `pm × 10 × shape_count` en modo triángulo — subir los triángulos multiplicaba la mutación sin que se viera en
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
- **Óvalos y modo mixto** (`problem.params.shape_type`: `triangle` default, `oval`, `both`) —
  el opcional del enunciado ("otros polígonos... u óvalos"). Bloque de tamaño fijo por modo en
  vez de genoma de longitud variable: la cruza corta en múltiplos de `block_size` asumiendo que
  ambos padres tienen el mismo largo (`ga/operators/crossover.py`), así que "cuántas figuras
  hay" tenía que seguir siendo un número fijo por `Problem` — lo que varía es *qué es* cada
  bloque, no cuántos hay. En `both` eso se resuelve con un gen discreto `kind` al principio del
  bloque (0=triángulo, 1=óvalo) + 6 slots genéricos que el decoder interpreta distinto según
  `kind` (padding de 1 slot cuando es óvalo, que sigue mutando aunque el decoder lo ignore).
  Ningún operador nuevo: `kind` es un gen discreto más, y los operadores de mutación existentes
  (`gene`, `multigene`, `uniform`, `non_uniform`) ya lo tratan como tal — qué proporción de
  triángulos y óvalos termina teniendo el mejor individuo lo decide la mutación generación a
  generación, no un ratio de config. `θ` se lee `[0,π)` y no `[0,2π)` porque una elipse es
  igual a sí misma rotada 180° — usar el giro completo desperdiciaría la mitad del rango de
  mutación en duplicados visuales; `rx`/`ry` escalan igual que cualquier coordenada
  (`allele × ancho/alto`) en vez de tener un tope propio. El alpha se mantiene como el último
  gen del bloque en los tres modos a propósito: es lo que deja que `initial_alpha` siga
  ubicándolo por `schema.block_size - 1` sin saber qué hay en el resto del bloque. La
  rasterización del óvalo en `rust/src/raster.rs` prueba pertenencia píxel a píxel dentro del
  bounding box rotado en vez del span-por-fila en punto fijo que usa el triángulo: sigue el
  mismo principio de "solo tocar el bounding box", pero sin el truco de resolver el span en
  forma cerrada — ese ahorro no era el cuello de botella compartido (`score_batch` ya paraleliza
  por individuo completo) y no valía la pena arriesgarlo sin poder correr `cargo test` al
  escribirlo.

- **`write_history` (config raíz, default `true`)**: si es `false`, `simulate()` no escribe
  `history.csv`/`history.json`. Es una clave de nivel raíz, como `import`, y no
  `engine.write_history` ni `problem.params`: no configura ni el motor ni el dominio, es una
  decisión de qué escribe la etapa `simulate` — `_write_history` vuelca `dataclasses.asdict`
  de cada `GenerationRecord` (`pipeline.py`), y con corridas largas o muchas generaciones ese
  archivo crece linealmente y nada lo vuelve a leer (`summary.json` y `best.json` ya alcanzan
  para reproducir o re-renderizar una corrida).

## Estado

Los seis bloques están hechos: core, config+registry, operadores, plug-in `triangles`
(triángulos, óvalos y modo mixto), tests y la salida de métricas. El backend nativo de
`rust/` reemplazó al camino Pillow del todo. `../.venv/bin/python -m pytest` da el conteo
vigente — sin el backend nativo compilado, los casos que necesitan `triangles_native` se
saltean en vez de fallar (ver "Cómo correr").

Agregado en la rama `dev-ag-analisis`: **`analysis/`**, el runner de experimentos y sus
gráficos. Es una capa estrictamente por encima de `run.py` — no toca `ga/` ni `problems/`.

## Pasos a seguir

La maquinaria está lista: agregar una serie es escribir una receta de ~6 líneas
(`analysis/serie_*.json`) y correr dos comandos (`analysis/main.py` y después
`analysis/plots_main.py`). No hace falta programar nada más — los tres gráficos salen solos de
cualquier serie.

1. **Correr las series que faltan.** Corridas: **cruza** y **mutación** (4 variantes x 10 seeds
   cada una). Faltan **selección**, **supervivencia**, **triángulos**, **población** y **espacio
   de color**; las siete recetas ya están escritas y validadas en `analysis/`. Regla: **una
   perilla por vez**, todo lo demás fijo, varias seeds, y `max_generations` fijo sin corte por
   fitness para que todas las corridas hagan el mismo trabajo.
2. **Ejercicio 1.** El del mapa NxN de caracteres ASCII. No se implementa, se piensa — pero es
   entregable y hay que responderlo en la presentación.
3. **Presentación.**

### Resultados hasta ahora

> **La serie de selección corrida el 2026-09-05 (3 seeds) quedó invalidada.** Se corrió antes
> del cambio de fitness (`ff952f9`) y del fix de la selección de padres (`6c9f297`), así que sus
> números están en otra escala y con otro consumo del RNG. Hay que volver a correrla; la receta
> ya está en 10 seeds.

**Cruza** (4 métodos x 10 seeds, 150 generaciones):

- `uniform` 0.9565 · `ring` 0.9433 · `two_point` 0.9402 · `one_point` 0.9299.
- Gana la uniforme, lo que contradice la intuición del teorema de esquemas. La explicación es
  propia de este problema: **el orden de los triángulos en el genotipo no codifica nada**, así
  que no hay bloques contiguos que romper y solo queda su ventaja de mezcla. Es la respuesta al
  "decidir qué método de cruza usarían en diferentes circunstancias y por qué" de la consigna.
- Hay solape entre seeds: gana en media, no en todas las corridas.

**Mutación** (4 operadores x 10 seeds, igualados en alelos tocados por hijo):

- `non_uniform` 0.9299 · `gene` 0.8202 · `multigene` 0.7139 · `uniform` 0.6873.
- **Concluyente**: la peor seed de `non_uniform` supera a la mejor de `gene`, y la peor de
  `gene` a la mejor de `multigene`. No se solapan.
- Perturbar el alelo le gana a reemplazarlo por lejos: reemplazar 25 alelos por hijo destruye lo
  que la selección venía construyendo.
- **`multigene` tiene la diversidad más alta (0.153) y el anteúltimo fitness.** Es el
  contraejemplo de "más diversidad es mejor": nunca converge, es búsqueda aleatoria cara. Buen
  material para la presentación junto al extremo opuesto (`one_point`, diversidad 0.0016).

**Control de reproducibilidad, gratis:** la variante `one_point` de la serie de cruza y la
variante `non_uniform` de la de mutación son la misma configuración, corridas en series
distintas. Dieron el mismo valor hasta el último decimal.

### Pendientes técnicos

Detectados en revisión; ninguno bloquea los experimentos, pero conviene resolverlos o tener la
respuesta lista para la defensa.

- **Escala del fitness: resuelto** por `ff952f9`. Era `1 - MSE/255²`, que vivía en `[0.85, 1.0]`
  y dejaba a ruleta y Boltzmann —que dependen de las *diferencias absolutas* de fitness— casi
  uniformes. Ahora se normaliza contra el error del canvas vacío, así que `0` = "no mejor que no
  dibujar nada". Queda **revisar las temperaturas de Boltzmann** de
  `analysis/serie_seleccion.json` (`t0=0.5, tmin=0.02`): se eligieron para la escala vieja y con
  la nueva pueden no ser las adecuadas.
- **La función de fitness no es elegible por config.** Hay una sola, en `rust/src/score.rs`.
  Para poder experimentar sobre ella (MAE vs MSE, comparación por bloques de píxeles) habría que
  resolverla por nombre desde el registry, igual que los operadores. **La consigna no lo pide**,
  así que es opcional.
- **`exclusive` no cubre `K <= N`.** El PPT define que en ese caso la nueva generación son los K
  hijos + (N−K) de la generación actual; hoy `ga/operators/survival.py` tira `ValueError`.
- **`stagnation` mal etiquetado.** Su docstring dice "structure-based", pero mide que el mejor
  fitness no mejore: eso es **contenido**. Falta un criterio de estructura propiamente dicho
  (la diversidad ya la calcula `ga/metrics.py`).
- **Nombres de mutación vs. el PPT.** Lo que el PPT llama "uniforme" (cada gen con prob. Pm) es
  nuestro `multigene`; nuestro `uniform` es por bloque y no figura en el PPT. Falta "multigen
  limitada". Renombrar, o aclararlo explícitamente en la presentación.

## Método de trabajo

Frenar entre cada bloque para revisión. Justificar cada decisión de diseño en una línea. Si
algo tiene más de una forma razonable de resolverse, plantear las opciones en vez de elegir
solo.

## Cómo correr

```bash
cd TP2
../.venv/bin/python build.py                      # compila rust/ y verifica el binario
../.venv/bin/python run.py config.json            # simular + dibujar, de un saque

../.venv/bin/python analysis/main.py              # una serie -> analysis/results/<sweep_id>/
../.venv/bin/python analysis/main.py --dry-run    # valida el sweep y muestra el plan
../.venv/bin/python analysis/plots_main.py        # dibuja la serie más reciente
```

Una corrida son tres etapas separables (ver "Etapas separadas" abajo):
`simulate.py` (solo datos), `render_final.py`, `render_snapshots.py`.

Uso del motor como librería: instanciar un `Problem`, un `EngineConfig` con los callables de
selección/cruza/mutación/supervivencia + `Pc`/`Pm`/`max_generations`, un `Rng` con
`make_rng(seed)`, y llamar `Engine(problem, config, rng).run()` → `RunResult` (mejor
individuo, generación en que apareció, criterio de corte, evaluaciones, tiempo, `history` de
`GenerationRecord`).

Tests: `../.venv/bin/python -m pytest` desde `TP2/`, deterministas.
Dependencias del dominio y tests: `../.venv/bin/pip install -r requirements.txt`.

## Importar un individuo inicial

El config admite un campo opcional de nivel raíz `"import"`: la ruta a un
`figures.json` de un run previo (mismo `shape_count`). Si se completa, ese
individuo reemplaza a uno de los `n` individuos aleatorios de la generación 0
(`EngineConfig.seed_individual`, `ga/core/engine.py`); vacío o ausente (`""`)
deshabilita la importación. La decodificación (`TrianglesProblem.
individual_from_export`, `problems/triangles/problem.py`) normaliza la
geometría en píxeles contra la resolución **nativa** de `image_path` — el
tamaño con el que las etapas de render exportan por defecto. Un `figures.json` exportado
con `--export-width`/`--export-height` explícitos no decodifica bien. Cada figura del
export debe ser del tipo que espera el `shape_type` de la corrida (`triangle`/`oval`
exigen que todas lo sean; `both` acepta cualquier mezcla).

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
  `figures.json` y, con `--snapshot-every N`, `checkpoints.jsonl`. **No dibuja nada.**
- `render_final.py` / `render_snapshots.py` — leen el directorio de resultados y dibujan.

**Por qué se separó**: `on_generation` renderizaba un PNG a resolución nativa *adentro* del
loop cronometrado, así que `elapsed_seconds` incluía trabajo ajeno al algoritmo (medido:
31,7 s de AG contra 5,9 s de dibujar 31 snapshots, un 19%). Hoy `simulate.py` solo guarda una
**referencia** al mejor individuo de cada N generaciones — los operadores nunca mutan in
place, así que checkpointear no le cuesta nada al loop — y las vuelca al terminar.
`--progress-every N` / `--quiet` hace lo mismo con los prints.

**`checkpoints.jsonl` guarda alelos crudos, no el export de `figures.json`**: ese export
normaliza vértices contra la resolución nativa y solo decodifica exacto para un export de
tamaño default, mientras que los alelos en `[0,1]` son independientes de la resolución por
construcción. Se redondean a 8 decimales (a 4096 px de export son 4e-5 de un píxel) porque
existen para dibujarse; `best.json` va a precisión completa porque es el resultado de la
corrida y puede volver a entrar por `import`.

**Las etapas de render no necesitan el config**: reconstruyen el problema desde el bloque
`config` de `summary.json`, para que la imagen la dibuje el mismo kernel, espacio de color,
`shape_type` y `shape_count` que la puntuó.

## Tandas de experimentos (`analysis/`)

Capa por encima de `run.py`, para comparar variantes entre sí. Un *sweep* declara una config
base, qué perilla variar y con qué seeds repetir; el runner corre el producto
`variantes x seeds`, un proceso por corrida, y emite dos CSVs comparables: `summary.csv` (una
fila por corrida) e `history.csv` (una fila por generación, formato largo con `(variant, seed)`
como identificador), más `resolved.json` con el config exacto que corrió cada variante.

`analysis/plots_main.py` dibuja esos CSVs: curva de fitness, curva de diversidad y un dot plot
de fitness final con un punto por seed. Los tres llevan al pie del título lo que se mantuvo
fijo en la serie, derivado de `resolved.json` — lo que la serie varió se cae solo de ese
cartel, porque difiere entre variantes.

Regla de método: **una perilla por vez**, todo lo demás fijo, varias seeds, y `max_generations`
fijo sin corte por fitness para que todas las corridas hagan el mismo trabajo.
