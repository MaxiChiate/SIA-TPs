#!/usr/bin/env python3
"""Genera los gráficos de análisis (Plotly -> HTML) desde un CSV de resultados.

    python analisis/graficos_main.py                  # último CSV de resultados/
    python analisis/graficos_main.py --listar         # qué CSVs y qué gráficos hay
    python analisis/graficos_main.py --archivo analisis/resultados/demo_full.csv
    python analisis/graficos_main.py --solo tiempo_vs_nivel

Son cuatro gráficos, todos con la misma estructura: **el eje x es el nivel**
(ordenado por dificultad creciente, medida en cantidad de cajas) y **cada color
es un algoritmo + heurística**. Es decir: la comparación que se lee de un
vistazo es "qué algoritmo gana en este nivel", y lo que se sigue de grupo a
grupo es cómo se degrada cada algoritmo al subir la dificultad.

Qué gráficos se generan se elige con el diccionario `GRAFICOS` de abajo
(True/False por gráfico), o con `--solo` / `--todos` desde la línea de comandos.

Cada gráfico se guarda como un HTML independiente en `SALIDA`, más un
`index.html` que los enlaza.

Los datos salen del CSV que produce `analisis/main.py`; el esquema de columnas
está documentado en `analisis/SCHEMA.md`.
"""

from __future__ import annotations

import argparse
import math
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analisis.graficos_datos import (  # noqa: E402
    Datos,
    DatosError,
    cargar,
    listar_csvs,
)
from analisis.graficos_estilo import (  # noqa: E402
    TEMAS,
    color_algoritmo,
    layout_base,
    nota,
)

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTADOS = PROJECT_ROOT / "analisis" / "resultados"
SALIDA = PROJECT_ROOT / "analisis" / "graficos"

# CSV a graficar. None = el más reciente de RESULTADOS.
# También se puede pasar por CLI con --archivo.
ARCHIVO: str | None = None

# Qué gráficos generar. Poné False para saltear uno.
GRAFICOS: dict[str, bool] = {
    "costo_vs_nivel":     True,   # calidad: largo de la solución encontrada
    "tiempo_vs_nivel":    True,   # cuánto tarda
    "nodos_vs_nivel":     True,   # esfuerzo de búsqueda
    "frontera_vs_nivel":  True,   # memoria: pico de la frontera
    "costo_dispersion_algoritmo":   True,  # dispersión de costo pooleada
    "tiempo_dispersion_algoritmo": True,  # dispersión de tiempo pooleada
    "nodos_dispersion_algoritmo":  True,  # dispersión de nodos pooleada
    "frontera_dispersion_algoritmo": True,  # dispersión de frontera pooleada
}

# Solo "light": el tema oscuro se sacó, el texto quedaba ilegible.
TEMA = "light"

# Cómo se incluye plotly.js en los HTML:
#   "directory" -> un plotly.min.js compartido en SALIDA (recomendado: offline y liviano)
#   "cdn"       -> se baja de internet al abrir (HTML chico, necesita conexión)
#   "embed"     -> cada HTML se autocontiene (~3 MB cada uno)
PLOTLY_JS = "directory"

# Abrir el index en el navegador al terminar.
ABRIR = False


# ============================================================================
# Helpers de formato
# ============================================================================

def _fmt_seg(v: float) -> str:
    if v >= 1:
        return f"{v:.2f} s"
    if v >= 0.001:
        return f"{v * 1000:.0f} ms"
    return f"{v * 1e6:.0f} µs"


def _fmt_int(v: int) -> str:
    return f"{v:,}".replace(",", ".")


def _nombre_nivel(datos: Datos, level: str) -> str:
    """Etiqueta del eje x. Las cajas van en una segunda línea: son el orden."""
    cajas = datos.cajas(level)
    return f"{level}<br>({cajas} cajas)" if cajas else level


def _subtitulo(datos: Datos) -> str:
    meta = datos.meta
    partes = [f"{datos.repeticiones} repeticiones"]
    if meta.get("timeout_seconds"):
        partes.append(f"timeout {meta['timeout_seconds']:.0f}s")
    if meta.get("executor"):
        partes.append(f"executor {meta['executor']}")
    return " · ".join(partes)


# Geometría de las barras agrupadas. Se usa también para ubicar las
# anotaciones de "no terminó" justo donde iría la barra que falta.
BARGAP = 0.30
BARGROUPGAP = 0.04


def _offset_barra(i: int, n: int) -> float:
    """Desplazamiento (en unidades de categoría) del centro de la barra i de n."""
    ancho_grupo = 1 - BARGAP
    slot = ancho_grupo / n
    return -ancho_grupo / 2 + (i + 0.5) * slot


# Proporción del alto del eje que se reserva arriba para la etiqueta de valor.
AIRE_ARRIBA = 0.20


def _rango_con_aire(valores: list[float], *, log: bool) -> list[float] | None:
    """Rango del eje y con lugar para la etiqueta que va encima de la barra más alta.

    En log el rango se expresa en potencias de 10 (es lo que espera plotly) y el
    piso baja a la década entera de abajo, para que la barra más chica no quede
    como una rayita pegada al eje.
    """
    valores = [v for v in valores if v is not None]
    if not log:
        return [0, max(valores) * (1 + AIRE_ARRIBA + 0.12)] if valores else None

    positivos = [v for v in valores if v > 0]
    if not positivos:
        return None
    piso = math.floor(math.log10(min(positivos)))
    techo = math.log10(max(positivos))
    alto = max(techo - piso, 1.0)        # con un solo dato el span sería 0
    return [piso, techo + AIRE_ARRIBA * alto]


# ============================================================================
# Gráfico genérico de barras: x = nivel, un color por algoritmo
# ============================================================================

def _barras(
    datos: Datos,
    tema: dict,
    *,
    titulo: str,
    y_titulo: str,
    valor,
    texto,
    hover_extra=None,
    log: bool = False,
    pie: str = "",
):
    """Barras agrupadas: x = nivel (por dificultad), un color por algoritmo.

    `valor(resumen)` devuelve la altura (o None si esa combinación no resolvió)
    y `texto(resumen)` la etiqueta que se dibuja sobre la barra. Esa etiqueta no
    es decorativa: es el "relief" de contraste de los slots claros de la paleta,
    y el único lugar donde se lee el número exacto sin pasar el mouse.

    Las combinaciones sin barra se anotan explícitamente como "no terminó", para
    que una ausencia no se lea como un cero.

    `hover_extra(resumen)` puede devolver líneas extra para el tooltip.
    """
    import plotly.graph_objects as go

    niveles = datos.niveles
    algoritmos = datos.algoritmos
    colores = color_algoritmo(tema, algoritmos)
    matriz = datos.matriz()

    etiquetas_x = [_nombre_nivel(datos, lv) for lv in niveles]

    fig = go.Figure()
    anotaciones = []
    todos_los_valores: list[float] = []

    for i, al in enumerate(algoritmos):
        ys, textos, hovers = [], [], []
        for level in niveles:
            r = matriz[(level, al)]
            v = valor(r)
            ys.append(v)
            textos.append(texto(r) if v is not None else "")
            if v is not None:
                todos_los_valores.append(v)

            extra = hover_extra(r) if (hover_extra and v is not None) else ""
            hovers.append(
                f"<b>{al}</b><br>{level} ({datos.cajas(level)} cajas)<br>"
                f"{y_titulo}: {texto(r) if v is not None else '—'}"
                f"{extra}<br>corridas exitosas: {r.exitosas}/{r.corridas}"
            )

            if v is None:
                estados = datos.conteo_estados(level, al)
                motivo = max(estados, key=estados.get) if estados else "sin datos"
                anotaciones.append(
                    dict(
                        x=niveles.index(level) + _offset_barra(i, len(algoritmos)),
                        y=0.02,
                        xref="x", yref="paper",
                        text=f"no terminó · {motivo}",
                        showarrow=False,
                        textangle=-90,
                        font=dict(color=tema["muted"], size=9),
                        xanchor="center",
                        yanchor="bottom",
                    )
                )

        fig.add_trace(
            go.Bar(
                name=al,
                x=etiquetas_x,
                y=ys,
                text=textos,
                textposition="outside",
                textangle=-90,          # 7 series por grupo: la barra es angosta
                textfont=dict(color=tema["ink_secondary"], size=10),
                cliponaxis=False,
                marker=dict(
                    color=colores[al],
                    # 1px de superficie por barra = los 2px de separación entre
                    # dos barras pegadas que pide la spec de marcas
                    line=dict(color=tema["surface"], width=1),
                ),
                hovertext=hovers,
                hovertemplate="%{hovertext}<extra></extra>",
            )
        )

    layout = layout_base(tema, titulo, _subtitulo(datos))
    layout["barmode"] = "group"
    layout["bargap"] = BARGAP
    layout["bargroupgap"] = BARGROUPGAP
    layout["xaxis"]["type"] = "category"
    layout["xaxis"]["title"]["text"] = "nivel — dificultad creciente →"
    layout["yaxis"]["title"]["text"] = y_titulo + (" — escala log" if log else "")
    if log:
        layout["yaxis"]["type"] = "log"
        layout["yaxis"]["dtick"] = 1        # una marca por década; sin esto plotly
        layout["yaxis"]["minor"] = dict(showgrid=False)   # llena el eje de ticks

    # Aire arriba para la etiqueta de valor de la barra más alta. El autorange de
    # plotly ajusta al dato, no al texto rotado que va *encima* del dato, así que
    # sin esto la barra más alta se come su propio número contra el techo.
    rango = _rango_con_aire(todos_los_valores, log=log)
    if rango:
        layout["yaxis"]["range"] = rango
    anotaciones.append(nota(tema, pie or "Solo se grafican las corridas con status=ok."))
    layout["annotations"] = anotaciones
    fig.update_layout(**layout)
    return fig


# ============================================================================
# Los cuatro gráficos
# ============================================================================

def g_costo_vs_nivel(datos: Datos, tema: dict):
    """Largo de la solución: la métrica que la consigna pide optimizar."""
    return _barras(
        datos, tema,
        titulo="Costo de la solución por nivel",
        y_titulo="movimientos",
        valor=lambda r: r.cost,
        texto=lambda r: _fmt_int(r.cost),
        log=False,
        pie=("Cantidad de movimientos de la solución encontrada (menos es mejor). Escala lineal: "
             "acá la diferencia importa como proporción real, no como orden de magnitud — una "
             "solución 10 veces más larga es 10 veces peor. BFS, IDDFS y A* con heurística "
             "admisible devuelven el óptimo, así que empatan en la barra más baja de cada nivel; "
             "DFS y Greedy no garantizan optimalidad y ahí se ve cuánto se pasan."),
    )


def g_tiempo_vs_nivel(datos: Datos, tema: dict):
    """Tiempo medio de resolución."""
    return _barras(
        datos, tema,
        titulo="Tiempo de resolución por nivel",
        y_titulo="segundos",
        valor=lambda r: r.tiempo_medio,
        texto=lambda r: _fmt_seg(r.tiempo_medio),
        hover_extra=lambda r: f"<br>desvío: {_fmt_seg(r.tiempo_desvio)}",
        log=True,
        pie=("Media de las corridas exitosas (columna elapsed_seconds, medida por el agente). "
             "Escala logarítmica: los tiempos abarcan varios órdenes de magnitud, así que en "
             "lineal el nivel más caro aplastaría a todos los demás contra el eje. El desvío "
             "entre repeticiones está en el tooltip."),
    )


def g_nodos_vs_nivel(datos: Datos, tema: dict):
    """Nodos expandidos: el esfuerzo de búsqueda, independiente de la máquina."""
    return _barras(
        datos, tema,
        titulo="Nodos expandidos por nivel",
        y_titulo="nodos expandidos",
        valor=lambda r: r.nodes_expanded,
        texto=lambda r: _fmt_int(r.nodes_expanded),
        log=True,
        pie=("Estados que el algoritmo sacó de la frontera y expandió. Es la medida de esfuerzo "
             "que no depende de la máquina ni de la implementación, así que es la que conviene "
             "mirar para comparar algoritmos; el tiempo la sigue de cerca. Escala logarítmica."),
    )


def g_frontera_vs_nivel(datos: Datos, tema: dict):
    """Pico de la frontera: el proxy de memoria."""
    return _barras(
        datos, tema,
        titulo="Frontera máxima por nivel",
        y_titulo="nodos en frontera (pico)",
        valor=lambda r: r.frontier_nodes,
        texto=lambda r: _fmt_int(r.frontier_nodes),
        log=True,
        pie=("Máximo de nodos que la frontera llegó a tener a la vez: el proxy de consumo de "
             "memoria. Es donde se ve la diferencia estructural entre los algoritmos que guardan "
             "un nivel entero del árbol (BFS) y los que solo guardan un camino (DFS, IDDFS). "
             "Escala logarítmica."),
    )


# ============================================================================
# Cuatro gráficos más: pooleados sobre TODOS los niveles y repeticiones, un
# bar/box por algoritmo+heurística (sin agrupar por nivel).
# ============================================================================

def _contexto_pooleado(datos: Datos, tema: dict):
    """Algoritmos en orden canónico, su color, y su resumen pooleado."""
    algoritmos = datos.algoritmos
    colores = color_algoritmo(tema, algoritmos)
    resumenes = {al: datos.resumen_pooleado(al) for al in algoritmos}
    return algoritmos, colores, resumenes


def _anotacion_no_termino(datos: Datos, tema: dict, al: str, indice: int) -> dict:
    """Misma anotación 'no terminó · <motivo>' que usa `_barras`, pero acá cada
    algoritmo es su propia categoría de x (sin offset fraccionario de grupo)."""
    estados = datos.conteo_estados_pooleado(al)
    motivo = max(estados, key=estados.get) if estados else "sin datos"
    return dict(
        x=indice, y=0.02,
        xref="x", yref="paper",
        text=f"no terminó · {motivo}",
        showarrow=False,
        textangle=-90,
        font=dict(color=tema["muted"], size=9),
        xanchor="center",
        yanchor="bottom",
    )


def _dispersion_pooleada(
    datos: Datos, tema: dict, *, titulo: str, y_titulo: str, campo: str, pie: str,
):
    """Boxplot pooleado: un box por algoritmo, valores crudos de `ResumenPooleado.<campo>`."""
    import plotly.graph_objects as go

    algoritmos, colores, resumenes = _contexto_pooleado(datos, tema)

    fig = go.Figure()
    anotaciones = []
    todos_los_valores: list[float] = []

    for i, al in enumerate(algoritmos):
        r = resumenes[al]
        valores = getattr(r, campo)
        if not valores:
            anotaciones.append(_anotacion_no_termino(datos, tema, al, i))
            continue

        todos_los_valores.extend(valores)
        fig.add_trace(
            go.Box(
                name=al,
                x=[al] * len(valores),
                y=valores,
                boxpoints="all",
                jitter=0.5,
                pointpos=0,
                fillcolor="rgba(0,0,0,0)",
                line=dict(width=2, color=colores[al]),
                marker=dict(color=colores[al], size=7),
                hovertemplate=(
                    f"<b>{al}</b><br>%{{y}}<br>"
                    f"corridas exitosas: {r.exitosas}/{r.corridas}<extra></extra>"
                ),
            )
        )

    layout = layout_base(tema, titulo, _subtitulo(datos))
    layout["showlegend"] = False
    layout["boxmode"] = "overlay"
    layout["xaxis"]["type"] = "category"
    layout["xaxis"]["categoryarray"] = algoritmos
    layout["xaxis"]["categoryorder"] = "array"
    layout["xaxis"]["title"]["text"] = "algoritmo + heurística"
    layout["yaxis"]["title"]["text"] = y_titulo + " — escala log"
    layout["yaxis"]["type"] = "log"
    layout["yaxis"]["dtick"] = 1
    layout["yaxis"]["minor"] = dict(showgrid=False)
    rango = _rango_con_aire(todos_los_valores, log=True)
    if rango:
        layout["yaxis"]["range"] = rango
    anotaciones.append(nota(tema, pie))
    layout["annotations"] = anotaciones
    fig.update_layout(**layout)
    return fig


_PIE_DISPERSION = (
    "Cada punto es una corrida exitosa (nivel × repetición) pooleada. Se usa boxplot en vez de "
    "media ± desvío porque los valores abarcan varios órdenes de magnitud entre niveles."
)


def g_costo_dispersion_algoritmo(datos: Datos, tema: dict):
    """Dispersión de costo (movimientos), pooleada sobre todos los niveles."""
    return _dispersion_pooleada(
        datos, tema,
        titulo="Dispersión de costo por algoritmo",
        y_titulo="movimientos",
        campo="costs",
        pie=_PIE_DISPERSION,
    )


def g_tiempo_dispersion_algoritmo(datos: Datos, tema: dict):
    """Dispersión del tiempo, pooleada sobre todos los niveles."""
    return _dispersion_pooleada(
        datos, tema,
        titulo="Dispersión de tiempo por algoritmo",
        y_titulo="segundos",
        campo="tiempos",
        pie=_PIE_DISPERSION,
    )


def g_nodos_dispersion_algoritmo(datos: Datos, tema: dict):
    """Dispersión de nodos expandidos, pooleada sobre todos los niveles."""
    return _dispersion_pooleada(
        datos, tema,
        titulo="Dispersión de nodos expandidos por algoritmo",
        y_titulo="nodos expandidos",
        campo="nodes_expanded",
        pie=_PIE_DISPERSION,
    )


def g_frontera_dispersion_algoritmo(datos: Datos, tema: dict):
    """Dispersión de frontera máxima, pooleada sobre todos los niveles."""
    return _dispersion_pooleada(
        datos, tema,
        titulo="Dispersión de frontera máxima por algoritmo",
        y_titulo="nodos en frontera (pico)",
        campo="frontier_nodes",
        pie=_PIE_DISPERSION,
    )


REGISTRO = {
    "costo_vs_nivel": (g_costo_vs_nivel, "Costo de la solución: qué tan lejos del óptimo queda cada algoritmo", "nivel"),
    "tiempo_vs_nivel": (g_tiempo_vs_nivel, "Tiempo de resolución en cada nivel", "nivel"),
    "nodos_vs_nivel": (g_nodos_vs_nivel, "Nodos expandidos: el esfuerzo real de búsqueda", "nivel"),
    "frontera_vs_nivel": (g_frontera_vs_nivel, "Pico de la frontera: proxy de consumo de memoria", "nivel"),
    "costo_dispersion_algoritmo": (g_costo_dispersion_algoritmo, "Dispersión de costo, pooleada sobre todos los niveles", "algoritmo"),
    "tiempo_dispersion_algoritmo": (g_tiempo_dispersion_algoritmo, "Dispersión de tiempo, pooleada sobre todos los niveles", "algoritmo"),
    "nodos_dispersion_algoritmo": (g_nodos_dispersion_algoritmo, "Dispersión de nodos expandidos, pooleada sobre todos los niveles", "algoritmo"),
    "frontera_dispersion_algoritmo": (g_frontera_dispersion_algoritmo, "Dispersión de frontera máxima, pooleada sobre todos los niveles", "algoritmo"),
}

# Título de sección por grupo, en el orden en que aparecen en index.html.
GRUPOS_INDEX = [
    ("nivel", "Gráficos"),
    ("algoritmo", "Gráficos promediados por algoritmo"),
]


# ============================================================================
# Guardado
# ============================================================================

def _guardar(fig, destino: Path, plotly_js: str) -> Path:
    """Escribe un gráfico como HTML independiente."""
    incluir = {"directory": "directory", "cdn": "cdn", "embed": True}[plotly_js]
    fig.write_html(
        str(destino),
        include_plotlyjs=incluir,
        full_html=True,
        config={"displaylogo": False, "responsive": True},
    )
    return destino


def _escribir_index(destino: Path, generados: list[tuple[str, Path]], datos: Datos, tema: dict) -> Path:
    """Un index.html que enlaza los gráficos generados y describe la corrida."""
    meta = datos.meta
    filas_meta = [
        ("archivo", datos.archivo.name),
        ("run_id", meta.get("run_id", "")),
        ("niveles", ", ".join(f"{lv} ({datos.cajas(lv)} cajas)" for lv in datos.niveles)),
        ("algoritmos", ", ".join(datos.algoritmos)),
        ("repeticiones", str(datos.repeticiones)),
        ("timeout", f"{meta['timeout_seconds']:.0f} s" if meta.get("timeout_seconds") else "sin límite"),
        ("executor", f"{meta.get('executor', '')} ({meta.get('workers', '')} workers)"),
        ("máquina", f"{meta.get('hostname', '')} · Python {meta.get('python_version', '')}"),
        ("commit", meta.get("git_commit", "") or "—"),
    ]

    aviso = ""
    if datos.invalidas:
        aviso = (
            f'<p class="aviso">Atención: {len(datos.invalidas)} corrida(s) con '
            f"<code>solution_valid=False</code>: el algoritmo devolvió una solución que "
            f"el motor no pudo reproducir.</p>"
        )

    por_grupo: dict[str, list[tuple[str, Path]]] = {grupo: [] for grupo, _ in GRUPOS_INDEX}
    for nombre, ruta in generados:
        grupo = REGISTRO[nombre][2]
        por_grupo.setdefault(grupo, []).append((nombre, ruta))

    secciones = []
    for grupo, titulo_grupo in GRUPOS_INDEX:
        entradas = por_grupo.get(grupo) or []
        if not entradas:
            continue
        items = "\n".join(
            f'      <li><a href="{ruta.name}">{nombre}</a>'
            f'<span>{REGISTRO[nombre][1]}</span></li>'
            for nombre, ruta in entradas
        )
        secciones.append(f"    <h2>{titulo_grupo}</h2>\n    <ul>\n{items}\n    </ul>")
    items = "\n".join(secciones)
    meta_html = "\n".join(
        f"      <tr><th>{k}</th><td>{v}</td></tr>" for k, v in filas_meta
    )

    html = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gráficos · {datos.archivo.stem}</title>
<style>
  :root {{
    --surface: {tema['surface']}; --page: {tema['page']};
    --ink: {tema['ink']}; --ink2: {tema['ink_secondary']};
    --muted: {tema['muted']}; --grid: {tema['grid']};
    --accent: {tema['series'][0]};
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 48px 24px; background: var(--page); color: var(--ink);
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif; line-height: 1.55;
  }}
  main {{ max-width: 760px; margin: 0 auto; }}
  h1 {{ font-size: 26px; margin: 0 0 4px; letter-spacing: -0.01em; }}
  p.sub {{ color: var(--ink2); margin: 0 0 24px; }}
  p.lead {{ color: var(--ink2); margin: 0 0 32px; font-size: 14px; }}
  .aviso {{
    background: rgba(208,59,59,0.08); border-left: 3px solid #d03b3b;
    padding: 12px 16px; border-radius: 4px; color: var(--ink2); font-size: 14px;
  }}
  ul {{ list-style: none; padding: 0; margin: 0 0 40px; }}
  li {{ border-bottom: 1px solid var(--grid); }}
  li a {{
    display: block; padding: 14px 0 4px; color: var(--accent);
    text-decoration: none; font-weight: 600; font-size: 15px;
  }}
  li a:hover {{ text-decoration: underline; }}
  li span {{ display: block; padding-bottom: 14px; color: var(--ink2); font-size: 13px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
  th, td {{ text-align: left; padding: 7px 12px 7px 0; border-bottom: 1px solid var(--grid); }}
  th {{ color: var(--muted); font-weight: 500; width: 150px; vertical-align: top; }}
  td {{ color: var(--ink2); font-variant-numeric: tabular-nums; }}
  h2 {{ font-size: 15px; color: var(--muted); font-weight: 500;
        text-transform: uppercase; letter-spacing: 0.06em; margin: 0 0 8px; }}
</style>
</head>
<body>
  <main>
    <h1>Análisis de algoritmos de búsqueda</h1>
    <p class="sub">Sokoban · TP1 Ejercicio 2 — {len(generados)} gráficos</p>
    <p class="lead">"Gráficos": el eje x es el nivel, ordenado por dificultad creciente, y cada
    color es un algoritmo con su heurística — dentro de cada nivel se comparan los algoritmos
    entre sí, de nivel a nivel se ve cómo escala cada uno. "Gráficos promediados por algoritmo":
    poolean todas las corridas exitosas de todos los niveles y repeticiones en un bar/box por
    algoritmo, sin separar por nivel.</p>
    {aviso}
{items}
    <h2>Corrida analizada</h2>
    <table>
{meta_html}
    </table>
  </main>
</body>
</html>
"""
    destino.write_text(html, encoding="utf-8")
    return destino


# ============================================================================
# CLI
# ============================================================================

def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="analisis/graficos_main.py",
        description="Genera gráficos Plotly (HTML) desde un CSV de resultados.",
    )
    p.add_argument("--archivo", help="CSV a graficar (default: el más reciente de analisis/resultados)")
    p.add_argument("--salida", help=f"directorio de salida (default: {SALIDA})")
    p.add_argument("--tema", choices=("light",), help=f"paleta (default: {TEMA})")
    p.add_argument("--solo", help="lista separada por comas: genera solo esos gráficos")
    p.add_argument("--todos", action="store_true", help="genera todos, ignorando GRAFICOS")
    p.add_argument("--listar", action="store_true", help="muestra CSVs y gráficos disponibles, y sale")
    p.add_argument("--plotly-js", choices=("directory", "cdn", "embed"),
                   help=f"cómo incluir plotly.js (default: {PLOTLY_JS})")
    p.add_argument("--abrir", action="store_true", help="abre el index en el navegador al terminar")
    return p.parse_args(argv[1:])


def _elegir_archivo(explicito: str | None) -> Path:
    if explicito:
        return Path(explicito)
    if ARCHIVO:
        ruta = Path(ARCHIVO)
        return ruta if ruta.is_absolute() else PROJECT_ROOT / ruta
    disponibles = listar_csvs(RESULTADOS)
    if not disponibles:
        raise DatosError(
            f"No hay CSVs en {RESULTADOS}. Corré primero `python analisis/main.py`."
        )
    # Una tanda interrumpida puede dejar un CSV con solo el header; elegir ese
    # por ser "el más reciente" sería un default inútil, así que lo salteamos.
    for candidato in disponibles:
        with candidato.open(encoding="utf-8") as fh:
            fh.readline()                      # header
            if fh.readline().strip():          # ¿hay al menos una fila?
                if candidato is not disponibles[0]:
                    print(f"nota: {disponibles[0].name} no tiene filas, uso {candidato.name}")
                return candidato
    raise DatosError(
        f"Los CSVs de {RESULTADOS} no tienen filas. Corré `python analisis/main.py`."
    )


def _seleccionar(args) -> list[str]:
    if args.solo:
        pedidos = [n.strip() for n in args.solo.split(",") if n.strip()]
        desconocidos = [n for n in pedidos if n not in REGISTRO]
        if desconocidos:
            raise DatosError(
                f"Gráfico(s) desconocido(s): {desconocidos}. "
                f"Disponibles: {sorted(REGISTRO)}."
            )
        return pedidos
    if args.todos:
        return list(REGISTRO)
    return [n for n in REGISTRO if GRAFICOS.get(n, False)]


def _listar() -> int:
    disponibles = listar_csvs(RESULTADOS)
    print(f"CSVs en {RESULTADOS}:")
    if not disponibles:
        print("  (ninguno — corré `python analisis/main.py` primero)")
    for i, p in enumerate(disponibles):
        marca = "  <- default (más reciente)" if i == 0 else ""
        print(f"  {p.name}{marca}")
    print("\nGráficos disponibles:")
    for nombre, (_, desc, _grupo) in REGISTRO.items():
        estado = "on " if GRAFICOS.get(nombre) else "off"
        print(f"  [{estado}] {nombre:20} {desc}")
    return 0


def main(argv: list[str]) -> int:
    args = _parse_args(argv)

    if args.listar:
        return _listar()

    try:
        import plotly  # noqa: F401
    except ImportError:
        print(
            "error: falta plotly. Instalalo con:\n"
            "    pip install -r analisis/requirements.txt",
            file=sys.stderr,
        )
        return 1

    try:
        archivo = _elegir_archivo(args.archivo)
        datos = cargar(archivo)
        seleccion = _seleccionar(args)
    except DatosError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not seleccion:
        print("No hay gráficos seleccionados (todos en False en GRAFICOS).", file=sys.stderr)
        print("Activá alguno, o usá --todos / --solo <nombres>.", file=sys.stderr)
        return 1

    tema = TEMAS[args.tema or TEMA]
    salida = Path(args.salida) if args.salida else SALIDA
    if not salida.is_absolute():
        salida = PROJECT_ROOT / salida
    salida.mkdir(parents=True, exist_ok=True)
    plotly_js = args.plotly_js or PLOTLY_JS

    print(f"datos:   {archivo}")
    print(f"corrida: {len(datos.filas)} filas · {datos.repeticiones} repeticiones · "
          f"{len(datos.niveles)} niveles · {len(datos.algoritmos)} algoritmos")
    print(f"salida:  {salida}")
    print(f"tema:    {args.tema or TEMA}\n")

    # La paleta está validada slot por slot hasta 8 series; más algoritmos que
    # eso caen a gris tenue y dejan de distinguirse entre sí.
    if len(datos.algoritmos) > len(tema["series"]):
        print(f"ATENCIÓN: {len(datos.algoritmos)} algoritmos y solo "
              f"{len(tema['series'])} colores validados: los últimos van todos en gris. "
              f"Recortá la lista de algoritmos del CSV.", file=sys.stderr)

    if datos.invalidas:
        print(f"ATENCIÓN: {len(datos.invalidas)} corrida(s) con solution_valid=False "
              f"(el algoritmo devolvió una solución que el motor no pudo reproducir).",
              file=sys.stderr)

    inestables = [
        (lv, al) for (lv, al), r in datos.matriz().items()
        if r.resolvio and not r.metricas_estables
    ]
    if inestables:
        print(f"ATENCIÓN: métricas no deterministas en {inestables} "
              f"(costo/nodos cambian entre repeticiones).", file=sys.stderr)

    generados: list[tuple[str, Path]] = []
    for nombre in seleccion:
        constructor, descripcion, _grupo = REGISTRO[nombre]
        try:
            fig = constructor(datos, tema)
        except Exception as exc:  # noqa: BLE001 - un gráfico roto no corta el resto
            print(f"  [error] {nombre}: {type(exc).__name__}: {exc}", file=sys.stderr)
            continue
        if fig is None:
            print(f"  [vacío] {nombre}: no hay datos suficientes, se saltea")
            continue
        destino = _guardar(fig, salida / f"{nombre}.html", plotly_js)
        generados.append((nombre, destino))
        print(f"  [ok]    {nombre:20} -> {destino.name}")

    if not generados:
        print("\nNo se generó ningún gráfico.", file=sys.stderr)
        return 1

    index = _escribir_index(salida / "index.html", generados, datos, tema)
    print(f"\n{len(generados)} gráficos generados.")
    print(f"índice: {index}")

    if args.abrir or ABRIR:
        webbrowser.open(index.as_uri())

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
