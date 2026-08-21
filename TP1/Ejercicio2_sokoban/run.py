#!/usr/bin/env python3
"""CLI: corre el agente que indique `config.json` sobre el nivel que indique.

Uso:
    python run.py                 # usa ./config.json
    python run.py otra_config.json

`config.json` decide todo (nivel, algoritmo, heurística) -- ver
`sokoban/config.py` y el README para el formato.
"""

from __future__ import annotations

import sys

from sokoban import ConfigError, build_agent, is_goal, load_config, replay
from sokoban.parser import LevelParseError, parse_level


def main(argv: list[str]) -> int:
    config_path = argv[1] if len(argv) > 1 else "config.json"

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
        # Confirma que la solución encontrada es jugable de punta a punta,
        # igual que hace el golden test con HardcodedAgent.
        trace = replay(level, result.solution)
        assert is_goal(trace[-1], level)
        print(f"solución:         {result.solution}")

    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
