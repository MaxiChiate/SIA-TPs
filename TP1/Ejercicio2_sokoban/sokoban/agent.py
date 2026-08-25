"""Interfaz del agente: el enchufe donde el equipo conecta la Fase 1.

`Agent` es el protocolo que van a implementar `search/bfs.py`, `dfs.py`,
`greedy.py`, `astar.py` e `iddfs.py`, usando `legal_moves`/`apply_move`/`is_goal`
de `engine.py`. `HardcodedAgent` es la Fase 0: un cable pelado que, para el
único nivel que tenemos, devuelve la solución ya conocida -- sirve solo para
probar que el motor y el visualizador andan de punta a punta.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from .state import Level

# Solución de referencia para levels/aenigma_01.txt (86 movimientos,
# verificada por el golden test en tests/test_replay_known_solution.py).
_UFO_SOLUTION = (
    "LruulldlddrUUUUdddlllluurururRRlddrruUUdrrddllddRluurrdrddl"
    "UUUUddrdrrruulululLLrddlluU"
)


@dataclass(frozen=True, slots=True)
class SearchResult:
    """Resultado uniforme que cualquier `Agent` (hardcodeado o de búsqueda) devuelve."""

    success: bool
    solution: str
    cost: int
    nodes_expanded: int
    frontier_nodes: int
    elapsed_seconds: float


class Agent(Protocol):
    def solve(self, level: Level) -> SearchResult: ...


class HardcodedAgent:
    """Fase 0: devuelve una solución hardcodeada conocida de antemano.

    Solo conoce `aenigma_01` (matchea por `Level.name`). No busca nada:
    `nodes_expanded` y `frontier_nodes` son N/A (0) para este agente.
    """

    _SOLUTIONS: dict[str, str] = {"aenigma_01": _UFO_SOLUTION}

    def solve(self, level: Level) -> SearchResult:
        start = time.perf_counter()
        solution = self._SOLUTIONS.get(level.name)
        elapsed = time.perf_counter() - start
        if solution is None:
            return SearchResult(
                success=False,
                solution="",
                cost=0,
                nodes_expanded=0,
                frontier_nodes=0,
                elapsed_seconds=elapsed,
            )
        return SearchResult(
            success=True,
            solution=solution,
            cost=len(solution),
            nodes_expanded=0,
            frontier_nodes=0,
            elapsed_seconds=elapsed,
        )
