"""BFS (Breadth-First Search): búsqueda no informada por niveles.

Como cada movimiento cuesta 1, BFS garantiza la solución con la menor
cantidad de movimientos posible -- a costa de guardar toda la frontera y el
conjunto de visitados en memoria.

`nodes_expanded` cuenta los estados sacados de la frontera y expandidos.
`frontier_nodes` es el tamaño máximo que alcanzó la frontera durante la
búsqueda (métrica más informativa que el tamaño final).
"""

from __future__ import annotations

import time
from collections import deque

from ..agent import SearchResult
from ..engine import apply_move, initial_state, is_goal, legal_moves
from ..state import Level
from ._common import Node, reconstruct_path


class BFSAgent:
    def solve(self, level: Level) -> SearchResult:
        start = time.perf_counter()

        root = Node(state=initial_state(level), parent=None, move=None, depth=0)
        if is_goal(root.state, level):
            elapsed = time.perf_counter() - start
            return SearchResult(True, "", 0, 0, 1, elapsed)

        frontier: deque[Node] = deque([root])
        visited = {root.state}
        nodes_expanded = 0
        max_frontier = 1

        while frontier:
            max_frontier = max(max_frontier, len(frontier))
            node = frontier.popleft()
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
                frontier.append(child)

        elapsed = time.perf_counter() - start
        return SearchResult(False, "", 0, nodes_expanded, max_frontier, elapsed)
