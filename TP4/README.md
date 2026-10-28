# TP4 SIA: aprendizaje no supervisado y memoria asociativa

TP4 de Sistemas de Inteligencia Artificial (ITBA, 2026, Grupo 9). Dos ejercicios, con los algoritmos escritos a mano en C
y el análisis en Python:

1. **Creadores de contenido** (`datos/creadores.csv`, 50 creadores, 31 variables): EDA y PCA, red de Kohonen (SOM), regla de
   Oja y decisiones de campaña (fútbol, perros, maquillaje, arte).
2. **Memoria asociativa**: red de Hopfield sobre 4 letras de 5×5 (ortogonalidad, capacidad, estado espurio) y sobre los 5 QR
   de 37×37 (ruido, energía, límites del caso de uso).

Se entregan el código, un fragmento de análisis por fase en `deliverables/`, las slides y el informe (los dos últimos como
Artifacts). Los resultados generados (`analysis/results/`, `datos/prepared/`) no se versionan: este archivo dice cómo
regenerar cada figura y cada tabla que muestran las slides y el informe.

## Requisitos

- Python 3.12, `make` (GNU Make 3.81 alcanza) y un compilador de C (`gcc` o `clang`).
- `uv` es opcional. Con `uv`, `make venv` crea `.venv` con `uv venv` y `uv pip install`. Sin `uv`, el mismo target cae a pip y
  hace lo siguiente (podés correrlo a mano):

```
python3.12 -m venv .venv
.venv/bin/python -m pip install -r analysis/requirements.txt
touch .venv/.installed
```

Las versiones están fijadas en `analysis/requirements.txt` (numpy, matplotlib, Pillow, pytest y Markdown). El README no instala
nada más.

## Inicio rápido

Todo desde `TP4/`:

```
make venv           # crea .venv e instala analysis/requirements.txt
make                # venv + datos/prepared/ + compila neuron/build/neuron
make results        # regenera SOLO los resultados de las fases 1 a 5 que faltan
make deliverables   # results + figuras de slide que falten, y arma las slides y el informe
make test           # tests de C y de Python
```

`make results` es idempotente: cada paso tiene un archivo centinela y, si existe, el paso no se vuelve a correr. En esta
máquina (sin `uv`, con el SOM ya hecho) los 12 pasos que faltaban tardaron unos 11 minutos (653 s). Desde cero se suman la etapa
1 del SOM (140 corridas) y la etapa 2, así que el primer `make results` de un clone nuevo tarda bastante más. Un segundo
`make results` no hace nada, y `make deliverables` sobre un árbol completo solo rearma slides e informe, en segundos.

## Cómo forzar un paso

Para repetir un paso hay que borrar su carpeta de resultados y volver a correr `make results`, por ejemplo:

```
rm -rf analysis/results/oja
make results
```

Un centinela viejo no detecta que el código cambió: si cambiaste un script, borrá la carpeta del paso. Los drivers tienen
guardas (la regla pre-registrada y el código de selección están commiteados y se verifican por sha256) y se niegan a correr si
la regla cambió; `make results` no las saltea. Si una guarda se niega, el camino es discutir el cambio de la regla, nunca editar
la regla en el lugar ni tocar el hash para que corra.

Pasos individuales (cada uno escribe en `analysis/results/`): `make eda`, `make pca`, `make corr-prune`, `make som-stage1`, `make som-stage2`,
`make som-figures`, `make som-profiles`, `make oja`, `make campaigns`, `make maintenance`, `make letters`,
`make hopfield-letters`, `make hopfield-figures`, `make qr`, `make hopfield-qr`, `make hopfield-qr-limits` y
`make hopfield-qr-figures`. Algunos arrastran sus prerrequisitos: `make campaigns` y `make maintenance` vuelven a correr la etapa 1
del SOM, que es lenta.

## Figuras

Una fila por cada figura que muestran el informe y las slides (31). Todas son deterministas dada su seed y su config. Las filas
marcadas con `slide/` tienen además una variante para las slides, en la carpeta `slide/` junto a la figura; la dibuja el mismo
comando. Las filas salen del manifiesto `analysis/deliverables_manifest.py` y `make test` verifica que sigan en sync.

| Figura | Fragmento | Comando | Config | Seed |
|---|---|---|---|---|
| `analysis/results/eda/distributions.svg` | `01-datos-pca.md` §2 | `make eda` | datos/creadores.csv (analysis/eda.py, sin config) | sin seed (determinista) |
| `analysis/results/eda/correlation.svg` | `01-datos-pca.md` §2 | `make eda` | datos/creadores.csv (analysis/eda.py, sin config) | sin seed (determinista) |
| `analysis/results/pca/audited/eigenvalues_variance.svg` (y `slide/`) | `01-datos-pca.md` §6 | `make pca` | datos/prepared/creadores_zscore.csv (make prepare) | sin seed (determinista) |
| `analysis/results/pca/audited/loadings.svg` | `01-datos-pca.md` §6 | `make pca` | datos/prepared/creadores_zscore.csv (make prepare) | sin seed (determinista) |
| `analysis/results/pca/audited/biplot.svg` (y `slide/`) | `01-datos-pca.md` §6 | `make pca` | datos/prepared/creadores_zscore.csv (make prepare) | sin seed (determinista) |
| `analysis/results/som/figures/map.svg` (y `slide/`) | `02-kohonen.md` §5 | `make som-figures` | analysis/series_som_stage1.json | 4 (figure_seed de selection.json) |
| `analysis/results/som/figures/planes_main.svg` | `02-kohonen.md` §5 | `make som-figures` | analysis/series_som_stage1.json | 4 (figure_seed de selection.json) |
| `analysis/results/som/figures/planes_appendix.svg` | `02-kohonen.md` §5 | `make som-figures` | analysis/series_som_stage1.json | 4 (figure_seed de selection.json) |
| `analysis/results/som/figures/trace.svg` | `02-kohonen.md` §5 | `make som-figures` | analysis/series_som_stage1.json | 4 (figure_seed de selection.json) |
| `analysis/results/som/figures/stage1_curves.svg` (y `slide/`) | `02-kohonen.md` §3 | `make som-figures` | analysis/series_som_stage1.json | 1-10 (las seeds de la serie; la media y el desvío entre ellas) |
| `analysis/results/som/profiles/regions.svg` (y `slide/`) | `02-kohonen.md` §6.1 | `make som-profiles` | analysis/series_som_stage1.json | 4 (figure_seed de selection.json) |
| `analysis/results/som/profiles/pc_planes.svg` (y `slide/`) | `02-kohonen.md` §6.4 | `make som-profiles` | analysis/series_som_stage1.json | 4 (figure_seed de selection.json) |
| `analysis/results/oja/convergence.svg` | `03-oja-campanas.md` §1 | `make oja` | analysis/series_oja.json | 1 (la seed que produce las figuras; la serie corre las seeds 1-10) |
| `analysis/results/oja/oja_vs_pc1.svg` (y `slide/`) | `03-oja-campanas.md` §2 | `make oja` | analysis/series_oja.json | 1 (la seed que produce las figuras; la serie corre las seeds 1-10) |
| `analysis/results/campaigns/shortlists_biplot.svg` (y `slide/`) | `03-oja-campanas.md` §5.6 | `make campaigns` | deliverables/03-oja-campanas.md sección 4 (analysis/campaigns_select.py) | 1 (índice de Oja) y 4 (mapa del SOM) |
| `analysis/results/campaigns/shortlists_som.svg` (y `slide/`) | `03-oja-campanas.md` §5.6 | `make campaigns` | deliverables/03-oja-campanas.md sección 4 (analysis/campaigns_select.py) | 1 (índice de Oja) y 4 (mapa del SOM) |
| `analysis/results/hopfield/figures/letters.svg` (y `slide/`) | `04-hopfield-letras.md` §2 | `make hopfield-figures` | deliverables/04-hopfield-letras.md sección 3 (analysis/hopfield_select.py) | sin seed (alfabeto fijo) |
| `analysis/results/hopfield/figures/overlaps.svg` (y `slide/`) | `04-hopfield-letras.md` §4 | `make hopfield-figures` | deliverables/04-hopfield-letras.md sección 3 (analysis/hopfield_select.py) | sin seed (alfabeto fijo) |
| `analysis/results/hopfield/figures/max_overlap_hist.svg` | `04-hopfield-letras.md` §4 | `make hopfield-figures` | deliverables/04-hopfield-letras.md sección 3 (analysis/hopfield_select.py) | sin seed (alfabeto fijo) |
| `analysis/results/hopfield/figures/cross_terms.svg` | `04-hopfield-letras.md` §4 | `make hopfield-figures` | deliverables/04-hopfield-letras.md sección 3 (analysis/hopfield_select.py) | sin seed (alfabeto fijo) |
| `analysis/results/hopfield/figures/recall_noise.svg` (y `slide/`) | `04-hopfield-letras.md` §5 | `make hopfield-figures` | deliverables/04-hopfield-letras.md sección 3 (analysis/hopfield_select.py) | 1-10 |
| `analysis/results/hopfield/figures/energy.svg` | `04-hopfield-letras.md` §5 | `make hopfield-figures` | deliverables/04-hopfield-letras.md sección 3 (analysis/hopfield_select.py) | 1 (ENERGY_SEED de analysis/hopfield_figures.py) |
| `analysis/results/hopfield/figures/capacity_p4.svg` (y `slide/`) | `04-hopfield-letras.md` §6 | `make hopfield-figures` | deliverables/04-hopfield-letras.md sección 3 (analysis/hopfield_select.py) | 1-10 |
| `analysis/results/hopfield/figures/capacity_by_p.svg` | `04-hopfield-letras.md` §6 | `make hopfield-figures` | deliverables/04-hopfield-letras.md sección 3 (analysis/hopfield_select.py) | 1-10 |
| `analysis/results/hopfield/figures/spurious.svg` (y `slide/`) | `04-hopfield-letras.md` §7 | `make hopfield-figures` | deliverables/04-hopfield-letras.md sección 3 (analysis/hopfield_select.py) | 1-10 |
| `analysis/results/hopfield/qr/figures/qr.svg` (y `slide/`) | `05-hopfield-qr.md` §2 | `make hopfield-qr-figures` | deliverables/05-hopfield-qr.md sección 3 (analysis/hopfield_qr_select.py) | sin seed (los 5 QR son fijos) |
| `analysis/results/hopfield/qr/figures/overlaps.svg` (y `slide/`) | `05-hopfield-qr.md` §2 | `make hopfield-qr-figures` | deliverables/05-hopfield-qr.md sección 3 (analysis/hopfield_qr_select.py) | sin seed (los 5 QR son fijos) |
| `analysis/results/hopfield/qr/figures/energy_trace.svg` (y `slide/`) | `05-hopfield-qr.md` §4 | `make hopfield-qr-figures` | deliverables/05-hopfield-qr.md sección 3 (analysis/hopfield_qr_select.py) | 1 (ENERGY_TRACE_SEED de analysis/hopfield_qr.py) |
| `analysis/results/hopfield/qr/figures/recovery.svg` (y `slide/`) | `05-hopfield-qr.md` §5 | `make hopfield-qr-figures` | deliverables/05-hopfield-qr.md sección 3 (analysis/hopfield_qr_select.py) | 1-10 |
| `analysis/results/hopfield/qr/figures/majority.svg` (y `slide/`) | `05-hopfield-qr.md` §6 | `make hopfield-qr-figures` | deliverables/05-hopfield-qr.md sección 3 (analysis/hopfield_qr_select.py) | sin seed (atractor mayoría determinista) |
| `analysis/results/hopfield/qr/figures/shift.svg` (y `slide/`) | `05-hopfield-qr.md` §6 | `make hopfield-qr-figures` | deliverables/05-hopfield-qr.md sección 3 (analysis/hopfield_qr_select.py) | 1 (SHIFT_SEED de analysis/hopfield_qr_limits.py) |

## Tablas

Las tablas principales y el comando que las escribe (todas bajo `analysis/results/`):

| Tabla | Qué es | Comando |
|---|---|---|
| `eda/audit_table.md` | Auditoría de las 31 variables: cuáles entran y por qué | `make eda` |
| `pca/audited/decision.json` | Autovalores, 80 % acumulado, componentes retenidas | `make pca` |
| `corr_prune/sensitivity.json` | Sensibilidad de la PCA a podar por umbral de |r| (variables que quedan, k, PC1, autovalor mínimo, condición); tabla de la slide `pca-prune` | `make corr-prune` |
| `som/series_som_stage1/selection.json` | Grilla elegida por la regla fijada de antemano (etapa 1) | `make som-stage1` |
| `som/series_som_stage2/robustness.json` | Robustez del schedule sobre la grilla elegida (etapa 2) | `make som-stage2` |
| `campaigns/shortlists.csv` | Lista de creadores por campaña con la regla commiteada | `make campaigns` |
| `campaigns/comparison.csv` | Comparación contra la línea base por `followers` | `make campaigns` |
| `hopfield/letters/recall.csv` | Recuperación de las letras por nivel de ruido, 10 seeds | `make hopfield-letters` |
| `hopfield/qr/recovery_table.csv` | Recuperación exacta de los 5 QR por regla (Hebb, pseudo-inversa, Hamming) y nivel de ruido | `make hopfield-qr` |
| `hopfield/qr/verdict.json` | Veredicto del protocolo pre-registrado: Hebb falla, pseudo-inversa funciona | `make hopfield-qr` |

Los números del texto de las slides y del informe no se tipean: salen de estos JSON y CSV (`analysis/facts.py`), y el informe
no se arma si un número citado de los fragmentos cambió.

## Slides e informe

`make deliverables` deja listo, sin publicar, lo siguiente (no se versiona):

- `analysis/results/slides/`: el deck (`project/deck.json` y `project/slides/*.html`, 25 slides), los PNG de las figuras
  (`assets/`) y `notes.md` (el guion). Lo arma `analysis/slides.py`; `make slides` corre solo ese paso.
- `analysis/results/informe/informe.html`: el informe, una página autocontenida. Lo arma `analysis/informe.py`; `make informe`
  corre solo ese paso.

Dos corridas seguidas de `make deliverables` dejan idénticos byte a byte el informe y todos los archivos de las slides.

**Publicación (paso manual, la hace una sesión de Claude con la herramienta Artifact; el formato probado está en
`.planning/phases/06-slides-e-informe/06-ARTIFACT-FORMAT.md`):**

1. Slides (tipo Slides). Subir los 15 PNG de `analysis/results/slides/assets/` como assets (hasta 25 por llamada); cada subida
   devuelve una url `/_blob/<id>`. Con esas urls escribir `asset_map.json` (`{"som_map.png": "/_blob/<id>", ...}`) y rearmar
   con `.venv/bin/python analysis/slides.py --asset-map asset_map.json`; sin esa opción las imágenes apuntan a los archivos
   locales y sirven solo para mirar el deck en la compu. Publicar una vez a la url del deck con `root` =
   `analysis/results/slides`, `file_path` = `<root>/project/deck.json` y `files` = `project/slides/*.html`. No se publican el
   `deck.json` de la raíz, `notes.md` ni `assets/`.
2. Informe (Artifact HTML). Publicar `analysis/results/informe/informe.html`.
3. Para actualizar, republicar a la misma url y el mismo archivo: así el link no cambia. Un PNG que cambió necesita una subida
   nueva y republicar la slide que lo usa.
4. Las slides quedan privadas (se leen solo con la cuenta dueña); el informe se entrega compartiendo el link del Artifact desde
   el menú Share de la página, un paso que solo puede hacer la persona dueña.

Las slides se publican como Artifact y al docente se le entrega el PDF que exporta ese Artifact (D-14). Ese PDF queda fuera
del repo: no se versiona ni en `docs/` ni en `deliverables/`, y se vuelve a exportar del Artifact después de republicarlo.
El informe llega como el link compartido del Artifact (D-15); no se usa el tipo Docs. Las notas del orador viajan en cada slide y también en
`notes.md`. El informe lleva además el guion como anexo "Guion de la presentación": `make deliverables` pasa
`INFORME_FLAGS := --notes analysis/results/slides/notes.md` (el `make informe` suelto arma el informe sin el anexo).

## Entrega

- Slides: https://claude.ai/artifact/9YjSxsDcVYSwvnXaD5JVy1
- Informe: https://claude.ai/artifact/32SjYXD12gS2Lh6vY22jyM

Los dos Artifacts son privados; el deck se entrega como su PDF exportado (no se versiona en `docs/`), y compartir el link del informe lo decide la persona dueña desde el menú Share. Lo entregable se regenera con `make deliverables`.

## Dónde seguir

- `CLAUDE.md`: estado del TP, árbol del código, trampas y convenciones (es el punto de partida de una sesión nueva).
- `DECISIONS.md`: cada decisión que nos pueden preguntar en la defensa, con su porqué y dónde quedó registrada.
- `deliverables/`: un fragmento por fase (datos y PCA, Kohonen, Oja y campañas, Hopfield letras, Hopfield QR) con su sección
  "Cómo reproducir".
- `analysis/README.md` (series de corridas y drivers) y `neuron/README.md` (el binario en C y su config).
