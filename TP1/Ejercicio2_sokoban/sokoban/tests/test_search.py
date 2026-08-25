"""Sanity tests para los algoritmos de `sokoban/search/` sobre el nivel dorado.

No comparan contra los 86 movimientos hardcodeados (cada algoritmo puede
encontrar una solución distinta, o de otra longitud); solo verifican que la
solución que devuelven es válida (`replay` no tira `MoveError` y llega a la
meta), y que BFS/IDDFS -- que garantizan optimalidad para costo uniforme --
coinciden en el largo de la solución óptima.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ..engine import is_goal, replay
from ..parser import parse_level_file
from ..search.bfs import BFSAgent
from ..search.dfs import DFSAgent
from ..search.greedy import GreedyAgent
from ..search.iddfs import IDDFSAgent
from ..search.registry import ALGORITHMS

LEVELS_DIR = Path(__file__).resolve().parent.parent / "levels"


@pytest.fixture
def level():
    return parse_level_file(str(LEVELS_DIR / "aenigma_01.txt"))


def _assert_valid_solution(level, result):
    assert result.success
    assert result.cost == len(result.solution)
    trace = replay(level, result.solution)  # no debe tirar MoveError
    assert is_goal(trace[-1], level)


@pytest.mark.parametrize("agent_cls", [BFSAgent, DFSAgent, GreedyAgent, IDDFSAgent])
def test_agente_encuentra_solucion_valida(level, agent_cls):
    result = agent_cls().solve(level)
    _assert_valid_solution(level, result)


def test_bfs_e_iddfs_coinciden_en_el_optimo(level):
    bfs_result = BFSAgent().solve(level)
    iddfs_result = IDDFSAgent().solve(level)

    assert bfs_result.cost == iddfs_result.cost


def test_registry_expone_los_cuatro_algoritmos_implementados(level):
    for name in ("bfs", "dfs", "greedy", "iddfs"):
        agent = ALGORITHMS[name](None)
        result = agent.solve(level)
        _assert_valid_solution(level, result)
