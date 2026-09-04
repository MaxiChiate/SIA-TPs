"""The abstract ``Problem`` interface: the only surface the engine sees of a domain.

A concrete problem (e.g. ``problems.triangles``) supplies the gene schema, a way to
build a valid random individual from the injected RNG, and a fitness function where
higher is better. Everything image-specific stays behind this interface.
"""

from __future__ import annotations

import abc
from pathlib import Path

from .gene import GeneSchema
from .individual import Individual
from .rng import Rng


class Problem(abc.ABC):
    """Contract between the generic engine and a concrete optimisation domain."""

    @abc.abstractmethod
    def schema(self) -> GeneSchema:
        """The gene specification of this problem's genotype."""

    @abc.abstractmethod
    def random_individual(self, rng: Rng) -> Individual:
        """A valid random individual, drawing all randomness from ``rng``."""

    @abc.abstractmethod
    def evaluate(self, individual: Individual) -> float:
        """Fitness of ``individual`` (higher is better). Must not mutate it.

        The engine owns caching and evaluation counting, so this should do the
        raw work every time it is called.
        """

    def describe(self) -> dict:
        """Optional metadata (image path, metric name, ...) for the run summary."""
        return {}

    def individual_from_export(self, path: str | Path) -> Individual:
        """Decode a previous run's export (e.g. this problem's ``triangles.json``)
        back into an ``Individual`` on this problem's schema, to seed a new run.

        Optional: a problem that supports importing overrides this; the default
        raises so ``ga.config`` can turn it into a clear ``ConfigError``.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support importing individuals"
        )
