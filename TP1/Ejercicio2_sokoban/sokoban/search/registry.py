"""Registro de algoritmos/heurísticas + fábrica de `Agent` a partir de un `RunConfig`.

Este es el único lugar que conoce el mapeo string -> implementación. Agregar un
algoritmo nuevo (`bfs.py`, `dfs.py`, etc.) es: implementarlo en `search/`,
importarlo acá y sumar una entrada a `ALGORITHMS`. `config.json` nunca importa
clases de Python directamente, solo nombres.
"""

from __future__ import annotations

from typing import Callable

from ..agent import Agent
from .astar import AStarAgent
from .heuristics import HEURISTICS, Heuristic

# Heurísticas soportadas: nombre (tal como aparece en config.json) -> función.
# Reexportado desde heuristics.py para que este módulo sea el único punto de
# entrada del registro (algoritmos + heurísticas).


def _build_astar(heuristic: Heuristic) -> Agent:
    return AStarAgent(heuristic=heuristic)


def _not_implemented(name: str) -> Callable[[Heuristic], Agent]:
    def _factory(heuristic: Heuristic) -> Agent:
        raise NotImplementedError(
            f"El algoritmo {name!r} todavía no está implementado en "
            f"sokoban/search/{name}.py. Algoritmos disponibles: "
            f"{sorted(ALGORITHMS)}."
        )

    return _factory


# Nombre (config.json: "algorithm") -> fábrica que recibe la heurística ya
# resuelta y devuelve un `Agent` listo para `.solve(level)`. Los algoritmos no
# informados (bfs/dfs/iddfs) ignoran la heurística; queda documentado acá para
# cuando el equipo los implemente.
ALGORITHMS: dict[str, Callable[[Heuristic], Agent]] = {
    "astar": _build_astar,
    "bfs": _not_implemented("bfs"),
    "dfs": _not_implemented("dfs"),
    "greedy": _not_implemented("greedy"),
    "iddfs": _not_implemented("iddfs"),
}

# Algoritmos que efectivamente usan la heurística (para validar config.json:
# si algorithm no está acá, "heuristic" es ignorado y no hace falta pedirlo).
INFORMED_ALGORITHMS = {"astar", "greedy"}


def build_agent(algorithm: str, heuristic: str | None) -> Agent:
    """Instancia el `Agent` que le corresponde a `algorithm`/`heuristic`.

    `algorithm` y `heuristic` son los strings crudos de `config.json` (ver
    `sokoban.config.RunConfig`). Tira `ValueError` con nombres disponibles si
    alguno no matchea.
    """
    try:
        factory = ALGORITHMS[algorithm]
    except KeyError as exc:
        raise ValueError(
            f"Algoritmo desconocido {algorithm!r}. Disponibles: {sorted(ALGORITHMS)}."
        ) from exc

    heuristic_name = heuristic or "manhattan_sum"
    try:
        heuristic_fn = HEURISTICS[heuristic_name]
    except KeyError as exc:
        raise ValueError(
            f"Heurística desconocida {heuristic_name!r}. "
            f"Disponibles: {sorted(HEURISTICS)}."
        ) from exc

    return factory(heuristic_fn)
