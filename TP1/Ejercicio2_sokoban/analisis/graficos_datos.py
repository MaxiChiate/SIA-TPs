"""Carga del CSV de resultados y agregación para los gráficos.

Solo librería estándar: los CSVs son chicos (decenas a miles de filas) y no
justifican traer pandas.

La regla de oro del módulo: **las filas con `status != "ok"` nunca entran en un
promedio**. Un `timeout` tiene `wall_seconds ≈ timeout_seconds`, que es un piso
artificial; promediarlo con las corridas exitosas inventa un número que no
significa nada. Esas combinaciones se marcan como "no terminó" en el lugar donde
iría la barra, así la ausencia no se lee como un cero.
"""

from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass, field
from pathlib import Path

# Orden canónico de presentación: primero los no informados, después los
# informados. Cualquier algoritmo que no esté acá se agrega al final, alfabético.
ORDEN_ALGORITMOS = ["bfs", "dfs", "iddfs", "greedy", "astar"]


class DatosError(ValueError):
    """El CSV no existe, está vacío, o le faltan columnas."""


def _num(valor: str | None, tipo):
    """Convierte una celda del CSV; las vacías son None (no 0)."""
    if valor is None or valor == "":
        return None
    try:
        return tipo(valor)
    except ValueError:
        return None


def _bool(valor: str | None):
    if valor is None or valor == "":
        return None
    return valor.strip().lower() == "true"


@dataclass(frozen=True, slots=True)
class Fila:
    """Una ejecución del CSV, ya tipada."""

    level: str
    algorithm: str
    algorithm_label: str
    heuristic: str | None
    repetition: int
    status: str
    success: bool
    cost: int | None
    nodes_expanded: int | None
    frontier_nodes: int | None
    elapsed_seconds: float | None
    wall_seconds: float | None
    solution_valid: bool | None
    pushes: int | None
    simple_steps: int | None
    boxes: int | None
    goals: int | None


@dataclass(frozen=True, slots=True)
class Resumen:
    """Métricas agregadas de un (nivel, algoritmo) sobre sus repeticiones."""

    level: str
    algorithm_label: str
    corridas: int
    exitosas: int
    tiempos: list[float] = field(default_factory=list)
    cost: int | None = None
    nodes_expanded: int | None = None
    frontier_nodes: int | None = None
    metricas_estables: bool = True

    @property
    def tiempo_medio(self) -> float | None:
        return statistics.fmean(self.tiempos) if self.tiempos else None

    @property
    def tiempo_desvio(self) -> float:
        """Desvío estándar muestral; 0 si hay una sola corrida."""
        return statistics.stdev(self.tiempos) if len(self.tiempos) > 1 else 0.0

    @property
    def resolvio(self) -> bool:
        return self.exitosas > 0


@dataclass(frozen=True, slots=True)
class ResumenPooleado:
    """Métricas de un algoritmo+heurística pooleadas sobre TODOS los niveles y repeticiones.

    A diferencia de `Resumen` (un nivel a la vez), acá `corridas`/`exitosas` y
    las listas de valores mezclan todos los niveles: es la base de los
    gráficos que comparan algoritmos sin separar por dificultad. Las listas
    son crudas a propósito — quien las use decide si les calcula media/desvío
    (costo) o se las pasa tal cual a un boxplot (tiempo/nodos/frontera).
    """

    algorithm_label: str
    corridas: int
    exitosas: int
    costs: list[int] = field(default_factory=list)
    tiempos: list[float] = field(default_factory=list)
    nodes_expanded: list[int] = field(default_factory=list)
    frontier_nodes: list[int] = field(default_factory=list)

    @property
    def costo_medio(self) -> float | None:
        return statistics.fmean(self.costs) if self.costs else None

    @property
    def costo_desvio(self) -> float:
        return statistics.stdev(self.costs) if len(self.costs) > 1 else 0.0


@dataclass
class Datos:
    """El CSV entero, más los ejes de presentación ya ordenados."""

    filas: list[Fila]
    archivo: Path
    meta: dict

    @property
    def niveles(self) -> list[str]:
        vistos = {f.level for f in self.filas}
        return sorted(vistos, key=lambda n: (self.cajas(n) or 0, n))

    def cajas(self, level: str) -> int | None:
        """Cantidad de cajas del nivel; es el proxy de dificultad del eje x."""
        for f in self.filas:
            if f.level == level and f.boxes is not None:
                return f.boxes
        return None

    @property
    def algoritmos(self) -> list[str]:
        """Etiquetas de algoritmo en orden canónico."""
        vistos = {f.algorithm_label for f in self.filas}

        def clave(label: str):
            base = label.split(":", 1)[0]
            idx = ORDEN_ALGORITMOS.index(base) if base in ORDEN_ALGORITMOS else len(ORDEN_ALGORITMOS)
            return (idx, label)

        return sorted(vistos, key=clave)

    @property
    def repeticiones(self) -> int:
        return max((f.repetition for f in self.filas), default=0)

    def resumen(self, level: str, algorithm_label: str) -> Resumen:
        """Agrega las repeticiones de una combinación.

        Las métricas no temporales (cost, nodos, frontera) se toman de la
        primera corrida exitosa: los algoritmos son deterministas, así que se
        repiten idénticas. `metricas_estables` avisa si eso no se cumplió, que
        sería señal de un bug en el algoritmo.
        """
        rs = [f for f in self.filas if f.level == level and f.algorithm_label == algorithm_label]
        ok = [f for f in rs if f.status == "ok"]

        estables = True
        for campo in ("cost", "nodes_expanded", "frontier_nodes"):
            distintos = {getattr(f, campo) for f in ok}
            if len(distintos) > 1:
                estables = False

        primero = ok[0] if ok else None
        return Resumen(
            level=level,
            algorithm_label=algorithm_label,
            corridas=len(rs),
            exitosas=len(ok),
            tiempos=[f.elapsed_seconds for f in ok if f.elapsed_seconds is not None],
            cost=primero.cost if primero else None,
            nodes_expanded=primero.nodes_expanded if primero else None,
            frontier_nodes=primero.frontier_nodes if primero else None,
            metricas_estables=estables,
        )

    def matriz(self) -> dict[tuple[str, str], Resumen]:
        """Todos los resúmenes, indexados por (nivel, algoritmo)."""
        return {
            (lv, al): self.resumen(lv, al)
            for lv in self.niveles
            for al in self.algoritmos
        }

    def conteo_estados(self, level: str, algorithm_label: str) -> dict[str, int]:
        conteo: dict[str, int] = {}
        for f in self.filas:
            if f.level == level and f.algorithm_label == algorithm_label:
                conteo[f.status] = conteo.get(f.status, 0) + 1
        return conteo

    def resumen_pooleado(self, algorithm_label: str) -> ResumenPooleado:
        """Poolea un algoritmo sobre TODOS los niveles y repeticiones.

        Mismo filtro `status == "ok"` que `resumen()`: no se reimplementa la
        clasificación de éxito, se reusa fila por fila. Si el algoritmo solo
        resolvió en algunos niveles, `exitosas` refleja nada más esas corridas
        (no se rellena ni imputa lo que falta).
        """
        rs = [f for f in self.filas if f.algorithm_label == algorithm_label]
        ok = [f for f in rs if f.status == "ok"]
        return ResumenPooleado(
            algorithm_label=algorithm_label,
            corridas=len(rs),
            exitosas=len(ok),
            costs=[f.cost for f in ok if f.cost is not None],
            tiempos=[f.elapsed_seconds for f in ok if f.elapsed_seconds is not None],
            nodes_expanded=[f.nodes_expanded for f in ok if f.nodes_expanded is not None],
            frontier_nodes=[f.frontier_nodes for f in ok if f.frontier_nodes is not None],
        )

    def conteo_estados_pooleado(self, algorithm_label: str) -> dict[str, int]:
        """Igual que `conteo_estados`, pero pooleado sobre todos los niveles."""
        conteo: dict[str, int] = {}
        for f in self.filas:
            if f.algorithm_label == algorithm_label:
                conteo[f.status] = conteo.get(f.status, 0) + 1
        return conteo

    @property
    def invalidas(self) -> list[Fila]:
        """Filas `ok` cuya solución no pasó la verificación del motor."""
        return [f for f in self.filas if f.status == "ok" and f.solution_valid is False]


def listar_csvs(directorio: Path) -> list[Path]:
    """CSVs disponibles, del más reciente al más viejo."""
    return sorted(directorio.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)


def cargar(archivo: str | Path) -> Datos:
    """Lee un CSV de resultados y lo devuelve tipado."""
    ruta = Path(archivo)
    try:
        with ruta.open(newline="", encoding="utf-8") as fh:
            crudas = list(csv.DictReader(fh))
    except FileNotFoundError:
        raise DatosError(f"No se encontró el CSV: {ruta}") from None

    if not crudas:
        raise DatosError(
            f"{ruta} no tiene filas (¿la corrida se cortó antes de terminar?). "
            f"Elegí otro archivo con --archivo."
        )

    requeridas = {"level", "algorithm_label", "status", "repetition"}
    faltan = requeridas - set(crudas[0])
    if faltan:
        raise DatosError(f"{ruta}: faltan las columnas {sorted(faltan)}")

    filas = [
        Fila(
            level=r["level"],
            algorithm=r.get("algorithm", ""),
            algorithm_label=r["algorithm_label"],
            heuristic=r.get("heuristic") or None,
            repetition=_num(r.get("repetition"), int) or 0,
            status=r["status"],
            success=_bool(r.get("success")) or False,
            cost=_num(r.get("cost"), int),
            nodes_expanded=_num(r.get("nodes_expanded"), int),
            frontier_nodes=_num(r.get("frontier_nodes"), int),
            elapsed_seconds=_num(r.get("elapsed_seconds"), float),
            wall_seconds=_num(r.get("wall_seconds"), float),
            solution_valid=_bool(r.get("solution_valid")),
            pushes=_num(r.get("pushes"), int),
            simple_steps=_num(r.get("simple_steps"), int),
            boxes=_num(r.get("boxes"), int),
            goals=_num(r.get("goals"), int),
        )
        for r in crudas
    ]

    primera = crudas[0]
    meta = {
        "run_id": primera.get("run_id", ""),
        "executor": primera.get("executor", ""),
        "workers": primera.get("workers", ""),
        "timeout_seconds": _num(primera.get("timeout_seconds"), float),
        "started_at_utc": primera.get("started_at_utc", ""),
        "hostname": primera.get("hostname", ""),
        "python_version": primera.get("python_version", ""),
        "git_commit": primera.get("git_commit", ""),
    }

    return Datos(filas=filas, archivo=ruta, meta=meta)
