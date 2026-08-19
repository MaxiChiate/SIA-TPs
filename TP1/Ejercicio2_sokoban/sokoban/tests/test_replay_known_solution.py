"""Golden test: nivel de referencia (level_01_ufo) + su solución de 86 movimientos.

Sirve para detectar regresiones en parser/notation/engine de punta a punta:
si alguien rompe cualquiera de los tres, este test frena la solución conocida.
"""

from __future__ import annotations

from pathlib import Path

from ..agent import HardcodedAgent
from ..engine import is_goal, replay
from ..parser import parse_level_file

LEVELS_DIR = Path(__file__).resolve().parent.parent / "levels"


def _load_solution() -> str:
    return (LEVELS_DIR / "level_01_ufo.solution.txt").read_text().strip()


def test_replay_solucion_conocida_llega_a_la_meta():
    level = parse_level_file(str(LEVELS_DIR / "level_01_ufo.txt"))
    solution = _load_solution()

    trace = replay(level, solution)  # no debe tirar MoveError

    assert is_goal(trace[-1], level)
    assert len(solution) == 86


def test_hardcoded_agent_devuelve_la_misma_solucion():
    level = parse_level_file(str(LEVELS_DIR / "level_01_ufo.txt"))
    result = HardcodedAgent().solve(level)

    assert result.success
    assert result.solution == _load_solution()
    assert result.cost == 86

    trace = replay(level, result.solution)
    assert is_goal(trace[-1], level)
