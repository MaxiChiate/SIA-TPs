"""The single seeded RNG for a run, injected into the engine and every operator.

Same seed + same config must always produce the same result, so no code may call
the ``random`` module functions directly: everything draws from this one instance.
"""

from __future__ import annotations

import random

# The engine and operators only need the ``random.Random`` API (``random``,
# ``uniform``, ``gauss``, ``choice``, ``sample``, ``shuffle``), so we alias it
# rather than wrapping it.
Rng = random.Random


def make_rng(seed: int) -> Rng:
    """Build the one RNG instance for a run from an integer seed."""
    return random.Random(seed)
