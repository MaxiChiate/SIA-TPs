"""The stages a run goes through, each usable on its own.

A run used to be one indivisible step: simulate and draw, interleaved. That
made the numbers and the pictures share a stopwatch - ``on_generation``
rendered a full-resolution PNG *inside* the engine's timed loop, so
``summary.json``'s ``elapsed_seconds`` included work that has nothing to do
with the algorithm. Splitting them means a timing run can skip every pixel:

    simulate           config -> history.csv / summary.json / best.json
                                 (+ checkpoints.jsonl, if snapshots are wanted)
    render_final       a finished results dir -> final.png
    render_snapshots   a finished results dir -> snapshots/*.png + progress.gif

``run.py`` still chains all three, so the one-command path is unchanged; the
other scripts are the same functions called separately. Every stage after
``simulate`` reads what it needs from the results directory, so rendering can
happen days later, on another machine, without the config that produced it.

Deferred rendering needs the genotypes the pictures are of, which is what
``checkpoints.jsonl`` holds: one line per snapshot generation, carrying the
raw ``[0, 1]`` allele vector rather than ``figures.json``'s pixel-space
export. That export normalises vertices against the *native* resolution, so
decoding it is only exact for a default-sized export; alleles are
resolution-independent by construction and always decode to the individual
that was actually scored.
"""

from __future__ import annotations

import csv
import dataclasses
import json
import time
from pathlib import Path

import ga.operators  # noqa: F401 -- registers GA operators by name
import problems.triangles  # noqa: F401 -- registers the "triangles" problem
from ga.config import load_config
from ga.core.engine import Engine, RunResult
from ga.core.individual import Individual
from ga.core.population import Population
from ga.metrics import mean as mean_fitness
from problems.triangles import colorspace
from problems.triangles.export import (
    native_resolution,
    save_figures_json,
    save_gif,
    save_image,
)

BEST_FILE = "best.json"
CHECKPOINTS_FILE = "checkpoints.jsonl"
SUMMARY_FILE = "summary.json"
FIGURES_FILE = "figures.json"
FINAL_IMAGE = "final.png"
GIF_FILE = "progress.gif"
SNAPSHOTS_DIR = "snapshots"

# Checkpoints exist to be drawn, never to be scored, so they are rounded: at
# an export width of 4096 px a 1e-8 allele is 4e-5 of a pixel. It cuts the file
# to about half the size of a full-repr dump. ``best.json`` is *not* rounded -
# that one is the run's result, and may be fed back in through ``import``.
CHECKPOINT_DIGITS = 8


def results_dir(config_path: Path, explicit: str | None) -> Path:
    """Where a run writes: ``--out`` if given, else a timestamped directory."""
    if explicit is not None:
        return Path(explicit)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    return Path("results") / f"{config_path.stem}_{stamp}"


# -- stage 1: simulate --------------------------------------------------------


def simulate(
    config_path: Path,
    out_dir: Path,
    snapshot_every: int = 0,
    progress_every: int = 1,
) -> RunResult:
    """Run one config to its stopping criterion and write only data files.

    Draws nothing. ``snapshot_every`` still matters here, because only the
    engine ever sees the intermediate populations: it decides how often the
    generation's best individual is kept for ``render_snapshots`` to draw
    later. Keeping one is a reference, not a copy - operators never mutate an
    individual in place - so checkpointing costs the timed loop nothing.

    ``progress_every`` throttles the per-generation print for the same reason:
    30.000 lines of stdout is not free, and it lands inside ``elapsed_seconds``
    exactly like a render would. 0 silences it.

    ``history.csv``/``history.json`` are skipped when the config's root-level
    ``write_history`` is ``false`` - one row per generation gets heavy on long
    runs, and nothing downstream reads them back (``summary.json`` and
    ``best.json`` are enough to reproduce or re-render a run).
    """
    loaded = load_config(config_path)
    description = loaded.problem.describe()
    out_dir.mkdir(parents=True, exist_ok=True)

    checkpoints: list[tuple[int, Individual]] = []

    def on_generation(population: Population) -> None:
        generation = population.generation
        best = population.best()
        if progress_every > 0 and generation % progress_every == 0:
            print(
                f"gen {generation:5d}  best={best.fitness:.6f}  "
                f"mean={mean_fitness(population.fitnesses()):.6f}"
            )
        if snapshot_every > 0 and generation % snapshot_every == 0:
            checkpoints.append((generation, best))

    engine = Engine(loaded.problem, loaded.engine_config, loaded.rng)
    result = engine.run(on_generation=on_generation)

    if loaded.write_history:
        _write_history(result.history, out_dir)
    _write_summary(result, loaded.raw, description, loaded.seed, out_dir)
    _write_best(result, out_dir)
    save_figures_json(
        result.best,
        description["shape_type"],
        description["shape_count"],
        *export_size(description, None, None),
        out_dir / FIGURES_FILE,
        colorspace.get(description["color_space"]),
    )
    if checkpoints:
        _write_checkpoints(checkpoints, out_dir)
    return result


def _write_history(history: list, out_dir: Path) -> None:
    rows = [dataclasses.asdict(record) for record in history]
    fieldnames = list(rows[0].keys()) if rows else []
    with (out_dir / "history.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    (out_dir / "history.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")


def _write_summary(
    result: RunResult, config: dict, problem: dict, seed: int, out_dir: Path
) -> None:
    """``config`` is what was asked for, ``problem`` is what actually ran.

    They differ wherever the problem resolves something: ``"work_resolution":
    "native"`` becomes the image's pixel size. A run has to record the second
    one, otherwise its numbers cannot be reproduced or compared against another
    run's. The render stages also rebuild the problem from the ``config`` block
    kept here, which is why it is the whole config and not a digest of it.
    """
    summary = {
        "seed": seed,
        "best_fitness": result.best.fitness,
        "best_generation": result.best_generation,
        "stop_reason": result.stop_reason,
        "generations": result.generations,
        "evaluations": result.evaluations,
        "elapsed_seconds": result.elapsed_seconds,
        "problem": problem,
        "config": config,
    }
    (out_dir / SUMMARY_FILE).write_text(json.dumps(summary, indent=2), encoding="utf-8")


def _write_best(result: RunResult, out_dir: Path) -> None:
    """The winning genotype at full precision, for an exact re-render."""
    payload = {
        "generation": result.best_generation,
        "fitness": result.best.fitness,
        "alleles": list(result.best.alleles),
    }
    (out_dir / BEST_FILE).write_text(json.dumps(payload), encoding="utf-8")


def _write_checkpoints(
    checkpoints: list[tuple[int, Individual]], out_dir: Path
) -> None:
    """One JSON object per line, written after the run rather than during it."""
    with (out_dir / CHECKPOINTS_FILE).open("w", encoding="utf-8") as fh:
        for generation, individual in checkpoints:
            fh.write(
                json.dumps(
                    {
                        "generation": generation,
                        "fitness": individual.fitness,
                        "alleles": [
                            round(a, CHECKPOINT_DIGITS) for a in individual.alleles
                        ],
                    }
                )
                + "\n"
            )


# -- reading a finished run back ---------------------------------------------


def load_summary(out_dir: Path) -> dict:
    path = out_dir / SUMMARY_FILE
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} not found - run the simulation first (python simulate.py)"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def rebuild_problem(summary: dict):
    """Reconstruct the run's problem (and therefore its renderer) from its config.

    Deliberately through ``load_config`` on the stored config rather than a
    second construction path: the picture has to be drawn by the same kernel,
    at the same colour space, shape type and shape count, that scored it.
    """
    return load_config(summary["config"]).problem


def export_size(
    description: dict, width: int | None, height: int | None
) -> tuple[int, int]:
    """Export dimensions: whatever was asked for, else the source image's own.

    Both render stages default the same way on purpose - ``progress.gif``
    splices ``final.png`` onto the end of the snapshots, and GIF frames of
    mismatched sizes do not assemble.
    """
    if width is None or height is None:
        native_width, native_height = native_resolution(description["image_path"])
        width = width or native_width
        height = height or native_height
    return width, height


def individual_from_alleles(problem, alleles: list[float]) -> Individual:
    return Individual(alleles=list(alleles), schema=problem.schema())


def read_checkpoints(out_dir: Path) -> list[dict]:
    path = out_dir / CHECKPOINTS_FILE
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} not found - re-run the simulation with --snapshot-every N"
        )
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


# -- stage 2: the final image -------------------------------------------------


def render_final(
    out_dir: Path, width: int | None = None, height: int | None = None
) -> Path:
    """Draw ``best.json`` at export resolution. Needs no config file."""
    summary = load_summary(out_dir)
    problem = rebuild_problem(summary)
    export_width, export_height = export_size(summary["problem"], width, height)

    payload = json.loads((out_dir / BEST_FILE).read_text(encoding="utf-8"))
    best = individual_from_alleles(problem, payload["alleles"])

    path = out_dir / FINAL_IMAGE
    save_image(problem.renderer, best, export_width, export_height, path)
    return path


# -- stage 3: the snapshots and the gif ---------------------------------------


def render_snapshots(
    out_dir: Path,
    width: int | None = None,
    height: int | None = None,
    gif: bool = True,
    frame_ms: int = 120,
    hold_ms: int = 3000,
) -> list[Path]:
    """Draw every checkpoint, then assemble them into ``progress.gif``.

    ``final.png`` closes the gif: the last checkpoint is only the best of its
    own generation, while that is the best individual of the whole run. It is
    rendered here if it does not already exist, so this stage stands alone.
    """
    summary = load_summary(out_dir)
    problem = rebuild_problem(summary)
    export_width, export_height = export_size(summary["problem"], width, height)

    snapshots_dir = out_dir / SNAPSHOTS_DIR
    snapshots_dir.mkdir(exist_ok=True)

    paths: list[Path] = []
    for checkpoint in read_checkpoints(out_dir):
        individual = individual_from_alleles(problem, checkpoint["alleles"])
        path = snapshots_dir / f"gen_{checkpoint['generation']:05d}.png"
        save_image(problem.renderer, individual, export_width, export_height, path)
        paths.append(path)

    if not gif:
        return paths

    final_path = out_dir / FINAL_IMAGE
    if not final_path.is_file():
        render_final(out_dir, export_width, export_height)
    save_gif([*paths, final_path], out_dir / GIF_FILE, frame_ms, hold_ms)
    return paths
