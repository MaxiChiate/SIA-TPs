"""Unit tests for ``ga.core.engine.Evaluator``: the batch-evaluation seam.

The engine hands a whole generation to ``Problem.evaluate_batch`` in one call, so
a problem can amortise setup or parallelise inside itself. These tests pin the
contract that surrounds that call: what reaches the problem, what never does,
and what the evaluation counter means.
"""

from __future__ import annotations

from collections.abc import Sequence

from conftest import make_individual
from ga.core.engine import Evaluator
from ga.core.gene import Gene, GeneSchema
from ga.core.individual import Individual
from ga.core.problem import Problem


class RecordingProblem(Problem):
    """A ``Problem`` that scores an individual by its first allele and records
    every batch it was handed."""

    def __init__(self, parallel: bool = False) -> None:
        self.batches: list[list[list[float]]] = []
        self._parallel = parallel

    def schema(self) -> GeneSchema:  # pragma: no cover - unused by these tests
        return GeneSchema(genes=(Gene("g0", 0.0, 1.0),))

    def random_individual(self, rng) -> Individual:  # pragma: no cover - unused
        raise NotImplementedError

    def evaluate(self, individual: Individual) -> float:
        return individual.alleles[0]

    def evaluate_batch(self, individuals: Sequence[Individual]) -> list[float]:
        self.batches.append([list(i.alleles) for i in individuals])
        return [self.evaluate(individual) for individual in individuals]

    def owns_parallelism(self) -> bool:
        return self._parallel


def _individuals(schema: GeneSchema, rows: list[list[float]]) -> list[Individual]:
    return [make_individual(schema, alleles=row) for row in rows]


# -- batching ----------------------------------------------------------------


def test_a_generation_reaches_the_problem_as_one_batch(schema):
    problem = RecordingProblem()
    evaluator = Evaluator(problem)
    individuals = _individuals(schema, [[0.1] * 6, [0.2] * 6, [0.3] * 6])

    evaluator.evaluate_all(individuals)

    assert len(problem.batches) == 1
    assert [i.fitness for i in individuals] == [0.1, 0.2, 0.3]
    assert evaluator.count == 3


def test_already_evaluated_individuals_never_reach_the_problem(schema):
    """A survivor carried into the next generation keeps its cached fitness, so
    re-rendering it would be pure waste."""
    problem = RecordingProblem()
    evaluator = Evaluator(problem)
    survivor = make_individual(schema, alleles=[0.9] * 6, fitness=0.42)
    fresh = make_individual(schema, alleles=[0.1] * 6)

    evaluator.evaluate_all([survivor, fresh])

    assert problem.batches == [[[0.1] * 6]]
    assert survivor.fitness == 0.42  # untouched, not recomputed as 0.9
    assert evaluator.count == 1


def test_nothing_is_called_when_every_individual_is_already_evaluated(schema):
    problem = RecordingProblem()
    evaluator = Evaluator(problem)
    evaluator.evaluate_all([make_individual(schema, alleles=[0.5] * 6, fitness=1.0)])
    assert problem.batches == []
    assert evaluator.count == 0


# -- deduplication -----------------------------------------------------------


def test_identical_genotypes_are_evaluated_once_and_share_the_result(schema):
    """``elite`` parent selection emits each winner twice, and a pair crossed
    with itself yields children identical to the parent."""
    problem = RecordingProblem()
    evaluator = Evaluator(problem)
    twins = _individuals(schema, [[0.7] * 6, [0.7] * 6, [0.2] * 6])

    evaluator.evaluate_all(twins)

    assert problem.batches == [[[0.7] * 6, [0.2] * 6]]
    assert [i.fitness for i in twins] == [0.7, 0.7, 0.2]
    assert evaluator.count == 2  # distinct genotypes, not individuals


def test_results_are_matched_back_by_position(schema):
    """Guards the zip between the representatives sent out and the values that
    come back: a reordering here would silently hand fitnesses to the wrong
    individuals."""
    problem = RecordingProblem()
    evaluator = Evaluator(problem)
    individuals = _individuals(schema, [[0.4] * 6, [0.1] * 6, [0.9] * 6, [0.1] * 6])

    evaluator.evaluate_all(individuals)

    assert [i.fitness for i in individuals] == [0.4, 0.1, 0.9, 0.1]


# -- parallelism ownership ---------------------------------------------------


def test_a_problem_that_owns_parallelism_gets_no_process_pool():
    """Stacking a process pool on top of a problem's own threads only
    oversubscribes the CPU."""
    evaluator = Evaluator(RecordingProblem(parallel=True), workers=8)
    assert evaluator._pool is None
    evaluator.close()


def test_close_is_safe_without_a_pool():
    evaluator = Evaluator(RecordingProblem())
    evaluator.close()
    evaluator.close()
