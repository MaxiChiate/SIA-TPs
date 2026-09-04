"""Config loading: parse and validate a run's JSON config into ready-to-use objects.

The engine and its operators are wired together entirely by name, resolved through
``ga.registry``. Any malformed or unknown value raises ``ConfigError`` with a
dotted path to the offending field, so a bad config fails fast at load time
instead of surfacing as a confusing error deep inside a run.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import registry
from .core.engine import EngineConfig, StopContext, Stopping
from .core.problem import Problem
from .core.rng import Rng, make_rng

_TOP_LEVEL_KEYS = {"seed", "engine", "operators", "stopping", "problem"}
_ENGINE_KEYS = {"n", "k", "pc", "pm", "max_generations"}
_ENGINE_OPTIONAL_KEYS = {"processes"}
_OPERATOR_CATEGORIES = ("parent_selection", "crossover", "mutation", "survival")


class ConfigError(Exception):
    """A config file or dict failed validation; the message names the bad field."""


@dataclass(slots=True, frozen=True)
class LoadedConfig:
    """Everything a caller needs to run a GA, fully resolved from a config."""

    seed: int
    rng: Rng
    problem: Problem
    engine_config: EngineConfig
    raw: dict[str, Any]


def load_config(source: str | Path | dict[str, Any]) -> LoadedConfig:
    """Load, validate and resolve a run config from a JSON file path or a dict."""
    raw = _expect_dict(_read(source), "")
    _check_keys(raw, _TOP_LEVEL_KEYS, "")

    seed = _require(raw, "seed", "")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ConfigError(f"seed: expected int, got {type(seed).__name__}")
    rng = make_rng(seed)

    operators_section = _require(raw, "operators", "")
    callables, extra_params = _resolve_operators(operators_section)
    stopping = _resolve_stopping(raw.get("stopping", []))

    engine_section = _require(raw, "engine", "")
    engine_config = _build_engine_config(
        engine_section, callables, stopping, extra_params
    )

    problem_section = _require(raw, "problem", "")
    problem = _build_problem(problem_section)

    return LoadedConfig(
        seed=seed, rng=rng, problem=problem, engine_config=engine_config, raw=raw
    )


# -- generic helpers ----------------------------------------------------------


def _read(source: str | Path | dict[str, Any]) -> dict[str, Any]:
    if isinstance(source, dict):
        return source
    path = Path(source)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as err:
        raise ConfigError(f"cannot read config file {path}: {err}") from err
    try:
        return json.loads(text)
    except json.JSONDecodeError as err:
        raise ConfigError(f"{path} is not valid JSON: {err}") from err


def _expect_dict(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        where = path or "<root>"
        raise ConfigError(f"{where}: expected an object, got {type(value).__name__}")
    return value


def _expect_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ConfigError(f"{path}: expected a list, got {type(value).__name__}")
    return value


def _check_keys(section: dict[str, Any], allowed: set[str], path: str) -> None:
    unknown = set(section) - allowed
    if unknown:
        where = path or "<root>"
        raise ConfigError(f"{where}: unknown key(s) {sorted(unknown)}")


def _require(section: dict[str, Any], key: str, path: str) -> Any:
    if key not in section:
        where = f"{path}.{key}" if path else key
        raise ConfigError(f"missing required key {where!r}")
    return section[key]


# -- operators ------------------------------------------------------------


def _resolve_operators(
    operators_section: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resolve each operator's callable and merge their static params.

    Returns ``(callables_by_category, merged_extra_params)``. Every operator's
    own ``params`` block folds into one shared dict because ``parent_selection``,
    ``crossover``, ``mutation`` and ``survival`` all end their call signature in a
    generic ``params: dict`` (see ``ga.core.engine``) — the engine threads it into
    every operator call each generation, so there is no need for per-category
    binding logic here.
    """
    operators_section = _expect_dict(operators_section, "operators")
    _check_keys(operators_section, set(_OPERATOR_CATEGORIES), "operators")
    callables: dict[str, Any] = {}
    merged_params: dict[str, Any] = {}
    for category in _OPERATOR_CATEGORIES:
        path = f"operators.{category}"
        entry = _expect_dict(_require(operators_section, category, "operators"), path)
        _check_keys(entry, {"name", "params"}, path)
        name = _require(entry, "name", path)
        try:
            callables[category] = registry.get(category, name)
        except registry.RegistryError as err:
            raise ConfigError(f"{path}: {err}") from err

        params = _expect_dict(entry.get("params", {}), f"{path}.params")
        collisions = set(merged_params) & set(params)
        if collisions:
            raise ConfigError(
                f"operators.{category}.params: key(s) {sorted(collisions)} "
                "collide with another operator's params"
            )
        merged_params.update(params)
    return callables, merged_params


# -- stopping -----------------------------------------------------------------


def _resolve_stopping(entries: list[dict[str, Any]]) -> Stopping | None:
    """Combine every ``stopping`` entry into one callable, OR'd together.

    ``Stopping`` is ``Callable[[StopContext], str | None]`` with no params dict
    (``StopContext`` is a closed dataclass, unlike the other operator categories),
    so each criterion's static params are bound at load time via a closure
    instead of flowing through a shared dict.
    """
    if not entries:
        return None
    entries = _expect_list(entries, "stopping")
    bound = [_bind_stopping_criterion(entry, index) for index, entry in enumerate(entries)]

    def combined(context: StopContext) -> str | None:
        for criterion in bound:
            reason = criterion(context)
            if reason is not None:
                return reason
        return None

    return combined


def _bind_stopping_criterion(entry: Any, index: int):
    path = f"stopping[{index}]"
    entry = _expect_dict(entry, path)
    _check_keys(entry, {"name", "params"}, path)
    name = _require(entry, "name", path)
    params = _expect_dict(entry.get("params", {}), f"{path}.params")
    try:
        fn = registry.get("stopping", name)
    except registry.RegistryError as err:
        raise ConfigError(f"{path}: {err}") from err
    return lambda context: fn(context, **params)


# -- engine ---------------------------------------------------------------


def _build_engine_config(
    engine_section: dict[str, Any],
    callables: dict[str, Any],
    stopping: Stopping | None,
    extra_params: dict[str, Any],
) -> EngineConfig:
    engine_section = _expect_dict(engine_section, "engine")
    _check_keys(engine_section, _ENGINE_KEYS | _ENGINE_OPTIONAL_KEYS, "engine")
    kwargs = {key: _require(engine_section, key, "engine") for key in _ENGINE_KEYS}
    processes = engine_section.get("processes", 1)
    if not isinstance(processes, int) or isinstance(processes, bool):
        raise ConfigError(
            f"engine.processes: expected int, got {type(processes).__name__}"
        )
    try:
        return EngineConfig(
            n=kwargs["n"],
            k=kwargs["k"],
            pc=kwargs["pc"],
            pm=kwargs["pm"],
            max_generations=kwargs["max_generations"],
            parent_selection=callables["parent_selection"],
            crossover=callables["crossover"],
            mutation=callables["mutation"],
            survival=callables["survival"],
            stopping=stopping,
            extra_params=extra_params,
            workers=processes,
        )
    except (ValueError, TypeError) as err:
        raise ConfigError(f"engine: {err}") from err


# -- problem --------------------------------------------------------------


def _build_problem(problem_section: dict[str, Any]) -> Problem:
    problem_section = _expect_dict(problem_section, "problem")
    _check_keys(problem_section, {"type", "params"}, "problem")
    problem_type = _require(problem_section, "type", "problem")
    params = _expect_dict(problem_section.get("params", {}), "problem.params")
    try:
        factory = registry.get("problem", problem_type)
    except registry.RegistryError as err:
        raise ConfigError(f"problem: {err}") from err
    try:
        return factory(params)
    except Exception as err:  # a plug-in's own errors all fold into ConfigError
        raise ConfigError(f"problem.params: {err}") from err
