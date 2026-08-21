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

## Nivel de referencia (fixture / golden test)

Nivel (formato game-sokoban.com), con solución de 86 movimientos ya verificada
(simulé el parseo + replay a mano: llega justo a los 2 goals sin ningún movimiento ilegal):

```
      ###
      #.#
  #####.#####
 ##         ##
##  # # # #  ##
#  ##     ##  #
# ##  # #  ## #
#     $@$     #
####  ###  ####
   #### ####
```

Solución:
```
LruulldlddrUUUUdddlllluurururRRlddrruUUdrrddllddRluurrdrddlUUUUddrdrrruulululLLrddlluU
```
(86 movimientos)

## Estructura de carpetas propuesta

```
sokoban/
  __init__.py
  state.py          # dataclasses Level y State
  parser.py         # parse_level(text) -> Level
  notation.py        # decode de u/d/l/r/U/D/L/R
  engine.py           # apply_move, replay, is_goal, legal_moves
  agent.py             # interfaz Agent + HardcodedAgent (fase 0)
  search/               # VACÍO por ahora — acá van bfs.py, dfs.py, greedy.py, astar.py, iddfs.py (equipo)
    __init__.py
  visualizer/
    sokoban_visualizer.html   # HTML autocontenido, reproduce un SearchResult
  levels/
    level_01_ufo.txt
    level_01_ufo.solution.txt
  tests/
    test_engine.py
    test_replay_known_solution.py   # golden test con el nivel de arriba
README.md
CLAUDE.md   # copia de este roadmap, para que quede como contexto persistente
```

## 1. Modelo de datos

### `Level` (estático — no cambia durante la búsqueda)
- `width: int`, `height: int`
- `walls: frozenset[(x, y)]`
- `goals: frozenset[(x, y)]`
- `initial_player: (x, y)`
- `initial_boxes: frozenset[(x, y)]`
- `name: str` (para identificar el nivel en el reporte final)

### `State` (lo que cambia con cada movimiento)
- `player: (x, y)`
- `boxes: frozenset[(x, y)]`

Importante: `walls` y `goals` **no van en `State`**, van en `Level`. Así `State` queda
chico y hasheable — es justo lo que después van a usar como nodo en BFS/A*
(`(player, boxes)` alcanza para el `visited`/`closed set`).

## 2. Formato de nivel (parser)

Charset estándar, el mismo que usa game-sokoban.com:

| Char | Significado |
|---|---|
| `#` | pared |
| ` ` (espacio) | piso libre |
| `.` | objetivo (goal) |
| `$` | caja |
| `@` | jugador |
| `*` | caja ya sobre un objetivo |
| `+` | jugador parado sobre un objetivo |

Reglas del parser:
- Los renglones pueden tener distinto largo (pasa seguido en archivos de Sokoban) →
  rellenar con espacios a la derecha hasta el ancho máximo **antes** de parsear.
- `parse_level` tiene que soportar cualquier cantidad de cajas/goals (no hardcodear 2),
  porque la consigna después pide variar "la cantidad de cajas/objetivos".
- Guardar el texto original o el nombre del archivo en `Level.name`, para el reporte.

## 3. Notación de movimientos (para reproducir soluciones)

Confirmado por simulación sobre el nivel de referencia:

- **minúscula** = paso simple, no empuja caja: `l r u d`
- **MAYÚSCULA** = empuje: mueve al jugador y a la caja que tiene adelante: `L R U D`

`apply_move(state, level, move_char) -> State` tiene que validar y tirar un
`MoveError` claro si:
- el destino es pared
- es empuje pero no hay caja adelante
- es paso simple pero hay una caja adelante (ese char debería haber sido mayúscula)
- el empuje choca la caja contra una pared o contra otra caja

## 4. Motor / Engine API

```python
parse_level(text: str) -> Level
initial_state(level: Level) -> State
apply_move(state: State, level: Level, move: str) -> State   # raises MoveError
replay(level: Level, solution: str) -> list[State]            # trace completo, para animar
is_goal(state: State, level: Level) -> bool                   # todas las cajas sobre algún goal
legal_moves(state: State, level: Level) -> list[str]           # para cuando el equipo arme la búsqueda
```

`legal_moves` ya devuelve los movimientos en la notación `u/d/l/r/U/D/L/R`, para que
el código de búsqueda del equipo no tenga que reinventar esa lógica.

## 5. Interfaz del agente (el enchufe para la Fase 1)

```python
class Agent(Protocol):
    def solve(self, level: Level) -> SearchResult: ...

@dataclass
class SearchResult:
    success: bool
    solution: str            # ej "LruulldlddrUUUU..."
    cost: int                # cantidad de movimientos totales (la consigna pide optimizar esto)
    nodes_expanded: int
    frontier_nodes: int
    elapsed_seconds: float
```

- Fase 0: `HardcodedAgent.solve(level)` devuelve el `SearchResult` armado a mano con la
  solución de 86 movimientos de arriba (`nodes_expanded=0`, `frontier_nodes=0`,
  son N/A para este agente).
- Fase 1 (equipo): `bfs.py`, `dfs.py`, `greedy.py`, `astar.py`, `iddfs.py` implementan
  `Agent` usando `legal_moves`/`apply_move`/`is_goal`, y llenan los campos reales.

Nota sobre `cost`: la consigna dice "queremos optimizar la cantidad de movimientos",
así que `cost` = cantidad total de pasos (empujes + pasos simples), no solo empujes.

## 6. Visualizador

Mismo criterio que el visualizador de 8-puzzle (HTML autocontenido, cero dependencias):
- Tablero con paredes, piso, goals (marca tenue), cajas (ícono distinto si está sobre
  un goal), jugador.
- Controles: play/pause/step/velocidad, contador de movimiento actual sobre el string
  de la solución.
- Barra de stats (success, cost, nodes_expanded, frontier_nodes, elapsed_seconds)
  leída directo del `SearchResult`.
- Fase 0 solo necesita reproducir el trace de `replay()`. No hace falta "modo libre"
  todavía (se puede sumar después si quieren, como el del 8-puzzle).

## 7. Test dorado (golden test)

Guardar:
- `levels/level_01_ufo.txt` → el nivel de arriba
- `levels/level_01_ufo.solution.txt` → el string de 86 movimientos

Test obligatorio (`tests/test_replay_known_solution.py`):
1. `parse_level` sobre `level_01_ufo.txt`
2. `replay(level, solucion)` sin que tire `MoveError`
3. `is_goal(estado_final, level) == True`
4. `len(solucion) == 86`

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

## Estado real de la Fase 0 (implementada)

Todo lo de arriba está hecho y verificado:

- `sokoban/state.py`, `parser.py`, `notation.py`, `engine.py`, `agent.py`: según la
  API de las secciones 1-5.
- `sokoban/tests/test_engine.py`: 14 chequeos unitarios del parser y el motor.
- `sokoban/tests/test_replay_known_solution.py`: el golden test de la sección 7,
  más un chequeo de que `HardcodedAgent` devuelve exactamente esa solución.
- `sokoban/visualizer/sokoban_visualizer.html`: autocontenido, reimplementa el
  parser/engine en JS (no depende de un paso de build en Python) y se probó en
  Chrome de punta a punta — las 86 jugadas llegan a los 2 goals sin errores.
- Nombre del nivel (`Level.name`): tiene que ser `"level_01_ufo"` (el stem del
  archivo) para que `HardcodedAgent` lo reconozca — está indexado por nombre en
  `agent.py`, no hardcodeado a "el único nivel que existe".

Correr los tests (no hay `pytest` instalado a nivel de sistema; usar un venv):

```bash
python3 -m venv .venv && .venv/bin/pip install pytest
cd TP1/Ejercicio2_sokoban && ../../<ruta al venv>/bin/python -m pytest sokoban/tests -v
```

Para la Fase 1, el equipo escribe en `sokoban/search/` usando únicamente
`legal_moves`/`apply_move`/`is_goal` de `engine.py` — no hace falta tocar el
parser, el motor ni el visualizador.

## Estado real de la Fase 1 (parcial: A* + selección por config.json)

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
  `build_agent(algorithm, heuristic) -> Agent`. Implementados: `astar` (real)
  y `hardcoded` (Fase 0, devuelve `HardcodedAgent()`). Algoritmos no
  implementados (`bfs`, `dfs`, `greedy`, `iddfs`) están registrados como
  placeholders que tiran `NotImplementedError` con la lista de disponibles —
  agregar el algoritmo real es escribir la clase + una entrada acá, sin tocar
  `run.py`.
- `sokoban/search/astar.py`: `AStarAgent` ahora recibe `heuristic` inyectada
  en el constructor (default `manhattan_sum`) en vez de importarla hardcodeada,
  para que `registry.py` pueda instanciarlo con la heurística que pida el
  config.
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

Falta (equipo, cuando implementen los algoritmos que quedan): sumar
`bfs.py`/`dfs.py`/`greedy.py`/`iddfs.py` siguiendo el patrón de `astar.py`, y
darlos de alta en `ALGORITHMS`/`INFORMED_ALGORITHMS` en `registry.py` (un
ejemplo de cómo hacerlo está en el README).
