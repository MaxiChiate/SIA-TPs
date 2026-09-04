"""Export a solved individual: a full-resolution rendered image, and a JSON
enumeration of its triangles (position + color) - the "output" the assignment
asks for, independent of whatever small resolution fitness was evaluated at.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from ga.core.individual import Individual

from .genotype import triangles_from_alleles
from .renderer import render_triangles


def native_resolution(image_path: str | Path) -> tuple[int, int]:
    """The source image's own pixel dimensions, for a full-resolution export."""
    with Image.open(image_path) as img:
        return img.size


def triangles_as_json(
    individual: Individual, triangle_count: int, width: int, height: int
) -> list[dict]:
    """Enumerate the individual's triangles (pixel vertices + RGBA color) at
    ``width``x``height``."""
    triangles = triangles_from_alleles(individual.alleles, triangle_count, width, height)
    return [
        {"vertices": [list(vertex) for vertex in triangle.vertices], "color": list(triangle.color)}
        for triangle in triangles
    ]


def save_image(
    individual: Individual,
    triangle_count: int,
    width: int,
    height: int,
    background_rgb: tuple[int, int, int],
    path: str | Path,
) -> None:
    triangles = triangles_from_alleles(individual.alleles, triangle_count, width, height)
    image = render_triangles(triangles, width, height, background_rgb)
    image.save(path)


def save_triangles_json(
    individual: Individual, triangle_count: int, width: int, height: int, path: str | Path
) -> None:
    data = triangles_as_json(individual, triangle_count, width, height)
    Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
