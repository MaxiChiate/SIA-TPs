"""Unit tests for ``problems.triangles.export`` (figure JSON + GIF assembly)."""

from __future__ import annotations

import json

import pytest
from PIL import Image

from ga.core.individual import Individual
from problems.triangles import colorspace
from problems.triangles.export import figures_as_json, save_figures_json, save_gif
from problems.triangles.genotype import schema_for

WIDTH, HEIGHT = 40, 30


def _write_frames(directory, colors) -> list:
    paths = []
    for index, color in enumerate(colors):
        path = directory / f"gen_{index:05d}.png"
        Image.new("RGB", (8, 6), color).save(path)
        paths.append(path)
    return paths


def _durations(path) -> list[int]:
    with Image.open(path) as gif:
        durations = []
        for index in range(gif.n_frames):
            gif.seek(index)
            durations.append(gif.info["duration"])
        return durations


def test_save_gif_holds_only_the_last_frame(tmp_path):
    frames = _write_frames(tmp_path, [(255, 0, 0), (0, 255, 0), (0, 0, 255)])
    out = tmp_path / "progress.gif"
    save_gif(frames, out, frame_ms=100, hold_ms=2500)
    assert _durations(out) == [100, 100, 2500]


def test_save_gif_keeps_frame_order_and_size(tmp_path):
    frames = _write_frames(tmp_path, [(255, 0, 0), (0, 255, 0)])
    out = tmp_path / "progress.gif"
    save_gif(frames, out, frame_ms=50, hold_ms=50)
    with Image.open(out) as gif:
        assert gif.size == (8, 6)
        assert gif.n_frames == 2
        assert gif.convert("RGB").getpixel((0, 0)) == (255, 0, 0)


def test_save_gif_rejects_an_empty_frame_list(tmp_path):
    with pytest.raises(ValueError):
        save_gif([], tmp_path / "progress.gif")


# -- figures_as_json / save_figures_json ----------------------------------------


def _individual(shape_type: str, shape_count: int) -> Individual:
    schema = schema_for(shape_type, shape_count, colorspace.RGB)
    alleles = [((0.29 * (i + 1)) % 1.0) for i in range(len(schema))]
    return Individual(alleles, schema)


def test_figures_as_json_tags_each_entry_with_its_type():
    individual = _individual("triangle", shape_count=3)
    data = figures_as_json(individual, "triangle", 3, WIDTH, HEIGHT, colorspace.RGB)
    assert len(data) == 3
    assert all(entry["type"] == "triangle" for entry in data)
    assert all("vertices" in entry and "color" in entry for entry in data)


def test_figures_as_json_reports_ovals():
    individual = _individual("oval", shape_count=2)
    data = figures_as_json(individual, "oval", 2, WIDTH, HEIGHT, colorspace.RGB)
    assert len(data) == 2
    assert all(entry["type"] == "oval" for entry in data)
    assert all("center" in entry and "radii" in entry and "angle" in entry for entry in data)


def test_save_figures_json_writes_readable_json(tmp_path):
    individual = _individual("triangle", shape_count=2)
    path = tmp_path / "figures.json"
    save_figures_json(individual, "triangle", 2, WIDTH, HEIGHT, path, colorspace.RGB)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data) == 2
    assert data[0]["type"] == "triangle"
