"""Unit tests for ``ga.operators.crossover``.

``PARENT_A``/``PARENT_B`` give every locus a distinct value, so a swapped
segment (or a block that got split when it shouldn't have) is visible directly
in the resulting allele list.
"""

from __future__ import annotations

import pytest

from conftest import ScriptedRandom, make_individual
from ga.core.gene import Gene, GeneSchema
from ga.operators.crossover import one_point, ring, two_point, uniform

PARENT_A = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
PARENT_B = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0]


def _parents(schema):
    return (
        make_individual(schema, alleles=PARENT_A),
        make_individual(schema, alleles=PARENT_B),
    )


def _single_block_schema() -> GeneSchema:
    """1 block covering the whole genotype: no valid interior block cut point."""
    genes = tuple(Gene(f"g{i}", 0.0, 1.0) for i in range(3))
    return GeneSchema(genes=genes, block_size=3)


# -- one_point -----------------------------------------------------------


def test_one_point_never_splits_a_block(schema):
    parent_a, parent_b = _parents(schema)
    rng = ScriptedRandom(sample=[[2]])  # only cut candidates are {2, 4}
    child_a, child_b = one_point(parent_a, parent_b, rng, {})
    assert child_a.alleles == [0.0, 1.0, 12.0, 13.0, 14.0, 15.0]
    assert child_b.alleles == [10.0, 11.0, 2.0, 3.0, 4.0, 5.0]
    assert child_a.fitness is None
    assert child_b.fitness is None


def test_one_point_allele_granularity_can_split_a_block(schema):
    parent_a, parent_b = _parents(schema)
    rng = ScriptedRandom(sample=[[3]])  # mid-block cut, invalid at block granularity
    child_a, _ = one_point(parent_a, parent_b, rng, {"granularity": "allele"})
    assert child_a.alleles == [0.0, 1.0, 2.0, 13.0, 14.0, 15.0]


# -- two_point -------------------------------------------------------------


def test_two_point_swaps_the_middle_block(schema):
    parent_a, parent_b = _parents(schema)
    # the only 2-cut combination on block boundaries {2, 4} is (2, 4) itself
    rng = ScriptedRandom(sample=[[2, 4]])
    child_a, child_b = two_point(parent_a, parent_b, rng, {})
    assert child_a.alleles == [0.0, 1.0, 12.0, 13.0, 4.0, 5.0]
    assert child_b.alleles == [10.0, 11.0, 2.0, 3.0, 14.0, 15.0]


def test_two_point_rejects_too_few_cut_candidates():
    schema = _single_block_schema()
    parent_a = make_individual(schema, alleles=[0.0, 1.0, 2.0])
    parent_b = make_individual(schema, alleles=[10.0, 11.0, 12.0])
    with pytest.raises(ValueError):
        two_point(parent_a, parent_b, ScriptedRandom(), {})


# -- uniform -----------------------------------------------------------------


def test_uniform_block_swaps_per_block_coin_flip(schema):
    parent_a, parent_b = _parents(schema)
    rng = ScriptedRandom(random=[0.1, 0.9, 0.2])  # swap block0, keep block1, swap block2
    child_a, child_b = uniform(parent_a, parent_b, rng, {})
    assert child_a.alleles == [10.0, 11.0, 2.0, 3.0, 14.0, 15.0]
    assert child_b.alleles == [0.0, 1.0, 12.0, 13.0, 4.0, 5.0]


def test_uniform_allele_granularity_swaps_per_locus(schema):
    parent_a, parent_b = _parents(schema)
    rng = ScriptedRandom(random=[0.1, 0.9, 0.1, 0.9, 0.1, 0.9])
    child_a, _ = uniform(parent_a, parent_b, rng, {"granularity": "allele"})
    assert child_a.alleles == [10.0, 1.0, 12.0, 3.0, 14.0, 5.0]


# -- ring ----------------------------------------------------------------------


def test_ring_swaps_a_wraparound_arc(schema):
    parent_a, parent_b = _parents(schema)
    # start_block=2, span_blocks=2 -> swap blocks {2, 0} (wrapping), keep block1
    rng = ScriptedRandom(randrange=[2], randint=[2])
    child_a, child_b = ring(parent_a, parent_b, rng, {})
    assert child_a.alleles == [10.0, 11.0, 2.0, 3.0, 14.0, 15.0]
    assert child_b.alleles == [0.0, 1.0, 12.0, 13.0, 4.0, 5.0]


def test_ring_is_a_noop_with_a_single_block():
    schema = _single_block_schema()
    parent_a = make_individual(schema, alleles=[0.0, 1.0, 2.0])
    parent_b = make_individual(schema, alleles=[10.0, 11.0, 12.0])
    child_a, child_b = ring(parent_a, parent_b, ScriptedRandom(), {})
    assert child_a.alleles == parent_a.alleles
    assert child_b.alleles == parent_b.alleles
