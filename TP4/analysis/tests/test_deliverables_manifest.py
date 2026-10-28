"""Integrity tests of the deliverables manifest (DELIV-02, DELIV-03).

They read the versioned fragments and the Makefile, never analysis/results (not versioned).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import deliverables_manifest as manifest
import informe

TP_DIR = Path(__file__).resolve().parents[2]
RESULT_FOLDERS = ("eda/", "pca/", "som/", "oja/", "campaigns/", "hopfield/")


def fragment_ids(number: int) -> set[str]:
    path = next(TP_DIR / item[1] for item in manifest.FRAGMENTS if item[0] == number)
    page = informe.render_fragment(path.read_text(encoding="utf-8"), number, [])
    return set(re.findall(r'<h[1-6] id="([^"]+)"', page))


def makefile_targets() -> set[str]:
    text = (TP_DIR / "Makefile").read_text(encoding="utf-8")
    return set(re.findall(r"^([A-Za-z0-9_.-]+):", text, flags=re.M))


def test_questions_are_25_with_unique_ids():
    ids = [q.id for q in manifest.QUESTIONS]
    expected = [f"Q1.{i}" for i in range(1, 18)] + [f"Q2.{i}" for i in range(1, 9)]
    assert ids == expected


def test_questions_have_text_section_and_anchors():
    for question in manifest.QUESTIONS:
        assert question.text.strip(), question.id
        assert question.enunciado_section in {"1.1", "1.2", "1.3", "1.4", "2.1", "2.2"}, question.id
        assert question.anchors, question.id


def test_every_question_anchor_is_a_real_heading_id():
    cache = {n: fragment_ids(n) for n in range(1, 6)}
    for question in manifest.QUESTIONS:
        for anchor in question.anchors:
            number = int(re.match(r"f(\d+)-", anchor).group(1))
            assert anchor in cache[number], f"{question.id}: {anchor}"


def test_question_fragment_is_the_fragment_of_its_first_anchor():
    for question in manifest.QUESTIONS:
        assert question.anchors[0].startswith(f"f{question.fragment}-"), question.id


def test_fragments_list_five_existing_files():
    assert [(n, e) for n, _, e, _ in manifest.FRAGMENTS] == [(1, 1), (2, 1), (3, 1), (4, 2), (5, 2)]
    for _, path, _, _ in manifest.FRAGMENTS:
        assert (TP_DIR / path).is_file(), path


def test_figure_anchors_are_real_heading_ids():
    cache = {n: fragment_ids(n) for n in range(1, 6)}
    for item in manifest.FIGURES:
        assert item.anchor in cache[item.fragment], item.key


def test_figure_make_targets_are_makefile_targets():
    targets = makefile_targets()
    for item in manifest.FIGURES:
        assert item.make_target in targets, item.key


def test_figure_keys_are_unique_and_counts_match():
    keys = [item.key for item in manifest.FIGURES]
    assert len(keys) == len(set(keys)) == 32
    assert sum(item.slide for item in manifest.FIGURES) == 23


def test_figure_paths_are_svg_inside_result_folders():
    for item in manifest.FIGURES:
        assert item.path.endswith(".svg"), item.key
        assert item.path.startswith(RESULT_FOLDERS), item.key


def test_slide_path_puts_slide_folder_before_the_file_name():
    assert manifest.slide_path(manifest.figure("som_map")) == "som/figures/slide/map.svg"
    assert manifest.slide_path(manifest.figure("pca_eigenvalues")) == "pca/audited/slide/eigenvalues_variance.svg"


def test_figure_lookup_rejects_unknown_key():
    with pytest.raises(KeyError):
        manifest.figure("nope")


def test_questions_sheet_lists_every_question_and_anchor_heading():
    lines = manifest.questions_sheet()
    rows = [line for line in lines if re.match(r"Q[12]\.\d+ \(", line)]
    assert len(rows) == 25
    assert lines[-1] == (
        f"QUESTIONS 25 checked={manifest.QUESTIONS_CHECKED_AGAINST_PDF} "
        f"sections_checked={manifest.ANSWER_SECTIONS_CHECKED}"
    )
    assert "    -> f2-s6-4 6.4 ¿Coinciden las regiones con PC1 y PC2 (biplot)?" in lines


def test_questions_sheet_fails_naming_question_and_anchor(monkeypatch):
    bad = (manifest.Question("Q9.9", "x", "1.1", 2, ("f2-s99",)),)
    monkeypatch.setattr(manifest, "QUESTIONS", bad)
    with pytest.raises(SystemExit) as error:
        manifest.questions_sheet()
    assert "Q9.9" in str(error.value) and "f2-s99" in str(error.value)


def test_main_prints_the_sheet(capsys):
    assert manifest.main(["questions"]) == 0
    out = capsys.readouterr().out
    assert out.rstrip().splitlines()[-1].startswith("QUESTIONS 25 checked=")


def test_main_rejects_other_arguments():
    assert manifest.main([]) == 2


def test_questions_checked_against_pdf():
    assert manifest.QUESTIONS_CHECKED_AGAINST_PDF is True


def test_answer_sections_checked():
    assert manifest.ANSWER_SECTIONS_CHECKED is True
