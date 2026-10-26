"""Tests of the informe builder: anchors, figure cards, question table and the build-time assertions (DELIV-02).

Every input is built in tmp_path; nothing here reads analysis/results (not versioned).
"""

from __future__ import annotations

import base64
import hashlib
import re
from pathlib import Path

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
    kwargs.setdefault("glossary_path", glossary_file(Path(repo_dir)))
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


# ---------- glossary, jargon links and presenter script (06-09 task 2) ----------

DECISIONS_TEXT = """# Decisiones del TP4

Texto de introducción con D-01 y Pitfall 1 que no es una entrada.

## Decisiones del proyecto

### KD-1 — Núcleo en C

**Qué:** el núcleo está en C.

## Fase 2 — Kohonen

### F2 D-07 — Rango k = 2 a 8, con "comillas" y <b>

**Qué:** se barre `k` de 2 a 8, también grillas con más neuronas que creadores.

**Por qué:** ver todo el rango.

### F1 D-09 — Regla fija por grupo

**Qué:** una regla fija elige qué variable se saca.

### F4 D-04b — Abecedario borrador descartado

**Qué:** se descarta el borrador.

### F5 D-11 — Limitaciones demostradas

**Qué:** las limitaciones se demuestran con experimentos.

### F9 D-07 — Detalle del fixture

**Qué:** lo que dice el fixture.

## Pitfalls

### Pitfall 1 — Hopfield con Hebb sobre los QR

**Qué:** Hebb no funciona sobre los 5 QR.

### Pitfall 14 — Letras 5×5

**Qué:** conclusiones erróneas sobre capacidad.

## Requisitos

### HOP-04 — Preparación de los 5 QR

Responde la [sección 2 del fragmento 05](deliverables/05-hopfield-qr.md) (decisión relacionada: F5 D-01).
"""


def parsed_glossary():
    return informe.parse_glossary(DECISIONS_TEXT)


def test_parse_glossary_keys_by_the_documented_anchor_scheme():
    glossary = parsed_glossary()
    assert set(glossary) == {
        "g-f2-d-07", "g-f1-d-09", "g-f4-d-04b", "g-f5-d-11", "g-f9-d-07", "g-pitfall-1", "g-pitfall-14", "g-req-hop-04",
    }


def test_parse_glossary_entry_has_label_title_and_the_que_sentence():
    glossary = parsed_glossary()
    entry = glossary["g-f2-d-07"]
    assert entry.anchor == "g-f2-d-07" and entry.label == "F2 D-07"
    assert entry.title.startswith("Rango k = 2 a 8")
    assert entry.que == "se barre `k` de 2 a 8, también grillas con más neuronas que creadores."
    assert glossary["g-f4-d-04b"].label == "F4 D-04b"
    assert glossary["g-pitfall-1"].label == "Pitfall 1"
    assert glossary["g-req-hop-04"].label == "HOP-04"


def test_parse_glossary_requirement_without_que_line_uses_its_first_paragraph_without_links():
    glossary = parsed_glossary()
    que = glossary["g-req-hop-04"].que
    assert que.startswith("Responde la sección 2 del fragmento 05") and "](" not in que


def test_parse_glossary_skips_project_decisions_and_the_introduction():
    glossary = parsed_glossary()
    assert not any(anchor.startswith("g-kd") for anchor in glossary)


def test_parse_glossary_entry_is_immutable():
    glossary = parsed_glossary()
    with pytest.raises(Exception):
        glossary["g-f2-d-07"].title = "otro"


def test_link_jargon_links_a_decision_of_the_fragment_phase():
    glossary = parsed_glossary()
    out, used = informe.link_jargon("<p>según D-07</p>", 2, glossary)
    assert '<a class="jargon" href="#g-f2-d-07" title="F2 D-07 — ' in out
    assert out.startswith("<p>según ") and out.endswith(">D-07</a></p>")
    assert used == {"g-f2-d-07"}


def test_link_jargon_cross_phase_form_resolves_to_the_named_phase():
    glossary = parsed_glossary()
    out, used = informe.link_jargon("<p>salió del conjunto de la Fase 1 (D-09) pero sigue</p>", 3, glossary)
    assert 'href="#g-f1-d-09"' in out and "Fase 1 (<a" in out
    assert used == {"g-f1-d-09"}


def test_link_jargon_cross_phase_list_keeps_the_named_phase_for_every_id():
    glossary = parsed_glossary()
    out, used = informe.link_jargon("<p>la Fase 2 (D-07, D-07)</p>", 4, glossary)
    assert used == {"g-f2-d-07"} and out.count("g-f2-d-07") == 2


def test_link_jargon_lettered_id_without_entry_falls_back_to_the_parent():
    glossary = parsed_glossary()
    out, used = informe.link_jargon("<p>los sub-ítems D-11a</p>", 5, glossary)
    assert 'href="#g-f5-d-11"' in out and ">D-11a</a>" in out
    assert used == {"g-f5-d-11"}


def test_link_jargon_lettered_id_with_its_own_entry_keeps_the_letter():
    glossary = parsed_glossary()
    _out, used = informe.link_jargon("<p>D-04b</p>", 4, glossary)
    assert used == {"g-f4-d-04b"}


def test_link_jargon_pitfall_and_requirement_ids():
    glossary = parsed_glossary()
    out, used = informe.link_jargon("<p>Pitfall 1 y HOP-04, también Pitfall 14b</p>", 5, glossary)
    assert 'href="#g-pitfall-1"' in out and 'href="#g-req-hop-04"' in out
    assert ">Pitfall 14b</a>" in out
    assert used == {"g-pitfall-1", "g-req-hop-04", "g-pitfall-14"}


@pytest.mark.parametrize("fragment", [
    "<p><code>D-07</code></p>",
    "<pre><code>D-07 y Pitfall 1</code></pre>",
    '<p><a href="#x">D-07</a></p>',
    '<p><span title="según D-07" data-x="HOP-04">texto</span></p>',
    '<p><img alt="D-07" src="data:image/png;base64,AAAA"></p>',
])
def test_link_jargon_leaves_code_pre_links_and_attribute_values_unchanged(fragment):
    glossary = parsed_glossary()
    out, used = informe.link_jargon(fragment, 2, glossary)
    assert out == fragment and used == set()


def test_link_jargon_links_text_after_a_code_element_in_the_same_paragraph():
    glossary = parsed_glossary()
    out, used = informe.link_jargon("<p><code>D-07</code> y D-07</p>", 2, glossary)
    assert out.count('class="jargon"') == 1 and used == {"g-f2-d-07"}


def test_link_jargon_does_not_link_inside_a_jargon_link_again():
    glossary = parsed_glossary()
    once, _ = informe.link_jargon("<p>D-07</p>", 2, glossary)
    twice, used = informe.link_jargon(once, 2, glossary)
    assert twice == once and used == set()


def test_link_jargon_title_is_attribute_escaped():
    glossary = parsed_glossary()
    out, _ = informe.link_jargon("<p>D-07</p>", 2, glossary)
    title = re.search(r'title="([^"]*)"', out).group(1)
    assert "&quot;comillas&quot;" in title and "&lt;b&gt;" in title
    assert "<b>" not in out


def test_link_jargon_unknown_decision_id_names_the_fragment_and_the_id():
    glossary = parsed_glossary()
    with pytest.raises(SystemExit) as stop:
        informe.link_jargon("<p>según D-99</p>", 2, glossary)
    assert "fragment 2" in str(stop.value) and "D-99" in str(stop.value)


def test_link_jargon_unknown_pitfall_and_requirement_stop():
    glossary = parsed_glossary()
    for text, name in (("Pitfall 77", "Pitfall 77"), ("HOP-99", "HOP-99")):
        with pytest.raises(SystemExit) as stop:
            informe.link_jargon(f"<p>{text}</p>", 3, glossary)
        assert name in str(stop.value)


def test_link_jargon_ignores_ids_of_other_shapes():
    glossary = parsed_glossary()
    fragment = "<p>KD-1, SHA-256, UTF-8 y ABC-12 no son jerga del informe</p>"
    assert informe.link_jargon(fragment, 2, glossary) == (fragment, set())


def glossary_file(tmp_path):
    path = tmp_path / "DECISIONS.md"
    path.write_text(DECISIONS_TEXT, encoding="utf-8")
    return path


def test_build_links_the_jargon_of_the_fragments_and_lists_only_the_referenced_entries(tmp_path):
    results, deliverables, fragments, questions, figures = make_fixture(tmp_path)
    (deliverables / "09-x.md").write_text(
        FRAGMENT + "\n\nVer D-07, Pitfall 1 y HOP-04; la Fase 2 (D-07) también.\n", encoding="utf-8"
    )
    page = fixture_build(results, deliverables, tmp_path / "o.html", questions, figures, fragments, tmp_path,
                         glossary_path=glossary_file(tmp_path)).read_text(encoding="utf-8")
    for anchor in ("g-f9-d-07", "g-pitfall-1", "g-req-hop-04", "g-f2-d-07"):
        assert f'href="#{anchor}"' in page and f'id="{anchor}"' in page
    annex = page[page.index('id="glosario"'):]
    assert "Glosario de decisiones y referencias" in annex
    assert 'id="g-f5-d-11"' not in page and 'id="g-pitfall-14"' not in page
    order = [annex.index(f'id="{a}"') for a in ("g-f2-d-07", "g-f9-d-07", "g-pitfall-1", "g-req-hop-04")]
    assert order == sorted(order)


def test_build_stops_on_a_jargon_id_without_a_glossary_entry(tmp_path):
    results, deliverables, fragments, questions, figures = make_fixture(tmp_path)
    (deliverables / "09-x.md").write_text(FRAGMENT + "\n\nSegún D-99.\n", encoding="utf-8")
    with pytest.raises(SystemExit) as stop:
        fixture_build(results, deliverables, tmp_path / "o.html", questions, figures, fragments, tmp_path,
                      glossary_path=glossary_file(tmp_path))
    assert "fragment 9" in str(stop.value) and "D-99" in str(stop.value)


def test_build_never_writes_the_glossary_source(tmp_path):
    path = glossary_file(tmp_path)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    build(tmp_path, glossary_path=path)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_build_stops_when_the_glossary_source_is_missing(tmp_path):
    with pytest.raises(SystemExit) as stop:
        build(tmp_path, glossary_path=tmp_path / "no-such.md")
    assert "no-such.md" in str(stop.value)


NOTES = "# Guion\n\n## Slide 1\n\nDecir la conclusión.\n\n| a | b |\n|---|---|\n| 1 | 2 |\n"


def test_build_with_notes_appends_the_script_annex_without_clashing_ids(tmp_path):
    notes = tmp_path / "notes.md"
    notes.write_text(NOTES, encoding="utf-8")
    page = build(tmp_path, glossary_path=glossary_file(tmp_path), notes_path=notes).read_text(encoding="utf-8")
    assert page.count('id="guion"') == 1 and "Guion de la presentación" in page
    annex = page[page.index('id="guion"'):]
    assert "Decir la conclusión." in annex and "table-wrap" in annex
    assert not re.search(r"<h[1-6] id=", annex.split("</h2>", 1)[1])
    assert page.index('id="glosario"') < page.index('id="guion"') < page.index("<footer>")


def test_build_without_notes_has_no_script_annex(tmp_path):
    page = build(tmp_path, glossary_path=glossary_file(tmp_path)).read_text(encoding="utf-8")
    assert 'id="guion"' not in page and "Guion de la presentación" not in page


def test_build_stops_when_the_notes_file_is_missing(tmp_path):
    with pytest.raises(SystemExit) as stop:
        build(tmp_path, glossary_path=glossary_file(tmp_path), notes_path=tmp_path / "gone.md")
    assert "gone.md" in str(stop.value)


def test_build_stops_on_a_script_element_in_the_notes(tmp_path):
    notes = tmp_path / "notes.md"
    notes.write_text("<script>x</script>\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        build(tmp_path, glossary_path=glossary_file(tmp_path), notes_path=notes)


def test_cli_notes_flag_is_accepted(tmp_path, monkeypatch):
    seen = {}

    def fake_build(results, deliverables, out, **kwargs):
        seen.update(kwargs)
        return out

    monkeypatch.setattr(informe, "build", fake_build)
    informe.main(["--out", str(tmp_path / "o.html"), "--notes", str(tmp_path / "n.md")])
    assert seen["notes_path"] == tmp_path / "n.md"


def test_every_jargon_id_of_the_real_fragments_resolves_in_the_real_decisions_file():
    """Versioned inputs only (deliverables/ and DECISIONS.md): an ID without an entry would stop the real build."""
    glossary = informe.parse_glossary((informe.TP_DIR / "DECISIONS.md").read_text(encoding="utf-8"))
    linked = 0
    for number, relative, _exercise, _title in manifest.FRAGMENTS:
        text = (informe.TP_DIR / relative).read_text(encoding="utf-8")
        rendered = informe.render_fragment(text, number, ())
        out, used = informe.link_jargon(rendered, number, glossary)
        linked += out.count('class="jargon"')
        assert used <= set(glossary)
    assert linked >= 120
