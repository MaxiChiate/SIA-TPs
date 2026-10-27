"""Tests of the slide deck builder: outline, figures placed, builder and writer (DELIV-01, D-01 to D-11).

Every input is built in tmp_path; nothing here reads analysis/results (not versioned). Facts are a fixture dict
with one value per placeholder found in the outline.
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import replace

import pytest

import deliverables_manifest as manifest
import facts
import slides

TAG = "Regla fijada de antemano"
PNG = b"\x89PNG\r\n\x1a\n" + b"fixture"
SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"><rect width="4" height="4"/></svg>'
TYPED_NUMBER = re.compile(r"\d+(?:,\d+)?[  ]?%|\d+,\d+")
DEFAULT_VALUE = "99,9 %"  # the longest value shape a title placeholder takes in the real facts


def sentences(text: str) -> int:
    return len(re.findall(r"[.!?](?:\s|$)", text.strip()))


def by_id(slide_id: str):
    return next(slide for slide in slides.OUTLINE if slide.id == slide_id)


def fixture_facts() -> dict[str, str]:
    """One value for every {group.key} placeholder of the outline (a long handle list for top5 keys)."""
    values: dict[str, str] = {}
    for slide in slides.OUTLINE:
        for text in slides.slide_templates(slide):
            for key in facts.TOKEN.findall(text):
                values[key] = (
                    "@aaaaaaaaaaaaaaa, @bbbbbbbbbbbbbbb, @ccccccccccccccc, @ddddddddddddddd, @eeeeeeeeeeeeeee"
                    if key.endswith(".top5") else DEFAULT_VALUE
                )
    return values


def write_figures(root):
    """Slide SVG and PNG of every figure with a slide variant, at the paths the manifest gives."""
    for item in manifest.FIGURES:
        if item.slide:
            svg = root / manifest.slide_path(item)
            svg.parent.mkdir(parents=True, exist_ok=True)
            svg.write_text(SVG, encoding="utf-8")
            svg.with_suffix(".png").write_bytes(PNG)
    return root


@pytest.fixture()
def deck(tmp_path):
    results = write_figures(tmp_path / "results")
    return slides.build_deck(fixture_facts(), results), results


# ---------- outline (D-01, D-02, D-04, D-05, D-07) ----------

def test_outline_has_27_unique_slides_in_method_order():
    ids = [slide.id for slide in slides.OUTLINE]
    assert len(ids) == 27 and len(set(ids)) == 27
    assert ids[:2] == ["portada", "metodo"]
    counts = {exercise: sum(1 for s in slides.OUTLINE if s.exercise == exercise) for exercise in (0, 1, 2)}
    assert counts == {0: 2, 1: 16, 2: 9}
    assert [s.exercise for s in slides.OUTLINE] == sorted(s.exercise for s in slides.OUTLINE)
    assert [s.id for s in slides.OUTLINE if s.exercise == 1][-1] == "ej1-conclusiones"
    assert ids[-1] == "ej2-conclusiones"


def test_outline_has_no_agenda_and_no_general_closing():
    for slide in slides.OUTLINE:
        text = f"{slide.id} {slide.title}".lower()
        assert "agenda" not in text and "gracias" not in text and "cierre" not in text


def test_unfavorable_and_campaign_slides_exist_with_their_own_ids():
    ids = {slide.id for slide in slides.OUTLINE}
    assert {"som-not-robust", "som-one-region", "qr-hebb-falla", "qr-lookup"} <= ids
    assert {"camp-futbol", "camp-table", "camp-followers", "camp-maintenance"} <= ids


def test_unfavorable_titles_say_the_result_plainly():
    assert "no es robusta" in by_id("som-not-robust").title
    assert "una sola región" in by_id("som-one-region").title
    assert "Hebb" in by_id("qr-hebb-falla").title and "{qr.hebb_exact_noise0}" in by_id("qr-hebb-falla").title
    assert "Hamming" in by_id("qr-lookup").title and "pseudo-inversa" in by_id("qr-lookup").title


def test_every_figure_is_a_slide_figure_and_questions_cover_the_enunciado():
    for slide in slides.OUTLINE:
        if slide.figure is not None:
            assert manifest.figure(slide.figure).slide is True
    asked = {question for slide in slides.OUTLINE for question in slide.question_ids}
    assert asked == {question.id for question in manifest.QUESTIONS}


def test_figures_placed_and_unplaced_are_exactly_the_slide_figures():
    placed = [slide.figure for slide in slides.OUTLINE if slide.figure is not None]
    assert all(isinstance(key, str) for key in placed)
    assert len(placed) == 18 and len(set(placed)) == 18
    unplaced = set(slides.UNPLACED_SLIDE_FIGURES)
    slide_true = {item.key for item in manifest.FIGURES if item.slide}
    assert not (set(placed) & unplaced)
    assert set(placed) | unplaced == slide_true and len(unplaced) == 5
    assert all(str(reason).strip() for reason in slides.UNPLACED_SLIDE_FIGURES.values())


def test_qr_slide_shows_the_qr_matrices_and_letras_ruido_the_noise_figure():
    assert manifest.figure(by_id("qr-correlados").figure).path == "hopfield/qr/figures/qr.svg"
    assert manifest.figure(by_id("letras-ruido").figure).path == "hopfield/figures/recall_noise.svg"


def test_qr_encoding_is_stated_as_this_works_choice_in_the_notes():
    notes = by_id("qr-correlados").notes
    assert "37×37" in notes and "±1" in notes and "oscuro = +1" in notes
    assert "como parte del enunciado" in notes or "no como parte" in notes
    assert "{qr.n_pixels}" in notes


def test_pre_registration_tag_is_on_five_slides_at_least_and_never_on_the_method_slide():
    assert sum(1 for slide in slides.OUTLINE if slide.tag == TAG) >= 5
    assert by_id("metodo").tag is None
    assert {slide.tag for slide in slides.OUTLINE} <= {None, TAG}


def test_slide_figure_is_none_or_a_single_string():
    for slide in slides.OUTLINE:
        assert slide.figure is None or isinstance(slide.figure, str)


def test_text_only_slides_name_no_figure():
    for slide_id in ("portada", "metodo", "som-not-robust", "oja-max", "camp-table", "camp-followers",
                     "camp-maintenance", "ej1-conclusiones", "ej2-conclusiones"):
        assert by_id(slide_id).figure is None


def test_campaign_table_rows_read_the_criterion_top5_and_cost_facts():
    table = by_id("camp-table").table
    assert table is not None
    text = " ".join(" ".join(row) for row in table[1])
    for campaign in ("perros", "maquillaje", "arte"):
        for part in ("criterion", "top5", "cost_per_thousand_ar"):
            assert f"{{camp.{campaign}.{part}}}" in text
    assert "{camp.futbol." not in text


def test_every_outline_number_is_a_fact_placeholder():
    for slide in slides.OUTLINE:
        for text in slides.slide_templates(slide):
            bare = facts.TOKEN.sub("", text)
            assert not TYPED_NUMBER.search(bare), (slide.id, text)


def test_no_title_body_or_note_makes_a_forbidden_claim():
    forbidden = re.compile(r"\bROI\b|retorno de la inversión|\bmejor\b|escanea\b|decodifica\b", re.I)
    for slide in slides.OUTLINE:
        for text in slides.slide_templates(slide):
            assert not forbidden.search(text), (slide.id, text)


# ---------- build_deck ----------

def test_build_deck_fills_every_template_and_every_note_has_two_to_four_sentences(deck):
    built, _ = deck
    assert len(built) == 27
    for slide in built:
        for text in [slide["title"], *slide["body"], slide["notes"]]:
            assert "{" not in text and "}" not in text, slide["id"]
        assert 2 <= sentences(slide["notes"]) <= 4, (slide["id"], slide["notes"])
        if slide["table"] is not None:
            assert all("{" not in cell for row in slide["table"]["rows"] for cell in row)


def test_build_deck_resolves_each_figure_to_its_slide_variant(deck):
    built, _ = deck
    with_figure = [slide for slide in built if slide["figure"] is not None]
    assert len(with_figure) == 18
    for slide in with_figure:
        expected = manifest.slide_path(manifest.figure(slide["figure"]))
        assert slide["figure_path"] == expected
        assert slide["png"] == f"{slide['figure']}.png"
    assert all(slide["figure_path"] is None for slide in built if slide["figure"] is None)


def test_build_deck_stops_on_an_unknown_fact_key(tmp_path, monkeypatch):
    results = write_figures(tmp_path / "results")
    values = fixture_facts()
    broken = replace(slides.OUTLINE[1], title="Valor {nope.key}")
    monkeypatch.setattr(slides, "OUTLINE", (slides.OUTLINE[0], broken, *slides.OUTLINE[2:]))
    with pytest.raises(SystemExit) as stop:
        slides.build_deck(values, results)
    assert "nope.key" in str(stop.value)


def test_build_deck_stops_on_a_missing_slide_figure_and_names_the_make_target(tmp_path):
    results = write_figures(tmp_path / "results")
    item = manifest.figure(by_id("som-map").figure)
    (results / manifest.slide_path(item)).unlink()
    with pytest.raises(SystemExit) as stop:
        slides.build_deck(fixture_facts(), results)
    assert item.make_target in str(stop.value) and manifest.slide_path(item) in str(stop.value)


def test_build_deck_stops_when_the_outline_has_more_than_28_slides(tmp_path, monkeypatch):
    results = write_figures(tmp_path / "results")
    extra = replace(slides.OUTLINE[-1], id="extra-slide")
    monkeypatch.setattr(slides, "OUTLINE", (*slides.OUTLINE, extra, replace(extra, id="extra-slide-2")))
    with pytest.raises(SystemExit) as stop:
        slides.build_deck(fixture_facts(), results)
    assert "28" in str(stop.value)


def test_a_long_handle_list_stays_in_a_table_cell_and_the_notes(deck):
    built, _ = deck
    table = next(slide for slide in built if slide["id"] == "camp-table")["table"]
    assert len(table["header"]) <= 4 and len(table["rows"]) == 3
    assert any("@aaaaaaaaaaaaaaa" in cell for row in table["rows"] for cell in row)


# ---------- write_deck ----------

def write(deck_and_results, out, **kwargs):
    built, results = deck_and_results
    slides.write_deck(built, out, slides.SLIDE_FORMAT, results, **kwargs)
    return out


def test_slide_format_copies_the_probe(tmp_path):
    fmt = slides.SLIDE_FORMAT
    assert fmt["image_embed"] == "relative-file" and fmt["notes_supported"] is True
    assert fmt["canvas"] == (1920, 1080) and "section" in fmt["content_unit"] and "aside" in fmt["notes_field"]


def test_write_deck_writes_the_probed_tree(deck, tmp_path):
    out = write(deck, tmp_path / "out")
    built, _ = deck
    manifest_file = json.loads((out / "deck.json").read_text(encoding="utf-8"))
    assert [slide["id"] for slide in manifest_file["slides"]] == [slide["id"] for slide in built]
    assert (out / "notes.md").is_file()
    index = json.loads((out / "project" / "deck.json").read_text(encoding="utf-8"))
    ids = [slide["id"] for slide in built]
    assert index["v"] == 4 and index["lists"] == "css" and index["order"] == ids
    assert index["cover"] == "portada" and index["faces"] == {} and index["designSystems"] == []
    assert set(index["createdOnFiles"]) == {"v", "at"} and index["designSystems"] == []
    assert {section["start"] for section in index["sections"].values()} <= set(ids) and len(index["sections"]) == 3
    for slide_id in ids:
        page = (out / "project" / "slides" / f"{slide_id}.html").read_text(encoding="utf-8")
        assert page.startswith(f'<section id="{slide_id}" style="') and page.rstrip().endswith("</section>")
        assert page.count("<section") == 1 and page.count("<aside>") == 1
        assert page.rstrip().endswith("</aside></section>")
    assert len(list((out / "project" / "slides").glob("*.html"))) == 27


def test_write_deck_copies_the_png_of_each_figure_and_lists_them(deck, tmp_path):
    out = write(deck, tmp_path / "out")
    built, _ = deck
    pngs = sorted(slide["png"] for slide in built if slide["png"])
    assert sorted(path.name for path in (out / "assets").glob("*.png")) == pngs and len(pngs) == 18
    listed = json.loads((out / "deck.json").read_text(encoding="utf-8"))["assets"]
    assert sorted(item["png"] for item in listed) == pngs
    assert all(item["file"] == f"assets/{item['png']}" for item in listed)


def test_write_deck_is_identical_byte_for_byte_on_a_second_run(deck, tmp_path):
    first, second = write(deck, tmp_path / "a"), write(deck, tmp_path / "b")
    names = sorted(str(path.relative_to(first)) for path in first.rglob("*") if path.is_file())
    assert names == sorted(str(path.relative_to(second)) for path in second.rglob("*") if path.is_file())
    for name in names:
        assert (first / name).read_bytes() == (second / name).read_bytes(), name


def test_write_deck_over_an_old_output_leaves_no_stale_slide_file(deck, tmp_path):
    out = tmp_path / "out"
    (out / "project" / "slides").mkdir(parents=True)
    (out / "project" / "slides" / "old.html").write_text("<section id=\"old\"></section>", encoding="utf-8")
    write(deck, out)
    assert not (out / "project" / "slides" / "old.html").exists()


def test_slide_files_define_no_colour_and_no_font_below_24px(deck, tmp_path):
    out = write(deck, tmp_path / "out")
    for page_file in (out / "project" / "slides").glob("*.html"):
        page = page_file.read_text(encoding="utf-8")
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b|rgb\(|rgba\(|hsl\(", page), page_file.name
        for size in re.findall(r"font-size:\s*(\d+)px", page):
            assert int(size) >= 24, page_file.name
        for forbidden in ("<style", "class=", "z-index", "margin", "var(", "font-family"):
            assert forbidden not in page, (page_file.name, forbidden)


def test_slide_files_use_only_the_elements_the_type_allows(deck, tmp_path):
    out = write(deck, tmp_path / "out")
    allowed = {"section", "h1", "h2", "h3", "p", "ul", "ol", "li", "div", "img", "table", "tr", "th", "td", "aside"}
    for page_file in (out / "project" / "slides").glob("*.html"):
        page = page_file.read_text(encoding="utf-8")
        assert set(re.findall(r"<([a-z0-9]+)", page)) <= allowed, page_file.name
        assert len(re.findall(r"<[a-z]", page)) <= 200


def test_text_values_are_html_escaped(deck, tmp_path):
    built, results = deck
    hostile = [dict(slide) for slide in built]
    hostile[2]["title"] = "Prueba <b>negrita</b> & más"
    hostile[2]["notes"] = "Nota con <script>alert(1)</script>. Segunda frase."
    out = tmp_path / "out"
    slides.write_deck(hostile, out, slides.SLIDE_FORMAT, results)
    page = (out / "project" / "slides" / f"{hostile[2]['id']}.html").read_text(encoding="utf-8")
    assert "<b>" not in page and "<script>" not in page
    assert "&lt;b&gt;negrita&lt;/b&gt; &amp; más" in page and "&lt;script&gt;" in page


def test_write_deck_refuses_a_home_path_or_an_email(deck, tmp_path):
    built, results = deck
    for bad in ("/Users/alguien/Documents", "alguien@example.com"):
        tainted = [dict(slide) for slide in built]
        tainted[0]["notes"] = f"Nota con {bad}. Otra frase."
        with pytest.raises(SystemExit):
            slides.write_deck(tainted, tmp_path / "out", slides.SLIDE_FORMAT, results)


def test_a_handle_is_not_taken_for_an_email(deck, tmp_path):
    built, results = deck
    fine = [dict(slide) for slide in built]
    fine[0]["notes"] = "Creador @mundoanimal.ar y (@otro.ar). Otra frase."
    slides.write_deck(fine, tmp_path / "out", slides.SLIDE_FORMAT, results)


def test_notes_md_is_the_presenter_script(deck, tmp_path):
    out = write(deck, tmp_path / "out")
    built, _ = deck
    text = (out / "notes.md").read_text(encoding="utf-8")
    assert text.startswith("# Guion de la presentación")
    headings = re.findall(r"^## (\d+)\. (.+)$", text, flags=re.M)
    assert [int(number) for number, _ in headings] == list(range(1, 28))
    assert [title for _, title in headings] == [slide["title"] for slide in built]
    for slide in built:
        assert slide["notes"] in text


def test_notes_go_into_the_aside_when_the_format_supports_them(deck, tmp_path):
    built, results = deck
    on = tmp_path / "on"
    slides.write_deck(built, on, slides.SLIDE_FORMAT, results)
    off = tmp_path / "off"
    slides.write_deck(built, off, {**slides.SLIDE_FORMAT, "notes_supported": False}, results)
    first = built[0]["id"]
    assert "<aside>" in (on / "project" / "slides" / f"{first}.html").read_text(encoding="utf-8")
    assert "<aside" not in (off / "project" / "slides" / f"{first}.html").read_text(encoding="utf-8")
    assert (off / "notes.md").is_file()


def test_aside_notes_respect_the_4000_character_cap(deck, tmp_path):
    built, results = deck
    long_notes = [dict(slide) for slide in built]
    long_notes[3]["notes"] = "Frase de relleno. " * 300
    with pytest.raises(SystemExit) as stop:
        slides.write_deck(long_notes, tmp_path / "out", slides.SLIDE_FORMAT, results)
    assert "4000" in str(stop.value)


# ---------- images ----------

def test_relative_mode_points_each_img_at_the_copied_png(deck, tmp_path):
    out = write(deck, tmp_path / "out")
    page = (out / "project" / "slides" / "som-map.html").read_text(encoding="utf-8")
    assert 'src="../../assets/som_map.png"' in page and "object-fit:contain" in page and "data:" not in page


def test_asset_map_writes_the_blob_urls_verbatim(deck, tmp_path):
    built, _ = deck
    asset_map = {slide["png"]: f"/_blob/id-{n}" for n, slide in enumerate(built) if slide["png"]}
    out = write(deck, tmp_path / "out", asset_map=asset_map)
    page = (out / "project" / "slides" / "som-map.html").read_text(encoding="utf-8")
    assert f'src="{asset_map["som_map.png"]}"' in page and "../../assets" not in page


def test_asset_map_missing_a_figure_or_with_a_foreign_url_stops(deck, tmp_path):
    built, results = deck
    asset_map = {slide["png"]: "/_blob/x" for slide in built if slide["png"]}
    del asset_map["som_map.png"]
    with pytest.raises(SystemExit) as stop:
        slides.write_deck(built, tmp_path / "a", slides.SLIDE_FORMAT, results, asset_map=asset_map)
    assert "som_map.png" in str(stop.value)
    asset_map["som_map.png"] = "https://example.org/x.png"
    with pytest.raises(SystemExit):
        slides.write_deck(built, tmp_path / "b", slides.SLIDE_FORMAT, results, asset_map=asset_map)


def test_data_uri_mode_embeds_the_png(deck, tmp_path):
    built, results = deck
    out = tmp_path / "out"
    slides.write_deck(built, out, {**slides.SLIDE_FORMAT, "image_embed": "data-uri"}, results)
    page = (out / "project" / "slides" / "som-map.html").read_text(encoding="utf-8")
    assert f"data:image/png;base64,{base64.b64encode(PNG).decode()}" in page


def test_every_img_is_a_matplotlib_slide_variant_never_a_hand_painted_chart(deck, tmp_path):
    out = write(deck, tmp_path / "out")
    for page_file in (out / "project" / "slides").glob("*.html"):
        page = page_file.read_text(encoding="utf-8")
        assert "<svg" not in page and "<canvas" not in page and "<x-" not in page


# ---------- main ----------

def test_main_prints_the_summary_line_and_writes_the_files(tmp_path, monkeypatch, capsys):
    results = write_figures(tmp_path / "results")
    monkeypatch.setattr(slides.facts, "load_facts", lambda *_args, **_kwargs: fixture_facts())
    out = tmp_path / "out"
    assert slides.main(["--results", str(results), "--out", str(out)]) == 0
    assert f"slides -> {out} (27 slides)" in capsys.readouterr().out
    assert (out / "deck.json").is_file() and (out / "notes.md").is_file()


def test_main_reads_an_asset_map_file(tmp_path, monkeypatch):
    results = write_figures(tmp_path / "results")
    monkeypatch.setattr(slides.facts, "load_facts", lambda *_args, **_kwargs: fixture_facts())
    asset_map = {f"{slide.figure}.png": f"/_blob/{slide.figure}" for slide in slides.OUTLINE if slide.figure}
    map_file = tmp_path / "asset_map.json"
    map_file.write_text(json.dumps(asset_map), encoding="utf-8")
    out = tmp_path / "out"
    assert slides.main(["--results", str(results), "--out", str(out), "--asset-map", str(map_file)]) == 0
    assert 'src="/_blob/som_map"' in (out / "project" / "slides" / "som-map.html").read_text(encoding="utf-8")


# ---------- fit and reproducibility of the real outline (Task 2) ----------

def test_max_title_chars_comes_from_the_type_scale_of_the_probe():
    per_line = int(slides.TEXT_W / (0.6 * slides.TITLE_PX))
    assert slides.MAX_TITLE_CHARS == int(2 * per_line * 0.9) and slides.MAX_TITLE_CHARS < 2 * per_line
    assert slides.TITLE_PX >= 24 and slides.BODY_PX >= 24 and slides.TABLE_PX >= 24 and slides.META_PX >= 24


def test_every_filled_title_fits_in_two_lines_under_max_title_chars(deck):
    built, _ = deck
    per_line = int(slides.TEXT_W / (0.6 * slides.TITLE_PX))
    for slide in built:
        assert len(slide["title"]) <= slides.MAX_TITLE_CHARS, (slide["id"], len(slide["title"]))
        assert slides._wrap_lines(slide["title"], per_line) <= 2, slide["id"]


def test_build_deck_stops_on_a_title_over_max_title_chars(tmp_path, monkeypatch):
    results = write_figures(tmp_path / "results")
    long_title = replace(slides.OUTLINE[2], title="palabra " * 20)
    monkeypatch.setattr(slides, "OUTLINE", (*slides.OUTLINE[:2], long_title, *slides.OUTLINE[3:]))
    with pytest.raises(SystemExit) as stop:
        slides.build_deck(fixture_facts(), results)
    assert long_title.id in str(stop.value) and "título" in str(stop.value)


def test_tables_have_at_most_4_columns_and_5_rows_and_bodies_at_most_3_lines():
    for slide in slides.OUTLINE:
        assert len(slide.body) <= 3, slide.id
        if slide.table is not None:
            header, rows = slide.table
            assert len(header) <= 4 and 1 <= len(rows) <= 5, slide.id
            assert all(len(row) == len(header) for row in rows), slide.id


def test_build_deck_stops_on_a_table_or_body_over_the_limits(tmp_path, monkeypatch):
    results = write_figures(tmp_path / "results")
    wide = replace(slides.OUTLINE[10], table=(("a", "b", "c", "d", "e"), (("1", "2", "3", "4", "5"),)))
    monkeypatch.setattr(slides, "OUTLINE", (*slides.OUTLINE[:10], wide, *slides.OUTLINE[11:]))
    with pytest.raises(SystemExit) as stop:
        slides.build_deck(fixture_facts(), results)
    assert wide.id in str(stop.value) and "columnas" in str(stop.value)
    chatty = replace(slides.OUTLINE[2], body=("a", "b", "c", "d"))
    monkeypatch.setattr(slides, "OUTLINE", (*slides.OUTLINE[:2], chatty, *slides.OUTLINE[3:]))
    with pytest.raises(SystemExit) as stop:
        slides.build_deck(fixture_facts(), results)
    assert chatty.id in str(stop.value) and "líneas" in str(stop.value)


def test_every_figure_the_slide_files_reference_exists_in_assets(deck, tmp_path):
    out = write(deck, tmp_path / "out")
    for page_file in (out / "project" / "slides").glob("*.html"):
        for src in re.findall(r'<img src="([^"]+)"', page_file.read_text(encoding="utf-8")):
            assert (page_file.parent / src).resolve().is_file(), (page_file.name, src)
            assert (page_file.parent / src).read_bytes() == PNG


def test_every_figure_fits_the_canvas_below_the_title(deck, tmp_path):
    out = write(deck, tmp_path / "out")
    for page_file in (out / "project" / "slides").glob("*.html"):
        for height in re.findall(r"height:(\d+)px;object-fit", page_file.read_text(encoding="utf-8")):
            assert slides.MIN_FIGURE_H <= int(height) <= slides.TEXT_H - slides.TITLE_LINE, page_file.name


def test_two_builds_through_main_are_identical(tmp_path, monkeypatch):
    results = write_figures(tmp_path / "results")
    monkeypatch.setattr(slides.facts, "load_facts", lambda *_args, **_kwargs: fixture_facts())
    for name in ("a", "b"):
        assert slides.main(["--results", str(results), "--out", str(tmp_path / name)]) == 0
    first, second = tmp_path / "a", tmp_path / "b"
    files = sorted(path.relative_to(first) for path in first.rglob("*") if path.is_file())
    assert files == sorted(path.relative_to(second) for path in second.rglob("*") if path.is_file())
    assert all((first / name).read_bytes() == (second / name).read_bytes() for name in files)
