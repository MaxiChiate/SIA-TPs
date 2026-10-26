"""Static tables that tie the informe to the enunciado, the fragments and the figures (D-12, DELIV-02, DELIV-03).

No I/O at import: informe.py reads these tables and checks them against the real files at build time.

- `FRAGMENTS`: (number, path of the Markdown fragment, exercise, short title) of the five fragments.
- `QUESTIONS`: the 25 literal questions of the enunciado with the anchors that answer them. An anchor is
  `f<n>-s<a>-<b>` for the heading "<a>.<b> ..." of fragment n (informe.make_slugify).
- `FIGURES`: every report figure of the fragments, with the make target that regenerates it, its config and
  its seed. `path` is relative to analysis/results; `slide` marks the 20 figures that also have a slide
  variant (`slide_path`, written by plots_style next to the report figure).

CLI: `python analysis/deliverables_manifest.py questions` prints the review sheet a human compares with the
enunciado PDF and reads for the answering sections (06-08, Task 2).
"""

from __future__ import annotations

import html
import re
import sys
from dataclasses import dataclass
from pathlib import Path

TP_DIR = Path(__file__).resolve().parent.parent

# The question texts were reconstructed from the enunciado PDF (docs/Archivo SIATP 42026.pdf) with the accents
# rebuilt from TeX escapes (06-RESEARCH A6). Task 3 of 06-08 sets this to True only after a human compared the
# 25 texts with the PDF at the Task 2 checkpoint. test_questions_checked_against_pdf guards it.
QUESTIONS_CHECKED_AGAINST_PDF = False

# The anchors come from the research proposal and the executor's reading of the fragments; the anchor tests only
# prove that each section exists, not that it answers its question. Task 3 of 06-08 sets this to True only after a
# human confirmed at the Task 2 checkpoint that every linked section answers its question.
# test_answer_sections_checked guards it.
ANSWER_SECTIONS_CHECKED = False


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
    (1, "deliverables/01-datos-pca.md", 1, "Datos, auditoría de variables y PCA"),
    (2, "deliverables/02-kohonen.md", 1, "Mapa de Kohonen (SOM)"),
    (3, "deliverables/03-oja-campanas.md", 1, "Regla de Oja y decisiones de campaña"),
    (4, "deliverables/04-hopfield-letras.md", 2, "Hopfield: núcleo y letras 5×5"),
    (5, "deliverables/05-hopfield-qr.md", 2, "Hopfield: QR"),
)

QUESTIONS = (
    Question(
        "Q1.1",
        "Analizar el conjunto de datos y seleccionar qué variables serán utilizadas para resolver el problema. "
        "Para ello, se debe realizar un Exploratory Data Analysis (EDA) y un Análisis de Componentes Principales (PCA).",
        "1.1", 1, ("f1-s2", "f1-s3", "f1-s4", "f1-s6"),
    ),
    Question(
        "Q1.2",
        "Justificar si se realiza una reducción de dimensionalidad y cómo se interpretan las componentes.",
        "1.1", 1, ("f1-s5", "f1-s6", "f1-s6-1", "f1-s7"),
    ),
    Question(
        "Q1.3",
        "Variar los hiperparámetros correspondientes a la red y justificar la elección final evaluando la "
        "performance del modelo.",
        "1.2", 2, ("f2-s2", "f2-s3", "f2-s4"),
    ),
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
    Question(
        "Q1.8",
        "¿qué representa este índice?",
        "1.3", 3, ("f3-s1", "f3-s3"),
    ),
    Question(
        "Q1.9",
        "¿Cómo se puede interpretar?",
        "1.3", 3, ("f3-s3",),
    ),
    Question(
        "Q1.10",
        "¿Sería correcto elegir automáticamente al creador con el valor más alto para cualquier campaña?",
        "1.3", 3, ("f3-s3",),
    ),
    Question(
        "Q1.11",
        "Comparar el resultado con la proyección sobre PC1 obtenida mediante PCA.",
        "1.3", 3, ("f3-s2",),
    ),
    Question(
        "Q1.12",
        "Para una campaña de fútbol, ¿conviene priorizar alcance masivo, descubrimiento o profundidad educativa? "
        "Fundamentar la elección según los resultados obtenidos previamente.",
        "1.4", 3, ("f3-s5-1",),
    ),
    Question(
        "Q1.13",
        "Comparar la selección obtenida con una estrategia basada únicamente en followers. "
        "¿Qué ventajas y/o desventajas tiene cada estrategia?",
        "1.4", 3, ("f3-s5-5",),
    ),
    Question(
        "Q1.14",
        "¿Qué implica el mantenimiento del sistema desarrollado? ¿Qué ocurre cuando llega a la agencia una nueva campaña?",
        "1.4", 3, ("f3-s6",),
    ),
    Question(
        "Q1.15",
        "¿Qué cambios serían necesarios en caso de tener que actualizar la cantidad de creadores de contenido "
        "o se desean incorporar nuevas variables?",
        "1.4", 3, ("f3-s6",),
    ),
    Question(
        "Q1.16",
        "¿Qué implicancias tiene la actualización de los datos de los creadores de contenido a fin de mes?",
        "1.4", 3, ("f3-s6",),
    ),
    Question(
        "Q1.17",
        "A lo largo de todo el trabajo se deben interpretar los resultados obtenidos y en base a la evidencia "
        "tomar decisiones para las campañas de marketing de los clientes de la agencia.",
        "1.4", 3, ("f3-s5-2", "f3-s5-3", "f3-s5-4", "f3-s5-6"),
    ),
    Question(
        "Q2.1",
        "Representar cada uno mediante una matriz binaria de 37×37",
        "2.1", 5, ("f5-s2",),
    ),
    Question(
        "Q2.2",
        "Almacenar los cinco vectores en la red y construir patrones de consulta.",
        "2.1", 5, ("f5-s3", "f5-s4"),
    ),
    Question(
        "Q2.3",
        "Analizar la alteración de los códigos QR mediante la adición de ruido aleatorio con distintos niveles "
        "de ruido, simulando el deterioro de los mismos.",
        "2.1", 5, ("f5-s4", "f5-s5"),
    ),
    Question(
        "Q2.4",
        "Analizar la cantidad de iteraciones y la energía en cada paso de la red.",
        "2.1", 5, ("f5-s4",),
    ),
    Question(
        "Q2.5",
        "Explicar las limitaciones del caso de uso.",
        "2.1", 5, ("f5-s6",),
    ),
    Question(
        "Q2.6",
        "Almacenar 4 patrones de letras. Implementar el modelo de Hopfield para asociar matrices de 5×5 con los "
        "patrones de las letras almacenadas.",
        "2.2", 4, ("f4-s1", "f4-s2", "f4-s5"),
    ),
    Question(
        "Q2.7",
        "Realizar un análisis de ortogonalidad y de la capacidad de almacenamiento de la red.",
        "2.2", 4, ("f4-s4", "f4-s6"),
    ),
    Question(
        "Q2.8",
        "Ingresar un patrón muy ruidoso e identificar un estado espurio.",
        "2.2", 4, ("f4-s7",),
    ),
)

# Config and seed per step, as the "Cómo reproducir" section of each fragment and the code constants fix them.
_EDA = ("datos/creadores.csv (analysis/eda.py, sin config)", "sin seed (determinista)")
_PCA = ("datos/prepared/creadores_zscore.csv (make prepare)", "sin seed (determinista)")
_SOM = ("analysis/series_som_stage1.json", "4 (figure_seed de selection.json)")
_OJA = ("analysis/series_oja.json", "1 (la seed que produce las figuras; la serie corre las seeds 1-10)")
_CAMPAIGNS = (
    "deliverables/03-oja-campanas.md sección 4 (analysis/campaigns_select.py)",
    "1 (índice de Oja) y 4 (mapa del SOM)",
)
_LETTERS = ("deliverables/04-hopfield-letras.md sección 3 (analysis/hopfield_select.py)", "sin seed (alfabeto fijo)")
_LETTERS_SEEDS = (_LETTERS[0], "1-10")
_LETTERS_ENERGY = (_LETTERS[0], "1 (ENERGY_SEED de analysis/hopfield_figures.py)")
_QR = ("deliverables/05-hopfield-qr.md sección 3 (analysis/hopfield_qr_select.py)", "sin seed (los 5 QR son fijos)")
_QR_SEEDS = (_QR[0], "1-10")
_QR_ENERGY = (_QR[0], "1 (ENERGY_TRACE_SEED de analysis/hopfield_qr.py)")
_QR_SHIFT = (_QR[0], "1 (SHIFT_SEED de analysis/hopfield_qr_limits.py)")
_QR_MAJORITY = (_QR[0], "sin seed (atractor mayoría determinista)")

FIGURES = (
    Figure(
        key="eda_distributions", path="eda/distributions.svg", make_target="eda",
        config=_EDA[0], seed=_EDA[1], fragment=1, anchor="f1-s2",
        alt="Histogramas de las 31 variables en unidades originales, con la asimetría de cada una en el título",
        caption="Distribución de cada variable del conjunto de datos antes de estandarizar.",
        slide=False,
    ),
    Figure(
        key="eda_correlation", path="eda/correlation.svg", make_target="eda",
        config=_EDA[0], seed=_EDA[1], fragment=1, anchor="f1-s2",
        alt="Matriz de correlación de Pearson entre las 31 variables",
        caption="Correlación de Pearson entre todas las variables del conjunto de datos.",
        slide=False,
    ),
    Figure(
        key="pca_scree", path="pca/audited/scree.svg", make_target="pca",
        config=_PCA[0], seed=_PCA[1], fragment=1, anchor="f1-s6",
        alt="Autovalores con la línea de Kaiser y varianza acumulada con la línea del 80 %",
        caption="Scree de la PCA de las variables auditadas, con la regla de decisión fijada de antemano.",
        slide=True,
    ),
    Figure(
        key="pca_loadings", path="pca/audited/loadings.svg", make_target="pca",
        config=_PCA[0], seed=_PCA[1], fragment=1, anchor="f1-s6",
        alt="Cargas de las variables en las primeras componentes principales",
        caption="Qué variables pesan en cada componente principal.",
        slide=False,
    ),
    Figure(
        key="pca_biplot", path="pca/audited/biplot.svg", make_target="pca",
        config=_PCA[0], seed=_PCA[1], fragment=1, anchor="f1-s6",
        alt="Biplot de PC1 y PC2 con los creadores coloreados por su tema dominante",
        caption="Los creadores en PC1 y PC2, coloreados por tema, con las cargas de las variables.",
        slide=True,
    ),
    Figure(
        key="som_map", path="som/figures/map.svg", make_target="som-figures",
        config=_SOM[0], seed=_SOM[1], fragment=2, anchor="f2-s5",
        alt="Mapa de Kohonen de la grilla elegida: a la izquierda los creadores por neurona, a la derecha la matriz U",
        caption="Creadores por neurona (celdas rayadas: neuronas vacías) y matriz U de la grilla elegida.",
        slide=True,
    ),
    Figure(
        key="som_planes_main", path="som/figures/planes_main.svg", make_target="som-figures",
        config=_SOM[0], seed=_SOM[1], fragment=2, anchor="f2-s5",
        alt="Planos de componentes de las variables principales sobre la grilla del SOM",
        caption="Valor de cada variable principal en el prototipo de cada neurona.",
        slide=False,
    ),
    Figure(
        key="som_planes_appendix", path="som/figures/planes_appendix.svg", make_target="som-figures",
        config=_SOM[0], seed=_SOM[1], fragment=2, anchor="f2-s5",
        alt="Planos de componentes de todas las variables, entrenadas y excluidas, sobre la grilla del SOM",
        caption="Planos de componentes de todas las variables, para el apéndice.",
        slide=False,
    ),
    Figure(
        key="som_trace", path="som/figures/trace.svg", make_target="som-figures",
        config=_SOM[0], seed=_SOM[1], fragment=2, anchor="f2-s5",
        alt="Error de cuantización y error topográfico en cada época de la corrida dibujada",
        caption="Entrenamiento de la corrida dibujada: QE y TE por época.",
        slide=False,
    ),
    Figure(
        key="som_stage1_curves", path="som/figures/stage1_curves.svg", make_target="som-figures",
        config=_SOM[0], seed="1-10 (las seeds de la serie; la media y el desvío entre ellas)",
        fragment=2, anchor="f2-s3",
        alt="Seis paneles de las medidas de la etapa 1 contra el tamaño de la grilla, para vecindad escalón y gaussiana",
        caption="Por qué el error de cuantización solo no decide la grilla.",
        slide=True,
    ),
    Figure(
        key="som_regions", path="som/profiles/regions.svg", make_target="som-profiles",
        config=_SOM[0], seed=_SOM[1], fragment=2, anchor="f2-s6-1",
        alt="Mapa de Kohonen con las regiones que resultan de la regla fijada de antemano",
        caption="Las regiones de la grilla elegida.",
        slide=True,
    ),
    Figure(
        key="som_pc_planes", path="som/profiles/pc_planes.svg", make_target="som-profiles",
        config=_SOM[0], seed=_SOM[1], fragment=2, anchor="f2-s6-4",
        alt="Mapa de Kohonen coloreado por las puntuaciones en PC1 y en PC2",
        caption="Las regiones del mapa frente a PC1 y PC2 (biplot).",
        slide=True,
    ),
    Figure(
        key="oja_convergence", path="oja/convergence.svg", make_target="oja",
        config=_OJA[0], seed=_OJA[1], fragment=3, anchor="f3-s1",
        alt="Convergencia de la regla de Oja por época: la seed 1 en color y las otras en gris",
        caption="Convergencia del vector de pesos de Oja hacia el primer componente principal.",
        slide=False,
    ),
    Figure(
        key="oja_vs_pc1", path="oja/oja_vs_pc1.svg", make_target="oja",
        config=_OJA[0], seed=_OJA[1], fragment=3, anchor="f3-s2",
        alt="Índice de Oja de cada creador frente a su proyección sobre PC1",
        caption="El índice de Oja frente al score de PC1, un punto por creador.",
        slide=True,
    ),
    Figure(
        key="campaigns_biplot", path="campaigns/shortlists_biplot.svg", make_target="campaigns",
        config=_CAMPAIGNS[0], seed=_CAMPAIGNS[1], fragment=3, anchor="f3-s5-6",
        alt="Biplot de PC1 y PC2 con las listas de cada campaña marcadas",
        caption="Las listas de cada campaña sobre PC1 y PC2.",
        slide=True,
    ),
    Figure(
        key="campaigns_som", path="campaigns/shortlists_som.svg", make_target="campaigns",
        config=_CAMPAIGNS[0], seed=_CAMPAIGNS[1], fragment=3, anchor="f3-s5-6",
        alt="Mapa de Kohonen con las listas de cada campaña marcadas, una grilla por campaña",
        caption="Las listas de cada campaña sobre el mapa de Kohonen.",
        slide=True,
    ),
    Figure(
        key="letters_glyphs", path="hopfield/figures/letters.svg", make_target="hopfield-figures",
        config=_LETTERS[0], seed=_LETTERS[1], fragment=4, anchor="f4-s2",
        alt="Las 26 letras de 5×5 dibujadas como imagen, con un marco de color para las de cada set",
        caption="El alfabeto de 5×5 y las letras de los dos sets.",
        slide=True,
    ),
    Figure(
        key="letters_overlaps", path="hopfield/figures/overlaps.svg", make_target="hopfield-figures",
        config=_LETTERS[0], seed=_LETTERS[1], fragment=4, anchor="f4-s4",
        alt="Dos matrices de solapamiento entre las cuatro letras de cada set",
        caption="Solapamientos entre pares de letras del set separado y del set correlacionado.",
        slide=True,
    ),
    Figure(
        key="letters_max_overlap_hist", path="hopfield/figures/max_overlap_hist.svg", make_target="hopfield-figures",
        config=_LETTERS[0], seed=_LETTERS[1], fragment=4, anchor="f4-s4",
        alt="Histograma del máximo solapamiento entre los subconjuntos de cuatro letras",
        caption="Dónde caen los dos sets entre todos los subconjuntos de cuatro letras.",
        slide=False,
    ),
    Figure(
        key="letters_cross_terms", path="hopfield/figures/cross_terms.svg", make_target="hopfield-figures",
        config=_LETTERS[0], seed=_LETTERS[1], fragment=4, anchor="f4-s4",
        alt="Mapas de 5×5 del margen de cada píxel con el término de cruce de cada letra",
        caption="Margen de cada píxel de cada letra, con una sola escala de color.",
        slide=False,
    ),
    Figure(
        key="letters_recall_noise", path="hopfield/figures/recall_noise.svg", make_target="hopfield-figures",
        config=_LETTERS_SEEDS[0], seed=_LETTERS_SEEDS[1], fragment=4, anchor="f4-s5",
        alt="Tasa de recuperación exacta frente a los píxeles invertidos, para los dos sets",
        caption="Recuperación frente al ruido en el set separado y en el correlacionado.",
        slide=True,
    ),
    Figure(
        key="letters_energy", path="hopfield/figures/energy.svg", make_target="hopfield-figures",
        config=_LETTERS_ENERGY[0], seed=_LETTERS_ENERGY[1], fragment=4, anchor="f4-s5",
        alt="Energía de la red en cada actualización de ensayos fijados de antemano, un panel por letra y nivel de ruido",
        caption="Energía por actualización en ensayos fijados de antemano.",
        slide=False,
    ),
    Figure(
        key="letters_capacity_p4", path="hopfield/figures/capacity_p4.svg", make_target="hopfield-figures",
        config=_LETTERS_SEEDS[0], seed=_LETTERS_SEEDS[1], fragment=4, anchor="f4-s6",
        alt="Los subconjuntos de cuatro letras repartidos según su máximo solapamiento y su estabilidad",
        caption="Capacidad con cuatro patrones: los subconjuntos posibles frente a su máximo solapamiento.",
        slide=True,
    ),
    Figure(
        key="letters_capacity_by_p", path="hopfield/figures/capacity_by_p.svg", make_target="hopfield-figures",
        config=_LETTERS_SEEDS[0], seed=_LETTERS_SEEDS[1], fragment=4, anchor="f4-s6",
        alt="Estabilidad y recuperación de la red frente a la cantidad de patrones almacenados",
        caption="Estabilidad y recuperación en función del número de patrones.",
        slide=False,
    ),
    Figure(
        key="letters_spurious", path="hopfield/figures/spurious.svg", make_target="hopfield-figures",
        config=_LETTERS_SEEDS[0], seed=_LETTERS_SEEDS[1], fragment=4, anchor="f4-s7",
        alt="Tres ejemplos de consulta muy ruidosa con su estado final y sus solapamientos con las cuatro letras",
        caption="Los tres ejemplos fijados de estado espurio.",
        slide=True,
    ),
    Figure(
        key="qr_glyphs", path="hopfield/qr/figures/qr.svg", make_target="hopfield-qr-figures",
        config=_QR[0], seed=_QR[1], fragment=5, anchor="f5-s2",
        alt="Los cinco códigos QR de 37×37 como imagen",
        caption="Los cinco QR almacenados en la red.",
        slide=True,
    ),
    Figure(
        key="qr_overlaps", path="hopfield/qr/figures/overlaps.svg", make_target="hopfield-qr-figures",
        config=_QR[0], seed=_QR[1], fragment=5, anchor="f5-s2",
        alt="Matriz de solapamientos de 5×5 entre los cinco QR",
        caption="Solapamiento entre cada par de QR.",
        slide=True,
    ),
    Figure(
        key="qr_energy_trace", path="hopfield/qr/figures/energy_trace.svg", make_target="hopfield-qr-figures",
        config=_QR_ENERGY[0], seed=_QR_ENERGY[1], fragment=5, anchor="f5-s4",
        alt="Energía asíncrona paso a paso de un ensayo fijo por QR y nivel de ruido",
        caption="Energía por paso de la red de Hebb en ensayos fijados de antemano.",
        slide=True,
    ),
    Figure(
        key="qr_recovery", path="hopfield/qr/figures/recovery.svg", make_target="hopfield-qr-figures",
        config=_QR_SEEDS[0], seed=_QR_SEEDS[1], fragment=5, anchor="f5-s5",
        alt="Recuperación exacta frente al nivel de ruido para Hebb, pseudo-inversa y la línea base de Hamming",
        caption="Recuperación exacta por nivel de ruido, con las tres reglas.",
        slide=True,
    ),
    Figure(
        key="qr_majority", path="hopfield/qr/figures/majority.svg", make_target="hopfield-qr-figures",
        config=_QR_MAJORITY[0], seed=_QR_MAJORITY[1], fragment=5, anchor="f5-s6",
        alt="El atractor mayoría de Hebb comparado con cada uno de los cinco QR",
        caption="El estado común al que cae Hebb y su distancia a cada QR.",
        slide=True,
    ),
    Figure(
        key="qr_shift", path="hopfield/qr/figures/shift.svg", make_target="hopfield-qr-figures",
        config=_QR_SHIFT[0], seed=_QR_SHIFT[1], fragment=5, anchor="f5-s6",
        alt="Recuperación de un QR desplazado uno y dos píxeles bajo la pseudo-inversa",
        caption="Sensibilidad de la pseudo-inversa a corrimientos de un QR.",
        slide=True,
    ),
)


def slide_path(figure: Figure) -> str:
    """The slide variant of a report figure: the same file name inside a slide/ folder next to it."""
    head, _, name = figure.path.rpartition("/")
    return f"{head}/slide/{name}" if head else f"slide/{name}"


def figure(key: str) -> Figure:
    for item in FIGURES:
        if item.key == key:
            return item
    raise KeyError(f"no figure with key {key!r}")


# ---------- review sheet (CLI) ----------

ANCHOR_SHAPE = re.compile(r"^f(\d+)-s\d+(?:-\d+)*$")
HEADING = re.compile(r'<h([1-6]) id="([^"]+)"[^>]*>(.*?)</h\1>', re.S)


def _headings(fragment_number: int) -> dict[str, str]:
    """id -> heading text of one versioned fragment, rendered by informe.render_fragment without figures."""
    import informe  # here, not at module level: informe imports this module

    path = next((TP_DIR / item[1] for item in FRAGMENTS if item[0] == fragment_number), None)
    if path is None or not path.is_file():
        raise SystemExit(f"fragment {fragment_number} is not in FRAGMENTS or its file is missing")
    page = informe.render_fragment(path.read_text(encoding="utf-8"), fragment_number, [])
    return {
        found.group(2): " ".join(html.unescape(re.sub(r"<[^>]+>", "", found.group(3))).split())
        for found in HEADING.finditer(page)
    }


def questions_sheet() -> list[str]:
    """One line per question and one indented line per anchor with the heading of its section."""
    cache: dict[int, dict[str, str]] = {}
    lines = []
    for question in QUESTIONS:
        lines.append(f"{question.id} ({question.enunciado_section}) {question.text}")
        for anchor in question.anchors:
            shape = ANCHOR_SHAPE.match(anchor)
            if shape is None:
                raise SystemExit(f"question {question.id}: anchor {anchor} is not of the form f<n>-s<a>[-<b>]")
            number = int(shape.group(1))
            if number not in cache:
                cache[number] = _headings(number)
            if anchor not in cache[number]:
                raise SystemExit(f"question {question.id}: anchor {anchor} is not a heading of fragment {number}")
            lines.append(f"    -> {anchor} {cache[number][anchor]}")
    lines.append(
        f"QUESTIONS {len(QUESTIONS)} checked={QUESTIONS_CHECKED_AGAINST_PDF} sections_checked={ANSWER_SECTIONS_CHECKED}"
    )
    return lines


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args != ["questions"]:
        print("usage: deliverables_manifest.py questions", file=sys.stderr)
        return 2
    print("\n".join(questions_sheet()))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(TP_DIR / "analysis"))
    sys.path.insert(0, str(TP_DIR / "scripts"))
    raise SystemExit(main())
