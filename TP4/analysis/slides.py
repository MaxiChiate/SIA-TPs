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
MAX_SLIDES = 30  # D-01 said 20 to 25; slides added after the review of the enunciado (EDA, zones, capacity), the Ej. 1 recap dropped
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
MAX_BODY_LINES, MAX_TABLE_COLUMNS, MAX_TABLE_ROWS = 3, 6, 7


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
        "eda", 1,
        "Salen {prune.r4.n_out_total} variables ({eda.n_dropped} triviales y {prune.r4.n_out} con |r| ≥ {prune.r4.tau}) y quedan {prune.r4.n}",
        None, (), (), None, _key("eda/correlation.svg"),
        "Primero salen {eda.n_dropped} variables triviales, que son combinación exacta de otras (precio en pesos, "
        "publicaciones orgánicas, engagement total y el tema y el tipo de contenido que completan su grupo), porque "
        "vuelven singular la matriz de correlación. "
        "La matriz muestra las {prune.n_audited} variables restantes: en negrita los pares con correlación en valor absoluto "
        "de al menos {prune.r4.tau}, que es el umbral con el que consideramos redundantes a dos variables, y en rojo las "
        "{prune.r4.n_out} que salen, la de mayor correlación media con las demás en cada par. "
        "El umbral lo fijamos como equipo y no sale de la teoría del curso. "
        "Quedan {prune.r4.n} variables estandarizadas con z-score, y followers y el alcance estimado en Argentina se "
        "conservan las dos porque quedan apenas por debajo del umbral.",
    ),
    Slide(
        "pca-eigenvalues", 1, "{pca17.k_80} componentes retienen {pca17.cum_k80} de la varianza, pero no reducimos la dimensión",
        None, ("Q1.1", "Q1.2"),
        (), None, _key("pca/pruned/eigenvalues_variance.svg"),
        "Sin las variables redundantes quedan {pca17.n_features} y la regla de decisión se fijó antes de mirar el "
        "gráfico: el menor k que pasa el umbral de varianza acumulada es {pca17.k_80} ({pca17.cum_k80}), y ese umbral es una "
        "convención del equipo. "
        "Con las 26 variables de antes eran {pca.k_80} componentes y {pca.cum_k80}, así que quitar las redundantes no cambia la "
        "conclusión de no reducir. "
        "La PCA es diagnóstica: el SOM y Oja se rehacen sobre estas {pca17.n_features} variables con z-score, como pide el enunciado.",
    ),
    Slide(
        "pca-biplot", 1,
        "PC1 ({pca17.var_pc1}) opone tamaño a guardados y comentarios; PC2 ({pca17.var_pc2}) sigue el patrocinio",
        None, ("Q1.2",), (), None, _key("pca/pruned/biplot.svg"),
        "Las flechas del biplot son las cargas (loadings) de cada variable, y que PC1 oponga dos grupos significa que sus "
        "cargas tienen signo contrario (se nombran las de {pca17.loading_min} o más en valor absoluto): positivas para {pca17.pc1_pos} y "
        "negativas para {pca17.pc1_neg}, de modo que un creador con PC1 alto tiene mucho de lo primero y poco de lo "
        "segundo, y con PC1 bajo pasa al revés. "
        "PC2 opone {pca17.pc2_pos}, con cargas positivas, a {pca17.pc2_neg}, con cargas negativas, y el signo global "
        "de una componente es arbitrario: lo que importa es que los dos grupos tengan signos opuestos. "
        "Sin precio ni las variables de alcance y de formato, que salieron por redundantes, PC1 ya no es un eje de tamaño y "
        "precio, y con {pca17.n_features} variables, PC1 y PC2 retienen {pca17.cum_pc2} de la varianza.",
    ),
    Slide(
        "pca-prune", 1,
        "Podar con |r| ≥ {prune.r4.tau} deja {prune.r4.n} de {prune.n_audited} variables y PC1 baja a {prune.r4.pc1}",
        None, ("Q1.1",),
        ("Elegimos {prune.r4.tau}; el SOM, Oja y las campañas todavía no se rehicieron con ese conjunto",),
        (
            ("Umbral de |r|", "Variables que quedan", "Componentes para el {prune.variance_threshold}", "Varianza de PC1", "Número de condición", "Qué pasa"),
            (
                ("{prune.r1.tau}", "{prune.r1.n}", "{prune.r1.k80}", "{prune.r1.pc1}", "{prune.r1.cond}",
             "Salen duplicados de alcance y formato"),
                ("{prune.r2.tau}", "{prune.r2.n}", "{prune.r2.k80}", "{prune.r2.pc1}", "{prune.r2.cond}",
             "Sale también el alcance promedio"),
                ("{prune.r3.tau}", "{prune.r3.n}", "{prune.r3.k80}", "{prune.r3.pc1}", "{prune.r3.cond}",
             "Mismo conjunto que con el umbral anterior"),
                ("{prune.r4.tau}", "{prune.r4.n}", "{prune.r4.k80}", "{prune.r4.pc1}", "{prune.r4.cond}",
             "Sale price_usd, justo en el borde"),
                ("{prune.r5.tau}", "{prune.r5.n}", "{prune.r5.k80}", "{prune.r5.pc1}", "{prune.r5.cond}",
             "Sale followers: queda el alcance estimado"),
                ("{prune.r6.tau}", "{prune.r6.n}", "{prune.r6.k80}", "{prune.r6.pc1}", "{prune.r6.cond}",
             "Se achica el engagement por mil"),
                ("{prune.r7.tau}", "{prune.r7.n}", "{prune.r7.k80}", "{prune.r7.pc1}", "{prune.r7.cond}",
             "Sin tamaño ni engagement por mil")
            ),
        ),
        None,
        "Además de las dependencias exactas probamos podar por correlación sobre las {prune.n_audited} variables auditadas: "
        "en cada umbral sale, del par más correlacionado en valor absoluto, la variable con mayor correlación media con las "
        "demás, hasta que ningún par llega al umbral, y después se repite la PCA. "
        "Cuanto más bajo el umbral, menos variables, menos varianza en PC1 y una matriz más estable: el número de condición "
        "baja de {prune.r1.cond} con {prune.r1.tau} a {prune.r7.cond} con {prune.r7.tau}, y el menor autovalor sube de "
        "{prune.r1.lmin} a {prune.r7.lmin}. "
        "Con {prune.r4.tau} quedan {prune.r4.n} variables, PC1 explica {prune.r4.pc1} y hacen falta {prune.r4.k80} "
        "componentes para el umbral de varianza (columna «Componentes para el {prune.variance_threshold}»); con {prune.r5.tau} sale followers y el tamaño queda solo en el alcance "
        "estimado en Argentina, y con {prune.r7.tau} no queda ni tamaño ni engagement por mil. "
        "El umbral es una decisión del equipo y no sale de la teoría del curso, price_usd sale con {prune.r4.tau} justo sobre el "
        "borde, y solo la PCA se calculó con cada umbral: el SOM, Oja y las campañas se rehacen únicamente con el elegido.",
    ),
    Slide(
        "som-hyperparams", 1, "Hiperparámetros del SOM y por qué los elegimos",
        None, ("Q1.3",),
        ("Inicializamos los pesos de las neuronas con muestras elegidas al azar de los datos de entrenamiento porque, "
         "con valores aleatorios, algunas neuronas quedan lejos de los datos, nunca ganan y quedan muertas.",
         "Descartamos las grillas con más de {som.empty_max} de neuronas vacías o con menos de {som.creators_min} "
         "creadores por neurona ocupada (en promedio entre las seeds).",
         "En cada iteración t el radio y la tasa bajan de forma exponencial: R(t) = R0 · ({som.base_radius_final} / R0)"
         "^(t / (T − 1)) y η(t) = η0 · ({som.base_eta_final} / η0)^(t / (T − 1)), con T los pasos de entrenamiento."),
        (
            ("Hiperparámetro", "Valor", "Por qué"),
            (
                ("Grilla", "{som.chosen_k} × {som.chosen_k}",
                 "La eligió la regla fijada de antemano: es la más grande entre las grillas que cumplen la ocupación"),
                ("Radio inicial R0", "{som.base_radius0}",
                 "Baseline fijado de antemano (la mitad de k); con otros valores la elección no cambia"),
                ("Tasa de aprendizaje inicial η0", "{som.base_eta0}",
                 "Menor que 1, como pide el curso; con η0 entre {som.eta_lo} y {som.eta_hi} la elección no cambia"),
                ("Épocas", "{som.base_epochs}",
                 "Baseline fijado de antemano; con 50 a 1040 épocas la ocupación no se degrada"),
            ),
        ),
        None,
        "Estos son los hiperparámetros del mapa que usamos en todo el ejercicio, y los pesos de cada neurona arrancan en "
        "un creador elegido al azar del conjunto de entrenamiento: con valores aleatorios hay neuronas que quedan lejos "
        "de los datos, nunca ganan y quedan muertas. "
        "La grilla la eligió la regla fijada de antemano, que descarta las grillas con más de {som.empty_max} de "
        "neuronas vacías o con menos de {som.creators_min} creadores por neurona ocupada y se queda con la más "
        "grande, y el resto del schedule es el baseline de la serie, también fijado antes de correr. "
        "El radio y la tasa los actualizamos en cada iteración con una bajada exponencial hasta R = "
        "{som.base_radius_final} y η = {som.base_eta_final}: la teoría pide que R tienda a 1 y como entrenamos un "
        "número finito de pasos llega a 1 en el último, y por eso el radio final y η final no son hiperparámetros "
        "sino el punto de llegada de la bajada. "
        "Después de elegir la grilla movimos una cosa a la vez (R0, η0 y épocas) con 10 seeds cada una, y en todas las "
        "variantes la ocupación pasa los filtros, así que la elección es robusta, y el mapa se entrena con los "
        "scores de las {pca17.k_80} primeras componentes de la PCA.",
    ),
    Slide(
        "som-k", 1, "k = {som.chosen_k} es la grilla más grande que cumple los dos límites de ocupación",
        None, ("Q1.3",), (), None, _key("som/figures/effect_k.svg"),
        "Cada punto es la media de 10 entrenamientos con distinta seed y las barras son el desvío entre ellas; el error "
        "topográfico es la fracción de creadores cuya neurona más cercana y la segunda más cercana no son vecinas en "
        "la grilla, así que mide si el mapa conserva la vecindad, que es justamente lo que busca Kohonen. "
        "Con k = {som.chosen_k} el error topográfico es {som.chosen_te}, sobre el límite de {som.te_max}, y ninguna "
        "grilla cumplió a la vez los tres límites: las que cumplen el error topográfico tienen demasiadas neuronas "
        "vacías, así que la regla quitó ese límite como decía de antemano. "
        "Con k = {som.chosen_k} hay {som.chosen_empty} de neuronas vacías (límite {som.empty_max}, la línea punteada) y "
        "{som.chosen_creators} creadores por neurona ocupada (mínimo {som.creators_min}, también punteada), y con "
        "k = {som.k_next} ya son {som.k_next_empty} y {som.k_next_creators}. "
        "Entre las grillas que cumplen los límites de ocupación, k = {som.chosen_k} es la más grande, y esa es la que "
        "usamos.",
    ),
    Slide(
        "som-eta0", 1, "Con η0 entre {som.eta_lo} y {som.eta_hi} el mapa casi no cambia",
        None, ("Q1.3",), (), None, _key("som/figures/effect_eta0.svg"),
        "Probamos η0 = {som.eta_values}, con k = {som.chosen_k} y el resto igual, y cada punto es la media de 10 "
        "entrenamientos con distinta seed y las barras son el desvío entre ellas; η0 es cuánto se mueve la neurona "
        "ganadora hacia el creador en los primeros pasos y después decae hasta {som.base_eta_final}. "
        "La distancia de cada creador a su neurona ganadora queda entre {som.eta_dist_min} y {som.eta_dist_max} y la "
        "U media, que es el promedio de la matriz U (la distancia entre neuronas vecinas), entre {som.eta_u_min} y "
        "{som.eta_u_max}. "
        "Los ejes están ampliados para que se vea el recorrido de cada curva, así que las diferencias parecen más "
        "grandes de lo que son: al lado de cambiar la grilla, que lleva la distancia a la neurona ganadora de "
        "{som.k_first_dist} con k = {som.k_first} a {som.k_last_dist} con k = {som.k_last}, cambiar η0 mueve muy "
        "poco. "
        "Usamos η0 = {som.base_eta0}, un valor medio fijado de antemano, y con los otros valores la elección de k "
        "no cambia.",
    ),
    Slide(
        "som-r0", 1, "Con R0 entre {som.r0_lo} y {som.r0_hi} el mapa casi no cambia",
        None, ("Q1.3",), (), None, _key("som/figures/effect_radius0.svg"),
        "Probamos R0 = {som.r0_values}, con k = {som.chosen_k} y el resto igual, y cada punto es la media de 10 "
        "entrenamientos con distinta seed y las barras son el desvío entre ellas; R0 es cuántas neuronas vecinas se "
        "mueven junto con la ganadora al principio del entrenamiento y después el radio baja hasta "
        "{som.base_radius_final}. "
        "La distancia de cada creador a su neurona ganadora queda entre {som.r0_dist_min} y {som.r0_dist_max} y la "
        "U media, que es el promedio de la matriz U (la distancia entre neuronas vecinas), entre {som.r0_u_min} y "
        "{som.r0_u_max}. "
        "Los ejes son los mismos que en la slide de η0 y también están ampliados, y un radio inicial más chico "
        "acerca un poco los creadores a sus neuronas, pero no cambia la elección de k. "
        "Usamos R0 = {som.base_radius0}, la mitad de k, fijado de antemano, y con los otros valores la elección de "
        "k no cambia.",
    ),
    Slide(
        "som-te", 1, "Las grillas con menor error topográfico dejan demasiadas neuronas vacías",
        None, ("Q1.3",),
        ("Error topográfico = creadores cuya neurona más cercana y segunda más cercana no son vecinas en la grilla "
         "/ total de creadores",),
        None, _key("som/figures/te_by_k.svg"),
        "El error topográfico es la fracción de creadores cuya neurona más cercana y segunda más cercana no son "
        "vecinas en la grilla (una diagonal cuenta como error), y mide si el mapa conserva la vecindad, que es lo que "
        "busca Kohonen; cada barra es la media de 10 entrenamientos con distinta seed, las líneas negras son el "
        "desvío entre ellas y la línea punteada es el límite de {som.te_max}. "
        "Los límites de ocupación son dos, fijados de antemano: como máximo {som.empty_max} de neuronas vacías y al "
        "menos {som.creators_min} creadores por neurona ocupada en promedio, o sea una neurona cada dos creadores "
        "como mucho; con k = {som.chosen_k} hay {som.chosen_neurons} neuronas para {oja.n_creators} creadores, y con "
        "k = {som.k_next} ya son {som.k_next_neurons}, con {som.k_next_empty} vacías y {som.k_next_creators} "
        "creadores por neurona ocupada. "
        "Las grillas más grandes tienen menos error que k = {som.chosen_k} ({som.chosen_te}), pero a costa de "
        "neuronas vacías y de creadores casi solos en su neurona, y por eso están en gris. "
        "Entre las grillas que cumplen los límites de ocupación, k = {som.chosen_k} es la de menor error topográfico "
        "y la más grande, y como ninguna cumplió el límite de {som.te_max}, la regla quitó ese límite y eligió "
        "k = {som.chosen_k}.",
    ),
    Slide(
        "som-robust", 1,
        "La elección es robusta: las {som.n_stage2_variants} variantes del schedule pasan los filtros",
        "Regla fijada de antemano", ("Q1.3",),
        (
            "Neuronas vacías entre {som.s2_empty_min} y {som.s2_empty_max} (máximo {som.empty_max}); creadores por "
            "neurona ocupada entre {som.s2_creators_min} y {som.s2_creators_max} (mínimo {som.creators_min})",
            "El TE medio queda entre {som.s2_te_min} y {som.s2_te_max}, sobre el máximo de {som.te_max}: ese filtro ya "
            "se había quitado en la etapa 1",
        ),
        None, None,
        "Sobre k = {som.chosen_k} se movió una cosa a la vez: el radio inicial, la tasa η0 y las épocas, con 10 seeds por "
        "variante. "
        "En todas las variantes la ocupación de las neuronas pasa los filtros, así que la elección es robusta según el "
        "criterio fijado de antemano. "
        "El filtro de TE no se revisa porque en la etapa 1 ninguna grilla lo cumplía, y el TE medio de la grilla elegida "
        "va de {som.s2_te_min} a {som.s2_te_max} según el schedule. "
        "La etapa 2 nunca vuelve a elegir k.",
    ),
    Slide(
        "som-map", 1, "Las paredes altas de la matriz U separan perfiles por patrocinio, engagement y alcance",
        None, ("Q1.4", "Q1.7"), (), None, _key("som/figures/map.svg"),
        "El mapa de {som.chosen_k} por {som.chosen_k} muestra a la izquierda cuántos creadores cayeron en cada neurona y, "
        "a la derecha, la matriz U, que para cada neurona es la distancia promedio entre su perfil y el de sus vecinas: "
        "un valor bajo (más oscuro) significa que se parece a sus vecinas y un valor alto (más claro) significa que es "
        "bien distinta. "
        "Una pared alta es un par de neuronas vecinas con perfiles muy distintos, y al cruzar la más alta, "
        "{som.wall_1.path} (distancia {som.wall_1.dist}), {som.wall_1.changes}. "
        "Al cruzar la segunda, {som.wall_2.path} (distancia {som.wall_2.dist}), {som.wall_2.changes}, y al cruzar la "
        "tercera, {som.wall_3.path} (distancia {som.wall_3.dist}), {som.wall_3.changes}. "
        "Ninguna se debe a followers ni al precio, o sea al tamaño, y en {som.n_walls_single} de las tres paredes hay "
        "una neurona con un solo creador, así que ese salto puede ser un caso suelto, y una pared junto a una neurona "
        "vacía es interpolación y no un límite entre grupos.",
    ),
    Slide(
        "som-zonas", 1, "Fútbol arriba, arte en el centro, perros abajo y maquillaje a la derecha",
        None, ("Q1.5",), (), None, _key("som/profiles/zones.svg"),
        "Cada neurona ocupada toma el color del tema dominante más frecuente entre sus creadores y muestra la mediana "
        "de followers y de precio por post. "
        "El tamaño crece en diagonal: en {som.zone_small.cell} hay {som.zone_small.n} creadores de "
        "{som.zone_small.topic} con una mediana de {som.zone_small.followers} followers y USD {som.zone_small.price}, y "
        "en {som.zone_large.cell} hay {som.zone_large.n} de {som.zone_large.topic} con {som.zone_large.followers} "
        "followers y USD {som.zone_large.price}. "
        "Dentro de ese eje los temas forman zonas, que son neuronas contiguas con un tema dominante en común: perros "
        "abajo, arte en el centro, fútbol arriba y maquillaje en la columna derecha, con fútbol tanto entre creadores "
        "chicos como entre grandes. "
        "Los temas son parte de lo que pesa en las componentes con las que se entrena el mapa, así que describen dónde "
        "cae cada perfil y no validan grupos.",
    ),
    Slide(
        "som-pc", 1, "El mapa ordena a los creadores igual que PC1 y, en menor medida, PC2",
        None, ("Q1.6",), (), None, _key("som/profiles/pc_planes.svg"),
        "Esta slide sirve para constatar que el biplot de la PCA y el mapa de Kohonen coinciden: son dos formas de "
        "ubicar a los creadores, como dos planos de la misma ciudad, y se chequea que los barrios queden en el mismo "
        "lugar. "
        "Si te digo solamente en qué casilla cayó un creador, con una regla simple sobre su fila y su columna se "
        "explica el {som.r2_pc1_pct} de lo que vale su PC1 y el {som.r2_pc2_pct} de lo que vale su PC2, o sea que el "
        "mapa ordena a los creadores casi igual que PC1 y solo en parte igual que PC2. "
        "Como el mapa se entrena con los scores de las componentes, que siga a PC1 y PC2 es esperable y no una "
        "validación independiente.",
    ),
    Slide(
        "oja-setup", 1, "Oja es una neurona lineal con una entrada por variable",
        None, (),
        (
            "Una neurona lineal: sus pesos arrancan uniformes entre 0 y 1 y su salida es y = w · x",
            "Entran los {oja.n_creators} creadores con sus {pca17.n_features} variables estandarizadas, de a uno por "
            "vez, y después de cada uno se actualiza w ← w + η · y · (x − y · w)",
            "La tasa baja en cada iteración de forma exponencial: η(t) = η0 · ({oja.eta_final} / η0)^(t / (T − 1)), "
            "con T los pasos de entrenamiento",
        ),
        (
            ("Hiperparámetro", "Valor"),
            (
                ("Tasa de aprendizaje inicial η0", "{oja.eta0}"),
                ("Épocas", "{oja.epochs}"),
            ),
        ),
        None,
        "La regla de Oja la usamos como un perceptrón lineal simple: una neurona con una entrada por variable, un "
        "peso por entrada y activación lineal, así que su salida es y = w · x, y como los datos están estandarizados "
        "la regla converge al primer componente principal, que es el vector w final. "
        "Los pesos se actualizan después de cada creador con w ← w + η · y · (x − y · w), que es el algoritmo del "
        "curso, y el orden de los creadores se baraja en cada época. "
        "La tasa inicial η0 = {oja.eta0} es una de las que sugiere el curso y queda muy por debajo del valor "
        "1 / ({pca17.eta_factor} · λ₁) = {pca17.eta_bound} que da para asegurar la convergencia, donde "
        "λ₁ = {pca17.lambda1} es el mayor autovalor de la matriz de correlación, lo que explica PC1; como ese "
        "autovalor no se conoce de antemano, el curso recomienda estandarizar y empezar con una tasa chica. "
        "Cuando converge, el vector de pesos final es la primera componente principal, como se vio en clase, y en "
        "{oja.n_abs_cos_above} de las {oja.n_seeds} seeds el vector quedó prácticamente paralelo a PC1.",
    ),
    Slide(
        "oja-pc1", 1, "Oja aprendió PC1: su índice y el score de PC1 ordenan igual a los creadores",
        None, ("Q1.8", "Q1.9", "Q1.11"),
        ("{oja.n_abs_cos_above} de {oja.n_seeds} seeds coinciden con PC1; mayor diferencia entre índice y score: {oja.max_abs_diff}",),
        None, _key("oja/oja_vs_pc1.svg"),
        "El índice de Oja es la proyección de cada creador sobre el vector w que aprende la neurona, y ese w coincide "
        "con el primer componente principal (abs(cos) mínimo entre pares de seeds {oja.abs_cos_min}), así que representa "
        "la posición del creador en el eje donde más se diferencian los creadores, que explica {pca17.var_pc1} de la varianza. "
        "Se interpreta por los pesos de w: followers, me gusta, alcance y alcance de no seguidores suman, y guardados, "
        "visitas al perfil, comentarios, tutoriales y tiempo de visualización restan, así que con la convención del "
        "proyecto (el peso de followers es positivo) un índice alto es un creador grande y uno bajo es un creador chico con audiencia que guarda y mira con "
        "atención; es una posición en un eje y no una calificación. "
        "Por eso el índice y el score de PC1 ordenan a los creadores del mismo modo, salvo un error de convergencia de "
        "{oja.max_abs_diff} como máximo, y no agrega información que PC1 no tenga.",
    ),
    Slide(
        "oja-max", 1, "Elegir el máximo del índice no es correcto: cambia con el signo y no mira el tema",
        None, ("Q1.9", "Q1.10"),
        ("Correlación del índice con followers: Pearson {oja.corr_followers_pearson}",),
        (
            ("Signo del índice", "Creador con el máximo", "Tema dominante", "Followers"),
            (
                ("Convención del proyecto: followers con peso positivo", "{oja.max_id} {oja.max_name}", "{oja.max_topic}", "{oja.max_followers}"),
                ("Signo opuesto", "{oja.max_opposite_id} {oja.max_opposite_name}", "{oja.max_opposite_topic}",
                 "{oja.max_opposite_followers}"),
            ),
        ),
        None,
        "El índice es la proyección sobre PC1, un eje de tamaño y de tipo de respuesta de la audiencia: con la convención "
        "del proyecto, que fija el signo de w para que followers pese positivo, un índice alto es un creador grande, y "
        "dar vuelta el signo da el extremo opuesto. "
        "Como w y −w son el mismo eje, el signo no significa nada y el máximo depende de una elección arbitraria: bajo "
        "cada signo es otro creador, de otro tema y de otro tamaño, {oja.max_name} con {oja.max_followers} followers "
        "contra {oja.max_opposite_name} con {oja.max_opposite_followers}. "
        "Con followers el índice tiene Pearson {oja.corr_followers_pearson}, "
        "porque en esencia ordena por tamaño y no conoce el tema de la campaña. "
        "El índice dice dónde cae cada creador en un eje de tamaño, pero no dice a quién conviene contratar para una "
        "campaña concreta, así que hay que filtrar primero por el tema de la campaña y ordenar por su propio objetivo; "
        "sirve solamente para describir el tamaño y el perfil de audiencia de cada creador, y lo incorrecto es usarlo "
        "como un puntaje de calidad.",
    ),
    Slide(
        "camp-futbol", 1, "Fútbol: conviene profundidad, que queda lejos de los más seguidos",
        "Regla fijada de antemano", ("Q1.12",),
        (
            "Recomendación: profundidad, con descubrimiento como segunda opción (USD {camp.futbol.cost_total} en "
            "total, USD {camp.futbol.cost_per_thousand_ar} por mil argentinos)",
        ),
        None, _key("campaigns/shortlists_biplot.svg"),
        "Los tres objetivos son reglas sobre variables del dataset: alcance masivo ordena por alcance argentino "
        "estimado, descubrimiento por la parte del alcance que viene de no seguidores, y profundidad por la media en z "
        "de contenido tutorial, guardados por mil y tiempo de visualización. "
        "La PCA da el fundamento: PC1 opone tamaño, me gusta y alcance a tutoriales, guardados y tiempo de "
        "visualización, y los más seguidos caen en el extremo de tamaño (PC1 media {camp.followers_global_pc1_mean}) mientras "
        "la lista de profundidad cae en el opuesto ({camp.futbol.pc1_mean}), que es justo lo que la agencia no estaba "
        "alcanzando. "
        "Para una marca de ropa de entrenamiento, que se vende mostrándola en uso, recomendamos profundidad, con "
        "descubrimiento como segunda opción si la marca necesita darse a conocer; es un juicio con ese supuesto y no un "
        "resultado de la regla. "
        "La lista ({camp.futbol.top5}) comparte {camp.futbol.overlap_followers} de {camp.k} con los más seguidos, "
        "cuesta USD {camp.futbol.cost_total} en total contra USD {camp.futbol.other_cost_total_min} o más de las otras "
        "dos, y su límite es el volumen: USD {camp.futbol.cost_per_thousand_ar} por mil argentinos, el costo por mil "
        "más alto de las tres.",
    ),
    Slide(
        "camp-table", 1, "Cada campaña se ordena con su propio criterio, no con followers",
        "Regla fijada de antemano", ("Q1.17",), (),
        (
            ("Campaña", "Criterio que fijamos", "Top 5", "USD por mil argentinos"),
            (
                ("Fútbol", "Mayor profundidad (tutoriales, guardados, tiempo de visualización)",
                 "{camp.futbol.top5}", "{camp.futbol.cost_per_thousand_ar}"),
                ("Perros", "Menor costo por mil argentinos", "{camp.perros.top5}", "{camp.perros.cost_per_thousand_ar}"),
                ("Maquillaje", "Mayor profundidad (tutoriales, guardados, tiempo de visualización)",
                 "{camp.maquillaje.top5}", "{camp.maquillaje.cost_per_thousand_ar}"),
                ("Arte", "Mayor engagement por mil y profundidad", "{camp.arte.top5}", "{camp.arte.cost_per_thousand_ar}"),
            ),
        ),
        None,
        "Cada lista sale de la regla de campaña fijada antes de calcular las listas: filtro por tema y ranking por un "
        "criterio que fijamos nosotros a partir de un supuesto sobre el cliente, que son refugios con poco presupuesto en perros, una marca de "
        "belleza que busca profundidad en maquillaje y un nicho que busca engagement y profundidad en arte, y fútbol muestra la lista de profundidad, que es la recomendada. "
        "En perros se ordena de menor a mayor costo por mil y los cinco tienen un costo por mil promedio de USD "
        "{camp.perros.criterion}; en maquillaje y arte se ordena de mayor a menor un puntaje que es la media de tutoriales, "
        "guardados y tiempo de visualización estandarizados (en arte, la mitad es engagement por mil), con promedios de "
        "{camp.maquillaje.criterion} y {camp.arte.criterion} desvíos sobre el promedio de los {oja.n_creators} creadores. "
        "El costo por mil de la lista, USD {camp.futbol.cost_per_thousand_ar} en fútbol, USD {camp.perros.cost_per_thousand_ar} en perros, USD {camp.maquillaje.cost_per_thousand_ar} "
        "en maquillaje y USD {camp.arte.cost_per_thousand_ar} en arte, es el costo total sobre el alcance argentino total, un "
        "cociente de sumas, y por eso no coincide con el promedio de los costos individuales de perros. "
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
        "letras", 2, "El set {letters.separated_set} es casi ortogonal (producto escalar máximo {letters.separated_max_overlap}); "
        "{letters.correlated_set} llega a {letters.correlated_max_overlap}",
        "Regla fijada de antemano", ("Q2.6", "Q2.7"),
        ("Con N = {letters.n_pixels} píxeles ningún par de letras es exactamente ortogonal",),
        None, _key("hopfield/figures/letters.svg"),
        "El alfabeto son las {letters.alphabet_size} mayúsculas dibujadas a mano en 5×5, y la regla elige, solo con los "
        "bitmaps, el set más "
        "separado ({letters.separated_set}) y el más correlacionado ({letters.correlated_set}) entre todos los "
        "subconjuntos de cuatro letras. "
        "Con N = {letters.n_pixels} el producto escalar es siempre impar, así que ningún par es exactamente ortogonal: el "
        "máximo producto escalar de un par de letras, dividido por N (vale 0 si son ortogonales y 1 si son iguales), es "
        "{letters.separated_max_overlap} en el primero y {letters.correlated_max_overlap} en el segundo. "
        "Una divulgación: {letters.draft_matching_glyphs} de los {letters.alphabet_size} glifos coinciden con un "
        "borrador que se usó en un prototipo, y el desempate del set "
        "correlacionado no es independiente de él.",
    ),
    Slide(
        "letras-ruido", 2, "El set separado resiste el ruido; el correlacionado nunca pasa de {letters.correlated_recall_k3}",
        "Regla fijada de antemano", ("Q2.7",),
        ("Recuperación exacta con {letters.flips_k3}, {letters.flips_k6} y {letters.flips_k9} píxeles invertidos en el "
         "set separado: {letters.separated_recall_k3}, {letters.separated_recall_k6} y {letters.separated_recall_k9}",),
        None, _key("hopfield/figures/recall_noise.svg"),
        "El ruido invierte el signo de k píxeles distintos de la letra, elegidos al azar y sin repetir, y el nivel de ruido es k dividido N. "
        "Recuperar es llegar exactamente a la letra de la consulta: en el set separado la tasa es "
        "{letters.separated_recall_k3} con {letters.flips_k3} píxeles invertidos, {letters.separated_recall_k6} con "
        "{letters.flips_k6} y {letters.separated_recall_k9} con {letters.flips_k9}. "
        "En el correlacionado solo {letters.correlated_n_stable} de las {letters.set_size} letras es punto fijo y las "
        "otras caen sobre ella, "
        "de ahí el techo de {letters.correlated_recall_k3}. "
        "La capacidad con p = 4 depende de cuánto se parezcan las letras: {letters.p4_all_stable_fraction} de los "
        "subconjuntos posibles de cuatro letras las tienen todas estables, y la fracción estable media es "
        "{letters.p4_mean_stable_fraction}.",
    ),
    Slide(
        "letras-energia", 2, "La red puede bajar de energía hasta un estado espurio, que no es ninguna letra",
        "Regla fijada de antemano", ("Q2.8",),
        (),
        None, _key("hopfield/figures/spurious_energy.svg"),
        "La energía de la red es E = −½ sᵀ W s y baja o se queda igual cada vez que una neurona cambia de estado, así que "
        "la curva solo desciende hasta quedar plana en un estado estable; eso no garantiza que sea una letra guardada. "
        "La consulta es la G con {letters.spur_flip_min} píxeles invertidos al azar y la red termina en el inverso de la "
        "{letters.spur_inverse_of}, que es la {letters.spur_inverse_of} con todos los píxeles al revés: no es ninguna de "
        "las letras guardadas, así que es un estado espurio. "
        "Con ruido alto sobre el set separado ({letters.spur_flip_min} a {letters.spur_flip_max} píxeles invertidos de "
        "{letters.n_pixels}), {letters.spur_total} de {letters.spur_trials} ensayos ({letters.spur_total_pct}) terminan "
        "en un estado que no es una letra guardada, repartidos en inverso ({letters.spur_inverse_pct}), mezcla "
        "({letters.spur_mixture_pct}) y otro ({letters.spur_other_pct}), y la clase más frecuente es la del "
        "{letters.spurious_class}. "
        "El inverso termina en {letters.stored_energy}, la misma energía de las letras guardadas, porque invertir todos "
        "los píxeles de un patrón no cambia la energía, mientras que una mezcla ({letters.spur_mixture_energy}) y otro "
        "estado ({letters.spur_other_energy}) de los ejemplos de la regla quedan en mínimos más altos; son tres ejemplos "
        "y no una ley sobre la energía de los estados espurios.",
    ),
    Slide(
        "letras-capacidad", 2,
        "Capacidad: el curso da {letters.course_capacity} patrones para N = {letters.n_pixels} y la estabilidad cae sin "
        "un corte",
        "Regla fijada de antemano", ("Q2.7",),
        (
            "Fracción de letras estables: {letters.stable_p3} con p = 3, {letters.stable_p4} con p = 4 y "
            "{letters.stable_p6} con p = 6",
        ),
        None, _key("hopfield/figures/capacity_by_p.svg"),
        "La curva azul, la fracción estable, responde si la red guarda la letra, o sea si sin ruido es un punto fijo, y la "
        "naranja, la tasa de recuperación con {letters.flips_k3} píxeles invertidos al azar, responde si la red corrige "
        "errores, o sea si devuelve la letra exacta. "
        "La referencia del curso es p ≤ {letters.course_capacity_ratio}·N, que con N = {letters.n_pixels} da "
        "{letters.course_capacity}, aunque es una estimación para patrones al azar con N grande y no para letras dibujadas: "
        "medida sobre subconjuntos al azar, la fracción de letras estables cae de forma gradual, de {letters.stable_p3} "
        "con p = 3 a {letters.stable_p4} con p = 4 y {letters.stable_p6} con p = 6, y con p = "
        "{letters.capacity_last_p} todavía vale {letters.stable_last_p}, así que no hay un quiebre en "
        "{letters.course_capacity}. "
        "Lo que decide es cuánto se parecen las letras: con p = 4 solo {letters.p4_all_stable_fraction} de los subconjuntos tienen "
        "las cuatro letras estables, porque el crosstalk de las letras parecidas le gana al de la propia letra. "
        "En los QR la misma referencia da {qr.course_capacity} patrones para {qr.n_pixels} píxeles, muy por encima de "
        "{qr.n_qr}: ahí Hebb no falla por capacidad sino por ese crosstalk, que solo se anula con patrones "
        "ortogonales.",
    ),
    Slide(
        "qr-correlados", 2, "Los QR son idénticos en {qr.identical_fraction} de sus píxeles: están muy correlacionados",
        None, ("Q2.1", "Q2.2"),
        ("Matrices binarias de 37×37 ({qr.n_pixels} píxeles); producto escalar normalizado máximo {qr.max_abs_overlap}, medio {qr.mean_abs_overlap}",),
        None, _key("hopfield/qr/figures/qr.svg"),
        "Cada QR es una matriz binaria de 37×37 de módulos oscuros y claros, como pide la pregunta, y son {qr.n_qr} "
        "almacenados en una sola red. "
        "Como codificación de este trabajo, y no como parte del enunciado, la red guarda cada matriz como un vector de "
        "{qr.n_pixels} valores ±1, con la polaridad oscuro = +1 y claro = −1. "
        "El {qr.identical_fraction} de los {qr.n_pixels} píxeles es idéntico en los {qr.n_qr} a la vez y el producto escalar normalizado "
        "entre pares es {qr.max_abs_overlap} como máximo y {qr.mean_abs_overlap} en promedio, lejos de la ortogonalidad.",
    ),
    Slide(
        "qr-hebb-falla", 2, "Con los 5 QR Hebb recupera {qr.hebb_exact_noise0}; con {qrm.n_chosen} QR y su parte variable, hasta {qrm.hebb_exact_noise0}",
        None, ("Q2.3",),
        ("El experimento con {qrm.n_chosen} QR es posterior al protocolo y no estaba preregistrado",),
        None, _key("hopfield/qr_masked/figures/masked_recovery.svg"),
        "Con el protocolo fijado de antemano la tasa de recuperación exacta de Hebb sobre los {qr.n_qr} QR es "
        "{qr.hebb_exact_noise0} en todos los niveles de ruido, el nivel cero incluido: no son puntos fijos porque están muy "
        "correlacionados (producto escalar normalizado medio {qr.mean_abs_overlap}), y la red converge a un único estado, la "
        "mayoría píxel a píxel de los cinco, que difiere de cada QR por entre {qr.majority_hamming_min} y "
        "{qr.majority_hamming_max} píxeles de {qr.n_pixels}; el ruido invierte el signo de una fracción de los píxeles de la "
        "consulta, elegidos al azar y sin repetir, en {qr.n_noise_levels} niveles. "
        "Después de ver ese cero diseñamos un experimento aparte, fuera del protocolo: la red guarda solo los {qrm.n_varying} "
        "píxeles que cambian entre los cinco QR, completa los {qrm.n_common} comunes desde la plantilla y se queda con el "
        "trío menos parecido, {qrm.chosen_names}. "
        "Hace falta todo junto: con los cinco QR sobre la parte variable son punto fijo {qrm.fixed_masked_all} y con los "
        "tres completos {qrm.fixed_full_subset}, mientras que con los tres sobre la parte variable son punto fijo "
        "{qrm.fixed_masked_subset}. "
        "Así Hebb recupera el {qrm.hebb_exact_noise0} hasta ruido {qrm.hebb_last_full_noise} y {qrm.hebb_at_0_40} en "
        "{qrm.noise_mid}, pero un lookup de Hamming sobre los mismos patrones sigue por encima: achica el problema, no lo "
        "resuelve para los cinco QR.",
    ),
    Slide(
        "qr-lookup", 2, "Un lookup de Hamming iguala o supera a la pseudo-inversa con ruido alto",
        "Regla fijada de antemano", ("Q2.3",),
        ("Con ruido alto (nivel {qr.noise_high}): Hamming {qr.hamming_at_high}, pseudo-inversa {qr.pinv_at_high}",),
        None, _key("hopfield/qr/figures/recovery.svg"),
        "La pseudo-inversa sí guarda los {qr.n_qr} QR: recupera {qr.pinv_exact_noise0} sin ruido y se mantiene así hasta "
        "el nivel {qr.pinv_last_full_noise}. "
        "Pero la línea base de Hamming, un 1-NN sin dinámica, queda por encima de ella con ruido alto: {qr.hamming_at_high} "
        "contra {qr.pinv_at_high} en el nivel {qr.noise_high} y {qr.hamming_at_0_50} contra {qr.pinv_at_0_50} en el último nivel. "
        "Con cinco patrones conocidos de antemano, la ventaja de Hopfield frente a una tabla de búsqueda no está en la tasa de acierto.",
    ),
    Slide(
        "qr-energia", 2, "Con Hebb la red converge al estado común; con la pseudo-inversa, al QR consultado",
        None, ("Q2.4", "Q2.5"),
        ("Ensayos fijos por QR y nivel de ruido: la energía baja hasta quedar plana",),
        None, _key("hopfield/qr/figures/energy_trace.svg"),
        "La figura traza la energía después de cada paso de un ensayo fijo por QR y nivel de ruido, arriba con "
        "Hebb y abajo con la pseudo-inversa; la teoría no garantiza que la energía no suba en cada paso, pero en estas "
        "corridas no subió nunca. "
        "Con Hebb cada corrida converge al estado común y no al QR consultado; con la pseudo-inversa converge al QR "
        "consultado hasta el nivel {qr.pinv_last_full_noise}, y cada QR guardado queda en la energía mínima, −N/2 = "
        "{qr.pinv_stored_energy}. "
        "Las escalas no se comparan: Hebb suma los productos de los patrones sin dividir por N y su energía es del "
        "orden de millones. "
        "El número de pasos crece poco con el ruido, y con un solo píxel de corrimiento la consulta ya está a "
        "{qr.shift1_query_hamming} de {qr.n_pixels} píxeles de la fuente y la pseudo-inversa la deja a "
        "{qr.shift1_recovered_hamming}.",
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
        "Las limitaciones medidas son tres: la correlación entre los QR ({qr.mean_abs_overlap} de producto escalar normalizado medio) rompe "
        "a Hebb, un corrimiento de un solo píxel ya mueve la consulta a {qr.shift1_query_hamming} de {qr.n_pixels} píxeles, "
        "y la matriz de pesos tiene {qr.n_pixels} por {qr.n_pixels} entradas para solo {qr.n_qr} patrones. "
        "Un lookup de Hamming resuelve el mismo problema cerrado con igual o más acierto y sin dinámica ni energía. "
        "Tampoco verificamos que un QR recuperado se decodifique, porque no corrimos ningún decodificador y el formato QR "
        "ya trae su propia corrección de errores, y el daño estructurado, como un rayón, no se midió.",
    ),
)

# Slide figures that are on no slide: the slide budget (MAX_SLIDES) leaves no room for them, their slide variants
# exist so that a later outline edit can swap one in without touching figure code, and each stays in the informe.
UNPLACED_SLIDE_FIGURES: dict[str, str] = {
    _key("campaigns/shortlists_som.svg"):
        "las cuatro slides de campaña están fijadas por D-05 (fútbol sobre el biplot, dos tablas y mantenimiento); "
        "la vista de las listas sobre el SOM queda en el fragmento 03",
    _key("hopfield/figures/spurious.svg"):
        "la slide letras-energia muestra un solo estado espurio con su energía; la frecuencia de cada clase se da en sus "
        "notas y los tres ejemplos con sus letras quedan en el fragmento 04",
    _key("hopfield/figures/overlaps.svg"):
        "la ortogonalidad de los dos sets de letras se da como números en la slide letras",
    _key("hopfield/figures/capacity_p4.svg"):
        "la slide letras-ruido muestra la recuperación frente al ruido; la capacidad con p = 4 queda en el fragmento 04 "
        "y se nombra en las notas de esa slide",
    _key("hopfield/qr/figures/overlaps.svg"):
        "la slide qr-correlados muestra los QR y da los productos escalares como números de facts",
    _key("hopfield/qr_masked/figures/masked_patterns.svg"):
        "la slide qr-hebb-falla muestra la recuperación del experimento con máscara; la máscara y los tres QR quedan en el "
        "fragmento 05",
    _key("hopfield/qr/figures/majority.svg"):
        "el estado común de Hebb se describe en las notas de qr-hebb-falla; la figura queda en el fragmento 05",
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
            # A row of a stage-2 variant that did not fail is dropped: the number of failing variants comes from the
            # results (som.fail_1 ... som.fail_N), and the outline reserves one row per possible failure.
            rows = [
                row for row in slide.table[1]
                if not any(key.startswith("som.fail_") and key not in values
                           for cell in row for key in facts.TOKEN.findall(cell))
            ]
            table = {"header": [fill(cell) for cell in slide.table[0]], "rows": [[fill(cell) for cell in row] for row in rows]}
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
        0: ("inicio", "Portada"),
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
