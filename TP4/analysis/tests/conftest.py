"""Pytest setup: make TP4/scripts and TP4/analysis importable (creadores, later pca)."""

from __future__ import annotations

import sys
from pathlib import Path

TP_DIR = Path(__file__).resolve().parent.parent.parent

for sub in ("analysis", "scripts"):
    path = str(TP_DIR / sub)
    if path not in sys.path:
        sys.path.insert(0, path)
