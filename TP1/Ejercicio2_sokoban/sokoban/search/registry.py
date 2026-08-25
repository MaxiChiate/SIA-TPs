"""Mapea nombres de `config.json` a clases de `Agent`."""

from __future__ import annotations

from typing import Callable

from ..agent import Agent, HardcodedAgent
from .astar import AStarAgent
from .bfs import BFSAgent
from .dfs import DFSAgent
from .greedy import GreedyAgent
from .iddfs import IDDFSAgent

from .heuristics import HEURISTICS, Heuristic


def _build_astar(heuristic: Heuristic | None) -> Agent:
    return AStarAgent(heuristic=heuristic)


def _build_hardcoded(heuristic: Heuristic | None) -> Agent:
    return HardcodedAgent()


def _not_implemented(name: str) -> Callable[[Heuristic | None], Agent]:
    def _factory(heuristic: Heuristic | None) -> Agent:
        raise NotImplementedError(
            f"El algoritmo {name!r} todavía no está implementado en "
            f"sokoban/search/{name}.py. Algoritmos disponibles: "
            f"{sorted(ALGORITHMS)}."
        )

    return _factory


ALGORITHMS: dict[str, Callable[[Heuristic | None], Agent]] = {
    "astar": _build_astar,
    "hardcoded": _build_hardcoded,
    "bfs": lambda heuristic: BFSAgent(),
    "dfs": lambda heuristic: DFSAgent(),
    "greedy": lambda heuristic: GreedyAgent(heuristic), 
    "iddfs": lambda heuristic: IDDFSAgent(), 
}

INFORMED_ALGORITHMS = {"astar", "greedy"}


def build_agent(algorithm: str, heuristic: str | None) -> Agent:
    """Instancia el `Agent` de `config.json`; tira `ValueError` si no matchea."""
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
