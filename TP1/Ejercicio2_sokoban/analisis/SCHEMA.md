# Esquema del CSV de resultados

Cada corrida de `analisis/main.py` produce **un CSV con una fila por ejecución**
(nivel x algoritmo x repetición). Este archivo documenta cada columna para el
sistema de análisis que lo consume.

- Codificación: UTF-8, separador `,`, comillas estándar (`csv` de Python).
- La primera fila es el header con los nombres de abajo, siempre en este orden.
- Las celdas vacías son `NULL` (Python `None`), no `0`. Pasa sobre todo en las
  filas con `status != "ok"`, donde no hay métricas que reportar.
- Los booleanos se serializan como `True` / `False`.
- Varios CSVs de tandas distintas se pueden concatenar: `run_id` los distingue.

```python
import pandas as pd
df = pd.read_csv("analisis/resultados/results_20260821T205430Z.csv")
ok = df[df.status == "ok"]                          # solo ejecuciones válidas
ok.groupby(["level", "algorithm_label"]).elapsed_seconds.agg(["mean", "std"])
```

## Identidad de la ejecución

| Columna | Tipo | Descripción |
|---|---|---|
| `run_id` | str | Id de la tanda completa (timestamp UTC, ej. `20260821T205430Z`). Igual en todas las filas del mismo CSV; sirve para distinguir tandas al concatenar archivos. |
| `level` | str | Nombre del nivel (stem del `.txt`, ej. `level_01_ufo`). |
| `algorithm` | str | Algoritmo: `bfs`, `dfs`, `iddfs`, `greedy`, `astar`, `hardcoded`. |
| `heuristic` | str \| NULL | Heurística usada. Solo la tienen los algoritmos informados (`astar`, `greedy`); vacía en el resto. |
| `algorithm_label` | str | `algorithm` + heurística (`astar:manhattan_sum`, o `bfs` si no es informado). **Es la clave para agrupar series en el análisis**: distingue el mismo algoritmo con distintas heurísticas. |
| `repetition` | int | Número de repetición, de `1` a `repetitions`. |

## Desenlace

| Columna | Tipo | Descripción |
|---|---|---|
| `status` | str | `ok` \| `no_solution` \| `timeout` \| `error`. Ver tabla de estados abajo. |
| `success` | bool | `True` solo si el agente encontró solución. Redundante con `status == "ok"`, se incluye porque es el campo del `SearchResult` original. |

### Valores de `status`

| Valor | Significado | ¿Tiene métricas? |
|---|---|---|
| `ok` | El agente terminó y encontró solución. | Sí, todas. |
| `no_solution` | El agente terminó y agotó el espacio de búsqueda sin encontrar solución. | Sí, salvo las de la solución (`cost` viene en 0). |
| `timeout` | Se cortó por `timeout_seconds`. **No hubo resultado**: no se sabe si habría resuelto. | No, solo `wall_seconds` (≈ el timeout). |
| `error` | Excepción, falta de memoria, o el worker murió. Ver `error_message`. | Normalmente no. |

> **Importante para el análisis**: filtrá por `status == "ok"` antes de promediar
> tiempos o nodos. Las filas `timeout` tienen `wall_seconds ≈ timeout_seconds`,
> que es un piso artificial, no el tiempo que el algoritmo hubiera tardado —
> promediarlas subestima groseramente el costo real. Tratalas como datos
> censurados: lo correcto es reportar la *tasa de éxito* por separado.

## Métricas del `SearchResult`

| Columna | Tipo | Descripción |
|---|---|---|
| `cost` | int \| NULL | Cantidad total de movimientos de la solución (empujes + pasos simples). Es lo que la consigna pide optimizar. |
| `nodes_expanded` | int \| NULL | Nodos sacados de la frontera y expandidos por la búsqueda. |
| `frontier_nodes` | int \| NULL | Tamaño **máximo** que alcanzó la frontera durante la búsqueda (no el final). Proxy del uso de memoria. |
| `elapsed_seconds` | float \| NULL | Tiempo que midió el propio agente alrededor de su búsqueda. **Es la columna de tiempo a usar en el análisis.** |
| `wall_seconds` | float | Tiempo medido por el runner alrededor de toda la ejecución. Incluye levantar el proceso, parsear el nivel y verificar la solución, así que siempre es un poco mayor que `elapsed_seconds`. Útil para costo total, no para comparar algoritmos. |

## Verificación de la solución

| Columna | Tipo | Descripción |
|---|---|---|
| `solution_valid` | bool \| NULL | El runner reproduce la solución con el motor (`replay` + `is_goal`). `True` = la solución es jugable y llega a los goals. **`False` señala un bug en el algoritmo**: esa fila no se debe promediar. |
| `pushes` | int \| NULL | Movimientos que empujan una caja (letras mayúsculas). |
| `simple_steps` | int \| NULL | Movimientos del jugador sin empujar (minúsculas). `pushes + simple_steps == cost`. |

## Características del nivel

Constantes por nivel; van repetidas en cada fila para que el CSV se analice sin
tener que cruzarlo con los archivos de niveles.

| Columna | Tipo | Descripción |
|---|---|---|
| `board_width` | int \| NULL | Ancho del tablero en celdas. |
| `board_height` | int \| NULL | Alto del tablero en celdas. |
| `boxes` | int \| NULL | Cantidad de cajas. Principal driver de la dificultad. |
| `goals` | int \| NULL | Cantidad de objetivos. |

## Contexto de ejecución

Iguales en toda la tanda. Están para que el CSV sea autocontenido y una medición
se pueda reproducir sin notas aparte.

| Columna | Tipo | Descripción |
|---|---|---|
| `executor` | str | `process` o `thread`. **Los tiempos de tandas con `thread` no son comparables con los de `process`** (ver README). |
| `workers` | int | Ejecuciones concurrentes configuradas. |
| `timeout_seconds` | float \| NULL | Timeout por ejecución. Vacío si no había. |
| `started_at_utc` | str | ISO-8601 UTC del arranque de la tanda. |
| `hostname` | str | Máquina donde se corrió. |
| `python_version` | str | Ej. `3.14.3`. |
| `cpu_count` | int \| NULL | CPUs lógicas de la máquina. |
| `git_commit` | str \| NULL | SHA corto del repo al momento de correr, para atar los números a una versión del código. |

## Extras

| Columna | Tipo | Descripción |
|---|---|---|
| `error_message` | str \| NULL | Detalle cuando `status` es `timeout`/`error`. También se llena en filas `ok` si la verificación de la solución falló. |
| `solution` | str \| NULL | String completo de movimientos (`u/d/l/r` = paso, `U/D/L/R` = empuje). Se puede omitir con `include_solution: false` en el config, y en ese caso **la columna no aparece en el CSV**. |

## Nota sobre determinismo

Los cinco algoritmos son deterministas: para un mismo (nivel, algoritmo,
heurística), `cost`, `nodes_expanded`, `frontier_nodes` y `solution` son
**idénticos en todas las repeticiones**. Lo único que varía entre repeticiones
es el tiempo (`elapsed_seconds`, `wall_seconds`).

O sea: `repetitions` sirve para promediar tiempos y estimar su dispersión, no
para muestrear resultados distintos. Para las métricas no temporales alcanza con
tomar una repetición cualquiera (o verificar con un `nunique() == 1` que
efectivamente no varían).
