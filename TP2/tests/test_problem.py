"""Unit tests for ``TrianglesProblem``'s genotype-level rules.

Scoring lives in ``test_renderers.py``; what is asserted here is how the problem
seeds a run, which is the part ``initial_alpha`` changes. Building a
``TrianglesProblem`` at all needs the native ``triangles_native`` extension
(there is no Python-only renderer left to construct it with), hence the same
skip guard as the renderer/parity tests.

Alpha-locus helpers derive the stride from ``problem.schema().block_size``
rather than a hardcoded constant, so the same assertions run unchanged across
``shape_type in {"triangle", "oval", "both"}`` - alpha is always a block's last
gene regardless of mode (see ``problems.triangles.genotype``).
"""

from __future__ import annotations

import pytest

pytest.importorskip(
    "triangles_native",
    reason="native backend not built; see README (cd rust && maturin develop --release)",
)

from ga.core.rng import make_rng  # noqa: E402  (after the skip guard)
from problems.triangles.problem import TrianglesProblem  # noqa: E402

IMAGE = "images/argentina.png"
SHAPES = 4
SHAPE_TYPES = ("triangle", "oval", "both")


def make_problem(**overrides) -> TrianglesProblem:
    params = {
        "image_path": IMAGE,
        "shape_count": SHAPES,
        "work_resolution": [32, 20],
        "background_rgb": [255, 255, 255],
    }
    return TrianglesProblem(params | overrides)


def alphas(problem: TrianglesProblem, alleles: list[float]) -> list[float]:
    block = problem.schema().block_size
    return alleles[block - 1 :: block]


def non_alphas(problem: TrianglesProblem, alleles: list[float]) -> list[float]:
    block = problem.schema().block_size
    return [a for i, a in enumerate(alleles) if i % block != block - 1]


@pytest.mark.parametrize("shape_type", SHAPE_TYPES)
def test_default_leaves_the_whole_alpha_range_available(shape_type):
    problem = make_problem(shape_type=shape_type)
    assert problem.initial_alpha == 1.0
    alleles = problem.random_individual(make_rng(7)).alleles
    assert alleles == make_problem(shape_type=shape_type).random_individual(make_rng(7)).alleles


@pytest.mark.parametrize("shape_type", SHAPE_TYPES)
def test_initial_alpha_scales_only_the_alpha_loci(shape_type):
    cap = 0.05
    plain_problem = make_problem(shape_type=shape_type)
    capped_problem = make_problem(shape_type=shape_type, initial_alpha=cap)
    plain = plain_problem.random_individual(make_rng(7)).alleles
    capped = capped_problem.random_individual(make_rng(7)).alleles

    # Same seed, same draws: the cap is applied after the vector is drawn, so
    # comparing two caps compares two populations and not two RNG streams.
    assert non_alphas(plain_problem, capped) == non_alphas(plain_problem, plain)
    assert alphas(plain_problem, capped) == [
        pytest.approx(a * cap) for a in alphas(plain_problem, plain)
    ]
    assert all(0.0 <= a <= cap for a in alphas(plain_problem, capped))


@pytest.mark.parametrize("shape_type", SHAPE_TYPES)
def test_initial_alpha_does_not_touch_later_generations(shape_type):
    """Only the seed draw is biased: nothing downstream clamps alpha, so an
    operator is free to walk it back up to 1."""
    problem = make_problem(shape_type=shape_type, initial_alpha=0.05)
    individual = problem.random_individual(make_rng(7))
    grown = list(individual.alleles)
    grown[problem.schema().block_size - 1] = 1.0
    assert problem.evaluate(individual.__class__(grown, problem.schema())) >= 0.0


def test_work_resolution_native_uses_the_source_image_size():
    from problems.triangles.export import native_resolution

    problem = make_problem(work_resolution="native")
    assert (problem.work_width, problem.work_height) == native_resolution(IMAGE)


def test_work_resolution_native_is_reported_resolved():
    """``describe`` feeds the run summary, so it has to record which pixels were
    actually compared - not the sentinel that asked for them."""
    from problems.triangles.export import native_resolution

    described = make_problem(work_resolution="native").describe()["work_resolution"]
    assert described == list(native_resolution(IMAGE))


def test_unknown_work_resolution_string_is_rejected():
    with pytest.raises(ValueError, match="work_resolution"):
        make_problem(work_resolution="full")


@pytest.mark.parametrize("value", [0.0, -0.1, 1.5])
def test_initial_alpha_outside_the_unit_interval_is_rejected(value):
    with pytest.raises(ValueError, match="initial_alpha"):
        make_problem(initial_alpha=value)


def test_initial_alpha_is_reported_in_describe():
    assert make_problem(initial_alpha=0.25).describe()["initial_alpha"] == 0.25


def test_shape_type_defaults_to_triangle():
    assert make_problem().shape_type == "triangle"
    assert make_problem().describe()["shape_type"] == "triangle"


@pytest.mark.parametrize("shape_type", SHAPE_TYPES)
def test_shape_type_and_shape_count_are_reported_in_describe(shape_type):
    described = make_problem(shape_type=shape_type).describe()
    assert described["shape_type"] == shape_type
    assert described["shape_count"] == SHAPES


def test_unknown_shape_type_is_rejected():
    with pytest.raises(ValueError, match="shape_type"):
        make_problem(shape_type="hexagon")
