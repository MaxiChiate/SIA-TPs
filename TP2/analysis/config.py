"""Parse and validate ``analysis/sweep.json``, the experiment runner's config.

A sweep config describes a *batch* of runs: one base ``config.json``, a set of
variants that each override some of its keys, and the seeds to repeat every
variant with. The runner's job is the cartesian product ``variants x seeds``.

Overrides are dotted paths into the base config (``engine.max_generations``,
``operators.parent_selection.name``), so a variant states only what it changes
and the rest stays pinned - which is the whole point of the "one knob at a
time" methodology.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# The TP2 root, where ``run.py``, ``config.json`` and ``images/`` live.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "analysis" / "results"
_TOP_LEVEL_KEYS = {
    "base_config",
    "seeds",
    "workers",
    "output_dir",
    "overrides",
    "variants",
    "sweep",
}


class SweepConfigError(ValueError):
    """The sweep config is missing, unparseable, or holds an invalid value."""


@dataclass(frozen=True, slots=True)
class Variant:
    """One point of the sweep: a label plus the overrides that define it."""

    label: str
    overrides: dict[str, Any]


@dataclass(frozen=True, slots=True)
class SweepConfig:
    """A whole batch of experiments, resolved and validated."""

    base_config: dict[str, Any]
    base_config_path: Path
    variants: tuple[Variant, ...]
    seeds: tuple[int, ...]
    workers: int
    output_dir: Path
    source_path: Path

    def total_runs(self) -> int:
        return len(self.variants) * len(self.seeds)


def set_by_path(config: dict[str, Any], dotted_path: str, value: Any) -> None:
    """Set ``config["a"]["b"] = value`` from the path ``"a.b"``, in place.

    Every segment but the last must already exist and be an object: a typo in
    an override should fail loudly here rather than silently adding a key the
    engine will never read.
    """
    segments = dotted_path.split(".")
    target: Any = config
    for index, segment in enumerate(segments[:-1]):
        if not isinstance(target, dict) or segment not in target:
            so_far = ".".join(segments[: index + 1])
            raise SweepConfigError(
                f"override path {dotted_path!r}: {so_far!r} does not exist in the "
                "base config"
            )
        target = target[segment]
    if not isinstance(target, dict):
        raise SweepConfigError(
            f"override path {dotted_path!r}: {'.'.join(segments[:-1])!r} is not an object"
        )
    target[segments[-1]] = value


def apply_overrides(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """A deep copy of ``base`` with every dotted-path override applied."""
    result = copy.deepcopy(base)
    for dotted_path, value in overrides.items():
        set_by_path(result, dotted_path, value)
    return result


def config_for(sweep: SweepConfig, variant: Variant, seed: int) -> dict[str, Any]:
    """The fully resolved run config for one (variant, seed) pair.

    ``engine.processes`` is forced to 1: the runner already parallelizes across
    runs, and letting each run open its own pool on top of that oversubscribes
    the CPU and nests process pools.
    """
    config = apply_overrides(sweep.base_config, variant.overrides)
    config["seed"] = seed
    if isinstance(config.get("engine"), dict):
        config["engine"]["processes"] = 1
    return config


# -- parsing ------------------------------------------------------------------


def _read_json(path: Path, what: str) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SweepConfigError(f"{what} not found: {path}") from None
    except json.JSONDecodeError as err:
        raise SweepConfigError(f"{path} is not valid JSON: {err}") from err
    if not isinstance(raw, dict):
        raise SweepConfigError(f"{path}: expected an object at the root")
    return raw


def _resolve_path(raw: str | None, default: Path) -> Path:
    """Relative paths in the sweep config resolve against the project root.

    So the runner behaves the same whether it is invoked from ``TP2/`` or from
    ``TP2/analysis/``, instead of depending on the cwd.
    """
    if raw is None:
        return default
    path = Path(raw)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _positive_int(raw: Any, key: str, default: int) -> int:
    value = default if raw is None else raw
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise SweepConfigError(f"{key!r} must be an int >= 1, got {raw!r}")
    return value


def _parse_seeds(raw: Any) -> tuple[int, ...]:
    if raw is None:
        return (1,)
    if not isinstance(raw, list) or not raw:
        raise SweepConfigError("'seeds' must be a non-empty list of ints")
    for seed in raw:
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise SweepConfigError(f"'seeds' must hold ints, got {seed!r}")
    if len(set(raw)) != len(raw):
        raise SweepConfigError(f"'seeds' has duplicates: {raw}")
    return tuple(raw)


def _parse_sweep_shorthand(raw: Any) -> list[Variant]:
    """``{"path": ..., "values": [...]}`` -> one variant per value.

    Sugar for the common case of varying a single knob; ``variants`` stays
    available for anything needing several keys changed at once.
    """
    if not isinstance(raw, dict):
        raise SweepConfigError("'sweep' must be an object with 'path' and 'values'")
    unknown = set(raw) - {"path", "values"}
    if unknown:
        raise SweepConfigError(f"sweep: unknown key(s) {sorted(unknown)}")
    path = raw.get("path")
    values = raw.get("values")
    if not isinstance(path, str) or not path:
        raise SweepConfigError("sweep.path must be a non-empty string")
    if not isinstance(values, list) or not values:
        raise SweepConfigError("sweep.values must be a non-empty list")
    return [Variant(label=str(value), overrides={path: value}) for value in values]


def _parse_variants(raw: Any) -> list[Variant]:
    if not isinstance(raw, list) or not raw:
        raise SweepConfigError("'variants' must be a non-empty list")
    variants: list[Variant] = []
    for index, entry in enumerate(raw):
        where = f"variants[{index}]"
        if not isinstance(entry, dict):
            raise SweepConfigError(f"{where}: expected an object")
        unknown = {key for key in entry if not key.startswith("_")} - {"label", "set"}
        if unknown:
            raise SweepConfigError(f"{where}: unknown key(s) {sorted(unknown)}")
        label = entry.get("label")
        if not isinstance(label, str) or not label:
            raise SweepConfigError(f"{where}.label must be a non-empty string")
        overrides = entry.get("set", {})
        if not isinstance(overrides, dict):
            raise SweepConfigError(f"{where}.set must be an object")
        variants.append(Variant(label=label, overrides=overrides))
    labels = [variant.label for variant in variants]
    duplicates = {label for label in labels if labels.count(label) > 1}
    if duplicates:
        raise SweepConfigError(f"duplicate variant label(s): {sorted(duplicates)}")
    return variants


def _validate_runnable(sweep: SweepConfig) -> None:
    """Load every variant through ``ga.config`` so a typo fails now, not in an hour.

    Imported here rather than at module scope so that merely importing this
    module does not drag in Pillow/numpy via the problem plug-in.
    """
    import ga.operators  # noqa: F401 -- registers the GA operators by name
    import problems.triangles  # noqa: F401 -- registers the "triangles" problem
    from ga.config import ConfigError, load_config

    for variant in sweep.variants:
        resolved = config_for(sweep, variant, sweep.seeds[0])
        try:
            load_config(resolved)
        except ConfigError as err:
            raise SweepConfigError(f"variant {variant.label!r} is not runnable: {err}") from err


def load_sweep_config(path: str | Path) -> SweepConfig:
    """Read, validate and resolve a sweep config. Raises ``SweepConfigError``."""
    sweep_path = Path(path)
    if not sweep_path.is_absolute() and not sweep_path.is_file():
        # Allows `python3 analysis/main.py serie_a.json` from any cwd.
        candidate = PROJECT_ROOT / "analysis" / sweep_path
        if candidate.is_file():
            sweep_path = candidate

    raw = _read_json(sweep_path, "sweep config")
    # Keys starting with "_" are ignored, so a JSON file can carry comments.
    unknown = {key for key in raw if not key.startswith("_")} - _TOP_LEVEL_KEYS
    if unknown:
        raise SweepConfigError(f"{sweep_path}: unknown key(s) {sorted(unknown)}")

    if ("variants" in raw) == ("sweep" in raw):
        raise SweepConfigError("give exactly one of 'variants' or 'sweep'")

    base_config_path = _resolve_path(raw.get("base_config"), PROJECT_ROOT / "config.json")
    base_config = _read_json(base_config_path, "base config")

    shared_overrides = raw.get("overrides", {})
    if not isinstance(shared_overrides, dict):
        raise SweepConfigError("'overrides' must be an object")
    if shared_overrides:
        # Applied once here so every variant inherits them; a variant's own
        # overrides win because they are applied afterwards, on top of this.
        base_config = apply_overrides(base_config, shared_overrides)

    variants = (
        _parse_sweep_shorthand(raw["sweep"])
        if "sweep" in raw
        else _parse_variants(raw["variants"])
    )

    sweep = SweepConfig(
        base_config=base_config,
        base_config_path=base_config_path,
        variants=tuple(variants),
        seeds=_parse_seeds(raw.get("seeds")),
        workers=_positive_int(raw.get("workers"), "workers", 4),
        output_dir=_resolve_path(raw.get("output_dir"), DEFAULT_OUTPUT_DIR),
        source_path=sweep_path,
    )
    _validate_runnable(sweep)
    return sweep
