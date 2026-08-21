"""Carga de `config.json`: qué nivel resolver, con qué algoritmo y heurística."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_LEVELS_DIR = Path(__file__).resolve().parent / "levels"
DEFAULT_VISUALIZER_DIR = Path(__file__).resolve().parent / "visualizer"


def _default_visualizer_output(level: str, algorithm: str, heuristic: str | None) -> Path:
    level_stem = Path(level).stem
    heuristic_part = heuristic or "sin-heuristica"
    return DEFAULT_VISUALIZER_DIR / f"last_run_{level_stem}_{algorithm}_{heuristic_part}.html"


class ConfigError(ValueError):
    """`config.json` falta, tiene JSON inválido, o le falta una clave requerida."""


@dataclass(frozen=True, slots=True)
class RunConfig:
    """Una corrida: un nivel + un algoritmo (+ heurística, si aplica)."""

    level: str
    algorithm: str
    heuristic: str | None
    levels_dir: Path
    visualize: bool
    visualizer_output: Path

    def level_path(self) -> Path:
        """`level` puede ser el stem (busca en `levels_dir`) o una ruta a un `.txt`."""
        as_path = Path(self.level)
        if as_path.suffix == ".txt":
            return as_path
        return self.levels_dir / f"{self.level}.txt"


def load_config(path: str | Path) -> RunConfig:
    """Lee y valida `config.json`; tira `ConfigError` si algo falta."""
    config_path = Path(path)
    try:
        raw = json.loads(config_path.read_text())
    except FileNotFoundError as exc:
        raise ConfigError(f"No se encontró el archivo de config: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{config_path} no es JSON válido: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError(f"{config_path} tiene que ser un objeto JSON")

    missing = [key for key in ("level", "algorithm") if key not in raw]
    if missing:
        raise ConfigError(f"{config_path}: faltan las claves {missing}")

    levels_dir = Path(raw["levels_dir"]) if "levels_dir" in raw else DEFAULT_LEVELS_DIR
    if "visualizer_output" in raw:
        visualizer_output = Path(raw["visualizer_output"])
    else:
        visualizer_output = _default_visualizer_output(
            raw["level"], raw["algorithm"], raw.get("heuristic")
        )

    return RunConfig(
        level=raw["level"],
        algorithm=raw["algorithm"],
        heuristic=raw.get("heuristic"),
        levels_dir=levels_dir,
        visualize=bool(raw.get("visualize", True)),
        visualizer_output=visualizer_output,
    )
