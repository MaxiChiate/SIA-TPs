"""Core GA abstractions: genes, individuals, population, the problem interface, the engine."""

from __future__ import annotations

from .engine import (
    Engine,
    EngineConfig,
    Evaluator,
    RunResult,
    StopContext,
)
from .gene import Gene, GeneKind, GeneSchema
from .individual import Individual
from .population import Population
from .problem import Problem
from .rng import Rng, make_rng

__all__ = [
    "Engine",
    "EngineConfig",
    "Evaluator",
    "Gene",
    "GeneKind",
    "GeneSchema",
    "Individual",
    "Population",
    "Problem",
    "Rng",
    "RunResult",
    "StopContext",
    "make_rng",
]
