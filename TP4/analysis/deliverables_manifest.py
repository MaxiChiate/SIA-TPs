"""Static tables that tie the informe to the enunciado, the fragments and the figures (D-12, DELIV-02).

No I/O here: informe.py reads these tables and checks them against the real files at build time.

- `FRAGMENTS`: (number, path of the Markdown fragment, exercise, short title).
- `QUESTIONS`: the literal questions of the enunciado with the anchors that answer them. An anchor is
  `f<n>-s<a>-<b>` for the heading "<a>.<b> ..." of fragment n (informe.make_slugify).
- `FIGURES`: every figure shown in the informe or the slides, with the make target that regenerates it and the
  fixed seed it was drawn with. `path` is relative to analysis/results.

The question texts were reconstructed from the enunciado PDF (docs/Archivo SIATP 42026.pdf) with accents
assumed (06-RESEARCH A6): compare each one against the PDF before publishing.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Question:
    id: str
    text: str
    enunciado_section: str
    fragment: int
    anchors: tuple[str, ...]


@dataclass(frozen=True)
class Figure:
    key: str
    path: str
    make_target: str
    config: str
    seed: str
    fragment: int
    anchor: str
    alt: str
    caption: str
    slide: bool
    embed: str = "svg"


FRAGMENTS = (
    (2, "deliverables/02-kohonen.md", 1, "Mapa de Kohonen (SOM)"),
)

QUESTIONS = (
    Question(
        "Q1.4",
        "Analizar la grilla de neuronas y la distribución de los creadores de contenido en la misma "
        "y analizar la Matriz U.",
        "1.2", 2, ("f2-s5",),
    ),
    Question(
        "Q1.5",
        "¿Qué perfiles de creadores reúne cada región de la grilla seleccionada?",
        "1.2", 2, ("f2-s6-1", "f2-s6-2", "f2-s6-3"),
    ),
    Question(
        "Q1.6",
        "¿Coinciden con los perfiles observados en la PC1 y PC2 (biplot)?",
        "1.2", 2, ("f2-s6-4",),
    ),
    Question(
        "Q1.7",
        "¿Qué indica una distancia alta entre neuronas vecinas en la matriz U?",
        "1.2", 2, ("f2-s6-5",),
    ),
)

FIGURES = (
    Figure(
        key="som_map",
        path="som/figures/map.svg",
        make_target="som-figures",
        config="analysis/series_som_stage1.json",
        seed="4 (figure_seed de selection.json)",
        fragment=2,
        anchor="f2-s5",
        alt="Mapa de Kohonen de la grilla elegida: a la izquierda los creadores por neurona, a la derecha la matriz U",
        caption="Creadores por neurona (celdas rayadas: neuronas vacías) y matriz U de la grilla elegida.",
        slide=True,
    ),
    Figure(
        key="som_pc_planes",
        path="som/profiles/pc_planes.svg",
        make_target="som-profiles",
        config="analysis/series_som_stage1.json",
        seed="4 (figure_seed de selection.json)",
        fragment=2,
        anchor="f2-s6-4",
        alt="Mapa de Kohonen coloreado por las puntuaciones en PC1 y en PC2",
        caption="Las regiones del mapa frente a PC1 y PC2 (biplot).",
        slide=True,
    ),
)
