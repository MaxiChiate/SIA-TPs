"""La unidad de trabajo: resolver un nivel con un algoritmo, una vez.

Todo acá es top-level y de tipos primitivos porque `Task` y `RunRecord` viajan
por pickle hacia y desde los procesos hijos del executor `process`.

El worker no sabe nada de paralelismo: `runner.py` decide si esto corre en un
thread o en un proceso aparte.
"""

from __future__ import annotations

import os
import platform
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from .records import (
    STATUS_ERROR,
    STATUS_NO_SOLUTION,
    STATUS_OK,
    RunRecord,
)


@dataclass(frozen=True, slots=True)
class Task:
    """Una ejecución pendiente. Solo primitivos: tiene que ser picklable."""

    run_id: str
    level: str
    level_path: str
    algorithm: str
    heuristic: str | None
    algorithm_label: str
    repetition: int
    memory_limit_mb: int | None

    def describe(self) -> str:
        return f"{self.level} / {self.algorithm_label} / rep {self.repetition}"


@dataclass(frozen=True, slots=True)
class RunContext:
    """Datos iguales para toda la tanda, que se copian en cada fila del CSV."""

    executor: str
    workers: int
    timeout_seconds: float | None
    started_at_utc: str
    hostname: str
    python_version: str
    cpu_count: int | None
    git_commit: str | None

    @staticmethod
    def capture(
        executor: str, workers: int, timeout_seconds: float | None, started_at_utc: str
    ) -> "RunContext":
        """Snapshot del entorno, para que el CSV sea reproducible sin notas aparte."""
        return RunContext(
            executor=executor,
            workers=workers,
            timeout_seconds=timeout_seconds,
            started_at_utc=started_at_utc,
            hostname=socket.gethostname(),
            python_version=platform.python_version(),
            cpu_count=os.cpu_count(),
            git_commit=_git_commit(),
        )


def _git_commit() -> str | None:
    """SHA corto del repo, o None si no estamos en un repo / no hay git."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path(__file__).resolve().parent,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None if result.returncode == 0 else None


def memory_limit_supported() -> bool:
    """¿Esta plataforma respeta `RLIMIT_AS`?

    Linux sí. macOS y Windows no lo implementan: `setrlimit` directamente tira
    ValueError y la asignación de memoria sigue sin tope (verificado en macOS
    15 / Python 3.14). Lo exponemos para que `main.py` avise en vez de dejar
    creer que el límite está puesto.
    """
    try:
        import resource
    except ImportError:
        return False
    return hasattr(resource, "RLIMIT_AS") and platform.system() not in ("Darwin", "Windows")


def apply_memory_limit(memory_limit_mb: int | None) -> None:
    """Limita la memoria virtual del proceso actual (best-effort).

    BFS/A* sobre niveles con muchas cajas se comen varios GB; con N workers en
    paralelo eso tumba la máquina. Con el límite puesto, el worker muere con
    MemoryError y queda registrado como `error` en vez de arrastrar a todo el
    sistema al swap.

    Solo tiene efecto en el executor `process` (en threads el límite sería del
    proceso entero, compartido con el runner) y SOLO en Linux -- ver
    `memory_limit_supported()`. Nunca aborta la corrida si no se puede aplicar.
    """
    if memory_limit_mb is None:
        return
    try:
        import resource

        limit_bytes = memory_limit_mb * 1024 * 1024
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        new_hard = hard if hard != resource.RLIM_INFINITY else limit_bytes
        resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, new_hard))
    except (ImportError, ValueError, OSError):
        pass


def execute_task(task: Task, context: RunContext) -> RunRecord:
    """Corre una ejecución completa y la devuelve como fila lista para el CSV.

    Nunca propaga excepciones del agente: cualquier fallo se convierte en un
    `RunRecord` con `status="error"`, para que una búsqueda que explota no
    corte la tanda entera.
    """
    # Import diferido: en el executor `process` esto corre en un hijo recién
    # spawneado, y así el costo de importar el motor queda dentro del worker.
    from sokoban.engine import is_goal, replay
    from sokoban.parser import LevelParseError, parse_level
    from sokoban.search import build_agent

    wall_start = time.perf_counter()

    def _failed(message: str) -> RunRecord:
        return _make_record(
            task, context,
            status=STATUS_ERROR,
            wall_seconds=time.perf_counter() - wall_start,
            error_message=message,
        )

    try:
        level_text = Path(task.level_path).read_text()
        level = parse_level(level_text, name=task.level)
    except (OSError, LevelParseError) as exc:
        return _failed(f"no se pudo cargar el nivel: {exc}")

    board = {
        "board_width": level.width,
        "board_height": level.height,
        "boxes": len(level.initial_boxes),
        "goals": len(level.goals),
    }

    try:
        agent = build_agent(task.algorithm, task.heuristic)
    except (ValueError, NotImplementedError) as exc:
        return _failed(f"no se pudo construir el agente: {exc}")

    try:
        result = agent.solve(level)
    except MemoryError:
        return _make_record(
            task, context,
            status=STATUS_ERROR,
            wall_seconds=time.perf_counter() - wall_start,
            error_message="MemoryError (se agotó la memoria del worker)",
            **board,
        )
    except RecursionError as exc:
        return _make_record(
            task, context,
            status=STATUS_ERROR,
            wall_seconds=time.perf_counter() - wall_start,
            error_message=f"RecursionError: {exc}",
            **board,
        )
    except Exception as exc:  # noqa: BLE001 - un agente roto no debe cortar la tanda
        return _make_record(
            task, context,
            status=STATUS_ERROR,
            wall_seconds=time.perf_counter() - wall_start,
            error_message=f"{type(exc).__name__}: {exc}",
            **board,
        )

    wall_seconds = time.perf_counter() - wall_start

    if not result.success:
        return _make_record(
            task, context,
            status=STATUS_NO_SOLUTION,
            wall_seconds=wall_seconds,
            success=False,
            cost=result.cost,
            nodes_expanded=result.nodes_expanded,
            frontier_nodes=result.frontier_nodes,
            elapsed_seconds=result.elapsed_seconds,
            **board,
        )

    # Verificamos la solución con el mismo motor: una fila con
    # solution_valid=False señala un bug del algoritmo, no un dato a promediar.
    solution = result.solution
    try:
        trace = replay(level, solution)
        solution_valid = is_goal(trace[-1], level)
        validation_error = None
    except Exception as exc:  # noqa: BLE001 - MoveError y cualquier otra sorpresa
        solution_valid = False
        validation_error = f"solución inválida: {type(exc).__name__}: {exc}"

    pushes = sum(1 for move in solution if move.isupper())

    return _make_record(
        task, context,
        status=STATUS_OK,
        wall_seconds=wall_seconds,
        success=True,
        cost=result.cost,
        nodes_expanded=result.nodes_expanded,
        frontier_nodes=result.frontier_nodes,
        elapsed_seconds=result.elapsed_seconds,
        solution_valid=solution_valid,
        pushes=pushes,
        simple_steps=len(solution) - pushes,
        solution=solution,
        error_message=validation_error,
        **board,
    )


def _make_record(
    task: Task,
    context: RunContext,
    *,
    status: str,
    wall_seconds: float,
    success: bool = False,
    cost: int | None = None,
    nodes_expanded: int | None = None,
    frontier_nodes: int | None = None,
    elapsed_seconds: float | None = None,
    solution_valid: bool | None = None,
    pushes: int | None = None,
    simple_steps: int | None = None,
    board_width: int | None = None,
    board_height: int | None = None,
    boxes: int | None = None,
    goals: int | None = None,
    error_message: str | None = None,
    solution: str | None = None,
) -> RunRecord:
    """Arma el `RunRecord` completando el contexto y la identidad de la task."""
    return RunRecord(
        run_id=task.run_id,
        level=task.level,
        algorithm=task.algorithm,
        heuristic=task.heuristic,
        algorithm_label=task.algorithm_label,
        repetition=task.repetition,
        status=status,
        success=success,
        cost=cost,
        nodes_expanded=nodes_expanded,
        frontier_nodes=frontier_nodes,
        elapsed_seconds=elapsed_seconds,
        wall_seconds=wall_seconds,
        solution_valid=solution_valid,
        pushes=pushes,
        simple_steps=simple_steps,
        board_width=board_width,
        board_height=board_height,
        boxes=boxes,
        goals=goals,
        executor=context.executor,
        workers=context.workers,
        timeout_seconds=context.timeout_seconds,
        started_at_utc=context.started_at_utc,
        hostname=context.hostname,
        python_version=context.python_version,
        cpu_count=context.cpu_count,
        git_commit=context.git_commit,
        error_message=error_message,
        solution=solution,
    )


def child_entrypoint(task: Task, context: RunContext, result_queue) -> None:
    """`target` del proceso hijo en el executor `process`.

    Aplica el límite de memoria y deja el `RunRecord` en la cola. Si ni
    siquiera eso se puede (p.ej. el pickle del record falla), manda el error
    como texto para que el padre lo registre.
    """
    apply_memory_limit(task.memory_limit_mb)
    try:
        record = execute_task(task, context)
        result_queue.put(record)
    except BaseException as exc:  # noqa: BLE001 - último recurso antes de morir mudo
        try:
            result_queue.put(("__worker_crash__", f"{type(exc).__name__}: {exc}"))
        except Exception:
            pass
    finally:
        # Con el start method "spawn" la cola usa un feeder thread; sin este
        # flush el proceso puede terminar antes de que el record salga.
        try:
            result_queue.close()
            result_queue.join_thread()
        except Exception:
            pass


def project_root_on_path() -> None:
    """Garantiza que `sokoban`/`analisis` sean importables desde cualquier cwd."""
    root = str(Path(__file__).resolve().parent.parent)
    if root not in sys.path:
        sys.path.insert(0, root)
