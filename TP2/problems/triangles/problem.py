"""``TrianglesProblem``: the ``Problem`` plug-in for approximating an image with
``triangle_count`` translucent triangles on a solid-color canvas.

Fitness is evaluated at a small, configurable ``work_resolution`` (rendering is
the bottleneck; a small canvas keeps a generation affordable) - the genotype
itself stays resolution-independent, so ``problems.triangles.export`` can render
the same individual at full size later.

The optional ``color_space`` param (``rgb`` by default, see
``problems.triangles.colorspace``) picks how each triangle's three color alleles
are read. It changes no interface: the genotype stays a flat [0,1] vector of the
same length, so every operator is unaffected - what changes is which colors sit
close together under mutation and crossover.

Scoring itself is delegated to a ``Renderer`` (``problems.triangles.renderers``),
chosen by the optional ``renderer`` param. The problem holds the genotype rules;
the renderer holds the pixels.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from ga import registry
from ga.core.gene import GeneSchema
from ga.core.individual import Individual
from ga.core.problem import Problem
from ga.core.rng import Rng

from . import colorspace
from .export import native_resolution
from .genotype import GENES_PER_TRIANGLE, schema_for
from .renderers import DEFAULT_NAME as DEFAULT_RENDERER
from .renderers import RenderSpec, make_renderer

_DEFAULT_WORK_RESOLUTION = (64, 64)
_DEFAULT_BACKGROUND_RGB = (255, 255, 255)


def _clamp01(value: float) -> float:
    return min(1.0, max(0.0, value))


class TrianglesProblem(Problem):
    def __init__(self, params: dict) -> None:
        self.image_path = params["image_path"]
        self.triangle_count = params["triangle_count"]
        width, height = params.get("work_resolution", _DEFAULT_WORK_RESOLUTION)
        self.work_width = width
        self.work_height = height
        self.background_rgb = tuple(params.get("background_rgb", _DEFAULT_BACKGROUND_RGB))
        self.color_space = colorspace.get(
            params.get("color_space", colorspace.DEFAULT.name)
        )

        self._schema = schema_for(self.triangle_count, self.color_space)
        self._renderer = make_renderer(
            params.get("renderer", DEFAULT_RENDERER),
            RenderSpec.build(
                self.image_path,
                width,
                height,
                self.background_rgb,
                self.color_space,
                self.triangle_count,
            ),
            threads=params.get("threads", 0),
        )

    def schema(self) -> GeneSchema:
        return self._schema

    def random_individual(self, rng: Rng) -> Individual:
        return Individual(self._schema.random_vector(rng), self._schema)

    def evaluate(self, individual: Individual) -> float:
        return self._renderer.score(individual.alleles)

    def evaluate_batch(self, individuals: Sequence[Individual]) -> list[float]:
        return self._renderer.score_batch([i.alleles for i in individuals])

    def owns_parallelism(self) -> bool:
        return self._renderer.owns_parallelism()

    def describe(self) -> dict:
        return {
            "image_path": self.image_path,
            "triangle_count": self.triangle_count,
            "work_resolution": [self.work_width, self.work_height],
            "background_rgb": list(self.background_rgb),
            "color_space": self.color_space.name,
            **self._renderer.describe(),
        }

    def individual_from_export(self, path: str | Path) -> Individual:
        """Decode a ``triangles.json`` export back into an individual on this
        problem's schema.

        The export stores pixel-space vertices with no resolution of its own,
        so this normalizes them back to ``[0,1]`` against ``self.image_path``'s
        *native* resolution - the width/height ``run.py`` exports at by default.
        An export produced with ``--export-width``/``--export-height`` overrides
        will decode incorrectly; this is a known limitation.

        Colors are stored as plain RGB, so they are re-encoded into whatever
        color space *this* run uses: an export can be imported under a different
        ``color_space`` than it was produced with and still render identically.
        """
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except OSError as err:
            raise ValueError(f"cannot read {path}: {err}") from err
        if len(data) != self.triangle_count:
            raise ValueError(
                f"{path} has {len(data)} triangles, expected {self.triangle_count}"
            )
        width, height = native_resolution(self.image_path)

        alleles: list[float] = []
        for triangle in data:
            for x, y in triangle["vertices"]:
                alleles.append(_clamp01(x / width))
                alleles.append(_clamp01(y / height))
            red, green, blue, alpha = triangle["color"]
            alleles.extend(
                _clamp01(channel)
                for channel in self.color_space.from_rgb(red, green, blue)
            )
            alleles.append(_clamp01(alpha / 255))
        assert len(alleles) == self.triangle_count * GENES_PER_TRIANGLE
        return Individual(alleles, self._schema)


@registry.register("problem", "triangles")
def make_triangles_problem(params: dict) -> Problem:
    return TrianglesProblem(params)
