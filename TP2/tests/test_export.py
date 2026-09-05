"""Unit tests for ``problems.triangles.export`` (the GIF assembly)."""

from __future__ import annotations

import pytest
from PIL import Image

from problems.triangles.export import save_gif


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
