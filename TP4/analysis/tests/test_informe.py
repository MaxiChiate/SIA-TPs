"""Tests of the informe builder: anchors, figure cards, question table and the build-time assertions (DELIV-02).

Every input is built in tmp_path; nothing here reads analysis/results (not versioned).
"""

from __future__ import annotations

import base64
import hashlib
import re

import pytest

import deliverables_manifest as manifest
import informe

from test_facts import write_results

SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"><rect width="4" height="4"/></svg>'

FRAGMENT = """# Fase 9 — Título

Texto inicial.

<!-- regla:inicio -->

## 1. A

Cuerpo de A.

### 1.2 B

| a | b |
|---|---|
| 1 | 2 |

<!-- regla:fin -->

## 2. C

Cierre.
"""

SKELETON = ("<!doctype", "<html", "<head", "<body")


def make_fixture(tmp_path, *, anchor="f9-s1-2"):
    results = write_results(tmp_path / "results")
    figure_path = results / "fx" / "fig.svg"
    figure_path.parent.mkdir(parents=True)
    figure_path.write_bytes(SVG)
    deliverables = tmp_path / "deliverables"
    deliverables.mkdir()
    (deliverables / "09-x.md").write_text(FRAGMENT, encoding="utf-8")
    fragments = ((9, "deliverables/09-x.md", 1, "X"),)
    questions = (manifest.Question("Q9.1", "¿Qué es <b>B</b>?", "1.2", 9, (anchor,)),)
    figures = (
        manifest.Figure(
            key="fx", path="fx/fig.svg", make_target="fx", config="c.json", seed="1", fragment=9,
            anchor="f9-s1-2", alt="alt <i>", caption="cap & co", slide=False,
        ),
    )
    return results, deliverables, fragments, questions, figures


def build(tmp_path, **override):
    results, deliverables, fragments, questions, figures = make_fixture(tmp_path)
    kwargs = {"questions": questions, "figures": figures, "fragments": fragments, "repo_dir": tmp_path}
    kwargs.update(override)
    return informe.build(results, deliverables, tmp_path / "out" / "informe.html", **kwargs)


def test_slugify_numbered_heading():
    assert informe.make_slugify(9)("6.4 ¿Coinciden?") == "f9-s6-4"


def test_slugify_numbered_heading_with_trailing_dot():
    assert informe.make_slugify(9)("1. Carga") == "f9-s1"


def test_slugify_top_heading():
    assert informe.make_slugify(9)("Fase 9 — Título") == "f9"


def test_slugify_unnumbered_heading_is_ascii_and_legal():
    slug = informe.make_slugify(9)("¿Qué más? Ñandú/año")
    assert slug.startswith("f9-")
    assert re.fullmatch(r"[A-Za-z0-9._~-]+", slug)


def test_render_fragment_anchors_table_comments_and_top_heading():
    out = informe.render_fragment(FRAGMENT, 9, ())
    for anchor in ("f9", "f9-s1", "f9-s1-2", "f9-s2"):
        assert f'id="{anchor}"' in out
    assert re.search(r'<div class="table-wrap">\s*<table>', out)
    assert "<!--" not in out
    assert "Detalle técnico (Fase 9)" in re.search(r'<h3 id="f9">(.*?)</h3>', out).group(1)


def test_render_fragment_duplicate_heading_gets_underscore_suffix():
    out = informe.render_fragment("# Fase 9 — T\n\n## Resumen\n\nx\n\n## Resumen\n\ny\n", 9, ())
    assert 'id="f9-resumen"' in out
    assert 'id="f9-resumen_1"' in out


def test_figure_card_data_uri_decodes_to_the_file_bytes(tmp_path):
    path = tmp_path / "t.svg"
    path.write_bytes(SVG)
    card = informe.figure_card(path, "alt", "caption")
    blob = re.search(r'src="data:image/svg\+xml;base64,([A-Za-z0-9+/=]+)"', card).group(1)
    assert base64.b64decode(blob) == SVG
    assert "<svg" not in card


def test_figure_card_escapes_alt_and_caption(tmp_path):
    path = tmp_path / "t.svg"
    path.write_bytes(SVG)
    card = informe.figure_card(path, '"><script>', "<b>")
    assert "<script>" not in card
    assert "&lt;b&gt;" in card


def test_render_fragment_puts_the_card_at_the_end_of_its_section(tmp_path):
    results, _deliverables, _fragments, _questions, figures = make_fixture(tmp_path)
    out = informe.render_fragment(FRAGMENT, 9, figures, results)
    card = out.index('<figure class="fig">')
    assert out.index('id="f9-s1-2"') < card < out.index('id="f9-s2"')


def test_question_table_links_and_escapes():
    questions = (manifest.Question("Q", "¿<b>x</b>?", "1.2", 2, ("f2-s6-4", "f2-s5")),)
    out = informe.question_table(questions)
    assert 'href="#f2-s6-4"' in out and "Fase 2, §6.4" in out
    assert 'href="#f2-s5"' in out and "Fase 2, §5" in out
    assert "<b>" not in out and "(sección 1.2)" in out
    assert out.startswith('<div class="table-wrap">')


def test_stamp_outside_a_repo_has_no_path(tmp_path):
    assert informe.stamp(tmp_path) == "commit desconocido"


def test_build_writes_a_contract_page(tmp_path):
    out = build(tmp_path)
    page = out.read_text(encoding="utf-8")
    assert page.startswith("<title>Informe TP4 SIA</title>")
    assert 'id="f9-s1-2"' in page and 'href="#f9-s1-2"' in page
    assert 'data-fact="som.r2_pc1">0,961<' in page
    assert "prefers-color-scheme: dark" in page and '[data-theme="dark"]' in page
    assert "claude:viewport-fit-sides" in page and "table-wrap" in page
    assert "--figure-surface: #fcfcfb" in page
    assert "<script" not in page.lower()
    lowered = page.lower()
    assert not any(tag in lowered for tag in SKELETON)
    assert "<b>B</b>" not in page


def test_build_never_writes_the_fragment(tmp_path):
    results, deliverables, fragments, questions, figures = make_fixture(tmp_path)
    source = deliverables / "09-x.md"
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    informe.build(results, deliverables, tmp_path / "o.html", questions=questions, figures=figures,
                  fragments=fragments, repo_dir=tmp_path)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before


def test_build_stops_on_an_absent_question_anchor(tmp_path):
    results, deliverables, fragments, _questions, figures = make_fixture(tmp_path)
    questions = (manifest.Question("Q", "x", "1.2", 9, ("f9-s7",)),)
    with pytest.raises(SystemExit) as stop:
        informe.build(results, deliverables, tmp_path / "o.html", questions=questions, figures=figures,
                      fragments=fragments, repo_dir=tmp_path)
    assert "f9-s7" in str(stop.value)


def test_build_stops_when_the_page_is_over_the_size_ceiling(tmp_path, monkeypatch):
    monkeypatch.setattr(informe, "MAX_BYTES", 100)
    with pytest.raises(SystemExit) as stop:
        build(tmp_path)
    assert "byte" in str(stop.value)


def test_build_stops_when_a_result_is_missing(tmp_path):
    results, deliverables, fragments, questions, figures = make_fixture(tmp_path)
    (results / "som" / "series_som_stage1" / "selection.json").unlink()
    with pytest.raises(SystemExit) as stop:
        informe.build(results, deliverables, tmp_path / "o.html", questions=questions, figures=figures,
                      fragments=fragments, repo_dir=tmp_path)
    assert "make results" in str(stop.value)


def test_build_stops_when_the_figure_is_missing(tmp_path):
    results, deliverables, fragments, questions, figures = make_fixture(tmp_path)
    (results / "fx" / "fig.svg").unlink()
    with pytest.raises(SystemExit) as stop:
        informe.build(results, deliverables, tmp_path / "o.html", questions=questions, figures=figures,
                      fragments=fragments, repo_dir=tmp_path)
    assert "make fx" in str(stop.value)


@pytest.mark.parametrize("leak", ["/Users/someone/work", "someone@example.com", "<script>x</script>"])
def test_build_stops_on_a_leak(tmp_path, leak):
    results, deliverables, fragments, questions, figures = make_fixture(tmp_path)
    (deliverables / "09-x.md").write_text(FRAGMENT + f"\n\nfuga {leak}\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        informe.build(results, deliverables, tmp_path / "o.html", questions=questions, figures=figures,
                      fragments=fragments, repo_dir=tmp_path)


def test_build_stops_on_an_unresolved_fact_placeholder(tmp_path):
    results, deliverables, fragments, questions, figures = make_fixture(tmp_path)
    (deliverables / "09-x.md").write_text(FRAGMENT + "\n\nvalor {som.r2_pc1}\n", encoding="utf-8")
    with pytest.raises(SystemExit) as stop:
        informe.build(results, deliverables, tmp_path / "o.html", questions=questions, figures=figures,
                      fragments=fragments, repo_dir=tmp_path)
    assert "som.r2_pc1" in str(stop.value)
