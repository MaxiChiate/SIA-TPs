"""Unit tests for ``ga.operators.selection``.

Each test scripts the ``Rng`` calls an operator is expected to make (see
``ScriptedRandom`` in conftest) rather than seeding a real RNG and checking a
distribution, so results are exact and never flaky.
"""

from __future__ import annotations

import math

import pytest

from conftest import ScriptedRandom, make_individual, make_population
from ga.core.population import Population
from ga.operators.selection import (
    boltzmann,
    elite,
    ranking,
    roulette,
    tournament_deterministic,
    tournament_probabilistic,
    universal,
)

# -- elite ---------------------------------------------------------------


def test_elite_ranks_descending_when_count_fits(schema):
    pop = make_population(schema, [3, 1, 4, 1, 5])
    result = elite(pop, count=3, rng=ScriptedRandom(), params={})
    assert [i.fitness for i in result] == [5, 4, 3]


def test_elite_distributes_extra_copies_by_rank(schema):
    pop = make_population(schema, [1, 2, 3, 4, 5])
    result = elite(pop, count=7, rng=ScriptedRandom(), params={})
    assert [i.fitness for i in result] == [5, 5, 4, 4, 3, 2, 1]


def test_elite_ignores_rng_entirely(schema):
    pop = make_population(schema, [5, 2, 8, 1])
    a = elite(pop, count=4, rng=ScriptedRandom(), params={})
    b = elite(pop, count=4, rng=ScriptedRandom(), params={})
    assert [i.fitness for i in a] == [i.fitness for i in b]


def test_elite_requires_evaluated_individuals(schema):
    pop = Population(individuals=[make_individual(schema, fitness=None)])
    with pytest.raises(ValueError):
        elite(pop, count=1, rng=ScriptedRandom(), params={})


# -- roulette --------------------------------------------------------------


def test_roulette_passes_fitness_as_weights(schema):
    pop = make_population(schema, [1, 2, 3])
    rng = ScriptedRandom(choices=[[pop.individuals[2]]])
    result = roulette(pop, count=1, rng=rng, params={})
    ((_, _, kwargs),) = rng.calls
    assert kwargs["weights"] == [1, 2, 3]
    assert kwargs["k"] == 1
    assert result == [pop.individuals[2]]


# -- universal (SUS) ---------------------------------------------------------


def test_universal_even_split_with_equal_weights(schema):
    pop = make_population(schema, [1, 1, 1, 1])
    rng = ScriptedRandom(uniform=[0.1])
    result = universal(pop, count=4, rng=rng, params={})
    assert result == pop.individuals


def test_universal_zero_total_weight_returns_empty_without_drawing(schema):
    pop = make_population(schema, [0, 0, 0])
    result = universal(pop, count=5, rng=ScriptedRandom(), params={})
    assert result == []


def test_universal_zero_count_returns_empty_without_drawing(schema):
    pop = make_population(schema, [1, 2, 3])
    result = universal(pop, count=0, rng=ScriptedRandom(), params={})
    assert result == []


# -- boltzmann ---------------------------------------------------------------


def test_boltzmann_weights_use_cooling_formula(schema):
    pop = make_population(schema, [2.0, 4.0])
    rng = ScriptedRandom(choices=[[pop.individuals[0]]])
    params = {"t0": 20.0, "tmin": 1.0, "tau": 10.0, "generation": 5}
    boltzmann(pop, count=1, rng=rng, params=params)
    ((_, _, kwargs),) = rng.calls
    temperature = 1.0 + 19.0 * math.exp(-5 / 10.0)
    expected = [math.exp(2.0 / temperature), math.exp(4.0 / temperature)]
    assert kwargs["weights"] == pytest.approx(expected)
    assert kwargs["k"] == 1


def test_boltzmann_defaults_tau_from_max_generations(schema):
    pop = make_population(schema, [1.0, 1.0])
    rng = ScriptedRandom(choices=[[pop.individuals[0]]])
    params = {"max_generations": 40, "generation": 10}
    boltzmann(pop, count=1, rng=rng, params=params)
    ((_, _, kwargs),) = rng.calls
    tau = 40 / 4
    temperature = 1.0 + 19.0 * math.exp(-10 / tau)
    expected = [math.exp(1.0 / temperature)] * 2
    assert kwargs["weights"] == pytest.approx(expected)


# -- tournament_deterministic -------------------------------------------------


def test_tournament_deterministic_picks_best_of_each_group(schema):
    pop = make_population(schema, [3, 7, 1])
    rng = ScriptedRandom(
        choices=[
            [pop.individuals[0], pop.individuals[1]],
            [pop.individuals[2], pop.individuals[1]],
        ]
    )
    result = tournament_deterministic(pop, count=2, rng=rng, params={"tournament_size": 2})
    assert result == [pop.individuals[1], pop.individuals[1]]
    choice_calls = [c for c in rng.calls if c[0] == "choices"]
    assert all(c[2]["k"] == 2 for c in choice_calls)


# -- tournament_probabilistic --------------------------------------------------


def test_tournament_probabilistic_picks_fitter_below_threshold(schema):
    pop = make_population(schema, [1, 9])
    rng = ScriptedRandom(
        choices=[[pop.individuals[0], pop.individuals[1]]], random=[0.5]
    )
    result = tournament_probabilistic(pop, count=1, rng=rng, params={"threshold": 0.75})
    assert result == [pop.individuals[1]]


def test_tournament_probabilistic_picks_weaker_above_threshold(schema):
    pop = make_population(schema, [1, 9])
    rng = ScriptedRandom(
        choices=[[pop.individuals[0], pop.individuals[1]]], random=[0.9]
    )
    result = tournament_probabilistic(pop, count=1, rng=rng, params={"threshold": 0.75})
    assert result == [pop.individuals[0]]


# -- ranking -------------------------------------------------------------------


def test_ranking_weights_are_rank_based_not_fitness_based(schema):
    pop = make_population(schema, [100, 1, 50])
    rng = ScriptedRandom(choices=[[pop.individuals[0]]])
    ranking(pop, count=1, rng=rng, params={})
    ((_, _, kwargs),) = rng.calls
    assert kwargs["population"] == [pop.individuals[0], pop.individuals[2], pop.individuals[1]]
    assert kwargs["weights"] == [3, 2, 1]
