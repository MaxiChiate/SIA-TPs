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


# Findings of the fixture page: anchors that exist in the fixture fragment, numbers only as fact placeholders.
FIXTURE_FINDINGS = (
    informe.Finding("PCA", "Componentes: {pca.k_80} de {pca.n_features}.", "f9-s1"),
    informe.Finding("SOM", "Grilla k = {som.chosen_k}, R² {som.r2_pc1}.", "f9-s1-2", True),
)


def fixture_build(results, deliverables, out_path, questions, figures, fragments, repo_dir, **override):
    """informe.build on a fixture tree: fixture findings, no drift pins (the fixture fragments carry no pinned numbers)."""
    kwargs = {
        "questions": questions, "figures": figures, "fragments": fragments, "repo_dir": repo_dir,
        "findings": FIXTURE_FINDINGS, "pins": (),
    }
    kwargs.update(override)
    return informe.build(results, deliverables, out_path, **kwargs)


def build(tmp_path, **override):
    results, deliverables, fragments, questions, figures = make_fixture(tmp_path)
    return fixture_build(
        results, deliverables, tmp_path / "out" / "informe.html", questions, figures, fragments, tmp_path, **override
    )


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
    fixture_build(results, deliverables, tmp_path / "o.html", questions, figures, fragments, tmp_path)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before


def test_build_stops_on_an_absent_question_anchor(tmp_path):
    results, deliverables, fragments, _questions, figures = make_fixture(tmp_path)
    questions = (manifest.Question("Q", "x", "1.2", 9, ("f9-s7",)),)
    with pytest.raises(SystemExit) as stop:
        fixture_build(results, deliverables, tmp_path / "o.html", questions, figures, fragments, tmp_path)
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
        fixture_build(results, deliverables, tmp_path / "o.html", questions, figures, fragments, tmp_path)
    assert "make results" in str(stop.value)


def test_build_stops_when_the_figure_is_missing(tmp_path):
    results, deliverables, fragments, questions, figures = make_fixture(tmp_path)
    (results / "fx" / "fig.svg").unlink()
    with pytest.raises(SystemExit) as stop:
        fixture_build(results, deliverables, tmp_path / "o.html", questions, figures, fragments, tmp_path)
    assert "make fx" in str(stop.value)


@pytest.mark.parametrize("leak", ["/Users/someone/work", "someone@example.com", "<script>x</script>"])
def test_build_stops_on_a_leak(tmp_path, leak):
    results, deliverables, fragments, questions, figures = make_fixture(tmp_path)
    (deliverables / "09-x.md").write_text(FRAGMENT + f"\n\nfuga {leak}\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        fixture_build(results, deliverables, tmp_path / "o.html", questions, figures, fragments, tmp_path)


def test_build_stops_on_an_unresolved_fact_placeholder(tmp_path):
    results, deliverables, fragments, questions, figures = make_fixture(tmp_path)
    (deliverables / "09-x.md").write_text(FRAGMENT + "\n\nvalor {som.r2_pc1}\n", encoding="utf-8")
    with pytest.raises(SystemExit) as stop:
        fixture_build(results, deliverables, tmp_path / "o.html", questions, figures, fragments, tmp_path)
    assert "som.r2_pc1" in str(stop.value)


# ---------- whole report (06-09 task 1) ----------

def test_typed_numbers_finds_a_decimal_or_percentage_outside_the_fact_spans():
    section = (
        '<p>Vale <span class="fact" data-fact="k">0,961</span> y también 3,5 y 40 % y 7%.</p>'
        '<p><span class="fact" data-fact="p">12,5 %</span></p>'
    )
    assert informe.typed_numbers(section) == ["3,5", "40 %", "7%"]


def test_typed_numbers_ignores_text_inside_tags_and_whole_numbers():
    assert informe.typed_numbers('<a href="#f1-s2,3" title="1,5">Fase 2, §6.4 con 26 variables</a>') == []


def test_every_real_finding_fills_with_the_fixture_facts_and_has_no_typed_number(tmp_path):
    values = informe.facts.load_facts(write_results(tmp_path / "results"))
    section = informe.summary_section(informe.FINDINGS, values)
    assert informe.typed_numbers(section) == []
    assert "{" not in section
    assert section.count('data-fact="') >= 8


def test_there_are_at_least_8_findings_one_per_method_with_the_unfavorable_ones_marked():
    topics = " ".join(finding.topic for finding in informe.FINDINGS)
    for method in ("PCA", "SOM", "Oja", "Campañas", "Letras", "QR"):
        assert method in topics
    assert len(informe.FINDINGS) >= 8
    text = " ".join(finding.text for finding in informe.FINDINGS)
    for key in ("som.n_regions", "som.robust", "qr.hebb_exact_noise0", "qr.hamming_at_0_45", "qr.pinv_at_0_45",
                "qr.noise_high"):
        assert "{" + key + "}" in text, key
    assert sum(finding.unfavorable for finding in informe.FINDINGS) >= 4


def test_findings_never_call_the_oja_index_better_nor_claim_roi_or_a_scannable_qr():
    text = " ".join(finding.text for finding in informe.FINDINGS).lower()
    assert "mejor" not in text
    assert "roi" not in text.split() and "retorno" in text  # the only mention of return denies the claim
    assert "no se afirma que un qr recuperado se pueda escanear" in text


def test_every_finding_anchor_is_a_section_of_the_manifest_or_has_the_anchor_shape():
    for finding in informe.FINDINGS:
        assert informe.ANCHOR_SHAPE.match(finding.anchor), finding.anchor


def test_build_summary_has_the_fixture_findings_with_links_and_the_unfavorable_mark(tmp_path):
    page = build(tmp_path).read_text(encoding="utf-8")
    front = page[page.index('id="resumen"'):page.index('id="preguntas"')]
    assert front.count("data-fact=") >= 4
    assert '<li class="unfavorable">' in front and "Resultado desfavorable" in front
    assert 'href="#f9-s1-2"' in front and "Fase 9, §1.2" in front


def test_build_stops_on_a_number_typed_in_a_finding(tmp_path):
    typed = (informe.Finding("PCA", "Explica 53,2 % de la varianza.", "f9-s1"),)
    with pytest.raises(SystemExit) as stop:
        build(tmp_path, findings=typed)
    assert "53,2 %" in str(stop.value)


def test_build_stops_on_an_unknown_fact_key_in_a_finding(tmp_path):
    with pytest.raises(SystemExit) as stop:
        build(tmp_path, findings=(informe.Finding("X", "Valor {pca.no_such_key}.", "f9-s1"),))
    assert "pca.no_such_key" in str(stop.value)


def test_build_stops_on_an_internal_link_to_a_section_that_is_not_there(tmp_path):
    with pytest.raises(SystemExit) as stop:
        build(tmp_path, findings=(informe.Finding("X", "Texto.", "f9-s7"),))
    assert "f9-s7" in str(stop.value)


def test_build_with_a_drifted_pin_stops_and_names_the_phrase(tmp_path):
    drifted = ((9, "Cuerpo de A. Valor {som.r2_pc1}"),)
    with pytest.raises(SystemExit) as stop:
        build(tmp_path, pins=drifted)
    message = str(stop.value)
    assert "drifted" in message and "Cuerpo de A. Valor 0,961" in message


def test_build_with_a_matching_pin_passes(tmp_path):
    assert build(tmp_path, pins=((9, "Cuerpo de A."),)).is_file()


def test_build_stops_when_the_questions_were_not_checked_and_names_the_pdf(tmp_path):
    with pytest.raises(SystemExit) as stop:
        build(tmp_path, questions_checked=False)
    assert "Archivo SIATP 42026.pdf" in str(stop.value)
    assert not (tmp_path / "out" / "informe.html").exists()


@pytest.mark.parametrize("flag", ["QUESTIONS_CHECKED_AGAINST_PDF", "ANSWER_SECTIONS_CHECKED"])
def test_build_default_reads_both_manifest_flags_at_call_time(tmp_path, monkeypatch, flag):
    monkeypatch.setattr(manifest, flag, False)
    with pytest.raises(SystemExit) as stop:
        build(tmp_path)
    assert "Archivo SIATP 42026.pdf" in str(stop.value)


def test_build_default_passes_with_both_manifest_flags_true(tmp_path, monkeypatch):
    monkeypatch.setattr(manifest, "QUESTIONS_CHECKED_AGAINST_PDF", True)
    monkeypatch.setattr(manifest, "ANSWER_SECTIONS_CHECKED", True)
    assert build(tmp_path).is_file()


def test_oversized_svg_is_embedded_as_its_png_sibling(tmp_path, monkeypatch):
    svg = tmp_path / "big.svg"
    svg.write_bytes(SVG)
    png = tmp_path / "big.png"
    png.write_bytes(b"\x89PNG-bytes")
    monkeypatch.setattr(informe, "EMBED_SVG_MAX", 10)
    card = informe.figure_card(svg, "alt", "cap")
    blob = re.search(r'src="data:image/png;base64,([A-Za-z0-9+/=]+)"', card).group(1)
    assert base64.b64decode(blob) == b"\x89PNG-bytes"
    assert "image/svg+xml" not in card


def test_oversized_svg_without_png_sibling_stops(tmp_path, monkeypatch):
    svg = tmp_path / "big.svg"
    svg.write_bytes(SVG)
    monkeypatch.setattr(informe, "EMBED_SVG_MAX", 10)
    with pytest.raises(SystemExit) as stop:
        informe.figure_card(svg, "alt", "cap")
    assert "big.png" in str(stop.value)


def test_png_only_figure_uses_the_png_even_when_small(tmp_path):
    svg = tmp_path / "s.svg"
    svg.write_bytes(SVG)
    (tmp_path / "s.png").write_bytes(b"png")
    assert "data:image/png;base64," in informe.figure_card(svg, "a", "c", png_only=True)


def test_build_embeds_the_png_of_an_oversized_figure_and_still_scans_the_rest(tmp_path, monkeypatch):
    results, deliverables, fragments, questions, figures = make_fixture(tmp_path)
    (results / "fx" / "fig.png").write_bytes(b"\x89PNG")
    monkeypatch.setattr(informe, "EMBED_SVG_MAX", 10)
    out = fixture_build(results, deliverables, tmp_path / "o.html", questions, figures, fragments, tmp_path)
    assert "data:image/png;base64," in out.read_text(encoding="utf-8")


def two_exercise_fixture(tmp_path):
    results, deliverables, fragments, questions, figures = make_fixture(tmp_path)
    (deliverables / "10-y.md").write_text(FRAGMENT.replace("Fase 9", "Fase 10"), encoding="utf-8")
    fragments = fragments + ((10, "deliverables/10-y.md", 2, "Y"),)
    return results, deliverables, fragments, questions, figures


def test_build_groups_fragments_under_the_two_exercise_headings(tmp_path):
    results, deliverables, fragments, questions, figures = two_exercise_fixture(tmp_path)
    page = fixture_build(results, deliverables, tmp_path / "o.html", questions, figures, fragments,
                         tmp_path).read_text(encoding="utf-8")
    assert page.count('id="ej1"') == 1 and page.count('id="ej2"') == 1
    assert "Ejercicio 2: memoria asociativa (Hopfield)" in page
    assert page.index('id="ej1"') < page.index('id="f9"') < page.index('id="ej2"') < page.index('id="f10"')
    assert "Detalle técnico (Fase 10)" in page


def test_build_has_no_ej2_heading_without_fragments_of_exercise_2(tmp_path):
    assert 'id="ej2"' not in build(tmp_path).read_text(encoding="utf-8")


def test_question_table_has_a_group_row_per_exercise_and_the_question_id():
    questions = (
        manifest.Question("Q1.1", "uno", "1.1", 1, ("f1-s2",)),
        manifest.Question("Q1.2", "dos", "1.1", 1, ("f1-s3",)),
        manifest.Question("Q2.1", "tres", "2.1", 5, ("f5-s2",)),
    )
    out = informe.question_table(questions)
    assert out.count('<tr class="group">') == 2
    assert "Ejercicio 1: aprendizaje no supervisado" in out and "Ejercicio 2: memoria asociativa" in out
    assert "<td>Q2.1</td>" in out and "“tres” (sección 2.1)" in out


def test_real_question_table_quotes_all_25_questions_and_links_every_anchor():
    out = informe.question_table(manifest.QUESTIONS)
    assert out.count("<tr><td>Q") == 25
    for question in manifest.QUESTIONS:
        for anchor in question.anchors:
            assert f'href="#{anchor}"' in out
