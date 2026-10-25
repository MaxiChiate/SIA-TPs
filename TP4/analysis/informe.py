#!/usr/bin/env python3
"""The informe of TP4 as one self-contained HTML page (DELIV-02, D-09 to D-12).

    .venv/bin/python analysis/informe.py [--results DIR] [--deliverables DIR] [--out FILE]

The page is hybrid (D-12): a generated front section (summary, table that maps each question of the enunciado
to where it is answered, method) followed by the Markdown fragments of deliverables/ converted with
Python-Markdown as "Detalle técnico". Numbers of the generated text come from the results JSON through
facts.py and are wrapped as <span class="fact" data-fact="KEY">; none is typed here (D-11). Fragment headings
get number-based anchors (heading "### 6.4 ..." of fragment 2 is id="f2-s6-4") and the question table links to
them. Figures are embedded as <img src="data:image/svg+xml;base64,..."> inside a card whose background is
plots_style.SURFACE in both themes (D-09 static, D-10 light panel): matplotlib SVGs carry a global <style> and
non-unique ids, so they cannot be inlined, and inside an <img> they cannot run script.

The page follows the Artifact page contract: own <title> and <style> first, no document skeleton tags, colour
tokens on bare :root redefined for dark, side gutters with safe-area insets, tables in their own scroll box.
The fragments are only read, never written (sha256 guard of Phase 2); every change happens at render time.
The build fails loudly (SystemExit with the make command to run) when a result file is missing, a question
anchor is absent, a fact placeholder is unresolved, the page is over MAX_BYTES, or it leaks a home path or an
email address. Output: analysis/results/informe/informe.html (not versioned).
"""

from __future__ import annotations

import argparse
import base64
import html
import re
import subprocess
import sys
import unicodedata
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

TOKEN_SHAPE = re.compile(r"\{[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+\}")
HOME_PATH = re.compile(r"/Users/|/home/|[A-Za-z]:\\Users\\")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}")
NUMBERED = re.compile(r"(\d+(?:\.\d+)*)\.?(?:\s|$)")
ANCHOR_SHAPE = re.compile(r"^f(\d+)-s(\d+(?:-\d+)*)$")

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


def figure_card(path: Path, alt: str, caption: str) -> str:
    """A figure element whose img carries the SVG bytes as a data URI (never inline svg)."""
    data = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    return (
        '<figure class="fig">'
        f'<img src="data:image/svg+xml;base64,{data}" alt="{html.escape(alt)}">'
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
        page = _insert_cards(page, figure, figure_card(source, figure.alt, figure.caption))
    return page


# ---------- front section ----------

def anchor_label(anchor: str) -> str:
    match = ANCHOR_SHAPE.match(anchor)
    if match is None:
        return anchor
    return f"Fase {match.group(1)}, §{match.group(2).replace('-', '.')}"


def question_table(questions: Iterable) -> str:
    """Question of the enunciado -> link to where it is answered."""
    rows = []
    for question in questions:
        links = " · ".join(
            f'<a href="#{html.escape(anchor, quote=True)}">{html.escape(anchor_label(anchor))}</a>'
            for anchor in question.anchors
        )
        rows.append(
            f"<tr><td>“{html.escape(question.text)}” (sección {html.escape(question.enunciado_section)})</td>"
            f"<td>{links}</td></tr>"
        )
    return (
        '<div class="table-wrap"><table>'
        "<thead><tr><th>Pregunta del enunciado</th><th>Dónde se responde</th></tr></thead>"
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


SUMMARY_BULLET = (
    "La grilla del SOM de {som.chosen_k}×{som.chosen_k} sigue a PC1 (R² {som.r2_pc1}, p = {som.p_r2_pc1}) "
    "y no a PC2 (R² {som.r2_pc2}, p = {som.p_r2_pc2})."
)
METHOD_PARAGRAPH = (
    "Las reglas de cada fase se fijaron y se commitearon antes de mirar los resultados, y un sha256 las "
    "custodia: si cambian, los scripts se niegan a correr. Los contrastes usan nulos por permutación "
    "({som.n_permutations} permutaciones, semilla fija)."
)


# ---------- build ----------

def _check_page(page: str, questions: Iterable, figure_texts: list[str]) -> None:
    for question in questions:
        for anchor in question.anchors:
            if f'id="{anchor}"' not in page:
                raise SystemExit(f"question {question.id}: anchor {anchor} is not in the page")
    leftover = TOKEN_SHAPE.search(page)
    if leftover:
        raise SystemExit(f"unresolved fact placeholder {leftover.group(0)} in the page")
    if "<script" in page.lower():
        raise SystemExit("the page must not contain a script element")
    size = len(page.encode("utf-8"))
    if size > MAX_BYTES:
        raise SystemExit(f"the page is {size} bytes, over the {MAX_BYTES} byte ceiling")
    for label, body in [("page", page), *[("embedded figure", t) for t in figure_texts]]:
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
    repo_dir: Path = TP_DIR,
) -> Path:
    results_dir, deliverables_dir, out_path = Path(results_dir), Path(deliverables_dir), Path(out_path)
    fact_values = facts.load_facts(results_dir)

    summary = facts.fill(SUMMARY_BULLET, fact_values, wrap=fact_span)
    method = facts.fill(METHOD_PARAGRAPH, fact_values, wrap=fact_span)

    exercise_one = []
    for number, relative, exercise, _title in fragments:
        if exercise != 1:
            continue
        source = deliverables_dir / Path(relative).name
        if not source.is_file():
            raise SystemExit(f"{source} not found; the fragment of phase {number} is missing")
        exercise_one.append(render_fragment(source.read_text(encoding="utf-8"), number, figures, results_dir))

    parts = [
        "<title>Informe TP4 SIA</title>",
        '<meta name="claude:viewport-fit-sides" content="cover">',
        f"<style>{STYLE}</style>",
        '<div class="informe">',
        "<h1>Informe TP4 SIA</h1>",
        '<h2 id="resumen">Qué encontramos</h2>',
        f"<ul><li>{summary}</li></ul>",
        '<h2 id="preguntas">Preguntas del enunciado</h2>',
        question_table(questions),
        '<h2 id="metodo">Cómo trabajamos</h2>',
        f"<p>{method}</p>",
        '<h2 id="ej1">Ejercicio 1</h2>',
        *exercise_one,
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
    args = parser.parse_args(argv)
    written = build(args.results, args.deliverables, args.out)
    try:
        shown = written.resolve().relative_to(TP_DIR)
    except ValueError:
        shown = written
    print(f"informe -> {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
