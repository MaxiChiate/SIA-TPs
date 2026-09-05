"""CLI entry point: run one GA config end-to-end and write its results.

Usage:
    python run.py [config.json] [--out DIR] [--snapshot-every N]
                   [--export-width W] [--export-height H]
                   [--no-gif] [--gif-frame-ms MS] [--gif-hold-ms MS]

Writes into the results directory: ``final.png`` (the best individual
rendered full-size), ``snapshots/gen_*.png`` and ``progress.gif`` (only if
``--snapshot-every`` is set), ``triangles.json`` (the best individual's
triangles enumerated), ``history.csv``/``history.json`` (one row per
generation), and ``summary.json`` (best fitness, stop reason, the resolved
problem description, full config + seed).
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import sys
import time
from pathlib import Path

import ga.operators  # noqa: F401 -- registers GA operators by name
import problems.triangles  # noqa: F401 -- registers the "triangles" problem
from ga.config import ConfigError, load_config
from ga.core.engine import Engine, RunResult
from ga.core.population import Population
from ga.metrics import mean as mean_fitness
from problems.triangles import colorspace
from problems.triangles.export import (
    native_resolution,
    save_gif,
    save_image,
    save_triangles_json,
)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a GA config end-to-end.")
    parser.add_argument(
        "config", nargs="?", default="config.json",
        help="path to the run's config JSON (default: config.json)",
    )
    parser.add_argument(
        "--out", default=None,
        help="results directory (default: results/<config stem>_<timestamp>/)",
    )
    parser.add_argument(
        "--snapshot-every", type=int, default=0,
        help="save an intermediate render every N generations (0 = disabled)",
    )
    parser.add_argument(
        "--export-width", type=int, default=None,
        help="final render width (default: the source image's native width)",
    )
    parser.add_argument(
        "--export-height", type=int, default=None,
        help="final render height (default: the source image's native height)",
    )
    parser.add_argument(
        "--no-gif", action="store_true",
        help="skip progress.gif (it is built whenever --snapshot-every is set)",
    )
    parser.add_argument(
        "--gif-frame-ms", type=int, default=120,
        help="milliseconds per snapshot frame in progress.gif (default: 120)",
    )
    parser.add_argument(
        "--gif-hold-ms", type=int, default=3000,
        help="milliseconds to hold the final image in progress.gif (default: 3000)",
    )
    return parser.parse_args(argv)


def _results_dir(config_path: Path, explicit: str | None) -> Path:
    if explicit is not None:
        return Path(explicit)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    return Path("results") / f"{config_path.stem}_{stamp}"


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
    "native"`` becomes the image's pixel size, ``"renderer": "auto"`` becomes the
    backend that was picked. A run has to record the second one, otherwise its
    numbers cannot be reproduced or compared against another run's.
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
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    config_path = Path(args.config)

    try:
        loaded = load_config(config_path)
    except ConfigError as err:
        print(f"config error: {err}", file=sys.stderr)
        return 1

    description = loaded.problem.describe()
    triangle_count = description["triangle_count"]
    color_space = colorspace.get(description["color_space"])
    renderer = loaded.problem.renderer

    export_width, export_height = args.export_width, args.export_height
    if export_width is None or export_height is None:
        native_width, native_height = native_resolution(description["image_path"])
        export_width = export_width or native_width
        export_height = export_height or native_height

    out_dir = _results_dir(config_path, args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    snapshots_dir = out_dir / "snapshots"
    if args.snapshot_every > 0:
        snapshots_dir.mkdir(exist_ok=True)

    # Collected as they are written rather than globbed afterwards, so a
    # re-run into a directory that already holds a longer run's snapshots does
    # not splice those stale frames into this run's gif.
    snapshot_paths: list[Path] = []

    def on_generation(population: Population) -> None:
        generation = population.generation
        best = population.best()
        print(
            f"gen {generation:5d}  best={best.fitness:.6f}  "
            f"mean={mean_fitness(population.fitnesses()):.6f}"
        )
        if args.snapshot_every > 0 and generation % args.snapshot_every == 0:
            snapshot_path = snapshots_dir / f"gen_{generation:05d}.png"
            save_image(renderer, best, export_width, export_height, snapshot_path)
            snapshot_paths.append(snapshot_path)

    engine = Engine(loaded.problem, loaded.engine_config, loaded.rng)
    result = engine.run(on_generation=on_generation)

    save_image(renderer, result.best, export_width, export_height, out_dir / "final.png")
    save_triangles_json(
        result.best, triangle_count, export_width, export_height,
        out_dir / "triangles.json", color_space,
    )
    # ``final.png`` closes the gif: the last snapshot is only the best of its
    # own generation, while this is the best individual of the whole run.
    if snapshot_paths and not args.no_gif:
        save_gif(
            [*snapshot_paths, out_dir / "final.png"],
            out_dir / "progress.gif",
            args.gif_frame_ms,
            args.gif_hold_ms,
        )

    _write_history(result.history, out_dir)
    _write_summary(result, loaded.raw, description, loaded.seed, out_dir)

    print(
        f"\nbest fitness {result.best.fitness:.6f} at generation {result.best_generation} "
        f"(stopped: {result.stop_reason})"
    )
    print(f"results written to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
