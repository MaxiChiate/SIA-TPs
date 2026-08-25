"""Chequeos unitarios del motor: parser, apply_move, legal_moves, is_goal."""

from __future__ import annotations

import pytest

from ..engine import MoveError, apply_move, initial_state, is_goal, legal_moves
from ..parser import LevelParseError, level_to_lines, parse_level

# Nivel mínimo para probar cada regla en aislamiento:
#
#   #####
#   #@$.#
#   #####
#
# jugador en (1,1), caja en (2,1), goal en (3,1). Empujar a la derecha (R)
# manda la caja al goal.
MINI_LEVEL = "#####\n#@$.#\n#####"


def _mini():
    return parse_level(MINI_LEVEL, name="mini")


def test_parse_level_ragged_lines_se_rellenan():
    # Renglones de distinto largo: el más corto se rellena con espacios.
    text = "###\n#######\n#@$.#\n#####"
    level = parse_level(text, name="ragged")
    assert level.width == 7
    assert level.height == 4


def test_level_to_lines_es_inverso_de_parse_level():
    level = _mini()
    assert level_to_lines(level) == ["#####", "#@$.#", "#####"]


def test_parse_level_falta_jugador():
    with pytest.raises(LevelParseError):
        parse_level("#####\n#.$.#\n#####")


def test_parse_level_cajas_y_goals_desparejos():
    with pytest.raises(LevelParseError):
        parse_level("#####\n#@$$#\n#####")


def test_parse_level_soporta_boxes_on_goal_y_player_on_goal():
    # '+' = jugador sobre goal, '*' = caja sobre goal, '$' balancea el conteo.
    level = parse_level("#######\n#+*$  #\n#######")
    assert level.initial_player == (1, 1)
    assert (1, 1) in level.goals
    assert (2, 1) in level.initial_boxes
    assert (2, 1) in level.goals


def test_initial_state_coincide_con_el_level():
    level = _mini()
    state = initial_state(level)
    assert state.player == level.initial_player
    assert state.boxes == level.initial_boxes


def test_apply_move_paso_simple_con_caja_adelante_falla():
    level = _mini()
    state = initial_state(level)
    # El jugador está pegado a la caja en (2,1): "r" (minúscula, paso simple)
    # debe fallar porque hay una caja adelante -- ese char debería ser "R".
    with pytest.raises(MoveError):
        apply_move(state, level, "r")


def test_apply_move_empuje_mueve_jugador_y_caja():
    level = _mini()
    state = initial_state(level)
    empujado = apply_move(state, level, "R")
    assert empujado.player == (2, 1)
    assert (3, 1) in empujado.boxes
    assert (2, 1) not in empujado.boxes


def test_apply_move_paso_simple_a_piso_libre():
    level = _mini()
    # Nivel con más lugar para caminar: jugador se aleja de la caja primero.
    level2 = parse_level("######\n#@ $.#\n######", name="paso_libre")
    state = initial_state(level2)
    nuevo = apply_move(state, level2, "r")
    assert nuevo.player == (2, 1)
    assert nuevo.boxes == state.boxes  # la caja no se movió


def test_apply_move_contra_pared_falla():
    level = _mini()
    state = initial_state(level)
    with pytest.raises(MoveError):
        apply_move(state, level, "u")


def test_apply_move_empuje_sin_caja_adelante_falla():
    level = _mini()
    state = initial_state(level)
    with pytest.raises(MoveError):
        apply_move(state, level, "U")


def test_apply_move_empuje_contra_pared_falla():
    level = _mini()
    state = initial_state(level)
    state = apply_move(state, level, "R")  # caja ahora en el goal (3,1), contra la pared en (4,1)
    with pytest.raises(MoveError):
        apply_move(state, level, "R")


def test_apply_move_empuje_contra_otra_caja_falla():
    level = parse_level("#######\n#@$$..#\n#######", name="dos_cajas")
    state = initial_state(level)
    with pytest.raises(MoveError):
        apply_move(state, level, "R")


def test_legal_moves_en_el_arranque():
    level = _mini()
    state = initial_state(level)
    # Jugador rodeado de pared arriba/abajo, caja a la derecha (empuje posible),
    # pared a la izquierda: único movimiento legal es "R".
    assert legal_moves(state, level) == ["R"]


def test_is_goal():
    level = _mini()
    state = initial_state(level)
    assert not is_goal(state, level)
    empujado = apply_move(state, level, "R")
    assert is_goal(empujado, level)
