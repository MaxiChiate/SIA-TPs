"""Core GA abstractions: genes, individuals, population, the problem interface, the engine."""

from __future__ import annotations

from .rng import Rng, make_rng

__all__ = [
    "Rng",
    "make_rng",
]
