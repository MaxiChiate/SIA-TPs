"""Heurísticas para Greedy/A* (Fase 1, equipo).

Toda heurística tiene la misma firma: `(state, level) -> int`, para que
`greedy.py`/`astar.py` las reciban como parámetro sin acoplarse a una sola.

Admisible = nunca sobreestima el costo real hasta la meta (necesario para que
A* devuelva la solución óptima). `manhattan_sum` lo es; si agregan una
heurística no admisible (para comparar en el informe), déjenlo documentado.
"""

from __future__ import annotations

from itertools import permutations
from typing import Callable

from ..state import Coord, Level, State

Heuristic = Callable[[State, Level], int]


def manhattan_sum(state: State, level: Level) -> int:
    """Costo mínimo de asignar cada caja a un goal distinto (suma de
    distancias Manhattan), probando todas las asignaciones posibles.

    Arma la matriz cajas x goals con `_manhattan`, y por fuerza bruta
    (permutaciones de goals tomados de a `len(boxes)`) busca la asignación
    de costo total mínimo. Admisible: nunca sobreestima, porque el costo
    real de mover todas las cajas a sus goals no puede ser menor que la
    mejor asignación biyectiva de distancias en línea recta.

    Con pocas cajas (2-4, como en level_01_ufo) esto es instantáneo; con
    muchas más se vuelve caro (factorial) y convendría el algoritmo húngaro.
    """
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
    """Detección de posiciones sin salida (caja empujada a una esquina sin
    goal, contra una pared sin goal en toda la fila/columna, etc.).

    No es una heurística en sí -- se usa para podar nodos en la búsqueda
    (ni Greedy ni A* van a expandir un estado si esto da True). Opcional para
    Fase 1, pero ayuda mucho a nodes_expanded en niveles con más cajas.

    TODO: implementar (o dejar `return False` si no lo usan todavía).
    """
    raise NotImplementedError


def _manhattan(a: Coord, b: Coord) -> int:
    """Distancia Manhattan entre dos coordenadas. Helper para las de arriba."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


# Nombre -> función, para que `config.json` pueda seleccionar la heurística
# por string (ver `sokoban/search/registry.py`).
HEURISTICS: dict[str, Heuristic] = {
    "manhattan_sum": manhattan_sum,
}
