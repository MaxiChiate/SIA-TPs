"""Parent-selection methods: pick ``count`` individuals from a population, with
replacement, to determine who reproduces.

Every method shares the signature ``(population, count, rng, params) -> list[Individual]``
(matching ``ga.core.engine.ParentSelection``) so ``ga.operators.survival`` can look
any of them up by name in the registry and reuse it verbatim over a different pool
(parents+children, or children only). Sampling is always with replacement, since
callers may ask for more individuals than the pool holds (e.g. ``2k > n``).
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from .. import registry
from ..core.individual import Individual
from ..core.population import Population
from ..core.rng import Rng


def _fitness(individual: Individual) -> float:
    if individual.fitness is None:
        raise ValueError("selection requires every individual to be evaluated")
    return individual.fitness


def _weighted_sample(
    individuals: Sequence[Individual], weights: Sequence[float], count: int, rng: Rng
) -> list[Individual]:
    """``count`` draws with replacement, one weighted spin of the wheel per draw."""
    return rng.choices(list(individuals), weights=list(weights), k=count)


@registry.register("parent_selection", "elite")
def elite(population: Population, count: int, rng: Rng, params: dict) -> list[Individual]:
    """Deterministic: rank descending, hand out ``ceil((count - rank) / n)`` copies.

    No randomness: the same population and count always yield the same picks.
    """
    ranked = sorted(population.individuals, key=_fitness, reverse=True)
    n = len(ranked)
    selected: list[Individual] = []
    for rank, individual in enumerate(ranked):
        copies = math.ceil((count - rank) / n)
        selected.extend([individual] * max(0, copies))
    return selected[:count]


@registry.register("parent_selection", "roulette")
def roulette(population: Population, count: int, rng: Rng, params: dict) -> list[Individual]:
    """Fitness-proportionate: each of ``count`` draws is an independent weighted spin.

    Requires non-negative fitness values (a proportionate-selection limitation,
    not something this operator works around).
    """
    individuals = population.individuals
    weights = [_fitness(i) for i in individuals]
    return _weighted_sample(individuals, weights, count, rng)


@registry.register("parent_selection", "universal")
def universal(population: Population, count: int, rng: Rng, params: dict) -> list[Individual]:
    """Stochastic Universal Sampling: one random offset, ``count`` evenly spaced pointers.

    Lower variance than roulette for the same weights, since all draws share one
    random offset instead of spinning independently.
    """
    individuals = population.individuals
    weights = [_fitness(i) for i in individuals]
    total = sum(weights)
    if total <= 0 or count == 0:
        return []
    step = total / count
    start = rng.uniform(0.0, step)

    selected: list[Individual] = []
    cumulative = 0.0
    idx = 0
    for i in range(count):
        pointer = start + i * step
        while cumulative + weights[idx] < pointer and idx < len(individuals) - 1:
            cumulative += weights[idx]
            idx += 1
        selected.append(individuals[idx])
    return selected


@registry.register("parent_selection", "boltzmann")
def boltzmann(population: Population, count: int, rng: Rng, params: dict) -> list[Individual]:
    """Weighted by ``exp(fitness / T)``, ``T`` cooling from ``t0`` down to ``tmin``.

    ``T(t) = tmin + (t0 - tmin) * exp(-generation / tau)``: a high early temperature
    keeps selection close to uniform (exploration); cooling toward ``tmin`` sharpens
    it toward pure elitism (exploitation) as the run progresses. The textbook
    formula also divides each weight by the population's mean weight for
    "expected copies" intuition; that cancels out in the final draw probabilities
    (``rng.choices`` normalizes by the weight total), so it is skipped here.
    """
    t0 = params.get("t0", 20.0)
    tmin = params.get("tmin", 1.0)
    tau = params.get("tau", max(params.get("max_generations", 1), 1) / 4)
    generation = params.get("generation", 0)

    temperature = tmin + (t0 - tmin) * math.exp(-generation / tau)
    individuals = population.individuals
    weights = [math.exp(_fitness(i) / temperature) for i in individuals]
    return _weighted_sample(individuals, weights, count, rng)


@registry.register("parent_selection", "tournament_deterministic")
def tournament_deterministic(
    population: Population, count: int, rng: Rng, params: dict
) -> list[Individual]:
    """Each draw: sample ``tournament_size`` individuals with replacement, keep the best."""
    size = params.get("tournament_size", 3)
    individuals = population.individuals
    selected = []
    for _ in range(count):
        contenders = rng.choices(individuals, k=size)
        selected.append(max(contenders, key=_fitness))
    return selected


@registry.register("parent_selection", "tournament_probabilistic")
def tournament_probabilistic(
    population: Population, count: int, rng: Rng, params: dict
) -> list[Individual]:
    """Each draw: pick 2 individuals, take the fitter one with probability ``threshold``."""
    threshold = params.get("threshold", 0.75)
    individuals = population.individuals
    selected = []
    for _ in range(count):
        a, b = rng.choices(individuals, k=2)
        better, worse = (a, b) if _fitness(a) >= _fitness(b) else (b, a)
        selected.append(better if rng.random() < threshold else worse)
    return selected


@registry.register("parent_selection", "ranking")
def ranking(population: Population, count: int, rng: Rng, params: dict) -> list[Individual]:
    """Roulette over rank instead of raw fitness: best -> weight ``n``, worst -> weight 1.

    Removes the influence of fitness magnitude/scale on selection pressure; only
    the ordering of individuals matters.
    """
    ranked = sorted(population.individuals, key=_fitness, reverse=True)
    n = len(ranked)
    weights = [n - rank for rank in range(n)]
    return _weighted_sample(ranked, weights, count, rng)
