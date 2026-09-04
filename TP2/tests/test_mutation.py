"""Unit tests for ``ga.operators.mutation``."""

from __future__ import annotations

import pytest

from conftest import ScriptedRandom, make_individual
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
