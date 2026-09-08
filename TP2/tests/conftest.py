"""Shared fixtures and a scripted RNG stub for deterministic operator tests.

Real randomness (statistical sampling over many draws) is deliberately avoided:
``ScriptedRandom`` returns pre-programmed values for whichever ``Rng`` methods an
operator calls, so every test asserts an exact result instead of a distribution.
"""

from __future__ import annotations

from ga.core.gene import Gene, GeneSchema
from ga.core.individual import Individual
from ga.core.population import Population

import pytest


class ScriptedRandom:
    """``Rng``-shaped stub: each method pops its next scripted return value.

    ``ScriptedRandom(random=[0.1, 0.9], uniform=[0.5])`` makes the first call to
    ``.random()`` return ``0.1``, the second ``0.9``, and the only call to
    ``.uniform(...)`` return ``0.5``. Every call is recorded in ``.calls`` as
    ``(method_name, args, kwargs)`` so tests can also assert what an operator
    passed in (e.g. the weights given to ``.choices``).
    """

    def __init__(self, **scripts: list) -> None:
        self._scripts = {name: list(values) for name, values in scripts.items()}
        self.calls: list[tuple[str, tuple, dict]] = []

    def _consume(self, name: str, args: tuple, kwargs: dict):
        self.calls.append((name, args, kwargs))
        try:
            return self._scripts[name].pop(0)
        except (KeyError, IndexError):
            raise AssertionError(
                f"ScriptedRandom: no more scripted {name!r} return values"
            ) from None

    def random(self) -> float:
        return self._consume("random", (), {})

    def uniform(self, a: float, b: float) -> float:
        return self._consume("uniform", (), {"a": a, "b": b})

    def randrange(self, *args) -> int:
        return self._consume("randrange", args, {})

    def randint(self, a: int, b: int) -> int:
        return self._consume("randint", (), {"a": a, "b": b})

    def choices(self, population, weights=None, k=1):
        return self._consume(
            "choices",
            (),
            {
                "population": list(population),
                "weights": list(weights) if weights is not None else None,
                "k": k,
            },
        )

    def sample(self, population, k):
        return self._consume(
            "sample", (), {"population": list(population), "k": k}
        )


@pytest.fixture
def schema() -> GeneSchema:
    """6 continuous genes in [0, 1], grouped into 3 blocks of 2.

    Small enough to hand-compute cut points / block boundaries in tests, big
    enough (3 blocks) to tell block-granularity and allele-granularity apart.
    """
    genes = tuple(Gene(name=f"g{i}", lower=0.0, upper=1.0) for i in range(6))
    return GeneSchema(genes=genes, block_size=2)


def make_individual(
    schema: GeneSchema, fitness: float | None = None, alleles: list[float] | None = None
) -> Individual:
    if alleles is None:
        alleles = [0.0] * len(schema)
    return Individual(alleles=list(alleles), schema=schema, fitness=fitness)


def make_population(schema: GeneSchema, fitnesses: list[float]) -> Population:
    return Population(
        individuals=[make_individual(schema, fitness=f) for f in fitnesses]
    )
