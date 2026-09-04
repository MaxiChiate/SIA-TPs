"""The generational GA loop.

``Engine.run`` wires together operators that are already resolved to callables
(the name->callable registry is block 2, and the engine never touches it):

    parent selection  ->  crossover (prob. Pc)  ->  mutation  ->  survival

The single injected ``Rng`` is threaded through those steps in that fixed order,
so the same seed and config always reproduce the same run.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from ..metrics import GenerationRecord, record_for
from .individual import Individual
from .population import Population
from .problem import Problem
from .rng import Rng

# ----------------------------------------------------------------------------
# Operator call signatures. Concrete implementations arrive in ga.operators.
# ``params`` carries per-call context the engine fills in each generation
# (``generation``, ``max_generations``, ``history``, ``pm``, ``pc``, plus
# anything from ``EngineConfig.extra_params``); Boltzmann selection and
# non-uniform mutation read it.
# ----------------------------------------------------------------------------
ParentSelection = Callable[[Population, int, Rng, dict], list[Individual]]
Crossover = Callable[[Individual, Individual, Rng, dict], "tuple[Individual, Individual]"]
Mutation = Callable[[Individual, Rng, dict], Individual]
Survival = Callable[[list[Individual], list[Individual], int, Rng, dict], list[Individual]]
Stopping = Callable[["StopContext"], "str | None"]


@dataclass(frozen=True, slots=True)
class StopContext:
    """Everything a stopping criterion may inspect (all criteria OR together)."""

    generation: int
    max_generations: int
    elapsed_seconds: float
    evaluations: int
    history: tuple[GenerationRecord, ...]
    best_fitness: float
    best_generation: int


class Evaluator:
    """Wraps ``problem.evaluate`` with a genotype memo and an evaluation counter.

    Fitness is cached twice: on the individual itself, and in a shared
    ``genotype -> fitness`` dict so a regenerated identical genotype is free.
    ``count`` only rises on real calls to ``problem.evaluate``.
    """

    def __init__(self, problem: Problem) -> None:
        self._problem = problem
        self._memo: dict[tuple[float, ...], float] = {}
        self.count = 0

    def evaluate(self, individual: Individual) -> float:
        if individual.fitness is not None:
            return individual.fitness
        key = individual.key()
        cached = self._memo.get(key)
        if cached is not None:
            individual.fitness = cached
            return cached
        value = self._problem.evaluate(individual)
        self.count += 1
        self._memo[key] = value
        individual.fitness = value
        return value

    def evaluate_all(self, individuals: Sequence[Individual]) -> None:
        for individual in individuals:
            self.evaluate(individual)

    @property
    def cache_size(self) -> int:
        return len(self._memo)


@dataclass(slots=True)
class EngineConfig:
    """Resolved hyper-parameters for one run."""

    n: int  # population size
    k: int  # offspring per generation
    pc: float  # recombination probability
    pm: float  # mutation probability (meaning depends on the mutation operator)
    max_generations: int
    parent_selection: ParentSelection
    crossover: Crossover
    mutation: Mutation
    survival: Survival
    stopping: Stopping | None = None
    extra_params: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.n <= 0:
            raise ValueError(f"n must be > 0, got {self.n}")
        if self.k <= 0:
            raise ValueError(f"k must be > 0, got {self.k}")
        if not 0.0 <= self.pc <= 1.0:
            raise ValueError(f"pc must be in [0, 1], got {self.pc}")
        if not 0.0 <= self.pm <= 1.0:
            raise ValueError(f"pm must be in [0, 1], got {self.pm}")
        if self.max_generations <= 0:
            raise ValueError(
                f"max_generations must be > 0, got {self.max_generations}"
            )


@dataclass(slots=True)
class RunResult:
    """The outcome of ``Engine.run``: the best individual and the full history."""

    best: Individual
    best_generation: int
    stop_reason: str
    generations: int
    evaluations: int
    elapsed_seconds: float
    history: list[GenerationRecord]


def _fitness(individual: Individual) -> float:
    if individual.fitness is None:
        raise RuntimeError("individual reached the loop unevaluated")
    return individual.fitness


class Engine:
    """Runs one GA from an initial random population to a stopping criterion."""

    def __init__(self, problem: Problem, config: EngineConfig, rng: Rng) -> None:
        self._problem = problem
        self._config = config
        self._rng = rng
        self._evaluator = Evaluator(problem)

    def run(
        self, on_generation: Callable[[Population], None] | None = None
    ) -> RunResult:
        """Run to a stopping criterion. ``on_generation``, if given, is called
        with each fully-evaluated ``Population`` (including the initial one at
        generation 0) - e.g. for a caller to print progress or snapshot the
        current best individual, without the engine knowing anything about it.
        """
        cfg = self._config
        started = time.perf_counter()

        population = Population(
            individuals=[
                self._problem.random_individual(self._rng) for _ in range(cfg.n)
            ],
            generation=0,
        )
        self._evaluator.evaluate_all(population.individuals)

        history: list[GenerationRecord] = [
            record_for(
                population, self._evaluator.count, time.perf_counter() - started
            )
        ]
        best = population.best().copy()
        best_generation = 0
        if on_generation is not None:
            on_generation(population)

        stop_reason = self._check_stop(population, history, best, best_generation, started)
        while stop_reason is None:
            population = self._advance(population, history)
            history.append(
                record_for(
                    population, self._evaluator.count, time.perf_counter() - started
                )
            )

            generation_best = population.best()
            if _fitness(generation_best) > _fitness(best):
                best = generation_best.copy()
                best_generation = population.generation

            if on_generation is not None:
                on_generation(population)

            stop_reason = self._check_stop(
                population, history, best, best_generation, started
            )

        return RunResult(
            best=best,
            best_generation=best_generation,
            stop_reason=stop_reason,
            generations=population.generation,
            evaluations=self._evaluator.count,
            elapsed_seconds=time.perf_counter() - started,
            history=history,
        )

    # -- one generation -------------------------------------------------------

    def _advance(
        self, population: Population, history: list[GenerationRecord]
    ) -> Population:
        cfg = self._config
        params = self._params(population.generation, history)

        parents = cfg.parent_selection(population, 2 * cfg.k, self._rng, params)
        if len(parents) < 2:
            raise RuntimeError(
                f"parent selection returned {len(parents)} individuals, need >= 2"
            )

        children = self._breed(parents, params)
        self._evaluator.evaluate_all(children)

        survivors = cfg.survival(
            population.individuals, children, cfg.n, self._rng, params
        )
        if len(survivors) != cfg.n:
            raise RuntimeError(
                f"survival returned {len(survivors)} individuals, expected {cfg.n}"
            )
        self._evaluator.evaluate_all(survivors)
        return Population(
            individuals=list(survivors), generation=population.generation + 1
        )

    def _breed(
        self, parents: Sequence[Individual], params: dict
    ) -> list[Individual]:
        cfg = self._config
        children: list[Individual] = []
        pair_index = 0
        while len(children) < cfg.k:
            parent_a = parents[(2 * pair_index) % len(parents)]
            parent_b = parents[(2 * pair_index + 1) % len(parents)]
            pair_index += 1

            if self._rng.random() < cfg.pc:
                child_a, child_b = cfg.crossover(
                    parent_a, parent_b, self._rng, params
                )
            else:
                child_a, child_b = parent_a.copy(), parent_b.copy()

            children.append(cfg.mutation(child_a, self._rng, params))
            if len(children) < cfg.k:
                children.append(cfg.mutation(child_b, self._rng, params))
        return children

    # -- stopping -----------------------------------------------------------

    def _params(self, generation: int, history: list[GenerationRecord]) -> dict:
        params = dict(self._config.extra_params)
        params.update(
            generation=generation,
            max_generations=self._config.max_generations,
            history=tuple(history),
            pm=self._config.pm,
            pc=self._config.pc,
        )
        return params

    def _check_stop(
        self,
        population: Population,
        history: list[GenerationRecord],
        best: Individual,
        best_generation: int,
        started: float,
    ) -> str | None:
        cfg = self._config
        if population.generation >= cfg.max_generations:
            return "max_generations"
        if cfg.stopping is None:
            return None
        context = StopContext(
            generation=population.generation,
            max_generations=cfg.max_generations,
            elapsed_seconds=time.perf_counter() - started,
            evaluations=self._evaluator.count,
            history=tuple(history),
            best_fitness=_fitness(best),
            best_generation=best_generation,
        )
        return cfg.stopping(context) or None
