# TP4 SIA — Aprendizaje no supervisado y memoria asociativa

Contexto vivo del TP4: **dónde está el TP hoy**. Se sobrescribe, y arranca cada sesión nueva desde acá, así se puede limpiar
el chat sin perder lo decidido.

Materia: Sistemas de Inteligencia Artificial (ITBA), 2° cuatrimestre 2026, Grupo 9.
Enunciado: `docs/Archivo SIATP 42026.pdf`.

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
  plots_style.py                 # estilo común y variantes de figura (informe y slide)
  deliverables_manifest.py       # fuente única: 31 figuras, 25 preguntas del enunciado, fragmentos
  facts.py                       # los números del texto salen de los JSON/CSV; `facts.py check` fija 67 frases de los fragmentos
  informe.py                     # arma analysis/results/informe/informe.html
  corr_prune.py                  # sensibilidad de la PCA a podar por umbral de |r| (tabla de la slide pca-prune; no rehace SOM ni Oja)
  slides.py                      # arma analysis/results/slides/ (25 slides, PNG y guion)
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
  editan en el lugar: un cambio pasa por discusión.
- **Los resultados se reportan como salieron**, incluso los desfavorables: una sola región en el mapa del SOM, etapa 2 "no robusta",
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

- **Slides**: 25 slides armadas por `make deliverables` en `analysis/results/slides/`; publicadas como Artifact tipo Slides (republicado el 2026-10-28 con la slide `pca-prune`).
- **Informe**: `analysis/results/informe/informe.html`, publicado como Artifact HTML (D-15).
- Slides: https://claude.ai/artifact/CxnuCZKwF55r2tUMPWXBSN (las URLs `9YjSx…` y `32SjY…` de antes ya no existen; el 2026-10-28 se reemplazó el contenido de este deck por las 25 slides del repo)
- Informe: https://claude.ai/artifact/ScERzQ4wTc8TrCNfuw2kKq (republicado el 2026-10-28 con el guion de las 25 slides en el anexo; está compartido por link)
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

- **Volver a exportar el PDF del deck** desde su Artifact (lo hace la persona dueña): el deck se republicó el 2026-10-26 y el PDF
  exportado antes no tiene la slide `som-rule` corregida.
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
