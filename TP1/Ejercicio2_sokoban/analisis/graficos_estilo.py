"""Paleta y layout base de los gráficos.

Los colores no son arbitrarios: salieron de validar la paleta contra los
criterios de daltonismo (CVD ΔE) y contraste sobre la superficie. No cambiar
un hex suelto sin revalidar. Solo hay tema claro: el oscuro se sacó porque el
texto quedaba ilegible.

Reglas que sostiene este módulo:

- **El color identifica al algoritmo (+ heurística), no al nivel.** El nivel ya
  está en el eje x: cada gráfico compara los algoritmos *dentro* de un nivel y
  después mira cómo se mueve esa comparación al subir la dificultad. El color
  tiene que ser la serie que se sigue de grupo a grupo, y esa es el algoritmo.
- **Los slots se asignan en orden fijo y no ciclan.** El orden de `SERIES` es el
  mecanismo de seguridad CVD, no decoración: los pares *adyacentes* (que en
  barras agrupadas son los que quedan pegados) están validados en ese orden.
  Con más de 8 algoritmos los extras caen a gris tenue en vez de inventar hues.
- **Nada depende solo del color**: siempre hay leyenda y etiqueta de valor en
  cada barra. Además de identidad, esa etiqueta es el "relief" obligatorio de
  los tres slots que en modo claro quedan por debajo de 3:1 de contraste
  (aqua, amarillo y magenta). Los ejes, la leyenda y los títulos de eje van en
  negrita para que se lean sin entrecerrar los ojos.

Validado con el script del skill de dataviz, sobre los 7 slots que usa la
corrida actual (bfs, dfs, iddfs, greedy x2, astar x2):

    node scripts/validate_palette.js \\
        "#2a78d6,#eb6834,#1baf7a,#eda100,#e87ba4,#008300,#4a3aa7" --mode light

    light: peor par adyacente CVD ΔE 9.1 (protan) · visión normal ΔE 19.6
"""

from __future__ import annotations

import textwrap

# --- superficies y tinta -----------------------------------------------------
TEMAS = {
    "light": {
        "surface": "#fcfcfb",
        "page": "#f9f9f7",
        "ink": "#0b0b0b",
        "ink_secondary": "#1c1b19",
        "muted": "#47453f",
        "grid": "#e1e0d9",
        "axis": "#726f66",
        # color por algoritmo: azul, naranja, aqua, amarillo, magenta, verde,
        # violeta, rojo. El orden importa (ver docstring).
        "series": [
            "#2a78d6", "#eb6834", "#1baf7a", "#eda100",
            "#e87ba4", "#008300", "#4a3aa7", "#e34948",
        ],
    },
}

FUENTE = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def color_algoritmo(tema: dict, algoritmos: list[str]) -> dict[str, str]:
    """Asigna un color fijo a cada algoritmo, en orden y sin ciclar.

    `algoritmos` llega en el orden canónico de `Datos.algoritmos` (primero los
    no informados, después los informados), así que un mismo algoritmo se queda
    con el mismo color mientras no cambie la lista de la corrida.

    Pasados los 8 slots se cae al gris tenue: ciclar la paleta pintaría dos
    algoritmos distintos del mismo color, que es peor que no distinguirlos.
    """
    paleta = tema["series"]
    return {
        algoritmo: paleta[i] if i < len(paleta) else tema["muted"]
        for i, algoritmo in enumerate(algoritmos)
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
            tickfont=dict(color=tema["muted"], size=12, weight="bold"),
            title=dict(text="", font=dict(color=tema["ink_secondary"], size=12, weight="bold")),
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
            font=dict(color=tema["ink_secondary"], size=12, weight="bold"),
            bgcolor="rgba(0,0,0,0)",
            traceorder="normal",
        ),
        # b tiene que alcanzar para: etiquetas de nivel en 2 líneas + título del
        # eje x + la nota al pie (ver DESPLAZAMIENTO_NOTA). Si queda corta, la
        # nota se dibuja fuera del canvas y desaparece sin avisar.
        margin=dict(l=70, r=40, t=120, b=185),
        hoverlabel=dict(font=dict(family=FUENTE, size=12)),
        barcornerradius=4,
    )


ANCHO_NOTA = 115   # caracteres por línea en la nota al pie

# Píxeles por debajo del eje x. Va en píxeles y no en fracción de `paper`
# porque `paper` es relativo al **alto del área de ploteo**, que cambia con el
# tamaño de la ventana: con una fracción fija la nota queda pegada al eje en una
# ventana chica y se sale del canvas en una grande. Estos ~105px son las dos
# líneas de la etiqueta de nivel más el título del eje x.
DESPLAZAMIENTO_NOTA = -105


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
        x=0, y=0,
        yshift=DESPLAZAMIENTO_NOTA,
        showarrow=False,
        xanchor="left",
        yanchor="top",
        font=dict(color=tema["muted"], size=11),
        align="left",
    )
