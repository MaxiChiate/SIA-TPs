"""IDDFS (Iterative Deepening DFS): corre DFS con límite de profundidad
creciente (0, 1, 2, ...) hasta encontrar la meta.

Combina la poca memoria de DFS con la garantía de optimalidad de BFS (para
costos uniformes): la primera vez que encuentra la meta es a la profundidad
mínima posible.

Nota de implementación: cada iteración con límite `d` es una búsqueda en
grafo (visited *por iteración*, no solo por camino ancestro). Un IDDFS de
libro que solo evita ciclos entre ancestros explota en Sokoban porque hay
muchísimas transposiciones (distintos órdenes de movimiento llegan al mismo
`State`); reexplorarlas todas en cada nivel de profundidad lo vuelve
intratable incluso para niveles chicos. Usar un `visited` por iteración es
la simplificación estándar para que IDDFS sea utilizable en este dominio.

`nodes_expanded` y `frontier_nodes` se acumulan sumando/tomando el máximo a
través de todas las iteraciones (el trabajo repetido en cada nivel de
profundidad es intrínseco al algoritmo).
"""

from __future__ import annotations

import time

from ..agent import SearchResult
from ..engine import apply_move, initial_state, is_goal, legal_moves
from ..state import Level, State
from ._common import Node, reconstruct_path

_MAX_DEPTH = 500


def _depth_limited_search(level: Level, limit: int) -> tuple[Node | None, int, int]:
    """DFS en grafo acotado a `limit` movimientos. Devuelve (nodo_meta_o_None, nodes_expanded, max_frontier)."""
    root = Node(state=initial_state(level), parent=None, move=None, depth=0)
    if is_goal(root.state, level):
        return root, 0, 1

    stack: list[Node] = [root]
    best_depth_seen: dict[State, int] = {root.state: 0}
    nodes_expanded = 0
    max_frontier = 1

    while stack:
        max_frontier = max(max_frontier, len(stack))
        node = stack.pop()
        if node.depth >= limit:
            continue
        nodes_expanded += 1

        for move in legal_moves(node.state, level):
            child_state = apply_move(node.state, level, move)
            child_depth = node.depth + 1
            if child_state in best_depth_seen and best_depth_seen[child_state] <= child_depth:
                continue
            best_depth_seen[child_state] = child_depth
            child = Node(child_state, node, move, child_depth)

            if is_goal(child_state, level):
                return child, nodes_expanded, max_frontier
            stack.append(child)

    return None, nodes_expanded, max_frontier


class IDDFSAgent:
    def solve(self, level: Level) -> SearchResult:
        start = time.perf_counter()

        total_nodes_expanded = 0
        max_frontier = 1

        for limit in range(_MAX_DEPTH + 1):
            goal_node, nodes_expanded, frontier = _depth_limited_search(level, limit)
            total_nodes_expanded += nodes_expanded
            max_frontier = max(max_frontier, frontier)

            if goal_node is not None:
                solution = reconstruct_path(goal_node)
                elapsed = time.perf_counter() - start
                return SearchResult(
                    True, solution, len(solution), total_nodes_expanded, max_frontier, elapsed
                )

        elapsed = time.perf_counter() - start
        return SearchResult(False, "", 0, total_nodes_expanded, max_frontier, elapsed)
