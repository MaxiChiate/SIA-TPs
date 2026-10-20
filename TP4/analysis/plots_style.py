"""Shared matplotlib palette and style, so every TP4 figure reads as one system.

Same categorical palette as TP3 (`../TP3/analysis/plots_style.py`), so a series keeps its colour across
both deliverables. Hues are assigned in slot order and never cycled: past 8 series the right move is
splitting the figure, not inventing a ninth colour. Some slots are under 3:1 contrast on the light
surface, so figures also carry non-colour identity (titles, labels, legends).

matplotlib is the figure path (D-06). Text is written as glyph paths in SVG, so a figure embedded in
the report or the slides looks the same even where its fonts are not installed.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

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

# Diverging colormap for signed quantities (correlations, loadings): zero is white-ish, the extremes
# are the saturated ends, so a +1 and a -1 cell are never confused.
DIVERGING = "RdBu_r"

FONT_FAMILY = ["Helvetica Neue", "Arial", "DejaVu Sans", "sans-serif"]
PNG_DPI = 150


class PaletteError(Exception):
    """More series than the palette has slots."""


def palette_for(variants: Sequence[str]) -> dict[str, str]:
    """Map each variant to its slot colour, stable across every figure of a series."""
    if len(variants) > len(_SERIES):
        raise PaletteError(
            f"{len(variants)} variants but only {len(_SERIES)} colour slots; split the figure"
        )
    return {variant: _SERIES[index] for index, variant in enumerate(variants)}


def apply_style():
    """Select the Agg backend, set the rcParams and return the pyplot module.

    The backend is chosen before pyplot is imported, so a headless run (make, CI) never needs a display.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "text.color": TEXT_PRIMARY,
            "axes.labelcolor": TEXT_SECONDARY,
            "axes.edgecolor": GRID,
            "axes.titlecolor": TEXT_PRIMARY,
            "xtick.color": TEXT_SECONDARY,
            "ytick.color": TEXT_SECONDARY,
            "grid.color": GRID,
            "axes.grid": False,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "font.family": "sans-serif",
            "font.sans-serif": FONT_FAMILY,
            "svg.fonttype": "path",
            "svg.hashsalt": "tp4",
        }
    )
    return plt


def save_figure(fig, path_without_suffix: str | Path) -> tuple[Path, Path]:
    """Write `{path}.svg` and `{path}.png` (dpi 150), then close the figure.

    The SVG carries no date (metadata Date None) and a fixed hash salt, so a rerun on the same data
    writes the same file.
    """
    import matplotlib.pyplot as plt

    base = Path(path_without_suffix)
    base.parent.mkdir(parents=True, exist_ok=True)
    svg_path = base.with_suffix(".svg")
    png_path = base.with_suffix(".png")
    fig.savefig(svg_path, format="svg", metadata={"Date": None})
    fig.savefig(png_path, format="png", dpi=PNG_DPI)
    plt.close(fig)
    return svg_path, png_path
