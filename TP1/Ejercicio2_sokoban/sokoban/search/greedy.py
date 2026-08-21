"""Greedy Best-First Search: búsqueda informada que expande siempre el nodo
con menor `heuristic(state, level)`, ignorando el costo ya acumulado.

Rápida pero no óptima: no garantiza la menor cantidad de movimientos, solo
que corta camino hacia estados que la heurística considera "cerca" de la
meta.

Si no se pasa una heurística propia (la que arme el equipo en Fase 1), usa
por default la suma de distancias Manhattan de cada caja a su goal más
cercano -- una heurística razonable aunque no admisible (no considera
paredes ni colisiones entre cajas).
"""

from __future__ import annotations

import heapq
import itertools
import time
from typing import Callable

from ..agent import SearchResult
from ..engine import apply_move, initial_state, is_goal, legal_moves
from ..state import Level, State
from ._common import Node, reconstruct_path

HeuristicFn = Callable[[State, Level], int]


def _default_heuristic(state: State, level: Level) -> int:
    if not state.boxes or not level.goals:
        return 0
    total = 0
    for bx, by in state.boxes:
        total += min(abs(bx - gx) + abs(by - gy) for gx, gy in level.goals)
    return total


class GreedyAgent:
    def __init__(self, heuristic: HeuristicFn | None = None):
        self.heuristic = heuristic or _default_heuristic

    def solve(self, level: Level) -> SearchResult:
        start = time.perf_counter()

        root = Node(state=initial_state(level), parent=None, move=None, depth=0)
        if is_goal(root.state, level):
            elapsed = time.perf_counter() - start
            return SearchResult(True, "", 0, 0, 1, elapsed)

        tiebreak = itertools.count()
        frontier: list[tuple[int, int, Node]] = [
            (self.heuristic(root.state, level), next(tiebreak), root)
        ]
        visited = {root.state}
        nodes_expanded = 0
        max_frontier = 1

        while frontier:
            max_frontier = max(max_frontier, len(frontier))
            _, _, node = heapq.heappop(frontier)
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
                heapq.heappush(
                    frontier, (self.heuristic(child_state, level), next(tiebreak), child)
                )

        elapsed = time.perf_counter() - start
        return SearchResult(False, "", 0, nodes_expanded, max_frontier, elapsed)
