"""Render a list of ``Triangle`` onto an RGB canvas.

Triangles are translucent (RGBA) and drawn in genotype order (painter's
algorithm), so later triangles blend over earlier ones. Each triangle is drawn
on its own transparent layer and alpha-composited onto the canvas, since
``ImageDraw.polygon`` on an RGBA image overwrites pixels rather than blending them.
"""

from __future__ import annotations

from PIL import Image, ImageDraw

from .genotype import Triangle


def render_triangles(
    triangles: list[Triangle],
    width: int,
    height: int,
    background_rgb: tuple[int, int, int],
) -> Image.Image:
    canvas = Image.new("RGBA", (width, height), (*background_rgb, 255))
    for triangle in triangles:
        layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        ImageDraw.Draw(layer).polygon(triangle.vertices, fill=triangle.color)
        canvas = Image.alpha_composite(canvas, layer)
    return canvas.convert("RGB")
