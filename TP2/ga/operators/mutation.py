"""Mutation: perturb an individual's alleles.

The engine calls every mutation operator unconditionally on every child each
generation (unlike crossover, which the engine itself gates by ``pc``) - see
``EngineConfig.pm``'s own "meaning depends on the operator" docstring. So each
operator here reads its rate from ``params`` and decides for itself how it
gates its own randomness.

That rate can be given two ways, and which one to use depends on whether the
genotype's length is fixed for the whole study:

``pm``                   the probability of each individual roll. Every
                         operator but ``gene`` rolls once per locus (or per
                         block), so the expected *number* of mutations per
                         child is ``pm * genome_length`` - it grows when the
                         genotype does.
``mutations_per_child``  the expected number of mutations directly, converted
                         to a per-roll probability against however many rolls
                         this operator will make. Invariant to genome length.

The second exists because the first is a trap when the genotype's length is
itself a parameter of the study. Measured on the triangles problem (10 alleles
per triangle, 1000 generations, argentina.png): going from 50 to 500 triangles
at a fixed ``pm=0.05`` took the mutation load from ~25 to ~250 loci per child
and made the result *worse* (RMSE 16,7 -> 18,6), because a child differing from
its parent in 250 places gives selection nothing it can attribute. Holding the
count at 25 instead, the extra capacity finally pays: RMSE 16,7 -> 15,3.

A "mutation" is counted in whatever unit the operator rolls in: a locus for
``multigene`` and ``non_uniform``, a whole block for ``uniform``. ``gene``
mutates at most one locus by construction, so it has nothing to normalize and
reads ``pm`` only.
"""

from __future__ import annotations

from ..core.individual import Individual
from ..core.rng import Rng
from ..registry import register


def _pm(params: dict) -> float:
    return params.get("pm", 0.0)


def _rate(params: dict, rolls: int) -> float:
    """Per-roll probability, from either ``pm`` or ``mutations_per_child``.

    ``rolls`` is how many independent chances this operator is about to take
    (one per locus, or one per block). ``mutations_per_child`` wins when both
    are present: asking for a fixed number of mutations is a strictly more
    specific request than asking for a probability.
    """
    target = params.get("mutations_per_child")
    if target is None:
        return _pm(params)
    if target < 0:
        raise ValueError(f"mutations_per_child must be >= 0, got {target}")
    if rolls <= 0:
        return 0.0
    return min(1.0, target / rolls)


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
    schema = individual.schema
    alleles = list(individual.alleles)
    pm = _rate(params, len(alleles))
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
    schema = individual.schema
    block_size = 1 if params.get("granularity") == "allele" else schema.block_size
    alleles = list(individual.alleles)
    starts = range(0, len(schema), block_size)
    pm = _rate(params, len(starts))
    for start in starts:
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
    b = params.get("b", 2.0)
    generation = params.get("generation", 0)
    max_generations = max(params.get("max_generations", 1), 1)
    progress = min(generation / max_generations, 1.0)
    shrink = (1.0 - progress) ** b

    schema = individual.schema
    alleles = list(individual.alleles)
    pm = _rate(params, len(alleles))
    for locus, value in enumerate(alleles):
        if rng.random() < pm:
            gene_spec = schema[locus]
            span = gene_spec.upper - gene_spec.lower
            sign = 1.0 if rng.random() < 0.5 else -1.0
            delta = sign * span * shrink * rng.random()
            alleles[locus] = gene_spec.clamp(value + delta)
    return individual.with_alleles(alleles)
