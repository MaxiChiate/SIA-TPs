"""Flat allele vector <-> list of ``Figure``, and the ``GeneSchema`` for a run's
shapes.

Three ``shape_type`` modes decide what each fixed-size block of the genotype
decodes to; alpha is always the block's last gene in every mode, which is what
lets ``problems.triangles.problem`` seed generation 0 with ``initial_alpha`` by
locus offset alone, without knowing which mode is active:

``triangle``  block of 10: ``x1,y1,x2,y2,x3,y3, c1,c2,c3, a`` - unchanged from
              the original triangles-only genotype.
``oval``      block of 9: ``cx,cy,rx,ry,theta, c1,c2,c3, a``.
``both``      block of 11: ``kind, p0..p5, c1,c2,c3, a``. ``kind`` is a
              discrete 0/1 gene - 0 decodes ``p0..p5`` as the triangle's six
              coordinates, 1 decodes ``p0..p4`` as the oval's
              ``cx,cy,rx,ry,theta`` (``p5`` sits unused but still mutates).
              Which shape lives in a block is therefore decided by mutation,
              generation over generation - there is no separate "structural"
              operator, ``kind`` is a gene like any other discrete gene.

``theta`` alleles are read as ``[0, pi)``, not ``[0, 2*pi)``: an ellipse looks
identical rotated by pi, so the full turn would waste half the mutation range
on visual duplicates. ``rx``/``ry`` scale exactly like any coordinate
(``allele * width`` / ``allele * height``), reusing the same rule vertices
already use rather than inventing a shape-specific cap.

``Figure`` is the abstraction that lets ``problems.triangles.export`` and
``problems.triangles.problem`` handle a genotype's shapes without knowing
which kind each one is: ``Triangle`` and ``Oval`` both expose ``to_export()``,
and ``figure_from_export`` is the one place that reads a ``"type"`` field back
into a concrete class.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

from ga.core.gene import Gene, GeneSchema

from .colorspace import DEFAULT as DEFAULT_COLOR_SPACE
from .colorspace import ColorSpace

ShapeType = Literal["triangle", "oval", "both"]
SHAPE_TYPES: tuple[ShapeType, ...] = ("triangle", "oval", "both")

# Genes per shape block, one per mode - see the module docstring for the layout.
TRIANGLE_GENES = 10
OVAL_GENES = 9
BOTH_GENES = 11
_GENES_PER_SHAPE: dict[str, int] = {
    "triangle": TRIANGLE_GENES,
    "oval": OVAL_GENES,
    "both": BOTH_GENES,
}

# Kept for the triangle-only mode specifically (the block layout that has not
# changed): alpha is the last of its 10 genes.
GENES_PER_TRIANGLE = TRIANGLE_GENES
ALPHA_LOCUS = TRIANGLE_GENES - 1

_COORD_NAMES = ("x1", "y1", "x2", "y2", "x3", "y3")
_OVAL_PARAM_NAMES = ("cx", "cy", "rx", "ry", "theta")
_ALPHA_NAME = "a"


def genes_per_shape(shape_type: str) -> int:
    """Block size (genes per shape) for ``shape_type``."""
    try:
        return _GENES_PER_SHAPE[shape_type]
    except KeyError:
        raise ValueError(
            f"unknown shape_type {shape_type!r}; expected one of {SHAPE_TYPES}"
        ) from None


class Figure(ABC):
    """One decoded shape: pixel-space geometry plus an RGBA colour.

    Downstream code (``export.py``, the render stages) works through this
    interface instead of branching on which concrete shape it holds.
    """

    __slots__ = ()  # keeps concrete dataclasses (slots=True) actually slotted

    color: tuple[int, int, int, int]

    @abstractmethod
    def to_export(self) -> dict:
        """This figure as a JSON-serialisable dict, tagged with its ``type``."""


@dataclass(frozen=True, slots=True)
class Triangle(Figure):
    """Three pixel-space vertices + an RGBA colour (0-255 per channel)."""

    vertices: tuple[tuple[float, float], tuple[float, float], tuple[float, float]]
    color: tuple[int, int, int, int]

    def to_export(self) -> dict:
        return {
            "type": "triangle",
            "vertices": [list(vertex) for vertex in self.vertices],
            "color": list(self.color),
        }


@dataclass(frozen=True, slots=True)
class Oval(Figure):
    """A pixel-space ellipse (centre, semi-axes, rotation) + an RGBA colour."""

    center: tuple[float, float]
    radii: tuple[float, float]
    angle: float  # radians, [0, pi)
    color: tuple[int, int, int, int]

    def to_export(self) -> dict:
        return {
            "type": "oval",
            "center": list(self.center),
            "radii": list(self.radii),
            "angle": self.angle,
            "color": list(self.color),
        }


def figure_from_export(data: dict) -> Figure:
    """The inverse of ``Figure.to_export()``, dispatched on ``data["type"]``."""
    kind = data.get("type")
    if kind == "triangle":
        return Triangle(
            vertices=tuple(tuple(vertex) for vertex in data["vertices"]),
            color=tuple(data["color"]),
        )
    if kind == "oval":
        return Oval(
            center=tuple(data["center"]),
            radii=tuple(data["radii"]),
            angle=data["angle"],
            color=tuple(data["color"]),
        )
    raise ValueError(f"unknown figure type {kind!r}; expected 'triangle' or 'oval'")


def schema_for(
    shape_type: str,
    shape_count: int,
    color_space: ColorSpace = DEFAULT_COLOR_SPACE,
) -> GeneSchema:
    """The ``GeneSchema`` for a genotype of ``shape_count`` shapes in ``shape_type`` mode.

    Every locus is a plain continuous ``[0,1]`` gene except ``kind`` in ``both``
    mode, which is discrete - see the module docstring for the block layout.
    """
    if shape_count <= 0:
        raise ValueError(f"shape_count must be > 0, got {shape_count}")
    color_names = color_space.channel_names

    if shape_type == "triangle":
        locus_names = _COORD_NAMES + color_names + (_ALPHA_NAME,)
        genes = tuple(
            Gene(f"s{s}_{name}", 0.0, 1.0)
            for s in range(shape_count)
            for name in locus_names
        )
    elif shape_type == "oval":
        locus_names = _OVAL_PARAM_NAMES + color_names + (_ALPHA_NAME,)
        genes = tuple(
            Gene(f"s{s}_{name}", 0.0, 1.0)
            for s in range(shape_count)
            for name in locus_names
        )
    elif shape_type == "both":
        param_names = tuple(f"p{i}" for i in range(6))
        genes = []
        for s in range(shape_count):
            genes.append(Gene(f"s{s}_kind", 0.0, 1.0, kind="discrete"))
            genes.extend(Gene(f"s{s}_{name}", 0.0, 1.0) for name in param_names)
            genes.extend(Gene(f"s{s}_{name}", 0.0, 1.0) for name in color_names)
            genes.append(Gene(f"s{s}_{_ALPHA_NAME}", 0.0, 1.0))
        genes = tuple(genes)
    else:
        raise ValueError(
            f"unknown shape_type {shape_type!r}; expected one of {SHAPE_TYPES}"
        )

    return GeneSchema(genes=genes, block_size=genes_per_shape(shape_type))


def _decode_triangle(
    params: list[float], color_alleles: list[float], alpha_allele: float,
    width: int, height: int, color_space: ColorSpace,
) -> Triangle:
    x1, y1, x2, y2, x3, y3 = params
    vertices = (
        (x1 * width, y1 * height),
        (x2 * width, y2 * height),
        (x3 * width, y3 * height),
    )
    color = (*color_space.to_rgb(*color_alleles), round(alpha_allele * 255))
    return Triangle(vertices=vertices, color=color)


def _decode_oval(
    params: list[float], color_alleles: list[float], alpha_allele: float,
    width: int, height: int, color_space: ColorSpace,
) -> Oval:
    cx, cy, rx, ry, theta = params[:5]
    center = (cx * width, cy * height)
    radii = (rx * width, ry * height)
    angle = theta * math.pi
    color = (*color_space.to_rgb(*color_alleles), round(alpha_allele * 255))
    return Oval(center=center, radii=radii, angle=angle, color=color)


def figures_from_alleles(
    alleles: list[float],
    shape_type: str,
    shape_count: int,
    width: int,
    height: int,
    color_space: ColorSpace = DEFAULT_COLOR_SPACE,
) -> list[Figure]:
    """Decode a flat ``[0,1]`` allele vector into pixel-space figures at
    ``width``x``height``.

    ``width``/``height`` need not match whatever resolution fitness was
    evaluated at - the genotype is resolution-independent by construction.
    Mirrors the native scorer's decode rules exactly (``rust/src/score.rs``),
    since this is the function the JSON export enumerates figures with.
    """
    block = genes_per_shape(shape_type)
    figures: list[Figure] = []
    for s in range(shape_count):
        base = s * block
        g = alleles[base : base + block]
        if shape_type == "triangle":
            figures.append(_decode_triangle(g[0:6], g[6:9], g[9], width, height, color_space))
        elif shape_type == "oval":
            figures.append(_decode_oval(g[0:5], g[5:8], g[8], width, height, color_space))
        else:  # both
            kind = round(g[0])
            params, color_alleles, alpha_allele = g[1:7], g[7:10], g[10]
            if kind == 0:
                figures.append(
                    _decode_triangle(params, color_alleles, alpha_allele, width, height, color_space)
                )
            else:
                figures.append(
                    _decode_oval(params, color_alleles, alpha_allele, width, height, color_space)
                )
    return figures


def alleles_from_figures(
    figures: list[Figure],
    shape_type: str,
    width: int,
    height: int,
    color_space: ColorSpace = DEFAULT_COLOR_SPACE,
) -> list[float]:
    """The inverse of ``figures_from_alleles``: pixel-space figures -> a flat
    ``[0,1]`` allele vector on ``shape_type``'s schema.

    Every figure must be importable under ``shape_type``: ``triangle``/``oval``
    modes reject a figure of the other kind (there is no block layout to put
    it in); ``both`` accepts either and sets the ``kind`` gene accordingly,
    padding the unused parameter slot with ``0.0``.
    """
    alleles: list[float] = []
    for index, figure in enumerate(figures):
        if shape_type == "triangle":
            if not isinstance(figure, Triangle):
                raise ValueError(
                    f"figure {index} is {figure.to_export()['type']!r}, "
                    f"but shape_type is 'triangle'"
                )
            alleles.extend(_encode_triangle_params(figure, width, height))
            alleles.extend(_encode_color(figure.color, color_space))
        elif shape_type == "oval":
            if not isinstance(figure, Oval):
                raise ValueError(
                    f"figure {index} is {figure.to_export()['type']!r}, "
                    f"but shape_type is 'oval'"
                )
            alleles.extend(_encode_oval_params(figure, width, height))
            alleles.extend(_encode_color(figure.color, color_space))
        else:  # both
            if isinstance(figure, Triangle):
                alleles.append(0.0)  # kind
                alleles.extend(_encode_triangle_params(figure, width, height))
            elif isinstance(figure, Oval):
                alleles.append(1.0)  # kind
                alleles.extend(_encode_oval_params(figure, width, height))
                alleles.append(0.0)  # unused 6th param slot
            else:
                raise ValueError(f"figure {index} is neither a triangle nor an oval")
            alleles.extend(_encode_color(figure.color, color_space))
    return alleles


def _clamp01(value: float) -> float:
    return min(1.0, max(0.0, value))


def _encode_triangle_params(triangle: Triangle, width: int, height: int) -> list[float]:
    return [
        coordinate
        for x, y in triangle.vertices
        for coordinate in (_clamp01(x / width), _clamp01(y / height))
    ]


def _encode_oval_params(oval: Oval, width: int, height: int) -> list[float]:
    cx, cy = oval.center
    rx, ry = oval.radii
    return [
        _clamp01(cx / width),
        _clamp01(cy / height),
        _clamp01(rx / width),
        _clamp01(ry / height),
        _clamp01((oval.angle % math.pi) / math.pi),
    ]


def _encode_color(color: tuple[int, int, int, int], color_space: ColorSpace) -> list[float]:
    red, green, blue, alpha = color
    return [
        *(_clamp01(channel) for channel in color_space.from_rgb(red, green, blue)),
        _clamp01(alpha / 255),
    ]
