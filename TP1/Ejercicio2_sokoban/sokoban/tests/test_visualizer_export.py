"""render_visualizer: inyecta el `run-data` JSON en una copia del template HTML."""

from __future__ import annotations

import json

from ..visualizer_export import _RUN_DATA_CLOSE, _RUN_DATA_OPEN, render_visualizer

_RUN_DATA = {
    "level_name": "mini",
    "level_lines": ["#####", "#@$.#", "#####"],
    "solution": "R",
    "result": {
        "success": True,
        "cost": 1,
        "nodes_expanded": 2,
        "frontier_nodes": 3,
        "elapsed_seconds": 0.001,
    },
    "algorithm": "astar",
    "heuristic": "manhattan_sum",
    "config_path": "config.json",
    "generated_at": "2026-01-01T00:00:00+00:00",
    "board": {"width": 5, "height": 3, "boxes": 1, "goals": 1},
    "moves": {"pushes": 1, "steps": 0},
}


def test_render_visualizer_incrusta_el_run_data(tmp_path):
    output = tmp_path / "out.html"

    render_visualizer(_RUN_DATA, output)

    html = output.read_text()
    start = html.index(_RUN_DATA_OPEN) + len(_RUN_DATA_OPEN)
    end = html.index(_RUN_DATA_CLOSE, start)
    embedded = json.loads(html[start:end])

    assert embedded == _RUN_DATA
    assert "<title>" in html  # sigue siendo el HTML del visualizador, no solo el JSON
