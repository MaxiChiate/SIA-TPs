"""Tests of the report and slide variants (D-08) of the Exercise 1 figures: PCA scree and biplot, Oja index vs PC1.

Synthetic data only: no dependence on datos/ or on analysis/results/.
"""

from __future__ import annotations

import re

import numpy as np
import pytest

import oja
import pca
import plots_style

FEATURES = ["a", "b", "c", "d"]


@pytest.fixture(autouse=True)
def report_variant():
    plots_style.use_variant("report")
    yield
    plots_style.use_variant("report")


@pytest.fixture
def synthetic(monkeypatch):
    rng = np.random.default_rng(7)
    raw = rng.normal(size=(12, 4)) @ rng.normal(size=(4, 4))
    z = (raw - raw.mean(axis=0)) / raw.std(axis=0, ddof=1)
    result = pca.pca_eigh(z, FEATURES)
    ids = [f"C{i:02d}" for i in range(12)]
    topics = [label for _, label in pca.TOPICS]
    monkeypatch.setattr(pca, "dominant_topics", lambda _ids: [topics[i % 4] for i in range(len(_ids))])
    return result, z, {"creator_id": ids, "variant": "synthetic"}


def svg_aspect(path) -> float:
    head = path.read_text(encoding="utf-8")[:2000]
    width = float(re.search(r'width="([0-9.]+)pt"', head).group(1))
    height = float(re.search(r'height="([0-9.]+)pt"', head).group(1))
    return width / height


def test_pca_scree_and_biplot_in_both_variants(tmp_path, synthetic):
    result, z, meta = synthetic
    dec = pca.decision(result, "synthetic")
    for _ in plots_style.iter_variants():
        pca.plot_scree(result, dec, "sintetico", tmp_path)
        pca.plot_biplot(result, z, meta, "sintetico", tmp_path)
    for stem in ("scree", "biplot"):
        for suffix in (".svg", ".png"):
            assert (tmp_path / f"{stem}{suffix}").stat().st_size > 0
            assert (tmp_path / "slide" / f"{stem}{suffix}").stat().st_size > 0
        slide_aspect = svg_aspect(tmp_path / "slide" / f"{stem}.svg")
        assert slide_aspect == pytest.approx(plots_style.SLIDE_FIGSIZE[0] / plots_style.SLIDE_FIGSIZE[1], abs=0.02)
    assert svg_aspect(tmp_path / "scree.svg") == pytest.approx(11 / 7.5, abs=0.02)
    assert plots_style.variant() == "report"


def test_report_scree_is_the_same_after_the_slide_loop(tmp_path, synthetic):
    result, z, meta = synthetic
    dec = pca.decision(result, "synthetic")
    first, again = tmp_path / "first", tmp_path / "again"
    first.mkdir()
    again.mkdir()
    pca.plot_scree(result, dec, "sintetico", first)
    for _ in plots_style.iter_variants():
        pca.plot_scree(result, dec, "sintetico", tmp_path)
    pca.plot_scree(result, dec, "sintetico", again)
    assert (first / "scree.svg").read_bytes() == (again / "scree.svg").read_bytes()
    assert (first / "scree.svg").read_bytes() == (tmp_path / "scree.svg").read_bytes()


def test_only_the_audited_set_draws_the_slide_variant():
    assert list(pca._figure_variants("audited")) == ["report", "slide"]
    assert list(pca._figure_variants("all31_sensitivity")) == ["report"]
    assert plots_style.variant() == "report"


def test_oja_vs_pc1_in_both_variants(tmp_path):
    rng = np.random.default_rng(3)
    pc1 = rng.normal(size=12)
    index = pc1 + rng.normal(scale=0.01, size=12)
    topics = [label for _, label in pca.TOPICS]
    labels = [topics[i % 4] for i in range(12)]
    comparison = {"abs_cos": 0.9999998, "pearson": 0.9999, "spearman": 1.0}
    for _ in plots_style.iter_variants():
        oja.plot_oja_vs_pc1(index, pc1, labels, comparison, tmp_path / "oja_vs_pc1")
    assert (tmp_path / "oja_vs_pc1.svg").stat().st_size > 0
    assert (tmp_path / "slide" / "oja_vs_pc1.svg").stat().st_size > 0
    assert svg_aspect(tmp_path / "slide" / "oja_vs_pc1.svg") == pytest.approx(
        plots_style.SLIDE_FIGSIZE[0] / plots_style.SLIDE_FIGSIZE[1], abs=0.02)
