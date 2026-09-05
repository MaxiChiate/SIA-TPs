"""Unit tests for ``TrianglesProblem``'s genotype-level rules.

Scoring lives in ``test_renderers.py``; what is asserted here is how the problem
seeds a run, which is the part ``initial_alpha`` changes.
"""

from __future__ import annotations

import pytest

from ga.core.rng import make_rng
from problems.triangles.genotype import ALPHA_LOCUS, GENES_PER_TRIANGLE
from problems.triangles.problem import TrianglesProblem

IMAGE = "images/argentina.png"
TRIANGLES = 4


def make_problem(**overrides) -> TrianglesProblem:
    params = {
        "image_path": IMAGE,
        "triangle_count": TRIANGLES,
        "work_resolution": [32, 20],
        "background_rgb": [255, 255, 255],
        "renderer": "pillow",
    }
    return TrianglesProblem(params | overrides)


def alphas(alleles: list[float]) -> list[float]:
    return alleles[ALPHA_LOCUS::GENES_PER_TRIANGLE]


def non_alphas(alleles: list[float]) -> list[float]:
    return [a for i, a in enumerate(alleles) if i % GENES_PER_TRIANGLE != ALPHA_LOCUS]


def test_default_leaves_the_whole_alpha_range_available():
    problem = make_problem()
    assert problem.initial_alpha == 1.0
    alleles = problem.random_individual(make_rng(7)).alleles
    assert alleles == make_problem().random_individual(make_rng(7)).alleles


def test_initial_alpha_scales_only_the_alpha_loci():
    cap = 0.05
    plain = make_problem().random_individual(make_rng(7)).alleles
    capped = make_problem(initial_alpha=cap).random_individual(make_rng(7)).alleles

    # Same seed, same draws: the cap is applied after the vector is drawn, so
    # comparing two caps compares two populations and not two RNG streams.
    assert non_alphas(capped) == non_alphas(plain)
    assert alphas(capped) == [pytest.approx(a * cap) for a in alphas(plain)]
    assert all(0.0 <= a <= cap for a in alphas(capped))


def test_initial_alpha_does_not_touch_later_generations():
    """Only the seed draw is biased: nothing downstream clamps alpha, so an
    operator is free to walk it back up to 1."""
    problem = make_problem(initial_alpha=0.05)
    individual = problem.random_individual(make_rng(7))
    grown = list(individual.alleles)
    grown[ALPHA_LOCUS] = 1.0
    assert problem.evaluate(individual.__class__(grown, problem.schema())) >= 0.0


@pytest.mark.parametrize("value", [0.0, -0.1, 1.5])
def test_initial_alpha_outside_the_unit_interval_is_rejected(value):
    with pytest.raises(ValueError, match="initial_alpha"):
        make_problem(initial_alpha=value)


def test_initial_alpha_is_reported_in_describe():
    assert make_problem(initial_alpha=0.25).describe()["initial_alpha"] == 0.25
