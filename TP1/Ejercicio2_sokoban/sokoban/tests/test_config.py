"""Config-driven agent selection: `load_config` + `build_agent`.

Cubre el enchufe que usa `run.py`: `config.json` -> `RunConfig` -> `Agent`,
sin tener que tocar código para cambiar de algoritmo/heurística.
"""

from __future__ import annotations

import json

import pytest

from ..config import ConfigError, load_config
from ..search import build_agent
from ..search.astar import AStarAgent
from ..search.heuristics import manhattan_sum


def _write_config(tmp_path, data: dict) -> str:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data))
    return str(path)


def test_load_config_nivel_por_stem(tmp_path):
    path = _write_config(
        tmp_path, {"level": "level_01_ufo", "algorithm": "astar", "heuristic": "manhattan_sum"}
    )

    config = load_config(path)

    assert config.level == "level_01_ufo"
    assert config.algorithm == "astar"
    assert config.heuristic == "manhattan_sum"
    assert config.level_path().name == "level_01_ufo.txt"


def test_load_config_heuristic_es_opcional(tmp_path):
    path = _write_config(tmp_path, {"level": "level_01_ufo", "algorithm": "astar"})

    config = load_config(path)

    assert config.heuristic is None


def test_load_config_archivo_inexistente():
    with pytest.raises(ConfigError):
        load_config("no_existe.json")


def test_load_config_falta_clave_requerida(tmp_path):
    path = _write_config(tmp_path, {"level": "level_01_ufo"})

    with pytest.raises(ConfigError):
        load_config(path)


def test_build_agent_astar_usa_manhattan_sum_por_default():
    agent = build_agent("astar", None)

    assert isinstance(agent, AStarAgent)
    assert agent._heuristic is manhattan_sum


def test_build_agent_algoritmo_desconocido():
    with pytest.raises(ValueError):
        build_agent("no_existe", None)


def test_build_agent_heuristica_desconocida():
    with pytest.raises(ValueError):
        build_agent("astar", "no_existe")


def test_build_agent_algoritmo_no_implementado_da_mensaje_claro():
    with pytest.raises(NotImplementedError):
        build_agent("bfs", None)
