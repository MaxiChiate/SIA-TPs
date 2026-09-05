"""Fitness = 1 - mean squared pixel error, normalized against a blank-canvas baseline.

Higher is better (the ``Problem`` contract), and the result lives in [0, 1]: 1.0
means a pixel-perfect match, 0.0 means "no better than drawing nothing" (the MSE
of the blank background canvas against the target). Normalizing against the
theoretical worst case (255**2 per channel) instead of this baseline compresses
almost every real result into a narrow band near 1.0 - a blank canvas already
scores ~0.9 on that scale - which makes the fitness both misleadingly high and
too flat for selection to discriminate between good and bad individuals.
"""

from __future__ import annotations

import numpy as np
from PIL import Image


def mean_squared_error(rendered: Image.Image, target: np.ndarray) -> float:
    rendered_array = np.asarray(rendered, dtype=np.float64)
    diff = rendered_array - target.astype(np.float64)
    return float(np.mean(diff * diff))


def pixel_similarity(rendered: Image.Image, target: np.ndarray, baseline_mse: float) -> float:
    mse = mean_squared_error(rendered, target)
    return max(0.0, 1.0 - (mse / baseline_mse))
