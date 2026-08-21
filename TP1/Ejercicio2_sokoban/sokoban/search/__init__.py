"""Fase 1 (equipo): acá van bfs.py, dfs.py, greedy.py, astar.py, iddfs.py.

Cada uno implementa el protocolo `Agent` de `sokoban.agent` usando
`legal_moves`/`apply_move`/`is_goal` de `sokoban.engine`, y llena
`nodes_expanded`/`frontier_nodes` reales en `SearchResult` (Fase 2).
"""

from .registry import ALGORITHMS, INFORMED_ALGORITHMS, build_agent
from .heuristics import HEURISTICS

__all__ = ["ALGORITHMS", "INFORMED_ALGORITHMS", "HEURISTICS", "build_agent"]
