"""The reproduction documents (README.md, CLAUDE.md, DECISIONS.md) stay present and consistent (DELIV-03).

In TP3 CLAUDE.md and DECISIONS.md were deleted on delivery day (commits 31958a4 and bcce0da) and nothing failed. These
tests turn that into a red `make test`: the three documents exist and are not near empty, every `make <target>` they name
is defined in the Makefile, every figure of the deliverables manifest has a README row with its make target, DECISIONS.md
keeps its entries for each phase, none of the documents leaks a home-directory path or an e-mail address, and no slides
export is versioned in docs/ (D-14).

Every check is a function of a root folder, so the failing cases are exercised on scratch copies of the real files
(a document missing, a target that does not exist, a figure row removed, a slides PDF added) and the real tree is
checked with the same functions. Only versioned files are read.
"""

from __future__ import annotations

import fnmatch
import re
import shutil
from pathlib import Path

import pytest

from conftest import TP_DIR
from deliverables_manifest import FIGURES

MIN_LINES = {"README.md": 60, "CLAUDE.md": 40, "DECISIONS.md": 200}
MAKE_MENTION = re.compile(r"\bmake[ \t]+([a-z][a-z0-9-]*)")
MAKE_TARGET_DEFINITION = re.compile(r"^([a-z][a-z0-9-]*)[ \t]*:(?!=)", re.MULTILINE)
HOME_PATH = re.compile(r"/Users/[^\s/]+|/home/[^\s/]+|[A-Za-z]:\\Users\\")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
NEGATION = re.compile(r"\b(no|ni|sin|nunca)\b", re.IGNORECASE)
FRAGMENT_PHASES = range(1, 7)


def _read(root: Path, name: str) -> str:
    return (root / name).read_text(encoding="utf-8")


def non_empty_lines(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


def check_presence(root: Path) -> list[str]:
    problems = []
    for name, minimum in MIN_LINES.items():
        path = root / name
        if not path.is_file():
            problems.append(f"{name} is missing")
        elif non_empty_lines(path.read_text(encoding="utf-8")) < minimum:
            problems.append(f"{name} has fewer than {minimum} non-empty lines")
    return problems


def defined_targets(makefile_text: str) -> set[str]:
    return set(MAKE_TARGET_DEFINITION.findall(makefile_text))


def check_make_targets(root: Path) -> list[str]:
    defined = defined_targets(_read(root, "Makefile"))
    problems = []
    for name in ("README.md", "CLAUDE.md"):
        if not (root / name).is_file():
            continue
        for number, line in enumerate(_read(root, name).splitlines(), start=1):
            for target in MAKE_MENTION.findall(line):
                if target not in defined:
                    problems.append(f"{name}:{number} names `make {target}`, which the Makefile does not define")
    return problems


def check_figure_rows(root: Path) -> list[str]:
    lines = _read(root, "README.md").splitlines()
    problems = []
    for figure in FIGURES:
        command = re.compile(rf"\bmake {re.escape(figure.make_target)}(?![a-z0-9-])")
        if not any(figure.path in line and command.search(line) for line in lines):
            problems.append(f"README.md has no row with {figure.path} and `make {figure.make_target}`")
    return problems


def check_decisions_phases(root: Path) -> list[str]:
    text = _read(root, "DECISIONS.md")
    return [f"DECISIONS.md has no `### F{n} D-` heading"
            for n in FRAGMENT_PHASES if not re.search(rf"^### F{n} D-", text, re.MULTILINE)]


def check_no_leaks(root: Path) -> list[str]:
    problems = []
    for name in MIN_LINES:
        if not (root / name).is_file():
            continue
        text = _read(root, name)
        if HOME_PATH.search(text):
            problems.append(f"{name} contains an absolute home-directory path")
        if EMAIL.search(text):
            problems.append(f"{name} contains an e-mail address")
    return problems


def check_no_slides_export(root: Path) -> list[str]:
    docs = root / "docs"
    if not docs.is_dir():
        return []
    problems = []
    for path in sorted(docs.rglob("*")):
        lowered = path.name.lower()
        if path.is_file() and (fnmatch.fnmatch(lowered, "slides_tp4*") or lowered.endswith(".pptx")):
            problems.append(f"docs/{path.relative_to(docs).as_posix()} is a slides export (D-14)")
    return problems


def check_no_informe_export(root: Path) -> list[str]:
    """D-15: the docs may say the informe has no PDF/Word export, never describe one, nor the Docs type."""
    problems = []
    for name in ("README.md", "CLAUDE.md"):
        if not (root / name).is_file():
            continue
        for number, line in enumerate(_read(root, name).splitlines(), start=1):
            lowered = line.lower()
            exports = "informe" in lowered and re.search(r"\b(pdf|word|docx)\b", lowered)
            docs_type = "tipo docs" in lowered
            if (exports or docs_type) and not NEGATION.search(line):
                problems.append(f"{name}:{number} describes an informe export or the Docs type (D-15)")
    return problems


def make_root(tmp_path: Path) -> Path:
    """A scratch copy of the files the checks read, with an empty docs/ holding one unrelated file."""
    for name in (*MIN_LINES, "Makefile"):
        shutil.copy(TP_DIR / name, tmp_path / name)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "Archivo SIATP 42026.pdf").write_bytes(b"%PDF-1.4\n")
    return tmp_path


# ---- the real tree ---------------------------------------------------------------------------------------------


def test_real_documents_exist_and_are_not_near_empty():
    assert check_presence(TP_DIR) == []


def test_real_documents_only_name_make_targets_the_makefile_defines():
    assert check_make_targets(TP_DIR) == []


def test_real_readme_has_a_row_with_the_make_target_for_every_manifest_figure():
    assert len(FIGURES) == 32
    assert check_figure_rows(TP_DIR) == []


def test_real_decisions_has_entries_for_each_phase_one_to_six():
    assert check_decisions_phases(TP_DIR) == []


def test_real_documents_have_no_home_path_and_no_email():
    assert check_no_leaks(TP_DIR) == []


def test_real_docs_folder_has_no_slides_export():
    assert check_no_slides_export(TP_DIR) == []


def test_real_documents_do_not_describe_an_informe_export():
    assert check_no_informe_export(TP_DIR) == []


# ---- the failing cases, on scratch copies ----------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(MIN_LINES))
def test_a_deleted_document_is_reported(tmp_path, name):
    root = make_root(tmp_path)
    (root / name).unlink()
    assert f"{name} is missing" in check_presence(root)


@pytest.mark.parametrize("name", sorted(MIN_LINES))
def test_a_near_empty_document_is_reported(tmp_path, name):
    root = make_root(tmp_path)
    (root / name).write_text("# placeholder\n\ntext\n", encoding="utf-8")
    assert any(problem.startswith(f"{name} has fewer than") for problem in check_presence(root))


def test_the_unmodified_scratch_copy_has_no_problem_in_any_check(tmp_path):
    root = make_root(tmp_path)
    for check in (check_presence, check_make_targets, check_figure_rows, check_decisions_phases, check_no_leaks,
                  check_no_slides_export, check_no_informe_export):
        assert check(root) == [], check.__name__


def test_a_documented_make_target_that_does_not_exist_is_reported(tmp_path):
    root = make_root(tmp_path)
    (root / "README.md").write_text(_read(root, "README.md") + "\nCorré `make no-such-target` para probar.\n",
                                    encoding="utf-8")
    problems = check_make_targets(root)
    assert len(problems) == 1 and "make no-such-target" in problems[0]


def test_a_target_removed_from_the_makefile_is_reported_where_the_docs_name_it(tmp_path):
    root = make_root(tmp_path)
    makefile = _read(root, "Makefile")
    (root / "Makefile").write_text(makefile.replace("\ndeliverables:", "\nrenamed-deliverables:"), encoding="utf-8")
    assert any("make deliverables" in problem for problem in check_make_targets(root))


def test_a_manifest_figure_without_its_readme_row_is_reported(tmp_path):
    root = make_root(tmp_path)
    figure = FIGURES[0]
    kept = [line for line in _read(root, "README.md").splitlines() if figure.path not in line]
    (root / "README.md").write_text("\n".join(kept) + "\n", encoding="utf-8")
    assert check_figure_rows(root) == [f"README.md has no row with {figure.path} and `make {figure.make_target}`"]


def test_a_readme_row_with_the_wrong_make_target_is_reported(tmp_path):
    root = make_root(tmp_path)
    figure = next(f for f in FIGURES if f.make_target == "som-figures")
    lines = [line.replace("make som-figures", "make som-profiles") if figure.path in line else line
             for line in _read(root, "README.md").splitlines()]
    (root / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert check_figure_rows(root) == [f"README.md has no row with {figure.path} and `make som-figures`"]


def test_a_decisions_file_without_a_phase_entry_is_reported(tmp_path):
    root = make_root(tmp_path)
    text = _read(root, "DECISIONS.md").replace("\n### F3 D-", "\n### F3 X-")
    (root / "DECISIONS.md").write_text(text, encoding="utf-8")
    assert check_decisions_phases(root) == ["DECISIONS.md has no `### F3 D-` heading"]


def test_a_home_directory_path_and_an_email_are_reported(tmp_path):
    root = make_root(tmp_path)
    (root / "CLAUDE.md").write_text(_read(root, "CLAUDE.md") + "\n/Users/someone/work/TP4\n", encoding="utf-8")
    (root / "README.md").write_text(_read(root, "README.md") + "\nEscribir a alguien@example.com\n", encoding="utf-8")
    assert check_no_leaks(root) == ["README.md contains an e-mail address",
                                    "CLAUDE.md contains an absolute home-directory path"]


def test_a_slides_pdf_or_pptx_added_to_docs_is_reported(tmp_path):
    root = make_root(tmp_path)
    (root / "docs" / "Slides_TP4.pdf").write_bytes(b"%PDF-1.4\n")
    (root / "docs" / "deck.PPTX").write_bytes(b"PK")
    assert check_no_slides_export(root) == ["docs/Slides_TP4.pdf is a slides export (D-14)",
                                            "docs/deck.PPTX is a slides export (D-14)"]


def test_a_line_that_describes_an_informe_pdf_export_or_the_docs_type_is_reported(tmp_path):
    root = make_root(tmp_path)
    (root / "README.md").write_text(_read(root, "README.md") + "\nEl informe se exporta a PDF desde la página.\n"
                                    "El informe se arma con el tipo Docs.\n", encoding="utf-8")
    problems = check_no_informe_export(root)
    assert len(problems) == 2 and all("D-15" in problem for problem in problems)
