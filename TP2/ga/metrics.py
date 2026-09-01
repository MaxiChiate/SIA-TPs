"""Per-generation metrics: one record per generation plus small aggregate helpers.

``run.py`` (block 6) dumps these to CSV/JSON. Nothing here draws plots.
"""

from __future__ import annotations

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
    """
    individuals = population.individuals
    if len(individuals) < 2:
        return 0.0
    length = len(individuals[0])
    per_locus = (
        statistics.pstdev(individual.alleles[i] for individual in individuals)
        for i in range(length)
    )
    return statistics.fmean(per_locus)


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
