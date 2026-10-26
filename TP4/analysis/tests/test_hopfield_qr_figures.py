"""Tests of the report and slide variants (D-08) of the Hopfield-on-QR figures.

Synthetic data only: five random +-1 patterns of 1369 pixels (37 x 37) and hand-made trace rows, so nothing here
reads datos/ or analysis/results/. The driver (`draw`) is not run: it refuses without the pre-registered results.
"""

from __future__ import annotations

import re

import numpy as np
import pytest

import hopfield_qr
import hopfield_qr_figures as figures
import hopfield_qr_limits
import plots_style

N_PIXELS = 1369


@pytest.fixture(autouse=True)
def report_variant():
    plots_style.use_variant("report")
    yield
    plots_style.use_variant("report")


@pytest.fixture(scope="module")
def patterns():
    rng = np.random.default_rng(11)
    return np.where(rng.random((5, N_PIXELS)) < 0.5, -1, 1).astype(np.int64)


def svg_aspect(path):
    head = path.read_text(encoding="utf-8")[:2000]
    width = float(re.search(r'<svg[^>]*\swidth="([\d.]+)pt"', head).group(1))
    height = float(re.search(r'<svg[^>]*\sheight="([\d.]+)pt"', head).group(1))
    return width / height


def draw_pair(patterns, out):
    overlaps = hopfield_qr.overlaps_json(patterns)
    majority = hopfield_qr_limits.majority_json(patterns)
    for _ in plots_style.iter_variants():
        figures.plot_qr(patterns, out / "qr")
        figures.plot_overlaps(overlaps, out / "overlaps")
        figures.plot_majority(majority, out / "majority")


def energy_rows():
    rows = []
    for rule in ("hebb", "pinv"):
        for source in range(5):
            for noise in (0.0, 0.25, 0.5):
                for step in range(6):
                    # noise 0 is a constant trace: the case that needs its own tick in the slide
                    energy = -100.0 if noise == 0.0 else -10.0 * step - source
                    rows.append({"rule": rule, "source": str(source), "noise": str(noise), "step": str(step),
                                 "energy": str(energy)})
    return rows


def test_report_and_slide_files_exist_with_slide_aspect(patterns, tmp_path):
    draw_pair(patterns, tmp_path)
    target = plots_style.SLIDE_FIGSIZE[0] / plots_style.SLIDE_FIGSIZE[1]
    for stem in ("qr", "overlaps", "majority"):
        assert (tmp_path / f"{stem}.svg").stat().st_size > 0, stem
        assert (tmp_path / f"{stem}.png").stat().st_size > 0, stem
        slide = tmp_path / "slide" / f"{stem}.svg"
        assert slide.stat().st_size > 0, stem
        assert (tmp_path / "slide" / f"{stem}.png").stat().st_size > 0, stem
        assert abs(svg_aspect(slide) - target) < 0.02, stem
        assert abs(svg_aspect(tmp_path / f"{stem}.svg") - target) > 0.02, stem  # the report keeps its own size
    assert plots_style.variant() == "report"


def test_report_svgs_are_byte_identical_on_a_second_draw(patterns, tmp_path):
    draw_pair(patterns, tmp_path / "a")
    draw_pair(patterns, tmp_path / "b")
    for stem in ("qr", "overlaps", "majority"):
        assert (tmp_path / "a" / f"{stem}.svg").read_bytes() == (tmp_path / "b" / f"{stem}.svg").read_bytes()
        assert (tmp_path / "a" / "slide" / f"{stem}.svg").read_bytes() == \
            (tmp_path / "b" / "slide" / f"{stem}.svg").read_bytes()


def test_report_figure_is_not_changed_by_drawing_the_slide(patterns, tmp_path):
    overlaps = hopfield_qr.overlaps_json(patterns)
    figures.plot_overlaps(overlaps, tmp_path / "only_report")
    draw_pair(patterns, tmp_path / "both")
    assert (tmp_path / "only_report.svg").read_bytes() == (tmp_path / "both" / "overlaps.svg").read_bytes()


def test_slide_has_no_caption_or_title_and_report_has_both(patterns, tmp_path):
    draw_pair(patterns, tmp_path)
    report = (tmp_path / "overlaps.svg").read_text(encoding="utf-8")
    slide = (tmp_path / "slide" / "overlaps.svg").read_text(encoding="utf-8")
    assert report.count("<g id=\"text_") > slide.count("<g id=\"text_")


def test_energy_trace_slide_layout_on_synthetic_rows(tmp_path):
    rows = energy_rows()
    for _ in plots_style.iter_variants():
        figures.plot_energy_trace(rows, tmp_path / "energy_trace")
    target = plots_style.SLIDE_FIGSIZE[0] / plots_style.SLIDE_FIGSIZE[1]
    slide = tmp_path / "slide" / "energy_trace.svg"
    assert slide.stat().st_size > 0 and (tmp_path / "energy_trace.svg").stat().st_size > 0
    assert abs(svg_aspect(slide) - target) < 0.02


def recovery_rows():
    """Hand-made rows of the recovery figure: hebb and pinv with both updates (dynamical cost), hamming as a
    single no-update line, over four noise levels."""
    rows = []
    for rule in ("hebb", "pinv", "hamming"):
        updates = ("none",) if rule == "hamming" else ("async", "sync")
        for update in updates:
            for index, noise in enumerate((0.0, 0.1, 0.3, 0.5)):
                rows.append({"rule": rule, "update": update, "noise": str(noise), "n_trials": "5",
                             "recall_rate": str(max(0.0, 1.0 - 2.0 * noise)), "recall_sd_seeds": "0.05",
                             "mean_final_overlap": str(max(0.0, 0.9 - noise)), "mean_sweeps": str(2 + index),
                             "mean_final_energy": str(-100.0 + 10 * index)})
    return rows


def shift_record(n_pixels=N_PIXELS):
    """A shift.json record with two shift magnitudes; the glyphs are random so the panels differ."""
    rng = np.random.default_rng(21)
    side = int(round(n_pixels ** 0.5))
    source = np.where(rng.random(n_pixels) < 0.5, -1, 1).astype(int)
    shifts = []
    for shift in (1, 2):
        query = np.where(rng.random(n_pixels) < 0.5, -1, 1).astype(int)
        recovered = np.where(rng.random(n_pixels) < 0.5, -1, 1).astype(int)
        shifts.append({"shift": shift, "query": query.tolist(), "query_hamming": int(np.sum(query != source)),
                       "recovered": recovered.tolist(),
                       "recovered_hamming": int(np.sum(recovered != source))})
    return {"n_pixels": n_pixels, "side": side, "source": 0, "source_pattern": source.tolist(),
            "edge_convention": "zero", "shifts": shifts}


def test_recovery_figure_slide_legend_in_both_variants(tmp_path):
    rows = recovery_rows()
    for _ in plots_style.iter_variants():
        figures.plot_recovery(rows, tmp_path / "recovery")
    target = plots_style.SLIDE_FIGSIZE[0] / plots_style.SLIDE_FIGSIZE[1]
    for suffix in (".svg", ".png"):
        assert (tmp_path / f"recovery{suffix}").stat().st_size > 0
        assert (tmp_path / "slide" / f"recovery{suffix}").stat().st_size > 0
    slide = tmp_path / "slide" / "recovery.svg"
    assert abs(svg_aspect(slide) - target) < 0.02
    assert (tmp_path / "recovery.svg").read_bytes() != slide.read_bytes()
    assert plots_style.variant() == "report"


def test_shift_figure_one_row_in_slide_in_both_variants(tmp_path):
    shift = shift_record()
    for _ in plots_style.iter_variants():
        figures.plot_shift(shift, tmp_path / "shift")
    target = plots_style.SLIDE_FIGSIZE[0] / plots_style.SLIDE_FIGSIZE[1]
    for suffix in (".svg", ".png"):
        assert (tmp_path / f"shift{suffix}").stat().st_size > 0
        assert (tmp_path / "slide" / f"shift{suffix}").stat().st_size > 0
    slide = tmp_path / "slide" / "shift.svg"
    assert abs(svg_aspect(slide) - target) < 0.02
    # the report keeps its 3 columns x 2 rows grid (taller than the slide), the slide one row of 5 panels
    assert abs(svg_aspect(tmp_path / "shift.svg") - target) > 0.02
    assert (tmp_path / "shift.svg").read_bytes() != slide.read_bytes()
    assert plots_style.variant() == "report"
