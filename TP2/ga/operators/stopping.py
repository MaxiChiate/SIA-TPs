"""Stopping criteria: additional halt conditions OR'd together with the engine's
hard ``max_generations`` cap (see ``ga.config._resolve_stopping``).
"""

from __future__ import annotations

from ..core.engine import StopContext
from ..registry import register


@register("stopping", "target_fitness")
def target_fitness(context: StopContext, threshold: float) -> str | None:
    """Stop once the best individual's fitness reaches ``threshold`` (content-based)."""
    return "target_fitness" if context.best_fitness >= threshold else None


@register("stopping", "stagnation")
def stagnation(context: StopContext, generations: int) -> str | None:
    """Stop if the best fitness hasn't improved in ``generations`` generations (structure-based)."""
    if context.generation - context.best_generation >= generations:
        return "stagnation"
    return None
