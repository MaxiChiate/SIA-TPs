"""Utilidades compartidas por los algoritmos de `sokoban/search/`.

`Node` es un nodo de árbol de búsqueda liviano (estado + puntero al padre +
movimiento que lo generó), para no tener que arrastrar el string de la
solución completa en cada nodo de la frontera.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..state import State


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
