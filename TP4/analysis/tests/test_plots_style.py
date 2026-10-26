"""Tests of the figure variants of plots_style (D-08): report is the default and unchanged, slide is another style."""

from __future__ import annotations

import numpy as np
import pytest

import plots_style


@pytest.fixture(autouse=True)
def report_variant():
    plots_style.use_variant("report")
    yield
    plots_style.use_variant("report")


def tiny_figure(plt):
    fig, ax = plt.subplots(figsize=plots_style.figsize((3.0, 2.0)))
    ax.plot([0, 1, 2], [0, 1, 0])
    ax.set_title("t")
    return fig


def test_unknown_variant_raises_and_default_is_report():
    assert plots_style.variant() == "report"
    with pytest.raises(ValueError):
        plots_style.use_variant("poster")
    assert plots_style.variant() == "report"


def test_iter_variants_order_and_restore():
    seen = []
    for name in plots_style.iter_variants():
        seen.append((name, plots_style.variant()))
    assert seen == [("report", "report"), ("slide", "slide")]
    assert plots_style.variant() == "report"


def test_iter_variants_restores_report_when_the_body_raises():
    with pytest.raises(RuntimeError):
        for name in plots_style.iter_variants():
            if name == "slide":
                raise RuntimeError("plot failed")
    assert plots_style.variant() == "report"


def test_figsize_and_rect_by_variant():
    assert plots_style.figsize((11.5, 6.4)) == (11.5, 6.4)
    assert plots_style.rect((0, 0.13, 1, 0.96)) == (0, 0.13, 1, 0.96)
    plots_style.use_variant("slide")
    assert plots_style.figsize((11.5, 6.4)) == plots_style.SLIDE_FIGSIZE
    assert plots_style.figsize((7, 7), slide=(8, 4.5)) == (8, 4.5)
    assert plots_style.rect((0, 0.13, 1, 0.96)) == (0, 0, 1, 1)
    assert plots_style.fontsize(8) == pytest.approx(8 * plots_style.SLIDE_FONT_SIZE / 10.0)
    plots_style.use_variant("report")
    assert plots_style.fontsize(8) == 8


def test_slide_figsize_is_the_figure_area_of_the_artifact_format():
    width, height = plots_style.SLIDE_FIGSIZE
    assert width == 12.8
    assert width / height == pytest.approx(1664 / 630, abs=0.02)


def test_caption_and_suptitle_only_in_report():
    plt = plots_style.apply_style()
    fig = plt.figure()
    plots_style.caption(fig, "texto")
    assert len(fig.texts) == 1
    plots_style.suptitle(fig, "titulo")
    assert fig.get_suptitle() == "titulo"
    plt.close(fig)

    plots_style.use_variant("slide")
    fig = plt.figure()
    plots_style.caption(fig, "texto")
    plots_style.suptitle(fig, "titulo")
    assert len(fig.texts) == 0
    assert fig.get_suptitle() == ""
    plt.close(fig)


def test_apply_style_font_size_by_variant():
    plt = plots_style.apply_style()
    assert plt.rcParams["font.size"] == 10.0
    plots_style.use_variant("slide")
    plt = plots_style.apply_style()
    assert plt.rcParams["font.size"] == plots_style.SLIDE_FONT_SIZE
    plots_style.use_variant("report")
    assert plots_style.apply_style().rcParams["font.size"] == 10.0


def test_save_figure_paths_by_variant(tmp_path):
    for name in plots_style.iter_variants():
        plt = plots_style.apply_style()
        plots_style.save_figure(tiny_figure(plt), tmp_path / "fig")
    for suffix in (".svg", ".png"):
        assert (tmp_path / f"fig{suffix}").stat().st_size > 0
        assert (tmp_path / "slide" / f"fig{suffix}").stat().st_size > 0


def test_slide_png_is_about_twice_its_box(tmp_path):
    plots_style.use_variant("slide")
    plt = plots_style.apply_style()
    _svg, png = plots_style.save_figure(tiny_figure(plt), tmp_path / "fig")
    data = png.read_bytes()
    width, height = int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    assert abs(width - 3200) <= 2
    assert abs(width / height - plots_style.SLIDE_FIGSIZE[0] / plots_style.SLIDE_FIGSIZE[1]) < 0.02


def test_report_figure_bytes_survive_a_slide_pass(tmp_path):
    def draw(out):
        plt = plots_style.apply_style()
        plots_style.save_figure(tiny_figure(plt), out / "fig")
        return (out / "fig.svg").read_bytes()

    before = draw(tmp_path / "before")
    for _ in plots_style.iter_variants():
        pass
    plots_style.use_variant("slide")
    plots_style.apply_style()
    plots_style.use_variant("report")
    after = draw(tmp_path / "after")
    assert before == after


def test_plot_map_writes_both_variants(tmp_path):
    import som_figures

    k = 2
    hits = np.array([3, 0, 1, 2])
    U = np.array([[1.0, 2.0], [3.0, 4.0]])
    for _ in plots_style.iter_variants():
        som_figures.plot_map(hits, U, k, "t", "caption", tmp_path / "map")
    assert (tmp_path / "map.svg").is_file()
    assert (tmp_path / "slide" / "map.svg").is_file()
    assert (tmp_path / "map.svg").read_bytes() != (tmp_path / "slide" / "map.svg").read_bytes()
    assert plots_style.variant() == "report"
