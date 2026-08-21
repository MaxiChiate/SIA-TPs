#!/usr/bin/env python3
"""CLI: python run.py [config.json] -- corre el agente que indique el config."""

from __future__ import annotations

import sys
from pathlib import Path

from sokoban import ConfigError, build_agent, is_goal, load_config, replay
from sokoban.parser import LevelParseError, parse_level

SCRIPT_DIR = Path(__file__).resolve().parent


def _resolve_config_path(raw: str) -> Path:
    # fallback para poder correr `python TP1/Ejercicio2_sokoban/run.py` desde la raíz del repo
    given = Path(raw)
    if given.is_file() or given.is_absolute():
        return given
    from_script_dir = SCRIPT_DIR / raw
    if from_script_dir.is_file():
        return from_script_dir
    return given


def main(argv: list[str]) -> int:
    config_path = _resolve_config_path(argv[1] if len(argv) > 1 else "config.json")

    try:
        config = load_config(config_path)
    except ConfigError as exc:
        print(f"error de configuración: {exc}", file=sys.stderr)
        return 1

    level_path = config.level_path()
    try:
        level = parse_level(level_path.read_text(), name=level_path.stem)
    except FileNotFoundError:
        print(f"error: no se encontró el nivel {level_path}", file=sys.stderr)
        return 1
    except LevelParseError as exc:
        print(f"error al parsear {level_path}: {exc}", file=sys.stderr)
        return 1

    try:
        agent = build_agent(config.algorithm, config.heuristic)
    except (ValueError, NotImplementedError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    result = agent.solve(level)

    print(f"nivel:            {level.name}")
    print(f"algoritmo:        {config.algorithm}")
    print(f"heurística:       {config.heuristic or '(n/a)'}")
    print(f"éxito:            {result.success}")
    print(f"costo (pasos):    {result.cost}")
    print(f"nodos expandidos: {result.nodes_expanded}")
    print(f"frontera máxima:  {result.frontier_nodes}")
    print(f"tiempo (s):       {result.elapsed_seconds:.4f}")

    if result.success:
        trace = replay(level, result.solution)
        assert is_goal(trace[-1], level)
        print(f"solución:         {result.solution}")

    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
