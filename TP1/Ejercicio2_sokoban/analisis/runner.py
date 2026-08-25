"""Orquestador paralelo: reparte las ejecuciones y va emitiendo resultados.

Dos backends, elegibles con `executor` en el config:

`thread`  -- ThreadPoolExecutor, el pedido original. Los algoritmos son Python
             puro y CPU-bound, así que el GIL los serializa: no hay speedup y
             los tiempos de corridas concurrentes se contaminan entre sí.
             Además un thread no se puede matar, así que el timeout es
             "best-effort": marca la fila como `timeout` y libera el slot
             lógico, pero la búsqueda sigue quemando CPU de fondo.

`process` -- un proceso por ejecución, con la concurrencia acotada por un pool
             de threads en el padre que solo esperan (no compiten por el GIL).
             Cada búsqueda corre aislada, así que los tiempos son limpios y el
             timeout mata de verdad al worker. Es el default.

En los dos casos `run_benchmark` es un generador: emite cada `RunRecord` ni
bien está listo, para que el CSV se escriba incrementalmente.
"""

from __future__ import annotations

import multiprocessing
import queue
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from typing import Callable, Iterator

from .config import BenchmarkConfig
from .records import STATUS_ERROR, STATUS_TIMEOUT, RunRecord
from .worker import RunContext, Task, child_entrypoint, execute_task, _make_record

# Cada cuánto el padre chequea si el hijo terminó o se pasó del timeout.
_POLL_SECONDS = 0.05

ProgressHook = Callable[[RunRecord, int, int], None]


def make_run_id(now: datetime | None = None) -> str:
    """Id de la tanda: timestamp UTC apto para nombre de archivo."""
    moment = now or datetime.now(timezone.utc)
    return moment.strftime("%Y%m%dT%H%M%SZ")


def build_tasks(config: BenchmarkConfig, run_id: str) -> list[Task]:
    """Producto cartesiano nivel x algoritmo x repetición.

    El orden agrupa por repetición al final para que, si la tanda se corta a
    mitad de camino, el CSV parcial tenga al menos una repetición de cada
    combinación en vez de todas las de un solo algoritmo.
    """
    tasks: list[Task] = []
    for repetition in range(1, config.repetitions + 1):
        for level in config.levels:
            for algorithm in config.algorithms:
                tasks.append(
                    Task(
                        run_id=run_id,
                        level=level,
                        level_path=str(config.level_path(level)),
                        algorithm=algorithm.name,
                        heuristic=algorithm.heuristic,
                        algorithm_label=algorithm.label,
                        repetition=repetition,
                        memory_limit_mb=config.memory_limit_mb,
                    )
                )
    return tasks


def run_benchmark(
    config: BenchmarkConfig,
    run_id: str | None = None,
    progress: ProgressHook | None = None,
) -> Iterator[RunRecord]:
    """Corre la tanda entera y va emitiendo un `RunRecord` por ejecución."""
    run_id = run_id or make_run_id()
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    context = RunContext.capture(
        executor=config.executor,
        workers=config.workers,
        timeout_seconds=config.timeout_seconds,
        started_at_utc=started_at,
    )

    tasks = build_tasks(config, run_id)
    total = len(tasks)

    backend = _run_processes if config.executor == "process" else _run_threads
    for index, record in enumerate(backend(tasks, context, config), start=1):
        if progress is not None:
            progress(record, index, total)
        yield record


# --------------------------------------------------------------------------
# Backend: procesos (default)
# --------------------------------------------------------------------------

def _run_processes(
    tasks: list[Task], context: RunContext, config: BenchmarkConfig
) -> Iterator[RunRecord]:
    """Un proceso por ejecución; el pool de threads solo acota la concurrencia.

    Los threads del padre pasan todo el tiempo bloqueados esperando al hijo,
    así que no pelean por el GIL entre ellos ni con las búsquedas.
    """
    # "spawn" da un hijo limpio (sin heredar estado del padre) y es el único
    # start method soportado en macOS/Windows sin sorpresas.
    ctx = multiprocessing.get_context("spawn")

    with ThreadPoolExecutor(max_workers=config.workers, thread_name_prefix="proc-sup") as pool:
        futures = [
            pool.submit(_run_one_in_process, task, context, config.timeout_seconds, ctx)
            for task in tasks
        ]
        yield from _as_they_finish(futures, tasks, context)


def _run_one_in_process(
    task: Task, context: RunContext, timeout: float | None, ctx
) -> RunRecord:
    """Lanza el hijo, espera el resultado y, si se pasa del timeout, lo mata."""
    result_queue = ctx.Queue()
    process = ctx.Process(
        target=child_entrypoint,
        args=(task, context, result_queue),
        daemon=True,
    )

    wall_start = time.perf_counter()
    process.start()

    payload = None
    timed_out = False
    deadline = None if timeout is None else wall_start + timeout

    try:
        while True:
            try:
                payload = result_queue.get(timeout=_POLL_SECONDS)
                break
            except queue.Empty:
                pass

            if not process.is_alive():
                # El hijo murió sin dejar resultado (OOM kill, segfault...).
                # Le damos una última chance a la cola por si el record ya
                # estaba en vuelo cuando el proceso terminó.
                try:
                    payload = result_queue.get(timeout=_POLL_SECONDS * 4)
                except queue.Empty:
                    payload = None
                break

            if deadline is not None and time.perf_counter() > deadline:
                timed_out = True
                break
    finally:
        _terminate(process)
        result_queue.close()
        try:
            result_queue.join_thread()
        except Exception:
            pass

    wall_seconds = time.perf_counter() - wall_start

    if timed_out:
        return _make_record(
            task, context,
            status=STATUS_TIMEOUT,
            wall_seconds=wall_seconds,
            error_message=f"superó timeout_seconds={timeout}; worker terminado",
        )

    if isinstance(payload, RunRecord):
        return payload

    if isinstance(payload, tuple) and payload and payload[0] == "__worker_crash__":
        return _make_record(
            task, context,
            status=STATUS_ERROR,
            wall_seconds=wall_seconds,
            error_message=f"el worker falló: {payload[1]}",
        )

    exit_code = process.exitcode
    return _make_record(
        task, context,
        status=STATUS_ERROR,
        wall_seconds=wall_seconds,
        error_message=(
            f"el worker murió sin devolver resultado (exitcode={exit_code}); "
            f"causas típicas: falta de memoria, o el script que lanzó el runner "
            f"no protege su entrada con `if __name__ == \"__main__\":` "
            f"(requerido por el start method 'spawn')"
        ),
    )


def _terminate(process) -> None:
    """Baja el proceso hijo: SIGTERM y, si no cede, SIGKILL."""
    if not process.is_alive():
        process.join(timeout=1)
        return
    process.terminate()
    process.join(timeout=5)
    if process.is_alive():
        process.kill()
        process.join(timeout=5)


# --------------------------------------------------------------------------
# Backend: threads (pedido original; ver la advertencia del docstring de arriba)
# --------------------------------------------------------------------------

def _run_threads(
    tasks: list[Task], context: RunContext, config: BenchmarkConfig
) -> Iterator[RunRecord]:
    """ThreadPoolExecutor puro. El timeout es best-effort: no mata el thread.

    Ojo: si una búsqueda se pasa del timeout, la fila sale como `timeout` pero
    el thread sigue corriendo, sigue compitiendo por el GIL y encima demora la
    salida del intérprete al final de la tanda.
    """
    # El timeout tiene que contarse desde que la task ARRANCA, no desde que se
    # encola: con `workers` threads, las tasks de más quedan esperando turno y
    # si les contaramos el tiempo en cola saldrían como timeout sin haber
    # corrido nunca. El wrapper estampa el arranque real de cada una.
    started_at: dict[Task, float] = {}

    def _timed(task: Task) -> RunRecord:
        started_at[task] = time.perf_counter()
        return execute_task(task, context)

    # A propósito NO usamos `with`: al salir, el context manager llama a
    # shutdown(wait=True) y se quedaría bloqueado para siempre esperando al
    # thread de una búsqueda que se pasó del timeout (y que no se puede matar).
    # Con wait=False el runner devuelve el control y puede cerrar el CSV; los
    # threads zombis quedan corriendo hasta que `main.py` fuerza la salida.
    pool = ThreadPoolExecutor(max_workers=config.workers, thread_name_prefix="solve")
    try:
        futures = [pool.submit(_timed, task) for task in tasks]
        yield from _as_they_finish(
            futures, tasks, context,
            timeout=config.timeout_seconds,
            started_at=started_at,
        )
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


# --------------------------------------------------------------------------
# Común a los dos backends
# --------------------------------------------------------------------------

def _as_they_finish(
    futures,
    tasks: list[Task],
    context: RunContext,
    timeout: float | None = None,
    started_at: dict[Task, float] | None = None,
) -> Iterator[RunRecord]:
    """Emite resultados a medida que terminan, aplicando el timeout si aplica.

    El backend de procesos ya resuelve su propio timeout adentro del worker, y
    llama a esto con `timeout=None`; el de threads lo aplica acá, que es lo
    único que puede hacer sin poder matar el thread. `started_at` dice cuándo
    arrancó realmente cada task: las que todavía esperan turno en el pool no
    tienen deadline.
    """
    by_future = {future: task for future, task in zip(futures, tasks)}
    watching = timeout is not None
    started_at = started_at if started_at is not None else {}
    pending = set(futures)

    while pending:
        done, pending = wait(pending, timeout=_POLL_SECONDS if watching else None,
                             return_when=FIRST_COMPLETED)

        for future in done:
            task = by_future[future]
            try:
                yield future.result()
            except Exception as exc:  # noqa: BLE001 - el futuro nunca debería explotar
                yield _make_record(
                    task, context,
                    status=STATUS_ERROR,
                    wall_seconds=0.0,
                    error_message=f"fallo del executor: {type(exc).__name__}: {exc}",
                )

        if not watching:
            continue

        now = time.perf_counter()
        expired = [
            future for future in pending
            if now - started_at.get(by_future[future], float("inf")) > timeout
        ]
        for future in expired:
            # `cancel()` solo sirve si todavía no arrancó; si ya está corriendo
            # el thread sigue vivo hasta que termine solo.
            future.cancel()
            pending.discard(future)
            task = by_future[future]
            yield _make_record(
                task, context,
                status=STATUS_TIMEOUT,
                wall_seconds=time.perf_counter() - started_at[task],
                error_message=(
                    f"superó timeout_seconds={timeout}; con executor=thread el "
                    f"worker NO se puede matar y sigue corriendo de fondo"
                ),
            )
