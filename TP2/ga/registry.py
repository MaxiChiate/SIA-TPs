"""Name -> callable registry, so a JSON config can select operators by string name.

Each operator module (``ga.operators.*``, ``problems.triangles``, ...) registers its
implementations here as an import-time side effect, via the ``register`` decorator.
``ga.config`` never imports an operator module directly by name; it only looks
things up here, so adding a new operator never touches ``config.py``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T", bound=Callable)

# Every category config.py knows how to resolve. "problem" holds factories
# (dict of params -> Problem instance) rather than GA operators, but shares the
# same name -> callable lookup mechanism.
_CATEGORIES = (
    "parent_selection",
    "crossover",
    "mutation",
    "survival",
    "stopping",
    "problem",
)

_registry: dict[str, dict[str, Callable]] = {category: {} for category in _CATEGORIES}


class RegistryError(Exception):
    """Unknown category, unknown operator name, or a duplicate registration."""


def register(category: str, name: str) -> Callable[[T], T]:
    """Decorator: register ``fn`` under ``category``/``name``.

    Usage: ``@register("parent_selection", "tournament")`` on the function itself.
    """
    if category not in _registry:
        raise RegistryError(f"unknown operator category {category!r}")

    def decorator(fn: T) -> T:
        if name in _registry[category]:
            raise RegistryError(f"{category}/{name} is already registered")
        _registry[category][name] = fn
        return fn

    return decorator


def get(category: str, name: str) -> Callable:
    """Look up a previously registered operator by category and name."""
    if category not in _registry:
        raise RegistryError(f"unknown operator category {category!r}")
    try:
        return _registry[category][name]
    except KeyError:
        available_names = ", ".join(sorted(_registry[category])) or "(none registered)"
        raise RegistryError(
            f"unknown {category} operator {name!r}; available: {available_names}"
        ) from None


def available(category: str) -> tuple[str, ...]:
    """Registered operator names for ``category``, for error messages or docs."""
    if category not in _registry:
        raise RegistryError(f"unknown operator category {category!r}")
    return tuple(sorted(_registry[category]))
