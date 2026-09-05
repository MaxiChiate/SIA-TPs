"""Flat allele vector <-> list of ``Triangle``, and the ``GeneSchema`` for T triangles.

Each triangle is 10 genes: 6 vertex coordinates (x1,y1,x2,y2,x3,y3) + 3 color
channels + alpha, all normalized to [0,1] like every other allele in this
codebase - independent of any pixel resolution, so the same genotype can be
rendered at evaluation size or at full export size. ``block_size=10`` makes a
triangle crossover/mutation's default indivisible unit.

How the three color channels are read is the ``ColorSpace``'s business (see
``problems.triangles.colorspace``): the genotype is the same flat [0,1] cube
either way, only its interpretation - and therefore the shape of the search
space - changes. The space also names those three loci in the schema, so a
genotype dump under ``hcl`` reads ``t0_h, t0_c, t0_l`` rather than ``t0_r, ...``.
"""

from __future__ import annotations

from dataclasses import dataclass

from ga.core.gene import Gene, GeneSchema

from .colorspace import DEFAULT as DEFAULT_COLOR_SPACE
from .colorspace import ColorSpace

GENES_PER_TRIANGLE = 10
_COORD_NAMES = ("x1", "y1", "x2", "y2", "x3", "y3")
_ALPHA_NAME = "a"


@dataclass(frozen=True, slots=True)
class Triangle:
    """One triangle: 3 pixel-space vertices + an RGBA color (0-255 per channel)."""

    vertices: tuple[tuple[float, float], tuple[float, float], tuple[float, float]]
    color: tuple[int, int, int, int]


def schema_for(
    triangle_count: int, color_space: ColorSpace = DEFAULT_COLOR_SPACE
) -> GeneSchema:
    """The ``GeneSchema`` for a genotype of ``triangle_count`` triangles.

    Only the gene *names* depend on ``color_space``; every locus is a plain
    continuous [0,1] gene regardless.
    """
    if triangle_count <= 0:
        raise ValueError(f"triangle_count must be > 0, got {triangle_count}")
    locus_names = _COORD_NAMES + color_space.channel_names + (_ALPHA_NAME,)
    genes = tuple(
        Gene(f"t{t}_{name}", 0.0, 1.0)
        for t in range(triangle_count)
        for name in locus_names
    )
    return GeneSchema(genes=genes, block_size=GENES_PER_TRIANGLE)


def triangles_from_alleles(
    alleles: list[float],
    triangle_count: int,
    width: int,
    height: int,
    color_space: ColorSpace = DEFAULT_COLOR_SPACE,
) -> list[Triangle]:
    """Decode a flat [0,1] allele vector into pixel-space triangles at ``width``x``height``.

    ``width``/``height`` need not match whatever resolution fitness was evaluated
    at - the genotype is resolution-independent by construction. ``color_space``
    decides how each triangle's three color alleles become an sRGB triple; alpha
    is always the linear tenth gene.
    """
    triangles = []
    to_rgb = color_space.to_rgb
    for t in range(triangle_count):
        base = t * GENES_PER_TRIANGLE
        x1, y1, x2, y2, x3, y3, c1, c2, c3, a = alleles[base : base + GENES_PER_TRIANGLE]
        vertices = (
            (x1 * width, y1 * height),
            (x2 * width, y2 * height),
            (x3 * width, y3 * height),
        )
        color = (*to_rgb(c1, c2, c3), round(a * 255))
        triangles.append(Triangle(vertices=vertices, color=color))
    return triangles
