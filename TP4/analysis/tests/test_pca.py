"""Test of the correlation PCA by eigenvalues (D-07): eigenvalue sum and full reconstruction."""

from __future__ import annotations

import numpy as np

import creadores
from creadores import PREPARED_DIR, RAW_PATH
from pca import correlation_matrix, pca_eigh, read_prepared, reconstruct, scores

STEM = "creadores_zscore"


def test_eigenvalues_sum_to_n_and_full_reconstruction():
    if not (PREPARED_DIR / f"{STEM}.csv").exists():
        creadores.prepare(RAW_PATH, PREPARED_DIR)
    features, z, _meta = read_prepared(STEM)
    assert z.shape == (50, 26)

    result = pca_eigh(z, features)
    values = result.eigenvalues
    vectors = result.eigenvectors

    assert np.all(np.diff(values) <= 0), "eigenvalues must be sorted in descending order"
    assert abs(values.sum() - 26) < 1e-9

    corr = correlation_matrix(z)
    assert np.allclose(corr @ vectors, vectors * values, atol=1e-10)

    assert np.allclose(reconstruct(result, scores(result, z)), z, atol=1e-10)

    # sign convention: the coefficient of largest magnitude of each eigenvector is positive
    largest = vectors[np.argmax(np.abs(vectors), axis=0), np.arange(vectors.shape[1])]
    assert np.all(largest > 0)
