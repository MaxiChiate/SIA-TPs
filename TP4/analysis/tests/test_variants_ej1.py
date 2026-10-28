"""Tests of the report and slide variants (D-08) of the Exercise 1 figures: PCA eigenvalue plot and biplot, Oja index vs PC1.

Synthetic data only: no dependence on datos/ or on analysis/results/.
"""

from __future__ import annotations

import re

import numpy as np
import pytest

import campaigns
import campaigns_select
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


def test_pca_eigenvalues_and_biplot_in_both_variants(tmp_path, synthetic):
    result, z, meta = synthetic
    dec = pca.decision(result, "synthetic")
    for _ in plots_style.iter_variants():
        pca.plot_eigenvalues(result, dec, "sintetico", tmp_path)
        pca.plot_biplot(result, z, meta, "sintetico", tmp_path)
    for stem in ("eigenvalues_variance", "biplot"):
        for suffix in (".svg", ".png"):
            assert (tmp_path / f"{stem}{suffix}").stat().st_size > 0
            assert (tmp_path / "slide" / f"{stem}{suffix}").stat().st_size > 0
        slide_aspect = svg_aspect(tmp_path / "slide" / f"{stem}.svg")
        assert slide_aspect == pytest.approx(plots_style.SLIDE_FIGSIZE[0] / plots_style.SLIDE_FIGSIZE[1], abs=0.02)
    assert svg_aspect(tmp_path / "eigenvalues_variance.svg") == pytest.approx(11 / 7.5, abs=0.02)
    assert plots_style.variant() == "report"


def test_report_eigenvalues_is_the_same_after_the_slide_loop(tmp_path, synthetic):
    result, z, meta = synthetic
    dec = pca.decision(result, "synthetic")
    first, again = tmp_path / "first", tmp_path / "again"
    first.mkdir()
    again.mkdir()
    pca.plot_eigenvalues(result, dec, "sintetico", first)
    for _ in plots_style.iter_variants():
        pca.plot_eigenvalues(result, dec, "sintetico", tmp_path)
    pca.plot_eigenvalues(result, dec, "sintetico", again)
    assert (first / "eigenvalues_variance.svg").read_bytes() == (again / "eigenvalues_variance.svg").read_bytes()
    assert (first / "eigenvalues_variance.svg").read_bytes() == (tmp_path / "eigenvalues_variance.svg").read_bytes()


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


def campaign_entries(n, seed=9):
    """Synthetic entries of the campaign lists: each CAMPAIGNS objective gets an own list of 4 creators, and each
    campaign a followers_global list of 5; the figures read only campaign, list, objective and members."""
    rng = np.random.default_rng(seed)
    entries = []
    for campaign, objectives in campaigns_select.CAMPAIGNS:
        entries.append({"campaign": campaign, "objective": "global", "list": "followers_global",
                        "members": [int(i) for i in rng.choice(n, size=5, replace=False)]})
        for objective in objectives:
            entries.append({"campaign": campaign, "objective": objective, "list": "propia",
                            "members": [int(i) for i in rng.choice(n, size=4, replace=False)]})
    return entries


def test_campaign_shortlists_biplot_in_both_variants(tmp_path):
    n = 50
    rng = np.random.default_rng(4)
    pc = rng.normal(size=(n, 2))
    entries = campaign_entries(n)
    for _ in plots_style.iter_variants():
        campaigns.plot_shortlists_biplot(entries, pc, [0.42, 0.21], tmp_path / "shortlists_biplot")
    for suffix in (".svg", ".png"):
        assert (tmp_path / f"shortlists_biplot{suffix}").stat().st_size > 0
        assert (tmp_path / "slide" / f"shortlists_biplot{suffix}").stat().st_size > 0
    slide = tmp_path / "slide" / "shortlists_biplot.svg"
    assert svg_aspect(slide) == pytest.approx(plots_style.SLIDE_FIGSIZE[0] / plots_style.SLIDE_FIGSIZE[1], abs=0.02)
    assert (tmp_path / "shortlists_biplot.svg").read_bytes() != slide.read_bytes()
    assert plots_style.variant() == "report"


def test_campaign_shortlists_som_grid_in_both_variants(tmp_path):
    # the slide puts the four campaign grids in one row (1 x 4); the report keeps 2 x 2: the aspect differs
    n, k = 50, 3
    rng = np.random.default_rng(6)
    bmu = rng.integers(0, k * k, size=n)
    entries = campaign_entries(n)
    for _ in plots_style.iter_variants():
        campaigns.plot_shortlists_som(entries, bmu, k, "sintetico", 1, tmp_path / "shortlists_som")
    for suffix in (".svg", ".png"):
        assert (tmp_path / f"shortlists_som{suffix}").stat().st_size > 0
        assert (tmp_path / "slide" / f"shortlists_som{suffix}").stat().st_size > 0
    slide = tmp_path / "slide" / "shortlists_som.svg"
    assert svg_aspect(slide) == pytest.approx(plots_style.SLIDE_FIGSIZE[0] / plots_style.SLIDE_FIGSIZE[1], abs=0.02)
    assert (tmp_path / "shortlists_som.svg").read_bytes() != slide.read_bytes()
    assert plots_style.variant() == "report"
