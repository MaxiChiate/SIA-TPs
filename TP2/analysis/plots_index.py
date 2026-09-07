"""The index.html that fronts a sweep's charts, and the chart/table types it renders.

Nothing here builds a figure; it renders what the two chart modules hand back.
Splitting it out is what lets ``plots_main`` write one index over charts that come
from both modules without either of them importing the other.

The index is the deliverable, not a convenience: fifteen HTML files named
``compare_speed.html`` in a timestamped directory are unnavigable during a
presentation, and the chart that answers a question from the floor has to be one
click away. So each entry carries the question it answers, and the run's own
metadata sits at the bottom - read from ``summary.csv`` and ``resolved.json``, so
the page cannot claim a configuration that did not run.
"""

from __future__ import annotations

import html
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from analysis.plots_style import GRID, SURFACE, TEXT_PRIMARY, TEXT_SECONDARY

# Section headings, in the order they appear on the page. A chart names its
# group; an unknown group is appended at the end rather than dropped.
GROUPS = (
    ("series", "Series", ""),
    ("trayectoria", "Trayectoria", "Qué hizo el algoritmo generación a generación."),
    ("comparacion", "Comparación entre variantes",
     "Si la diferencia entre dos variantes es un resultado o es ruido entre seeds."),
    ("estructura", "Propiedades del operador",
     "Lo que la estrategia garantiza por construcción, no por esta imagen."),
)


@dataclass(frozen=True, slots=True)
class Entry:
    """One row of an index: a title, a line about it, and usually a link.

    ``href`` empty renders the row as plain text instead of a link - a sweep
    that has not been plotted yet still belongs in the catalog, and linking it
    to a file that does not exist would be worse than saying so.
    """

    href: str
    title: str
    description: str
    group: str = "comparacion"


# The chart index calls its rows charts; the type is the same.
Chart = Entry


@dataclass(frozen=True, slots=True)
class Table:
    """One block of the text summary, rendered to stdout and to the index alike.

    Carrying the numbers as rows instead of preformatted lines is what lets the
    same computation feed both: a ``<pre>`` dump of the terminal output would
    render, but it would not align, wrap, or be copyable into a slide.
    """

    title: str
    headers: Sequence[str]
    rows: Sequence[Sequence[str]]
    note: str = ""
    # Columns to align right - the numeric ones. Left-aligned numbers in a table
    # cannot be scanned down a column, which is the only reason to put them in one.
    numeric_from: int = 1
    highlight_first_row: bool = False


@dataclass(frozen=True, slots=True)
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
            f"        <li>{_render_title(entry)}"
            f"<span>{_escape(entry.description)}</span></li>"
            for entry in by_group[key]
        )
        caption = f'      <p class="blurb">{_escape(blurb)}</p>\n' if blurb else ""
        sections.append(
            f"      <h2>{_escape(title)}</h2>\n{caption}      <ul>\n{items}\n      </ul>"
        )
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
    note = f'\n      <p class="note">{_escape(table.note)}</p>' if table.note else ""
    rows = "\n".join(body)
    return (
        f"      <h3>{_escape(table.title)}</h3>\n"
        f'      <div class="scroll"><table>\n'
        f"          <tr>{header}</tr>\n{rows}\n"
        f"      </table></div>{note}"
    )


_STYLE = f"""
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 48px 24px; background: {SURFACE}; color: {TEXT_PRIMARY};
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    line-height: 1.55; font-size: 14px;
  }}
  main {{ max-width: 860px; margin: 0 auto; }}
  h1 {{ font-size: 26px; margin: 0 0 4px; letter-spacing: -0.01em; }}
  p.sub {{ color: {TEXT_SECONDARY}; margin: 0 0 20px; }}
  p.lead {{ color: {TEXT_SECONDARY}; margin: 0 0 36px; }}
  h2 {{
    font-size: 13px; color: {TEXT_SECONDARY}; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.06em; margin: 36px 0 4px;
  }}
  p.blurb {{ color: {TEXT_SECONDARY}; margin: 0 0 8px; font-size: 13px; }}
  h3 {{ font-size: 15px; margin: 28px 0 8px; font-weight: 600; }}
  ul {{ list-style: none; padding: 0; margin: 0; }}
  li {{ border-bottom: 1px solid {GRID}; }}
  li a {{
    display: block; padding: 13px 0 3px; color: #2a78d6;
    text-decoration: none; font-weight: 600; font-size: 15px;
  }}
  li a:hover {{ text-decoration: underline; }}
  li span {{ display: block; padding-bottom: 13px; color: {TEXT_SECONDARY}; font-size: 13px; }}
  li .unlinked {{
    display: block; padding: 13px 0 3px; color: {TEXT_SECONDARY};
    font-weight: 600; font-size: 15px;
  }}
  /* Wide tables scroll inside their own box; the page itself never does. */
  .scroll {{ overflow-x: auto; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
  th, td {{
    text-align: left; padding: 6px 14px 6px 0; border-bottom: 1px solid {GRID};
    white-space: nowrap;
  }}
  th {{ color: {TEXT_SECONDARY}; font-weight: 500; }}
  td {{ color: {TEXT_PRIMARY}; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  tr.lead-row td {{ font-weight: 600; }}
  p.note {{ color: {TEXT_SECONDARY}; font-size: 12px; margin: 6px 0 0; }}
  table.meta th {{ width: 190px; vertical-align: top; white-space: normal; }}
  table.meta td {{ color: {TEXT_SECONDARY}; white-space: normal; }}
"""


# The catalog's own group, so a sweep listing does not borrow a chart heading.
CATALOG_GROUP = "series"


def catalog_page(summaries: Sequence) -> tuple[IndexPage, list[Entry]]:
    """The landing page over every sweep in a results directory.

    Without it the results folder is a pile of UTC timestamps: knowing which
    directory holds the crossover series means opening them until one matches,
    which is exactly the friction the per-sweep index removed one level down.
    """
    entries = []
    for summary in summaries:
        variants = ", ".join(summary.variants)
        parts = [
            f"{len(summary.variants)} variantes",
            f"{summary.seeds} seeds",
            f"{summary.runs} corridas",
        ]
        if summary.failed:
            parts.append(f"{summary.failed} fallidas")
        if summary.started:
            parts.append(summary.started)
        note = "" if summary.has_charts else " · sin gráficos: correr analysis/plots_main.py"
        entries.append(Entry(
            href=f"{summary.directory.name}/index.html" if summary.has_charts else "",
            title=summary.title,
            description=f"{variants} — {' · '.join(parts)}{note}",
            group=CATALOG_GROUP,
        ))

    plotted = sum(1 for summary in summaries if summary.has_charts)
    page = IndexPage(
        heading="TP2 · Series de experimentos",
        subtitle=f"{len(summaries)} series · {sum(s.runs for s in summaries)} corridas",
        lead="Cada serie mueve una perilla del algoritmo y repite la misma "
             "configuración sobre varias seeds. Entrá a una para ver sus gráficos, "
             "sus tablas de resultados y el config exacto que corrió."
             + ("" if plotted == len(summaries) else
                " Las que no tienen link todavía no fueron graficadas."),
    )
    return page, entries


def write_index(path: Path, page: IndexPage, charts: Sequence[Entry]) -> Path:
    """Write the index for one sweep, linking every chart written beside it."""
    tables = "\n".join(_render_table(table) for table in page.tables)
    tables_block = f"      <h2>Resultados</h2>\n{tables}\n" if tables else ""
    meta = "\n".join(
        f"          <tr><th>{_escape(key)}</th><td>{_escape(value)}</td></tr>"
        for key, value in page.meta_rows
    )
    meta_block = (
        f"      <h2>Corrida analizada</h2>\n"
        f'      <div class="scroll"><table class="meta">\n{meta}\n      </table></div>\n'
        if meta else ""
    )

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
    <h1>{_escape(page.heading)}</h1>
    <p class="sub">{_escape(page.subtitle)}</p>
    <p class="lead">{_escape(page.lead)}</p>
{_render_groups(charts)}

{tables_block}{meta_block}  </main>
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8")
    return path
