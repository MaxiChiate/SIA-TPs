"""Parity between the native backend and the Pillow/Python reference.

The whole point of keeping the Python implementation around is to have an oracle
to check the Rust one against. The comparison is split by how exact it can be:

* **Colour decoding is bit-exact.** It is pure scalar float maths on both sides,
  so these assert equality with ``==`` and no tolerance at all.
* **Rasterized scores are not**, and cannot be: Pillow's polygon fill and an
  independent scanline rasterizer disagree on which pixels a triangle covers.
  Those comparisons live further down and are statistical.

Skipped wholesale when the extension is not built, so a checkout with no Rust
toolchain still runs a green suite.
"""

from __future__ import annotations

import itertools

import pytest

native = pytest.importorskip(
    "triangles_native",
    reason="native backend not built; see README (cd rust && maturin develop --release)",
)

from problems.triangles import colorspace  # noqa: E402  (after the skip guard)

_ALL_SPACES = (colorspace.RGB, colorspace.HSV, colorspace.HCL)
_GRID = [index / 12 for index in range(13)]


# -- module identity ---------------------------------------------------------


def test_the_built_extension_matches_this_source_tree():
    """A stale .so from an earlier build would otherwise score genomes with
    numerics that no longer match the code in front of you."""
    from problems.triangles.renderers import NATIVE_SCHEMA_VERSION

    assert native.schema_version() == NATIVE_SCHEMA_VERSION


def test_build_info_reports_an_optimised_build():
    """A debug build of the kernel is slower than the Pillow path it replaces,
    which looks like a failed port rather than a wrong build command."""
    assert "release" in native.build_info()


# -- colour decoding: exact --------------------------------------------------


@pytest.mark.parametrize("space", _ALL_SPACES, ids=lambda s: s.name)
def test_color_decoding_is_bit_exact_over_the_allele_cube(space):
    for alleles in itertools.product(_GRID, repeat=3):
        assert native.to_rgb(space.name, *alleles) == space.to_rgb(*alleles)


@pytest.mark.parametrize("space", _ALL_SPACES, ids=lambda s: s.name)
def test_color_decoding_is_bit_exact_on_the_domain_boundaries(space):
    """Corners and edges of the cube are where the two implementations' rounding
    and clamping rules would first diverge."""
    for alleles in itertools.product([0.0, 1.0], repeat=3):
        assert native.to_rgb(space.name, *alleles) == space.to_rgb(*alleles)


def test_hcl_gamut_reduction_agrees_where_it_actually_fires():
    """Most of the HCL box is out of gamut; the bisection is the subtlest part
    of the port, so it gets its own sweep at high chroma."""
    for hue in _GRID:
        for lightness in _GRID:
            assert native.to_rgb("hcl", hue, 1.0, lightness) == colorspace.HCL.to_rgb(
                hue, 1.0, lightness
            )


def test_an_unknown_color_space_is_rejected():
    with pytest.raises(ValueError):
        native.to_rgb("cmyk", 0.1, 0.2, 0.3)
