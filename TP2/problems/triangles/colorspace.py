"""Color spaces: how a triangle's three color alleles are read as an sRGB color.

Every allele lives in ``[0,1]`` (like the rest of the genotype), so a color space
here is just a pair of pure numeric functions: one that reads three alleles as a
0-255 sRGB triple, and its inverse (needed to decode a previous run's export back
into alleles). The alpha allele is always linear and space-independent.

The choice is not cosmetic - it reshapes the search space. Under ``rgb``, mutation
and crossover move along the three primaries; under ``hcl`` they move along
perceptual hue / colorfulness / lightness, so a mutation that shifts hue keeps the
lightness a triangle had already found.

``hcl`` is CIE LCh(ab): the polar form of CIELAB under a D65 white point (the
convention used by chroma.js and CSS Color 4's ``lch()``). Roughly 40% of the
``H x C x L`` box falls outside the sRGB gamut; those colors are brought back by
**reducing chroma** at constant hue and lightness (bisection, ``_GAMUT_STEPS``
iterations), rather than by clamping the RGB channels. Clamping distorts all three
axes at once and collapses large regions of the box onto the same color, which
would flatten the fitness landscape in H, C and L alike; reducing chroma keeps hue
and lightness faithful and confines the resulting plateau to the C axis.

All conversions are deliberately allocation-free scalar float math (no numpy), so
this module ports to C essentially line for line.
"""

from __future__ import annotations

import colorsys
import math
from collections.abc import Callable
from dataclasses import dataclass

# Allele scaling for hcl. L is CIELAB lightness in [0,100]; C is capped at the
# most colorful sRGB color in Lab (blue, C ~ 133.8), so the whole gamut stays
# reachable and ``from_rgb`` never has to clamp a real color's chroma.
_MAX_CHROMA = 140.0
_GAMUT_STEPS = 12  # bisection depth: 140/2**12 << one 8-bit step
# Slack on the gamut test, in linear light. Sized so a color sitting exactly on
# the gamut surface survives the round-trip's float noise (~1e-8) without being
# pushed inward, while staying orders of magnitude below one 8-bit step (~4e-3
# in linear light near white), so it can never change a rendered byte.
_GAMUT_TOLERANCE = 1e-6

# CIELAB, D65 white point (the sRGB reference white).
_WHITE_X, _WHITE_Y, _WHITE_Z = 0.95047, 1.0, 1.08883
_LAB_EPSILON = 216.0 / 24389.0
_LAB_KAPPA = 24389.0 / 27.0


@dataclass(frozen=True, slots=True)
class ColorSpace:
    """One way to read three ``[0,1]`` alleles as a color, plus its inverse.

    ``channel_names`` names the three loci in the ``GeneSchema`` (e.g. ``h,c,l``),
    so a genotype dump says which axis each allele is on.
    """

    name: str
    channel_names: tuple[str, str, str]
    to_rgb: Callable[[float, float, float], tuple[int, int, int]]
    from_rgb: Callable[[int, int, int], tuple[float, float, float]]


def _clamp01(value: float) -> float:
    return min(1.0, max(0.0, value))


def _to_byte(value: float) -> int:
    return round(_clamp01(value) * 255)


# -- rgb ---------------------------------------------------------------------


def rgb_to_rgb(r: float, g: float, b: float) -> tuple[int, int, int]:
    return _to_byte(r), _to_byte(g), _to_byte(b)


def rgb_from_rgb(r: int, g: int, b: int) -> tuple[float, float, float]:
    return r / 255.0, g / 255.0, b / 255.0


# -- hsv ---------------------------------------------------------------------


def hsv_to_rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    """Every point of the HSV cube is a valid sRGB color, so there is no gamut
    step here - only a change of coordinates."""
    r, g, b = colorsys.hsv_to_rgb(_clamp01(h), _clamp01(s), _clamp01(v))
    return _to_byte(r), _to_byte(g), _to_byte(b)


def hsv_from_rgb(r: int, g: int, b: int) -> tuple[float, float, float]:
    return colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)


# -- hcl (CIE LCh(ab), D65) --------------------------------------------------


def _srgb_companding(linear: float) -> float:
    if linear <= 0.0031308:
        return 12.92 * linear
    return 1.055 * (linear ** (1.0 / 2.4)) - 0.055


def _srgb_inverse_companding(encoded: float) -> float:
    if encoded <= 0.04045:
        return encoded / 12.92
    return ((encoded + 0.055) / 1.055) ** 2.4


def _lab_to_linear_rgb(lightness: float, a: float, b: float) -> tuple[float, float, float]:
    fy = (lightness + 16.0) / 116.0
    fx = fy + a / 500.0
    fz = fy - b / 200.0

    x = fx**3 if fx**3 > _LAB_EPSILON else (116.0 * fx - 16.0) / _LAB_KAPPA
    y = fy**3 if lightness > _LAB_KAPPA * _LAB_EPSILON else lightness / _LAB_KAPPA
    z = fz**3 if fz**3 > _LAB_EPSILON else (116.0 * fz - 16.0) / _LAB_KAPPA
    x, y, z = x * _WHITE_X, y * _WHITE_Y, z * _WHITE_Z

    return (
        3.2404542 * x - 1.5371385 * y - 0.4985314 * z,
        -0.9692660 * x + 1.8760108 * y + 0.0415560 * z,
        0.0556434 * x - 0.2040259 * y + 1.0572252 * z,
    )


def _linear_rgb_to_lab(r: float, g: float, b: float) -> tuple[float, float, float]:
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / _WHITE_X
    y = (0.2126729 * r + 0.7151522 * g + 0.0721750 * b) / _WHITE_Y
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / _WHITE_Z

    fx, fy, fz = (
        v ** (1.0 / 3.0) if v > _LAB_EPSILON else (_LAB_KAPPA * v + 16.0) / 116.0
        for v in (x, y, z)
    )
    return 116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz)


def _in_gamut(linear: tuple[float, float, float]) -> bool:
    return all(
        -_GAMUT_TOLERANCE <= channel <= 1.0 + _GAMUT_TOLERANCE for channel in linear
    )


def _lch_to_linear_rgb(
    lightness: float, chroma: float, hue_radians: float
) -> tuple[float, float, float]:
    return _lab_to_linear_rgb(
        lightness, chroma * math.cos(hue_radians), chroma * math.sin(hue_radians)
    )


def hcl_to_rgb(h: float, c: float, lightness: float) -> tuple[int, int, int]:
    """Read ``(h, c, l)`` alleles as an sRGB color, reducing chroma if needed.

    ``c = 0`` is always in gamut (an achromatic color of that lightness), so the
    bisection below always has a valid lower bound.
    """
    hue = _clamp01(h) * 2.0 * math.pi
    chroma = _clamp01(c) * _MAX_CHROMA
    light = _clamp01(lightness) * 100.0

    linear = _lch_to_linear_rgb(light, chroma, hue)
    if not _in_gamut(linear):
        # Start from the achromatic color of this lightness rather than from the
        # out-of-gamut one: when the in-gamut chroma range is narrower than the
        # bisection's first step (e.g. at L = 100, where only pure white fits),
        # no midpoint is ever accepted, and ``linear`` must still hold a real
        # color instead of falling back to clamping the raw channels.
        low, high = 0.0, chroma
        linear = _lch_to_linear_rgb(light, 0.0, hue)
        for _ in range(_GAMUT_STEPS):
            middle = (low + high) / 2.0
            candidate = _lch_to_linear_rgb(light, middle, hue)
            if _in_gamut(candidate):
                low, linear = middle, candidate
            else:
                high = middle

    r, g, b = (_srgb_companding(_clamp01(channel)) for channel in linear)
    return _to_byte(r), _to_byte(g), _to_byte(b)


def hcl_from_rgb(r: int, g: int, b: int) -> tuple[float, float, float]:
    lightness, a, b_star = _linear_rgb_to_lab(
        *(_srgb_inverse_companding(channel / 255.0) for channel in (r, g, b))
    )
    chroma = math.hypot(a, b_star)
    hue = math.atan2(b_star, a) % (2.0 * math.pi)
    return (
        hue / (2.0 * math.pi),
        _clamp01(chroma / _MAX_CHROMA),
        _clamp01(lightness / 100.0),
    )


# -- registry ----------------------------------------------------------------

RGB = ColorSpace("rgb", ("r", "g", "b"), rgb_to_rgb, rgb_from_rgb)
HSV = ColorSpace("hsv", ("h", "s", "v"), hsv_to_rgb, hsv_from_rgb)
HCL = ColorSpace("hcl", ("h", "c", "l"), hcl_to_rgb, hcl_from_rgb)

_BY_NAME = {space.name: space for space in (RGB, HSV, HCL)}
DEFAULT = RGB


def get(name: str) -> ColorSpace:
    """The ``ColorSpace`` registered under ``name``, or ``ValueError``."""
    try:
        return _BY_NAME[name]
    except KeyError:
        known = ", ".join(sorted(_BY_NAME))
        raise ValueError(f"unknown color_space {name!r}; known: {known}") from None
