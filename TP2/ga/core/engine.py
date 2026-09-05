"""The generational GA loop.

``Engine.run`` wires together operators that are already resolved to callables
(the name->callable registry is block 2, and the engine never touches it):

    parent selection  ->  crossover (prob. Pc)  ->  mutation  ->  survival

The single injected ``Rng`` is threaded through those steps in that fixed order,
so the same seed and config always reproduce the same run.
"""

from __future__ import annotations

import multiprocessing as mp
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from ..metrics import GenerationRecord, record_for
from .individual import Individual
from .population import Population
from .problem import Problem
from .rng import Rng

# Set by ``_init_worker`` once per worker process (spawned fresh, so this
# module-level global is never shared across processes). Lets pool workers
# call ``problem.evaluate`` without re-sending the problem on every task.
_worker_problem: Problem | None = None


def _init_worker(problem: Problem) -> None:
    global _worker_problem
    _worker_problem = problem


def _worker_evaluate(individuals: list[Individual]) -> list[float]:
    assert _worker_problem is not None, "worker pool not initialized with a problem"
    return _worker_problem.evaluate_batch(individuals)

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
    """Wraps ``problem.evaluate`` with per-individual fitness caching and an
    evaluation counter.

    Fitness is cached on the individual itself, so re-evaluating the same
    object (e.g. a survivor carried into the next generation) is free.
    ``count`` only rises on real calls to ``problem.evaluate``. There is no
    genotype -> fitness memo across individuals: genes are continuous, so two
    distinct individuals essentially never share an exact genotype, and such
    a memo would grow without bound over a long run instead of ever paying
    off.

    Every path goes through ``problem.evaluate_batch``: a generation's pending
    individuals are handed over in one call, so a problem that can amortise
    setup or parallelise internally gets the chance to. The default
    ``evaluate_batch`` just loops, which is exactly the old behaviour.

    With ``workers > 1``, ``evaluate_all`` splits that batch across a
    persistent process pool - one chunk per worker, so a generation costs one
    round-trip per worker rather than one per individual. A problem that
    reports ``owns_parallelism()`` gets no pool at all: stacking processes on
    top of a problem's own threads only oversubscribes the CPU.
    """

    def __init__(self, problem: Problem, workers: int = 1) -> None:
        self._problem = problem
        self.count = 0
        self._pool = None
        self._workers = workers
        if workers > 1 and problem.owns_parallelism():
            self._workers = 1
        elif workers > 1:
            ctx = mp.get_context("spawn")
            self._pool = ctx.Pool(
                processes=workers, initializer=_init_worker, initargs=(problem,)
            )

    def evaluate_all(self, individuals: Sequence[Individual]) -> None:
        # Group by genotype so identical individuals within this batch are only
        # evaluated once. Crossover and mutation make duplicates vanishingly
        # rare (measured: 0 in 4100 children over 40 generations), but ``elite``
        # parent selection emits each winner twice, and a pair crossed with
        # itself yields children identical to the parent - so the guard earns
        # its ~0.4 ms per generation on exactly the configs that need it.
        groups: dict[tuple[float, ...], list[Individual]] = {}
        for individual in individuals:
            if individual.fitness is not None:
                continue
            groups.setdefault(individual.key(), []).append(individual)

        if not groups:
            return

        representatives = [group[0] for group in groups.values()]
        values = self._evaluate_batch(representatives)
        self.count += len(representatives)
        for group, value in zip(groups.values(), values):
            for member in group:
                member.fitness = value

    def _evaluate_batch(self, representatives: list[Individual]) -> list[float]:
        if self._pool is None:
            return self._problem.evaluate_batch(representatives)
        # One chunk per worker per generation: per-individual work is uniform
        # (render + MSE at a fixed resolution), so finer-grained chunks buy
        # nothing and cost extra IPC round-trips.
        size = -(-len(representatives) // self._workers)  # ceil division
        chunks = [
            representatives[start : start + size]
            for start in range(0, len(representatives), size)
        ]
        return [value for chunk in self._pool.map(_worker_evaluate, chunks) for value in chunk]

    def close(self) -> None:
        """Shut down the process pool, if any. Safe to call more than once."""
        if self._pool is not None:
            self._pool.close()
            self._pool.join()
            self._pool = None


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
    workers: int = 1  # individuals per generation evaluated in parallel processes
    seed_individual: Individual | None = None  # replaces one random individual at gen 0

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
        if self.workers <= 0:
            raise ValueError(f"workers must be > 0, got {self.workers}")


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
        self._evaluator = Evaluator(problem, workers=config.workers)

    def run(
        self, on_generation: Callable[[Population], None] | None = None
    ) -> RunResult:
        """Run to a stopping criterion. ``on_generation``, if given, is called
        with each fully-evaluated ``Population`` (including the initial one at
        generation 0) - e.g. for a caller to print progress or snapshot the
        current best individual, without the engine knowing anything about it.
        """
        try:
            return self._run(on_generation)
        finally:
            self._evaluator.close()

    def _run(
        self, on_generation: Callable[[Population], None] | None
    ) -> RunResult:
        cfg = self._config
        started = time.perf_counter()

        random_count = cfg.n - (1 if cfg.seed_individual is not None else 0)
        individuals = [
            self._problem.random_individual(self._rng) for _ in range(random_count)
        ]
        if cfg.seed_individual is not None:
            individuals.append(cfg.seed_individual.copy())
        population = Population(individuals=individuals, generation=0)
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
