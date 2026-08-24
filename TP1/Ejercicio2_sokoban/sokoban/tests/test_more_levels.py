"""Niveles agregados en Fase 3 (más niveles / más cajas), sacados de la
colección "aenigma" de game-sokoban.com (cid=4, lid 200-249): mismo formato
que level_01_ufo.

- level_02_soko11 y level_03_soko12 traen la solución demo del sitio: se
  verifican igual que el golden test de level_01_ufo (replay -> is_goal).
- El resto (level_04..level_08) solo se valida que parseen: son estructuralmente
  válidos (cajas == goals, un jugador) y provienen de la misma colección
  ya resuelta por jugadores reales, pero no traen solución demo pública.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ..engine import is_goal, replay
from ..parser import parse_level_file

LEVELS_DIR = Path(__file__).resolve().parent.parent / "levels"

_LEVELS_CON_SOLUCION = ["level_02_soko11", "level_03_soko12"]
_LEVELS_SIN_SOLUCION = [
    "level_04_soko03",
    "level_05_soko15",
    "level_06_soko13",
    "level_07_soko10",
    "level_08_soko04",
]


@pytest.mark.parametrize("stem", _LEVELS_CON_SOLUCION)
def test_replay_solucion_demo_llega_a_la_meta(stem):
    level = parse_level_file(str(LEVELS_DIR / f"{stem}.txt"))
    solution = (LEVELS_DIR / f"{stem}.solution.txt").read_text().strip()

    trace = replay(level, solution)  # no debe tirar MoveError

    assert is_goal(trace[-1], level)


@pytest.mark.parametrize("stem", _LEVELS_SIN_SOLUCION)
def test_nivel_parsea_con_cajas_y_goals_balanceados(stem):
    level = parse_level_file(str(LEVELS_DIR / f"{stem}.txt"))

    assert len(level.initial_boxes) == len(level.goals)
    assert level.initial_boxes  # al menos una caja
