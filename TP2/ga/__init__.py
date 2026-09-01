"""Generic genetic-algorithm engine.

The engine knows nothing about any concrete domain: a problem plugs in by
implementing ``ga.core.problem.Problem`` (gene schema, random individual, fitness).
Nothing outside ``problems/`` may import Pillow or numpy.
"""
