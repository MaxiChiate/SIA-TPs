"""Importing this package registers ``TrianglesProblem`` in ``ga.registry`` under
``problem/triangles`` as a side effect - ``ga.config.load_config`` needs this
import to have happened before it can resolve ``"type": "triangles"`` by name.
"""

from __future__ import annotations

from . import export, problem

__all__ = ["export", "problem"]
