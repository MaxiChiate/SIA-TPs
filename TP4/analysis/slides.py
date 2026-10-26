#!/usr/bin/env python3
"""The slide deck of TP4 as files ready to publish as a Slides Artifact (DELIV-01, D-01 to D-08, D-10, D-11).

    .venv/bin/python analysis/slides.py [--results DIR] [--out DIR] [--asset-map FILE]

OUTLINE is the whole narrative in method order (D-02): cover and method slide (D-07, D-03), 14 slides of exercise 1
(PCA, SOM, Oja, campaigns, closing with its own conclusions) and 8 of exercise 2 (letters, QR, closing with its own
conclusions); no agenda and no general closing (D-01, D-07). Every title states a conclusion, every number of every
title, body line, table cell and note is a `{group.key}` placeholder that facts.fill resolves from analysis/results
(D-11), and the build stops on an unknown key or a missing slide figure. The four unfavorable results have a slide of
their own with the result in the title and one line of why (D-04). A figure is the matplotlib slide variant that
plots_style writes next to each report figure (D-08), a PNG on its own light SURFACE panel (D-10); charts are never
painted in HTML. Slide files carry no colour, font or palette of their own: the Slides type applies its default
design system.

Output under --out (default analysis/results/slides, not versioned):

- `deck.json`      this build's manifest (slides with filled text, figure paths relative to the results directory,
                   the list of PNG assets to upload); not part of the Artifact tree.
- `notes.md`       the presenter script, the D-06 fallback that the informe appends as an annex (`informe --notes`).
- `project/deck.json` and `project/slides/<id>.html`   the Artifact tree 06-ARTIFACT-FORMAT.md records: a v4 index
                   and one file per slide holding exactly one <section id>, with the notes in one <aside>.
- `assets/<figure key>.png`   the slide PNGs the publish step uploads (06-12). An uploaded PNG gets a `/_blob/<id>`
                   url; `--asset-map` takes a JSON object {png name: url} and the build writes those urls verbatim
                   into the img srcs. Without it the srcs point at the copied files (`../../assets/<name>.png`),
                   enough to preview the tree locally.

Every filled text is html.escape-d; write_deck refuses a home-directory path or an email-shaped string (T-06-24,
T-06-25). Two runs write identical bytes.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

TP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TP_DIR / "scripts"))
sys.path.insert(0, str(TP_DIR / "analysis"))

import deliverables_manifest  # noqa: E402
import facts  # noqa: E402

DEFAULT_OUT = TP_DIR / "analysis" / "results" / "slides"
MAX_SLIDES = 25  # D-01: about 20 to 25 slides
HOME_PATH = re.compile(r"/Users/|/home/|[A-Za-z]:\\Users\\")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}")
SLIDE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
BLOB_URL = re.compile(r"^/_blob/[A-Za-z0-9._~-]+$")

# Copied from .planning/phases/06-slides-e-informe/06-ARTIFACT-FORMAT.md (probed_at 2026-10-25T22:10:00Z).
SLIDE_FORMAT: dict = {
    "content_unit": "one slide = project/slides/<id>.html holding exactly one <section id=\"<id>\">; "
                    "order given by the order list in project/deck.json (v4 index)",
    "canvas": (1920, 1080),
    "image_embed": "relative-file",
    "notes_supported": True,
    "notes_field": "plain text in one <aside> as the last child of the slide's <section>, max 4000 characters",
}
NOTES_MAX_CHARS = 4000
DECK_TITLE = "TP4 SIA — Grupo 9: aprendizaje no supervisado y memoria asociativa"
DECK_CREATED_AT = "2026-10-25T22:10:00Z"  # fixed so that two builds write the same bytes

# Layout in px, from section 2 of 06-ARTIFACT-FORMAT.md: 1920x1080 canvas, 128 px padding (160 at the bottom).
TEXT_W, TEXT_H = 1664, 824
GAP = 24
TITLE_PX, TITLE_LINE = 56, 67
BODY_PX, BODY_LINE = 32, 44
BULLET_PX, BULLET_LINE = 44, 60
TABLE_PX, TABLE_LINE = 28, 36
META_PX, META_LINE = 24, 32
MIN_FIGURE_H = 400
CHAR_WIDTH = 0.6  # the probe's rule: a character is about 0.6 x the font size wide
# A title wraps at spaces into lines of about TEXT_W / (0.6 x TITLE_PX) characters; two lines at 90 % fill leave room
# for a long word that moves to the next line, so the figure area below it stays at least MIN_FIGURE_H.
MAX_TITLE_CHARS = int(2 * int(TEXT_W / (CHAR_WIDTH * TITLE_PX)) * 0.9)
MAX_BODY_LINES, MAX_TABLE_COLUMNS, MAX_TABLE_ROWS = 3, 4, 5


def _key(path: str) -> str:
    """The FIGURES key whose path is `path` (the outline names figures by path, never by a guessed key)."""
    for item in deliverables_manifest.FIGURES:
        if item.path == path:
            return item.key
    raise SystemExit(f"slides.py: no entry of deliverables_manifest.FIGURES has the path {path}")


@dataclass(frozen=True)
class Slide:
    """One slide: title, body lines, table cells and notes are templates with {group.key} placeholders."""

    id: str
    exercise: int  # 0 opening, 1 and 2 as in the enunciado
    title: str
    tag: str | None
    question_ids: tuple[str, ...]
    body: tuple[str, ...]
    table: tuple[tuple[str, ...], tuple[tuple[str, ...], ...]] | None  # (header, rows)
    figure: str | None  # a FIGURES key (one figure at most) or None
    notes: str


_FAIL_ROWS = tuple((f"{{som.fail_{n}.variant}}", f"{{som.fail_{n}.te}}") for n in range(1, 6))

OUTLINE: tuple[Slide, ...] = (
    Slide(
        "portada", 0, "TP4 SIA — Grupo 9", None, (),
        ("Aprendizaje no supervisado y memoria asociativa",), None, None,
        "Presentamos los dos ejercicios del TP4: aprendizaje no supervisado sobre {oja.n_creators} creadores de "
        "contenido y memoria asociativa de Hopfield sobre letras y códigos QR. "
        "Cada título dice la conclusión y las notas de cada slide traen los números por si preguntan. "
        "El detalle completo está en el informe.",
    ),
    Slide(
        "metodo", 0, "Fijamos cada regla antes de ver los resultados y los informamos como salieron", None, (),
        (
            "Reglas escritas y commiteadas antes de correr, con guardia sha256 sobre su texto",
            "{qr.n_seeds} seeds por configuración: media y desvío, nunca una sola corrida",
            "Nulos por permutación ({som.n_permutations}) para contrastar el mapa con PC1 y PC2",
        ),
        None, None,
        "Cada regla de decisión (variables, grilla del SOM, listas de campaña, letras y protocolo de los QR) está "
        "escrita y commiteada antes de ver el resultado, y un hash sha256 de su texto impide correrla si cambió. "
        "Las seeds van de 1 a {qr.n_seeds} y se reporta la media y el desvío entre ellas, no una corrida. "
        "El SOM se contrasta con {som.n_permutations} permutaciones. "
        "Por eso los resultados poco favorables se muestran tal cual salieron, cada uno con su slide.",
    ),
    Slide(
        "pca-scree", 1, "{pca.k_80} componentes retienen {pca.cum_k80} de la varianza, pero no reducimos la dimensión",
        None, ("Q1.1", "Q1.2"),
        ("Los dos criterios coinciden: Kaiser también da {pca.kaiser} componentes",), None, _key("pca/audited/scree.svg"),
        "El conjunto auditado queda en {pca.n_features} variables y la regla de decisión se fijó antes de mirar el "
        "scree: el menor k que pasa el umbral de varianza es {pca.k_80} ({pca.cum_k80}) y Kaiser también da {pca.kaiser}. "
        "Con las columnas originales Kaiser pasa a {pca.kaiser_all31} y aparecen autovalores nulos, por eso se usa el "
        "conjunto auditado. "
        "La PCA es diagnóstica: el SOM y Oja corren sobre las {pca.n_features} variables con z-score, como pide el enunciado.",
    ),
    Slide(
        "pca-biplot", 1,
        "PC1 ({pca.var_pc1}) es un eje de tamaño y precio; PC2 ({pca.var_pc2}) sigue la audiencia argentina",
        None, ("Q1.2",), (), None, _key("pca/audited/biplot.svg"),
        "PC1 opone creadores grandes y caros, con más alcance y video corto, a creadores chicos con epígrafes largos, "
        "tutoriales y respuesta que se guarda o se comenta. "
        "PC2 se apoya en la audiencia argentina y en el tema perros. "
        "Los temas de fútbol y maquillaje aparecen recién en PC3 y PC4, fuera de este plano.",
    ),
    Slide(
        "som-rule", 1, "La grilla sale de la regla fijada, k = {som.chosen_k}, y no del menor QE (k = {som.qe_train_argmin_k})",
        "Regla fijada de antemano", ("Q1.3",), (), None, _key("som/figures/stage1_curves.svg"),
        "La regla filtra por error topográfico, neuronas vacías y creadores por neurona ocupada, y no por QE, que baja "
        "siempre al agrandar la grilla. "
        "El menor QE de entrenamiento elegiría k = {som.qe_train_argmin_k}, con muchas neuronas vacías, y la regla "
        "eligió k = {som.chosen_k}. "
        "Todas las curvas son media entre seeds y no una corrida.",
    ),
    Slide(
        "som-not-robust", 1,
        "La etapa 2 no es robusta: {som.n_failing_variants} variantes del schedule rompen el filtro de TE",
        "Regla fijada de antemano", ("Q1.3",),
        ("k = {som.chosen_k} se mantiene; lo que cambia es cuánto cumple el TE al mover el schedule",),
        (("Variante del schedule", "TE medio"), _FAIL_ROWS), None,
        "Sobre k = {som.chosen_k} se movió una cosa a la vez: el radio inicial, la tasa η0 y las épocas. "
        "En {som.n_failing_variants} variantes el error topográfico medio queda apenas sobre el máximo de la regla, "
        "mientras que la ocupación de las neuronas pasa en todas. "
        "La conclusión es que el TE de esta grilla depende del schedule y no que la ocupación se degrade, y por eso el "
        "veredicto de robustez es «no robusta».",
    ),
    Slide(
        "som-map", 1, "Las paredes altas de la matriz U separan perfiles distintos, sobre todo tamaño y precio",
        None, ("Q1.4", "Q1.7"), (), None, _key("som/figures/map.svg"),
        "El mapa de {som.chosen_k} por {som.chosen_k} muestra los creadores por neurona y, a la derecha, la matriz U: "
        "una distancia alta entre vecinas es un límite entre perfiles lejanos en las variables en z. "
        "Las paredes más altas entre neuronas ocupadas separan sobre todo por tamaño y precio, el eje de PC1, y una por "
        "tipo de contenido. "
        "En las tres hay una neurona con un solo creador, así que cada salto puede ser un caso suelto, y una pared junto "
        "a una neurona vacía es interpolación y no un límite entre grupos.",
    ),
    Slide(
        "som-one-region", 1, "Con la regla fijada el mapa da una sola región: no se parte en grupos de creadores",
        "Regla fijada de antemano", ("Q1.5",),
        ("{som.n_regions} región con los {oja.n_creators} creadores; no cambiamos el percentil para obtener más",),
        None, _key("som/profiles/regions.svg"),
        "La regla de regiones corta las aristas entre neuronas vecinas por encima de un percentil fijado de las "
        "distancias entre prototipos y descarta las que tocan neuronas vacías. "
        "Con esos cortes las neuronas ocupadas siguen conectadas, así que sale una sola región con los "
        "{oja.n_creators} creadores. "
        "Cambiar el percentil para obtener más regiones sería elegir la regla mirando el mapa, y por eso se informa como salió. "
        "La lectura útil es la de un continuo: creadores chicos y baratos arriba a la izquierda y grandes y caros abajo a la derecha.",
    ),
    Slide(
        "som-pc", 1, "El mapa coincide con PC1 (R² {som.r2_pc1}, p = {som.p_r2_pc1}) pero no con PC2 (R² {som.r2_pc2})",
        "Regla fijada de antemano", ("Q1.6",), (), None, _key("som/profiles/pc_planes.svg"),
        "La posición de la neurona ganadora explica el {som.r2_pc1_pct} de la variación de PC1, y ninguna de las "
        "{som.n_permutations} permutaciones lo alcanza (p = {som.p_r2_pc1}). "
        "Con PC2 el R² es {som.r2_pc2} y p = {som.p_r2_pc2}: una variación así de chica es habitual si se reparten al "
        "azar las posiciones. "
        "En conjunto, el orden de las distancias de la grilla coincide moderadamente con el del plano PC1-PC2 "
        "(Mantel rho {som.mantel_rho}), casi tanto como con las {pca.n_features} variables ({som.mantel_z26_rho}).",
    ),
    Slide(
        "oja-pc1", 1, "Oja aprendió PC1: su índice y el score de PC1 ordenan igual a los creadores",
        None, ("Q1.8", "Q1.11"),
        ("{oja.n_abs_cos_above} de {oja.n_seeds} seeds coinciden con PC1; mayor diferencia entre índice y score: {oja.max_abs_diff}",),
        None, _key("oja/oja_vs_pc1.svg"),
        "El índice de Oja es la proyección de cada creador sobre el vector w que aprende la neurona, y ese w coincide "
        "con el primer componente principal: entre pares de seeds el abs(cos) mínimo es {oja.abs_cos_min}. "
        "Por eso el índice y el score de PC1 ordenan a los creadores del mismo modo, salvo un error de convergencia de "
        "{oja.max_abs_diff} como máximo. "
        "El índice no agrega información que PC1 no tenga.",
    ),
    Slide(
        "oja-max", 1, "Elegir el máximo del índice no es correcto: cambia con el signo y no mira el tema",
        None, ("Q1.9", "Q1.10"),
        ("Correlación del índice con followers: Pearson {oja.corr_followers_pearson}, Spearman {oja.corr_followers_spearman}",),
        (
            ("Signo del índice", "Creador con el máximo", "Tema dominante", "Followers"),
            (
                ("Convención del proyecto", "{oja.max_id} {oja.max_name}", "{oja.max_topic}", "{oja.max_followers}"),
                ("Signo opuesto", "{oja.max_opposite_id} {oja.max_opposite_name}", "{oja.max_opposite_topic}",
                 "{oja.max_opposite_followers}"),
            ),
        ),
        None,
        "El índice es la proyección sobre PC1, un eje de tamaño y formato: con la convención del proyecto un índice alto "
        "es un creador chico, y dar vuelta el signo da el extremo opuesto. "
        "El máximo bajo cada signo es otro creador, de otro tema y de otro tamaño: {oja.max_name} con {oja.max_followers} "
        "followers contra {oja.max_opposite_name} con {oja.max_opposite_followers}. "
        "Con followers el índice tiene Pearson {oja.corr_followers_pearson} y Spearman {oja.corr_followers_spearman}, "
        "porque en esencia ordena por tamaño y no conoce el tema de la campaña. "
        "Una campaña debe filtrar primero por su tema y ordenar por su propio objetivo.",
    ),
    Slide(
        "camp-futbol", 1, "Para fútbol recomendamos profundidad: es el que más se aleja de elegir por followers",
        "Regla fijada de antemano", ("Q1.12",),
        ("Recomendación: profundidad educativa, con descubrimiento como segunda opción",),
        None, _key("campaigns/shortlists_biplot.svg"),
        "La recomendación es un juicio y no un resultado de la regla, que no elige el objetivo: para una marca de ropa de "
        "entrenamiento se empieza por profundidad educativa, descubrimiento queda segunda y alcance masivo es la menos conveniente. "
        "La lista de profundidad ({camp.futbol.top5}) comparte {camp.futbol.overlap_followers} de {camp.k} con los más "
        "seguidos y {camp.futbol.overlap_followers_tema} de {camp.k} con los más seguidos del tema. "
        "Su límite es el volumen: USD {camp.futbol.cost_per_thousand_ar} por mil argentinos, el costo más alto de las tres "
        "listas de fútbol. "
        "Si la marca fuera nueva el objetivo pasa a ser descubrimiento, y con presupuesto grande y prioridad en el volumen, alcance masivo.",
    ),
    Slide(
        "camp-table", 1, "Perros, maquillaje y arte se ordenan con su propio criterio, no con followers",
        "Regla fijada de antemano", ("Q1.17",), (),
        (
            ("Campaña", "Criterio (valor medio)", "Top 5", "USD por mil argentinos"),
            (
                ("Perros", "{camp.perros.objective}: {camp.perros.criterion}", "{camp.perros.top5}",
                 "{camp.perros.cost_per_thousand_ar}"),
                ("Maquillaje", "{camp.maquillaje.objective}: {camp.maquillaje.criterion}", "{camp.maquillaje.top5}",
                 "{camp.maquillaje.cost_per_thousand_ar}"),
                ("Arte", "{camp.arte.objective}: {camp.arte.criterion}", "{camp.arte.top5}",
                 "{camp.arte.cost_per_thousand_ar}"),
            ),
        ),
        None,
        "Cada lista sale de la regla de campaña fijada antes de calcular las listas: filtro por tema y ranking por el "
        "criterio propio. "
        "El costo por mil de la lista es USD {camp.perros.cost_per_thousand_ar} en perros, que se ordena por costo por mil, "
        "USD {camp.maquillaje.cost_per_thousand_ar} en maquillaje y USD {camp.arte.cost_per_thousand_ar} en arte, que se "
        "ordenan por profundidad y por engagement con profundidad. "
        "El costo por mil es el costo total sobre el alcance argentino total, un cociente de sumas. "
        "Son {oja.n_creators} creadores en un solo corte de datos: describimos y no probamos, y estos datos no dicen nada de ventas.",
    ),
    Slide(
        "camp-followers", 1, "Solo por followers suele salir más barato por mil, pero ignora tema y objetivo",
        None, ("Q1.13",), (),
        (
            ("Campaña", "Comparte con followers global", "Comparte con followers del tema", "USD por mil: propia / followers global"),
            tuple(
                (
                    name,
                    f"{{camp.{key}.overlap_followers}} de {{camp.k}}",
                    f"{{camp.{key}.overlap_followers_tema}} de {{camp.k}}",
                    f"{{camp.{key}.cost_per_thousand_ar}} / {{camp.{key}.followers_global_cost_per_thousand_ar}}",
                )
                for name, key in (("Fútbol", "futbol"), ("Perros", "perros"), ("Maquillaje", "maquillaje"), ("Arte", "arte"))
            ),
        ),
        None,
        "La línea base global son los {camp.k} creadores con más followers, la misma lista para las cuatro campañas, y la "
        "del tema ordena por followers pero solo entre los creadores del tema. "
        "Las listas propias comparten {camp.futbol.overlap_followers}, {camp.perros.overlap_followers}, "
        "{camp.maquillaje.overlap_followers} y {camp.arte.overlap_followers} de {camp.k} con la global en fútbol, perros, "
        "maquillaje y arte, así que el criterio cambia la lista. "
        "Elegir por followers es simple, no tiene regla que mantener y consigue más alcance total, pero es la misma lista "
        "para todas las campañas, casi no toca el tema y no mira el objetivo, por ejemplo la profundidad. "
        "Sin datos de ventas no se puede decir cuál de las dos estrategias rinde más.",
    ),
    Slide(
        "camp-maintenance", 1, "Una campaña nueva no re-entrena nada; variables nuevas obligan a rehacer el modelo",
        None, ("Q1.14", "Q1.15", "Q1.16"),
        (
            "Campaña nueva: una regla nueva sobre el mismo filtro de tema, sin re-entrenar",
            "Creador nuevo: se ubica con el scaler guardado; variables nuevas: se rehace todo",
            "Actualización mensual: se versiona el modelo y se re-entrena solo si la distancia al BMU supera el máximo de entrenamiento",
        ),
        None, None,
        "Una campaña nueva es una regla nueva sobre el mismo filtro de tema: se escribe y se commitea antes de calcular su "
        "lista, y el SOM, Oja y la PCA no se tocan. "
        "Un creador nuevo se estandariza con el scaler guardado y se ubica en su neurona ganadora, y se re-entrena solo si "
        "su distancia supera el máximo de entrenamiento ({maint.max_training_distance}), mientras que las variables nuevas "
        "cambian la dimensión y obligan a rehacer la auditoría, la PCA, el SOM y Oja. "
        "En la actualización mensual se fija la seed, se versionan el scaler, el mapa y el w de Oja, y las neuronas se "
        "rotulan por su perfil porque la orientación del mapa puede cambiar. "
        "En la demo con el creador sintético SYN001 la distancia a su neurona {maint.bmu} es {maint.distance} y el "
        "veredicto es: {maint.retrain}; es una demostración del mecanismo y no una prueba sobre creadores reales.",
    ),
    Slide(
        "ej1-conclusiones", 1, "Cada método describe y la regla de la campaña decide quién entra",
        None, (),
        (
            "PCA: {pca.n_features} variables y un eje de tamaño y precio, como diagnóstico sin reducir",
            "SOM y Oja: describen dónde cae cada lista y ninguno eligió a nadie",
            "Campañas: filtro por tema y criterio propio, fijados antes de ver las listas",
        ),
        None, None,
        "La PCA mostró un eje dominante de tamaño y precio (PC1 explica {pca.var_pc1}), pero los modelos corren sobre las "
        "{pca.n_features} variables. "
        "El SOM da un mapa continuo de perfiles, con una sola región según la regla fijada, y Oja aprende PC1 sin agregar "
        "información, por eso elegir por su índice no daría ninguna de las listas de campaña. "
        "La decisión de cada campaña sale de su regla de selección, y las lecturas con SOM, Oja y PCA describen dónde cae cada lista.",
    ),
    Slide(
        "letras", 2, "El set {letters.separated_set} casi no se solapa (máximo {letters.separated_max_overlap}); el set "
        "{letters.correlated_set} llega a {letters.correlated_max_overlap}",
        "Regla fijada de antemano", ("Q2.6", "Q2.7"),
        ("Con N = {letters.n_pixels} píxeles ningún par de letras es exactamente ortogonal",),
        None, _key("hopfield/figures/letters.svg"),
        "El alfabeto son las 26 mayúsculas dibujadas a mano en 5×5, y la regla elige, solo con los bitmaps, el set más "
        "separado ({letters.separated_set}) y el más correlacionado ({letters.correlated_set}) entre todos los "
        "subconjuntos de cuatro letras. "
        "Con N = {letters.n_pixels} el producto escalar es siempre impar, así que ningún par es exactamente ortogonal: el "
        "máximo solapamiento es {letters.separated_max_overlap} en el primero y {letters.correlated_max_overlap} en el segundo. "
        "Una divulgación: 25 de los 26 glifos coinciden con un borrador que se usó en un prototipo, y el desempate del set "
        "correlacionado no es independiente de él.",
    ),
    Slide(
        "letras-ruido", 2, "El set separado resiste el ruido; el correlacionado nunca pasa de {letters.correlated_recall_k3}",
        "Regla fijada de antemano", ("Q2.7",),
        ("Recuperación exacta con 3, 6 y 9 píxeles invertidos en el set separado: {letters.separated_recall_k3}, "
         "{letters.separated_recall_k6} y {letters.separated_recall_k9}",),
        None, _key("hopfield/figures/recall_noise.svg"),
        "Recuperar es llegar exactamente a la letra de la consulta: en el set separado la tasa es "
        "{letters.separated_recall_k3} con 3 píxeles invertidos, {letters.separated_recall_k6} con 6 y "
        "{letters.separated_recall_k9} con 9. "
        "En el correlacionado solo {letters.correlated_n_stable} de las 4 letras es punto fijo y las otras caen sobre ella, "
        "de ahí el techo de {letters.correlated_recall_k3}. "
        "La capacidad con p = 4 depende de cuánto se solapen las letras: {letters.p4_all_stable_fraction} de los "
        "subconjuntos posibles de cuatro letras las tienen todas estables, y la fracción estable media es "
        "{letters.p4_mean_stable_fraction}.",
    ),
    Slide(
        "espurio", 2, "Con mucho ruido la red cae en estados espurios: {letters.spur_total_pct} de los ensayos",
        "Regla fijada de antemano", ("Q2.8",),
        ("{letters.spur_trials} ensayos: inverso {letters.spur_inverse_pct}, mezcla {letters.spur_mixture_pct}, "
         "otro {letters.spur_other_pct}",),
        None, _key("hopfield/figures/spurious.svg"),
        "Con ruido alto sobre el set separado (10 a 12 píxeles invertidos de 25), {letters.spur_total} de "
        "{letters.spur_trials} ensayos ({letters.spur_total_pct}) terminan en un estado que no es una letra almacenada. "
        "Las clases son inverso ({letters.spur_inverse_pct}), mezcla ({letters.spur_mixture_pct}) y otro "
        "({letters.spur_other_pct}), y la más frecuente es la del {letters.spurious_class}. "
        "Un inverso tiene la misma energía que su letra, porque la energía no cambia al invertir todo el patrón, mientras "
        "que la mezcla y el otro quedan en mínimos locales más altos; son tres ejemplos fijados y no una ley sobre la "
        "energía de los estados espurios.",
    ),
    Slide(
        "qr-correlados", 2, "Los QR son idénticos en {qr.identical_fraction} de sus píxeles: están muy correlacionados",
        None, ("Q2.1", "Q2.2"),
        ("Matrices binarias de 37×37 ({qr.n_pixels} píxeles); solapamiento máximo {qr.max_abs_overlap}, medio {qr.mean_abs_overlap}",),
        None, _key("hopfield/qr/figures/qr.svg"),
        "Cada QR es una matriz binaria de 37×37 de módulos oscuros y claros, como pide la pregunta, y son {qr.n_qr} "
        "almacenados en una sola red. "
        "Como codificación de este trabajo, y no como parte del enunciado, la red guarda cada matriz como un vector de "
        "{qr.n_pixels} valores ±1, con la polaridad oscuro = +1 y claro = −1. "
        "El {qr.identical_fraction} de los {qr.n_pixels} píxeles es idéntico en los {qr.n_qr} a la vez y el solapamiento "
        "entre pares es {qr.max_abs_overlap} como máximo y {qr.mean_abs_overlap} en promedio, lejos de la ortogonalidad.",
    ),
    Slide(
        "qr-hebb-falla", 2, "Hebb recupera {qr.hebb_exact_noise0} de los QR, ni siquiera sin ruido",
        "Regla fijada de antemano", ("Q2.3",),
        ("Cae siempre al mismo estado: la mayoría píxel a píxel de los {qr.n_qr} QR",),
        None, _key("hopfield/qr/figures/majority.svg"),
        "Con el protocolo fijado de antemano la tasa de recuperación exacta de Hebb es {qr.hebb_exact_noise0} en todos los "
        "niveles de ruido, el nivel cero incluido: los {qr.n_qr} QR no son puntos fijos de la regla de Hebb. "
        "La causa es la correlación entre los QR, con solapamiento medio {qr.mean_abs_overlap}: la red converge a un único "
        "estado, la mayoría píxel a píxel de los cinco, que difiere de cada QR por entre {qr.majority_hamming_min} y "
        "{qr.majority_hamming_max} píxeles de {qr.n_pixels}. "
        "Es el resultado de la regla tal como se fijó y se informa así.",
    ),
    Slide(
        "qr-lookup", 2, "Un lookup de Hamming iguala o supera a la pseudo-inversa con ruido alto",
        "Regla fijada de antemano", ("Q2.3",),
        ("Con ruido alto (nivel {qr.noise_high}): Hamming {qr.hamming_at_0_45}, pseudo-inversa {qr.pinv_at_0_45}",),
        None, _key("hopfield/qr/figures/recovery.svg"),
        "La pseudo-inversa sí guarda los {qr.n_qr} QR: recupera {qr.pinv_exact_noise0} sin ruido y se mantiene así hasta "
        "el nivel {qr.pinv_last_full_noise}. "
        "Pero la línea base de Hamming, un 1-NN sin dinámica, queda por encima de ella con ruido alto: {qr.hamming_at_0_45} "
        "contra {qr.pinv_at_0_45} en el nivel {qr.noise_high} y {qr.hamming_at_0_50} contra {qr.pinv_at_0_50} en el último nivel. "
        "Con cinco patrones conocidos de antemano, la ventaja de Hopfield frente a una tabla de búsqueda no está en la tasa de acierto.",
    ),
    Slide(
        "qr-energia", 2, "La energía baja en cada paso y la red converge, pero al estado común y no al QR",
        None, ("Q2.4", "Q2.5"),
        ("Ensayos fijos por QR y nivel de ruido: la energía asíncrona nunca sube",),
        None, _key("hopfield/qr/figures/energy_trace.svg"),
        "La figura traza la energía asíncrona, paso a paso, de un ensayo fijo por QR y nivel de ruido, y en todos los "
        "ensayos trazados la energía nunca sube. "
        "Cada corrida converge, pero al estado común y no al QR consultado, y la energía final por sí sola no distingue un "
        "estado recuperado de uno que no lo es. "
        "El número de barridos crece poco con el ruido, y una limitación es la sensibilidad a corrimientos: con un solo "
        "píxel de corrimiento la consulta ya está a {qr.shift1_query_hamming} de {qr.n_pixels} píxeles de la fuente y la "
        "pseudo-inversa la deja a {qr.shift1_recovered_hamming}.",
    ),
    Slide(
        "ej2-conclusiones", 2, "Hopfield para QR: la correlación rompe Hebb y un lookup resuelve el mismo problema",
        None, ("Q2.5",),
        (
            "Correlación entre los QR: Hebb converge a un atractor común",
            "Sensibilidad a corrimientos de uno o dos píxeles y matriz de {qr.n_pixels} por {qr.n_pixels} pesos para {qr.n_qr} patrones",
            "No verificamos que un QR recuperado se decodifique",
        ),
        None, None,
        "Las limitaciones medidas son tres: la correlación entre los QR ({qr.mean_abs_overlap} de solapamiento medio) rompe "
        "a Hebb, un corrimiento de un solo píxel ya mueve la consulta a {qr.shift1_query_hamming} de {qr.n_pixels} píxeles, "
        "y la matriz de pesos tiene {qr.n_pixels} por {qr.n_pixels} entradas para solo {qr.n_qr} patrones. "
        "Un lookup de Hamming resuelve el mismo problema cerrado con igual o más acierto y sin dinámica ni energía. "
        "Tampoco verificamos que un QR recuperado se decodifique, porque no corrimos ningún decodificador y el formato QR "
        "ya trae su propia corrección de errores, y el daño estructurado, como un rayón, no se midió.",
    ),
)

# Slide figures that are on no slide: the D-01 budget of 24 slides leaves no room for them, their slide variants
# exist so that a later outline edit can swap one in without touching figure code, and each stays in the informe.
UNPLACED_SLIDE_FIGURES: dict[str, str] = {
    _key("campaigns/shortlists_som.svg"):
        "las cuatro slides de campaña están fijadas por D-05 (fútbol sobre el biplot, dos tablas y mantenimiento); "
        "la vista de las listas sobre el SOM queda en el fragmento 03",
    _key("hopfield/figures/overlaps.svg"):
        "la ortogonalidad de los dos sets de letras se da como números en la slide letras",
    _key("hopfield/figures/capacity_p4.svg"):
        "la slide letras-ruido muestra la recuperación frente al ruido; la capacidad con p = 4 queda en el fragmento 04 "
        "y se nombra en las notas de esa slide",
    _key("hopfield/qr/figures/overlaps.svg"):
        "la slide qr-correlados muestra los QR y da los solapamientos como números de facts",
    _key("hopfield/qr/figures/shift.svg"):
        "la limitación del corrimiento se nombra en las notas de qr-energia y ej2-conclusiones; la figura queda en el fragmento 05",
}


def slide_templates(slide: Slide) -> list[str]:
    """Every text template of a slide: title, body lines, table cells and notes."""
    texts = [slide.title, *slide.body, slide.notes]
    if slide.table is not None:
        texts.extend(slide.table[0])
        texts.extend(cell for row in slide.table[1] for cell in row)
    return texts


# ---------- build ----------

def _figure_files(figure_key: str) -> tuple[str, str]:
    """Results-relative paths of the slide SVG and of the PNG that is uploaded."""
    svg = deliverables_manifest.slide_path(deliverables_manifest.figure(figure_key))
    return svg, str(Path(svg).with_suffix(".png"))


def build_deck(values: dict[str, str], results_dir: Path = facts.RESULTS_DIR) -> list[dict]:
    """The outline with every template filled from the facts and every figure resolved to its slide variant."""
    if len(OUTLINE) > MAX_SLIDES:
        raise SystemExit(f"the outline has {len(OUTLINE)} slides; D-01 allows {MAX_SLIDES} at most")
    built = []
    for slide in OUTLINE:
        if len(slide.body) > MAX_BODY_LINES:
            raise SystemExit(f"slide {slide.id}: {len(slide.body)} líneas de cuerpo; el máximo es {MAX_BODY_LINES}")
        if slide.table is not None and (len(slide.table[0]) > MAX_TABLE_COLUMNS or len(slide.table[1]) > MAX_TABLE_ROWS):
            raise SystemExit(
                f"slide {slide.id}: la tabla supera {MAX_TABLE_COLUMNS} columnas o {MAX_TABLE_ROWS} filas"
            )
        fill = lambda text: facts.fill(text, values)  # noqa: E731
        table = None
        if slide.table is not None:
            table = {"header": [fill(cell) for cell in slide.table[0]], "rows": [[fill(cell) for cell in row] for row in slide.table[1]]}
        figure_path = png = None
        if slide.figure is not None:
            item = deliverables_manifest.figure(slide.figure)
            figure_path, png_path = _figure_files(slide.figure)
            for relative in (figure_path, png_path):
                if not (Path(results_dir) / relative).is_file():
                    raise SystemExit(
                        f"slide {slide.id}: figure {relative} not found; run `make results` (step {item.make_target})"
                    )
            png = f"{slide.figure}.png"
        title = fill(slide.title)
        if len(title) > MAX_TITLE_CHARS or _wrap_lines(title, _chars(TITLE_PX)) > 2:
            raise SystemExit(
                f"slide {slide.id}: el título tiene {len(title)} caracteres; el máximo es {MAX_TITLE_CHARS} (dos líneas)"
            )
        built.append({
            "id": slide.id,
            "exercise": slide.exercise,
            "title": title,
            "tag": slide.tag,
            "question_ids": list(slide.question_ids),
            "body": [fill(line) for line in slide.body],
            "table": table,
            "figure": slide.figure,
            "figure_path": figure_path,
            "png": png,
            "notes": fill(slide.notes),
        })
    return built


# ---------- layout ----------

def _wrap_lines(text: str, max_chars: int) -> int:
    """Lines a text takes when wrapped greedily at spaces into lines of at most `max_chars` characters."""
    lines, used = 1, 0
    for word in text.split():
        if used and used + 1 + len(word) > max_chars:
            lines, used = lines + 1, len(word)
        else:
            used = used + 1 + len(word) if used else len(word)
    return lines


def _chars(px: int, width: int = TEXT_W) -> int:
    return int(width / (CHAR_WIDTH * px))


def _figure_height(slide: dict) -> int:
    """Height left for the figure under the title, the body lines and the meta line (flex column with GAP)."""
    items = [_wrap_lines(slide["title"], _chars(TITLE_PX)) * TITLE_LINE]
    body = sum(_wrap_lines(line, _chars(BODY_PX)) * BODY_LINE for line in slide["body"])
    if body:
        items.append(body)
    if slide["tag"] or slide["question_ids"]:
        items.append(META_LINE)
    items.append(0)  # the figure itself
    return TEXT_H - sum(items) - GAP * (len(items) - 1)


def _table_html(table: dict) -> str:
    columns = len(table["header"])
    weights = [
        min(max(10, max(len(row[col]) for row in [table["header"], *table["rows"]])), 70) for col in range(columns)
    ]
    usable = TEXT_W - 32 * columns
    widths = [round(usable * weight / sum(weights)) for weight in weights]
    widths[-1] += usable - sum(widths)
    cell = f"padding:12px 16px;text-align:left;font-size:{TABLE_PX}px;line-height:{TABLE_LINE}px;"
    head = "".join(
        f'<th style="width:{width}px;{cell}border-bottom:2px solid;">{html.escape(text)}</th>'
        for width, text in zip(widths, table["header"])
    )
    rows = "".join(
        "<tr>" + "".join(
            f'<td style="width:{width}px;{cell}border-bottom:1px solid;">{html.escape(text)}</td>'
            for width, text in zip(widths, row)
        ) + "</tr>"
        for row in table["rows"]
    )
    return f'<table style="width:{TEXT_W}px;border-collapse:collapse;"><tr>{head}</tr>{rows}</table>'


def _image_source(slide: dict, fmt: dict, results_dir: Path, asset_map: dict | None) -> str | None:
    if slide["png"] is None or fmt["image_embed"] == "none":
        return None
    if fmt["image_embed"] in ("data-uri", "both"):
        data = (Path(results_dir) / Path(slide["figure_path"]).with_suffix(".png")).read_bytes()
        return "data:image/png;base64," + base64.b64encode(data).decode("ascii")
    if asset_map is not None:
        return asset_map[slide["png"]]
    return f"../../assets/{slide['png']}"


def _slide_html(slide: dict, fmt: dict, results_dir: Path, asset_map: dict | None) -> str:
    esc = html.escape
    parts: list[str] = []
    cover = slide["id"] == "portada"
    if cover:
        parts.append(f'<h1 style="font-size:120px;line-height:132px;">{esc(slide["title"])}</h1>')
        parts.extend(f'<p style="font-size:{BULLET_PX}px;line-height:{BULLET_LINE}px;">{esc(line)}</p>' for line in slide["body"])
    else:
        parts.append(f'<h2 style="font-size:{TITLE_PX}px;line-height:{TITLE_LINE}px;">{esc(slide["title"])}</h2>')
        text_only = slide["figure"] is None and slide["table"] is None
        if slide["body"] and text_only:
            items = "".join(f"<li>{esc(line)}</li>" for line in slide["body"])
            parts.append(f'<ul style="font-size:{BULLET_PX}px;line-height:{BULLET_LINE}px;padding-left:48px;">{items}</ul>')
        else:
            parts.extend(
                f'<p style="font-size:{BODY_PX}px;line-height:{BODY_LINE}px;">{esc(line)}</p>' for line in slide["body"]
            )
        if slide["table"] is not None:
            parts.append(_table_html(slide["table"]))
        source = _image_source(slide, fmt, results_dir, asset_map)
        if source is not None:
            height = _figure_height(slide)
            if height < MIN_FIGURE_H:
                raise SystemExit(f"slide {slide['id']}: only {height} px are left for the figure (minimum {MIN_FIGURE_H})")
            alt = esc(deliverables_manifest.figure(slide["figure"]).alt, quote=True)
            parts.append(
                f'<img src="{esc(source, quote=True)}" alt="{alt}" '
                f'style="width:{TEXT_W}px;height:{height}px;object-fit:contain;">'
            )
        meta = []
        if slide["tag"]:
            meta.append(f'<p style="font-size:{META_PX}px;line-height:{META_LINE}px;">{esc(slide["tag"])}</p>')
        if slide["question_ids"]:
            asked = ", ".join(slide["question_ids"])
            meta.append(f'<p style="font-size:{META_PX}px;line-height:{META_LINE}px;">Responde: {esc(asked)}</p>')
        if meta:
            parts.append(f'<div style="display:flex;gap:48px;">{"".join(meta)}</div>')
    if fmt["notes_supported"]:
        parts.append(f"<aside>{esc(slide['notes'])}</aside>")
    style = f"display:flex;flex-direction:column;gap:{GAP}px;padding:128px 128px 160px;"
    if cover:
        style += "justify-content:center;"
    return f'<section id="{esc(slide["id"], quote=True)}" style="{style}">' + "".join(parts) + "</section>\n"


# ---------- write ----------

def _json(payload) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _check_text(text: str, where: str) -> None:
    """T-06-25: nothing written may carry a home-directory path or an email-shaped string."""
    if HOME_PATH.search(text):
        raise SystemExit(f"{where}: refusing to write a home-directory path")
    if EMAIL.search(text):
        raise SystemExit(f"{where}: refusing to write an email-shaped string")


def _sections(deck: list[dict]) -> dict:
    names = {
        0: ("inicio", "Portada y método"),
        1: ("ejercicio-1", "Ejercicio 1: PCA, SOM, Oja y campañas"),
        2: ("ejercicio-2", "Ejercicio 2: Hopfield con letras y QR"),
    }
    out = {}
    for exercise, (key, description) in names.items():
        first = next((slide["id"] for slide in deck if slide["exercise"] == exercise), None)
        if first is not None:
            out[key] = {"description": description, "start": first}
    return out


def _notes_md(deck: list[dict]) -> str:
    lines = ["# Guion de la presentación", ""]
    for number, slide in enumerate(deck, start=1):
        lines += [f"## {number}. {slide['title']}", "", slide["notes"], ""]
    return "\n".join(lines)


def write_deck(
    deck: list[dict],
    out_dir: Path,
    fmt: dict = SLIDE_FORMAT,
    results_dir: Path = facts.RESULTS_DIR,
    asset_map: dict | None = None,
) -> None:
    """Write deck.json, notes.md, the v4 index, one file per slide and the PNG assets, as 06-ARTIFACT-FORMAT.md lays them out."""
    out = Path(out_dir)
    results = Path(results_dir)
    for slide in deck:
        if not SLIDE_ID.match(slide["id"]):
            raise SystemExit(f"slide id {slide['id']!r} does not match [A-Za-z0-9_-]{{1,64}}")
        if fmt["notes_supported"] and len(slide["notes"]) > NOTES_MAX_CHARS:
            raise SystemExit(f"slide {slide['id']}: notes have {len(slide['notes'])} characters; the cap is {NOTES_MAX_CHARS}")
    if asset_map is not None and fmt["image_embed"] == "relative-file":
        for slide in deck:
            if slide["png"] is None:
                continue
            url = asset_map.get(slide["png"])
            if url is None:
                raise SystemExit(f"asset map has no url for {slide['png']}; upload it and add it to the map")
            if not BLOB_URL.match(str(url)):
                raise SystemExit(f"asset map url for {slide['png']} is not a /_blob/<id> url: {url!r}")

    files: dict[Path, str] = {}
    assets = [
        {"file": f"assets/{slide['png']}", "png": slide["png"], "slide": slide["id"], "source": str(Path(slide["figure_path"]).with_suffix(".png"))}
        for slide in deck if slide["png"]
    ]
    files[out / "deck.json"] = _json({
        "assets": assets,
        "format": {key: fmt[key] for key in ("canvas", "image_embed", "notes_supported")},
        "slides": deck,
    })
    files[out / "notes.md"] = _notes_md(deck)
    files[out / "project" / "deck.json"] = _json({
        "v": 4,
        "createdOnFiles": {"v": 1, "at": DECK_CREATED_AT},
        "lists": "css",
        "title": DECK_TITLE,
        "cover": deck[0]["id"],
        "order": [slide["id"] for slide in deck],
        "sections": _sections(deck),
        "faces": {},
        "designSystems": [],
    })
    for slide in deck:
        files[out / "project" / "slides" / f"{slide['id']}.html"] = _slide_html(slide, fmt, results, asset_map)
    for path, text in files.items():
        _check_text(text, str(path.relative_to(out)))

    for stale in (out / "project" / "slides", out / "assets"):
        if stale.is_dir():
            shutil.rmtree(stale)
    for path, text in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    for item in assets:
        target = out / item["file"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(results / item["source"], target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results", type=Path, default=facts.RESULTS_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--asset-map", type=Path, default=None, help="JSON object {png name: /_blob/<id>} written verbatim into the img srcs")
    args = parser.parse_args(argv)
    asset_map = None
    if args.asset_map is not None:
        if not args.asset_map.is_file():
            raise SystemExit(f"{args.asset_map} not found; --asset-map takes the JSON file of the uploaded assets")
        asset_map = json.loads(args.asset_map.read_text(encoding="utf-8"))
    deck = build_deck(facts.load_facts(args.results), args.results)
    write_deck(deck, args.out, SLIDE_FORMAT, args.results, asset_map)
    try:
        shown = args.out.resolve().relative_to(TP_DIR)
    except ValueError:
        shown = args.out
    print(f"slides -> {shown} ({len(deck)} slides)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
