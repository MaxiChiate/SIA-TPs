#!/usr/bin/env python3
"""The informe of TP4 as one self-contained HTML page (DELIV-02, D-09 to D-12).

    .venv/bin/python analysis/informe.py [--results DIR] [--deliverables DIR] [--out FILE] [--notes FILE]

The page is hybrid (D-12): a generated front section (summary of findings, table that maps each question of the
enunciado to where it is answered, method) followed by the Markdown fragments of deliverables/ converted with
Python-Markdown as "Detalle técnico", grouped under "Ejercicio 1" (fragments 1-3) and "Ejercicio 2" (fragments
4-5). Every D-NN, Pitfall N and requirement ID of the fragments becomes a link (class jargon) to an annex generated
from DECISIONS.md (D-13; an ID without an entry stops the build); --notes appends the presenter script as an annex
(the D-06 fallback when the Slides type has no notes). Numbers of the generated text come from the results JSON through facts.py and are wrapped as
<span class="fact" data-fact="KEY">; none is typed here (D-11), and build stops if one is (typed_numbers). Before
writing, build runs facts.check_fragment_numbers and stops with the failing pins if a number typed in a fragment
drifted from the results (D-12). Fragment headings
get number-based anchors (heading "### 6.4 ..." of fragment 2 is id="f2-s6-4") and the question table links to
them. Figures are embedded as <img src="data:image/svg+xml;base64,..."> inside a card whose background is
plots_style.SURFACE in both themes (D-09 static, D-10 light panel): matplotlib SVGs carry a global <style> and
non-unique ids, so they cannot be inlined, and inside an <img> they cannot run script. An SVG larger than
EMBED_SVG_MAX is embedded as the PNG that plots_style.save_figure writes next to it.

The page follows the Artifact page contract: own <title> and <style> first, no document skeleton tags, colour
tokens on bare :root redefined for dark, side gutters with safe-area insets, tables in their own scroll box.
The fragments are only read, never written (sha256 guard of Phase 2); every change happens at render time.
The build fails loudly (SystemExit with the make command to run) when a result file is missing, the question
texts or their answering sections were not checked by a human (deliverables_manifest flags), a number drifted, a
question anchor or an internal link target is absent, a fact placeholder is unresolved, the page is over MAX_BYTES,
or it leaks a home path or an email address. Output: analysis/results/informe/informe.html (not versioned).
"""

from __future__ import annotations

import argparse
import base64
import html
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import markdown

TP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TP_DIR / "scripts"))
sys.path.insert(0, str(TP_DIR / "analysis"))

import deliverables_manifest  # noqa: E402
import facts  # noqa: E402
import plots_style  # noqa: E402

DEFAULT_OUT = TP_DIR / "analysis" / "results" / "informe" / "informe.html"
MAX_BYTES = 12_000_000  # below the 16 MB Artifact limit, data: images included
EMBED_SVG_MAX = 1_500_000  # a larger SVG goes into the page as its PNG sibling

TOKEN_SHAPE = re.compile(r"\{[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+\}")
HOME_PATH = re.compile(r"/Users/|/home/|[A-Za-z]:\\Users\\")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}")
NUMBERED = re.compile(r"(\d+(?:\.\d+)*)\.?(?:\s|$)")
ANCHOR_SHAPE = re.compile(r"^f(\d+)-s(\d+(?:-\d+)*)$")
FACT_SPAN = re.compile(r'<span class="fact"[^>]*>.*?</span>', re.S)
TYPED_NUMBER = re.compile(r"\d+(?:,\d+)?[ \u00a0]?%|\d+,\d+")
DATA_URI = re.compile(r"data:image/(?:svg\+xml|png);base64,[A-Za-z0-9+/=]+")
HREF_TARGET = re.compile(r'href="#([^"]+)"')
ID_VALUE = re.compile(r'\bid="([^"]+)"')

# Exercise number -> (page id, heading) of the groups that hold the fragments as "Detalle técnico".
EXERCISES = (
    (1, "ej1", "Ejercicio 1: aprendizaje no supervisado"),
    (2, "ej2", "Ejercicio 2: memoria asociativa (Hopfield)"),
)

STYLE = """
:root {
  --bg: #ffffff; --fg: #1f2328; --muted: #59636e; --rule: #d1d9e0; --accent: #0b5cad; --link: #0b5cad;
  --code-bg: #f3f4f6; --th-bg: #eef1f4; --fact-bg: #e8f1fb;
  --figure-surface: __SURFACE__; --figure-border: #d0d0cc;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #14161a; --fg: #e6e8eb; --muted: #9aa4af; --rule: #3a4048; --accent: #6cb0f5; --link: #6cb0f5;
    --code-bg: #1f232a; --th-bg: #1f242b; --fact-bg: #1c2a3a;
    --figure-surface: __SURFACE__; --figure-border: #d0d0cc;
    color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --bg: #14161a; --fg: #e6e8eb; --muted: #9aa4af; --rule: #3a4048; --accent: #6cb0f5; --link: #6cb0f5;
  --code-bg: #1f232a; --th-bg: #1f242b; --fact-bg: #1c2a3a;
  --figure-surface: __SURFACE__; --figure-border: #d0d0cc;
  color-scheme: dark;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg);
  font: 16px/1.6 system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
.informe { max-width: 960px; margin: 0 auto; padding-block: 24px 48px; overflow-wrap: break-word;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
h1 { font-size: 1.9rem; line-height: 1.25; margin: 0 0 .5rem; }
h2 { font-size: 1.45rem; margin: 2.2rem 0 .6rem; padding-bottom: .25rem; border-bottom: 1px solid var(--rule); }
h3 { font-size: 1.2rem; margin: 1.8rem 0 .5rem; }
h4 { font-size: 1.08rem; margin: 1.5rem 0 .4rem; }
h5 { font-size: 1rem; margin: 1.2rem 0 .3rem; }
a { color: var(--link); }
p, li { max-width: 78ch; }
.lead, footer { color: var(--muted); }
code { background: var(--code-bg); padding: .1em .3em; border-radius: 4px; font-size: .9em; overflow-wrap: anywhere; }
pre { background: var(--code-bg); padding: 12px; border-radius: 6px; overflow-x: auto; max-width: 100%; }
pre code { background: none; padding: 0; overflow-wrap: normal; }
.table-wrap { overflow-x: auto; max-width: 100%; margin: 1rem 0; }
table { border-collapse: collapse; font-size: .92rem; }
th, td { border: 1px solid var(--rule); padding: 6px 10px; text-align: left; vertical-align: top; }
th { background: var(--th-bg); }
.fact { background: var(--fact-bg); border-radius: 3px; padding: 0 .2em; }
.fig { margin: 1.2rem 0; padding: 10px; background: var(--figure-surface); border: 1px solid var(--figure-border);
  border-radius: 8px; color: #2b2b28; }
.fig img { display: block; max-width: 100%; height: auto; margin: 0 auto; }
.fig figcaption { margin-top: 8px; font-size: .88rem; }
li.unfavorable { border-left: 3px solid var(--accent); padding-left: 10px; margin-left: -13px; }
tr.group th { background: var(--code-bg); font-size: .95rem; }
a.jargon { text-decoration: underline dotted; text-underline-offset: 2px; }
dl.glossary dt { font-weight: 600; margin-top: .9rem; }
dl.glossary dd { margin: .2rem 0 0 0; max-width: 78ch; }
section.guion { margin-top: 1rem; }
footer { margin-top: 3rem; padding-top: .8rem; border-top: 1px solid var(--rule); font-size: .85rem; }
""".replace("__SURFACE__", plots_style.SURFACE)


# ---------- fragments ----------

def make_slugify(n: int):
    """Toc slugify for fragment n: "6.4 ..." gives f<n>-s6-4, the "Fase <n> ..." top heading gives f<n>, any
    other heading f<n>- plus an ASCII slug; always inside [A-Za-z0-9._~-]."""
    top = re.compile(rf"^Fase\s+{n}\b")

    def slugify(value: str, separator: str = "-") -> str:
        text = value.strip()
        numbered = NUMBERED.match(text)
        if numbered:
            return f"f{n}-s" + numbered.group(1).replace(".", "-")
        if top.match(text):
            return f"f{n}"
        plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        slug = re.sub(r"[^A-Za-z0-9._~-]+", "-", plain).strip("-").lower()
        return f"f{n}-{slug}" if slug else f"f{n}-section"

    return slugify


def figure_card(path: Path, alt: str, caption: str, *, png_only: bool = False) -> str:
    """A figure element whose img carries the SVG bytes as a data URI (never inline svg).

    An SVG larger than EMBED_SVG_MAX (or any figure with png_only) is embedded as the PNG that save_figure wrote next
    to it; with no PNG sibling the build stops.
    """
    source = Path(path)
    if png_only or source.stat().st_size > EMBED_SVG_MAX:
        sibling = source.with_suffix(".png")
        if not sibling.is_file():
            raise SystemExit(f"{source} is too large to embed as SVG and {sibling} is missing; run its make target")
        mime, payload = "image/png", sibling.read_bytes()
    else:
        mime, payload = "image/svg+xml", source.read_bytes()
    data = base64.b64encode(payload).decode("ascii")
    return (
        '<figure class="fig">'
        f'<img src="data:{mime};base64,{data}" alt="{html.escape(alt)}">'
        f"<figcaption>{html.escape(caption)}</figcaption>"
        "</figure>"
    )


def _insert_cards(page: str, figure, card: str) -> str:
    """Put the card at the end of the section whose heading id is figure.anchor."""
    heading = re.search(rf'<h([1-6]) id="{re.escape(figure.anchor)}"[^>]*>', page)
    if heading is None:
        raise SystemExit(f"figure {figure.key}: anchor {figure.anchor} not found in fragment {figure.fragment}")
    following = re.search(r"<h[1-6][ >]", page[heading.end():])
    position = heading.end() + following.start() if following else len(page)
    return page[:position] + card + "\n" + page[position:]


def render_fragment(text: str, n: int, figures: Iterable, results_dir: Path = facts.RESULTS_DIR) -> str:
    """Markdown fragment n to HTML: number-based anchors, tables in a scroll box, rule markers (HTML comments)
    dropped, top heading prefixed "Detalle técnico (Fase n)", figure cards at the end of their section."""
    md = markdown.Markdown(
        extensions=["tables", "fenced_code", "toc"],
        extension_configs={"toc": {"slugify": make_slugify(n), "baselevel": 3}},
    )
    page = md.convert(text)
    page = re.sub(r"<!--.*?-->", "", page, flags=re.S)
    page = re.sub(r"<table>.*?</table>", lambda m: f'<div class="table-wrap">{m.group(0)}</div>', page, flags=re.S)
    page = re.sub(
        rf'(<h[1-6] id="f{n}">)(?:Fase {n}\s*[—–-]\s*)?',
        rf"\g<1>Detalle técnico (Fase {n}): ",
        page,
        count=1,
    )
    for figure in figures:
        if figure.fragment != n:
            continue
        source = Path(results_dir) / figure.path
        if not source.is_file():
            raise SystemExit(f"{source} not found; run `make {figure.make_target}` (or `make results`)")
        card = figure_card(source, figure.alt, figure.caption, png_only=figure.embed == "png")
        page = _insert_cards(page, figure, card)
    return page


# ---------- front section ----------

def anchor_label(anchor: str) -> str:
    match = ANCHOR_SHAPE.match(anchor)
    if match is None:
        return anchor
    return f"Fase {match.group(1)}, §{match.group(2).replace('-', '.')}"


def _exercise_of(question) -> int | None:
    """The exercise a question belongs to, from its id ("Q2.3" is exercise 2); None for an id of another shape."""
    match = re.match(r"^Q(\d+)\.", question.id)
    return int(match.group(1)) if match else None


def question_table(questions: Iterable) -> str:
    """Question of the enunciado -> link to where it is answered, with a header row per exercise."""
    titles = {number: title for number, _anchor, title in EXERCISES}
    rows = []
    current = None
    for question in questions:
        exercise = _exercise_of(question)
        if exercise is not None and exercise != current:
            current = exercise
            rows.append(
                f'<tr class="group"><th colspan="3">{html.escape(titles.get(exercise, f"Ejercicio {exercise}"))}</th></tr>'
            )
        links = " · ".join(
            f'<a href="#{html.escape(anchor, quote=True)}">{html.escape(anchor_label(anchor))}</a>'
            for anchor in question.anchors
        )
        rows.append(
            f"<tr><td>{html.escape(question.id)}</td>"
            f"<td>“{html.escape(question.text)}” (sección {html.escape(question.enunciado_section)})</td>"
            f"<td>{links}</td></tr>"
        )
    return (
        '<div class="table-wrap"><table>'
        "<thead><tr><th>Pregunta</th><th>Texto del enunciado</th><th>Dónde se responde</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def stamp(repo_dir: Path = TP_DIR) -> str:
    """Short HEAD plus a dirty flag; no dates, no paths."""

    def git(*args: str) -> str:
        done = subprocess.run(["git", *args], cwd=repo_dir, capture_output=True, text=True, check=False)
        return done.stdout.strip() if done.returncode == 0 else ""

    head = git("rev-parse", "--short", "HEAD")
    if not head:
        return "commit desconocido"
    dirty = git("status", "--porcelain", "--untracked-files=no", "--", ".")
    return f"commit {head}" + (" (con cambios sin commitear)" if dirty else "")


def fact_span(key: str, value: str) -> str:
    return f'<span class="fact" data-fact="{html.escape(key, quote=True)}">{html.escape(value)}</span>'


@dataclass(frozen=True)
class Finding:
    """One bullet of "Qué encontramos": a template of {group.key} facts and the section it summarizes."""

    topic: str
    text: str
    anchor: str
    unfavorable: bool = False


# Wording follows the conclusions of the fragments. Every number is a {group.key} fact (D-11); the unfavorable
# results are stated as they came out (PROJECT.md Key Decisions, D-04 of the slides).
FINDINGS: tuple[Finding, ...] = (
    Finding(
        "PCA",
        "El conjunto auditado tiene {pca.n_features} variables y {pca.k_80} componentes retendrían {pca.cum_k80} de la "
        "varianza. PC1 sola explica {pca.var_pc1} y es un eje de tamaño, alcance "
        "y precio. La PCA queda como diagnóstico: los modelos corren sobre las {pca.n_features} variables.",
        "f1-s6",
    ),
    Finding(
        "PCA, sensibilidad",
        "Con todas las columnas originales, que incluyen cinco dependencias lineales exactas, aparecen "
        "autovalores nulos y la matriz de correlación es singular: por eso los modelos usan el conjunto auditado.",
        "f1-s7",
    ),
    Finding(
        "SOM, grilla",
        "La regla de elección de la grilla, fijada y commiteada antes de ver resultados, eligió k = {som.chosen_k}; "
        "por error de cuantización de entrenamiento solo se habría elegido k = {som.qe_train_argmin_k}, que deja casi "
        "la mitad de las neuronas vacías.",
        "f2-s3",
    ),
    Finding(
        "SOM frente a PCA",
        "El mapa de {som.chosen_k}×{som.chosen_k} sigue a PC1 (R² {som.r2_pc1}, p = {som.p_r2_pc1}) y no a PC2 "
        "(R² {som.r2_pc2}, p = {som.p_r2_pc2}); los p salen de {som.n_permutations} permutaciones.",
        "f2-s6-4",
    ),
    Finding(
        "SOM, regiones",
        "Cantidad de regiones que da la regla fijada de antemano sobre el mapa: {som.n_regions}. No hay segmentos de "
        "creadores que interpretar; el mapa se lee como un continuo de tamaño y precio, y la regla no se retocó para "
        "obtener más regiones.",
        "f2-s6-1",
        True,
    ),
    Finding(
        "SOM, robustez",
        "Robustez de la grilla elegida frente al schedule de entrenamiento: {som.robust}. En {som.n_failing_variants} "
        "variantes de radio, tasa o épocas el error topográfico medio queda apenas sobre el máximo fijado; la "
        "ocupación de las neuronas no se degrada.",
        "f2-s4",
        True,
    ),
    Finding(
        "Oja",
        "La regla de Oja converge a PC1 en las {oja.n_seeds} seeds (abs(cos) mínimo entre pares de seeds "
        "{oja.abs_cos_min}), así que el índice es en lo esencial un orden por tamaño (Spearman {oja.corr_followers_spearman} "
        "con followers con el signo fijado). Elegir automáticamente al creador con el índice más alto no es correcto "
        "para cualquier campaña: con un signo sale {oja.max_name} (tema {oja.max_topic}, {oja.max_followers} followers) y "
        "con el signo opuesto {oja.max_opposite_name} ({oja.max_opposite_followers} followers).",
        "f3-s3",
    ),
    Finding(
        "Campañas",
        "Cada campaña tiene su regla, fijada antes de calcular las listas (commit {camp.rule_commit}). Para fútbol se "
        "recomienda empezar por profundidad educativa, que es la lista más barata en total y la más cara por mil "
        "argentinos alcanzados (USD {camp.futbol.cost_per_thousand_ar}); en perros, la lista propia cuesta USD "
        "{camp.perros.cost_per_thousand_ar} por mil. Es un juicio apoyado en supuestos escritos, no un resultado de la regla.",
        "f3-s5-1",
    ),
    Finding(
        "Campañas frente a followers",
        "Elegir solo por followers ignora el tema y el objetivo: la lista de fútbol por profundidad comparte "
        "{camp.futbol.overlap_followers} de {camp.k} creadores con la lista de más followers y "
        "{camp.futbol.overlap_followers_tema} con la de más followers dentro del tema; la de perros comparte "
        "{camp.perros.overlap_followers} y {camp.perros.overlap_followers_tema}. Estos datos no permiten afirmar nada "
        "sobre el retorno de ninguna de las dos estrategias.",
        "f3-s5-5",
    ),
    Finding(
        "Letras",
        "En letras de {letters.n_pixels} píxeles, el set separado {letters.separated_set} tiene máximo |solapamiento| "
        "{letters.separated_max_overlap} y margen mínimo {letters.separated_min_margin}; el correlacionado "
        "{letters.correlated_set} llega a {letters.correlated_max_overlap}. Entre todos los subconjuntos de cuatro "
        "letras, {letters.p4_stable_4} ({letters.p4_all_stable_fraction}) tienen las cuatro estables.",
        "f4-s6",
    ),
    Finding(
        "Letras, estados espurios",
        "Con ruido alto, {letters.spur_total} de {letters.spur_trials} corridas ({letters.spur_total_pct}) terminan en un "
        "estado espurio (inverso, mezcla u otro); el más común es el {letters.spurious_class}.",
        "f4-s7",
    ),
    Finding(
        "QR, Hebb",
        "Con la regla de Hebb la recuperación exacta de los {qr.n_qr} QR es {qr.hebb_exact_noise0} incluso sin ruido: no "
        "son puntos fijos de la red. Siempre cae al mismo atractor, la mayoría píxel a píxel de los QR, a entre "
        "{qr.majority_hamming_min} y {qr.majority_hamming_max} píxeles de cada uno (de {qr.n_pixels}); la causa es la "
        "correlación entre los QR (máximo |solapamiento| {qr.max_abs_overlap}).",
        "f5-s4",
        True,
    ),
    Finding(
        "QR, pseudo-inversa",
        "La pseudo-inversa sostiene {qr.pinv_exact_noise0} de recuperación exacta hasta el nivel de ruido "
        "{qr.pinv_last_full_noise}, pero en el nivel {qr.noise_high} cae a {qr.pinv_at_high}. Una tabla de búsqueda por "
        "distancia de Hamming, sin dinámica, queda en {qr.hamming_at_high} en ese mismo nivel: iguala o supera a la red "
        "en todo el rango evaluado.",
        "f5-s5",
        True,
    ),
    Finding(
        "QR, límites",
        "Un corrimiento de un píxel ya deja la consulta a {qr.shift1_query_hamming} de {qr.n_pixels} píxeles de la fuente "
        "y el estado que recupera la pseudo-inversa queda todavía más lejos, a {qr.shift1_recovered_hamming}. No se "
        "corrió ningún decodificador de QR: no se afirma que un QR recuperado se pueda escanear.",
        "f5-s6",
        True,
    ),
)

SUMMARY_LEAD = (
    "Los números de esta sección se leen de los archivos de resultados cuando se arma la página y se marcan con "
    "fondo; los resultados poco favorables van de frente, con la marca de la izquierda, tal como salieron."
)
METHOD_PARAGRAPHS = (
    "Las reglas de cada análisis se fijaron y se commitearon antes de mirar los resultados, y un sha256 las custodia: "
    "si cambia el texto de la regla o el código que la aplica, los scripts se niegan a correr. Son la regla de la "
    "grilla del SOM, la regla de cada campaña (commit {camp.rule_commit}), la selección de letras y el protocolo de "
    "los QR. Lo que sale de una regla se informa como salió, aunque sea poco favorable.",
    "Cada experimento corre varias seeds ({oja.n_seeds} en Oja, {qr.n_seeds} en los QR) y las tablas muestran la media y "
    "el desvío entre seeds, no una seed sola. Los contrastes del SOM usan nulos por permutación "
    "({som.n_permutations} permutaciones, semilla fija).",
    "Para reconstruir todo: `make results` regenera las tablas y las figuras desde los datos, y `make deliverables` "
    "arma además las slides y esta página. Los números de las secciones generadas se leen de los resultados; los que "
    "están escritos en los fragmentos se verifican contra ellos al armar la página, que se niega a construirse si "
    "alguno cambió.",
)


def typed_numbers(section_html: str) -> list[str]:
    """Every decimal number (with comma) or percentage in the text of the HTML outside the data-fact spans."""
    bare = re.sub(r"<[^>]+>", " ", FACT_SPAN.sub("", section_html))
    return TYPED_NUMBER.findall(bare)


def _inline_markup(text: str) -> str:
    """Escape text and turn `x` into <code>x</code> and **x** into <strong>x</strong> (the only inline markup used)."""
    escaped = html.escape(text, quote=False)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)


def summary_section(findings: Iterable[Finding], fact_values: dict[str, str]) -> str:
    items = []
    for finding in findings:
        # escape the template first, as method_section does; fact_span escapes the values
        body = facts.fill(html.escape(finding.text, quote=False), fact_values, wrap=fact_span)
        mark = "Resultado desfavorable" if finding.unfavorable else finding.topic
        topic = f"{finding.topic}. " if finding.unfavorable else ""
        link = f'<a href="#{html.escape(finding.anchor, quote=True)}">{html.escape(anchor_label(finding.anchor))}</a>'
        css = ' class="unfavorable"' if finding.unfavorable else ""
        items.append(f"<li{css}><strong>{html.escape(mark)}.</strong> {html.escape(topic)}{body} Detalle: {link}.</li>")
    return (
        '<h2 id="resumen">Qué encontramos</h2>\n'
        f'<p class="lead">{html.escape(SUMMARY_LEAD)}</p>\n'
        f"<ul>{''.join(items)}</ul>"
    )


def method_section(fact_values: dict[str, str]) -> str:
    paragraphs = [f"<p>{facts.fill(_inline_markup(text), fact_values, wrap=fact_span)}</p>" for text in METHOD_PARAGRAPHS]
    return '<h2 id="metodo">Cómo trabajamos</h2>\n' + "\n".join(paragraphs)


# ---------- glossary and jargon links (D-13) ----------

@dataclass(frozen=True)
class GlossaryEntry:
    anchor: str
    label: str
    title: str
    que: str


DECISION_HEADING = re.compile(r"^### F(\d+) D-(\d+)([a-z]?) — (.+?)\s*$")
PITFALL_HEADING = re.compile(r"^### Pitfall (\d+)([a-z]?) — (.+?)\s*$")
REQUIREMENT_HEADING = re.compile(r"^### ([A-Z]{2,6})-(\d+) — (.+?)\s*$")
MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
QUE_PREFIX = "**Qué:**"
DECISION_ID = re.compile(r"D-(\d+)([a-z]?)")
TAG_SPLIT = re.compile(r"(<[^>]*>)")
TAG_NAME = re.compile(r"<(/?)([A-Za-z][A-Za-z0-9]*)")
SKIP_ELEMENTS = frozenset({"code", "pre", "a"})


def _que_of(body: list[str]) -> str:
    """The **Qué:** sentence of an entry; an entry without one (a requirement) gives its first paragraph line."""
    lines = [line.strip() for line in body if line.strip()]
    for line in lines:
        if line.startswith(QUE_PREFIX):
            return MARKDOWN_LINK.sub(r"\1", line[len(QUE_PREFIX):].strip())
    return MARKDOWN_LINK.sub(r"\1", lines[0]) if lines else ""


def parse_glossary(text: str) -> dict[str, GlossaryEntry]:
    """Entries of DECISIONS.md keyed by anchor: g-f<n>-d-<nn><letter>, g-pitfall-<n><letter>, g-req-<id>.

    Reads the fixed heading grammar `### F<n> D-<nn> — `, `### Pitfall <n> — ` and `### <REQ-ID> — `; the project
    decisions (`### KD-<n> — `) are not jargon of the fragments and are skipped. A duplicate anchor stops the build.
    """
    lines = text.splitlines()
    entries: dict[str, GlossaryEntry] = {}
    for index, line in enumerate(lines):
        decision = DECISION_HEADING.match(line)
        pitfall = PITFALL_HEADING.match(line)
        requirement = REQUIREMENT_HEADING.match(line)
        if decision:
            phase, number, letter, title = decision.groups()
            anchor, label = f"g-f{phase}-d-{number}{letter}", f"F{phase} D-{number}{letter}"
        elif pitfall:
            number, letter, title = pitfall.groups()
            anchor, label = f"g-pitfall-{number}{letter}", f"Pitfall {number}{letter}"
        elif requirement and requirement.group(1) != "KD":
            prefix, number, title = requirement.groups()
            anchor, label = f"g-req-{prefix.lower()}-{number}", f"{prefix}-{number}"
        else:
            continue
        end = next((i for i in range(index + 1, len(lines)) if lines[i].startswith("#")), len(lines))
        if anchor in entries:
            raise SystemExit(f"DECISIONS.md has two entries for {label}")
        entries[anchor] = GlossaryEntry(anchor, label, title.replace("`", ""), _que_of(lines[index + 1:end]))
    return entries


def link_jargon(html_text: str, fragment_no: int, glossary: dict[str, GlossaryEntry]) -> tuple[str, set[str]]:
    """Link decision IDs, Pitfall N and requirement IDs of the text of an HTML fragment to the glossary annex.

    A decision ID belongs to the phase of the fragment, except in "Fase M (D-NN, ...": there it belongs to phase M. A
    lettered ID without an entry of its own (D-11a, Pitfall 14b) links to its parent. Text inside code, pre and a
    elements and every attribute value are left alone. An ID without an entry stops the build. Returns the new HTML
    and the set of glossary anchors it linked.
    """
    used: set[str] = set()
    prefixes = sorted({m.group(1) for anchor in glossary if (m := re.match(r"g-req-([a-z]+)-", anchor))})

    def anchor_for(kind: str, found: str, candidates: list[str], phase: int | None = None) -> str:
        for candidate in candidates:
            if candidate in glossary:
                return candidate
        where = f" (looked for phase {phase})" if phase is not None else ""
        raise SystemExit(
            f"fragment {fragment_no}: {kind} {found} has no entry in the glossary{where}; add it to DECISIONS.md"
        )

    def link(anchor: str, text: str) -> str:
        entry = glossary[anchor]
        used.add(anchor)
        title = html.escape(f"{entry.label} — {entry.title}", quote=True)
        return f'<a class="jargon" href="#{anchor}" title="{title}">{text}</a>'

    def link_decision(found: str, phase: int) -> str:
        number, letter = DECISION_ID.fullmatch(found).groups()
        candidates = [f"g-f{phase}-d-{number}{letter}"] + ([f"g-f{phase}-d-{number}"] if letter else [])
        return link(anchor_for("decision", found, candidates, phase), found)

    alternatives = [
        r"(?P<lead>Fase\s+(?P<phase>\d+)\s*\()(?P<group>D-\d+[a-z]?(?![\w-])(?:\s*(?:,|;|\by\b|\be\b)\s*D-\d+[a-z]?(?![\w-]))*)",
        r"(?<![\w-])(?P<decision>D-\d+[a-z]?)(?![\w-])",
        r"(?<![\w-])(?P<pitfall>Pitfall\s+(?P<pn>\d+)(?P<pl>[a-z]?))(?![\w-])",
    ]
    if prefixes:
        alternatives.append(rf"(?<![\w-])(?P<req>(?P<rp>{'|'.join(prefixes).upper()})-(?P<rn>\d+))(?![\w-])")
    jargon = re.compile("|".join(alternatives))

    def replace(match: re.Match) -> str:
        if match.group("group") is not None:
            phase = int(match.group("phase"))
            return match.group("lead") + DECISION_ID.sub(lambda i: link_decision(i.group(0), phase), match.group("group"))
        if match.group("decision") is not None:
            return link_decision(match.group("decision"), fragment_no)
        if match.group("pitfall") is not None:
            number, letter = match.group("pn"), match.group("pl")
            candidates = [f"g-pitfall-{number}{letter}"] + ([f"g-pitfall-{number}"] if letter else [])
            return link(anchor_for("Pitfall", match.group("pitfall"), candidates), match.group("pitfall"))
        found = match.group("req")
        return link(anchor_for("requirement", found, [f"g-req-{match.group('rp').lower()}-{match.group('rn')}"]), found)

    out: list[str] = []
    depth = 0  # open code, pre or a elements around the current text
    for index, piece in enumerate(TAG_SPLIT.split(html_text)):
        if index % 2:  # a tag: only its name matters, its attributes are never rewritten
            tag = TAG_NAME.match(piece)
            if tag and tag.group(2).lower() in SKIP_ELEMENTS and not piece.endswith("/>"):
                depth = max(0, depth + (-1 if tag.group(1) else 1))
            out.append(piece)
        else:
            out.append(piece if depth else jargon.sub(replace, piece))
    return "".join(out), used


def _glossary_order(anchor: str) -> tuple:
    """Decisions by phase and ID, then pitfalls, then requirements."""
    if match := re.fullmatch(r"g-f(\d+)-d-(\d+)([a-z]?)", anchor):
        return (0, "", int(match.group(1)), int(match.group(2)), match.group(3))
    if match := re.fullmatch(r"g-pitfall-(\d+)([a-z]?)", anchor):
        return (1, "", int(match.group(1)), 0, match.group(2))
    match = re.fullmatch(r"g-req-([a-z]+)-(\d+)", anchor)
    return (2, match.group(1), 0, int(match.group(2)), "") if match else (3, anchor, 0, 0, "")


def glossary_section(glossary: dict[str, GlossaryEntry], used: set[str]) -> str:
    """The annex: a definition list of the referenced entries, each term carrying the id its links point to."""
    items = []
    for anchor in sorted(used, key=_glossary_order):
        entry = glossary[anchor]
        items.append(
            f'<dt id="{anchor}">{html.escape(entry.label)} — {html.escape(entry.title)}</dt>'
            f"<dd>{_inline_markup(entry.que)}</dd>"
        )
    return (
        '<h2 id="glosario">Glosario de decisiones y referencias</h2>\n'
        '<p class="lead">Cada sigla de los fragmentos (decisión, Pitfall o requisito) enlaza a su entrada.</p>\n'
        f'<dl class="glossary">{"".join(items)}</dl>'
    )


def notes_section(notes_path: Path) -> str:
    """The presenter script (D-06 fallback) as an annex: the Markdown file rendered without ids, headings demoted.

    The notes quote creator names and handles from the data, so `&` and `<` are escaped before Markdown runs: Markdown
    passes raw HTML through, and an entity it keeps as text. `>` is left alone, since it marks a Markdown quote.
    """
    path = Path(notes_path)
    if not path.is_file():
        raise SystemExit(f"{path} not found; --notes needs the presenter script as a Markdown file")
    source = path.read_text(encoding="utf-8").replace("&", "&amp;").replace("<", "&lt;")
    body = markdown.markdown(source, extensions=["tables", "fenced_code"])
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    body = re.sub(r"<table>.*?</table>", lambda m: f'<div class="table-wrap">{m.group(0)}</div>', body, flags=re.S)
    body = re.sub(r"<(/?)h([1-6])>", lambda m: f"<{m.group(1)}h{min(int(m.group(2)) + 2, 6)}>", body)
    return f'<h2 id="guion">Guion de la presentación</h2>\n<section class="guion">{body}</section>'


# ---------- build ----------

def _check_page(page: str, questions: Iterable, figure_texts: list[str]) -> None:
    for question in questions:
        for anchor in question.anchors:
            if f'id="{anchor}"' not in page:
                raise SystemExit(f"question {question.id}: anchor {anchor} is not in the page")
    missing = sorted(set(HREF_TARGET.findall(page)) - set(ID_VALUE.findall(page)))
    if missing:
        raise SystemExit(f"internal link target(s) not in the page: {', '.join(missing[:10])}")
    leftover = TOKEN_SHAPE.search(page)
    if leftover:
        raise SystemExit(f"unresolved fact placeholder {leftover.group(0)} in the page")
    if "<script" in page.lower():
        raise SystemExit("the page must not contain a script element")
    size = len(page.encode("utf-8"))
    if size > MAX_BYTES:
        raise SystemExit(f"the page is {size} bytes, over the {MAX_BYTES} byte ceiling")
    # The base64 runs hold the figures, scanned below once decoded; left in, the e-mail pattern would rescan each
    # multi-megabyte run from every position (quadratic).
    page_text = DATA_URI.sub("data:", page)
    for label, body in [("page", page_text), *[("embedded figure", t) for t in figure_texts]]:
        if HOME_PATH.search(body):
            raise SystemExit(f"{label} contains an absolute home-directory path")
        if EMAIL.search(body):
            raise SystemExit(f"{label} contains an email address")


def build(
    results_dir: Path,
    deliverables_dir: Path,
    out_path: Path,
    *,
    questions=deliverables_manifest.QUESTIONS,
    figures=deliverables_manifest.FIGURES,
    fragments=deliverables_manifest.FRAGMENTS,
    findings: Iterable[Finding] = FINDINGS,
    repo_dir: Path = TP_DIR,
    questions_checked: bool | None = None,
    pins: tuple[tuple[int, str], ...] = facts.DRIFT_PINS,
    glossary_path: Path = TP_DIR / "DECISIONS.md",
    notes_path: Path | None = None,
) -> Path:
    results_dir, deliverables_dir, out_path = Path(results_dir), Path(deliverables_dir), Path(out_path)
    if questions_checked is None:  # read at call time, so a test (or a later edit of the flags) is honored
        questions_checked = bool(
            deliverables_manifest.QUESTIONS_CHECKED_AGAINST_PDF is True
            and deliverables_manifest.ANSWER_SECTIONS_CHECKED is True
        )
    if questions_checked is not True:
        raise SystemExit(
            "the question table is built only from texts compared with docs/Archivo SIATP 42026.pdf and from "
            "answering sections a human confirmed (06-08 blocking-human checkpoint); set "
            "QUESTIONS_CHECKED_AGAINST_PDF and ANSWER_SECTIONS_CHECKED in analysis/deliverables_manifest.py after "
            "that review"
        )
    glossary_path = Path(glossary_path)
    if not glossary_path.is_file():
        raise SystemExit(f"{glossary_path} not found; the glossary annex is generated from DECISIONS.md")
    glossary = parse_glossary(glossary_path.read_text(encoding="utf-8"))
    fact_values = facts.load_facts(results_dir)
    drifted = facts.check_fragment_numbers(fact_values, deliverables_dir, pins)
    if drifted:
        raise SystemExit(
            f"{len(drifted)} number(s) typed in the fragments drifted from the results (D-12):\n  " + "\n  ".join(drifted)
        )

    front = [summary_section(findings, fact_values), method_section(fact_values)]
    typed = typed_numbers("\n".join(front))
    if typed:
        raise SystemExit(f"typed number(s) in the generated front section, use a fact placeholder (D-11): {typed}")

    exercises = []
    used: set[str] = set()
    for exercise_number, anchor, title in EXERCISES:
        chosen = [item for item in fragments if item[2] == exercise_number]
        if not chosen:
            continue
        exercises.append(f'<h2 id="{anchor}">{html.escape(title)}</h2>')
        for number, relative, _exercise, _title in chosen:
            source = deliverables_dir / Path(relative).name
            if not source.is_file():
                raise SystemExit(f"{source} not found; the fragment of phase {number} is missing")
            rendered = render_fragment(source.read_text(encoding="utf-8"), number, figures, results_dir)
            rendered, anchors = link_jargon(rendered, number, glossary)
            used |= anchors
            exercises.append(rendered)

    parts = [
        "<title>Informe TP4 SIA</title>",
        '<meta name="claude:viewport-fit-sides" content="cover">',
        f"<style>{STYLE}</style>",
        '<div class="informe">',
        "<h1>Informe TP4 SIA</h1>",
        front[0],
        '<h2 id="preguntas">Preguntas del enunciado</h2>',
        question_table(questions),
        front[1],
        *exercises,
        glossary_section(glossary, used),
        *([notes_section(notes_path)] if notes_path is not None else []),
        f"<footer>Generado desde {html.escape(stamp(repo_dir))}.</footer>",
        "</div>",
    ]
    page = "\n".join(parts) + "\n"

    figure_texts = [
        base64.b64decode(blob).decode("utf-8", errors="replace")
        for blob in re.findall(r'src="data:image/svg\+xml;base64,([A-Za-z0-9+/=]+)"', page)
    ]
    _check_page(page, questions, figure_texts)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results", type=Path, default=facts.RESULTS_DIR)
    parser.add_argument("--deliverables", type=Path, default=TP_DIR / "deliverables")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--notes", type=Path, default=None,
        help="presenter script (Markdown) appended as the annex 'Guion de la presentación' (D-06 fallback)",
    )
    args = parser.parse_args(argv)
    written = build(args.results, args.deliverables, args.out, notes_path=args.notes)
    try:
        shown = written.resolve().relative_to(TP_DIR)
    except ValueError:
        shown = written
    print(f"informe -> {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
