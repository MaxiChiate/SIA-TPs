"""Unit tests for ``problems.triangles.renderers``."""

from __future__ import annotations

import pytest

from problems.triangles import colorspace
from problems.triangles.fitness import mean_squared_error
from problems.triangles.renderer import render_triangles
from problems.triangles.renderers import (
    PillowRenderer,
    RenderSpec,
    _baseline_mse,
    available,
    make_renderer,
)

IMAGE = "images/argentina.png"
WIDTH, HEIGHT = 32, 20
BACKGROUND = (255, 255, 255)


@pytest.fixture
def spec() -> RenderSpec:
    return RenderSpec.build(
        IMAGE, WIDTH, HEIGHT, BACKGROUND, colorspace.RGB, triangle_count=4
    )


def _genome(seed: float) -> list[float]:
    """Four triangles' worth of alleles, deterministic and inside [0, 1]."""
    return [((seed * (i + 1)) % 1.0) for i in range(40)]


# -- RenderSpec --------------------------------------------------------------


def test_spec_holds_the_target_at_the_work_resolution(spec):
    assert spec.target_array().shape == (HEIGHT, WIDTH, 3)
    assert len(spec.target_rgb) == WIDTH * HEIGHT * 3


def test_closed_form_baseline_matches_rendering_a_blank_canvas(spec):
    """The fitness denominator must not depend on which backend computes it."""
    blank = render_triangles([], WIDTH, HEIGHT, BACKGROUND)
    assert spec.baseline_mse == mean_squared_error(blank, spec.target_array())


def test_baseline_never_reaches_zero_for_a_target_equal_to_the_background():
    """A target identical to the canvas has zero error, and fitness divides by
    this number."""
    background = (10, 20, 30)
    baseline = _baseline_mse(bytes(background * 4), background)
    assert baseline > 0.0


# -- backend selection -------------------------------------------------------


def test_pillow_is_always_available():
    assert "pillow" in available()


def test_auto_resolves_to_the_best_available_backend(spec):
    renderer = make_renderer("auto", spec)
    assert renderer.name == available()[0]


def test_an_explicit_backend_name_is_honoured(spec):
    assert isinstance(make_renderer("pillow", spec), PillowRenderer)


def test_an_unknown_backend_name_is_rejected_and_lists_the_known_ones(spec):
    with pytest.raises(ValueError) as err:
        make_renderer("opengl", spec)
    assert "opengl" in str(err.value)
    assert "pillow" in str(err.value)


# -- scoring -----------------------------------------------------------------


def test_pillow_scoring_matches_rendering_by_hand(spec):
    """Pins the backend against the original inline implementation."""
    from problems.triangles.fitness import pixel_similarity
    from problems.triangles.genotype import triangles_from_alleles

    alleles = _genome(0.37)
    triangles = triangles_from_alleles(alleles, 4, WIDTH, HEIGHT, colorspace.RGB)
    rendered = render_triangles(triangles, WIDTH, HEIGHT, BACKGROUND)
    expected = pixel_similarity(rendered, spec.target_array(), spec.baseline_mse)

    assert make_renderer("pillow", spec).score(alleles) == expected


def test_batch_scoring_agrees_with_scoring_one_at_a_time(spec):
    renderer = make_renderer("pillow", spec)
    genomes = [_genome(0.11), _genome(0.37), _genome(0.83)]
    assert renderer.score_batch(genomes) == [renderer.score(g) for g in genomes]


def test_mse_is_reported_unclamped(spec):
    """Fitness floors at 0 for anything worse than a blank canvas; the parity
    tests need the raw error, which has no such floor."""
    renderer = make_renderer("pillow", spec)
    alleles = _genome(0.37)
    assert renderer.mse(alleles) > 0.0
    assert renderer.score(alleles) >= 0.0


def test_pillow_does_not_claim_to_own_parallelism(spec):
    """It is the engine's process pool that parallelises this backend."""
    assert make_renderer("pillow", spec).owns_parallelism() is False


def test_describe_reports_the_backend(spec):
    assert make_renderer("pillow", spec).describe() == {"renderer": "pillow"}
