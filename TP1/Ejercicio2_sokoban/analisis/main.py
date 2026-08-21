#!/usr/bin/env python3
"""CLI del runner de experimentos.

    python analisis/main.py                      # usa analisis/config.yaml
    python analisis/main.py mi_config.yaml
    python analisis/main.py --repetitions 10 --workers 8
    python analisis/main.py --dry-run            # lista qué correría, sin correr

Escribe un CSV (una fila por ejecución) en `output_dir` y lo va flusheando a
medida que avanza, así una tanda larga que se corta igual deja datos usables.
"""

from __future__ import annotations

import argparse
import os
import platform
import sys
from pathlib import Path

# El script se puede invocar como `python analisis/main.py`, sin -m: en ese
# caso `analisis` todavía no es importable, así que sumamos la raíz al path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analisis.config import (  # noqa: E402
    PROJECT_ROOT,
    BenchmarkConfigError,
    load_benchmark_config,
)
from analisis.records import (  # noqa: E402
    STATUS_ERROR,
    STATUS_OK,
    STATUS_TIMEOUT,
    CsvResultWriter,
)
from analisis.runner import make_run_id, build_tasks, run_benchmark  # noqa: E402
from analisis.worker import memory_limit_supported  # noqa: E402

DEFAULT_CONFIG = PROJECT_ROOT / "analisis" / "config.yaml"


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="analisis/main.py",
        description="Corre N veces cada (nivel x algoritmo) en paralelo y vuelca un CSV.",
    )
    parser.add_argument(
        "config", nargs="?", default=None,
        help=f"config YAML/JSON del runner (default: {DEFAULT_CONFIG.name})",
    )
    parser.add_argument("--executor", choices=("process", "thread"),
                        help="pisa `executor` del config")
    parser.add_argument("--workers", type=int, help="pisa `workers` del config")
    parser.add_argument("--repetitions", type=int, help="pisa `repetitions` del config")
    parser.add_argument("--timeout", type=float, dest="timeout_seconds",
                        help="pisa `timeout_seconds` del config (0 = sin timeout)")
    parser.add_argument("--output-dir", help="pisa `output_dir` del config")
    parser.add_argument("--output-file", help="pisa `output_file` del config")
    parser.add_argument("--dry-run", action="store_true",
                        help="muestra el plan de ejecución y sale sin correr nada")
    parser.add_argument("--quiet", action="store_true",
                        help="no imprime el progreso fila por fila")
    return parser.parse_args(argv[1:])


def _apply_overrides(config, args):
    """Los flags de CLI pisan el config; útil para barridos sin editar el YAML."""
    from dataclasses import replace

    changes = {}
    if args.executor:
        changes["executor"] = args.executor
    if args.workers is not None:
        if args.workers < 1:
            raise BenchmarkConfigError("--workers tiene que ser >= 1")
        changes["workers"] = args.workers
    if args.repetitions is not None:
        if args.repetitions < 1:
            raise BenchmarkConfigError("--repetitions tiene que ser >= 1")
        changes["repetitions"] = args.repetitions
    if args.timeout_seconds is not None:
        if args.timeout_seconds < 0:
            raise BenchmarkConfigError("--timeout tiene que ser >= 0")
        changes["timeout_seconds"] = args.timeout_seconds or None
    if args.output_dir:
        path = Path(args.output_dir)
        changes["output_dir"] = path if path.is_absolute() else PROJECT_ROOT / path
    if args.output_file:
        changes["output_file"] = args.output_file
    return replace(config, **changes) if changes else config


def _print_plan(config, run_id: str, output_path: Path) -> None:
    print(f"run_id:        {run_id}")
    print(f"config:        {config.source_path}")
    print(f"executor:      {config.executor} ({config.workers} workers)")
    print(f"repeticiones:  {config.repetitions}")
    print(f"timeout:       {config.timeout_seconds or 'sin límite'}")
    print(f"límite memoria: {config.memory_limit_mb or 'sin límite'} MB")
    print(f"niveles:       {', '.join(config.levels)}")
    print(f"algoritmos:    {', '.join(a.label for a in config.algorithms)}")
    print(f"ejecuciones:   {config.total_runs()}")
    print(f"salida:        {output_path}")
    if config.memory_limit_mb and not memory_limit_supported():
        print(
            f"\naviso: `memory_limit_mb` no tiene efecto en esta plataforma "
            f"({platform.system()}):\n       RLIMIT_AS solo lo implementa Linux. "
            f"La corrida sigue, pero SIN tope de memoria.",
            file=sys.stderr,
        )
    if config.executor == "thread":
        print(
            "\naviso: con executor=thread los algoritmos (Python puro, CPU-bound) "
            "se serializan\n       por el GIL y los tiempos concurrentes se "
            "contaminan; además el timeout\n       no puede matar el thread. "
            "Para medir tiempos usá executor=process.",
            file=sys.stderr,
        )


def main(argv: list[str]) -> int:
    args = _parse_args(argv)

    try:
        config = load_benchmark_config(args.config or DEFAULT_CONFIG)
        config = _apply_overrides(config, args)
    except BenchmarkConfigError as exc:
        print(f"error de configuración: {exc}", file=sys.stderr)
        return 1

    run_id = make_run_id()
    output_path = config.output_path(run_id)

    _print_plan(config, run_id, output_path)

    if args.dry_run:
        print("\n--dry-run: no se ejecutó nada.")
        for task in build_tasks(config, run_id):
            print(f"  {task.describe()}")
        return 0

    print()
    counts = {STATUS_OK: 0, "no_solution": 0, STATUS_TIMEOUT: 0, STATUS_ERROR: 0}
    invalid = 0
    written = 0

    def progress(record, index: int, total: int) -> None:
        if args.quiet:
            return
        seconds = record.elapsed_seconds if record.elapsed_seconds is not None else record.wall_seconds
        detail = f"{seconds:7.3f}s"
        if record.status == STATUS_OK:
            detail += f"  cost={record.cost} exp={record.nodes_expanded}"
        elif record.error_message:
            detail += f"  {record.error_message[:70]}"
        print(
            f"[{index:>{len(str(total))}}/{total}] {record.status:<12} "
            f"{record.level} / {record.algorithm_label} / rep {record.repetition}  {detail}",
            flush=True,
        )

    try:
        with CsvResultWriter(output_path, include_solution=config.include_solution) as writer:
            for record in run_benchmark(config, run_id=run_id, progress=progress):
                writer.write(record)
                written += 1
                counts[record.status] = counts.get(record.status, 0) + 1
                if record.status == STATUS_OK and record.solution_valid is False:
                    invalid += 1
    except KeyboardInterrupt:
        print(
            f"\ninterrumpido: quedaron {written} ejecuciones en {output_path}",
            file=sys.stderr,
        )
        return 130

    print(f"\n{written} ejecuciones -> {output_path}")
    print(
        f"  ok={counts.get(STATUS_OK, 0)}  "
        f"sin_solucion={counts.get('no_solution', 0)}  "
        f"timeout={counts.get(STATUS_TIMEOUT, 0)}  "
        f"error={counts.get(STATUS_ERROR, 0)}"
    )
    if invalid:
        print(
            f"  ATENCIÓN: {invalid} solucion(es) no pasaron la verificación con el "
            f"motor (solution_valid=False)",
            file=sys.stderr,
        )

    if config.executor == "thread" and counts.get(STATUS_TIMEOUT, 0):
        # Las búsquedas que se pasaron del timeout siguen vivas en sus threads
        # y son no-daemon: si dejáramos que el intérprete salga normalmente, se
        # colgaría esperándolas. El CSV ya está cerrado y flusheado, así que
        # cortamos por lo sano.
        print(
            f"  aviso: {counts[STATUS_TIMEOUT]} búsqueda(s) siguen corriendo en sus "
            f"threads y no se pueden matar; forzando la salida.",
            file=sys.stderr,
        )
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(0)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
