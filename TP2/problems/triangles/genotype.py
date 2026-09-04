"""Flat allele vector <-> list of ``Triangle``, and the ``GeneSchema`` for T triangles.

Each triangle is 10 genes: 6 vertex coordinates (x1,y1,x2,y2,x3,y3) + RGBA color,
all normalized to [0,1] like every other allele in this codebase - independent of
any pixel resolution, so the same genotype can be rendered at evaluation size or
at full export size. ``block_size=10`` makes a triangle crossover/mutation's
default indivisible unit.
"""

from __future__ import annotations

from dataclasses import dataclass

from ga.core.gene import Gene, GeneSchema

GENES_PER_TRIANGLE = 10
_COORD_NAMES = ("x1", "y1", "x2", "y2", "x3", "y3")
_COLOR_NAMES = ("r", "g", "b", "a")


@dataclass(frozen=True, slots=True)
class Triangle:
    """One triangle: 3 pixel-space vertices + an RGBA color (0-255 per channel)."""

    vertices: tuple[tuple[float, float], tuple[float, float], tuple[float, float]]
    color: tuple[int, int, int, int]


def schema_for(triangle_count: int) -> GeneSchema:
    """The ``GeneSchema`` for a genotype of ``triangle_count`` triangles."""
    if triangle_count <= 0:
        raise ValueError(f"triangle_count must be > 0, got {triangle_count}")
    genes = tuple(
        Gene(f"t{t}_{name}", 0.0, 1.0)
        for t in range(triangle_count)
        for name in _COORD_NAMES + _COLOR_NAMES
    )
    return GeneSchema(genes=genes, block_size=GENES_PER_TRIANGLE)


def triangles_from_alleles(
    alleles: list[float], triangle_count: int, width: int, height: int
) -> list[Triangle]:
    """Decode a flat [0,1] allele vector into pixel-space triangles at ``width``x``height``.

    ``width``/``height`` need not match whatever resolution fitness was evaluated
    at - the genotype is resolution-independent by construction.
    """
    triangles = []
    for t in range(triangle_count):
        base = t * GENES_PER_TRIANGLE
        x1, y1, x2, y2, x3, y3, r, g, b, a = alleles[base : base + GENES_PER_TRIANGLE]
        vertices = (
            (x1 * width, y1 * height),
            (x2 * width, y2 * height),
            (x3 * width, y3 * height),
        )
        color = (round(r * 255), round(g * 255), round(b * 255), round(a * 255))
        triangles.append(Triangle(vertices=vertices, color=color))
    return triangles
