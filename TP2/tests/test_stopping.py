"""Unit tests for ``ga.operators.stopping``."""

from __future__ import annotations

from ga.core.engine import StopContext
from ga.operators.stopping import stagnation, target_fitness


def _context(**overrides) -> StopContext:
    defaults = dict(
        generation=10,
        max_generations=100,
        elapsed_seconds=1.0,
        evaluations=50,
        history=(),
        best_fitness=0.5,
        best_generation=5,
    )
    defaults.update(overrides)
    return StopContext(**defaults)


def test_target_fitness_stops_once_threshold_reached():
    ctx = _context(best_fitness=0.98)
    assert target_fitness(ctx, threshold=0.98) == "target_fitness"


def test_target_fitness_keeps_going_below_threshold():
    ctx = _context(best_fitness=0.5)
    assert target_fitness(ctx, threshold=0.98) is None


def test_stagnation_stops_after_enough_stale_generations():
    ctx = _context(generation=55, best_generation=5)
    assert stagnation(ctx, generations=50) == "stagnation"


def test_stagnation_keeps_going_while_still_improving():
    ctx = _context(generation=54, best_generation=5)
    assert stagnation(ctx, generations=50) is None
