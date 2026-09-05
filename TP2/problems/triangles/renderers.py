"""Scoring backends: allele vector -> fitness, behind one interface.

Rendering and comparing pixels is ~90% of a run's wall clock, so it is the one
place worth having more than one implementation of. Following the same shape as
``TP1/Ejercicio2_sokoban/analisis/runner.py``'s ``thread``/``process`` backends,
the choice is a name in the config and nothing upstream of it changes:

``pillow``  -- ``render_triangles`` plus a numpy MSE, i.e. the original
               implementation. Kept as the reference oracle the other backend is
               validated against, and as the fallback that needs no toolchain.
``rust``    -- the ``triangles_native`` extension module. Not built yet.
``auto``    -- ``rust`` when the extension is importable, ``pillow`` otherwise,
               so a checkout with no Rust toolchain still runs.

A ``Renderer`` owns a ``RenderSpec``: the target pixels and every decode rule
that never changes during a run. That is what lets a native backend upload the
target once at construction rather than on every call.

Only the hot path lives here. ``renderer.render_triangles`` stays Pillow-only
and keeps serving ``export.py``: final images, snapshots and the GIF run a
handful of times per run, need a real ``PIL.Image``, and are not worth porting.
"""

from __future__ import annotations

import abc
from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

import numpy as np
from PIL import Image

from .colorspace import ColorSpace
from .fitness import mean_squared_error, pixel_similarity
from .genotype import triangles_from_alleles
from .renderer import render_triangles

_MIN_BASELINE_MSE = 1e-9


@dataclass(frozen=True, slots=True)
class RenderSpec:
    """Everything about a run that a scorer needs and that never changes.

    ``target_rgb`` is raw row-major RGB bytes rather than a numpy array so the
    spec stays picklable and hands straight to a native backend; a backend that
    wants an array builds its own view once.
    """

    width: int
    height: int
    background_rgb: tuple[int, int, int]
    color_space: ColorSpace
    triangle_count: int
    target_rgb: bytes
    baseline_mse: float

    @classmethod
    def build(
        cls,
        image_path: str,
        width: int,
        height: int,
        background_rgb: tuple[int, int, int],
        color_space: ColorSpace,
        triangle_count: int,
    ) -> "RenderSpec":
        target = Image.open(image_path).convert("RGB").resize((width, height))
        target_rgb = target.tobytes()
        return cls(
            width=width,
            height=height,
            background_rgb=background_rgb,
            color_space=color_space,
            triangle_count=triangle_count,
            target_rgb=target_rgb,
            baseline_mse=_baseline_mse(target_rgb, background_rgb),
        )

    def target_array(self) -> np.ndarray:
        """The target as an ``(H, W, 3)`` uint8 array."""
        return np.frombuffer(self.target_rgb, dtype=np.uint8).reshape(
            self.height, self.width, 3
        )


def _baseline_mse(target_rgb: bytes, background_rgb: tuple[int, int, int]) -> float:
    """MSE of the blank canvas against the target - the fitness denominator.

    Computed in closed form instead of by rendering an empty triangle list: the
    blank canvas is a constant colour, so this is the same number without a
    Pillow call, and both backends then normalise against an identical value
    rather than against their own idea of a blank canvas.
    """
    target = np.frombuffer(target_rgb, dtype=np.uint8).reshape(-1, 3).astype(np.float64)
    background = np.asarray(background_rgb, dtype=np.float64)
    difference = target - background
    return max(float(np.mean(difference * difference)), _MIN_BASELINE_MSE)


class Renderer(abc.ABC):
    """Scores allele vectors against one run's target."""

    name: ClassVar[str]

    def __init__(self, spec: RenderSpec) -> None:
        self.spec = spec

    @abc.abstractmethod
    def score(self, alleles: Sequence[float]) -> float:
        """Fitness of one genotype. Higher is better, as ``Problem`` requires."""

    def score_batch(self, genomes: Sequence[Sequence[float]]) -> list[float]:
        """Fitness of several genotypes, in order. Default: one at a time."""
        return [self.score(alleles) for alleles in genomes]

    def owns_parallelism(self) -> bool:
        """True if ``score_batch`` already spreads the batch across cores."""
        return False

    def describe(self) -> dict:
        return {"renderer": self.name}


class PillowRenderer(Renderer):
    """The original implementation: ``render_triangles`` plus a numpy MSE."""

    name = "pillow"

    def __init__(self, spec: RenderSpec) -> None:
        super().__init__(spec)
        self._target_array = spec.target_array()

    def score(self, alleles: Sequence[float]) -> float:
        spec = self.spec
        triangles = triangles_from_alleles(
            list(alleles), spec.triangle_count, spec.width, spec.height, spec.color_space
        )
        rendered = render_triangles(
            triangles, spec.width, spec.height, spec.background_rgb
        )
        return pixel_similarity(rendered, self._target_array, spec.baseline_mse)

    def mse(self, alleles: Sequence[float]) -> float:
        """Raw mean squared error, before the fitness normalisation.

        The parity tests compare backends on this rather than on fitness:
        fitness clamps at 0 for anything worse than a blank canvas, and that
        floor swallows the difference being measured.
        """
        spec = self.spec
        triangles = triangles_from_alleles(
            list(alleles), spec.triangle_count, spec.width, spec.height, spec.color_space
        )
        rendered = render_triangles(
            triangles, spec.width, spec.height, spec.background_rgb
        )
        return mean_squared_error(rendered, self._target_array)


_BY_NAME: dict[str, type[Renderer]] = {PillowRenderer.name: PillowRenderer}
DEFAULT_NAME = "auto"


def available() -> list[str]:
    """Backend names that can actually run here, in preference order."""
    return [name for name in ("rust", "pillow") if name in _BY_NAME]


def make_renderer(name: str, spec: RenderSpec, threads: int = 0) -> Renderer:
    """Build the named backend, or raise ``ValueError`` naming what is known.

    ``threads`` is only meaningful for a backend that parallelises internally;
    ``0`` means "one per core".
    """
    if name == "auto":
        return _BY_NAME[available()[0]](spec)
    if name not in _BY_NAME:
        known = ", ".join(sorted(_BY_NAME) + ["auto"])
        raise ValueError(f"unknown renderer {name!r}; known: {known}")
    return _BY_NAME[name](spec)
