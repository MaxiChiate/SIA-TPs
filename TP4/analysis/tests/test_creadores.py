"""Tests of the creadores loader, the variable audit and the saved scaler (D-07).

The prepared files in datos/prepared/ are generated outputs (not versioned); the `prepared`
fixture regenerates them with the same code path as scripts/prepare_creadores.py when absent.
"""

from __future__ import annotations

import csv

import numpy as np
import pytest

import creadores
from creadores import (
    PREPARED_DIR,
    RAW_PATH,
    load_creadores,
    load_meta,
)

AUDITED = PREPARED_DIR / "creadores_zscore.csv"
AUDITED_META = PREPARED_DIR / "creadores_zscore.meta.json"
ALL31 = PREPARED_DIR / "creadores_zscore_all31.csv"
ALL31_META = PREPARED_DIR / "creadores_zscore_all31.meta.json"

EXPECTED_DROPPED = {
    "price_ars",
    "organic_posts_pct",
    "total_engagement_per_1000",
    "topic_art_pct",
    "content_showcase_pct",
}


@pytest.fixture(scope="session")
def prepared():
    if not (AUDITED.exists() and AUDITED_META.exists() and ALL31.exists() and ALL31_META.exists()):
        creadores.prepare(RAW_PATH, PREPARED_DIR)
    return PREPARED_DIR


def read_matrix(path):
    with path.open(newline="") as file:
        reader = csv.reader(file)
        header = next(reader)
        values = np.array([[float(cell) for cell in row] for row in reader])
    return header, values


def test_loader_requires_50_rows_and_33_columns(tmp_path):
    data = load_creadores()
    assert data.ids == [f"INF{i:03d}" for i in range(1, 51)]
    assert len(data.names) == 50
    assert data.values.shape == (50, 31)

    lines = RAW_PATH.read_text().splitlines()

    short = tmp_path / "short.csv"
    short.write_text("\n".join(lines[:-1]) + "\n")
    with pytest.raises(ValueError) as short_error:
        load_creadores(short)
    assert "50" in str(short_error.value) and "33" in str(short_error.value)

    narrow = tmp_path / "narrow.csv"
    narrow.write_text("\n".join(",".join(line.split(",")[:-1]) for line in lines) + "\n")
    with pytest.raises(ValueError) as narrow_error:
        load_creadores(narrow)
    assert "33" in str(narrow_error.value)


def test_audit_drops_exactly_the_five_dependencies(prepared):
    data = load_creadores()
    audit = creadores.audit_variables(data)
    assert {d.name for d in audit.dropped} == EXPECTED_DROPPED
    assert len(audit.kept) == 26
    assert audit.kept == [c for c in data.columns if c not in EXPECTED_DROPPED]

    meta = load_meta(AUDITED_META)
    assert meta["features"] == audit.kept

    header, z = read_matrix(AUDITED)
    assert header == audit.kept
    assert np.linalg.matrix_rank(z) == 26
    eigenvalues = np.linalg.eigvalsh(np.corrcoef(z, rowvar=False))
    assert eigenvalues.min() > 1e-5


def test_all31_correlation_has_five_null_eigenvalues(prepared):
    header, z = read_matrix(ALL31)
    assert len(header) == 31
    eigenvalues = np.linalg.eigvalsh(np.corrcoef(z, rowvar=False))
    assert int(np.sum(np.abs(eigenvalues) < 1e-10)) == 5
    assert int(np.sum(eigenvalues > 1e-5)) == 26

    meta = load_meta(ALL31_META)
    assert meta["variant"] == "all31_sensitivity"
    assert meta["dropped"] == []
