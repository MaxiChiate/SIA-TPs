"""Unit tests for ``ga.operators.mutation``."""

from __future__ import annotations

import random

import pytest

from conftest import ScriptedRandom, make_individual
from ga.core.gene import Gene, GeneSchema
from ga.operators.mutation import gene, multigene, non_uniform, uniform

# -- gene ------------------------------------------------------------------


def test_gene_mutation_is_a_noop_when_rng_exceeds_pm(schema):
    ind = make_individual(schema, alleles=[0.1] * 6)
    rng = ScriptedRandom(random=[0.5])
    result = gene(ind, rng, {"pm": 0.3})
    assert result is ind


def test_gene_mutation_replaces_one_locus_when_triggered(schema):
    ind = make_individual(schema, alleles=[0.1] * 6)
    rng = ScriptedRandom(random=[0.1], randrange=[3], uniform=[0.9])
    result = gene(ind, rng, {"pm": 0.3})
    assert result.alleles == [0.1, 0.1, 0.1, 0.9, 0.1, 0.1]
    assert result.fitness is None
    assert result is not ind


# -- multigene ---------------------------------------------------------------


def test_multigene_mutates_each_locus_independently(schema):
    ind = make_individual(schema, alleles=[0.1] * 6)
    rng = ScriptedRandom(
        random=[0.1, 0.9, 0.1, 0.9, 0.1, 0.9],
        uniform=[0.2, 0.4, 0.6],
    )
    result = multigene(ind, rng, {"pm": 0.5})
    assert result.alleles == [0.2, 0.1, 0.4, 0.1, 0.6, 0.1]


# -- uniform (block mutation) -------------------------------------------------


def test_uniform_mutation_re_randomizes_whole_blocks(schema):
    ind = make_individual(schema, alleles=[0.1] * 6)
    rng = ScriptedRandom(
        random=[0.1, 0.9, 0.1],
        uniform=[0.2, 0.3, 0.7, 0.8],
    )
    result = uniform(ind, rng, {"pm": 0.5})
    assert result.alleles == [0.2, 0.3, 0.1, 0.1, 0.7, 0.8]


def test_uniform_mutation_allele_granularity_hits_single_loci(schema):
    ind = make_individual(schema, alleles=[0.1] * 6)
    rng = ScriptedRandom(
        random=[0.1, 0.9, 0.9, 0.9, 0.9, 0.9],
        uniform=[0.5],
    )
    result = uniform(ind, rng, {"pm": 0.5, "granularity": "allele"})
    assert result.alleles == [0.5, 0.1, 0.1, 0.1, 0.1, 0.1]


# -- non_uniform ---------------------------------------------------------------


def test_non_uniform_perturbs_instead_of_replacing(schema):
    ind = make_individual(schema, alleles=[0.5] * 6)
    # locus0: gate(0.1<0.5)->mutate, sign(0.9)->negative, magnitude(0.4)
    # loci1-5: gate(0.9)->skip
    rng = ScriptedRandom(random=[0.1, 0.9, 0.4, 0.9, 0.9, 0.9, 0.9, 0.9])
    result = non_uniform(
        ind, rng, {"pm": 0.5, "generation": 0, "max_generations": 1, "b": 2.0}
    )
    assert result.alleles == pytest.approx([0.1, 0.5, 0.5, 0.5, 0.5, 0.5])


def test_non_uniform_shrinks_as_generation_approaches_max(schema):
    ind = make_individual(schema, alleles=[0.5] * 6)
    rng = ScriptedRandom(random=[0.1, 0.9, 1.0, 0.9, 0.9, 0.9, 0.9, 0.9])
    result = non_uniform(
        ind, rng, {"pm": 0.5, "generation": 9, "max_generations": 10, "b": 2.0}
    )
    # progress=0.9 -> shrink=(1-0.9)**2=0.01 -> delta = -span*shrink*1.0 = -0.01
    assert result.alleles[0] == pytest.approx(0.5 - 0.01)
    assert result.alleles[1:] == pytest.approx([0.5] * 5)


def test_non_uniform_clamps_to_gene_domain(schema):
    ind = make_individual(schema, alleles=[0.05] * 6)
    # b=0 -> shrink=1.0 regardless of progress -> delta = -span*1.0*1.0 = -1.0
    rng = ScriptedRandom(random=[0.1, 0.9, 1.0, 0.9, 0.9, 0.9, 0.9, 0.9])
    result = non_uniform(
        ind, rng, {"pm": 0.5, "generation": 0, "max_generations": 1, "b": 0.0}
    )
    assert result.alleles[0] == 0.0


# -- mutations_per_child: rate that survives a change of genome length --------


def _long_schema(loci: int) -> GeneSchema:
    return GeneSchema(
        genes=tuple(Gene(name=f"g{i}", lower=0.0, upper=1.0) for i in range(loci)),
        block_size=2,
    )


@pytest.mark.parametrize("loci", [10, 100])
def test_mutations_per_child_holds_the_count_across_genome_lengths(loci):
    """The whole point: the same request mutates the same number of loci
    whether the genotype has 10 alleles or 100."""
    schema = _long_schema(loci)
    individual = make_individual(schema, alleles=[0.5] * loci)
    rng = random.Random(7)
    params = {"mutations_per_child": 4, "pm": 0.9}

    counts = []
    for _ in range(400):
        mutated = multigene(individual, rng, params)
        counts.append(sum(1 for a, b in zip(individual.alleles, mutated.alleles) if a != b))
    assert 3.4 < sum(counts) / len(counts) < 4.6


def test_mutations_per_child_wins_over_pm():
    """Both present is not an error - the more specific request takes it."""
    schema = _long_schema(100)
    individual = make_individual(schema, alleles=[0.5] * 100)
    rng = random.Random(7)

    mutated = multigene(individual, rng, {"mutations_per_child": 0, "pm": 1.0})
    assert mutated.alleles == individual.alleles


def test_uniform_counts_blocks_not_loci():
    """``uniform`` re-randomizes whole blocks, so its unit of "one mutation" is
    a block - 3 requested out of 5 blocks, not 3 out of 10 loci."""
    schema = _long_schema(10)  # block_size=2 -> 5 blocks
    individual = make_individual(schema, alleles=[0.5] * 10)
    rng = random.Random(7)

    counts = []
    for _ in range(400):
        mutated = uniform(individual, rng, {"mutations_per_child": 3})
        blocks = sum(
            1
            for start in range(0, 10, 2)
            if individual.alleles[start:start + 2] != mutated.alleles[start:start + 2]
        )
        counts.append(blocks)
    assert 2.5 < sum(counts) / len(counts) < 3.5


def test_a_negative_mutation_count_is_rejected():
    schema = _long_schema(10)
    individual = make_individual(schema, alleles=[0.5] * 10)
    with pytest.raises(ValueError, match="mutations_per_child"):
        multigene(individual, random.Random(1), {"mutations_per_child": -1})
