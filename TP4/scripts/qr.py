"""Reads the five fixed 37x37 QR PNGs of HOP-04 and encodes them to +-1 (dark = +1, light = -1).

Library only, no side effects on import. This module only reads and encodes bitmaps: it never
runs the network. Each PNG is measured (Pitfall 22) to be grayscale 37x37 with only 0/255 pixel
values, so no threshold and no resampling is applied: a value outside {0, 255} or a shape other
than 37x37 raises QrError and nothing is written. Written files hold no timestamp and no absolute
path, so a rerun reproduces them byte for byte.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

TP_DIR = Path(__file__).resolve().parent.parent
HOPFIELD_DIR = TP_DIR / "datos" / "hopfield"
PREPARED_DIR = TP_DIR / "datos" / "prepared"
PREPARED_CSV = PREPARED_DIR / "qr_pm1.csv"

SIDE = 37
N_PIXELS = SIDE * SIDE

# Fixed order (HOP-04): this is the order written to qr_pm1.csv and is what the Plan 02 guard
# hashes and the Plan 03-05 drivers index by subset [0, 1, 2, 3, 4].
SOURCES: tuple[str, ...] = (
    "beverages_menu_qr.png",
    "dessert_menu_qr.png",
    "food_menu_qr.png",
    "specials_menu_qr.png",
    "wine_menu_qr.png",
)

# Polarity (fixed for display; Hebb's W is invariant to a global flip of a pattern, Pitfall 22):
# dark pixel (0) maps to +1, light pixel (255) maps to -1.
ENCODING = "row-major 37x37, dark (0) = +1, light (255) = -1"


class QrError(ValueError):
    """A QR PNG does not follow the measured 37x37 / {0, 255} contract."""


@dataclass(frozen=True)
class QrSet:
    names: tuple[str, ...]
    patterns: np.ndarray  # (5, 1369) int64, values +-1
    source_sha256: tuple[str, ...]  # per-PNG sha256, same order as names


def _source_label(source: Path) -> str:
    try:
        return Path(source).resolve().relative_to(TP_DIR).as_posix()
    except ValueError:
        return Path(source).name


def encode(path: Path) -> tuple[np.ndarray, str]:
    """Read one PNG, assert 37x37 and values in {0, 255}, map to a 1369-vector of +-1."""
    path = Path(path)
    if not path.is_file():
        raise QrError(f"QR file not found: {_source_label(path)}")
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    with Image.open(path) as image:
        image = image.convert("L")
        arr = np.array(image)
    if arr.shape != (SIDE, SIDE):
        raise QrError(
            f"{_source_label(path)}: expected {SIDE}x{SIDE}, found {arr.shape[1]}x{arr.shape[0]}"
        )
    values = set(np.unique(arr).tolist())
    if not values <= {0, 255}:
        bad = sorted(values - {0, 255})
        raise QrError(f"{_source_label(path)}: expected pixel values in {{0, 255}}, found {bad}")
    pattern = np.where(arr.reshape(-1) == 0, 1, -1).astype(np.int64)
    return pattern, digest


def load_qr_set(source_dir: Path = HOPFIELD_DIR) -> QrSet:
    source_dir = Path(source_dir)
    patterns = []
    digests = []
    for name in SOURCES:
        pattern, digest = encode(source_dir / name)
        patterns.append(pattern)
        digests.append(digest)
    return QrSet(names=SOURCES, patterns=np.vstack(patterns).astype(np.int64), source_sha256=tuple(digests))


def _atomic_write(path: Path, text: str) -> None:
    """Write via a temporary file in the same folder, then os.replace: readers never see half."""
    handle, temp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", newline="", encoding="utf-8") as file:
            file.write(text)
        os.replace(temp_name, path)
    except BaseException:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
        raise


def write_prepared(qr_set: QrSet, out_dir: Path, source_dir: Path) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "qr_pm1.csv"
    meta_path = out_dir / "qr_pm1.meta.json"

    header = ",".join(f"p{k}" for k in range(N_PIXELS))
    body = [",".join(str(int(v)) for v in row) for row in qr_set.patterns]
    meta = {
        "source": _source_label(source_dir),
        "sources": list(qr_set.names),
        "source_sha256": dict(zip(qr_set.names, qr_set.source_sha256)),
        "encoding": ENCODING,
        "polarity": "dark (0) = +1, light (255) = -1",
        "n_patterns": len(qr_set.names),
        "n_pixels": N_PIXELS,
    }
    _atomic_write(csv_path, "\n".join([header, *body]) + "\n")
    _atomic_write(meta_path, json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    return [csv_path, meta_path]


def prepare(source_dir: Path = HOPFIELD_DIR, out_dir: Path = PREPARED_DIR) -> tuple[QrSet, list[Path]]:
    """Convert the five fixed QR PNGs and write the CSV and its meta; a refused PNG writes nothing."""
    qr_set = load_qr_set(source_dir)
    return qr_set, write_prepared(qr_set, out_dir, source_dir)
