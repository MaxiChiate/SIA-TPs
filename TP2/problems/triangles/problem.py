"""``TrianglesProblem``: the ``Problem`` plug-in for approximating an image with
``shape_count`` translucent shapes on a solid-color canvas.

``problem.params.shape_type`` (``triangle`` by default, see
``problems.triangles.genotype``) picks what those shapes are: all triangles,
all ovals, or a mix where each shape's kind is itself a gene that mutation can
flip generation over generation. It changes the genotype's block size and
decode rules but nothing about how the engine drives the search - selection,
crossover, mutation and survival stay exactly as generic as they always were.

Fitness is evaluated at a small, configurable ``work_resolution`` (rendering is
the bottleneck; a small canvas keeps a generation affordable) - the genotype
itself stays resolution-independent, so ``problems.triangles.export`` can render
the same individual at full size later.

The optional ``color_space`` param (``rgb`` by default, see
``problems.triangles.colorspace``) picks how each shape's three color alleles
are read. It changes no interface: the genotype stays a flat [0,1] vector of the
same length, so every operator is unaffected - what changes is which colors sit
close together under mutation and crossover.

Scoring itself is delegated to ``RustRenderer`` (``problems.triangles.renderers``):
the problem holds the genotype rules, the renderer holds the pixels and the
native kernel that scores them. There is no Python-side scoring path to choose
instead - building the ``triangles_native`` extension is a prerequisite, not an
option (see the README).

``work_resolution`` also accepts the string ``"native"``, which resolves to the
source image's own resolution: fitness then compares every pixel of the target,
with no downscaling in between. It is the most faithful the objective function
can get, and the most expensive - cost grows with the pixel count, and at native
size rendering is the bottleneck again.

The optional ``initial_alpha`` param caps the alpha of the *first* generation
only. Fitness floors at 0 for anything worse than the blank canvas, and a
population of opaque random shapes starts entirely under that floor: every
individual ties at 0, selection has nothing to rank, and the run stalls until a
mutation happens to cross back over. Starting nearly transparent puts the
initial population on the useful side of the floor. It biases only the seed
draw - no operator, and no later generation, knows about it. Alpha is always
the last gene of a shape's block regardless of ``shape_type``, so this bias
applies the same way in every mode without knowing what is in the rest of the
block.
"""

from __future__ import annotations

import json
import os
import warnings
from collections.abc import Sequence
from pathlib import Path

from ga import registry
from ga.core.gene import GeneSchema
from ga.core.individual import Individual
from ga.core.problem import Problem
from ga.core.rng import Rng

from . import colorspace
from .export import native_resolution
from .genotype import SHAPE_TYPES, alleles_from_figures, figure_from_export, schema_for
from .renderers import RenderSpec, RustRenderer

_DEFAULT_WORK_RESOLUTION = (64, 64)
_DEFAULT_BACKGROUND_RGB = (255, 255, 255)
_DEFAULT_INITIAL_ALPHA = 1.0  # the whole [0,1] range, i.e. no bias at all
_DEFAULT_SHAPE_TYPE = "triangle"


_NATIVE_WORK_RESOLUTION = "native"


def _shape_type(value) -> str:
    if value not in SHAPE_TYPES:
        raise ValueError(f"shape_type must be one of {SHAPE_TYPES}, got {value!r}")
    return value


def _threads(value) -> int:
    """``problem.params.threads``: how many threads the native scorer gets.

    ``0`` means one per logical CPU, which is the default and the right answer
    almost always. It is validated here rather than left to PyO3 so a bad value
    names the config key it came from, and because oversubscribing is legal but
    almost never intended: more threads than CPUs adds context switches to a
    kernel that is already memory-bound, so it is warned about instead of
    silently obeyed.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"threads must be an int, got {value!r}")
    if value < 0:
        raise ValueError(f"threads must be >= 0 (0 = one per core), got {value}")
    available = os.cpu_count() or 1
    if value > available:
        warnings.warn(
            f"threads={value} exceeds the {available} logical CPUs available; "
            f"the scorer will oversubscribe",
            stacklevel=3,
        )
    return value


def _work_resolution(value, image_path: str) -> tuple[int, int]:
    """``[width, height]``, or ``"native"`` for the source image's own size."""
    if value == _NATIVE_WORK_RESOLUTION:
        return native_resolution(image_path)
    if isinstance(value, str):
        raise ValueError(
            f"work_resolution must be [width, height] or "
            f"{_NATIVE_WORK_RESOLUTION!r}, got {value!r}"
        )
    width, height = value
    return int(width), int(height)


class TrianglesProblem(Problem):
    def __init__(self, params: dict) -> None:
        self.image_path = params["image_path"]
        self.shape_count = params["shape_count"]
        self.shape_type = _shape_type(params.get("shape_type", _DEFAULT_SHAPE_TYPE))
        width, height = _work_resolution(
            params.get("work_resolution", _DEFAULT_WORK_RESOLUTION), self.image_path
        )
        self.work_width = width
        self.work_height = height
        self.background_rgb = tuple(params.get("background_rgb", _DEFAULT_BACKGROUND_RGB))
        self.color_space = colorspace.get(
            params.get("color_space", colorspace.DEFAULT.name)
        )
        self.initial_alpha = float(params.get("initial_alpha", _DEFAULT_INITIAL_ALPHA))
        if not 0.0 < self.initial_alpha <= 1.0:
            raise ValueError(
                f"initial_alpha must be in (0, 1], got {self.initial_alpha}"
            )

        self._schema = schema_for(self.shape_type, self.shape_count, self.color_space)
        self._renderer = RustRenderer(
            RenderSpec.build(
                self.image_path,
                width,
                height,
                self.background_rgb,
                self.color_space,
                self.shape_count,
                self.shape_type,
            ),
            threads=_threads(params.get("threads", 0)),
        )

    @property
    def renderer(self):
        """The backend that scores this run - and therefore the one that must
        also draw its exported images."""
        return self._renderer

    def schema(self) -> GeneSchema:
        return self._schema

    def random_individual(self, rng: Rng) -> Individual:
        alleles = self._schema.random_vector(rng)
        if self.initial_alpha < 1.0:
            block_size = self._schema.block_size
            for locus in range(block_size - 1, len(alleles), block_size):
                alleles[locus] *= self.initial_alpha
        return Individual(alleles, self._schema)

    def evaluate(self, individual: Individual) -> float:
        return self._renderer.score(individual.alleles)

    def evaluate_batch(self, individuals: Sequence[Individual]) -> list[float]:
        return self._renderer.score_batch([i.alleles for i in individuals])

    def owns_parallelism(self) -> bool:
        return self._renderer.owns_parallelism()

    def describe(self) -> dict:
        return {
            "image_path": self.image_path,
            "shape_count": self.shape_count,
            "shape_type": self.shape_type,
            "work_resolution": [self.work_width, self.work_height],
            "background_rgb": list(self.background_rgb),
            "color_space": self.color_space.name,
            "initial_alpha": self.initial_alpha,
            **self._renderer.describe(),
        }

    def individual_from_export(self, path: str | Path) -> Individual:
        """Decode a previous run's export (e.g. this problem's
        ``figures.json``) back into an individual on this problem's schema.

        The export stores pixel-space geometry with no resolution of its own,
        so this normalizes it back to ``[0,1]`` against ``self.image_path``'s
        *native* resolution - the width/height ``run.py`` exports at by
        default. An export produced with ``--export-width``/
        ``--export-height`` overrides will decode incorrectly; this is a known
        limitation.

        Every figure must be importable under this problem's ``shape_type``:
        ``triangle``/``oval`` modes reject an export containing the other
        kind (there is no block layout to put it in); ``both`` accepts either.
        Colors are stored as plain RGB, so they are re-encoded into whatever
        color space *this* run uses: an export can be imported under a
        different ``color_space`` than it was produced with and still render
        identically.
        """
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except OSError as err:
            raise ValueError(f"cannot read {path}: {err}") from err
        if len(data) != self.shape_count:
            raise ValueError(
                f"{path} has {len(data)} figures, expected {self.shape_count}"
            )
        figures = [figure_from_export(entry) for entry in data]
        width, height = native_resolution(self.image_path)
        alleles = alleles_from_figures(
            figures, self.shape_type, width, height, self.color_space
        )
        assert len(alleles) == len(self._schema)
        return Individual(alleles, self._schema)


@registry.register("problem", "triangles")
def make_triangles_problem(params: dict) -> Problem:
    return TrianglesProblem(params)
