# Runner de experimentos

Corre cada combinación **nivel x algoritmo** una cantidad `N` de veces, en
paralelo, y deja **un CSV con una fila por ejecución** para que otro sistema
haga el análisis después.

El esquema del CSV está documentado en [`SCHEMA.md`](SCHEMA.md).

```
analisis/
  config.json          config del runner (editá esto)
  main.py              CLI del runner
  config.py            BenchmarkConfig + load_benchmark_config
  runner.py            orquestador paralelo (backends process / thread)
  worker.py            una ejecución: parsear -> resolver -> verificar
  records.py           RunRecord (esquema del CSV) + writer incremental
  resultados/          CSVs generados (gitignoreados)
  SCHEMA.md            documentación de cada columna

  graficos_main.py     CLI de los gráficos: qué generar y de qué CSV
  graficos_datos.py    carga del CSV y agregación por (nivel, algoritmo)
  graficos_estilo.py   paleta validada y layout base
  graficos/            HTMLs generados (gitignoreados)
  requirements.txt     plotly (solo hace falta para los gráficos)
```

## Correrlo

Sin dependencias: solo la librería estándar.

```bash
python3 analisis/main.py                    # usa analisis/config.json
python3 analisis/main.py otro_config.json
python3 analisis/main.py --dry-run          # lista qué correría, sin correr nada
```

Las rutas relativas del config se resuelven contra la raíz del proyecto
(`Ejercicio2_sokoban/`), así que el runner anda igual desde cualquier directorio.

Flags para barrer sin editar el config (lo pisan):

```bash
python3 analisis/main.py --repetitions 10 --workers 8
python3 analisis/main.py --executor thread --timeout 30
python3 analisis/main.py --output-file corrida_final.csv --quiet
```

> No confundir con el `config.json` de la **raíz**, que es el de `run.py` y
> tiene otro esquema (una sola corrida: `level`/`algorithm`/`heuristic`). El del
> runner es `analisis/config.json`, en plural y con las opciones de paralelismo.

## Configuración

| Clave | Default | Qué hace |
|---|---|---|
| `executor` | `process` | `process` o `thread`. Ver [Threads vs. procesos](#threads-vs-procesos). |
| `workers` | `4` | Ejecuciones simultáneas. |
| `repetitions` | `3` | Cuántas veces se corre **cada** (nivel x algoritmo). |
| `timeout_seconds` | `60` | Corta una ejecución que se pasa. `null` = sin límite. |
| `memory_limit_mb` | `null` | Tope de memoria por worker. **Solo funciona en Linux** (ver abajo). |
| `levels` | — | Lista de stems de nivel, o `"all"` para todos los `.txt` de `levels_dir`. |
| `levels_dir` | `sokoban/levels` | Dónde buscar los niveles. |
| `algorithms` | — | Lista. Cada item es un string (`- bfs`) o un mapping (`{name, heuristic}`). |
| `output_dir` | `analisis/resultados` | Dónde dejar el CSV. |
| `output_file` | `null` | Nombre del CSV. `null` = `results_<run_id>.csv`, así cada tanda va a su archivo. |
| `include_solution` | `true` | Incluir la columna `solution` (el string completo de movimientos). |

JSON no tiene comentarios, así que **las claves que empiezan con `_` se ignoran**:
`config.json` las usa (`_comment_timeout`, etc.) para documentarse a sí mismo.

El config se valida entero **antes** de correr nada: niveles inexistentes,
algoritmos o heurísticas desconocidas y claves con typo cortan al instante con
un mensaje concreto, en vez de fallar media hora después.

La heurística solo aplica a los algoritmos informados (`astar`, `greedy`); en el
resto se ignora y sale vacía en el CSV, para no sugerir que influyó.

## Timeouts, memoria y algoritmos que no terminan

No todas las combinaciones terminan. Verificado en esta máquina con
`timeout_seconds: 60`:

- `aenigma_03` (4 cajas) es el nivel que más rechaza: `bfs`, `dfs`, `iddfs` y
  las dos `astar` no la resuelven en 60s. Solo `greedy` (con cualquier
  heurística) la resuelve, y lo hace casi instantáneo.
- `greedy` tampoco resuelve `level_69` (6 cajas), con ninguna heurística.
- El resto sí resuelve `level_69`, pero al límite: `bfs` ~31-33s, `dfs` ~18-20s,
  `astar` ~37-41s (ambas heurísticas). `bfs` expande **~4.044.079 nodos** ahí,
  con una frontera máxima de ~107k — varios GB de RAM en un solo worker.
- `iddfs` sobre `level_01_ufo` también resuelve, pero tarda ~45s: con un
  timeout menor a ese quedaría afuera igual que `aenigma_03`.

De ahí las dos precauciones del config:

- **`timeout_seconds` es prácticamente obligatorio.** Sin él, la tanda se cuelga
  para siempre en la primera combinación que no converge.
- **Cuidado con `workers` en niveles pesados.** 4 workers corriendo BFS sobre
  `level_69` son 4 búsquedas de varios GB en simultáneo. Si la máquina empieza a
  swapear, los tiempos dejan de significar algo: bajá `workers`.

`memory_limit_mb` usa `RLIMIT_AS`, que **solo implementa Linux**. En macOS y
Windows no tiene efecto: el runner lo detecta y avisa al arrancar en vez de
dejarte creer que estás protegido.

## Salida

```
analisis/resultados/results_<run_id>.csv
```

El CSV se escribe **incrementalmente**, flusheando cada fila. Una tanda larga que
se corta (Ctrl-C, OOM, se cierra la notebook) deja igual en disco todo lo que ya
había terminado.

Cada solución que un algoritmo devuelve se **verifica con el propio motor**
(`replay` + `is_goal`) antes de escribir la fila: la columna `solution_valid`
delata un algoritmo que devuelve movimientos inválidos. Si alguna da `False`, el
runner lo avisa al final por stderr.

Salida típica:

```
[ 6/20] ok        level_69 / bfs / rep 1   16.539s  cost=164 exp=4044079
[ 8/20] timeout   level_69 / iddfs / rep 1  25.046s  superó timeout_seconds=25.0

20 ejecuciones -> analisis/resultados/demo_full.csv
  ok=12  sin_solucion=0  timeout=8  error=0
```

## Gráficos

`graficos_main.py` lee un CSV de `resultados/` y genera gráficos Plotly, uno por
archivo HTML, más un `index.html` que los enlaza.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r analisis/requirements.txt   # plotly

python3 analisis/graficos_main.py                    # último CSV, gráficos activos
python3 analisis/graficos_main.py --listar           # qué CSVs y qué gráficos hay
python3 analisis/graficos_main.py --archivo analisis/resultados/demo_full.csv
python3 analisis/graficos_main.py --solo costo_vs_nivel,tiempo_vs_nivel
python3 analisis/graficos_main.py --abrir
```

**Qué se genera** se elige con el diccionario `GRAFICOS` arriba de
`graficos_main.py` (un `True`/`False` por gráfico), o con `--solo` / `--todos`
sin tocar el archivo. **De qué CSV** se elige con `ARCHIVO` o `--archivo`; por
defecto toma el más reciente de `resultados/` (salteando los que quedaron sin
filas por una corrida interrumpida).

Son **cuatro gráficos con la misma estructura**: el eje x es el **nivel**
(ordenado por dificultad creciente, medida en cantidad de cajas) y cada color es
un **algoritmo + heurística**. Dentro de cada nivel se comparan los algoritmos
entre sí; de nivel a nivel se ve cómo escala cada uno.

| Gráfico | Qué muestra | Escala |
|---|---|---|
| `costo_vs_nivel` | Largo de la solución: qué tan lejos del óptimo queda cada algoritmo | lineal |
| `tiempo_vs_nivel` | Tiempo medio de resolución | log |
| `nodos_vs_nivel` | Nodos expandidos: el esfuerzo de búsqueda, independiente de la máquina | log |
| `frontera_vs_nivel` | Pico de la frontera: el proxy de memoria | log |

Cuatro decisiones que vale la pena conocer al leerlos:

- **Las filas con `status != "ok"` nunca entran en un promedio.** Un `timeout`
  tiene `wall_seconds ≈ timeout_seconds`, que es un piso artificial. Las
  combinaciones que no terminaron aparecen marcadas como "no terminó · <motivo>"
  en el lugar exacto donde iría la barra, para que la ausencia no se lea como un
  cero.
- **El color identifica al algoritmo, no al nivel** (el nivel ya está en el eje
  x): es la serie que se sigue de grupo a grupo. La paleta está validada para
  daltonismo y contraste en claro y oscuro, y los slots se asignan **en orden
  fijo**, porque los pares validados son los adyacentes — que en barras
  agrupadas son los que quedan pegados. Hay 8 colores; con más algoritmos que
  eso los extras van a gris y el programa avisa por stderr.
- **El costo va en escala lineal y las otras tres en log.** El costo importa
  como proporción real (una solución 10x más larga es 10x peor); las demás
  métricas abarcan 4-6 órdenes de magnitud y en lineal el nivel más caro
  aplastaría a todos los demás contra el eje.
- **`repetitions` solo sirve para los tiempos.** Los algoritmos son
  deterministas: costo, nodos y frontera se repiten idénticos, y los gráficos
  los toman de la primera corrida exitosa. Si llegaran a variar, el runner de
  gráficos avisa por stderr.

## Uso programático

```python
from analisis import load_benchmark_config, run_benchmark
from analisis.records import write_csv


def main():
    config = load_benchmark_config("analisis/config.json")
    records = list(run_benchmark(config))
    write_csv(config.output_dir / "mi_tanda.csv", records)


if __name__ == "__main__":   # obligatorio: ver la advertencia de abajo
    main()
```

`run_benchmark` es un generador: emite cada `RunRecord` ni bien está listo, así
que se puede consumir en streaming en vez de esperar a que termine la tanda.

> **El `if __name__ == "__main__":` no es opcional.** Con `executor: process` el
> start method es `spawn`, y cada proceso hijo reimporta el módulo principal: sin
> el guard, el hijo vuelve a lanzar la tanda entera en cascada. Si el script se
> pasa por stdin (`python3 - <<EOF`) directamente no hay módulo que reimportar y
> **todas las filas salen con `status=error`**. Usá siempre un archivo `.py` con
> el guard, o el CLI (`analisis/main.py`), que ya lo tiene.

## Agregar un algoritmo o una heurística

El runner **no** tiene su propia lista de algoritmos: los toma de
`sokoban.search.ALGORITHMS` y `sokoban.search.HEURISTICS`. Si el equipo da de
alta uno nuevo en `sokoban/search/registry.py`, queda disponible acá
automáticamente — solo hay que nombrarlo en `algorithms` del config.
