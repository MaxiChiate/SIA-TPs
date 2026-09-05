"""Export a solved individual: a full-resolution rendered image, a JSON
enumeration of its triangles (position + color), and an animated GIF of a run's
progress - the "output" the assignment asks for, independent of whatever small
resolution fitness was evaluated at.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from PIL import Image

from ga.core.individual import Individual

from .colorspace import DEFAULT as DEFAULT_COLOR_SPACE
from .colorspace import ColorSpace
from .genotype import triangles_from_alleles
from .renderer import render_triangles


def native_resolution(image_path: str | Path) -> tuple[int, int]:
    """The source image's own pixel dimensions, for a full-resolution export."""
    with Image.open(image_path) as img:
        return img.size


def triangles_as_json(
    individual: Individual,
    triangle_count: int,
    width: int,
    height: int,
    color_space: ColorSpace = DEFAULT_COLOR_SPACE,
) -> list[dict]:
    """Enumerate the individual's triangles (pixel vertices + RGBA color) at
    ``width``x``height``.

    Colors are always dumped as RGBA, whatever ``color_space`` the run searched
    in: the export describes the picture, not the genotype's coordinates.
    """
    triangles = triangles_from_alleles(
        individual.alleles, triangle_count, width, height, color_space
    )
    return [
        {"vertices": [list(vertex) for vertex in triangle.vertices], "color": list(triangle.color)}
        for triangle in triangles
    ]


def save_image(
    renderer,
    individual: Individual,
    width: int,
    height: int,
    path: str | Path,
) -> None:
    """Draw ``individual`` at ``width``x``height`` with the run's own renderer.

    Deliberately the renderer and not ``render_triangles``: the exported picture
    has to be drawn by whichever rasterizer scored it, or the image being looked
    at is not the image the fitness refers to.
    """
    renderer.render_rgb(individual.alleles, width, height).save(path)


def save_triangles_json(
    individual: Individual,
    triangle_count: int,
    width: int,
    height: int,
    path: str | Path,
    color_space: ColorSpace = DEFAULT_COLOR_SPACE,
) -> None:
    data = triangles_as_json(individual, triangle_count, width, height, color_space)
    Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")


def save_gif(
    frame_paths: Sequence[str | Path],
    path: str | Path,
    frame_ms: int = 120,
    hold_ms: int = 3000,
) -> None:
    """Assemble already-rendered PNG frames into a looping GIF.

    The last frame is held for ``hold_ms`` instead of ``frame_ms`` (GIF allows a
    per-frame delay, so the result is held without duplicating the frame), which
    is what makes the finished image readable before the loop restarts.

    Frames are read back from disk rather than kept in memory during the run:
    they are full export-resolution renders, and a long run with a small
    snapshot interval would otherwise hold hundreds of them at once.
    """
    frames = []
    for frame_path in frame_paths:
        with Image.open(frame_path) as frame:
            frames.append(frame.convert("RGB"))
    if not frames:
        raise ValueError("save_gif needs at least one frame")

    durations = [frame_ms] * (len(frames) - 1) + [hold_ms]
    first, *rest = frames
    first.save(
        path,
        save_all=True,
        append_images=rest,
        duration=durations,
        loop=0,
        optimize=True,
    )
