"""The index.html that fronts a series' charts, and the chart/table types it renders.

Nothing here builds a figure; it renders what the chart modules hand back. Splitting it out lets
`plots_main` write one index over charts that come from several modules without any of them importing the
others.

The index is the deliverable, not a convenience: a dozen HTML files named `compare_speed.html` in a
timestamped directory are unnavigable, and the chart that answers a question has to be one click away. Each
entry carries the question it answers behind an (i) button, like the run reports: the page shows titles and
numbers, the explanations open in a modal. The run's own metadata sits at the bottom, read from the series'
outputs, so the page can't claim a configuration that didn't run.
"""

from __future__ import annotations

import html
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from plots_style import GRID, SURFACE, TEXT_PRIMARY, TEXT_SECONDARY

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from run_report import MODAL_HTML, MODAL_SCRIPT, info  # noqa: E402

# Section headings, in the order they appear. A chart names its group; an unknown group goes last
GROUPS = (
    ("series", "Series", ""),
    ("trayectoria", "Trayectoria", "Qué hizo la red época a época."),
    ("comparacion", "Comparación entre variantes",
     "Si la diferencia entre dos variantes es un resultado o es dispersión entre seeds."),
)


@dataclass(frozen=True)
class Entry:
    """One row of an index: a title, the question it answers, and usually a link.

    An empty `href` renders the row as plain text: a series that hasn't been plotted yet still belongs in
    the catalog, and linking a file that doesn't exist would be worse than saying so.
    """

    href: str
    title: str
    description: str
    group: str = "comparacion"


# The chart index calls its rows charts; the type is the same
Chart = Entry


@dataclass(frozen=True)
class Table:
    """One block of the summary, rendered to stdout and to the index alike.

    The numbers travel as rows, not preformatted lines, so the same computation feeds both and the page can
    align, wrap and copy them.
    """

    title: str
    headers: Sequence[str]
    rows: Sequence[Sequence[str]]
    note: str = ""
    numeric_from: int = 1  # columns from here on are numbers: aligned right
    highlight_first_row: bool = False


@dataclass(frozen=True)
class IndexPage:
    """Everything the page shows besides the charts themselves."""

    heading: str
    subtitle: str
    lead: str
    meta_rows: Sequence[tuple[str, str]] = field(default_factory=tuple)
    tables: Sequence[Table] = field(default_factory=tuple)


def _escape(value) -> str:
    return html.escape(str(value), quote=True)


def _render_title(entry: Entry) -> str:
    if not entry.href:
        return f'<span class="unlinked">{_escape(entry.title)}</span>'
    return f'<a href="{_escape(entry.href)}">{_escape(entry.title)}</a>'


def _heading(tag: str, title: str, explanation: str = "") -> str:
    button = info(title, _escape(explanation)) if explanation else ""
    return f'<div class="head"><{tag}>{_escape(title)}</{tag}>{button}</div>'


def _render_groups(charts: Sequence[Entry]) -> str:
    by_group: dict[str, list[Entry]] = {}
    for chart in charts:
        by_group.setdefault(chart.group, []).append(chart)

    known = [key for key, _, _ in GROUPS]
    ordered = [(key, title, blurb) for key, title, blurb in GROUPS if key in by_group]
    ordered += [(key, key.title(), "") for key in by_group if key not in known]

    sections = []
    for key, title, blurb in ordered:
        items = "\n".join(
            f'        <li><div class="row">{_render_title(entry)}{info(entry.title, _escape(entry.description))}</div></li>'
            for entry in by_group[key])
        sections.append(f"      {_heading('h2', title, blurb)}\n      <ul>\n{items}\n      </ul>")
    return "\n".join(sections)


def _render_table(table: Table) -> str:
    def cell(tag: str, index: int, value) -> str:
        align = ' class="num"' if index >= table.numeric_from else ""
        return f"<{tag}{align}>{_escape(value)}</{tag}>"

    header = "".join(cell("th", i, name) for i, name in enumerate(table.headers))
    body = []
    for position, row in enumerate(table.rows):
        cells = "".join(cell("td", i, value) for i, value in enumerate(row))
        marker = ' class="lead-row"' if table.highlight_first_row and position == 0 else ""
        body.append(f"          <tr{marker}>{cells}</tr>")
    rows = "\n".join(body)
    return (f"      {_heading('h3', table.title, table.note)}\n"
            f'      <div class="scroll"><table>\n          <tr>{header}</tr>\n{rows}\n      </table></div>')


_STYLE = f"""
  * {{ box-sizing: border-box; }}
  [hidden] {{ display: none !important; }}
  body {{
    margin: 0; padding: 48px 24px; background: {SURFACE}; color: {TEXT_PRIMARY};
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    line-height: 1.55; font-size: 14px;
  }}
  main {{ max-width: 860px; margin: 0 auto; }}
  h1 {{ font-size: 26px; margin: 0 0 4px; letter-spacing: -0.01em; }}
  p.sub {{ color: {TEXT_SECONDARY}; margin: 0 0 8px; }}
  .head {{ display: flex; align-items: center; gap: 8px; }}
  h2 {{
    font-size: 13px; color: {TEXT_SECONDARY}; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.06em; margin: 36px 0 4px;
  }}
  h3 {{ font-size: 15px; margin: 28px 0 8px; font-weight: 600; }}
  ul {{ list-style: none; padding: 0; margin: 0; }}
  li {{ border-bottom: 1px solid {GRID}; }}
  .row {{ display: flex; align-items: center; gap: 8px; padding: 12px 0; }}
  .row a {{ color: #2a78d6; text-decoration: none; font-weight: 600; font-size: 15px; }}
  .row a:hover {{ text-decoration: underline; }}
  .unlinked {{ color: {TEXT_SECONDARY}; font-weight: 600; font-size: 15px; }}
  .info {{ flex: none; width: 20px; height: 20px; padding: 0; border: 1px solid {GRID}; border-radius: 50%;
          background: #fff; color: #7b818b; font: italic 600 12px/1 Georgia, serif; cursor: pointer; }}
  .info:hover, .info:focus-visible {{ color: #2a78d6; border-color: #2a78d6; background: #eaf2fd; outline: 0; }}
  /* Wide tables scroll inside their own box; the page itself never does. */
  .scroll {{ overflow-x: auto; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
  th, td {{
    text-align: left; padding: 6px 14px 6px 0; border-bottom: 1px solid {GRID}; white-space: nowrap;
  }}
  th {{ color: {TEXT_SECONDARY}; font-weight: 500; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  tr.lead-row td {{ font-weight: 600; }}
  table.meta th {{ width: 190px; vertical-align: top; white-space: normal; }}
  table.meta td {{ color: {TEXT_SECONDARY}; white-space: normal; }}
  dialog.modal {{ width: min(540px, calc(100vw - 32px)); padding: 0; border: 0; border-radius: 14px;
                 background: #fff; color: {TEXT_PRIMARY}; box-shadow: 0 24px 64px rgba(16, 24, 40, 0.28); }}
  dialog.modal::backdrop {{ background: rgba(16, 24, 40, 0.4); }}
  .modal-head {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 16px 20px 0; }}
  .modal-title {{ font-size: 17px; margin: 0; }}
  .modal-close {{ font: inherit; font-size: 22px; line-height: 1; width: 30px; height: 30px; border: 0;
                 border-radius: 6px; background: transparent; color: #7b818b; cursor: pointer; }}
  .modal-close:hover {{ background: {SURFACE}; color: {TEXT_PRIMARY}; }}
  .modal-body {{ padding: 8px 20px 20px; color: {TEXT_SECONDARY}; font-size: 14px; }}
  .modal-body p {{ margin: 8px 0; }}
"""

# The catalog's own group, so a series listing doesn't borrow a chart heading
CATALOG_GROUP = "series"


def catalog_page(summaries: Sequence) -> tuple[IndexPage, list[Entry]]:
    """The landing page over every series in a results directory.

    Without it the results folder is a pile of `<series>_<date>_<time>` names: knowing which holds the
    learning-rate series means opening them until one matches.
    """
    entries = []
    for summary in summaries:
        parts = [f"{len(summary.variants)} variantes", f"{summary.seeds} seeds", f"{summary.runs} corridas"]
        if summary.failed:
            parts.append(f"{summary.failed} fallidas")
        if summary.started:
            parts.append(summary.started)
        note = "" if summary.has_charts else " · sin gráficos: correr analysis/plots_main.py"
        entries.append(Entry(
            href=f"{summary.directory.name}/index.html" if summary.has_charts else "",
            title=summary.title, description=f"{', '.join(summary.variants)} — {' · '.join(parts)}{note}",
            group=CATALOG_GROUP))

    plotted = sum(1 for summary in summaries if summary.has_charts)
    page = IndexPage(
        heading="TP3 · Series de experimentos",
        subtitle=f"{len(summaries)} series · {sum(s.runs for s in summaries)} corridas",
        lead="Cada serie cambia una perilla de la red y repite la misma configuración sobre varias seeds. Entrá a "
             "una para ver sus gráficos, sus tablas de resultados y el config exacto que corrió."
             + ("" if plotted == len(summaries) else " Las que no tienen link todavía no fueron graficadas."))
    return page, entries


def write_index(path: Path, page: IndexPage, charts: Sequence[Entry]) -> Path:
    """Write the index for one series, linking every chart written beside it."""
    tables = "\n".join(_render_table(table) for table in page.tables)
    tables_block = f"      {_heading('h2', 'Resultados')}\n{tables}\n" if tables else ""
    meta = "\n".join(f"          <tr><th>{_escape(key)}</th><td>{_escape(value)}</td></tr>"
                     for key, value in page.meta_rows)
    meta_block = (f"      {_heading('h2', 'Corrida analizada')}\n"
                  f'      <div class="scroll"><table class="meta">\n{meta}\n      </table></div>\n' if meta else "")

    document = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_escape(page.heading)}</title>
<style>{_STYLE}</style>
</head>
<body>
  <main>
    <div class="head"><h1>{_escape(page.heading)}</h1>{info(page.heading, _escape(page.lead))}</div>
    <p class="sub">{_escape(page.subtitle)}</p>
{_render_groups(charts)}

{tables_block}{meta_block}  </main>
{MODAL_HTML}
<script>{MODAL_SCRIPT}</script>
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8")
    return path
