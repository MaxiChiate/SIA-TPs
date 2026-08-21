#!/usr/bin/env python3
"""Genera los gráficos de análisis (Plotly -> HTML) desde un CSV de resultados.

    python analisis/graficos_main.py                  # último CSV de resultados/
    python analisis/graficos_main.py --listar         # qué CSVs y qué gráficos hay
    python analisis/graficos_main.py --archivo analisis/resultados/demo_full.csv
    python analisis/graficos_main.py --solo tiempo_por_algoritmo,tabla_resumen

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
    ESTADO_COLOR,
    ESTADO_ORDEN,
    TEMAS,
    color_nivel,
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
    "tiempo_por_algoritmo":   True,   # cuánto tarda cada algoritmo
    "dispersion_tiempos":     True,   # cuánto varía el tiempo entre repeticiones
    "costo_solucion":         True,   # calidad: largo de la solución encontrada
    "nodos_expandidos":       True,   # esfuerzo de búsqueda
    "frontera_maxima":        True,   # memoria: pico de la frontera
    "tradeoff_costo_nodos":   True,   # optimalidad vs esfuerzo, todo junto
    "tasa_exito":             True,   # qué combinaciones terminaron y cuáles no
    "composicion_movimientos": True,  # empujes vs pasos simples
    "tabla_resumen":          True,   # los números crudos, en tabla
}

# "light" o "dark". Las dos paletas están validadas por separado.
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
    cajas = datos._cajas(level)
    return f"{level} ({cajas} cajas)" if cajas else level


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
BARGAP = 0.28
BARGROUPGAP = 0.06


def _offset_barra(i: int, n: int) -> float:
    """Desplazamiento (en unidades de categoría) del centro de la barra i de n."""
    ancho_grupo = 1 - BARGAP
    slot = ancho_grupo / n
    return -ancho_grupo / 2 + (i + 0.5) * slot


# ============================================================================
# Gráfico genérico de barras por (algoritmo x nivel)
# ============================================================================

def _barras(
    datos: Datos,
    tema: dict,
    *,
    titulo: str,
    y_titulo: str,
    valor,
    texto,
    hover_extra: str = "",
    log: bool = False,
    pie: str = "",
):
    """Barras agrupadas: x = algoritmo, un color por nivel.

    `valor(resumen)` devuelve la altura (o None si esa combinación no resolvió).
    Las combinaciones sin barra se anotan explícitamente como "no terminó", para
    que una ausencia no se lea como un cero.
    """
    import plotly.graph_objects as go

    niveles = datos.niveles
    algoritmos = datos.algoritmos
    colores = color_nivel(tema, niveles)
    matriz = datos.matriz()

    fig = go.Figure()
    anotaciones = []

    for i, level in enumerate(niveles):
        ys, textos, customs = [], [], []
        for al in algoritmos:
            r = matriz[(level, al)]
            v = valor(r)
            ys.append(v)
            textos.append(texto(r) if v is not None else "")
            customs.append(r.exitosas)
            if v is None:
                estados = datos.conteo_estados(level, al)
                motivo = max(estados, key=estados.get) if estados else "sin datos"
                anotaciones.append(
                    dict(
                        x=algoritmos.index(al) + _offset_barra(i, len(niveles)),
                        y=0.02,
                        xref="x", yref="paper",
                        text=f"no terminó<br>({motivo})",
                        showarrow=False,
                        textangle=-90,
                        font=dict(color=tema["muted"], size=10),
                        align="center",
                    )
                )

        fig.add_trace(
            go.Bar(
                name=_nombre_nivel(datos, level),
                x=algoritmos,
                y=ys,
                text=textos,
                textposition="outside",
                textfont=dict(color=tema["ink_secondary"], size=11),
                cliponaxis=False,
                marker=dict(
                    color=colores[level],
                    line=dict(color=tema["surface"], width=1),
                ),
                customdata=customs,
                hovertemplate=(
                    f"<b>%{{x}}</b><br>{_nombre_nivel(datos, level)}<br>"
                    f"{y_titulo}: %{{text}}<br>"
                    f"corridas exitosas: %{{customdata}}"
                    f"{hover_extra}<extra></extra>"
                ),
            )
        )

    layout = layout_base(tema, titulo, _subtitulo(datos))
    layout["barmode"] = "group"
    layout["bargap"] = BARGAP
    layout["bargroupgap"] = BARGROUPGAP
    layout["xaxis"]["type"] = "category"
    layout["yaxis"]["title"]["text"] = y_titulo + (" — escala log" if log else "")
    if log:
        layout["yaxis"]["type"] = "log"
        layout["yaxis"]["dtick"] = 1        # una marca por década; sin esto plotly
        layout["yaxis"]["minor"] = dict(showgrid=False)   # llena el eje de ticks
    anotaciones.append(nota(tema, pie or "Solo se grafican las corridas con status=ok."))
    layout["annotations"] = anotaciones
    fig.update_layout(**layout)
    return fig


# ============================================================================
# Los gráficos
# ============================================================================

def g_tiempo_por_algoritmo(datos: Datos, tema: dict):
    """Tiempo medio de resolución por algoritmo y nivel."""
    return _barras(
        datos, tema,
        titulo="Tiempo de resolución por algoritmo",
        y_titulo="segundos",
        valor=lambda r: r.tiempo_medio,
        texto=lambda r: _fmt_seg(r.tiempo_medio),
        log=True,
        pie=("Media de las corridas exitosas (columna elapsed_seconds, medida por el "
             "agente). Escala logarítmica: los tiempos abarcan varios órdenes de magnitud."),
    )


def g_costo_solucion(datos: Datos, tema: dict):
    """Largo de la solución encontrada — la métrica que la consigna pide optimizar."""
    import plotly.graph_objects as go

    fig = _barras(
        datos, tema,
        titulo="Costo de la solución (cantidad de movimientos)",
        y_titulo="movimientos",
        valor=lambda r: r.cost,
        texto=lambda r: _fmt_int(r.cost),
        pie=("Menos es mejor. BFS, A* e IDDFS garantizan el óptimo; Greedy y DFS no, "
             "y se ve en la diferencia de altura."),
    )

    # Marcamos el óptimo de cada nivel: es la referencia contra la que se lee
    # todo lo demás, y sin ella un costo alto no dice nada por sí solo.
    matriz = datos.matriz()
    colores = color_nivel(tema, datos.niveles)
    for level in datos.niveles:
        costos = [
            matriz[(level, al)].cost
            for al in datos.algoritmos
            if matriz[(level, al)].cost is not None
        ]
        if not costos:
            continue
        # La etiqueta va en el margen derecho, fuera del área de barras: a la
        # izquierda se superponía con el valor de la primera barra, y pegada al
        # borde sin margen se recortaba.
        fig.add_hline(
            y=min(costos),
            line=dict(color=colores[level], width=1, dash="dot"),
            annotation_text=f"óptimo {level}: {min(costos)}",
            annotation_position="right",
            annotation_xshift=6,
            annotation_font=dict(color=colores[level], size=11),
        )
    fig.update_layout(margin=dict(l=70, r=185, t=110, b=110))
    return fig


def g_nodos_expandidos(datos: Datos, tema: dict):
    """Esfuerzo de búsqueda: cuántos estados tuvo que expandir cada algoritmo."""
    return _barras(
        datos, tema,
        titulo="Nodos expandidos por algoritmo",
        y_titulo="nodos",
        valor=lambda r: r.nodes_expanded,
        texto=lambda r: _fmt_int(r.nodes_expanded),
        log=True,
        pie=("Cuántos estados sacó de la frontera y expandió. Es el trabajo real de la "
             "búsqueda, independiente de la velocidad de la máquina."),
    )


def g_frontera_maxima(datos: Datos, tema: dict):
    """Pico de la frontera — el proxy de consumo de memoria."""
    return _barras(
        datos, tema,
        titulo="Frontera máxima (proxy de memoria)",
        y_titulo="nodos en la frontera",
        valor=lambda r: r.frontier_nodes,
        texto=lambda r: _fmt_int(r.frontier_nodes),
        log=True,
        pie=("Tamaño máximo que alcanzó la frontera. Acá se ve la ventaja de IDDFS: "
             "resuelve con una frontera mínima, a cambio de reexpandir muchísimos nodos."),
    )


def g_composicion_movimientos(datos: Datos, tema: dict):
    """Desglose de la solución en empujes vs. pasos simples."""
    import plotly.graph_objects as go

    algoritmos = datos.algoritmos
    matriz = datos.matriz()
    fig = go.Figure()

    # Un subeje por nivel sería excesivo: mostramos el nivel en el eje x
    # combinado, que además deja comparar el mismo algoritmo entre niveles.
    etiquetas_x, empujes, pasos, hover = [], [], [], []
    for level in datos.niveles:
        for al in algoritmos:
            r = matriz[(level, al)]
            if not r.resolvio or r.pushes is None:
                continue
            etiquetas_x.append(f"{al}<br>{level}")
            empujes.append(r.pushes)
            pasos.append(r.simple_steps)
            hover.append(f"{al} · {level}")

    if not etiquetas_x:
        return None

    for nombre, valores, color in (
        ("empujes (mayúsculas)", empujes, tema["moves"][0]),
        ("pasos simples (minúsculas)", pasos, tema["moves"][1]),
    ):
        fig.add_trace(
            go.Bar(
                name=nombre,
                x=etiquetas_x,
                y=valores,
                marker=dict(color=color, line=dict(color=tema["surface"], width=1)),
                customdata=hover,
                hovertemplate=f"<b>%{{customdata}}</b><br>{nombre}: %{{y}}<extra></extra>",
            )
        )

    layout = layout_base(
        tema,
        "Composición de la solución: empujes vs. pasos simples",
        _subtitulo(datos),
    )
    layout["barmode"] = "stack"
    layout["bargap"] = BARGAP
    layout["xaxis"]["type"] = "category"
    layout["yaxis"]["title"]["text"] = "movimientos"
    layout["annotations"] = [nota(
        tema,
        "El costo total que se optimiza incluye los dos. Los empujes son casi constantes "
        "entre algoritmos: lo que se dispara en las soluciones malas son los pasos en vano.",
    )]
    layout["margin"]["b"] = 120
    fig.update_layout(**layout)
    return fig


def _posiciones_etiquetas(puntos: list[tuple[float, float]]) -> list[str]:
    """Ubica cada etiqueta evitando que dos puntos casi encimados se pisen.

    Pasa seguido: BFS y A* expanden casi los mismos nodos para el mismo costo,
    así que sus etiquetas se superponían hasta volverse ilegibles ("abfsar").
    El primero de un grupo encimado va arriba, el segundo abajo, el resto a los
    costados.
    """
    alternativas = ["top center", "bottom center", "middle right", "middle left"]
    ys = [y for _, y in puntos] or [0]
    rango_y = (max(ys) - min(ys)) or 1

    posiciones: list[str] = []
    colocados: list[tuple[float, float, int]] = []
    for x, y in puntos:
        lx = math.log10(x) if x > 0 else 0.0
        usadas = {
            idx for px, py, idx in colocados
            if abs(lx - px) < 0.06 and abs(y - py) / rango_y < 0.06
        }
        idx = next((i for i in range(len(alternativas)) if i not in usadas), 0)
        posiciones.append(alternativas[idx])
        colocados.append((lx, y, idx))
    return posiciones


def g_tradeoff_costo_nodos(datos: Datos, tema: dict):
    """Optimalidad vs. esfuerzo: el gráfico que resume la comparación."""
    import plotly.graph_objects as go

    niveles = datos.niveles
    colores = color_nivel(tema, niveles)
    matriz = datos.matriz()
    fig = go.Figure()

    for level in niveles:
        xs, ys, textos, custom = [], [], [], []
        for al in datos.algoritmos:
            r = matriz[(level, al)]
            if not r.resolvio or r.nodes_expanded is None or r.cost is None:
                continue
            xs.append(r.nodes_expanded)
            ys.append(r.cost)
            textos.append(al.split(":")[0])
            custom.append([_fmt_seg(r.tiempo_medio), _fmt_int(r.frontier_nodes or 0)])

        if not xs:
            continue

        fig.add_trace(
            go.Scatter(
                name=_nombre_nivel(datos, level),
                x=xs, y=ys,
                mode="markers+text",
                text=textos,
                textposition=_posiciones_etiquetas(list(zip(xs, ys))),
                textfont=dict(color=tema["ink_secondary"], size=12),
                marker=dict(
                    color=colores[level],
                    size=13,
                    line=dict(color=tema["surface"], width=2),
                ),
                customdata=custom,
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "nodos expandidos: %{x:,}<br>"
                    "costo: %{y} movimientos<br>"
                    "tiempo: %{customdata[0]}<br>"
                    "frontera máx.: %{customdata[1]}<extra></extra>"
                ),
            )
        )

    layout = layout_base(
        tema,
        "Optimalidad vs. esfuerzo de búsqueda",
        _subtitulo(datos),
    )
    layout["xaxis"]["type"] = "log"
    layout["xaxis"]["dtick"] = 1
    layout["xaxis"]["minor"] = dict(showgrid=False)
    layout["xaxis"]["title"]["text"] = "nodos expandidos — escala log"
    layout["yaxis"]["title"]["text"] = "costo de la solución (movimientos)"
    layout["annotations"] = [nota(
        tema,
        "Abajo a la izquierda es lo ideal: solución corta con poco trabajo. Cada punto "
        "está etiquetado con su algoritmo; el color distingue el nivel. Solo aparecen "
        "las combinaciones que terminaron.",
    )]
    fig.update_layout(**layout)
    return fig


def g_tasa_exito(datos: Datos, tema: dict):
    """Qué combinaciones terminaron y cuáles no. Contexto obligatorio del resto."""
    import plotly.graph_objects as go

    # Horizontal: son 10 combinaciones con nombres largos ("greedy:manhattan_sum
    # level_69"); en vertical las etiquetas salen rotadas, se pisan entre sí y se
    # recortan contra el borde.
    etiquetas = []
    for level in datos.niveles:
        for al in datos.algoritmos:
            etiquetas.append(f"{al} · {level}")

    fig = go.Figure()
    presentes = set()
    for level in datos.niveles:
        for al in datos.algoritmos:
            presentes.update(datos.conteo_estados(level, al))

    for estado in ESTADO_ORDEN:
        if estado not in presentes:
            continue
        valores = []
        for level in datos.niveles:
            for al in datos.algoritmos:
                valores.append(datos.conteo_estados(level, al).get(estado, 0))
        fig.add_trace(
            go.Bar(
                name=estado,
                y=etiquetas,
                x=valores,
                orientation="h",
                marker=dict(
                    color=ESTADO_COLOR[estado],
                    line=dict(color=tema["surface"], width=1),
                ),
                hovertemplate=f"<b>%{{y}}</b><br>{estado}: %{{x}} corridas<extra></extra>",
            )
        )

    layout = layout_base(
        tema,
        "Resultado de cada corrida por combinación",
        _subtitulo(datos),
    )
    layout["barmode"] = "stack"
    layout["bargap"] = 0.35
    layout["yaxis"]["type"] = "category"
    layout["yaxis"]["autorange"] = "reversed"   # primera combinación arriba
    layout["yaxis"]["showgrid"] = False
    layout["xaxis"]["title"]["text"] = "corridas"
    layout["xaxis"]["dtick"] = 1
    layout["annotations"] = [nota(
        tema,
        "Este gráfico es el contexto de todos los demás: una combinación en amarillo "
        "no aparece en los gráficos de tiempo/costo porque nunca terminó, no porque "
        "haya dado cero.",
    )]
    layout["margin"] = dict(l=245, r=40, t=110, b=110)
    fig.update_layout(**layout)
    return fig


def g_dispersion_tiempos(datos: Datos, tema: dict):
    """Distribución del tiempo entre repeticiones: para qué sirvió correr N veces."""
    import plotly.graph_objects as go

    niveles = datos.niveles
    colores = color_nivel(tema, niveles)
    fig = go.Figure()

    for level in niveles:
        xs, ys = [], []
        for al in datos.algoritmos:
            for f in datos.filas:
                if (f.level == level and f.algorithm_label == al
                        and f.status == "ok" and f.elapsed_seconds is not None):
                    xs.append(al)
                    ys.append(f.elapsed_seconds)
        if not ys:
            continue
        fig.add_trace(
            go.Box(
                name=_nombre_nivel(datos, level),
                x=xs, y=ys,
                marker=dict(color=colores[level], size=7),
                line=dict(width=2),
                fillcolor="rgba(0,0,0,0)",
                boxpoints="all",
                jitter=0.5,
                pointpos=0,
                hovertemplate="<b>%{x}</b><br>%{y:.4f} s<extra></extra>",
            )
        )

    layout = layout_base(
        tema,
        "Dispersión del tiempo entre repeticiones",
        _subtitulo(datos),
    )
    layout["boxmode"] = "group"
    layout["xaxis"]["type"] = "category"
    layout["yaxis"]["type"] = "log"
    layout["yaxis"]["dtick"] = 1
    layout["yaxis"]["minor"] = dict(showgrid=False)
    layout["yaxis"]["title"]["text"] = "segundos — escala log"
    layout["annotations"] = [nota(
        tema,
        "Los algoritmos son deterministas: costo y nodos se repiten idénticos entre "
        "repeticiones. Lo único que varía es el tiempo, y esto muestra cuánto.",
    )]
    fig.update_layout(**layout)
    return fig


def g_tabla_resumen(datos: Datos, tema: dict):
    """Los números crudos. Es también la 'vista de tabla' que acompaña a los gráficos."""
    import plotly.graph_objects as go

    matriz = datos.matriz()
    filas = []
    for level in datos.niveles:
        for al in datos.algoritmos:
            r = matriz[(level, al)]
            if r.resolvio:
                filas.append([
                    level, al,
                    f"{r.exitosas}/{r.corridas}",
                    _fmt_int(r.cost),
                    _fmt_int(r.nodes_expanded),
                    _fmt_int(r.frontier_nodes),
                    _fmt_seg(r.tiempo_medio),
                    f"± {_fmt_seg(r.tiempo_desvio)}" if r.tiempo_desvio else "—",
                ])
            else:
                estados = datos.conteo_estados(level, al)
                motivo = max(estados, key=estados.get) if estados else "sin datos"
                filas.append([level, al, f"0/{r.corridas}", "—", "—", "—", motivo, "—"])

    encabezados = ["nivel", "algoritmo", "éxitos", "costo", "nodos exp.",
                   "frontera máx.", "tiempo medio", "desvío"]
    columnas = list(zip(*filas)) if filas else [[] for _ in encabezados]

    # Anchos relativos: con el reparto automático la columna de algoritmo
    # recortaba "greedy:manhattan_sum".
    anchos = [1.1, 1.7, 0.7, 0.8, 1.1, 1.0, 1.0, 0.9]

    fig = go.Figure(
        go.Table(
            columnwidth=anchos,
            header=dict(
                values=[f"<b>{h}</b>" for h in encabezados],
                fill_color=tema["page"],
                font=dict(color=tema["ink"], size=12),
                align="left",
                line=dict(color=tema["grid"], width=1),
                height=32,
            ),
            cells=dict(
                values=columnas,
                fill_color=tema["surface"],
                font=dict(color=tema["ink_secondary"], size=12),
                align="left",
                line=dict(color=tema["grid"], width=1),
                height=28,
            ),
        )
    )
    layout = layout_base(tema, "Resumen numérico", _subtitulo(datos))
    layout.pop("xaxis"), layout.pop("yaxis")
    layout["margin"] = dict(l=20, r=20, t=100, b=60)
    fig.update_layout(**layout)
    return fig


# Registro: nombre -> (función, descripción para --listar y el index)
REGISTRO = {
    "tiempo_por_algoritmo": (g_tiempo_por_algoritmo, "Tiempo medio de resolución por algoritmo y nivel"),
    "dispersion_tiempos": (g_dispersion_tiempos, "Distribución del tiempo entre repeticiones"),
    "costo_solucion": (g_costo_solucion, "Largo de la solución encontrada, contra el óptimo"),
    "nodos_expandidos": (g_nodos_expandidos, "Nodos expandidos: el esfuerzo real de búsqueda"),
    "frontera_maxima": (g_frontera_maxima, "Pico de la frontera: proxy de consumo de memoria"),
    "tradeoff_costo_nodos": (g_tradeoff_costo_nodos, "Optimalidad vs. esfuerzo, todo en un plano"),
    "tasa_exito": (g_tasa_exito, "Qué corridas terminaron y cuáles dieron timeout"),
    "composicion_movimientos": (g_composicion_movimientos, "Empujes vs. pasos simples de cada solución"),
    "tabla_resumen": (g_tabla_resumen, "Los números crudos en tabla"),
}


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

    items = "\n".join(
        f'      <li><a href="{ruta.name}">{nombre}</a>'
        f'<span>{REGISTRO[nombre][1]}</span></li>'
        for nombre, ruta in generados
    )
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
  p.sub {{ color: var(--ink2); margin: 0 0 32px; }}
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
  th {{ color: var(--muted); font-weight: 500; width: 150px; }}
  td {{ color: var(--ink2); font-variant-numeric: tabular-nums; }}
  h2 {{ font-size: 15px; color: var(--muted); font-weight: 500;
        text-transform: uppercase; letter-spacing: 0.06em; margin: 0 0 8px; }}
</style>
</head>
<body>
  <main>
    <h1>Análisis de algoritmos de búsqueda</h1>
    <p class="sub">Sokoban · TP1 Ejercicio 2 — {len(generados)} gráficos</p>
    {aviso}
    <h2>Gráficos</h2>
    <ul>
{items}
    </ul>
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
    p.add_argument("--tema", choices=("light", "dark"), help=f"paleta (default: {TEMA})")
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
    for nombre, (_, desc) in REGISTRO.items():
        estado = "on " if GRAFICOS.get(nombre) else "off"
        print(f"  [{estado}] {nombre:24} {desc}")
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
        constructor, descripcion = REGISTRO[nombre]
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
        print(f"  [ok]    {nombre:24} -> {destino.name}")

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
