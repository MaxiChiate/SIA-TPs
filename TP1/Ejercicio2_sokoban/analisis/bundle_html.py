#!/usr/bin/env python3
"""Junta el index.html + los gráficos que genera graficos_main.py en un solo
archivo HTML autocontenido, para compartir sin tener que mandar la carpeta
entera (mail, Slack, un artifact).

    python analisis/graficos_main.py            # genera analisis/graficos/
    python analisis/bundle_html.py               # los junta en un solo HTML
    python analisis/bundle_html.py --abrir

Requiere que `graficos_main.py` se haya corrido con `--plotly-js directory`
(el default): este script busca un `plotly.min.js` al lado del `index.html` y
lo inlinea una sola vez, así el resultado no depende de ningún archivo externo.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ORIGEN = PROJECT_ROOT / "analisis" / "graficos"


class BundleError(Exception):
    pass


_decoder = json.JSONDecoder()


def _parse_next(texto: str, idx: int) -> tuple[object, int]:
    while texto[idx] in " \t\r\n,":
        idx += 1
    return _decoder.raw_decode(texto, idx)


def _extraer_grafico(html: str) -> tuple[str, object, object, object]:
    """De un HTML que exportó Plotly (`fig.write_html`), saca el id del div y
    los tres argumentos de `Plotly.newPlot(id, data, layout, config)`, ya
    parseados como objetos Python (no como substring: un regex no-greedy se
    corta en el primer `}`/`]` que encuentra, y estos JSON tienen miles)."""
    m = re.search(r'<div id="([0-9a-f-]{36})" class="plotly-graph-div"', html)
    if not m:
        raise BundleError("no parece un HTML de Plotly (falta el div plotly-graph-div)")
    div_id = m.group(1)
    ancla = re.search(r'Plotly\.newPlot\(\s*"' + re.escape(div_id) + r'"\s*,', html)
    if not ancla:
        raise BundleError(f"no encontré el Plotly.newPlot(\"{div_id}\", ...) correspondiente")
    idx = ancla.end()
    data, idx = _parse_next(html, idx)
    layout, idx = _parse_next(html, idx)
    config, idx = _parse_next(html, idx)
    return div_id, data, layout, config


def bundle(origen: Path, salida: Path) -> Path:
    index_path = origen / "index.html"
    if not index_path.exists():
        raise BundleError(f"no existe {index_path}. Corré primero graficos_main.py.")
    plotly_path = origen / "plotly.min.js"
    if not plotly_path.exists():
        raise BundleError(
            f"no existe {plotly_path}. Corré graficos_main.py sin --plotly-js "
            f"(el default 'directory' deja plotly.min.js al lado del index)."
        )

    index_html = index_path.read_text(encoding="utf-8")
    plotly_js = plotly_path.read_text(encoding="utf-8")

    # Los <a href="nombre.html"> del index son los gráficos a embeber. Cada uno
    # pasa a ser un ancla (#nombre) a una sección nueva más abajo.
    slugs = [
        m.group(1)
        for m in re.finditer(r'href="([\w.\-]+)\.html"', index_html)
    ]
    if not slugs:
        raise BundleError(f"{index_path} no tiene links a gráficos (href=\"*.html\")")

    secciones = []
    newplots = []
    for slug in slugs:
        ruta = origen / f"{slug}.html"
        if not ruta.exists():
            print(f"aviso: {ruta.name} no existe, lo salteo", file=sys.stderr)
            continue
        try:
            div_id, data, layout, config = _extraer_grafico(ruta.read_text(encoding="utf-8"))
        except BundleError as exc:
            print(f"aviso: {ruta.name}: {exc}, lo salteo", file=sys.stderr)
            continue
        index_html = index_html.replace(f'href="{slug}.html"', f'href="#{slug}"')
        secciones.append(
            f'    <section class="grafico" id="{slug}">\n'
            f'      <div class="plot" id="{div_id}"></div>\n'
            f'    </section>'
        )
        newplots.append(
            f'Plotly.newPlot("{div_id}", {json.dumps(data)}, '
            f'{json.dumps(layout)}, {json.dumps(config)});'
        )

    if not secciones:
        raise BundleError("ningún gráfico se pudo embeber")

    index_html = index_html.replace(
        "</style>",
        "  section.grafico { margin: 0 0 40px; }\n"
        "  .plot { width: 100%; height: 60vh; min-height: 420px; }\n"
        "</style>",
    )
    marcador = "    <h2>Corrida analizada</h2>"
    bloque_secciones = "\n".join(secciones)
    if marcador in index_html:
        index_html = index_html.replace(marcador, f"{bloque_secciones}\n\n{marcador}")
    else:
        index_html = index_html.replace("</main>", f"{bloque_secciones}\n  </main>")

    index_html = index_html.replace(
        "</body>",
        f"<script>{plotly_js}</script>\n<script>\n" + "\n".join(newplots) + "\n</script>\n</body>",
    )

    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(index_html, encoding="utf-8")
    return salida


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="analisis/bundle_html.py",
        description="Junta index.html + gráficos de analisis/graficos/ en un solo HTML autocontenido.",
    )
    p.add_argument("--origen", help=f"carpeta con index.html + gráficos (default: {ORIGEN})")
    p.add_argument("--salida", help="archivo HTML de salida (default: <origen>/standalone.html)")
    p.add_argument("--abrir", action="store_true", help="abre el resultado en el navegador al terminar")
    return p.parse_args(argv[1:])


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    origen = Path(args.origen) if args.origen else ORIGEN
    if not origen.is_absolute():
        origen = PROJECT_ROOT / origen
    salida = Path(args.salida) if args.salida else origen / "standalone.html"
    if not salida.is_absolute():
        salida = PROJECT_ROOT / salida

    try:
        resultado = bundle(origen, salida)
    except BundleError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"listo: {resultado}")
    if args.abrir:
        webbrowser.open(resultado.as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
