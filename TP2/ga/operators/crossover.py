"""Crossover: recombine two parents into two children.

Cut points default to multiples of ``schema.block_size`` (so a triangle's 10
genes never get split across children); pass ``params={"granularity": "allele"}``
per-operator to cut at any locus instead.
"""

from __future__ import annotations

from ..core.individual import Individual
from ..core.rng import Rng
from ..registry import register


def _cut_candidates(length: int, block_size: int, granularity: str) -> list[int]:
    """Valid interior cut-point indices, 1..length-1."""
    if granularity == "allele":
        return list(range(1, length))
    return list(range(block_size, length, block_size))


def _cut_points(individual: Individual, count: int, rng: Rng, params: dict) -> list[int]:
    schema = individual.schema
    granularity = params.get("granularity", "block")
    candidates = _cut_candidates(len(schema), schema.block_size, granularity)
    if len(candidates) < count:
        raise ValueError(
            f"schema has only {len(candidates)} valid cut point(s) for "
            f"granularity={granularity!r}, need {count}"
        )
    return sorted(rng.sample(candidates, count))


def _swap_segment(a: list[float], b: list[float], start: int, end: int) -> None:
    a[start:end], b[start:end] = b[start:end], a[start:end]


@register("crossover", "one_point")
def one_point(
    parent_a: Individual, parent_b: Individual, rng: Rng, params: dict
) -> tuple[Individual, Individual]:
    (cut,) = _cut_points(parent_a, 1, rng, params)
    child_a = list(parent_a.alleles)
    child_b = list(parent_b.alleles)
    _swap_segment(child_a, child_b, cut, len(child_a))
    return parent_a.with_alleles(child_a), parent_b.with_alleles(child_b)


@register("crossover", "two_point")
def two_point(
    parent_a: Individual, parent_b: Individual, rng: Rng, params: dict
) -> tuple[Individual, Individual]:
    first, second = _cut_points(parent_a, 2, rng, params)
    child_a = list(parent_a.alleles)
    child_b = list(parent_b.alleles)
    _swap_segment(child_a, child_b, first, second)
    return parent_a.with_alleles(child_a), parent_b.with_alleles(child_b)


@register("crossover", "uniform")
def uniform(
    parent_a: Individual, parent_b: Individual, rng: Rng, params: dict
) -> tuple[Individual, Individual]:
    """Swap each block (or each allele, with ``granularity="allele"``) with probability 0.5."""
    granularity = params.get("granularity", "block")
    schema = parent_a.schema
    block_size = schema.block_size if granularity == "block" else 1
    child_a = list(parent_a.alleles)
    child_b = list(parent_b.alleles)
    for start in range(0, len(schema), block_size):
        if rng.random() < 0.5:
            _swap_segment(child_a, child_b, start, start + block_size)
    return parent_a.with_alleles(child_a), parent_b.with_alleles(child_b)


@register("crossover", "ring")
def ring(
    parent_a: Individual, parent_b: Individual, rng: Rng, params: dict
) -> tuple[Individual, Individual]:
    """Anular: pick a random start block and a random run length, swap that wrap-around arc.

    Like one-point crossover but the cut need not start at locus 0, at the cost
    of the swapped segment possibly wrapping past the end of the genotype.
    """
    schema = parent_a.schema
    granularity = params.get("granularity", "block")
    block_size = schema.block_size if granularity == "block" else 1
    blocks = len(schema) // block_size

    child_a = list(parent_a.alleles)
    child_b = list(parent_b.alleles)
    if blocks > 1:
        start_block = rng.randrange(blocks)
        span_blocks = rng.randint(1, blocks - 1)
        for offset in range(span_blocks):
            block_index = (start_block + offset) % blocks
            s = block_index * block_size
            _swap_segment(child_a, child_b, s, s + block_size)
    return parent_a.with_alleles(child_a), parent_b.with_alleles(child_b)
