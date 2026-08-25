"""Utilidades compartidas por los algoritmos de `sokoban/search/`.

`Node` es un nodo de árbol de búsqueda liviano (estado + puntero al padre +
movimiento que lo generó), para no tener que arrastrar el string de la
solución completa en cada nodo de la frontera.

`successors` es el generador de hijos que usan los cinco algoritmos: ahí
vive la poda de deadlocks, así que ningún agente tiene que acordarse de
hacerla.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from ..engine import apply_move, legal_moves
from ..state import Level, State
from .deadlock import is_deadlock


@dataclass(slots=True)
class Node:
    state: State
    parent: "Node | None"
    move: str | None
    depth: int


def reconstruct_path(node: Node) -> str:
    """Reconstruye la solución (secuencia de movimientos) subiendo por los padres."""
    moves: list[str] = []
    while node.parent is not None:
        assert node.move is not None
        moves.append(node.move)
        node = node.parent
    moves.reverse()
    return "".join(moves)


def successors(state: State, level: Level) -> Iterator[tuple[str, State]]:
    """Pares `(movimiento, estado resultante)` desde `state`, **salteando los
    deadlocks**.

    Único punto donde los cinco algoritmos generan hijos: la poda de estados
    irrecuperables (`deadlock.is_deadlock`) se hace acá y no en cada agente.
    Como la detección no tiene falsos positivos, podar no cambia qué niveles
    son resolubles ni la optimalidad de BFS/IDDFS/A*.
    """
    for move in legal_moves(state, level):
        child = apply_move(state, level, move)
        if is_deadlock(child, level):
            continue
        yield move, child
