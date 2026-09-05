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


# -- rasterized scores: statistical ------------------------------------------

_PARITY_SAMPLES = 120
_TRIANGLES = 40
_SIZE = (96, 60)


def _renderers(space):
    from problems.triangles.renderers import RenderSpec, make_renderer

    spec = RenderSpec.build(
        "images/argentina.png", _SIZE[0], _SIZE[1], (255, 255, 255), space, _TRIANGLES
    )
    return make_renderer("pillow", spec), make_renderer("rust", spec)


def _genomes():
    from ga.core.rng import make_rng

    rng = make_rng(20260905)
    return [
        [rng.random() for _ in range(_TRIANGLES * 10)] for _ in range(_PARITY_SAMPLES)
    ]


@pytest.fixture(scope="module", params=_ALL_SPACES, ids=lambda s: s.name)
def scores(request):
    """Raw MSE from both backends over the same genomes.

    Compared on MSE rather than fitness: fitness floors at 0 for anything worse
    than a blank canvas, and every uniformly random genome is - so a fitness
    comparison here would be 0.0 against 0.0 and would prove nothing.
    """
    pillow, rust = _renderers(request.param)
    genomes = _genomes()
    return [pillow.mse(g) for g in genomes], [rust.mse(g) for g in genomes]


def test_backends_rank_genomes_the_same_way(scores):
    """The primary criterion. Selection only ever consumes the *order* of
    fitnesses, so ranking the same way is what "measures the same thing" means
    operationally."""
    import statistics

    pillow, rust = scores
    assert statistics.correlation(pillow, rust, method="ranked") > 0.99


def test_no_genome_diverges_wildly(scores):
    """A wrong blend, winding or colour space moves this by 10x, not by 2x."""
    pillow, rust = scores
    assert max(abs(r - p) / p for p, r in zip(pillow, rust)) < 0.05


def test_the_systematic_coverage_bias_stays_small(scores):
    """The native rasterizer covers slightly less than ``ImageDraw.polygon``,
    which paints a polygon's outline as well as its interior. That bias is
    inherent to any independent rasterizer; what matters is that it stays an
    order of magnitude below the fitness differences the GA acts on."""
    import statistics

    pillow, rust = scores
    bias = statistics.fmean((r - p) / p for p, r in zip(pillow, rust))
    assert -0.02 < bias < 0.0


def test_fitness_agrees_where_it_is_not_floored():
    """Fitness parity in the regime a converged run actually occupies: small
    alphas, so the picture is built from many translucent layers."""
    from problems.triangles import colorspace

    pillow, rust = _renderers(colorspace.RGB)
    genomes = [
        [value * 0.15 if index % 10 == 9 else value for index, value in enumerate(g)]
        for g in _genomes()[:40]
    ]
    deltas = [abs(rust.score(g) - pillow.score(g)) for g in genomes]
    assert max(deltas) < 0.02


# -- native API contract -----------------------------------------------------


def test_batch_scoring_agrees_with_scoring_one_at_a_time():
    from problems.triangles import colorspace

    _, rust = _renderers(colorspace.RGB)
    genomes = _genomes()[:12]
    assert rust.score_batch(genomes) == [rust.score(g) for g in genomes]


def test_a_genome_of_the_wrong_length_is_rejected():
    from problems.triangles import colorspace

    _, rust = _renderers(colorspace.RGB)
    with pytest.raises(ValueError):
        rust.score([0.5] * 7)


def test_rendering_at_export_size_returns_that_many_pixels():
    """The genotype is resolution-independent, so the same individual must draw
    at export size, not only at the scoring size."""
    from problems.triangles import colorspace

    _, rust = _renderers(colorspace.RGB)
    image = rust.render_rgb(_genomes()[0], 200, 125)
    assert image.size == (200, 125)
    assert image.mode == "RGB"


# -- thread invariance -------------------------------------------------------


def test_scores_do_not_depend_on_the_thread_count():
    """Reproducibility rests on this: parallelism is across individuals, and the
    per-individual kernel is sequential, so the thread count is free to change
    without changing a single result."""
    from problems.triangles import colorspace
    from problems.triangles.renderers import RenderSpec, RustRenderer

    spec = RenderSpec.build(
        "images/argentina.png", _SIZE[0], _SIZE[1], (255, 255, 255), colorspace.HCL,
        _TRIANGLES,
    )
    genomes = _genomes()[:24]
    single = RustRenderer(spec, threads=1).score_batch(genomes)
    many = RustRenderer(spec, threads=8).score_batch(genomes)
    assert single == many


def test_the_thread_count_is_honoured():
    from problems.triangles import colorspace
    from problems.triangles.renderers import RenderSpec, RustRenderer

    spec = RenderSpec.build(
        "images/argentina.png", 16, 16, (255, 255, 255), colorspace.RGB, 2
    )
    assert RustRenderer(spec, threads=3)._scorer.threads == 3


def test_the_rust_backend_claims_ownership_of_parallelism():
    """Which is what stops the engine from also opening a process pool."""
    from problems.triangles import colorspace
    from problems.triangles.renderers import RenderSpec, RustRenderer

    spec = RenderSpec.build(
        "images/argentina.png", 16, 16, (255, 255, 255), colorspace.RGB, 2
    )
    assert RustRenderer(spec).owns_parallelism() is True
