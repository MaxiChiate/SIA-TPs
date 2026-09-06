"""Scoring: allele vector -> fitness, entirely inside the ``triangles_native``
extension.

Rendering and comparing pixels is ~90% of a run's wall clock, and it now runs
only in the native ``rust/`` crate: there is no separate Python
implementation of the hot path to fall back to. Building the extension
(``cd rust && maturin develop --release`` - see the README) is therefore a
prerequisite for running the triangles problem at all, not an optional
speed-up. ``colorspace.py`` keeps a pure-Python colour decoder, but it only
serves cold paths - ``export.py``'s JSON enumeration and
``TrianglesProblem.individual_from_export``'s reverse decode - that run a
handful of times per generation, not per individual.

Importing this module never requires the extension (so ``import
problems.triangles`` - and anything that only needs ``colorspace.py``, like
its own tests - still works without one). Only *constructing* a renderer
does, which happens when a ``TrianglesProblem`` is actually built for a run.

``RustRenderer`` owns a ``RenderSpec``: the target pixels and every decode
rule that never changes during a run. That is what lets it upload the target
once, into a native ``Scorer``, rather than re-sending it on every call.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from PIL import Image

from .colorspace import ColorSpace

_MIN_BASELINE_MSE = 1e-9

# Bumped in lockstep with ``SCHEMA_VERSION`` in rust/src/lib.rs whenever the
# native kernel's numerics change, so a stale .so left over from an earlier
# build fails loudly instead of quietly scoring genomes a different way.
NATIVE_SCHEMA_VERSION = 1

try:
    import triangles_native as _native
except ImportError:  # not built, or built against a different interpreter
    _native = None


@dataclass(frozen=True, slots=True)
class RenderSpec:
    """Everything about a run that the native scorer needs and that never
    changes.

    ``target_rgb`` is raw row-major RGB bytes rather than a numpy array so the
    spec stays picklable and hands straight to the native ``Scorer``.
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
    render call, and every run normalises against an identical value rather
    than against its own idea of a blank canvas.
    """
    target = np.frombuffer(target_rgb, dtype=np.uint8).reshape(-1, 3).astype(np.float64)
    background = np.asarray(background_rgb, dtype=np.float64)
    difference = target - background
    return max(float(np.mean(difference * difference)), _MIN_BASELINE_MSE)


class RustRenderer:
    """Scores allele vectors against one run's target via ``triangles_native``.

    One ``Scorer`` per run: the target and every decode rule are uploaded once,
    at construction, so a generation costs one call across the FFI boundary
    rather than one per pixel buffer.
    """

    def __init__(self, spec: RenderSpec, threads: int = 0) -> None:
        if _native is None:
            raise ImportError(
                "the triangles problem needs the triangles_native extension; "
                "build it with: cd rust && maturin develop --release"
            )
        if _native.schema_version() != NATIVE_SCHEMA_VERSION:
            raise ValueError(
                f"triangles_native was built from a different revision "
                f"(schema {_native.schema_version()}, expected "
                f"{NATIVE_SCHEMA_VERSION}); rebuild it with: "
                f"cd rust && maturin develop --release"
            )
        self.spec = spec
        self._scorer = _native.Scorer(
            spec.target_rgb,
            spec.width,
            spec.height,
            tuple(spec.background_rgb),
            spec.triangle_count,
            spec.color_space.name,
            spec.baseline_mse,
            threads,
        )

    def owns_parallelism(self) -> bool:
        """Always ``True``: ``score_batch`` already uses every thread it was
        given, so the engine must not also fan the batch out across processes
        (see ``ga.core.engine.Evaluator``)."""
        return True

    def score(self, alleles: Sequence[float]) -> float:
        return self._scorer.score(list(alleles))

    def score_batch(self, genomes: Sequence[Sequence[float]]) -> list[float]:
        return self._scorer.score_batch([list(alleles) for alleles in genomes])

    def mse(self, alleles: Sequence[float]) -> float:
        """Raw mean squared error, before the fitness normalisation.

        The thread-invariance tests compare backends on this rather than on
        fitness: fitness clamps at 0 for anything worse than a blank canvas,
        and that floor would swallow the difference being measured.
        """
        return self._scorer.mse(list(alleles))

    def render_rgb(self, alleles: Sequence[float], width: int, height: int) -> Image.Image:
        """Draw one genotype at an arbitrary size, with the same rasterizer
        that scored it - otherwise the exported picture is not the picture
        the fitness refers to."""
        raw = self._scorer.render_rgb(list(alleles), width, height)
        return Image.frombytes("RGB", (width, height), raw)

    def describe(self) -> dict:
        return {
            "renderer": "rust",
            "renderer_build": _native.build_info(),
            "renderer_threads": self._scorer.threads,
        }
