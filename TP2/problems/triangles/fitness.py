"""Fitness = 1 - normalized mean squared pixel error against the target image.

Higher is better (the ``Problem`` contract), and the result lives in [0, 1] like
every other value in this codebase's allele/diversity conventions: 1.0 means a
pixel-perfect match, 0.0 means every channel of every pixel is maximally wrong.
"""

from __future__ import annotations

import numpy as np
from PIL import Image

_MAX_SQUARED_CHANNEL_DIFF = 255.0**2


def pixel_similarity(rendered: Image.Image, target: np.ndarray) -> float:
    rendered_array = np.asarray(rendered, dtype=np.float64)
    diff = rendered_array - target.astype(np.float64)
    mse = float(np.mean(diff * diff))
    return 1.0 - (mse / _MAX_SQUARED_CHANNEL_DIFF)
