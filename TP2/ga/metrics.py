"""Per-generation metrics: one record per generation plus small aggregate helpers.

``run.py`` (block 6) dumps these to CSV/JSON. Nothing here draws plots.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass

from .core.population import Population


@dataclass(frozen=True, slots=True)
class GenerationRecord:
    """A snapshot of one generation, ready to serialise to a log row."""

    generation: int
    best_fitness: float
    mean_fitness: float
    std_fitness: float
    worst_fitness: float
    genotypic_diversity: float
    cumulative_evaluations: int
    cumulative_seconds: float


def mean(values: Sequence[float]) -> float:
    """Arithmetic mean, or 0.0 for an empty sequence."""
    return statistics.fmean(values) if values else 0.0


def std(values: Sequence[float]) -> float:
    """Population standard deviation, or 0.0 for fewer than two values."""
    return statistics.pstdev(values) if len(values) > 1 else 0.0


def genotypic_diversity(population: Population) -> float:
    """Mean per-locus population standard deviation of the allele vectors.

    O(N*L) and comparable across runs because every allele lives in [0, 1].

    Deliberately not ``statistics.pstdev`` per locus: that computes an *exact*
    result over ``Fraction`` values, and paying for exact rational arithmetic L
    times per generation made this single diagnostic ~25% of a run's wall clock
    (measured: 49 ms per generation at N=100, L=500). ``math.fsum`` plus
    ``math.sumprod`` do the same reduction at C speed in 2.6 ms.

    Two passes per locus, not the ``E[x^2] - E[x]^2`` shortcut: the shortcut is
    only 0.6 ms faster and loses ~1e-4 of relative accuracy once a locus
    converges to a spread of ~1e-6, exactly when this number is being read to
    see whether the population has collapsed. Subtracting the mean first keeps
    it exact there.
    """
    individuals = population.individuals
    count = len(individuals)
    if count < 2:
        return 0.0
    vectors = [individual.alleles for individual in individuals]
    total = 0.0
    length = 0
    for column in zip(*vectors):
        average = math.fsum(column) / count
        deviations = [value - average for value in column]
        total += math.sqrt(math.sumprod(deviations, deviations) / count)
        length += 1
    return total / length


def record_for(
    population: Population,
    cumulative_evaluations: int,
    cumulative_seconds: float,
) -> GenerationRecord:
    """Build the ``GenerationRecord`` for an already-evaluated population."""
    fitnesses = population.fitnesses()
    return GenerationRecord(
        generation=population.generation,
        best_fitness=max(fitnesses),
        mean_fitness=mean(fitnesses),
        std_fitness=std(fitnesses),
        worst_fitness=min(fitnesses),
        genotypic_diversity=genotypic_diversity(population),
        cumulative_evaluations=cumulative_evaluations,
        cumulative_seconds=cumulative_seconds,
    )
