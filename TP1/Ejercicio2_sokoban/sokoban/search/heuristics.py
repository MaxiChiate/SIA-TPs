"""Heurísticas para Greedy/A* (Fase 1, equipo)."""

from __future__ import annotations

from typing import Callable

from ..state import Coord, Level, State

Heuristic = Callable[[State, Level], int]


def manhattan_sum(state: State, level: Level) -> int:
    """Costo mínimo de asignar cada caja a un goal distinto (suma de
    distancias Manhattan). Admisible.

    El matching óptimo se resuelve con el algoritmo húngaro (O(cajas^2 *
    goals)) en vez de fuerza bruta con `itertools.permutations` (factorial):
    con 6 cajas eso son 720 asignaciones evaluadas *por cada nodo* que
    expande la búsqueda, y con niveles de más cajas se vuelve intratable.
    """
    boxes = list(state.boxes)
    goals = list(level.goals)
    if not boxes:
        return 0

    cost = [[_manhattan(box, goal) for goal in goals] for box in boxes]
    return _min_cost_assignment(cost)


def is_deadlock(state: State, level: Level) -> bool:
    """True si algún caja no está sobre un goal y quedó encajonada en un
    rincón formado por dos paredes perpendiculares -- no se la puede
    empujar en ningún eje nunca más, así que el estado es irrecuperable.

    No detecta todos los deadlocks posibles (p. ej. dos cajas trabadas
    entre sí, o contra una pared sin rincón), pero podar estos ya reduce
    mucho el espacio de búsqueda en niveles con varias cajas, sin nunca dar
    un falso positivo (si detecta deadlock, realmente lo es).
    """
    for x, y in state.boxes:
        if (x, y) in level.goals:
            continue
        blocked_vertical = (x, y - 1) in level.walls or (x, y + 1) in level.walls
        blocked_horizontal = (x - 1, y) in level.walls or (x + 1, y) in level.walls
        if blocked_vertical and blocked_horizontal:
            return True
    return False


def _min_cost_assignment(cost: list[list[int]]) -> int:
    """Algoritmo húngaro (Kuhn-Munkres) para el matching de costo mínimo
    entre `len(cost)` filas y `len(cost[0])` columnas, con filas <= columnas
    (siempre se cumple acá: no puede haber más cajas que goals en un nivel
    resoluble). Devuelve la suma de costos del matching óptimo."""
    n = len(cost)
    m = len(cost[0])
    inf = float("inf")
    u = [0.0] * (n + 1)
    v = [0.0] * (m + 1)
    p = [0] * (m + 1)  # p[j] = fila (1-indexada) asignada a la columna j
    way = [0] * (m + 1)

    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [inf] * (m + 1)
        used = [False] * (m + 1)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = inf
            j1 = -1
            for j in range(1, m + 1):
                if used[j]:
                    continue
                cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                if cur < minv[j]:
                    minv[j] = cur
                    way[j] = j0
                if minv[j] < delta:
                    delta = minv[j]
                    j1 = j
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1

    return int(sum(cost[p[j] - 1][j - 1] for j in range(1, m + 1) if p[j] != 0))


def _manhattan(a: Coord, b: Coord) -> int:
    """Distancia Manhattan entre dos coordenadas. Helper para las de arriba."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


HEURISTICS: dict[str, Heuristic] = {
    "manhattan_sum": manhattan_sum,
}
