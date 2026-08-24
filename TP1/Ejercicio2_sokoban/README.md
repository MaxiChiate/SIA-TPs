# Sokoban · motor + búsqueda configurable

Motor de reglas para el Ejercicio 2 del TP1: parser de niveles, engine de
movimientos, agentes de búsqueda seleccionables por `config.json`, replay y un
visualizador HTML. El roadmap completo, con el detalle de cada decisión, está
en [`CLAUDE.md`](CLAUDE.md).

```
config.json            algoritmo + heurística + nivel a correr (edita esto)
run.py                  CLI: python3 run.py [config.json]
sokoban/
  state.py            Level (estático) y State (player, boxes)
  parser.py           parse_level(text) -> Level, charset de game-sokoban.com
  notation.py         decode de la notación u/d/l/r/U/D/L/R
  engine.py           apply_move, replay, is_goal, legal_moves
  agent.py            Agent (Protocol), SearchResult, HardcodedAgent
  config.py           RunConfig, load_config(path) -> lee config.json
  visualizer_export.py render_visualizer(run_data, output_path)
  search/
    registry.py        ALGORITHMS/HEURISTICS por nombre, build_agent(algorithm, heuristic)
    astar.py            AStarAgent(heuristic=...)
    bfs.py/dfs.py/greedy.py/iddfs.py  BFS/DFS/Greedy/IDDFS
    heuristics.py       manhattan_sum/push_distance_sum + registro HEURISTICS
  levels/
    level_01_ufo.txt              nivel de referencia (2 cajas)
    level_01_ufo.solution.txt     solución de 86 movimientos (golden)
    microban_08.txt               2 cajas (incluido en analisis/config.json)
    aenigma_03.txt                4 cajas (incluido en analisis/config.json)
    level_69.txt                  6 cajas (más pesado)
  visualizer/
    sokoban_visualizer.html       template del visor, autocontenido
    last_run_<level>_<algo>_<heuristic>.html   generado por run.py (gitignored)
  tests/
    test_engine.py                 parser + reglas del motor
    test_config.py                 config.json -> RunConfig -> Agent
    test_visualizer_export.py      render_visualizer inyecta el run-data
    test_replay_known_solution.py  golden test end-to-end
analisis/               runner paralelo de experimentos -> CSV + gráficos Plotly
                        (ver analisis/README.md)
```

## Arranque rápido

`config.json` en la raíz elige nivel, algoritmo y heurística; `run.py` lo lee
y corre el agente correspondiente:

```json
{
  "level": "level_01_ufo",
  "algorithm": "astar",
  "heuristic": "manhattan_sum"
}
```

```bash
python3 run.py                 # usa ./config.json
python3 run.py otra_config.json
```

Imprime `success`, `cost`, `nodes_expanded`, `frontier_nodes`,
`elapsed_seconds`, el string de movimientos (si encontró solución) y la ruta
del visualizador que generó (ver [El visualizador](#el-visualizador)).

- `level`: stem de un archivo en `sokoban/levels/` (ej. `"level_01_ufo"`) o una
  ruta explícita a un `.txt`. Opcional: `"levels_dir"` para apuntar a otra carpeta.
- `algorithm`: uno de `sokoban.search.ALGORITHMS`. Implementados:
  `"bfs"`, `"dfs"`, `"iddfs"`, `"greedy"`, `"astar"`, y `"hardcoded"`
  (Fase 0, `HardcodedAgent`, solo conoce `level_01_ufo`).
- `heuristic`: uno de `sokoban.search.HEURISTICS` (`"manhattan_sum"` o
  `"push_distance_sum"`). Solo aplica a algoritmos en
  `sokoban.search.INFORMED_ALGORITHMS` (`astar`/`greedy`); en el resto
  (incluido `hardcoded`) se ignora sin validar, y si se omite A*/Greedy usan
  `manhattan_sum` por default.
- `visualize`: bool, default `true`. Si es `false`, `run.py` no genera el HTML.
- `visualizer_output`: ruta de salida del HTML generado. Default:
  `sokoban/visualizer/last_run_<nivel>_<algoritmo>_<heurística>.html` (ej.
  `last_run_level_01_ufo_astar_manhattan_sum.html`), para no pisar el archivo
  de una corrida anterior con otra combinación.

Programáticamente, el mismo flujo sin pasar por el CLI:

```python
from sokoban import load_config, build_agent, parse_level, replay, is_goal

config = load_config("config.json")
level = parse_level(config.level_path().read_text(), name=config.level)
agent = build_agent(config.algorithm, config.heuristic)
result = agent.solve(level)
trace = replay(level, result.solution)
assert is_goal(trace[-1], level)
```

`HardcodedAgent` (Fase 0, en `sokoban/agent.py`) sigue existiendo para
`level_01_ufo` como cable pelado de referencia, pero `run.py`/`config.json` ya
no pasan por él salvo que se seleccione explícitamente en código.

## Tests

No hay `pytest` instalado a nivel de sistema en este entorno; usar un venv:

```bash
python3 -m venv .venv
.venv/bin/pip install pytest
.venv/bin/python3 -m pytest sokoban/tests -v
```

`test_replay_known_solution.py` es el test dorado: parsea `level_01_ufo.txt`,
reproduce las 86 jugadas sin que `apply_move` tire `MoveError`, y verifica que
el estado final cumple `is_goal`.

## El visualizador

Cada corrida de `run.py` genera `sokoban/visualizer/last_run_<nivel>_<algoritmo>_<heurística>.html`
(path configurable con `visualizer_output`): una copia standalone de
`sokoban/visualizer/sokoban_visualizer.html` con los datos de esa corrida
incrustados. Se abre con doble clic (o `python3 -m http.server` y navegar),
no necesita build ni servidor real.

- play / pause / paso a paso / velocidad, con teclado (`←` `→` `espacio`
  `Home` `End`);
- contador de movimiento sobre el string de la solución, con el carácter
  actual resaltado (clic en un carácter salta a ese paso);
- tablero con paredes, piso, goals (aro tenue), cajas (ámbar; verdes si están
  sobre un goal) y jugador;
- panel **corrida**: `algorithm`, `heuristic`, el `config.json` usado y cuándo
  se generó;
- panel **resultado (SearchResult)**: `success`, `cost`, `nodes_expanded`,
  `frontier_nodes`, `elapsed_seconds`;
- panel **nivel / movimientos**: tamaño del tablero, cantidad de cajas/goals,
  y el desglose de la solución en empujes vs. pasos simples.

Mecánica: el template tiene un `<script type="application/json"
id="run-data">` con los datos de Fase 0 (`level_01_ufo` + `HardcodedAgent`)
como default, así el archivo sigue siendo visualizable si se abre directo sin
pasar por `run.py`. `sokoban/visualizer_export.py::render_visualizer` arma un
`run_data` dict (nivel, solución, `SearchResult`, algoritmo, heurística, etc.)
y reemplaza ese bloque JSON en una copia del template — el resto del HTML
(parser/motor reimplementados en JS, UI) no cambia. El parser/motor en JS
replica la misma lógica que `parser.py`/`engine.py`, sin depender de un paso
de exportación en Python más allá de ese reemplazo de texto.

## Motor de reglas

Notación de movimientos: minúscula = paso simple, MAYÚSCULA = empuje (mueve
jugador y la caja que tiene adelante). `apply_move` valida cada caso y tira
`MoveError` si el movimiento choca contra una pared, empuja sin caja adelante,
da un paso simple con una caja adelante, o empuja una caja contra una pared u
otra caja.

`Level` es estático (paredes, goals, tamaño) y `State` es lo mínimo que cambia
turno a turno (`player`, `boxes`) — pensado para que la Fase 1 use
`(player, boxes)` como clave del `visited`/`closed set` en BFS/A* sin cargar
con nada de más.

## Correr experimentos en lote

`run.py` corre **una** combinación. Para medir y comparar algoritmos está el
runner paralelo en [`analisis/`](analisis/README.md): corre cada
(nivel x algoritmo) N veces y deja un CSV con una fila por ejecución.

```bash
python3 analisis/main.py --dry-run     # lista qué correría
python3 analisis/main.py               # usa analisis/config.json
```

Se configura por `analisis/config.json` (niveles, algoritmos, repeticiones,
workers, timeout, directorio de salida) — distinto del `config.json` de la raíz,
que es el de `run.py`. El esquema del CSV está en
[`analisis/SCHEMA.md`](analisis/SCHEMA.md).

Sobre ese CSV, `analisis/graficos_main.py` genera los gráficos del informe
(Plotly, un HTML por gráfico más un índice):

```bash
pip install -r analisis/requirements.txt
python3 analisis/graficos_main.py --listar   # qué CSVs y qué gráficos hay
python3 analisis/graficos_main.py            # genera los activos
```

Son cuatro gráficos —costo, tiempo, nodos expandidos y frontera máxima— y los
cuatro tienen la misma estructura: el eje x es el **nivel** (ordenado por
dificultad creciente) y cada color es un **algoritmo + heurística**. Dentro de
cada nivel se comparan los algoritmos entre sí; de nivel a nivel se ve cómo
escala cada uno. Cuál se genera se elige con el diccionario `GRAFICOS` de ese
archivo (True/False), o con `--solo`/`--todos`.

Dos cosas a tener en cuenta antes de correrlo:

- **El timeout no es opcional.** Con 60s de margen, `aenigma_03` (4 cajas) es
  el que más combinaciones deja afuera —solo `greedy` la resuelve—, y `greedy`
  tampoco termina en `level_69` (6 cajas). El resto sí resuelve, pero al
  límite: `iddfs` en `level_01_ufo` y `bfs`/`dfs`/`astar` en `level_69` tardan
  entre 20 y 45s.
- **Usá `executor: process` (el default) para medir tiempos.** Los algoritmos
  son Python puro y CPU-bound: con threads el GIL los serializa y los tiempos
  se inflan 2-4x. El detalle está en el README del runner.

## Agregar un algoritmo o una heurística

`sokoban/search/registry.py` es el único lugar que hay que tocar: `ALGORITHMS`
mapea nombre -> fábrica de `Agent`, e `INFORMED_ALGORITHMS` marca cuáles usan
heurística.

```python
from .bfs import BFSAgent
ALGORITHMS["bfs"] = lambda heuristic: BFSAgent()  # ignora heuristic, no es informado
```

Si el algoritmo es informado, la fábrica usa el parámetro `heuristic` que le
pasa `build_agent` (igual que `_build_astar`) y hay que sumarlo a
`INFORMED_ALGORITHMS`. Las heurísticas nuevas van en `heuristics.py` y se dan de
alta en el dict `HEURISTICS`.

Dado de alta ahí, el algoritmo queda disponible en `config.json` **y** en el
runner de `analisis/` sin tocar nada más: los dos leen del mismo registro.
