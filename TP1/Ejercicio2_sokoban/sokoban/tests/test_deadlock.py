"""Tests de `search/deadlock.py`: qué se poda y, sobre todo, qué NO.

Los falsos positivos son el riesgo real: marcar como deadlock un estado
recuperable haría que los algoritmos pierdan soluciones.
"""

from __future__ import annotations

import pytest

from ..engine import legal_moves
from ..search._common import successors
from ..search.deadlock import is_deadlock
from ..state import Level, State

# Sala vacía de 5x3 (interior x=1..5, y=1..3) rodeada de paredes, con los dos
# rincones de arriba como goals. Se arma a mano y no con `parse_level` porque
# varios casos usan más cajas que goals, algo que el parser (con razón) rechaza
# en un nivel real.
_ANCHO, _ALTO = 7, 5
_PAREDES = frozenset(
    (x, y)
    for x in range(_ANCHO)
    for y in range(_ALTO)
    if x in (0, _ANCHO - 1) or y in (0, _ALTO - 1)
)


@pytest.fixture
def level():
    return Level(
        width=_ANCHO,
        height=_ALTO,
        walls=_PAREDES,
        goals=frozenset({(1, 1), (5, 1)}),
        initial_player=(3, 3),
        initial_boxes=frozenset({(3, 2)}),
        name="test",
    )


def _estado(level, caja, jugador=(3, 3)):
    return State(player=jugador, boxes=frozenset({caja}))


def test_caja_en_rincon_fuera_de_goal_es_deadlock(level):
    # (5, 3): pegada a la pared derecha y a la de abajo.
    assert is_deadlock(_estado(level, (5, 3)), level)


def test_caja_en_rincon_sobre_goal_no_es_deadlock(level):
    # (5, 1) también es rincón, pero es goal: el nivel está resuelto.
    assert (5, 1) in level.goals
    assert not is_deadlock(_estado(level, (5, 1)), level)


def test_caja_libre_no_es_deadlock(level):
    assert not is_deadlock(_estado(level, (3, 2)), level)


def test_caja_contra_una_sola_pared_no_es_deadlock(level):
    # Pegada a la pared de abajo pero todavía empujable en horizontal.
    assert not is_deadlock(_estado(level, (3, 3), jugador=(2, 3)), level)


def test_bloque_2x2_de_cajas_es_deadlock(level):
    cuatro = frozenset({(2, 2), (3, 2), (2, 3), (3, 3)})
    assert is_deadlock(State(player=(4, 3), boxes=cuatro), level)


def test_dos_cajas_juntas_no_son_deadlock(level):
    dos = frozenset({(2, 2), (3, 2)})
    assert not is_deadlock(State(player=(4, 2), boxes=dos), level)


def test_successors_no_devuelve_estados_en_deadlock(level):
    # Jugador arriba de la caja: empujarla hacia abajo ("D") la mandaría al
    # rincón (5, 3), del que no vuelve. `successors` no ofrece ese movimiento,
    # aunque el motor lo considere legal.
    estado = State(player=(5, 1), boxes=frozenset({(5, 2)}))
    hijos = dict(successors(estado, level))
    assert "D" in legal_moves(estado, level)
    assert "D" not in hijos
    assert "l" in hijos  # los movimientos sanos siguen estando
