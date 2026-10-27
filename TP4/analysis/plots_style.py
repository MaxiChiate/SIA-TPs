"""Shared matplotlib palette and style, so every TP4 figure reads as one system.

Same categorical palette as TP3 (`../TP3/analysis/plots_style.py`), so a series keeps its colour across
both deliverables. Hues are assigned in slot order and never cycled: past 8 series the right move is
splitting the figure, not inventing a ninth colour. Some slots are under 3:1 contrast on the light
surface, so figures also carry non-colour identity (titles, labels, legends).

matplotlib is the figure path (D-06). Text is written as glyph paths in SVG, so a figure embedded in
the report or the slides looks the same even where its fonts are not installed.

Two variants of one figure (D-08). The same plot function draws both; only the style changes:
  - "report" (default): the sizes, type scale, long caption and figure title the informe has always used.
  - "slide": the 16:9-slide size (SLIDE_FIGSIZE), a larger type scale, no caption and no figure-level title
    (the slide carries its own h2 title and speaker notes), saved under `<figure dir>/slide/<stem>`.
A plot function asks the module for what depends on the variant (`figsize`, `rect`, `fontsize`, `caption`,
`suptitle`) and a driver draws both with `for _ in iter_variants(): plot(...)`. The report values equal
matplotlib's defaults, so report output stays byte-identical to what it was before the variants existed.
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

VARIANTS = ("report", "slide")
# 12.8 in wide and 4.85 in high = 1664 x 630 px, the `figure_area` of 06-ARTIFACT-FORMAT.md (the box below a
# slide title on the 1920 x 1080 canvas). A figure that shares the slide passes its own `slide=` size.
SLIDE_FIGSIZE = (12.8, 4.85)
SLIDE_FONT_SIZE = 15.0  # pt; the report default is matplotlib's 10.0
_REPORT_FONT_SIZE = 10.0
# 250 dpi gives a full-width slide figure of 3200 px, about 2x its 1664 px box (06-ARTIFACT-FORMAT.md section 3).
SLIDE_PNG_DPI = 250

_current_variant = "report"


class PaletteError(Exception):
    """More series than the palette has slots."""


def palette_for(variants: Sequence[str]) -> dict[str, str]:
    """Map each variant to its slot colour, stable across every figure of a series."""
    if len(variants) > len(_SERIES):
        raise PaletteError(
            f"{len(variants)} variants but only {len(_SERIES)} colour slots; split the figure"
        )
    return {variant: _SERIES[index] for index, variant in enumerate(variants)}


def use_variant(name: str) -> None:
    """Select the variant the next figures are drawn in; ValueError for a name outside VARIANTS."""
    global _current_variant
    if name not in VARIANTS:
        raise ValueError(f"unknown figure variant {name!r}; expected one of {VARIANTS}")
    _current_variant = name


def variant() -> str:
    """The current variant: "report" unless a driver switched to "slide"."""
    return _current_variant


def iter_variants():
    """Yield "report" then "slide", each one selected while the loop body runs; "report" is restored after
    the loop, also when the body raises, so a figure drawn afterwards is a report figure."""
    try:
        for name in VARIANTS:
            use_variant(name)
            yield name
    finally:
        use_variant("report")


def figsize(report: tuple[float, float], slide: tuple[float, float] | None = None) -> tuple[float, float]:
    """The figure size in inches: `report` in the report variant, `slide` (or SLIDE_FIGSIZE) in the slide one."""
    if _current_variant == "slide":
        return tuple(slide) if slide is not None else SLIDE_FIGSIZE
    return tuple(report)


def rect(report: tuple[float, float, float, float],
         slide: tuple[float, float, float, float] = (0, 0, 1, 1)) -> tuple[float, float, float, float]:
    """The `tight_layout` rect: the report one reserves room for the caption and the title, the slide one
    fills the figure."""
    return tuple(slide) if _current_variant == "slide" else tuple(report)


def fontsize(report: float) -> float:
    """A hard-coded text size in points: unchanged in the report, scaled by SLIDE_FONT_SIZE / 10 in a slide."""
    if _current_variant == "slide":
        return report * SLIDE_FONT_SIZE / _REPORT_FONT_SIZE
    return report


def caption(fig, text: str, width: int = 125, y: float = 0.01, fontsize: float = 8) -> None:
    """The long figure caption (report only): a wrapped grey text at the bottom left of the figure."""
    if _current_variant == "slide":
        return
    import textwrap

    fig.text(0.01, y, textwrap.fill(text, width), ha="left", va="bottom", fontsize=fontsize,
             color=TEXT_SECONDARY)


def suptitle(fig, text: str, **kwargs) -> None:
    """The figure-level title (report only): the slide has its own title."""
    if _current_variant == "slide":
        return
    fig.suptitle(text, **kwargs)


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
            "font.size": SLIDE_FONT_SIZE if _current_variant == "slide" else _REPORT_FONT_SIZE,
            "svg.fonttype": "path",
            "svg.hashsalt": "tp4",
        }
    )
    return plt


def save_figure(fig, path_without_suffix: str | Path) -> tuple[Path, Path]:
    """Write `{path}.svg` and `{path}.png` (dpi 150), then close the figure.

    In the slide variant the files go to `<folder>/slide/<name>.svg` and `.png` (dpi SLIDE_PNG_DPI).
    The SVG carries no date (metadata Date None) and a fixed hash salt, so a rerun on the same data
    writes the same file.
    """
    import matplotlib.pyplot as plt

    base = Path(path_without_suffix)
    slide = _current_variant == "slide"
    if slide:
        base = base.parent / "slide" / base.name
    base.parent.mkdir(parents=True, exist_ok=True)
    svg_path = base.with_suffix(".svg")
    png_path = base.with_suffix(".png")
    fig.savefig(svg_path, format="svg", metadata={"Date": None})
    fig.savefig(png_path, format="png", dpi=SLIDE_PNG_DPI if slide else PNG_DPI)
    plt.close(fig)
    return svg_path, png_path
