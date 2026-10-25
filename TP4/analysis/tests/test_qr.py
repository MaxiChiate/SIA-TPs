"""Tests of the 37x37 QR PNG-to-pm-one converter (HOP-04 preparation, plan 05-06).

Mirrors analysis/tests/test_letters.py. The fixtures are synthetic 37x37 grayscale PNGs written to
tmp_path: no test here needs the real datos/hopfield/*.png files. The real-file checks at the end are
skipped when those files are absent. No network code runs on any of these inputs.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

import qr

SIDE = qr.SIDE
N = qr.N_PIXELS
REAL_DIR = qr.HOPFIELD_DIR


def blank(value: int = 255) -> np.ndarray:
    return np.full((SIDE, SIDE), value, dtype=np.uint8)


def write_png(path: Path, arr: np.ndarray, mode: str = "L") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr).convert(mode).save(path, format="PNG")
    return path


def synthetic_arrays() -> list[np.ndarray]:
    """Five distinct 37x37 {0,255} images: checkerboard-like, one-dot, and bars."""
    rng = np.random.default_rng(37)
    arrays = []
    for k in range(5):
        bits = rng.integers(0, 2, size=(SIDE, SIDE))
        arrays.append(np.where(bits == 1, 0, 255).astype(np.uint8))
    return arrays


def write_set(source_dir: Path, arrays: list[np.ndarray] | None = None) -> dict[str, bytes]:
    arrays = synthetic_arrays() if arrays is None else arrays
    raw = {}
    for name, arr in zip(qr.SOURCES, arrays):
        path = write_png(source_dir / name, arr)
        raw[name] = path.read_bytes()
    return raw


def expected_pm1(arr: np.ndarray) -> np.ndarray:
    return np.where(arr.reshape(-1) == 0, 1, -1).astype(np.int64)


# ---------------------------------------------------------------------------------------------
# Shape
# ---------------------------------------------------------------------------------------------


def test_encode_accepts_37x37_and_returns_1369_vector(tmp_path):
    arr = synthetic_arrays()[0]
    pattern, digest = qr.encode(write_png(tmp_path / "ok.png", arr))
    assert pattern.shape == (N,)
    assert pattern.dtype == np.int64
    assert np.array_equal(pattern, expected_pm1(arr))
    assert digest == hashlib.sha256((tmp_path / "ok.png").read_bytes()).hexdigest()


@pytest.mark.parametrize("shape", [(36, 37), (37, 36), (38, 38), (10, 10)])
def test_encode_refuses_wrong_shape(tmp_path, shape):
    arr = np.full(shape, 255, dtype=np.uint8)
    path = write_png(tmp_path / "bad.png", arr)
    with pytest.raises(qr.QrError, match="expected 37x37"):
        qr.encode(path)


# ---------------------------------------------------------------------------------------------
# Pixel purity: no thresholding, no resampling
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("bad_value", [1, 127, 128, 254])
def test_encode_refuses_gray_levels_instead_of_thresholding(tmp_path, bad_value):
    arr = blank(255)
    arr[10, 20] = bad_value
    path = write_png(tmp_path / "gray.png", arr)
    with pytest.raises(qr.QrError, match=str(bad_value)):
        qr.encode(path)


def test_encode_refuses_when_only_one_pixel_is_off_pure(tmp_path):
    arr = np.where(np.random.default_rng(1).integers(0, 2, (SIDE, SIDE)) == 1, 0, 255).astype(np.uint8)
    arr[36, 36] = 200  # a single non-{0,255} pixel in the last corner
    with pytest.raises(qr.QrError, match="200"):
        qr.encode(write_png(tmp_path / "one_off.png", arr))


def test_encode_does_not_resample_a_non_37_image_into_shape(tmp_path):
    # A 74x74 image of pure {0,255} must be refused, not downscaled to 37x37.
    arr = np.full((74, 74), 0, dtype=np.uint8)
    with pytest.raises(qr.QrError, match="expected 37x37"):
        qr.encode(write_png(tmp_path / "big.png", arr))


def test_encode_accepts_one_bit_png_as_pure_bitmap(tmp_path):
    # A mode-"1" PNG converts to L as exactly {0,255}, so it must be accepted without thresholding.
    arr = synthetic_arrays()[1]
    path = write_png(tmp_path / "bit.png", arr, mode="1")
    pattern, _ = qr.encode(path)
    assert np.array_equal(pattern, expected_pm1(arr))


# ---------------------------------------------------------------------------------------------
# Polarity and row-major order
# ---------------------------------------------------------------------------------------------


def test_dark_maps_to_plus_one_and_light_to_minus_one(tmp_path):
    arr = blank(255)
    arr[0, 0] = 0  # one dark pixel at top-left
    pattern, _ = qr.encode(write_png(tmp_path / "pol.png", arr))
    assert pattern[0] == 1
    assert np.count_nonzero(pattern == 1) == 1
    assert np.count_nonzero(pattern == -1) == N - 1


def test_all_dark_is_all_plus_one_and_all_light_is_all_minus_one(tmp_path):
    dark, _ = qr.encode(write_png(tmp_path / "d.png", blank(0)))
    light, _ = qr.encode(write_png(tmp_path / "l.png", blank(255)))
    assert np.all(dark == 1)
    assert np.all(light == -1)


def test_order_is_row_major_not_column_major(tmp_path):
    # Dark pixel at (row 0, col 1) must land at flat index 1; column-major would give index 37.
    arr = blank(255)
    arr[0, 1] = 0
    pattern, _ = qr.encode(write_png(tmp_path / "rm.png", arr))
    assert pattern[1] == 1
    assert pattern[SIDE] == -1
    # Dark pixel at (row 2, col 5) must land at flat index 2*37+5 = 79.
    arr = blank(255)
    arr[2, 5] = 0
    pattern, _ = qr.encode(write_png(tmp_path / "rm2.png", arr))
    assert pattern[2 * SIDE + 5] == 1
    assert np.count_nonzero(pattern == 1) == 1


def test_encoding_is_exact_per_pixel(tmp_path):
    arr = synthetic_arrays()[2]
    pattern, _ = qr.encode(write_png(tmp_path / "px.png", arr))
    for r in range(SIDE):
        for c in range(SIDE):
            want = 1 if arr[r, c] == 0 else -1
            assert pattern[r * SIDE + c] == want, (r, c)


# ---------------------------------------------------------------------------------------------
# Set loading and the fixed source order
# ---------------------------------------------------------------------------------------------


def test_load_qr_set_uses_fixed_order_and_shape(tmp_path):
    arrays = synthetic_arrays()
    write_set(tmp_path, arrays)
    qr_set = qr.load_qr_set(tmp_path)
    assert qr_set.names == qr.SOURCES
    assert qr_set.patterns.shape == (5, N)
    assert qr_set.patterns.dtype == np.int64
    assert set(np.unique(qr_set.patterns)) <= {-1, 1}
    for k, arr in enumerate(arrays):
        assert np.array_equal(qr_set.patterns[k], expected_pm1(arr))


def test_source_order_is_the_five_real_names():
    assert qr.SOURCES == (
        "beverages_menu_qr.png",
        "dessert_menu_qr.png",
        "food_menu_qr.png",
        "specials_menu_qr.png",
        "wine_menu_qr.png",
    )


def test_missing_qr_file_is_reported(tmp_path):
    with pytest.raises(qr.QrError, match="not found"):
        qr.encode(tmp_path / "absent.png")


# ---------------------------------------------------------------------------------------------
# Written CSV and meta
# ---------------------------------------------------------------------------------------------


def test_prepare_writes_csv_with_header_and_five_rows(tmp_path):
    arrays = synthetic_arrays()
    src = tmp_path / "src"
    write_set(src, arrays)
    _, paths = qr.prepare(src, tmp_path / "out")
    csv_path, meta_path = paths
    lines = csv_path.read_text().split("\n")
    assert lines[-1] == ""
    lines = lines[:-1]
    assert lines[0] == ",".join(f"p{k}" for k in range(N))
    assert len(lines) == 6
    for k, arr in enumerate(arrays):
        fields = [int(v) for v in lines[k + 1].split(",")]
        assert len(fields) == N
        assert set(fields) <= {-1, 1}
        assert fields == list(expected_pm1(arr))


def test_prepare_meta_provenance_fields(tmp_path):
    src = tmp_path / "src"
    raw = write_set(src)
    _, paths = qr.prepare(src, tmp_path / "out")
    meta = json.loads(paths[1].read_text())
    assert meta["sources"] == list(qr.SOURCES)
    assert list(meta["source_sha256"].keys()) == list(qr.SOURCES)
    for name in qr.SOURCES:
        assert meta["source_sha256"][name] == hashlib.sha256(raw[name]).hexdigest()
    assert meta["n_patterns"] == 5
    assert meta["n_pixels"] == N
    assert meta["polarity"] == "dark (0) = +1, light (255) = -1"
    assert meta["encoding"] == qr.ENCODING


def test_prepare_meta_has_no_absolute_path_or_timestamp(tmp_path):
    src = tmp_path / "src"
    write_set(src)
    _, paths = qr.prepare(src, tmp_path / "out")
    text = paths[1].read_text()
    assert str(tmp_path) not in text
    assert str(qr.TP_DIR) not in text
    assert "timestamp" not in text.lower()
    assert "source" in json.loads(text)


def test_prepare_is_deterministic(tmp_path):
    src = tmp_path / "src"
    write_set(src)
    first = qr.prepare(src, tmp_path / "one")[1]
    second = qr.prepare(src, tmp_path / "two")[1]
    for a, b in zip(first, second):
        assert a.read_bytes() == b.read_bytes()


def test_prepare_refused_set_writes_nothing(tmp_path):
    arrays = synthetic_arrays()
    arrays[3] = arrays[3].copy()
    arrays[3][5, 5] = 128
    src = tmp_path / "src"
    write_set(src, arrays)
    out = tmp_path / "out"
    with pytest.raises(qr.QrError, match="128"):
        qr.prepare(src, out)
    assert not (out / "qr_pm1.csv").exists()
    assert not (out / "qr_pm1.meta.json").exists()


def test_prepare_refused_shape_writes_nothing(tmp_path):
    src = tmp_path / "src"
    write_set(src)
    write_png(src / qr.SOURCES[4], np.full((36, 37), 255, dtype=np.uint8))
    out = tmp_path / "out"
    with pytest.raises(qr.QrError, match="expected 37x37"):
        qr.prepare(src, out)
    assert not out.exists() or not any(out.iterdir())


# ---------------------------------------------------------------------------------------------
# Real QR set (skipped when the PNGs are absent)
# ---------------------------------------------------------------------------------------------


def _real_present() -> bool:
    return all((REAL_DIR / name).is_file() for name in qr.SOURCES)


@pytest.mark.skipif(not _real_present(), reason="real QR PNGs not present under datos/hopfield")
def test_real_qr_set_is_pure_37x37_pm1():
    qr_set = qr.load_qr_set()
    assert qr_set.patterns.shape == (5, N)
    assert set(np.unique(qr_set.patterns)) <= {-1, 1}
