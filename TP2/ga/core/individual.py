"""Individual: a flat allele vector bound to a schema, with a cached fitness.

Operators never mutate an individual in place; they build a fresh one with a new
allele list and ``fitness=None``. A changed genotype therefore always carries an
empty cache, which keeps the engine's fitness memo correct.
"""

from __future__ import annotations

from dataclasses import dataclass

from .gene import GeneSchema


@dataclass(slots=True)
class Individual:
    """One candidate solution: ``len(schema)`` alleles plus its (maybe cached) fitness."""

    alleles: list[float]
    schema: GeneSchema
    fitness: float | None = None

    def __post_init__(self) -> None:
        if len(self.alleles) != len(self.schema):
            raise ValueError(
                f"expected {len(self.schema)} alleles, got {len(self.alleles)}"
            )

    def copy(self) -> "Individual":
        """A deep-enough copy: new allele list, same schema, same cached fitness."""
        return Individual(list(self.alleles), self.schema, self.fitness)

    def with_alleles(self, alleles: list[float]) -> "Individual":
        """A fresh, unevaluated individual on this schema from a new allele list."""
        return Individual(alleles, self.schema, None)

    def key(self) -> tuple[float, ...]:
        """Hashable genotype key for the engine's fitness memo."""
        return tuple(self.alleles)

    def __len__(self) -> int:
        return len(self.alleles)
