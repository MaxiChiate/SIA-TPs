"""Carga y validación del config del runner (`config.yaml` o `config.json`).

El config describe una *tanda* de experimentos: qué niveles, qué algoritmos,
cuántas repeticiones, con cuánto paralelismo y dónde dejar el CSV.

Formato preferido: YAML (necesita PyYAML). Si PyYAML no está instalado y el
config es `.yaml`/`.yml`, se busca automáticamente un `.json` hermano con el
mismo nombre -- el esquema de claves es idéntico en los dos formatos.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

# Raíz del proyecto (donde viven `sokoban/`, `run.py` y `config.json`).
PROJECT_ROOT = Path(__file__).resolve().parent.parent

EXECUTORS = ("process", "thread")

DEFAULT_LEVELS_DIR = PROJECT_ROOT / "sokoban" / "levels"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "analisis" / "resultados"
DEFAULT_HEURISTIC = "manhattan_sum"


class BenchmarkConfigError(ValueError):
    """El config no existe, no parsea, o tiene un valor inválido."""


@dataclass(frozen=True, slots=True)
class AlgorithmSpec:
    """Un algoritmo a correr, con su heurística ya resuelta (o `None`)."""

    name: str
    heuristic: str | None

    @property
    def label(self) -> str:
        """Identificador estable para agrupar en el análisis.

        `astar:manhattan_sum` vs `bfs` -- distingue la misma búsqueda con
        distintas heurísticas, que en el CSV son series distintas.
        """
        return f"{self.name}:{self.heuristic}" if self.heuristic else self.name


@dataclass(frozen=True, slots=True)
class BenchmarkConfig:
    """Una tanda completa de experimentos."""

    executor: str
    workers: int
    repetitions: int
    timeout_seconds: float | None
    memory_limit_mb: int | None
    levels: tuple[str, ...]
    levels_dir: Path
    algorithms: tuple[AlgorithmSpec, ...]
    output_dir: Path
    output_file: str | None
    include_solution: bool
    source_path: Path

    def level_path(self, level: str) -> Path:
        """`level` es el stem de un archivo en `levels_dir`, o una ruta a un `.txt`."""
        as_path = Path(level)
        if as_path.suffix == ".txt":
            return as_path if as_path.is_absolute() else PROJECT_ROOT / as_path
        return self.levels_dir / f"{level}.txt"

    def output_path(self, run_id: str) -> Path:
        """Archivo CSV de salida. Por default lleva el `run_id` en el nombre."""
        name = self.output_file or f"results_{run_id}.csv"
        return self.output_dir / name

    def total_runs(self) -> int:
        return len(self.levels) * len(self.algorithms) * self.repetitions


def _resolve_path(raw: str | Path, default: Path) -> Path:
    """Las rutas relativas del config se resuelven contra la raíz del proyecto.

    Así el runner se comporta igual corriéndolo desde la raíz del repo o desde
    `analisis/`, en vez de depender del cwd.
    """
    if raw is None:
        return default
    path = Path(raw)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _load_raw(config_path: Path) -> tuple[dict, Path]:
    """Lee el config como dict; devuelve también el archivo realmente usado.

    El path de vuelta puede diferir del pedido cuando cae el fallback de
    YAML -> JSON, y es el que queda registrado en el CSV.
    """
    if config_path.suffix in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore[import-untyped]
        except ImportError:
            # Fallback documentado: mismo esquema de claves, en JSON.
            sibling = config_path.with_suffix(".json")
            if sibling.is_file():
                return _load_json(sibling), sibling
            raise BenchmarkConfigError(
                f"{config_path} es YAML pero PyYAML no está instalado. "
                f"Instalá con `pip install pyyaml` (ver analisis/requirements.txt), "
                f"o dejá el mismo config en {sibling.name}."
            ) from None
        try:
            raw = yaml.safe_load(config_path.read_text())
        except FileNotFoundError:
            raise BenchmarkConfigError(f"No se encontró el config: {config_path}") from None
        except yaml.YAMLError as exc:
            raise BenchmarkConfigError(f"{config_path} no es YAML válido: {exc}") from exc
        if raw is None:
            raise BenchmarkConfigError(f"{config_path} está vacío")
        return raw, config_path

    return _load_json(config_path), config_path


def _load_json(config_path: Path) -> dict:
    try:
        return json.loads(config_path.read_text())
    except FileNotFoundError:
        raise BenchmarkConfigError(f"No se encontró el config: {config_path}") from None
    except json.JSONDecodeError as exc:
        raise BenchmarkConfigError(f"{config_path} no es JSON válido: {exc}") from exc


def _parse_levels(raw_levels, levels_dir: Path) -> tuple[str, ...]:
    """Acepta una lista de niveles, o `"all"` para tomar todos los `.txt` de `levels_dir`.

    Ignora los `*.solution.txt`, que son soluciones de referencia y no niveles.
    """
    if isinstance(raw_levels, str):
        if raw_levels.strip().lower() != "all":
            raise BenchmarkConfigError(
                f"`levels` como string solo acepta \"all\"; recibí {raw_levels!r}"
            )
        found = sorted(
            path.stem
            for path in levels_dir.glob("*.txt")
            if not path.name.endswith(".solution.txt")
        )
        if not found:
            raise BenchmarkConfigError(f"`levels: all` pero no hay niveles en {levels_dir}")
        return tuple(found)

    if not isinstance(raw_levels, list) or not raw_levels:
        raise BenchmarkConfigError("`levels` tiene que ser una lista no vacía (o \"all\")")

    levels = []
    for item in raw_levels:
        if not isinstance(item, str):
            raise BenchmarkConfigError(f"`levels` debe contener strings; recibí {item!r}")
        levels.append(item)
    return tuple(levels)


def _parse_algorithms(raw_algorithms) -> tuple[AlgorithmSpec, ...]:
    """Cada item puede ser un string (`- bfs`) o un mapping (`{name, heuristic}`)."""
    from sokoban.search import ALGORITHMS, HEURISTICS, INFORMED_ALGORITHMS

    if not isinstance(raw_algorithms, list) or not raw_algorithms:
        raise BenchmarkConfigError("`algorithms` tiene que ser una lista no vacía")

    specs: list[AlgorithmSpec] = []
    for item in raw_algorithms:
        if isinstance(item, str):
            name, heuristic = item, None
        elif isinstance(item, dict):
            if "name" not in item:
                raise BenchmarkConfigError(f"Item de `algorithms` sin clave `name`: {item!r}")
            name = item["name"]
            heuristic = item.get("heuristic")
        else:
            raise BenchmarkConfigError(
                f"Item de `algorithms` debe ser string o mapping; recibí {item!r}"
            )

        if name not in ALGORITHMS:
            raise BenchmarkConfigError(
                f"Algoritmo desconocido {name!r}. Disponibles: {sorted(ALGORITHMS)}."
            )

        if name in INFORMED_ALGORITHMS:
            # Mismo default que `build_agent`, pero explícito en el CSV para que
            # el análisis no tenga que adivinar con qué heurística corrió.
            heuristic = heuristic or DEFAULT_HEURISTIC
            if heuristic not in HEURISTICS:
                raise BenchmarkConfigError(
                    f"Heurística desconocida {heuristic!r} para {name!r}. "
                    f"Disponibles: {sorted(HEURISTICS)}."
                )
        else:
            # Los no informados ignoran la heurística; la anulamos para que no
            # aparezca en el CSV sugiriendo que influyó en el resultado.
            heuristic = None

        spec = AlgorithmSpec(name=name, heuristic=heuristic)
        if spec in specs:
            raise BenchmarkConfigError(f"`algorithms` tiene un duplicado: {spec.label}")
        specs.append(spec)

    return tuple(specs)


def _positive_int(raw, key: str, default: int) -> int:
    value = default if raw is None else raw
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise BenchmarkConfigError(f"`{key}` tiene que ser un entero >= 1; recibí {raw!r}")
    return value


def load_benchmark_config(path: str | Path) -> BenchmarkConfig:
    """Lee y valida el config del runner. Tira `BenchmarkConfigError` si algo no cierra."""
    config_path = Path(path)
    if not config_path.is_absolute() and not config_path.is_file():
        # Permite `python analisis/main.py config.yaml` desde cualquier cwd.
        candidate = PROJECT_ROOT / "analisis" / config_path
        if candidate.is_file():
            config_path = candidate

    raw, config_path = _load_raw(config_path)
    if not isinstance(raw, dict):
        raise BenchmarkConfigError(f"{config_path} tiene que ser un mapping en la raíz")

    unknown = set(raw) - {
        "executor", "workers", "repetitions", "timeout_seconds", "memory_limit_mb",
        "levels", "levels_dir", "algorithms", "output_dir", "output_file",
        "include_solution",
    }
    if unknown:
        raise BenchmarkConfigError(f"{config_path}: claves desconocidas {sorted(unknown)}")

    missing = [key for key in ("levels", "algorithms") if key not in raw]
    if missing:
        raise BenchmarkConfigError(f"{config_path}: faltan las claves {missing}")

    executor = raw.get("executor", "process")
    if executor not in EXECUTORS:
        raise BenchmarkConfigError(
            f"`executor` tiene que ser uno de {list(EXECUTORS)}; recibí {executor!r}"
        )

    timeout_raw = raw.get("timeout_seconds", 60)
    if timeout_raw is None:
        timeout_seconds = None
    elif isinstance(timeout_raw, (int, float)) and not isinstance(timeout_raw, bool) and timeout_raw > 0:
        timeout_seconds = float(timeout_raw)
    else:
        raise BenchmarkConfigError(
            f"`timeout_seconds` tiene que ser un número > 0, o null; recibí {timeout_raw!r}"
        )

    memory_raw = raw.get("memory_limit_mb")
    if memory_raw is None:
        memory_limit_mb = None
    elif isinstance(memory_raw, int) and not isinstance(memory_raw, bool) and memory_raw > 0:
        memory_limit_mb = memory_raw
    else:
        raise BenchmarkConfigError(
            f"`memory_limit_mb` tiene que ser un entero > 0, o null; recibí {memory_raw!r}"
        )

    levels_dir = _resolve_path(raw.get("levels_dir"), DEFAULT_LEVELS_DIR)
    if not levels_dir.is_dir():
        raise BenchmarkConfigError(f"`levels_dir` no es un directorio: {levels_dir}")

    config = BenchmarkConfig(
        executor=executor,
        workers=_positive_int(raw.get("workers"), "workers", 4),
        repetitions=_positive_int(raw.get("repetitions"), "repetitions", 3),
        timeout_seconds=timeout_seconds,
        memory_limit_mb=memory_limit_mb,
        levels=_parse_levels(raw["levels"], levels_dir),
        levels_dir=levels_dir,
        algorithms=_parse_algorithms(raw["algorithms"]),
        output_dir=_resolve_path(raw.get("output_dir"), DEFAULT_OUTPUT_DIR),
        output_file=raw.get("output_file"),
        include_solution=bool(raw.get("include_solution", True)),
        source_path=config_path,
    )

    missing_levels = [lvl for lvl in config.levels if not config.level_path(lvl).is_file()]
    if missing_levels:
        raise BenchmarkConfigError(
            f"No se encontraron los niveles {missing_levels} "
            f"(buscados en {config.levels_dir})"
        )

    return config
