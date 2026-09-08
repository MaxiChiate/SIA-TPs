"""Population: an ordered list of individuals plus the generation index.

Deliberately thin. Aggregate statistics (mean, std, diversity) live in
``ga.metrics`` so this stays a plain container.
"""

from __future__ import annotations

from dataclasses import dataclass

from .individual import Individual


def _fitness_of(individual: Individual) -> float:
    if individual.fitness is None:
        raise ValueError("individual is not evaluated")
    return individual.fitness


@dataclass(slots=True)
class Population:
    """The individuals alive at generation ``generation``."""

    individuals: list[Individual]
    generation: int = 0

    @property
    def size(self) -> int:
        return len(self.individuals)

    def fitnesses(self) -> list[float]:
        """Fitness of every individual; raises if any is unevaluated."""
        return [_fitness_of(individual) for individual in self.individuals]

    def best(self) -> Individual:
        """The individual with the highest fitness (higher is better)."""
        return max(self.individuals, key=_fitness_of)

    def worst(self) -> Individual:
        """The individual with the lowest fitness."""
        return min(self.individuals, key=_fitness_of)
