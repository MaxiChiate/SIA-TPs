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
  dentro de `ga/`.
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
  operators/            # selection (7), crossover (4), mutation (4), survival (2), stopping (2)
  registry.py           # nombre en config -> implementación, vía decorador @register
  config.py             # parseo + validación de config.json -> ConfigError
  metrics.py            # GenerationRecord + mean / std / genotypic_diversity + record_for
problems/
  triangles/            # genotype, renderer, fitness, problem, export  [Pillow/numpy]
analysis/               # runner de experimentos — capa por encima de run.py
  config.py             # SweepConfig + overrides por ruta con puntos
  runner.py             # orquestador paralelo (un proceso por corrida)
  records.py            # esquema de summary.csv (1 fila/corrida) e history.csv (1 fila/generación)
  main.py               # CLI: python3 analysis/main.py [sweep.json]
  sweep.json            # serie A de ejemplo: los 7 métodos de selección
tests/                  # unitarios de operadores (pytest, RNG scripteado, deterministas)
images/                 # imágenes fuente (argentina.png, starry_night.png)
run.py                  # CLI: python3 run.py [config.json]
config.json.example     # plantilla — copiar a config.json
requirements.txt        # pillow, numpy, pytest  (el core no los usa)
```

## Genotipo (problema triangles)

Individuo = lista fija de `T` triángulos, cada uno 10 genes `x1,y1,x2,y2,x3,y3,R,G,B,A`.
Genotipo plano de `10*T` alelos. **Todos los alelos normalizados a `[0,1]`**; el renderer
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

## Estado

Los 6 bloques originales están hechos:

1. **Core** — `ga/core/*`, `ga/metrics.py`
2. **Config + registry** — `ga/registry.py`, `ga/config.py`, `config.json.example`
3. **Operadores** — 7 selecciones, 4 cruzas, 4 mutaciones, 2 supervivencias, 2 criterios de corte
4. **Plug-in `triangles`** — genotype, renderer, fitness, problem, export
5. **Tests** — 40 unitarios de operadores
6. **`run.py` + salidas** — imagen final, snapshots, `triangles.json`, `history.csv`/`.json`,
   `summary.json`

Agregado después: `analysis/` (runner de experimentos) y el multiprocessing del `Evaluator`
(`engine.processes`, un proceso por individuo sin fitness cacheado).

## Pasos a seguir

1. **Correr los experimentos.** `analysis/sweep.json` ya trae la serie A (los 7 métodos de
   selección). Faltan las series de cruza, mutación (+ barrido de `pm`), supervivencia, tamaño
   de población y cantidad de triángulos. Regla: **una perilla por vez**, todo lo demás fijo,
   varias seeds, y `max_generations` fijo sin corte por fitness para que todas las corridas
   hagan el mismo trabajo.
2. **Gráficos.** Hoy no hay nada que dibuje los CSVs. Mínimo: curva de fitness por generación,
   curva de diversidad (la que muestra convergencia prematura) y comparativa de fitness final
   por variante. Molde en `TP1/Ejercicio2_sokoban/analisis/graficos_*.py` (plotly).
3. **Ejercicio 1.** El del mapa NxN de caracteres ASCII. No se implementa, se piensa — pero es
   entregable y hay que responderlo en la presentación.
4. **Presentación.**

### Pendientes técnicos

Detectados en revisión; ninguno bloquea los experimentos, pero conviene resolverlos o tener la
respuesta lista para la defensa.

- **Escala del fitness.** `1 - MSE/255²` vive en `[0.85, 1.0]`, así que ruleta y Boltzmann —que
  dependen de las *diferencias absolutas* de fitness— quedan casi uniformes. O se reescala el
  fitness (sigma scaling / normalización por generación), o se ajustan las temperaturas por
  defecto de Boltzmann (`t0=20, tmin=1` no sirven para este rango).
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

Siempre desde `TP2/`: las rutas del config son relativas a ese directorio.

```bash
pip3 install -r requirements.txt     # pillow, numpy, pytest
cp config.json.example config.json   # ajustar imagen, triangle_count, operadores, hiperparámetros

python3 run.py                       # una corrida -> results/<config>_<timestamp>/
python3 run.py config.json --snapshot-every 25

python3 analysis/main.py             # una tanda -> analysis/results/<sweep_id>/
python3 analysis/main.py --dry-run   # valida el sweep y muestra el plan, sin correr nada

python3 -m pytest tests/ -v          # 40 tests de operadores
```

Uso del motor como librería: instanciar un `Problem`, un `EngineConfig` con los callables de
selección/cruza/mutación/supervivencia + `Pc`/`Pm`/`max_generations`, un `Rng` con
`make_rng(seed)`, y llamar `Engine(problem, config, rng).run()` → `RunResult` (mejor
individuo, generación en que apareció, criterio de corte, evaluaciones, tiempo, `history` de
`GenerationRecord`).

## Salida

`run.py` corre una config y emite en un directorio de resultados: imagen final (+ snapshots
opcionales cada X generaciones), enumeración de triángulos del mejor individuo (vértices +
color) en JSON, log por generación en CSV/JSON (generación, mejor/promedio/desvío/peor
fitness, diversidad, evaluaciones acumuladas, tiempo acumulado), y un resumen final (mejor
fitness, generación en que apareció, criterio de corte que disparó, config completo + seed).

`analysis/main.py` corre una tanda entera y emite dos CSVs comparables: `summary.csv` (una fila
por corrida, para comparar variantes entre sí) e `history.csv` (una fila por generación, formato
largo con `(variant, seed)` como identificador, para las curvas), más `resolved.json` con el
config exacto que corrió cada variante.
