"""Genera una copia standalone de `visualizer/sokoban_visualizer.html` con los
datos de una corrida (nivel, solución, `SearchResult`, algoritmo/heurística)."""

from __future__ import annotations

import json
from pathlib import Path

TEMPLATE_PATH = Path(__file__).resolve().parent / "visualizer" / "sokoban_visualizer.html"

_RUN_DATA_OPEN = '<script type="application/json" id="run-data">'
_RUN_DATA_CLOSE = "</script>"


def render_visualizer(run_data: dict, output_path: Path) -> None:
    template = TEMPLATE_PATH.read_text()
    start = template.index(_RUN_DATA_OPEN) + len(_RUN_DATA_OPEN)
    end = template.index(_RUN_DATA_CLOSE, start)
    html = f"{template[:start]}\n{json.dumps(run_data, indent=2)}\n{template[end:]}"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
