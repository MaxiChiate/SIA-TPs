"""Heurísticas para Greedy/A* (Fase 1, equipo)."""

from __future__ import annotations

from itertools import permutations
from typing import Callable

from ..state import Coord, Level, State

Heuristic = Callable[[State, Level], int]


def manhattan_sum(state: State, level: Level) -> int:
    """Costo mínimo de asignar cada caja a un goal distinto (suma de
    distancias Manhattan). Admisible; factorial en cantidad de cajas."""
    boxes = list(state.boxes)
    goals = list(level.goals)
    if not boxes:
        return 0

    distances = [[_manhattan(box, goal) for goal in goals] for box in boxes]

    return min(
        sum(distances[i][goal_index] for i, goal_index in enumerate(assignment))
        for assignment in permutations(range(len(goals)), len(boxes))
    )


def is_deadlock(state: State, level: Level) -> bool:
    """Detección de posiciones sin salida, para podar la búsqueda. TODO."""
    raise NotImplementedError


def _manhattan(a: Coord, b: Coord) -> int:
    """Distancia Manhattan entre dos coordenadas. Helper para las de arriba."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


HEURISTICS: dict[str, Heuristic] = {
    "manhattan_sum": manhattan_sum,
}
