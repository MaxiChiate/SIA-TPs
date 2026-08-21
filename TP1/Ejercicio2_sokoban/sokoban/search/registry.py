"""Registro de algoritmos/heurísticas + fábrica de `Agent` a partir de un `RunConfig`.

Este es el único lugar que conoce el mapeo string -> implementación. Agregar un
algoritmo nuevo (`bfs.py`, `dfs.py`, etc.) es: implementarlo en `search/`,
importarlo acá y sumar una entrada a `ALGORITHMS`. `config.json` nunca importa
clases de Python directamente, solo nombres.
"""

from __future__ import annotations

from typing import Callable

from ..agent import Agent, HardcodedAgent
from .astar import AStarAgent
from .heuristics import HEURISTICS, Heuristic

# Heurísticas soportadas: nombre (tal como aparece en config.json) -> función.
# Reexportado desde heuristics.py para que este módulo sea el único punto de
# entrada del registro (algoritmos + heurísticas).


def _build_astar(heuristic: Heuristic | None) -> Agent:
    return AStarAgent(heuristic=heuristic)


def _build_hardcoded(heuristic: Heuristic | None) -> Agent:
    # Fase 0: no busca nada, así que ignora la heurística por completo.
    return HardcodedAgent()


def _not_implemented(name: str) -> Callable[[Heuristic | None], Agent]:
    def _factory(heuristic: Heuristic | None) -> Agent:
        raise NotImplementedError(
            f"El algoritmo {name!r} todavía no está implementado en "
            f"sokoban/search/{name}.py. Algoritmos disponibles: "
            f"{sorted(ALGORITHMS)}."
        )

    return _factory


# Nombre (config.json: "algorithm") -> fábrica que recibe la heurística ya
# resuelta (o `None` si el algoritmo no es informado) y devuelve un `Agent`
# listo para `.solve(level)`. `hardcoded` es la Fase 0 (`HardcodedAgent`, solo
# conoce `level_01_ufo`); bfs/dfs/iddfs son placeholders para cuando el equipo
# los implemente.
ALGORITHMS: dict[str, Callable[[Heuristic | None], Agent]] = {
    "astar": _build_astar,
    "hardcoded": _build_hardcoded,
    "bfs": _not_implemented("bfs"),
    "dfs": _not_implemented("dfs"),
    "greedy": _not_implemented("greedy"),
    "iddfs": _not_implemented("iddfs"),
}

# Algoritmos que efectivamente usan la heurística. Los que no están acá
# (hardcoded/bfs/dfs/iddfs) reciben `heuristic=None` sin validar el nombre
# que haya en config.json, porque para ellos ese campo no aplica.
INFORMED_ALGORITHMS = {"astar", "greedy"}


def build_agent(algorithm: str, heuristic: str | None) -> Agent:
    """Instancia el `Agent` que le corresponde a `algorithm`/`heuristic`.

    `algorithm` y `heuristic` son los strings crudos de `config.json` (ver
    `sokoban.config.RunConfig`). Tira `ValueError` con nombres disponibles si
    alguno no matchea. Para algoritmos no informados, `heuristic` no se
    valida (es irrelevante para ellos).
    """
    try:
        factory = ALGORITHMS[algorithm]
    except KeyError as exc:
        raise ValueError(
            f"Algoritmo desconocido {algorithm!r}. Disponibles: {sorted(ALGORITHMS)}."
        ) from exc

    if algorithm not in INFORMED_ALGORITHMS:
        return factory(None)

    heuristic_name = heuristic or "manhattan_sum"
    try:
        heuristic_fn = HEURISTICS[heuristic_name]
    except KeyError as exc:
        raise ValueError(
            f"Heurística desconocida {heuristic_name!r}. "
            f"Disponibles: {sorted(HEURISTICS)}."
        ) from exc

    return factory(heuristic_fn)
