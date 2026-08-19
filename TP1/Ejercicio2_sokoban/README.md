# Sokoban · motor (Fase 0)

Motor de reglas para el Ejercicio 2 del TP1: parser de niveles, engine de
movimientos, replay de una solución conocida y un visualizador HTML. **Sin
ningún algoritmo de búsqueda todavía** — ese es el trabajo de la Fase 1, que
hace el equipo sobre esta base. El roadmap completo, con el detalle de cada
decisión, está en [`CLAUDE.md`](CLAUDE.md).

```
sokoban/
  state.py            Level (estático) y State (player, boxes)
  parser.py           parse_level(text) -> Level, charset de game-sokoban.com
  notation.py         decode de la notación u/d/l/r/U/D/L/R
  engine.py           apply_move, replay, is_goal, legal_moves
  agent.py            Agent (Protocol), SearchResult, HardcodedAgent
  search/             vacío -- acá va bfs.py/dfs.py/greedy.py/astar.py/iddfs.py (equipo)
  levels/
    level_01_ufo.txt              nivel de referencia
    level_01_ufo.solution.txt     solución de 86 movimientos (golden)
  visualizer/
    sokoban_visualizer.html       visor autocontenido, sin dependencias
  tests/
    test_engine.py                 parser + reglas del motor
    test_replay_known_solution.py  golden test end-to-end
```

## Arranque rápido

```python
from sokoban import parse_level, initial_state, replay, is_goal, HardcodedAgent
from pathlib import Path

level = parse_level(Path("sokoban/levels/level_01_ufo.txt").read_text(), name="level_01_ufo")
result = HardcodedAgent().solve(level)          # Fase 0: solución hardcodeada
trace = replay(level, result.solution)          # lista de States, uno por movimiento
assert is_goal(trace[-1], level)
```

`HardcodedAgent` solo conoce `level_01_ufo` (matchea por `Level.name`); para
cualquier otro nivel devuelve `success=False`. Sirve únicamente para probar
que parser → engine → visualizador andan de punta a punta.

## Tests

No hay `pytest` instalado a nivel de sistema en este entorno; usar un venv:

```bash
python3 -m venv .venv
.venv/bin/pip install pytest
.venv/bin/python -m pytest sokoban/tests -v
```

`test_replay_known_solution.py` es el test dorado: parsea `level_01_ufo.txt`,
reproduce las 86 jugadas sin que `apply_move` tire `MoveError`, y verifica que
el estado final cumple `is_goal`.

## El visualizador

`sokoban/visualizer/sokoban_visualizer.html` se abre con doble clic (o
`python3 -m http.server` y navegar), no necesita build ni servidor real.
Reimplementa el parser y el motor en JS (misma lógica que `parser.py`/
`engine.py`) para no depender de un paso de exportación en Python.

- play / pause / paso a paso / velocidad, con teclado (`←` `→` `espacio`
  `Home` `End`);
- contador de movimiento sobre el string de la solución, con el carácter
  actual resaltado (clic en un carácter salta a ese paso);
- tablero con paredes, piso, goals (aro tenue), cajas (ámbar; verdes si están
  sobre un goal) y jugador;
- barra de stats leída directo de `SearchResult`: `success`, `cost`,
  `nodes_expanded`, `frontier_nodes`, `elapsed_seconds`.

Para la Fase 0 el nivel y la solución están embebidos a mano al principio del
`<script>` (`LEVEL_LINES`, `SOLUTION`, `RESULT`). Cuando el equipo tenga
resultados reales de búsqueda, alcanza con reemplazar esos tres valores por
los de otro `Level`/`SearchResult`.

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

## Para la Fase 1 (equipo)

`sokoban/search/` está vacío a propósito. Cada algoritmo (`bfs.py`, `dfs.py`,
`greedy.py`, `astar.py`, `iddfs.py`) implementa el protocolo `Agent` de
`agent.py` usando solo `legal_moves`/`apply_move`/`is_goal` de `engine.py`, y
llena `nodes_expanded`/`frontier_nodes` con los valores reales de cada
búsqueda (el motor solo define el molde de `SearchResult`, no puede contarlos
por ustedes). Ver el detalle completo en [`CLAUDE.md`](CLAUDE.md).
