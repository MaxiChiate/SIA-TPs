"""Native-vs-Python colour parity, and the native kernel's own API contract.

Colour decoding still has an independent pure-Python implementation
(``problems.triangles.colorspace``, used by ``export.py``'s JSON enumeration and
by importing a previous run's ``triangles.json``), so it is still worth
checking the native kernel's decode against it bit for bit - that comparison
lives in the first half of this file.

Rasterizing and scoring, by contrast, now run *only* in the native kernel:
there is no Pillow oracle left to compare against, so the tests further down
that exercise those are about the kernel's own API contract (batch scoring,
thread invariance, malformed input) rather than parity with anything.

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
    """A debug build of this kernel is slower than pure-Python rendering ever
    was, which looks like a failed port rather than a wrong build command."""
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


# -- native API contract -----------------------------------------------------

_TRIANGLES = 40
_SIZE = (96, 60)


def _rust_renderer(space):
    from problems.triangles.renderers import RenderSpec, RustRenderer

    spec = RenderSpec.build(
        "images/argentina.png", _SIZE[0], _SIZE[1], (255, 255, 255), space, _TRIANGLES
    )
    return RustRenderer(spec)


def _genomes():
    from ga.core.rng import make_rng

    rng = make_rng(20260905)
    return [[rng.random() for _ in range(_TRIANGLES * 10)] for _ in range(120)]


def test_batch_scoring_agrees_with_scoring_one_at_a_time():
    from problems.triangles import colorspace

    rust = _rust_renderer(colorspace.RGB)
    genomes = _genomes()[:12]
    assert rust.score_batch(genomes) == [rust.score(g) for g in genomes]


def test_a_genome_of_the_wrong_length_is_rejected():
    from problems.triangles import colorspace

    rust = _rust_renderer(colorspace.RGB)
    with pytest.raises(ValueError):
        rust.score([0.5] * 7)


def test_rendering_at_export_size_returns_that_many_pixels():
    """The genotype is resolution-independent, so the same individual must draw
    at export size, not only at the scoring size."""
    from problems.triangles import colorspace

    rust = _rust_renderer(colorspace.RGB)
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
