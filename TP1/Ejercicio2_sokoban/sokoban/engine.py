"""Motor de reglas: aplicar movimientos, reproducir soluciones, chequear la meta.

Esta es la única API que el equipo necesita para escribir BFS/DFS/Greedy/A*/IDDFS
en `search/`: `legal_moves` + `apply_move` + `is_goal`.
"""

from __future__ import annotations

from .notation import direction_of, is_push
from .state import Level, State

Coord = tuple[int, int]


class MoveError(ValueError):
    """Un movimiento no se puede aplicar en el estado actual."""


def initial_state(level: Level) -> State:
    """El `State` de arranque de un nivel."""
    return State(player=level.initial_player, boxes=level.initial_boxes)


def _add(pos: Coord, delta: Coord) -> Coord:
    return (pos[0] + delta[0], pos[1] + delta[1])


def apply_move(state: State, level: Level, move: str) -> State:
    """Aplica un único movimiento (notación `u/d/l/r/U/D/L/R`) y devuelve el `State` resultante.

    Levanta `MoveError` si:
    - el destino es pared;
    - es empuje pero no hay caja adelante;
    - es paso simple pero hay una caja adelante (ese char debería ser mayúscula);
    - el empuje choca la caja contra una pared o contra otra caja.
    """
    delta = direction_of(move)
    push = is_push(move)
    dest = _add(state.player, delta)

    if dest in level.walls:
        raise MoveError(f"Movimiento {move!r} inválido: {dest} es pared")

    box_ahead = dest in state.boxes

    if push:
        if not box_ahead:
            raise MoveError(
                f"Movimiento {move!r} es un empuje pero no hay caja en {dest}"
            )
        box_dest = _add(dest, delta)
        if box_dest in level.walls:
            raise MoveError(
                f"Empuje {move!r} inválido: la caja chocaría contra una pared en {box_dest}"
            )
        if box_dest in state.boxes:
            raise MoveError(
                f"Empuje {move!r} inválido: la caja chocaría contra otra caja en {box_dest}"
            )
        new_boxes = frozenset((state.boxes - {dest}) | {box_dest})
        return State(player=dest, boxes=new_boxes)

    if box_ahead:
        raise MoveError(
            f"Movimiento {move!r} es un paso simple pero hay una caja en {dest} "
            "(¿debería ser mayúscula?)"
        )
    return State(player=dest, boxes=state.boxes)


def replay(level: Level, solution: str) -> list[State]:
    """Aplica `solution` movimiento a movimiento y devuelve la traza completa de estados.

    El primer elemento es el estado inicial; hay `len(solution) + 1` estados.
    """
    trace = [initial_state(level)]
    for move in solution:
        trace.append(apply_move(trace[-1], level, move))
    return trace


def is_goal(state: State, level: Level) -> bool:
    """True si todas las cajas están sobre algún objetivo."""
    return state.boxes <= level.goals


def legal_moves(state: State, level: Level) -> list[str]:
    """Movimientos aplicables desde `state`, en notación `u/d/l/r/U/D/L/R`.

    Para que la búsqueda del equipo no tenga que reinventar esta lógica.
    """
    moves: list[str] = []
    for lower, upper in (("u", "U"), ("d", "D"), ("l", "L"), ("r", "R")):
        delta = direction_of(lower)
        dest = _add(state.player, delta)
        if dest in level.walls:
            continue
        if dest in state.boxes:
            box_dest = _add(dest, delta)
            if box_dest not in level.walls and box_dest not in state.boxes:
                moves.append(upper)
        else:
            moves.append(lower)
    return moves
