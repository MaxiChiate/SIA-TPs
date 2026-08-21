"""Paleta y layout base de los gráficos.

Los colores no son arbitrarios: salieron de validar la paleta contra los
criterios de daltonismo (CVD ΔE), contraste sobre la superficie y banda de
luminosidad, en modo claro y oscuro. No cambiar un hex suelto sin revalidar.

Reglas que sostiene este módulo:

- **El color identifica al nivel, no al algoritmo.** El algoritmo ya está en el
  eje x. Con solo 2 series de color la paleta pasa la validación en todos los
  tipos de gráfico, incluido el scatter (donde con 5 colores el par
  magenta/naranja queda por debajo del piso de distinción).
- **Los estados (`ok`/`timeout`/...) usan la paleta de estado**, reservada, que
  nunca se reutiliza como color de serie.
- **Nada depende solo del color**: siempre hay leyenda, etiquetas de valor en
  las barras y una tabla resumen.
"""

from __future__ import annotations

import textwrap

# --- superficies y tinta -----------------------------------------------------
TEMAS = {
    "light": {
        "surface": "#fcfcfb",
        "page": "#f9f9f7",
        "ink": "#0b0b0b",
        "ink_secondary": "#52514e",
        "muted": "#898781",
        "grid": "#e1e0d9",
        "axis": "#c3c2b7",
        # color por nivel (slots categóricos 1 y 2)
        "series": ["#2a78d6", "#eb6834"],
        # par para el desglose de movimientos (empujes / pasos simples)
        "moves": ["#4a3aa7", "#1baf7a"],
    },
    "dark": {
        "surface": "#1a1a19",
        "page": "#0d0d0d",
        "ink": "#ffffff",
        "ink_secondary": "#c3c2b7",
        "muted": "#898781",
        "grid": "#2c2c2a",
        "axis": "#383835",
        "series": ["#3987e5", "#d95926"],
        "moves": ["#9085e9", "#199e70"],
    },
}

# --- paleta de estado (fija, no se tematiza) ---------------------------------
ESTADO_COLOR = {
    "ok": "#0ca30c",           # good
    "no_solution": "#ec835a",  # serious
    "timeout": "#fab219",      # warning
    "error": "#d03b3b",        # critical
}

ESTADO_ORDEN = ["ok", "no_solution", "timeout", "error"]

FUENTE = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def color_nivel(tema: dict, levels: list[str]) -> dict[str, str]:
    """Asigna un color fijo a cada nivel, en orden y sin ciclar.

    Si algún día hay más de 2 niveles, se cae al gris tenue en vez de inventar
    hues nuevos (la paleta está validada para 2 series en todos los gráficos).
    """
    paleta = tema["series"]
    return {
        level: paleta[i] if i < len(paleta) else tema["muted"]
        for i, level in enumerate(levels)
    }


def layout_base(tema: dict, titulo: str, subtitulo: str = "") -> dict:
    """Layout común: grilla hairline sólida, ejes recesivos, leyenda arriba."""
    title = f"<b>{titulo}</b>"
    if subtitulo:
        title += f'<br><span style="font-size:13px;color:{tema["ink_secondary"]}">{subtitulo}</span>'

    def eje() -> dict:
        # Se construye de cero por eje: con un dict compartido, `dict(...)` copia
        # superficial y los dos ejes terminan apuntando al MISMO sub-dict `title`,
        # así que poner el título del eje y lo escribe también en el eje x.
        return dict(
            showgrid=True,
            gridcolor=tema["grid"],
            gridwidth=1,
            zeroline=False,
            linecolor=tema["axis"],
            linewidth=1,
            tickfont=dict(color=tema["muted"], size=12),
            title=dict(text="", font=dict(color=tema["ink_secondary"], size=12)),
        )

    return dict(
        template="none",
        title=dict(
            text=title,
            font=dict(color=tema["ink"], size=19, family=FUENTE),
            x=0,
            xref="paper",
            y=0.97,
            yanchor="top",
        ),
        paper_bgcolor=tema["surface"],
        plot_bgcolor=tema["surface"],
        font=dict(family=FUENTE, color=tema["ink_secondary"], size=13),
        xaxis=eje(),
        yaxis=eje(),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color=tema["ink_secondary"], size=12),
            bgcolor="rgba(0,0,0,0)",
            # por defecto plotly invierte la leyenda en las barras apiladas,
            # y queda al revés del orden en que se dibujan las series
            traceorder="normal",
        ),
        margin=dict(l=70, r=40, t=110, b=110),
        hoverlabel=dict(font=dict(family=FUENTE, size=12)),
        barcornerradius=4,
    )


ANCHO_NOTA = 115   # caracteres por línea en la nota al pie


def nota(tema: dict, texto: str, ancho: int = ANCHO_NOTA) -> dict:
    """Anotación al pie, para aclarar filtros o unidades sin ensuciar el título.

    El salto de línea se calcula acá: la propiedad `width` de las anotaciones de
    Plotly **recorta** el texto que no entra, no lo envuelve, así que hay que
    meter los `<br>` explícitamente.
    """
    lineas = textwrap.wrap(texto, width=ancho) or [texto]
    return dict(
        text="<br>".join(lineas),
        xref="paper", yref="paper",
        x=0, y=-0.20,
        showarrow=False,
        xanchor="left",
        yanchor="top",
        font=dict(color=tema["muted"], size=11),
        align="left",
    )
