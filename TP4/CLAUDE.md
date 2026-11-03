# TP4 SIA — Aprendizaje no supervisado y memoria asociativa

Contexto vivo del TP4: **dónde está el TP hoy**. Se sobrescribe, y arranca cada sesión nueva desde acá, así se puede limpiar
el chat sin perder lo decidido.

Materia: Sistemas de Inteligencia Artificial (ITBA), 2° cuatrimestre 2026, Grupo 9.
Enunciado: `docs/Archivo SIATP 42026.pdf`.

## Dónde estamos hoy (leer primero)

**Retomar (2026-11-03):** el ejercicio 1 está hecho con las 17 variables y las 7 componentes en repo y deck, y las slides 20 a 25 están revisadas con el usuario.
Orden del deck publicado: 20 `oja-pc1`, 21 `oja-max`, 22 `camp-futbol`, 23 `camp-table`, 24 `camp-followers`, 25 `camp-maintenance`; `ej1-conclusiones` se sacó
(repo y deck, 30 slides en el repo). Lo que cambió en esa revisión: notas de 20 y 21 (convención de signo: followers con peso positivo; el signo de w es arbitrario),
`camp-futbol` con título nuevo y solo el panel de fútbol en el gráfico (`campaigns.py`, variante slide), `camp-table` con la columna "Criterio que fijamos" y la fila
de fútbol arriba, en el mismo orden que `camp-followers`. `camp-followers` y `camp-maintenance` quedan como están (decisión del usuario). **El deck publicado en el Artifact es lo que se presenta**: sus slides se editaron
varias veces desde la página; no republicar el que arma el repo (ver "Cómo se publica el deck"). Ejercicio 2, ya revisado: 26 (`6aa851b4`, a mano), 27 `letras`
(título con "producto escalar máximo", sin "solapamiento"), 28 `letras-ruido` (solo la curva de recuperación; notas con la función de ruido: invierte k píxeles
distintos al azar), 29 `letras-energia` (nueva: una consulta, la G con 10 píxeles invertidos, que termina en un estado espurio; absorbió la antigua `espurio`),
30 `letras-capacidad` (sin rombos, sin 0,138N, notas con qué responde cada curva), 31 `qr-correlados`, 32 `qr-hebb-falla`, 33 `qr-lookup`, 34 `qr-energia`,
35 `ej2-conclusiones`. Regla del usuario: **ninguna slide, figura ni texto dice "solapamiento"** (se usa "parecido" o "producto escalar"); queda solo en el texto
congelado de las reglas pre-registradas de los fragmentos 04 y 05 (su sha256) y en `.planning/`. Sin sync/async en slides, figuras y fragmentos (el código en C
todavía tiene los dos modos). Lo que sigue: revisar las slides 32 a 35, la de Hamming y la pseudo-inversa (el usuario quiere justificarlas bien o sacarlas) y
traer la rama `fix-entrega` de Matías (QR: experimento con 3 QR sobre los 414 píxeles variables; solo actualización síncrona). Dudas abiertas: (a) tres columnas de criterio de campaña están fuera de las 17 (`price_usd`, `total_engagement_per_1000`, `trend_posts_pct`; la
regla pre-registrada de campañas no se tocó, decidir con el usuario si se deja o se rehace el criterio de arte); (b) el texto de la regla pre-registrada del SOM
sigue nombrando QE, QE-LOO, estabilidad, escalón y gaussiana (no se edita: su sha256 lo guardan los pasos del SOM).

**El ejercicio 1 se está rehaciendo con las variables que quedan después de podar por correlación.** Orden de lo hecho (2026-10-28 a 11-02):

1. **Variables**: se sacan las 5 triviales (combinación lineal exacta de otras) y, con el umbral **|r| ≥ 0,8**, 9 más por correlación (en cada
   par sale la de mayor |r| medio con las demás, `analysis/corr_prune.py`, `make corr-prune`). Quedan **17 de 31** (F1 D-14). La tabla de
   otros umbrales (0,95 a 0,50) es solo sensibilidad (slide `pca-prune`).
2. **PCA de las 17** (`analysis/results/pca/pruned/`, `make pca`): 7 componentes llegan al 83,4 %; PC1 40,0 % y PC2 11,7 %. La PCA de las 26
   (`pca/audited/`) sigue existiendo para el informe y la sensibilidad.
3. **SOM sobre los scores de PC1 a PC7, sin reescalar** (`datos/prepared/creadores_pca_scores.csv`, lo escribe `make pca`; F2 D-16). La regla
   de grilla no cambió. Resultado: k = 5 (ninguna grilla cumple el TE máximo, se aplica F2 D-14), etapa 2 robusta, una sola región, el
   mapa sigue a PC1 (R² 0,938) y a PC2 (R² 0,439), que son entradas suyas.
4. **Oja y campañas, con las 17 (2026-11-02)**: `make pca` escribe también `datos/prepared/creadores_zscore_pruned.csv` (las 17 columnas
   z-score) y Oja entrena sobre él; se compara con PC1 de `pca/pruned/`. Con las 17, el pivote de la convención de signo es `followers`: un
   índice alto es un creador **grande** (antes, con las 26, era chico). Las listas de campaña no cambiaron (la regla pre-registrada elige sobre
   las columnas crudas del dataset, no sobre la PCA); cambiaron las lecturas (índice de Oja, PC1 y PC2, neuronas) y la demo de
   mantenimiento. Fragmento 03, `ej1-conclusiones` y las slides de Oja y campañas ya usan las 17; falta el informe publicado.

## Reglas de trabajo que dio el usuario

- **Solo se usa lo visto en clase** (la teoría está en `docs/`). Se sacaron del trabajo y no pueden volver, ni en el repo ni en las slides ni
  en el informe: el **criterio de Kaiser**, el **scree plot** (el gráfico se llama "autovalores y varianza acumulada", archivo
  `eigenvalues_variance`), la **correlación de Spearman** (en el SOM se usa Pearson) y el **número de condición**. El 80 % de varianza
  acumulada y el umbral |r| ≥ 0,8 se presentan como **convenciones del equipo**, no como reglas del curso. Antes de proponer un método o
  una medida nueva, comprobar que esté en `docs/`.
- **Qué no se muestra del SOM (2026-11-02)**: el **QE**, el **QE-LOO** y la **estabilidad entre seeds** no se vieron en clase y no van en las slides ni en los MD (informe y fragmentos). Siguen en el código, que no se toca por pedido del usuario, y en el texto de la regla pre-registrada (entre `<!-- regla:inicio -->` y `<!-- regla:fin -->` de `deliverables/02-kohonen.md`), que no se edita: su sha256 lo comprueban los pasos del SOM. El **error topográfico (TE)** se queda, con su justificación en las notas de la slide `som-k`: mide si el mapa conserva la vecindad, que es lo que busca Kohonen. Tampoco están en `docs/` la correlación tipo Mantel, las permutaciones con p-valor, la pseudo-inversa ni el lookup de Hamming; decidir con el usuario antes de sacarlos.
- **Sin GSD**: no correr comandos `/gsd-*`; se edita el repo directo. Los archivos de `.planning/` son historial y no se actualizan.
- **Commits locales sí, push solo si lo pide**. Reglas pre-registradas (sha256): se re-fijan con un commit antes de volver a correr.
- Pedir confirmación antes de publicar el informe (está compartido por link); el deck es privado.

## Estado técnico (código)

**Las seis fases están hechas y verificadas (UAT completo en todas, 2026-10-26), y las slides y el informe están publicados.** El núcleo de los tres
modelos (Kohonen, Oja, Hopfield) está en C, hecho a mano; el análisis, las figuras y los entregables están en Python. Todo se
maneja con `make` desde `TP4/`; los resultados generados no se versionan y se regeneran con `make results` (ver `README.md`).

```
docs/Archivo SIATP 42026.pdf     # el enunciado; el resto de docs/ es la teoría del curso (PCA, Kohonen, Oja y Sanger, Hopfield)
datos/
  creadores.csv                  # 50 creadores x 31 variables
  hopfield/*.png                 # los 5 QR de 37x37
  letters/alphabet_5x5.txt       # las 26 letras 5x5, dibujadas y aprobadas con la regla
  prepared/                      # se genera (make prepare, make letters, make qr); no se versiona
neuron/                          # C11 + make; README.md explica el binario y su config
  main.c, rng.c/h                # carga el config, despacha por `model`; RNG propio (splitmix64), uno por corrida
  models/                        # kohonen.c, oja.c, hopfield.c y hopfield_core.c/h (Hebb y pseudo-inversa)
  io/                            # config.json estricto (cJSON vendoreado), matrices CSV y results/ de cada corrida
  tests/                         # tests de C (make test los corre, con sanitizers)
scripts/
  prepare_creadores.py, creadores.py   # creadores.csv -> datos/prepared/ (matriz auditada de 26 variables y de 31 columnas)
  prepare_letters.py, letters.py       # alfabeto 5x5 -> alphabet_pm1.csv
  prepare_qr.py, qr.py                 # 5 PNG -> qr_pm1.csv, con sha256 por PNG
  map_creator.py                       # mapea un creador nuevo con el scaler guardado (mantenimiento)
analysis/                        # README.md explica las series y los drivers
  sweep.py, series_*.json        # series de corridas del binario con varias seeds -> summary.csv
  eda.py, pca.py                 # EDA y PCA por autovalores de la matriz de correlación
  som.py, som_loo.py, som_select.py, som_stage.py   # SOM: medidas, leave-one-out, regla de elección de grilla, etapas 1 y 2
  som_figures.py, som_profiles.py                   # figuras de la grilla elegida; regiones, perfiles, contraste con PC1/PC2
  oja.py, campaigns.py, campaigns_select.py, maintenance_demo.py   # Oja vs PC1, listas por campaña, demo de mantenimiento
  hopfield.py, hopfield_letters.py, hopfield_select.py, hopfield_figures.py     # Hopfield sobre las letras
  hopfield_qr.py, hopfield_qr_limits.py, hopfield_qr_select.py, hopfield_qr_figures.py   # Hopfield sobre los 5 QR
  hopfield_qr_masked.py, hopfield_qr_masked_figures.py   # experimento posterior: Hebb sobre la parte variable de 3 QR (KD-9)
  plots_style.py                 # estilo común y variantes de figura (informe y slide)
  deliverables_manifest.py       # fuente única: 39 figuras, 25 preguntas del enunciado, fragmentos
  facts.py                       # los números del texto salen de los JSON/CSV; `facts.py check` fija 68 frases de los fragmentos
  informe.py                     # arma analysis/results/informe/informe.html
  corr_prune.py                  # sensibilidad de la PCA a podar por umbral de |r| (tabla de la slide pca-prune; no rehace SOM ni Oja)
  slides.py                      # arma analysis/results/slides/ (30 slides, PNG y guion)
  tests/                         # pytest; incluye test_repro_docs.py, que cuida README.md, CLAUDE.md y DECISIONS.md
deliverables/                    # un fragmento por fase (01 a 05): lo que se entrega por escrito, congelado por guardas sha256
DECISIONS.md                     # decisiones para la defensa y fuente del glosario del informe
README.md                        # cómo reproducir cada figura y cada tabla
Makefile                         # results, deliverables, slides, informe y un target por paso
```

Los números de cada resultado, con su porqué, están en `deliverables/0X-*.md` y en `DECISIONS.md`. Se trabaja en la rama
`dev-tp4` del repo `SIA-TPs` (monorepo: TP4 es una subcarpeta).

## Qué pide el enunciado

**Ejercicio 1 — Creadores de contenido** (`datos/creadores.csv`, 50 creadores, 31 variables). El foco es el método y su
interpretación, no el análisis de marketing; se pueden asumir supuestos sobre las variables.

1. EDA y PCA: elegir las variables y justificar si se reduce la dimensionalidad y cómo se interpretan las componentes (biplot).
2. Red de Kohonen sobre todas las variables: variar hiperparámetros y justificar la elección con métricas; analizar la grilla, la
   distribución de los creadores y la matriz U; perfiles por región y contraste con PC1 y PC2.
3. Regla de Oja para un índice de creadores: qué representa, cómo se interpreta, si es correcto elegir el máximo para cualquier
   campaña, y comparación con la proyección sobre PC1.
4. Decisiones de campaña: fútbol (alcance, descubrimiento o profundidad), comparación con elegir solo por `followers`,
   mantenimiento (campaña nueva, creadores o variables nuevas, actualización de fin de mes).

**Ejercicio 2 — Memoria asociativa con Hopfield.**

1. Los 5 QR de 37x37 como matriz binaria: almacenarlos, consultar con distintos niveles de ruido, analizar iteraciones y energía
   por paso y explicar las limitaciones del caso de uso.
2. Cuatro letras de 5x5: asociar matrices con las letras almacenadas, analizar ortogonalidad y capacidad, y mostrar un patrón muy
   ruidoso que caiga en un estado espurio identificado.

Las 25 preguntas textuales, con su sección del enunciado y la sección que las responde, están en
`analysis/deliverables_manifest.py` (`QUESTIONS`) y en la tabla del informe.

## Decisiones cerradas (el detalle y el porqué están en `DECISIONS.md`)

- **Reglas pre-registradas y commiteadas antes de ver resultados**, con guarda sha256 en cada driver: la regla de elección de
  grilla del SOM (commit `ea7a0b1`), la de las campañas (`a6212e8`), la de las letras (`23c3563`) y el protocolo de los 5 QR. No se
  editan en el lugar: un cambio pasa por discusión. Las letras y los QR se re-registraron juntos el 2026-10-31 (commit `6a4bbd2`,
  KD-8) para quedarse solo con la actualización síncrona; la guarda acepta un re-registro solo si el módulo de la regla y el texto
  entre marcadores cambian en el mismo commit.
- **Los resultados se reportan como salieron**, incluso los desfavorables: una sola región en el mapa del SOM, ninguna grilla que cumpla el TE máximo,
  Hebb con 0 % de recuperación exacta aun sin ruido en los QR, y el lookup de Hamming que iguala o supera a la pseudo-inversa con
  ruido alto.
- **Oja**: el índice no se llama "mejor" y la respuesta a "¿elegir el máximo para cualquier campaña?" es no. El signo se orienta en
  C con una convención fija.
- **Entregables (Fase 6)**: informe como Artifact HTML autocontenido (D-15) y slides como Artifact tipo Slides (D-14), en dos
  entregables separados (KD-2). Los números del texto salen de los JSON/CSV (D-11), las notas del orador van en cada slide
  (D-06) y la publicación es manual.
- Las figuras de slide son siempre PNG subidos como assets: el almacén del tipo Slides borra los rasters embebidos de un SVG. El tipo
  Slides no admite script.

## Entrega

- **Slides**: 30 slides armadas por `make deliverables` en `analysis/results/slides/` (el repo no tiene la slide de método; el deck empieza con portada y EDA). El Artifact publicado tiene además slides que armó la persona dueña a mano o yo directo en el Artifact y que **no están en el repo**: `289f728e` ("Ejercicio 1"), `0732067f` (EDA: z-score, 5 triviales, umbral), `bc794b98` ("Kohonen"), `oja-intro` ("Regla de Oja") y `pca-eigenvalue-table` (tabla de los 17 autovalores). El orden del deck publicado manda: `project/deck.json` del Artifact no se pisa con el que arma el repo.
- **Cómo se publica el deck** (a mano, con la herramienta Artifact): (1) subir como asset los PNG que cambiaron (`analysis/results/slides/assets/`) y anotar sus `/_blob/…`; (2) armar `slides.py --out <carpeta> --asset-map <json>` con esas URLs; (3) **leer del Artifact** `project/deck.json` y las slides que se van a pisar (la persona dueña edita desde la página y las versiones cambian solas); (4) publicar **solo las slides que cambiaron** (y `deck.json` solo si cambia el orden, editando la copia leída). Nunca mandar el `deck.json` que arma el repo.
- **Informe**: `analysis/results/informe/informe.html`, publicado como Artifact HTML (D-15).
- Slides: https://claude.ai/artifact/CxnuCZKwF55r2tUMPWXBSN (las URLs `9YjSx…` y `32SjY…` de antes ya no existen; el 2026-10-28 se reemplazó el contenido de este deck por las slides del repo)
- Informe: https://claude.ai/artifact/ScERzQ4wTc8TrCNfuw2kKq (republicado el 2026-11-02 con el SOM sobre las 7 componentes y sin Kaiser, scree ni Spearman; está compartido por link; no lleva las slides armadas a mano porque salen del repo)
- Los dos Artifacts son privados; el deck se entrega como su PDF exportado (D-14: queda fuera del repo, ni en `docs/` ni en `deliverables/`), y compartir el link del informe lo decide la persona dueña desde el menú Share.
- El informe lleva el guion de la presentación como anexo (`id="guion"`, decisión del usuario en el checkpoint de 06-12): `make deliverables` pasa `INFORME_FLAGS := --notes analysis/results/slides/notes.md`; el guion viaja además como notas del orador en cada slide.
- Cualquier cambio de resultados: regenerar con `make deliverables`, actualizar `DECISIONS.md` y este archivo, y republicar a la
  misma url.
- Se publicó antes de verificar la Fase 3 (decisión 06-12). La verificación posterior (2026-10-26: UAT 3/3, `03-VERIFICATION.md` en
  `passed`) no cambió ningún resultado, así que el deck y el informe publicados siguen valiendo y no hubo que republicar.
- Republicado el 2026-10-26 por el arreglo de WR-03 de la Fase 6, sin cambiar ningún número: en el deck solo la slide `som-rule`
  (título y nota; la regla de grilla elige el menor QE-LOO entre las k que pasan los filtros), y el informe entero, que lleva esa
  nota en el anexo del guion ("Generado desde commit d4d145e.").

## Pendientes

- **Regenerar el informe** (`make deliverables`) con los números de las 17 variables y republicarlo, con el OK del usuario.
- **Volver a exportar el PDF del deck** desde su Artifact (lo hace la persona dueña): el exportado antes no tiene los cambios de esta tanda.

- **Experimento posterior de QR con máscara (2026-11-01, KD-9)**: Hebb sobre los 414 píxeles que cambian entre los 5 QR y
  solo el trío menos parecido (beverages, dessert, wine), rotulado como no preregistrado. Nuevo §7 del fragmento 05 (Cómo
  reproducir pasó a §8), slide `qr-mascara` (el deck pasa a 28), hallazgo en el informe y 2 figuras. El informe y las slides
  locales están armados; falta republicar los dos a la misma url y copiar la slide nueva a mano al Google Slides.

- **Hopfield solo síncrono (2026-10-31, KD-8)**: se quitó la actualización asíncrona del código, de los protocolos (re-registrados,
  declarado en los fragmentos 04 y 05) y de los textos; todo Hopfield se volvió a correr. Cambian números del fragmento 04
  (recuperación, capacidad por recuperación, estado espurio: ahora el más común es el otro, con 318 ciclos de 1200) y del 05
  (pinv 99,8 / 96,1 / 61 % en 0,35 / 0,40 / 0,45). La energía no subió en ninguna corrida. El informe local está armado; falta
  republicarlo y el deck a la misma url, copiar a mano al Google Slides los cambios (slides `letras-ruido`, `espurio`,
  `qr-energia`, `qr-hamming` y las figuras de Hopfield) y volver a exportar el PDF.

- **Conclusión de QR reescrita (2026-10-31)**: el informe explica el 0 % de Hebb como el caso de falla de la teoría (QR
  demasiado parecidos → crosstalk → atractor espurio que combina los cinco) y presenta la pseudo-inversa como los pesos que
  sí recuperan (`FINDINGS` de `informe.py` y párrafo "Conclusión" al inicio de la §6 del fragmento 05, fuera del bloque
  congelado). Además, "solapamiento" pasó a "producto escalar" y "término de cruce" a "crosstalk". Sin números nuevos. El
  informe local está armado; falta republicarlo a la misma url y copiar a mano al Google Slides los cambios de vocabulario.

- **Revisión del deck contra el enunciado (F6 D-16, 2026-10-27)**: 3 slides nuevas (`eda`, `som-zonas`, `letras-capacidad`) y 4
  reescritas (`som-not-robust`, `camp-futbol`, `ej1-conclusiones`, `qr-energia`). El deck que se presenta ahora es un Google
  Slides (convertido del Artifact): los cambios se copiaron a mano ahí, y las 3 figuras nuevas se suben a mano. El informe
  publicado no se republicó todavía.
- **La etapa 2 del SOM puede no ser idéntica entre máquinas** (otra versión de gcc o de glibc): una corrida anterior del mapa de 26 variables, regenerada en otra máquina, cambió cuántas variantes fallaban el TE. Las cifras del deck y del informe son las de la corrida del 2026-11-01 en esta máquina, con el SOM entrenado sobre los scores de las 7 componentes (F2 D-16); la elección de k y la robustez (ocupación) no deberían moverse.
- **Cerrar el milestone** con `/gsd-complete-milestone`: las seis fases están completas en `ROADMAP.md`.
- **Hallazgos de code review abiertos** (`NN-REVIEW-DISPOSITION.md` de las fases 2 a 6): los de la Fase 2 son 11, los de la Fase 3,
  14 (WR-01 a WR-05 e IN-01 a IN-09), y los de la Fase 6, IN-01 a IN-06 (WR-01 a WR-08 quedaron en `fixed` el 2026-10-26).
  Cualquier arreglo que toque una regla fijada de antemano (por ejemplo WR-01 de la Fase 2) pasa por `/gsd-discuss-phase`, no por
  edición en el lugar.
- Auditoría Nyquist: las fases 2 y 3 quedaron validadas el 2026-10-26 (sin huecos; `03-VALIDATION.md` se reconstruyó de los
  planes y los SUMMARY). La fase 6 también, el mismo día: los 55 chequeos de sus planes dan verde y se agregaron 8 tests de las
  variantes de slide que solo se verificaban sobre resultados reales (WR-08 de `06-REVIEW.md`, que queda en `fixed`).
- Sin verificar: la pseudo-inversa con ruido muy alto y la existencia de un decodificador de QR (HOP-09 quedó en v2).
- Fase 2 (decisión 06-12, 2026-10-26): se publicó con los 11 hallazgos de `02-REVIEW-DISPOSITION.md` abiertos (WR-01 a WR-04 e
  IN-01 a IN-07). Solo dos tocan la regla fijada de antemano: WR-01 (la igualdad en los umbrales se decide en punto flotante) e
  IN-01 (QE-LOO baja con k, así que la regla elige la k más grande que pasa los filtros). Arreglarlos anula el pre-registro y pasa
  por `/gsd-discuss-phase`. WR-02 y WR-03 son guardas de `som_stage.py`, fuera de la regla, y WR-04 es el kernel gaussiano en C.
  Ninguno cambia un número publicado: según `02-REVIEW.md`, ningún valor cae justo en un umbral salvo `epochs-1040`, que pasa
  igual. Además, el 2026-10-26 se comprobó que el texto de la regla, `som_select.py` y la serie de la etapa 1 son idénticos a
  `ea7a0b1`, que la serie de la etapa 2 es toda de k = 5 y que todas las series usan `radius_final` 1,0. IN-02 a IN-07 son de
  calidad de código.

## Cómo reproducir (los resultados no se versionan)

Todo desde `TP4/` y con los comandos de `README.md`: `make venv`, `make results` (regenera solo lo que falta; unos 11 minutos en esta
máquina sin las etapas del SOM), `make deliverables` (slides e informe) y `make test`. El README tiene una fila por cada figura
(comando, config y seed) y la tabla de las tablas principales. Para forzar un paso se borra su carpeta en `analysis/results/` y
se vuelve a correr `make results`. `make test` falla si falta o queda casi vacío alguno de `README.md`, `CLAUDE.md` y
`DECISIONS.md`, si nombran un target que no existe o si una figura del manifiesto no tiene su fila.

## Trampas conocidas

- **Los fragmentos `deliverables/0X-*.md` y los archivos de regla están congelados por guardas sha256**: el texto entre marcadores, el
  código de selección y los datos de entrada. Si un driver se niega a correr, la causa es un cambio en alguno; el camino es
  discutir el cambio, no editar la regla ni el hash.
- `make campaigns` y `make maintenance` vuelven a correr la etapa 1 del SOM por sus prerrequisitos phony. `make results` no lo
  hace si ya existe `selection.json`.
- Un centinela viejo de `make results` no detecta que el código cambió: hay que borrar la carpeta del paso.
- `make results` tarda unos 11 minutos en esta máquina para los 12 pasos que faltaban (sin las etapas 1 y 2 del SOM, que son 240
  corridas más).
- `uv` es opcional: sin él, `make venv` usa `python3.12 -m venv` y pip. En esta máquina `uv` no está.
- `analysis/results/` y `datos/prepared/` no se versionan. Los Artifacts son una publicación, no la fuente de verdad: la fuente es el
  código más `analysis/results/`.
- `make deliverables` arma las slides con las imágenes apuntando a los PNG locales. Antes de publicar hay que rearmar con
  `slides.py --asset-map`, o el deck publicado apunta a archivos que no existen.
- Las notas del orador de las slides las lee cualquiera que abra el deck: no pongas nada que no deba leerse.
- El monorepo tiene el `.git` en la raíz de `SIA-TPs`: nunca crear un `.git` dentro de `TP4/`, agregar archivos de a uno (no
  `git add -A` en la raíz) y no commitear `.planning/milestone.lock`.
- El shell es zsh: no divide palabras en variables sin comillas y un `=====` suelto se expande. `grep` puede ser `ugrep`: con
  metacaracteres literales conviene `grep -F`.

## Convenciones

- **Todo identificador en inglés**: variables, funciones, clases, nombres de archivo y de directorio. La prosa (README, este archivo,
  docs, slides e informe) en español rioplatense, con coma decimal.
- Los algoritmos (Kohonen, Oja, Hopfield) se implementan **a mano en C**: nada de librerías que los resuelvan. Librerías externas solo
  para I/O, arrays y gráficos.
- El índice de Oja nunca se llama "mejor".
- Nombres de archivo descriptivos, no numerados ni abreviados (salvo los fragmentos `deliverables/0X-*.md`).
- Los números del texto no se tipean: salen de `analysis/results/` por `analysis/facts.py`.
