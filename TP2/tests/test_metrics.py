"""Unit tests for ``ga.metrics``."""

from __future__ import annotations

import random
import statistics

import pytest

from conftest import make_individual
from ga.core.gene import Gene, GeneSchema
from ga.core.population import Population
from ga.metrics import genotypic_diversity, record_for


def _population(rows: list[list[float]]) -> Population:
    schema = GeneSchema(
        genes=tuple(Gene(f"g{i}", 0.0, 1.0) for i in range(len(rows[0]))),
        block_size=1,
    )
    return Population(
        individuals=[make_individual(schema, fitness=0.0, alleles=row) for row in rows]
    )


def _reference_diversity(rows: list[list[float]]) -> float:
    """The exact-arithmetic definition this metric is an approximation of."""
    length = len(rows[0])
    return statistics.fmean(
        statistics.pstdev(row[i] for row in rows) for i in range(length)
    )


# -- genotypic_diversity -----------------------------------------------------


def test_diversity_is_zero_for_fewer_than_two_individuals():
    assert genotypic_diversity(_population([[0.1, 0.2]])) == 0.0


def test_diversity_is_zero_when_every_individual_is_identical():
    assert genotypic_diversity(_population([[0.3, 0.7]] * 5)) == 0.0


def test_diversity_matches_the_exact_definition():
    rng = random.Random(20260905)
    rows = [[rng.random() for _ in range(40)] for _ in range(30)]
    got = genotypic_diversity(_population(rows))
    assert got == pytest.approx(_reference_diversity(rows), rel=1e-12)


def test_diversity_matches_on_near_identical_alleles():
    """A converged population is the worst case for a one-pass variance: the
    two terms nearly cancel. Subtracting the mean first must hold up here."""
    rng = random.Random(7)
    rows = [[0.5 + rng.random() * 1e-6 for _ in range(20)] for _ in range(25)]
    got = genotypic_diversity(_population(rows))
    assert got == pytest.approx(_reference_diversity(rows), rel=1e-12)


def test_diversity_averages_over_loci_not_over_individuals():
    """One spread locus among three flat ones must average down to a quarter of
    its own standard deviation."""
    rows = [[0.0, 0.5, 0.5, 0.5], [1.0, 0.5, 0.5, 0.5]]
    assert genotypic_diversity(_population(rows)) == pytest.approx(0.5 / 4)


# -- record_for --------------------------------------------------------------


def test_record_for_summarises_the_population():
    population = _population([[0.0, 1.0], [1.0, 0.0], [0.5, 0.5]])
    for individual, fitness in zip(population.individuals, [0.2, 0.8, 0.5]):
        individual.fitness = fitness
    record = record_for(population, cumulative_evaluations=12, cumulative_seconds=3.5)
    assert record.best_fitness == 0.8
    assert record.worst_fitness == 0.2
    assert record.mean_fitness == pytest.approx(0.5)
    assert record.cumulative_evaluations == 12
    assert record.cumulative_seconds == 3.5
