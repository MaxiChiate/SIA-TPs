"""``TrianglesProblem``: the ``Problem`` plug-in for approximating an image with
``triangle_count`` translucent triangles on a solid-color canvas.

Fitness is evaluated at a small, configurable ``work_resolution`` (rendering is
the bottleneck; a small canvas keeps a generation affordable) - the genotype
itself stays resolution-independent, so ``problems.triangles.export`` can render
the same individual at full size later.
"""

from __future__ import annotations

import numpy as np
from PIL import Image

from ga import registry
from ga.core.gene import GeneSchema
from ga.core.individual import Individual
from ga.core.problem import Problem
from ga.core.rng import Rng

from .fitness import pixel_similarity
from .genotype import schema_for, triangles_from_alleles
from .renderer import render_triangles

_DEFAULT_WORK_RESOLUTION = (64, 64)
_DEFAULT_BACKGROUND_RGB = (255, 255, 255)


class TrianglesProblem(Problem):
    def __init__(self, params: dict) -> None:
        self.image_path = params["image_path"]
        self.triangle_count = params["triangle_count"]
        width, height = params.get("work_resolution", _DEFAULT_WORK_RESOLUTION)
        self.work_width = width
        self.work_height = height
        self.background_rgb = tuple(params.get("background_rgb", _DEFAULT_BACKGROUND_RGB))

        target = Image.open(self.image_path).convert("RGB").resize((width, height))
        self._target_array = np.asarray(target, dtype=np.uint8)
        self._schema = schema_for(self.triangle_count)

    def schema(self) -> GeneSchema:
        return self._schema

    def random_individual(self, rng: Rng) -> Individual:
        return Individual(self._schema.random_vector(rng), self._schema)

    def evaluate(self, individual: Individual) -> float:
        triangles = triangles_from_alleles(
            individual.alleles, self.triangle_count, self.work_width, self.work_height
        )
        rendered = render_triangles(
            triangles, self.work_width, self.work_height, self.background_rgb
        )
        return pixel_similarity(rendered, self._target_array)

    def describe(self) -> dict:
        return {
            "image_path": self.image_path,
            "triangle_count": self.triangle_count,
            "work_resolution": [self.work_width, self.work_height],
            "background_rgb": list(self.background_rgb),
        }


@registry.register("problem", "triangles")
def make_triangles_problem(params: dict) -> Problem:
    return TrianglesProblem(params)
