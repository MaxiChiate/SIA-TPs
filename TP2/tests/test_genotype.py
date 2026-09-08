"""Unit tests for ``problems.triangles.genotype``: the ``shape_type`` gene
layouts, and the round-trip between alleles and ``Figure`` objects that the
JSON export/import path depends on.

Pure Python, no native extension needed - unlike ``test_problem.py`` and
``test_renderers.py``, everything here runs without ``triangles_native`` built.
"""

from __future__ import annotations

import math

import pytest

from problems.triangles import colorspace
from problems.triangles.genotype import (
    BOTH_GENES,
    OVAL_GENES,
    TRIANGLE_GENES,
    Oval,
    Triangle,
    alleles_from_figures,
    figure_from_export,
    figures_from_alleles,
    genes_per_shape,
    schema_for,
)

WIDTH, HEIGHT = 40, 30

# -- schema_for ----------------------------------------------------------------


def test_triangle_schema_matches_the_original_fixed_layout():
    schema = schema_for("triangle", shape_count=3, color_space=colorspace.RGB)
    assert schema.block_size == TRIANGLE_GENES == 10
    assert len(schema) == 3 * 10
    names = [gene.name for gene in schema][:10]
    assert names == ["s0_x1", "s0_y1", "s0_x2", "s0_y2", "s0_x3", "s0_y3", "s0_r", "s0_g", "s0_b", "s0_a"]
    assert all(gene.kind == "continuous" for gene in schema)


def test_oval_schema_block_size_and_names():
    schema = schema_for("oval", shape_count=2, color_space=colorspace.RGB)
    assert schema.block_size == OVAL_GENES == 9
    assert len(schema) == 2 * 9
    names = [gene.name for gene in schema][:9]
    assert names == ["s0_cx", "s0_cy", "s0_rx", "s0_ry", "s0_theta", "s0_r", "s0_g", "s0_b", "s0_a"]
    assert all(gene.kind == "continuous" for gene in schema)


def test_both_schema_block_size_and_discrete_kind_gene():
    schema = schema_for("both", shape_count=2, color_space=colorspace.RGB)
    assert schema.block_size == BOTH_GENES == 11
    assert len(schema) == 2 * 11
    block = list(schema)[:11]
    assert block[0].name == "s0_kind"
    assert block[0].kind == "discrete"
    assert [gene.kind for gene in block[1:]] == ["continuous"] * 10
    assert [gene.name for gene in block[1:7]] == [f"s0_p{i}" for i in range(6)]
    assert [gene.name for gene in block[7:]] == ["s0_r", "s0_g", "s0_b", "s0_a"]


def test_alpha_is_always_the_last_gene_of_the_block():
    for shape_type in ("triangle", "oval", "both"):
        schema = schema_for(shape_type, shape_count=2, color_space=colorspace.RGB)
        block = schema.block_size
        assert list(schema)[block - 1].name.endswith("_a")
        assert list(schema)[2 * block - 1].name.endswith("_a")


def test_schema_for_rejects_unknown_shape_type():
    with pytest.raises(ValueError, match="shape_type"):
        schema_for("hexagon", shape_count=1)


def test_schema_for_rejects_non_positive_shape_count():
    with pytest.raises(ValueError, match="shape_count"):
        schema_for("triangle", shape_count=0)


def test_genes_per_shape_matches_the_schema_block_size():
    for shape_type, expected in (("triangle", 10), ("oval", 9), ("both", 11)):
        assert genes_per_shape(shape_type) == expected


def test_genes_per_shape_rejects_unknown_shape_type():
    with pytest.raises(ValueError, match="shape_type"):
        genes_per_shape("hexagon")


# -- Figure.to_export / figure_from_export --------------------------------------


def test_triangle_export_round_trip():
    triangle = Triangle(vertices=((1.0, 2.0), (3.0, 4.0), (5.0, 6.0)), color=(10, 20, 30, 200))
    restored = figure_from_export(triangle.to_export())
    assert restored == triangle
    assert triangle.to_export()["type"] == "triangle"


def test_oval_export_round_trip():
    oval = Oval(center=(5.0, 6.0), radii=(2.0, 3.0), angle=1.2, color=(10, 20, 30, 200))
    restored = figure_from_export(oval.to_export())
    assert restored == oval
    assert oval.to_export()["type"] == "oval"


def test_figure_from_export_rejects_unknown_type():
    with pytest.raises(ValueError, match="figure type"):
        figure_from_export({"type": "hexagon"})


# -- figures_from_alleles / alleles_from_figures (allele <-> Figure) ------------


def test_figures_from_alleles_decodes_the_right_number_and_type():
    schema = schema_for("triangle", shape_count=3, color_space=colorspace.RGB)
    alleles = [0.5] * len(schema)
    figures = figures_from_alleles(alleles, "triangle", 3, WIDTH, HEIGHT, colorspace.RGB)
    assert len(figures) == 3
    assert all(isinstance(figure, Triangle) for figure in figures)


def test_figures_from_alleles_oval_decodes_ovals():
    schema = schema_for("oval", shape_count=2, color_space=colorspace.RGB)
    alleles = [0.5] * len(schema)
    figures = figures_from_alleles(alleles, "oval", 2, WIDTH, HEIGHT, colorspace.RGB)
    assert len(figures) == 2
    assert all(isinstance(figure, Oval) for figure in figures)


@pytest.mark.parametrize("kind_allele,expected_type", [(0.0, Triangle), (1.0, Oval)])
def test_both_mode_decodes_by_the_kind_gene(kind_allele, expected_type):
    # kind, p0..p5, r,g,b, a
    block = [kind_allele] + [0.4] * 6 + [0.1, 0.2, 0.3, 0.9]
    figures = figures_from_alleles(block, "both", 1, WIDTH, HEIGHT, colorspace.RGB)
    assert isinstance(figures[0], expected_type)


def test_oval_theta_wraps_to_half_a_turn():
    """theta=1.0 must decode to pi, not 2*pi - an ellipse repeats every half turn."""
    block = [0.5, 0.5, 0.3, 0.2, 1.0, 0.1, 0.2, 0.3, 1.0]  # cx,cy,rx,ry,theta,r,g,b,a
    (oval,) = figures_from_alleles(block, "oval", 1, WIDTH, HEIGHT, colorspace.RGB)
    assert oval.angle == pytest.approx(math.pi)


@pytest.mark.parametrize("shape_type", ["triangle", "oval"])
def test_pure_mode_round_trip_recovers_the_same_figures(shape_type):
    schema = schema_for(shape_type, shape_count=3, color_space=colorspace.RGB)
    original_alleles = [((0.37 * (i + 1)) % 1.0) for i in range(len(schema))]
    figures = figures_from_alleles(original_alleles, shape_type, 3, WIDTH, HEIGHT, colorspace.RGB)

    recovered_alleles = alleles_from_figures(figures, shape_type, WIDTH, HEIGHT, colorspace.RGB)
    recovered_figures = figures_from_alleles(recovered_alleles, shape_type, 3, WIDTH, HEIGHT, colorspace.RGB)
    assert recovered_figures == figures


def test_both_mode_round_trip_preserves_kind_per_block():
    figures = [
        Triangle(vertices=((1.0, 1.0), (10.0, 1.0), (1.0, 10.0)), color=(200, 0, 0, 255)),
        Oval(center=(20.0, 15.0), radii=(5.0, 3.0), angle=0.4, color=(0, 200, 0, 128)),
    ]
    alleles = alleles_from_figures(figures, "both", WIDTH, HEIGHT, colorspace.RGB)
    assert len(alleles) == 2 * BOTH_GENES

    decoded = figures_from_alleles(alleles, "both", 2, WIDTH, HEIGHT, colorspace.RGB)
    assert isinstance(decoded[0], Triangle)
    assert isinstance(decoded[1], Oval)
    assert decoded[0].color == (200, 0, 0, 255)
    assert decoded[1].color == (0, 200, 0, 128)
    assert decoded[1].center == pytest.approx(figures[1].center, abs=0.5)
    assert decoded[1].radii == pytest.approx(figures[1].radii, abs=0.5)


def test_alleles_from_figures_rejects_an_oval_in_triangle_only_mode():
    oval = Oval(center=(1.0, 1.0), radii=(1.0, 1.0), angle=0.0, color=(0, 0, 0, 255))
    with pytest.raises(ValueError, match="triangle"):
        alleles_from_figures([oval], "triangle", WIDTH, HEIGHT, colorspace.RGB)


def test_alleles_from_figures_rejects_a_triangle_in_oval_only_mode():
    triangle = Triangle(vertices=((0.0, 0.0), (1.0, 0.0), (0.0, 1.0)), color=(0, 0, 0, 255))
    with pytest.raises(ValueError, match="oval"):
        alleles_from_figures([triangle], "oval", WIDTH, HEIGHT, colorspace.RGB)
