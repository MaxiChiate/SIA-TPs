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

- **Fase 1** (equipo) ✅ HECHA: BFS/DFS/Greedy/A*/IDDFS + las 2 heurísticas admisibles
  (`manhattan_sum` y `push_distance_sum`), sobre `legal_moves`/`apply_move`.
- **Fase 2** (equipo) ✅ HECHA: `nodes_expanded`/`frontier_nodes` reales ya están
  instrumentados en los cinco algoritmos (cada uno los cuenta y los devuelve en su `SearchResult`).
- **Fase 3** ✅ HECHA: sumar más niveles / más cajas (la consigna permite variar la complejidad).
  Hay 4 niveles en `sokoban/levels/` (`aenigma_01` original más
  `microban_08`, `aenigma_03` y `yasgood_69`, usados en `analisis/config.json`).
- **Fase 4**: README de cómo correrlo + presentación. (Existe `README.md`; falta la presentación.)

## Cómo arrancar con Claude Code

1. Copiá este archivo como `ROADMAP.md` (o `CLAUDE.md`) en la raíz del repo.
2. Corré `claude` y pedile: *"Leé ROADMAP.md e implementá la Fase 0 completa: parser,
   engine, notation, HardcodedAgent, visualizador HTML, y el test dorado con
   aenigma_01."*
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

Dos heurísticas admisibles implementadas, ambas con la misma estructura
(distancia caja->goal + matching de costo mínimo por algoritmo húngaro,
O(cajas²·goals), no fuerza bruta factorial); lo único que cambia es cómo
miden la distancia:

- `manhattan_sum`: distancia Manhattan (`|Δx|+|Δy|`), que ignora las paredes.
- `push_distance_sum`: distancia real esquivando paredes, precalculada con un
  BFS desde cada goal (cacheado por nivel con `lru_cache`). Domina a
  `manhattan_sum` (al respetar las paredes cada distancia es >= la Manhattan) y
  sigue admisible. Si una caja no alcanza ningún goal, el costo se dispara.

Ambas están en `heuristics.py` y registradas en `HEURISTICS`; las usan los
algoritmos informados (`astar`/`greedy`).

## Estado real: poda de deadlocks (los cinco algoritmos)

Antes, `is_deadlock` vivía en `heuristics.py` y **solo lo usaba `astar.py`**:
`bfs`/`dfs`/`iddfs`/`greedy` expandían igual estados ya irrecuperables. Ahora
la poda es de todos y está en un solo lugar:

- `sokoban/search/deadlock.py::is_deadlock(state, level)`: dos reglas, ambas
  sobre cajas que no están en un goal. (1) **rincón**: caja entre dos paredes
  perpendiculares -- el conjunto de esas celdas se precalcula por nivel con
  `lru_cache` (`_celdas_muertas`), así el chequeo por caja es un `in` de set;
  (2) **bloque 2x2**: caja dentro de un cuadrado de 2x2 lleno de paredes y/o
  cajas (se traban mutuamente). La regla 2 solo se evalúa si hay otra caja
  pegada: un 2x2 lleno con una sola caja ya implica dos paredes
  perpendiculares, o sea el caso 1.
- `sokoban/search/_common.py::successors(state, level)`: generador de
  `(movimiento, estado)` que envuelve `legal_moves`+`apply_move` y saltea los
  deadlocks. Los cinco agentes generan hijos **solo** por acá, así que la poda
  no se puede olvidar en uno; en cada agente son 0 líneas de deadlock (el
  `for move in legal_moves(...)` + `apply_move` pasó a ser un solo
  `for move, child in successors(...)`).

La detección es conservadora a propósito: no encuentra todos los deadlocks,
pero **no tiene falsos positivos**. Eso es lo que permite podar sin romper la
optimalidad de BFS/IDDFS/A* (medido: el costo de la solución no cambia en
ningún nivel).

Impacto medido (nodos expandidos, sin poda -> con poda; mismo costo):

| Nivel | bfs | dfs | greedy | astar |
|---|---|---|---|---|
| `aenigma_01` | 30346 -> 15129 | 13535 -> 3062 | 756 -> 658 | 30316 -> 15113 |
| `microban_08` | 4101 -> 1697 | 2960 -> 829 | 2210 -> 808 | 3937 -> 1622 |

El tiempo por nodo no empeora (el chequeo es un par de lookups de set), así
que la mitad de nodos es mitad de tiempo. `aenigma_03` con `astar` +
`push_distance_sum` ahora termina (83 movimientos, ~9.6M nodos, ~195s en esta
máquina), pero sigue por encima del `timeout_seconds: 60` de
`analisis/config.json`.

Tests: `sokoban/tests/test_deadlock.py` (rincón sí / rincón sobre goal no /
caja libre no / una sola pared no / bloque 2x2 sí / dos cajas juntas no, y que
`successors` no ofrezca un movimiento legal que mete la caja en un rincón).

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

- **No todas las combinaciones terminan**: con `timeout_seconds: 60`,
  `aenigma_03` (4 cajas) es el nivel que más rechaza — `bfs`, `dfs`, `iddfs` y
  las dos `astar` no lo resuelven ahí, solo `greedy` sí. En `yasgood_69`
  (6 cajas) el que no termina es `greedy`; `bfs`/`dfs`/`astar` sí lo resuelven,
  pero tardan 20-40s. `iddfs` sobre `aenigma_01` también resuelve, pero al
  límite (~45s). Por eso `timeout_seconds` es prácticamente obligatorio: varias
  de estas combinaciones dependen de tener un timeout generoso (≥60s) para no
  quedar afuera.
- **Los threads no paralelizan acá**: los algoritmos son Python puro y
  CPU-bound, así que el GIL los serializa y los tiempos concurrentes se inflan
  2-4x (bfs 0.091s -> 0.292s con 4 workers, al 94% de CPU = un solo core).
  Además un thread no se puede matar: con `executor: thread` el timeout marca
  la fila pero la búsqueda sigue de fondo, y el runner fuerza la salida al
  final para no colgarse esperándola. Para medir, `executor: process`.
- **`memory_limit_mb` solo funciona en Linux** (`RLIMIT_AS`); en macOS/Windows
  no tiene efecto y el runner avisa al arrancar. Importa porque BFS sobre
  `yasgood_69` expande ~4M nodos (varios GB por worker).

El runner no tiene su propia lista de algoritmos: los lee de
`sokoban.search.ALGORITHMS`/`HEURISTICS`, así que lo que se dé de alta en
`registry.py` queda disponible acá automáticamente.

## Estado real: gráficos del análisis (`analisis/graficos_main.py`)

Sobre el CSV que produce el runner, `graficos_main.py` genera gráficos Plotly
(un HTML por gráfico + un `index.html`) en `analisis/graficos/` (gitignoreado,
porque incluye una copia de `plotly.min.js` de ~5 MB).

**Son cuatro gráficos y los cuatro tienen la misma estructura**: el eje x es el
**nivel** (ordenado por dificultad creciente = cantidad de cajas) y cada color
es un **algoritmo + heurística**. Es decir, dentro de cada nivel se comparan los
algoritmos entre sí, y de grupo a grupo se ve cómo escala cada uno al subir la
dificultad.

| Gráfico | Métrica | Escala |
|---|---|---|
| `costo_vs_nivel` | `cost` — largo de la solución | lineal |
| `tiempo_vs_nivel` | media de `elapsed_seconds` | log |
| `nodos_vs_nivel` | `nodes_expanded` | log |
| `frontera_vs_nivel` | `frontier_nodes` (pico) | log |

- `graficos_main.py`: el diccionario `GRAFICOS` (True/False por gráfico) decide
  qué se genera, y `ARCHIVO` de qué CSV; los dos se pueden pisar por CLI
  (`--solo`, `--todos`, `--archivo`, `--tema`, `--salida`, `--listar`). Los
  cuatro gráficos son la misma función `_barras` con distinto `valor`/`texto`:
  cambiar la forma de todos es tocar un solo lugar.
- `graficos_datos.py`: carga tipada del CSV y agregación por (nivel,
  algoritmo). Solo stdlib, sin pandas.
- `graficos_estilo.py`: paleta y layout base.
- Única dependencia: `plotly` (`analisis/requirements.txt`). El runner sigue sin
  dependencias.

Decisiones que no son obvias leyendo el código:

- **Nada con `status != "ok"` entra en un promedio.** Un `timeout` tiene
  `wall_seconds ≈ timeout_seconds`, un piso artificial. Las combinaciones que no
  terminaron se anotan como "no terminó · <motivo>" en el lugar exacto donde
  iría la barra faltante (por eso existe `_offset_barra`), para que la ausencia
  no se lea como un cero.
- **El color codifica el algoritmo, no el nivel** (el nivel ya está en el eje x).
  Es lo que hay que seguir de grupo a grupo. Los 8 slots de `series` están
  validados para daltonismo y contraste **en el orden en que están**: los pares
  que valen son los *adyacentes*, que en barras agrupadas son justamente los que
  quedan pegados. Con más de 8 algoritmos los extras van a gris y el runner
  avisa por stderr — no se cicla la paleta, porque repetir un color es peor que
  no distinguir.
- **La etiqueta de valor sobre cada barra no es decorativa**: es el "relief" de
  contraste obligatorio de los tres slots que en modo claro quedan por debajo de
  3:1 (aqua, amarillo, magenta), y el único lugar donde se lee el número exacto
  sin pasar el mouse. Va rotada -90° porque con 7 series la barra es angosta.
- **`costo_vs_nivel` es el único lineal.** El costo importa como proporción real
  (una solución 10x más larga es 10x peor), no como orden de magnitud. Las otras
  tres métricas abarcan 4-6 órdenes de magnitud y en lineal el nivel más caro
  aplastaría a todos los demás contra el eje.
- **El rango del eje y se calcula a mano** (`_rango_con_aire`): el autorange de
  Plotly ajusta al dato, no al texto rotado que va *encima* del dato, así que
  sin eso la barra más alta se come su propio número contra el techo.
- **La nota al pie se desplaza en píxeles, no en fracción de `paper`**
  (`DESPLAZAMIENTO_NOTA`): `paper` es relativo al alto del área de ploteo, que
  cambia con el tamaño de la ventana, así que una fracción fija la deja pegada
  al eje en una ventana chica y fuera del canvas en una grande.
- **Las métricas no temporales se toman de la primera corrida exitosa**, porque
  los algoritmos son deterministas. Si variaran entre repeticiones sería un bug,
  y `graficos_main.py` lo avisa por stderr (`métricas no deterministas`).
- `nota()` corta las líneas con `textwrap`: la propiedad `width` de las
  anotaciones de Plotly **recorta** el texto que no entra, no lo envuelve.
- Los gráficos se revisan renderizados (Chrome headless), no solo generados: así
  aparecieron la nota al pie clipeada fuera del canvas y las etiquetas de las
  barras más altas cortadas contra el techo del área de ploteo. Antes, con la
  orientación vieja, así habían aparecido el título de eje duplicado (los dos
  ejes compartían el mismo sub-dict `title` por copia superficial), las
  etiquetas encimadas de BFS/A* en el scatter y las etiquetas recortadas de la
  tabla — bugs de los gráficos viejos (`tradeoff_costo_nodos`, `tabla_resumen`)
  que ya no existen en el esquema de cuatro gráficos actual.

## Estado real: niveles (Fase 3)

`sokoban/levels/` tiene 4 niveles: `aenigma_01` (el original, golden test
de 86 movimientos), y `microban_08`/`aenigma_03`/`yasgood_69`, que son los que
usa `analisis/config.json` para comparar algoritmos y heurísticas.

Hubo un intento de sumar 7 niveles más (`level_02_soko11` .. `level_08_soko04`,
sacados de la colección "aenigma" de game-sokoban.com) que terminaron sin
usarse en el benchmark de `analisis/` — se quitaron junto con
`sokoban/tests/test_more_levels.py`, que era el único lugar que los ejercitaba.
