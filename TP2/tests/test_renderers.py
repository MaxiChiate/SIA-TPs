"""Unit tests for ``problems.triangles.renderers``."""

from __future__ import annotations

import pytest

from problems.triangles import colorspace
from problems.triangles.genotype import genes_per_shape

native = pytest.importorskip(
    "triangles_native",
    reason="native backend not built; see README (cd rust && maturin develop --release)",
)

from problems.triangles.renderers import (  # noqa: E402  (after the skip guard)
    RenderSpec,
    RustRenderer,
    _baseline_mse,
)

IMAGE = "images/argentina.png"
WIDTH, HEIGHT = 32, 20
BACKGROUND = (255, 255, 255)
SHAPE_COUNT = 4
SHAPE_TYPES = ("triangle", "oval", "both")


@pytest.fixture(params=SHAPE_TYPES)
def shape_type(request) -> str:
    return request.param


@pytest.fixture
def spec(shape_type) -> RenderSpec:
    return RenderSpec.build(
        IMAGE, WIDTH, HEIGHT, BACKGROUND, colorspace.RGB, SHAPE_COUNT, shape_type
    )


def _genome(seed: float, shape_type: str = "triangle") -> list[float]:
    """One genome's worth of alleles, deterministic and inside [0, 1]."""
    length = SHAPE_COUNT * genes_per_shape(shape_type)
    return [((seed * (i + 1)) % 1.0) for i in range(length)]


def _blank_genome(shape_type: str = "triangle") -> list[float]:
    """Same shape count, every alpha zeroed - the native rasterizer's
    equivalent of "draw nothing". ``RenderSpec`` fixes the shape count, so
    there is no way to hand it an empty list; a fully transparent population
    leaves the canvas unchanged instead."""
    block = genes_per_shape(shape_type)
    alleles = _genome(0.5, shape_type)
    for locus in range(block - 1, len(alleles), block):  # alpha is always the last gene
        alleles[locus] = 0.0
    return alleles


# -- RenderSpec ----------------------------------------------------------------


def test_spec_holds_the_target_at_the_work_resolution(spec):
    assert spec.target_array().shape == (HEIGHT, WIDTH, 3)
    assert len(spec.target_rgb) == WIDTH * HEIGHT * 3


def test_closed_form_baseline_matches_rendering_nothing(spec, shape_type):
    """The fitness denominator must match what the renderer itself reports for
    a fully transparent - i.e. invisible - population of shapes."""
    renderer = RustRenderer(spec)
    assert spec.baseline_mse == pytest.approx(renderer.mse(_blank_genome(shape_type)))


def test_baseline_never_reaches_zero_for_a_target_equal_to_the_background():
    """A target identical to the canvas has zero error, and fitness divides by
    this number."""
    background = (10, 20, 30)
    baseline = _baseline_mse(bytes(background * 4), background)
    assert baseline > 0.0


# -- construction ----------------------------------------------------------


def test_a_stale_schema_version_is_rejected(spec, monkeypatch):
    """A .so built from an older revision of the kernel must fail loudly
    instead of silently scoring genomes a different way."""
    import problems.triangles.renderers as renderers_module

    monkeypatch.setattr(
        renderers_module._native,
        "schema_version",
        lambda: renderers_module.NATIVE_SCHEMA_VERSION + 1,
    )
    with pytest.raises(ValueError, match="schema"):
        RustRenderer(spec)


def test_unknown_shape_type_is_rejected():
    spec = RenderSpec.build(IMAGE, WIDTH, HEIGHT, BACKGROUND, colorspace.RGB, SHAPE_COUNT, "hexagon")
    with pytest.raises(ValueError, match="shape_type"):
        RustRenderer(spec)


# -- scoring -----------------------------------------------------------------


def test_batch_scoring_agrees_with_scoring_one_at_a_time(spec, shape_type):
    renderer = RustRenderer(spec)
    genomes = [_genome(0.11, shape_type), _genome(0.37, shape_type), _genome(0.83, shape_type)]
    assert renderer.score_batch(genomes) == [renderer.score(g) for g in genomes]


def test_mse_is_reported_unclamped(spec, shape_type):
    """Fitness floors at 0 for anything worse than a blank canvas; the thread
    invariance tests need the raw error, which has no such floor."""
    renderer = RustRenderer(spec)
    alleles = _genome(0.37, shape_type)
    assert renderer.mse(alleles) > 0.0
    assert renderer.score(alleles) >= 0.0


def test_rust_owns_its_own_parallelism(spec):
    """The engine must not also open a process pool on top of the kernel's
    own rayon threads."""
    assert RustRenderer(spec).owns_parallelism() is True


def test_describe_reports_the_build(spec):
    described = RustRenderer(spec).describe()
    assert described["renderer"] == "rust"
    assert "renderer_build" in described
    assert described["renderer_threads"] >= 1
