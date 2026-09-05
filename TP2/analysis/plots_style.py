"""Shared palette and layout, so every chart of a sweep reads as one system.

The categorical palette is a fixed, validated order: worst adjacent CVD Delta E 9.1
and worst adjacent normal-vision Delta E 19.6 on this surface (OKLab x100; targets
are 8 and 15). Hues are assigned in slot order and never cycled - past 8 variants
the right move is faceting, not a ninth invented colour.

Three of these slots fall below 3:1 contrast against the light surface, so every
chart here also carries non-colour identity: a legend, direct labels at the end of
each line, and value labels on bars.
"""

from __future__ import annotations

from pathlib import Path

# Categorical slots, in fixed order. Colour follows the variant, not its rank.
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


class PaletteError(Exception):
    """More series than the validated palette has slots."""


def palette_for(variants: tuple[str, ...] | list[str]) -> dict[str, str]:
    """Map each variant to its slot colour, stable across every chart of a sweep."""
    if len(variants) > len(_SERIES):
        raise PaletteError(
            f"{len(variants)} variants but only {len(_SERIES)} validated colour slots; "
            "split the sweep or facet instead of inventing a colour"
        )
    return {variant: _SERIES[index] for index, variant in enumerate(variants)}


def base_layout(title: str, subtitle: str, x_title: str, y_title: str) -> dict:
    """Recessive axes and grid, generous margins, legend under the title.

    The subtitle rides inside the title block rather than as a footer annotation:
    a footer below the axis has to be positioned in paper coordinates, and any
    margin change silently collides it with the axis title.
    """
    heading = title
    if subtitle:
        heading += (
            f"<br><span style='font-size:12px;color:{TEXT_SECONDARY}'>{subtitle}</span>"
        )
    axis = {
        "showgrid": True,
        "gridcolor": GRID,
        "gridwidth": 1,
        "zeroline": False,
        "linecolor": GRID,
        "ticks": "outside",
        "tickcolor": GRID,
        "tickfont": {"color": TEXT_SECONDARY, "size": 12},
        "title": {"font": {"color": TEXT_SECONDARY, "size": 13}},
    }
    return {
        "title": {"text": heading, "font": {"color": TEXT_PRIMARY, "size": 18}, "x": 0},
        "paper_bgcolor": SURFACE,
        "plot_bgcolor": SURFACE,
        "font": {"family": FONT_FAMILY, "color": TEXT_PRIMARY, "size": 13},
        "xaxis": {**axis, "title": {**axis["title"], "text": x_title}},
        "yaxis": {**axis, "title": {**axis["title"], "text": y_title}},
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
            "font": {"color": TEXT_SECONDARY, "size": 12},
        },
        # Right margin leaves room for the end-of-line direct labels; the top one
        # for the title, its subtitle and the legend stacked above the plot.
        "margin": {"l": 80, "r": 150, "t": 120, "b": 60},
        "hovermode": "x unified",
    }


def end_label(text: str, x: float, y: float, color: str) -> dict:
    """A direct label past the end of a line, so identity is never colour-alone."""
    return {
        "x": x,
        "y": y,
        "text": f" {text}",
        "xanchor": "left",
        "yanchor": "middle",
        "showarrow": False,
        "font": {"color": color, "size": 11},
    }


def write_html(figure, path: Path) -> Path:
    """Write a standalone HTML chart.

    plotly.js is embedded rather than loaded from a CDN (~3 MB per file): these
    are meant to be opened during a presentation, where assuming internet is a
    bad bet. The output directory is gitignored anyway.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.write_html(str(path), include_plotlyjs=True, full_html=True)
    return path
