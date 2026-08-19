"""Modelo de datos: `Level` (estático) y `State` (lo que cambia con cada movimiento).

`walls` y `goals` viven en `Level`, no en `State`: así `State` queda chico y
hasheable -- (player, boxes) es exactamente lo que la búsqueda del equipo va a
usar como clave del visited/closed set en BFS/A*.
"""

from __future__ import annotations

from dataclasses import dataclass

Coord = tuple[int, int]


@dataclass(frozen=True, slots=True)
class Level:
    """Descripción estática de un nivel. No cambia durante la búsqueda."""

    width: int
    height: int
    walls: frozenset[Coord]
    goals: frozenset[Coord]
    initial_player: Coord
    initial_boxes: frozenset[Coord]
    name: str


@dataclass(frozen=True, slots=True)
class State:
    """Snapshot mutable del juego: posición del jugador y de las cajas."""

    player: Coord
    boxes: frozenset[Coord]
