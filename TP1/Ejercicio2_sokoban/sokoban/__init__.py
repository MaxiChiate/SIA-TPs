"""Motor de Sokoban: parser, engine y agente-enchufe para las búsquedas del equipo.

Fase 0 (este paquete): tablero de juego completo sin ningún algoritmo de
búsqueda. `HardcodedAgent` es un cable pelado que devuelve la solución conocida
del nivel de referencia, solo para probar parseo -> replay -> animación de
punta a punta.
"""

from .agent import Agent, HardcodedAgent, SearchResult
from .engine import MoveError, apply_move, initial_state, is_goal, legal_moves, replay
from .parser import parse_level
from .state import Level, State

__all__ = [
    "Agent",
    "HardcodedAgent",
    "SearchResult",
    "MoveError",
    "apply_move",
    "initial_state",
    "is_goal",
    "legal_moves",
    "replay",
    "parse_level",
    "Level",
    "State",
]
