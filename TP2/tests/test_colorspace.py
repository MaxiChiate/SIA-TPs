"""Unit tests for ``problems.triangles.colorspace``."""

from __future__ import annotations

import itertools

import pytest

from problems.triangles import colorspace

# A coarse but exhaustive sweep of the sRGB cube: every 15th value per channel.
_SAMPLE_COLORS = list(itertools.product(range(0, 256, 15), repeat=3))
_ALL_SPACES = (colorspace.RGB, colorspace.HSV, colorspace.HCL)

# -- registry ----------------------------------------------------------------


def test_get_returns_the_registered_space():
    assert colorspace.get("hcl") is colorspace.HCL
    assert colorspace.get("rgb") is colorspace.DEFAULT


def test_get_rejects_an_unknown_name_and_lists_the_known_ones():
    with pytest.raises(ValueError) as err:
        colorspace.get("cmyk")
    assert "cmyk" in str(err.value)
    assert "hcl" in str(err.value)


def test_every_space_names_its_three_channels():
    for space in _ALL_SPACES:
        assert len(space.channel_names) == 3
        assert len(set(space.channel_names)) == 3


# -- allele domain -----------------------------------------------------------


@pytest.mark.parametrize("space", _ALL_SPACES, ids=lambda s: s.name)
def test_any_point_of_the_allele_cube_is_a_valid_srgb_color(space):
    """The genotype is a plain [0,1] cube, so no allele triple may decode to an
    out-of-range byte - for hcl that is what the gamut reduction guarantees."""
    steps = [i / 8 for i in range(9)]
    for alleles in itertools.product(steps, repeat=3):
        for channel in space.to_rgb(*alleles):
            assert isinstance(channel, int)
            assert 0 <= channel <= 255


@pytest.mark.parametrize("space", _ALL_SPACES, ids=lambda s: s.name)
def test_from_rgb_stays_inside_the_allele_domain(space):
    for color in _SAMPLE_COLORS:
        assert all(0.0 <= allele <= 1.0 for allele in space.from_rgb(*color))


@pytest.mark.parametrize("space", _ALL_SPACES, ids=lambda s: s.name)
def test_from_rgb_then_to_rgb_is_the_identity(space):
    """``individual_from_export`` decodes a run's RGB export back into alleles;
    re-rendering them must reproduce the exact same pixels."""
    for color in _SAMPLE_COLORS:
        assert space.to_rgb(*space.from_rgb(*color)) == color


# -- rgb ---------------------------------------------------------------------


def test_rgb_scales_alleles_linearly_to_bytes():
    assert colorspace.RGB.to_rgb(0.0, 0.5, 1.0) == (0, 128, 255)


# -- hsv ---------------------------------------------------------------------


def test_hsv_hue_sweeps_the_primaries_at_full_saturation_and_value():
    assert colorspace.HSV.to_rgb(0.0, 1.0, 1.0) == (255, 0, 0)
    assert colorspace.HSV.to_rgb(1 / 3, 1.0, 1.0) == (0, 255, 0)
    assert colorspace.HSV.to_rgb(2 / 3, 1.0, 1.0) == (0, 0, 255)


def test_hsv_zero_saturation_is_grey_of_the_given_value():
    assert colorspace.HSV.to_rgb(0.7, 0.0, 0.6) == (153, 153, 153)


# -- hcl ---------------------------------------------------------------------


def test_hcl_zero_chroma_is_grey_whatever_the_hue():
    for hue in (0.0, 0.25, 0.5, 0.9):
        red, green, blue = colorspace.HCL.to_rgb(hue, 0.0, 0.5)
        assert red == green == blue


def test_hcl_lightness_spans_black_to_white():
    assert colorspace.HCL.to_rgb(0.0, 0.0, 0.0) == (0, 0, 0)
    assert colorspace.HCL.to_rgb(0.0, 0.0, 1.0) == (255, 255, 255)


@pytest.mark.parametrize("chroma", [0.1, 0.3, 1.0])
def test_hcl_lightness_is_monotone_at_constant_hue_and_chroma(chroma):
    """Raising the L allele must never darken the color, including where the
    gamut reduction kicks in - a plateau is fine, a dip is not."""
    previous = -1.0
    for step in range(21):
        rendered = colorspace.HCL.to_rgb(0.1, chroma, step / 20)
        lightness = colorspace.HCL.from_rgb(*rendered)[2]
        assert lightness >= previous
        previous = lightness


def test_hcl_gamut_reduction_preserves_hue_and_lightness():
    """An out-of-gamut chroma is pulled back to the gamut surface at constant H
    and L, so the decoded color still reports (nearly) the requested hue and
    lightness - which clamping the RGB channels would not."""
    hue, lightness = 0.1, 0.5
    rendered = colorspace.HCL.to_rgb(hue, 1.0, lightness)
    back_hue, back_chroma, back_lightness = colorspace.HCL.from_rgb(*rendered)
    assert back_hue == pytest.approx(hue, abs=0.01)
    assert back_lightness == pytest.approx(lightness, abs=0.01)
    assert back_chroma < 1.0  # it really was reduced


def test_hcl_leaves_an_in_gamut_chroma_untouched():
    """The bisection must not nibble at colors that already fit."""
    alleles = colorspace.HCL.from_rgb(120, 90, 60)
    assert colorspace.HCL.to_rgb(*alleles) == (120, 90, 60)


def test_hcl_falls_back_to_grey_when_no_chroma_fits():
    """At the extremes of L only the achromatic color is in gamut; the reduction
    must land exactly on it instead of clamping the raw channels."""
    assert colorspace.HCL.to_rgb(0.1, 0.9, 1.0) == (255, 255, 255)
    assert colorspace.HCL.to_rgb(0.1, 0.9, 0.0) == (0, 0, 0)
