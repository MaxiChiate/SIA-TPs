"""Tests of the report and slide variants (D-08) of the SOM figures: component planes, stage-1 curves and the
region map with its legend beside it (`som_profiles.plot_regions`, slide layout with `legend_ax`).

Synthetic data only: small random planes, hit counts and hand-made stage-1 rows, so nothing here reads datos/ or
analysis/results/.
"""

from __future__ import annotations

import re

import numpy as np
import pytest

import plots_style
import som
import som_figures
import som_profiles

TARGET_ASPECT = plots_style.SLIDE_FIGSIZE[0] / plots_style.SLIDE_FIGSIZE[1]


@pytest.fixture(autouse=True)
def report_variant():
    plots_style.use_variant("report")
    yield
    plots_style.use_variant("report")


def svg_aspect(path) -> float:
    head = path.read_text(encoding="utf-8")[:2000]
    width = float(re.search(r'<svg[^>]*\swidth="([\d.]+)pt"', head).group(1))
    height = float(re.search(r'<svg[^>]*\sheight="([\d.]+)pt"', head).group(1))
    return width / height


def assert_both_variants(out, stem):
    """Report and slide SVG and PNG exist and are non-empty; the slide SVG has the slide aspect and differs
    from the report one (the report keeps its own size)."""
    for suffix in (".svg", ".png"):
        assert (out / f"{stem}{suffix}").stat().st_size > 0, f"report {stem}{suffix}"
        assert (out / "slide" / f"{stem}{suffix}").stat().st_size > 0, f"slide {stem}{suffix}"
    slide_svg = out / "slide" / f"{stem}.svg"
    assert svg_aspect(slide_svg) == pytest.approx(TARGET_ASPECT, abs=0.02)
    assert (out / f"{stem}.svg").read_bytes() != slide_svg.read_bytes()


def synthetic_planes(k, count=5, seed=5):
    rng = np.random.default_rng(seed)
    planes = []
    for index in range(count):
        kind = "z" if index % 2 == 0 else "raw"
        values = rng.normal(size=(k, k)) if kind == "z" else rng.uniform(10, 500, size=(k, k))
        planes.append(som_figures.Plane(name=f"var{index}", values=values, kind=kind,
                                        unit="z" if kind == "z" else "USD"))
    return planes


def test_plot_planes_in_both_variants(tmp_path):
    k = 4
    planes = synthetic_planes(k)
    hits = np.zeros(k * k, dtype=int)
    hits[:10] = np.arange(1, 11)  # six empty neurons, to exercise the hatched empty cells too
    for _ in plots_style.iter_variants():
        som_figures.plot_planes(planes, k, hits, "Planos sinteticos", "caption", tmp_path / "planes")
    assert_both_variants(tmp_path, "planes")
    assert plots_style.variant() == "report"


def test_plot_stage1_curves_in_both_variants(tmp_path):
    rows = []
    for neighborhood in ("step", "gaussian"):
        for grid_k in (3, 4, 5):
            row = {"neighborhood": neighborhood, "grid_k": str(grid_k), "stability": str(0.6 + 0.05 * grid_k)}
            for measure, base in (("qe", 0.9), ("qe_loo", 1.1), ("te", 0.4), ("empty_fraction", 0.2),
                                  ("creators_per_occupied", 2.0)):
                row[f"{measure}_mean"] = str(base / grid_k + (0.05 if neighborhood == "gaussian" else 0.0))
                row[f"{measure}_sd"] = str(0.01 * grid_k)
            rows.append(row)
    selection = {"thresholds": {"te_max": 0.5, "empty_max": 0.3, "creators_min": 1.0}, "chosen_k": 4,
                 "qe_train_argmin_k": 5}
    for _ in plots_style.iter_variants():
        som_figures.plot_stage1_curves(rows, selection, tmp_path / "stage1_curves")
    assert_both_variants(tmp_path, "stage1_curves")
    assert plots_style.variant() == "report"


def synthetic_regions(k, region_sizes, cut_every):
    """Adjacent neurons of the k x k grid joined in pairs; a region's size is its neuron count."""
    labels = []
    for region in range(len(region_sizes)):
        labels.extend([region] * region_sizes[region])
    labels.extend([-1] * (k * k - len(labels)))
    labels = np.asarray(labels, dtype=int)
    cut = np.zeros(len(som.adjacent_pairs(k)), dtype=bool)
    cut[::cut_every] = True
    sizes = np.asarray(region_sizes, dtype=int)
    interpretable = sizes >= som_profiles.MIN_MEMBERS
    return som_profiles.RegionResult(labels=labels, threshold=1.0, cut=cut, sizes=sizes,
                                     interpretable=interpretable)


def test_plot_regions_slide_legend_beside_the_map(tmp_path):
    k = 4
    result = synthetic_regions(k, region_sizes=[5, 4, 3, 1], cut_every=3)
    hits = np.arange(k * k) % 4
    for _ in plots_style.iter_variants():
        som_profiles.plot_regions(result, hits, k, [], "Regiones sinteticas", "caption", tmp_path / "regions")
    assert_both_variants(tmp_path, "regions")
    assert plots_style.variant() == "report"


def test_plot_regions_slide_with_more_regions_than_palette_slots(tmp_path):
    # nine interpretable regions (more than the 8 palette slots): every cell keeps the neutral fill, no ninth
    # colour, and the slide still draws with the same aspect
    k = 5
    result = synthetic_regions(k, region_sizes=[2] * 9, cut_every=4)
    hits = np.ones(k * k, dtype=int)
    for _ in plots_style.iter_variants():
        som_profiles.plot_regions(result, hits, k, [], "Muchas regiones", "caption", tmp_path / "many")
    assert_both_variants(tmp_path, "many")
    assert plots_style.variant() == "report"
