"""Detección de deadlocks: estados desde los que ya no se puede llegar a la meta.

Un deadlock es un estado con alguna caja que no está sobre un goal y que no se
puede volver a mover *nunca más*. Seguir por ese camino es trabajo tirado: por
más movimientos que se hagan, esa caja se queda donde está.

La detección es conservadora: no encuentra todos los deadlocks posibles, pero
nunca da un falso positivo. Eso es lo que importa, porque los algoritmos la
usan para podar: marcar como deadlock un estado recuperable haría que BFS/IDDFS
pierdan la solución óptima (o que no encuentren solución).

Se aplican dos reglas, ambas sobre cajas que no están en un goal:

1. **Rincón**: la caja tiene pared arriba o abajo *y* pared a izquierda o
   derecha, así que no se la puede empujar en ningún eje. Como depende solo de
   las paredes y los goals, el conjunto de celdas "rincón" se precalcula una
   vez por nivel (`_celdas_muertas`) y el chequeo queda en un `in` de set.
2. **Bloque 2x2**: la caja forma parte de un cuadrado de 2x2 celdas ocupado
   enteramente por paredes y cajas. Ahí ninguna de esas cajas se puede empujar
   (la celda de destino está ocupada, o el jugador no puede pararse del otro
   lado), y como se traban entre sí el bloque es permanente. Esta regla solo
   agrega algo cuando hay otra caja en el cuadrado: un 2x2 lleno con una sola
   caja implica dos paredes perpendiculares, que ya es el caso 1.
"""

from __future__ import annotations

from functools import lru_cache

from ..state import Coord, Level, State


def is_deadlock(state: State, level: Level) -> bool:
    """True si `state` es irrecuperable y no vale la pena seguir por ese camino."""
    muertas = _celdas_muertas(level)
    for box in state.boxes:
        if box in muertas:
            return True
        if box not in level.goals and _en_bloque_2x2(box, state, level):
            return True
    return False


@lru_cache(maxsize=None)
def _celdas_muertas(level: Level) -> frozenset[Coord]:
    """Celdas que no son goal y son un rincón entre dos paredes perpendiculares:
    una caja que cae ahí ya no se mueve más. Solo depende del nivel."""
    return frozenset(
        (x, y)
        for x in range(level.width)
        for y in range(level.height)
        if (x, y) not in level.walls
        and (x, y) not in level.goals
        and ((x, y - 1) in level.walls or (x, y + 1) in level.walls)
        and ((x - 1, y) in level.walls or (x + 1, y) in level.walls)
    )


def _en_bloque_2x2(box: Coord, state: State, level: Level) -> bool:
    """Caja dentro de un cuadrado de 2x2 lleno de paredes y/o cajas."""
    x, y = box
    if not any(
        (x + dx, y + dy) in state.boxes for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
    ):
        return False  # sin otra caja al lado, el caso ya lo cubre `_celdas_muertas`
    for dx, dy in ((-1, -1), (-1, 0), (0, -1), (0, 0)):  # esquina superior izquierda
        cuadrado = (
            (x + dx, y + dy),
            (x + dx + 1, y + dy),
            (x + dx, y + dy + 1),
            (x + dx + 1, y + dy + 1),
        )
        if all(c in level.walls or c in state.boxes for c in cuadrado):
            return True
    return False
