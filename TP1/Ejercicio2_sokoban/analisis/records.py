"""Esquema de salida: una fila de CSV por ejecución.

`RunRecord` es el contrato con el sistema de análisis posterior. Es un
dataclass de tipos primitivos a propósito: se serializa a CSV sin conversiones
raras y viaja por pickle entre procesos sin arrastrar objetos del motor.

El detalle de cada columna está en `analisis/SCHEMA.md`.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import IO, Iterable

# Valores posibles de la columna `status`.
STATUS_OK = "ok"                  # el agente terminó y encontró solución
STATUS_NO_SOLUTION = "no_solution"  # el agente terminó y agotó el espacio sin solución
STATUS_TIMEOUT = "timeout"        # se cortó por `timeout_seconds`
STATUS_ERROR = "error"            # excepción (incluye MemoryError / muerte del worker)

STATUSES = (STATUS_OK, STATUS_NO_SOLUTION, STATUS_TIMEOUT, STATUS_ERROR)


@dataclass(frozen=True, slots=True)
class RunRecord:
    """Resultado de UNA ejecución de un algoritmo sobre un nivel."""

    # --- identidad de la corrida ---
    run_id: str
    level: str
    algorithm: str
    heuristic: str | None
    algorithm_label: str
    repetition: int

    # --- desenlace ---
    status: str
    success: bool

    # --- métricas del SearchResult ---
    cost: int | None
    nodes_expanded: int | None
    frontier_nodes: int | None
    elapsed_seconds: float | None
    wall_seconds: float

    # --- verificación de la solución ---
    solution_valid: bool | None
    pushes: int | None
    simple_steps: int | None

    # --- características del nivel ---
    board_width: int | None
    board_height: int | None
    boxes: int | None
    goals: int | None

    # --- contexto de ejecución (mismo valor en toda la tanda) ---
    executor: str
    workers: int
    timeout_seconds: float | None
    started_at_utc: str
    hostname: str
    python_version: str
    cpu_count: int | None
    git_commit: str | None

    # --- extras ---
    error_message: str | None
    solution: str | None


CSV_COLUMNS: tuple[str, ...] = tuple(field.name for field in fields(RunRecord))


class CsvResultWriter:
    """Escribe `RunRecord`s a CSV de a una fila, flusheando en cada una.

    Es incremental a propósito: una tanda con niveles pesados puede durar
    horas, y si se corta (Ctrl-C, OOM, batería) las filas ya completadas
    quedan en disco igual.
    """

    def __init__(self, path: Path, include_solution: bool = True) -> None:
        self.path = path
        self.include_solution = include_solution
        self.columns = [
            name for name in CSV_COLUMNS
            if include_solution or name != "solution"
        ]
        self._handle: IO[str] | None = None
        self._writer: csv.DictWriter | None = None

    def __enter__(self) -> "CsvResultWriter":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._handle, fieldnames=self.columns)
        self._writer.writeheader()
        self._handle.flush()
        return self

    def write(self, record: RunRecord) -> None:
        if self._writer is None or self._handle is None:
            raise RuntimeError("CsvResultWriter usado fuera de su context manager")
        row = asdict(record)
        if not self.include_solution:
            row.pop("solution", None)
        self._writer.writerow(row)
        self._handle.flush()

    def __exit__(self, *exc_info) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None
            self._writer = None


def write_csv(path: Path, records: Iterable[RunRecord], include_solution: bool = True) -> Path:
    """Escribe todos los records de una (para uso programático / tests)."""
    with CsvResultWriter(path, include_solution=include_solution) as writer:
        for record in records:
            writer.write(record)
    return path
