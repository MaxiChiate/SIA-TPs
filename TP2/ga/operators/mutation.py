"""Mutation: perturb an individual's alleles.

The engine calls every mutation operator unconditionally on every child each
generation (unlike crossover, which the engine itself gates by ``pc``) - see
``EngineConfig.pm``'s own "meaning depends on the operator" docstring. So each
operator here reads ``pm`` from ``params`` and decides for itself how it gates
its own randomness.
"""

from __future__ import annotations

from ..core.individual import Individual
from ..core.rng import Rng
from ..registry import register


def _pm(params: dict) -> float:
    return params.get("pm", 0.0)


@register("mutation", "gene")
def gene(individual: Individual, rng: Rng, params: dict) -> Individual:
    """With probability ``pm``, replace one randomly chosen gene's value."""
    if rng.random() >= _pm(params):
        return individual  # already a fresh object (crossover never aliases a parent)
    schema = individual.schema
    locus = rng.randrange(len(schema))
    alleles = list(individual.alleles)
    alleles[locus] = schema[locus].random_value(rng)
    return individual.with_alleles(alleles)


@register("mutation", "multigene")
def multigene(individual: Individual, rng: Rng, params: dict) -> Individual:
    """Each gene independently mutates (uniform replacement) with probability ``pm``."""
    pm = _pm(params)
    schema = individual.schema
    alleles = list(individual.alleles)
    for locus in range(len(alleles)):
        if rng.random() < pm:
            alleles[locus] = schema[locus].random_value(rng)
    return individual.with_alleles(alleles)


@register("mutation", "uniform")
def uniform(individual: Individual, rng: Rng, params: dict) -> Individual:
    """Each block independently mutates (every gene in it re-randomized) with probability ``pm``.

    Block-granular counterpart to ``multigene``'s locus granularity: for the
    triangles problem this re-randomizes whole triangles rather than single
    coordinates/colour channels. ``params={"granularity": "allele"}`` collapses
    it to per-locus (equivalent to ``multigene``).
    """
    pm = _pm(params)
    schema = individual.schema
    block_size = 1 if params.get("granularity") == "allele" else schema.block_size
    alleles = list(individual.alleles)
    for start in range(0, len(schema), block_size):
        if rng.random() < pm:
            for locus in range(start, start + block_size):
                alleles[locus] = schema[locus].random_value(rng)
    return individual.with_alleles(alleles)


@register("mutation", "non_uniform")
def non_uniform(individual: Individual, rng: Rng, params: dict) -> Individual:
    """Each gene independently perturbs (not replaces) with probability ``pm``.

    Delta shrinks as the run progresses (Michalewicz's non-uniform mutation):
    ``delta = sign * span * (1 - generation/max_generations)**b * U(0,1)``, so
    early mutations roam broadly and late ones fine-tune. ``b`` (default 2) is
    this operator's own shape parameter, from ``params["b"]``.
    """
    pm = _pm(params)
    b = params.get("b", 2.0)
    generation = params.get("generation", 0)
    max_generations = max(params.get("max_generations", 1), 1)
    progress = min(generation / max_generations, 1.0)
    shrink = (1.0 - progress) ** b

    schema = individual.schema
    alleles = list(individual.alleles)
    for locus, value in enumerate(alleles):
        if rng.random() < pm:
            gene_spec = schema[locus]
            span = gene_spec.upper - gene_spec.lower
            sign = 1.0 if rng.random() < 0.5 else -1.0
            delta = sign * span * shrink * rng.random()
            alleles[locus] = gene_spec.clamp(value + delta)
    return individual.with_alleles(alleles)
