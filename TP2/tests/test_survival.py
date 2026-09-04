"""Unit tests for ``ga.operators.survival``.

The individual selection algorithms (elite, tournament, ...) are already
covered in ``test_selection.py``; these tests only check what ``survival``
itself is responsible for: which pool (parents+children, or children only) it
hands to the configured selector, and how many it asks for.
"""

from __future__ import annotations

import pytest

import ga.operators  # noqa: F401 -- registers "elite" for the default path
from conftest import ScriptedRandom, make_individual
from ga import registry
from ga.operators.survival import additive, exclusive

_captured: dict = {}


@registry.register("parent_selection", "_test_capture")
def _capture_selection(population, count, rng, params):
    _captured["pool"] = list(population.individuals)
    _captured["count"] = count
    _captured["params"] = params
    return list(population.individuals)[:count]


# -- additive (mu + lambda) ---------------------------------------------------


def test_additive_pool_is_parents_plus_children_ranked_by_elite(schema):
    current = [make_individual(schema, fitness=f) for f in [1, 2]]
    children = [make_individual(schema, fitness=f) for f in [5, 3]]
    survivors = additive(current, children, n=2, rng=ScriptedRandom(), params={})
    assert [i.fitness for i in survivors] == [5, 3]


def test_additive_keeps_a_fitter_parent_over_a_weaker_child(schema):
    current = [make_individual(schema, fitness=f) for f in [10, 1]]
    children = [make_individual(schema, fitness=f) for f in [2, 3]]
    survivors = additive(current, children, n=2, rng=ScriptedRandom(), params={})
    assert [i.fitness for i in survivors] == [10, 3]


def test_additive_passes_pool_count_and_params_to_configured_selector(schema):
    current = [make_individual(schema, fitness=f) for f in [1, 2]]
    children = [make_individual(schema, fitness=f) for f in [3, 4]]
    params = {"selection_method": "_test_capture", "generation": 7}
    additive(current, children, n=3, rng=ScriptedRandom(), params=params)
    assert _captured["pool"] == current + children
    assert _captured["count"] == 3
    assert _captured["params"] == params


# -- exclusive (mu, lambda) ----------------------------------------------------


def test_exclusive_pool_is_children_only(schema):
    current = [make_individual(schema, fitness=f) for f in [100, 100]]
    children = [make_individual(schema, fitness=f) for f in [1, 2]]
    survivors = exclusive(current, children, n=2, rng=ScriptedRandom(), params={})
    assert sorted(i.fitness for i in survivors) == [1, 2]


def test_exclusive_passes_children_only_as_pool(schema):
    current = [make_individual(schema, fitness=1)]
    children = [make_individual(schema, fitness=f) for f in [2, 3]]
    params = {"selection_method": "_test_capture"}
    exclusive(current, children, n=2, rng=ScriptedRandom(), params=params)
    assert _captured["pool"] == children


def test_exclusive_requires_enough_children(schema):
    current = [make_individual(schema, fitness=1)]
    children = [make_individual(schema, fitness=2)]
    with pytest.raises(ValueError):
        exclusive(current, children, n=2, rng=ScriptedRandom(), params={})
