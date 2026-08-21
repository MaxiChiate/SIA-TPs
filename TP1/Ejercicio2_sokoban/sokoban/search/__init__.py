"""Fase 1 (equipo): bfs.py, dfs.py, greedy.py, iddfs.py -- astar.py, pendiente.

Cada uno implementa el protocolo `Agent` de `sokoban.agent` usando
`legal_moves`/`apply_move`/`is_goal` de `sokoban.engine`, y llena
`nodes_expanded`/`frontier_nodes` reales en `SearchResult`.

`ALGORITHMS` (ver `registry.py`) mapea nombre -> factory de `Agent`.
"""

from __future__ import annotations

from .registry import ALGORITHMS, INFORMED_ALGORITHMS, build_agent
from .heuristics import HEURISTICS

__all__ = ["ALGORITHMS", "INFORMED_ALGORITHMS", "HEURISTICS", "build_agent"]
