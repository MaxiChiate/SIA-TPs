"""Survival strategies: assemble the pool for generational replacement, then pick
``n`` from it using one of the registered ``parent_selection`` methods.

"Aditiva"/"exclusiva" only decide the *pool* (parents+children, or children only);
picking which ``n`` of that pool survive reuses ``ga.operators.selection`` via the
registry instead of duplicating every selection algorithm a second time.
"""

from __future__ import annotations

from .. import registry
from ..core.individual import Individual
from ..core.population import Population
from ..core.rng import Rng


def _select_from_pool(
    pool: list[Individual], n: int, rng: Rng, params: dict
) -> list[Individual]:
    method_name = params.get("selection_method", "elite")
    selector = registry.get("parent_selection", method_name)
    return selector(Population(individuals=pool), n, rng, params)


@registry.register("survival", "additive")
def additive(
    current: list[Individual],
    children: list[Individual],
    n: int,
    rng: Rng,
    params: dict,
) -> list[Individual]:
    """(mu + lambda): survivors are picked from parents and children together."""
    return _select_from_pool(current + children, n, rng, params)


@registry.register("survival", "exclusive")
def exclusive(
    current: list[Individual],
    children: list[Individual],
    n: int,
    rng: Rng,
    params: dict,
) -> list[Individual]:
    """(mu, lambda): survivors come only from children; the old generation is discarded.

    Requires at least ``n`` children, since there is nothing else to fall back on.
    """
    if len(children) < n:
        raise ValueError(
            f"exclusive survival needs >= {n} children to replace the population, "
            f"got {len(children)} (increase k)"
        )
    return _select_from_pool(children, n, rng, params)
