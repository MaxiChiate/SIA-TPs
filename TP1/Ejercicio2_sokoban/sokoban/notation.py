"""Notación de movimientos usada para reproducir soluciones.

- minúscula = paso simple, no empuja caja: ``l r u d``
- MAYÚSCULA = empuje: mueve al jugador y a la caja que tiene adelante:
  ``L R U D``

`(dx, dy)` con `x` = columna (crece a la derecha) e `y` = fila (crece hacia
abajo), consistente con `Level`/`State`.
"""

from __future__ import annotations

Coord = tuple[int, int]

_DIRECTIONS: dict[str, Coord] = {
    "u": (0, -1),
    "d": (0, 1),
    "l": (-1, 0),
    "r": (1, 0),
}

MOVE_CHARS = frozenset("udlrUDLR")


def is_push(move: str) -> bool:
    """True si `move` es un empuje (mayúscula)."""
    return move.isupper()


def direction_of(move: str) -> Coord:
    """`(dx, dy)` asociado a un char de movimiento, sin importar el case."""
    try:
        return _DIRECTIONS[move.lower()]
    except KeyError as exc:
        raise ValueError(f"Movimiento desconocido: {move!r}") from exc
