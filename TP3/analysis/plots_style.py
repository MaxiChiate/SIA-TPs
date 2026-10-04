"""Shared palette and layout, so every chart of a series reads as one system.

Same categorical palette as the run and series reports (`scripts/run_report.py`, `sweep_report.py`), so a
variant keeps its color between them. Hues are assigned in slot order and never cycled: past 8 variants the
right move is splitting the series, not inventing a ninth color.

Some of these slots are under 3:1 contrast on the light surface, so every chart also carries non-color
identity: a legend, direct labels at the end of each line, and value labels next to the dots.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from pathlib import Path

import plotly.graph_objects as go

_SERIES = (
    "#2a78d6",  # blue
    "#eb6834",  # orange
    "#1baf7a",  # aqua
    "#eda100",  # yellow
    "#e87ba4",  # magenta
    "#008300",  # green
    "#4a3aa7",  # violet
    "#e34948",  # red
)

SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e6e5e1"

FONT_FAMILY = "system-ui, -apple-system, Segoe UI, Roboto, sans-serif"

# How many points of each curve carry an error bar: a sample of the spread along the run without turning
# a 50-epoch line into a fence
ERROR_MARKS = 10


class PaletteError(Exception):
    """More series than the palette has slots."""


def palette_for(variants: Sequence[str]) -> dict[str, str]:
    """Map each variant to its slot color, stable across every chart of a series."""
    if len(variants) > len(_SERIES):
        raise PaletteError(f"{len(variants)} variants but only {len(_SERIES)} color slots; split the series")
    return {variant: _SERIES[index] for index, variant in enumerate(variants)}


def translucent(color: str, alpha: float) -> str:
    """`"#2a78d6"` -> `"rgba(42,120,214,0.13)"`: a faded fill that still reads as its series."""
    digits = color.lstrip("#")
    red, green, blue = (int(digits[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({red},{green},{blue},{alpha})"


def is_log_scale(values: Sequence[float]) -> bool:
    """Log once the values are positive and span more than two orders of magnitude, like run_report's curve."""
    positive = [value for value in values if value > 0]
    return bool(positive) and len(positive) == len(values) and max(positive) / min(positive) > 100


def as_axis_value(value: float, log: bool) -> float:
    """Plotly places annotations on a log axis by the exponent, not by the value."""
    return math.log10(value) if log else value


def add_error_bars(figure: go.Figure, marks: tuple[list[float], list[float], list[float], list[float]],
                   color: str) -> None:
    """Mark a curve's spread across seeds at the points `marks` samples: `(x, y, up, down)`.

    Hidden from the legend and the hover: the bars annotate their own line, and an extra hover entry per
    variant would drown the unified tooltip. Added after the lines so the caps sit on top.
    """
    x, y, up, down = marks
    figure.add_trace(go.Scatter(
        x=x, y=y, mode="markers", marker={"color": color, "size": 5},
        error_y={"type": "data", "symmetric": False, "array": up, "arrayminus": down,
                 "color": color, "thickness": 1.2, "width": 4},
        showlegend=False, hoverinfo="skip",
    ))


def base_layout(title: str, subtitles: Sequence[str], x_title: str, y_title: str) -> dict:
    """Recessive axes and grid, generous margins, legend below the plot.

    Subtitles ride inside the title block: a footer would have to be placed in paper coordinates, and any
    margin change would collide it with the axis title or the legend. The top margin grows with them.
    """
    lines = [line for line in subtitles if line]
    heading = title
    for line in lines:
        heading += f"<br><span style='font-size:11px;color:{TEXT_SECONDARY}'>{line}</span>"
    axis = {
        "showgrid": True, "gridcolor": GRID, "gridwidth": 1, "zeroline": False, "linecolor": GRID,
        "ticks": "outside", "tickcolor": GRID, "tickfont": {"color": TEXT_SECONDARY, "size": 12},
        "title": {"font": {"color": TEXT_SECONDARY, "size": 13}},
    }
    return {
        "title": {
            "text": heading, "font": {"color": TEXT_PRIMARY, "size": 18},
            "x": 0, "xref": "container", "xanchor": "left", "y": 1, "yanchor": "top", "yref": "container",
            "pad": {"t": 20, "l": 20},
        },
        "paper_bgcolor": SURFACE,
        "plot_bgcolor": SURFACE,
        "font": {"family": FONT_FAMILY, "color": TEXT_PRIMARY, "size": 13},
        "xaxis": {**axis, "title": {**axis["title"], "text": x_title}},
        "yaxis": {**axis, "title": {**axis["title"], "text": y_title}},
        "legend": {"orientation": "h", "yanchor": "top", "y": -0.18, "xanchor": "left", "x": 0,
                   "font": {"color": TEXT_SECONDARY, "size": 12}},
        # Right margin leaves room for the end-of-line labels; bottom for the axis title and the legend
        "margin": {"l": 80, "r": 150, "t": 62 + 22 * len(lines), "b": 130},
        "hovermode": "x unified",
    }


def end_label(text: str, x: float, y: float, color: str) -> dict:
    """A direct label past the end of a line, so identity is never color alone."""
    return {"x": x, "y": y, "text": f" {text}", "xanchor": "left", "yanchor": "middle", "showarrow": False,
            "font": {"color": color, "size": 11}}


def write_html(figure: go.Figure, path: Path) -> Path:
    """Write a standalone HTML chart.

    plotly.js goes once next to the charts (`plotly.min.js`) instead of inside every file (~3 MB each):
    offline like an embedded copy, but a series of 10 charts weighs 3 MB, not 30.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.write_html(str(path), include_plotlyjs="directory", full_html=True)
    return path
