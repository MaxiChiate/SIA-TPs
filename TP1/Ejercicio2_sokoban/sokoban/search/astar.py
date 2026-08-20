"""A* sobre `legal_moves`/`apply_move`/`is_goal`, usando `heuristics.manhattan_sum`.

Nodo = `State` (`player`, `boxes`), que ya es hasheable de fábrica (ver
`state.py`). Costo de cada movimiento (empuje o paso simple) = 1, así que
`cost` en `SearchResult` termina siendo `len(solution)`, como pide la consigna.
"""

from __future__ import annotations

import heapq
import itertools
import time

from ..agent import SearchResult
from ..engine import apply_move, is_goal, legal_moves
from ..state import Level, State
from .heuristics import manhattan_sum


class AStarAgent:
    """Implementa el protocolo `Agent` con A* + `manhattan_sum`."""

    def solve(self, level: Level) -> SearchResult:
        start_time = time.perf_counter()

        start_state = State(player=level.initial_player, boxes=level.initial_boxes)
        counter = itertools.count()  # desempata en el heap sin comparar States

        g_score: dict[State, int] = {start_state: 0}
        came_from: dict[State, tuple[State, str]] = {}
        closed: set[State] = set()

        open_heap: list[tuple[int, int, State]] = [
            (manhattan_sum(start_state, level), next(counter), start_state)
        ]

        nodes_expanded = 0
        max_frontier = len(open_heap)

        while open_heap:
            max_frontier = max(max_frontier, len(open_heap))
            _, _, current = heapq.heappop(open_heap)

            if current in closed:
                continue  # entrada obsoleta: ya se expandió con un g menor o igual
            closed.add(current)
            nodes_expanded += 1

            if is_goal(current, level):
                solution = self._reconstruct(came_from, current)
                return SearchResult(
                    success=True,
                    solution=solution,
                    cost=len(solution),
                    nodes_expanded=nodes_expanded,
                    frontier_nodes=max_frontier,
                    elapsed_seconds=time.perf_counter() - start_time,
                )

            current_g = g_score[current]
            for move in legal_moves(current, level):
                neighbor = apply_move(current, level, move)
                if neighbor in closed:
                    continue
                tentative_g = current_g + 1
                if tentative_g < g_score.get(neighbor, float("inf")):
                    g_score[neighbor] = tentative_g
                    came_from[neighbor] = (current, move)
                    f_score = tentative_g + manhattan_sum(neighbor, level)
                    heapq.heappush(open_heap, (f_score, next(counter), neighbor))

        return SearchResult(
            success=False,
            solution="",
            cost=0,
            nodes_expanded=nodes_expanded,
            frontier_nodes=max_frontier,
            elapsed_seconds=time.perf_counter() - start_time,
        )

    @staticmethod
    def _reconstruct(
        came_from: dict[State, tuple[State, str]], goal_state: State
    ) -> str:
        """Recorre `came_from` desde el goal hasta el estado inicial y arma
        la solución en el orden correcto (`came_from` no tiene entrada para
        el estado inicial, así que el loop corta solo)."""
        moves: list[str] = []
        state = goal_state
        while state in came_from:
            prev_state, move = came_from[state]
            moves.append(move)
            state = prev_state
        moves.reverse()
        return "".join(moves)
