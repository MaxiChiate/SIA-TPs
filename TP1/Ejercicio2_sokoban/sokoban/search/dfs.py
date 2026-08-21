"""DFS (Depth-First Search): búsqueda no informada, LIFO.

Búsqueda en grafo (marca visitado al encolar, no al desencolar) para no
reexplorar estados ya alcanzados por otro camino -- si no, en Sokoban hay
ciclos triviales (ida y vuelta del jugador) que la harían no terminar.

No garantiza el camino más corto: la solución encontrada puede ser mucho más
larga que la óptima.
"""

from __future__ import annotations

import time

from ..agent import SearchResult
from ..engine import apply_move, initial_state, is_goal, legal_moves
from ..state import Level
from ._common import Node, reconstruct_path


class DFSAgent:
    def solve(self, level: Level) -> SearchResult:
        start = time.perf_counter()

        root = Node(state=initial_state(level), parent=None, move=None, depth=0)
        if is_goal(root.state, level):
            elapsed = time.perf_counter() - start
            return SearchResult(True, "", 0, 0, 1, elapsed)

        stack: list[Node] = [root]
        visited = {root.state}
        nodes_expanded = 0
        max_frontier = 1

        while stack:
            max_frontier = max(max_frontier, len(stack))
            node = stack.pop()
            nodes_expanded += 1

            for move in legal_moves(node.state, level):
                child_state = apply_move(node.state, level, move)
                if child_state in visited:
                    continue
                visited.add(child_state)
                child = Node(child_state, node, move, node.depth + 1)

                if is_goal(child_state, level):
                    solution = reconstruct_path(child)
                    elapsed = time.perf_counter() - start
                    return SearchResult(
                        True, solution, len(solution), nodes_expanded, max_frontier, elapsed
                    )
                stack.append(child)

        elapsed = time.perf_counter() - start
        return SearchResult(False, "", 0, nodes_expanded, max_frontier, elapsed)
