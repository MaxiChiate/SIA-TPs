# Roadmap – Motor de Sokoban (TP1, Ejercicio 2)

> Documento pensado para pegarle a Claude Code y que arranque solo con la Fase 0.
> El resto de las fases (búsqueda, heurísticas) las implementa el equipo — no Claude Code.

## Objetivo de esta etapa (Fase 0)

Armar el "tablero de juego" completo, pero **sin ningún algoritmo de búsqueda**:
parser de nivel, motor de reglas, reproducción/animación de una solución ya conocida,
y la interfaz donde después se va a enchufar el agente propio.

En esta fase el "agente" es un cable pelado: para el único nivel que tenemos,
devuelve la solución hardcodeada de abajo. Sirve solo para probar que el motor
y el visualizador andan de punta a punta (parseo → replay → animación).

**Lo que NO entra en esta fase** (eso queda para el equipo, según la consigna):
- BFS, DFS, Greedy, A*, IDDFS
- Heurísticas admisibles / no admisibles
- Conteo real de nodos expandidos / frontera (el motor solo define el molde de esos datos)

## 8. Fases siguientes

- **Fase 1** (equipo): BFS/DFS/Greedy/A*/IDDFS + heurísticas, sobre `legal_moves`/`apply_move`.
- **Fase 2** (equipo): instrumentar `nodes_expanded`/`frontier_nodes` reales en cada
  algoritmo — el motor no puede hacerlo por ustedes, es parte de cada implementación.
- **Fase 3**: sumar más niveles / más cajas (la consigna permite variar la complejidad).
- **Fase 4**: README de cómo correrlo + presentación.

## Cómo arrancar con Claude Code

1. Copiá este archivo como `ROADMAP.md` (o `CLAUDE.md`) en la raíz del repo.
2. Corré `claude` y pedile: *"Leé ROADMAP.md e implementá la Fase 0 completa: parser,
   engine, notation, HardcodedAgent, visualizador HTML, y el test dorado con
   level_01_ufo."*
3. Cuando eso ande y veas la animación de las 86 jugadas, seguís con la Fase 1
   (ahí entran BFS/A*/heurísticas, que es la parte que escriben ustedes).

---

## Correr los tests

No hay `pytest` instalado a nivel de sistema; usar un venv:

```bash
python3 -m venv .venv && .venv/bin/pip install pytest
cd TP1/Ejercicio2_sokoban && ../../<ruta al venv>/bin/python -m pytest sokoban/tests -v
```

Para la Fase 1, el equipo escribe en `sokoban/search/` usando únicamente
`legal_moves`/`apply_move`/`is_goal` de `engine.py` — no hace falta tocar el
parser, el motor ni el visualizador.

## Estado real de la Fase 1 (completa: los 5 algoritmos + selección por config.json)

Se sumó una capa de configuración para que la elección de algoritmo y
heurística sea un archivo, no un cambio de código (pedido explícito, con
`config.json`/`config.yml` de referencia en el material de la materia):

- `config.json` (raíz del proyecto): `{"level", "algorithm", "heuristic"}`.
  `level` es el stem de un archivo en `sokoban/levels/` o una ruta a un
  `.txt`; `levels_dir` es opcional para apuntar a otra carpeta.
- `sokoban/config.py`: `RunConfig` + `load_config(path)`, valida JSON y
  claves requeridas, tira `ConfigError` con mensaje claro si algo falta.
- `sokoban/search/registry.py`: único lugar que mapea nombres de
  `config.json` a clases de Python. `ALGORITHMS` (nombre -> fábrica que recibe
  la heurística ya resuelta, o `None` si el algoritmo no es informado),
  `HEURISTICS` (reexportado de `heuristics.py`), `INFORMED_ALGORITHMS` (qué
  algoritmos sí usan la heurística — solo `astar`/`greedy`; para el resto
  `heuristic` en config.json ni siquiera se valida), y
  `build_agent(algorithm, heuristic) -> Agent`. Implementados los cinco:
  `bfs`, `dfs`, `iddfs`, `greedy` y `astar`, más `hardcoded` (Fase 0, devuelve
  `HardcodedAgent()`). Sumar un algoritmo nuevo es escribir la clase + una
  entrada acá, sin tocar `run.py` ni el runner de `analisis/`.
- `sokoban/search/astar.py`: `AStarAgent` ahora recibe `heuristic` inyectada
  en el constructor (default `manhattan_sum`) en vez de importarla hardcodeada,
  para que `registry.py` pueda instanciarlo con la heurística que pida el
  config. `greedy.py` sigue el mismo patrón; `bfs`/`dfs`/`iddfs` no son
  informados y su fábrica ignora el parámetro.
- `sokoban/search/_common.py`: `Node` (estado + puntero al padre + movimiento)
  y `reconstruct_path`, compartidos por los cinco algoritmos para no arrastrar
  el string completo de la solución en cada nodo de la frontera.
- `run.py` (raíz): CLI (`python run.py [config.json]`) que encadena
  `load_config` → `parse_level` → `build_agent` → `agent.solve(level)` →
  imprime el `SearchResult` y confirma con `replay`/`is_goal` que la solución
  es jugable. Maneja `ConfigError`/`ValueError`/`NotImplementedError`/
  `LevelParseError` con mensajes por stderr y exit code 1.
- `sokoban/tests/test_config.py`: cubre `load_config` (nivel por stem,
  heurística opcional, archivo inexistente, clave faltante) y `build_agent`
  (default de heurística, algoritmo/heurística desconocidos, algoritmo no
  implementado).

`HardcodedAgent` (Fase 0) sigue existiendo tal cual en `agent.py`, y ahora
también se puede seleccionar desde `config.json` con `"algorithm": "hardcoded"`
(vía `registry.py`) además de seguir siendo el fixture del golden test.

Única heurística implementada: `manhattan_sum` (admisible; recorre las
permutaciones caja->goal, así que es factorial en cantidad de cajas).
`is_deadlock` en `heuristics.py` sigue siendo un `TODO`.

## Estado real: `run.py` genera el visualizador de cada corrida

`sokoban/parser.py::level_to_lines(level)` es el inverso de `parse_level`
(reconstruye el ASCII desde `Level`). `sokoban/visualizer_export.py::
render_visualizer(run_data, output_path)` toma un dict y una copia de
`visualizer/sokoban_visualizer.html`, y reemplaza el `<script
type="application/json" id="run-data">` del template por ese dict
serializado; el resto del HTML/JS no cambia.

`run.py`, si `config.visualize` (default `true`), arma `run_data` con nivel,
solución, `SearchResult`, `algorithm`, `heuristic`, el `config_path` usado,
`generated_at` (UTC ISO) y dos bloques extra: `board`
(`width`/`height`/`boxes`/`goals`) y `moves` (`pushes`/`steps`, desglosando
`cost` en empujes vs. pasos simples). Lo escribe en `config.visualizer_output`
(default `sokoban/visualizer/last_run_<nivel>_<algoritmo>_<heurística>.html`
vía `_default_visualizer_output` en `config.py`, gitignored) e imprime la
ruta.

El template (`sokoban_visualizer.html`) sigue teniendo datos default de
Fase 0 embebidos en ese mismo bloque JSON, para que siga siendo abrible
directo sin pasar por `run.py`. Tests: `test_visualizer_export.py`
(round-trip del JSON incrustado) y `test_engine.py::
test_level_to_lines_es_inverso_de_parse_level`.

## Estado real: runner paralelo de experimentos (`analisis/`)

`run.py` corre una sola combinación. Para la comparación de algoritmos que pide
la consigna está `analisis/`, que corre cada (nivel x algoritmo) N veces y deja
**un CSV con una fila por ejecución** para el análisis posterior.

- `analisis/config.json` (JSON puro, sin dependencias; distinto del
  `config.json` de la raíz, que es el de `run.py`). Claves:
  `executor`, `workers`, `repetitions`, `timeout_seconds`, `memory_limit_mb`,
  `levels` (lista o `"all"`), `levels_dir`, `algorithms` (string o
  `{name, heuristic}`), `output_dir`, `output_file`, `include_solution`.
- `analisis/config.py`: `BenchmarkConfig` + `load_benchmark_config`. Valida
  todo **antes** de correr nada (niveles inexistentes, algoritmos/heurísticas
  desconocidas, claves con typo) y tira `BenchmarkConfigError`. Las rutas
  relativas se resuelven contra la raíz del proyecto, no contra el cwd.
- `analisis/runner.py`: dos backends. `process` (default) usa un proceso por
  ejecución con la concurrencia acotada por un pool de threads que solo
  esperan; `thread` es un `ThreadPoolExecutor` puro. `run_benchmark` es un
  generador, así que el CSV se escribe en streaming.
- `analisis/worker.py`: una ejecución (parsear -> resolver -> **verificar la
  solución con `replay`/`is_goal`**). Nunca propaga excepciones: todo fallo
  sale como una fila con `status="error"`.
- `analisis/records.py`: `RunRecord` (30 columnas) + writer CSV incremental
  que flushea fila por fila, para no perder una tanda larga que se corta.
- `analisis/SCHEMA.md`: documentación de cada columna, para el sistema de
  análisis que consume el CSV.

Tres cosas que condicionan el diseño, verificadas en esta máquina:

- **No todas las combinaciones terminan**: `iddfs` no resuelve `level_01_ufo`,
  y `greedy`/`astar` no resuelven `level_69` (5 cajas). Por eso
  `timeout_seconds` es prácticamente obligatorio.
- **Los threads no paralelizan acá**: los algoritmos son Python puro y
  CPU-bound, así que el GIL los serializa y los tiempos concurrentes se inflan
  2-4x (bfs 0.091s -> 0.292s con 4 workers, al 94% de CPU = un solo core).
  Además un thread no se puede matar: con `executor: thread` el timeout marca
  la fila pero la búsqueda sigue de fondo, y el runner fuerza la salida al
  final para no colgarse esperándola. Para medir, `executor: process`.
- **`memory_limit_mb` solo funciona en Linux** (`RLIMIT_AS`); en macOS/Windows
  no tiene efecto y el runner avisa al arrancar. Importa porque BFS sobre
  `level_69` expande ~4M nodos (varios GB por worker).

El runner no tiene su propia lista de algoritmos: los lee de
`sokoban.search.ALGORITHMS`/`HEURISTICS`, así que lo que se dé de alta en
`registry.py` queda disponible acá automáticamente.
