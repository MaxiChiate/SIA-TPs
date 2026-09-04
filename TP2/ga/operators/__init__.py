"""Concrete GA operators. Importing this package registers all of them in
``ga.registry`` as a side effect - ``ga.config.load_config`` needs this import to
have happened before it can resolve any operator by name.
"""

from __future__ import annotations

from . import crossover, mutation, selection, stopping, survival

__all__ = ["crossover", "mutation", "selection", "stopping", "survival"]
