# Phase 6: Slides e informe - Research

**Researched:** 2026-10-25
**Domain:** Deliverable assembly (Artifact slides + Artifact report + reproduction docs) on top of a finished C/Python pipeline
**Confidence:** MEDIUM overall. HIGH on repo facts (read this session). MEDIUM on the report path. LOW on the Slides Artifact type: the researcher had no `Artifact` tool, so the type's input format and speaker-notes support are NOT verified (see "Open Questions" and "Who does what").

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Presentación de **~20 minutos, ~20-25 slides**. Reparto aproximado: Ej. 1 (EDA/PCA, Kohonen, Oja, campañas) ~12-14 slides; Ej. 2 (letras, QR) ~7-9 slides. Una idea por slide.
- **D-02:** Orden **por método** (PCA → SOM → Oja → campañas → letras → QR), con **título-conclusión** en cada slide (el título dice la conclusión, no el tema: «El mapa sigue a PC1 pero no a PC2», no «Matriz U»). La pregunta del enunciado que responde la slide puede ir en chico, pero no ordena el guion.
- **D-03:** El rigor metodológico entra como **una slide de método** al principio (reglas fijadas y commiteadas antes de ver resultados con guardia sha256, 10 seeds, nulos por permutación) y después **menciones cortas** en cada resultado (p. ej. «regla fijada de antemano»). El detalle de cada regla queda en el informe.
- **D-04:** Los resultados poco favorables van **de frente, con slide propia y título-conclusión**, más una línea del porqué: una sola región en el SOM (R1 = 50) con la regla fijada, etapa 2 «no robusta», Hebb 0 % de recuperación exacta en los QR (solapamiento medio 0,67), y el lookup de Hamming 1-NN que iguala o supera a la pseudo-inversa con ruido alto. Coherente con la Key Decision de PROJECT.md «reportar el resultado de la regla tal cual».
- **D-05:** Campañas en ~4 slides: **fútbol aparte** (alcance masivo / descubrimiento / profundidad educativa y la recomendación), **una tabla resumen** para perros, maquillaje y arte (criterio, top-5, costo por mil argentinos), **una slide de comparación contra solo `followers`** y **una de mantenimiento**.
- **D-06:** Cada slide lleva **notas del orador**: 2-4 frases de qué decir y los números clave para responder preguntas. El cuerpo visible queda limpio. Si el formato Slides no soporta notas, el planner propone el equivalente más cercano y lo informa.
- **D-07:** Apertura con **portada** (TP4 SIA, Grupo 9) y la **slide de método** (D-03). Cada ejercicio **cierra con su propia slide de conclusiones**: Ej. 1 dice qué aporta cada método a la decisión de campaña y Ej. 2 dice qué limitaciones tiene Hopfield para los QR. **No hay agenda ni cierre general.**
- **D-08:** Las figuras de las slides son una **variante «slide» del mismo código matplotlib** que ya dibuja las del informe: la misma función de datos con otro estilo (letra más grande, menos anotaciones, proporción para 16:9). Los datos se calculan una vez y se dibujan dos (patrón de `.planning/research/ARCHITECTURE.md`). No se pintan gráficos a mano en HTML como en TP3. — **Reversibility:** costly.
- **D-09:** El informe es **todo estático**: se usan los SVG de matplotlib existentes, inline. No lleva plotly, JS de gráficos ni CDN para las figuras.
- **D-10:** Tema: cada figura va **siempre sobre un panel claro** (tarjeta con el fondo `SURFACE` de `analysis/plots_style.py` y borde), también en modo oscuro. La página alrededor sí cambia de tema. Hay una sola versión de cada figura y no se generan variantes oscuras.
- **D-11:** El armado es **por script + `make`**. Un target (p. ej. `make deliverables`, o `make slides` + `make informe`) regenera los resultados que faltan, dibuja las figuras de informe y de slide, y escribe el HTML del informe y los archivos de datos de las slides, listos para publicar. **Los números del texto se leen de los JSON/CSV de `analysis/results/` y no se tipean a mano.** La publicación de los Artifacts es manual (un paso aparte que se documenta). — **Reversibility:** costly.

### Claude's Discretion
El usuario eligió no discutir el formato del informe ni los documentos de reproducción. Quedan a criterio del researcher/planner, con estos defaults:
- **Formato del informe:** página HTML autocontenida publicada como Artifact, generada por script desde los resultados (PROJECT.md Key Decision y `.planning/research/STACK.md` §Deliverables). Existe también el tipo de Artifact «Docs» (editable, exporta a PDF/.docx); usarlo solo si el planner encuentra una razón fuerte y la informa. Hay que elegir si el informe reutiliza los fragmentos `deliverables/0X-*.md` (convertidos a HTML) o es una síntesis escrita aparte. Lo que importa es que el texto no diverja de los fragmentos ni de los números.
- **Tabla pregunta→respuesta (DELIV-02):** cada pregunta **literal** del enunciado (`docs/Archivo SIATP 42026.pdf`), con un link a la sección del informe donde se responde y, si conviene, la slide. La forma de la tabla queda libre.
- **Slides:** usar el tipo de Artifact **Slides** (16:9, se exporta a .pptx/PDF), siguiendo las instrucciones que da el tipo al crearlo y su design system por defecto (no se elige paleta a mano). Las figuras de matplotlib se insertan como SVG/imagen dentro de ese formato. Verificar en la investigación cómo el tipo recibe los datos y si soporta notas del orador (blocker abierto en STATE.md).
- **Documentos de reproducción (DELIV-03):** contenido de `CLAUDE.md` (punto de partida para una sesión nueva, como el de TP3 en el commit `7ff59c3`), `DECISIONS.md` (consolida las decisiones D-xx de las 5 fases y las Key Decisions, con link a cada CONTEXT.md/fragmento) y `README.md` (comando, config y seed de cada figura y tabla; cómo armar slides e informe). Nota: en TP3 un compañero borró `CLAUDE.md` y `DECISIONS.md` el día de la entrega (commits `31958a4`, `bcce0da`). En TP4 son requisito (DELIV-03) y se versionan igual.
- Nombres de scripts (p. ej. `analysis/slides.py`, `analysis/informe.py`), de targets del Makefile y de la carpeta de salida (no versionada, como el resto de `analysis/results/`).
- Qué figuras exactas van a cada slide, dentro del presupuesto de D-01 y D-05.

### Deferred Ideas (OUT OF SCOPE)
None. La discusión no salió del alcance de la fase. (No se agregan análisis nuevos: todo el contenido sale de lo que ya producen las Fases 1-5.)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DELIV-01 | Slides en Artifact para presentar, una sección por ejercicio | "Slides" section: outline that fits D-01/D-05, figure inventory, slide-variant mechanism, notes fallback, publish checkpoint |
| DELIV-02 | Informe en Artifact con tabla que mapea cada pregunta del enunciado a dónde se responde | "Literal questions" table (Q1.1-Q2.8 with answering section), hybrid report architecture, anchor scheme, Artifact page contract |
| DELIV-03 | `CLAUDE.md`, `DECISIONS.md` y README con cómo reproducir cada resultado | "Reproduction docs" section, `make results`/`make deliverables` sentinel design, per-figure manifest, guard pitfalls, tests that fail if the docs are deleted |
</phase_requirements>

## Summary

Phase 6 adds no analysis. Its inputs are 5 Markdown fragments (`deliverables/01..05`, 178 KB, about 31 000 words), roughly 35 SVG/PNG figures written by 9 figure scripts, and JSON/CSV result files. The work is assembly: (1) a facts layer that reads numbers from `analysis/results/**`, (2) a per-figure manifest so every figure shown in slides or report is traceable to a `make` target, (3) a "slide" rendering variant of the existing matplotlib code, (4) an HTML report builder, (5) a slide builder, (6) three reproduction documents, (7) two manual publish steps.

Three findings change how the work should be planned. First, **the researcher could not exercise the Artifact tool**, so the Slides type's input format, canvas size and speaker-notes support are unknown. The plan must start with a probe run by the top-level session (it has the `Artifact` tool; executors may not). Second, **matplotlib SVGs cannot be pasted inline** into one HTML page: each carries a global `<style>` rule and non-unique ids (verified below), so the report must embed figures as `<img src="data:image/svg+xml;base64,...">`. This is a deviation from the literal word "inline" in D-09 that keeps its intent (static, no JS, no CDN). Third, **the long result chain is slow and its Make targets are all `.PHONY`** (one earlier `make hopfield-qr` took ~46 min), so `make deliverables` must use file-sentinel targets to "regenerate what is missing" instead of re-running everything each time.

**Primary recommendation:** Build the report as a hybrid. A generated front section (summary + the question-to-answer table + method) whose numbers come from a `facts` loader, followed by the five existing fragments converted to HTML with Python-Markdown (pinned, human-verified install) as "detalle por fase". Guard the numbers hand-typed inside the fragments with a curated drift test against the JSON. Slides are generated from a Python outline plus the same facts. Publishing is a final checkpoint executed by the top-level session.

## Project Constraints (from CLAUDE.md)

No `./CLAUDE.md` or `./.claude/CLAUDE.md` exists in TP4 (checked: `ls` of the repo root shows neither; `.planning/config.json` has `"claude_md_path": "./.claude/CLAUDE.md"` but no `.claude/` directory exists). No project skills directories exist (`.claude/skills/`, `.agents/skills/` absent). Inherited conventions that the planner should treat as locked, taken from CONTEXT.md and the TP3 precedent `git show 7ff59c3:TP3/CLAUDE.md` [CITED]:
- Text in Spanish rioplatense with **decimal comma** and without "mejor" for the Oja index (03-CONTEXT D-06 via 06-CONTEXT code_context).
- All identifiers, file names and directories in English; prose (README, docs) in Spanish (TP3 CLAUDE.md "Convenciones").
- Algorithms (Kohonen, Oja, Hopfield) by hand in C; external libraries only for I/O, arrays and plots (TP3 CLAUDE.md; PROJECT.md Out of Scope). The new `markdown` dependency is a report-rendering library, not an ML library, so it does not conflict.
- Results under `analysis/results/` are not versioned (`analysis/.gitignore` contains `results/`).
- **Location decision needed:** put the new file at `TP4/CLAUDE.md` (what TP3 did, what Claude Code auto-loads when launched in `TP4/`, and what DELIV-03 names literally). The GSD config points at `./.claude/CLAUDE.md`; either update that config key or accept that GSD would create a second file. [ASSUMED] A10.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Numbers shown in text | Python `analysis/facts.py` reading `analysis/results/**` | Fragments `deliverables/*.md` (hand-typed, guarded by test) | D-11: numbers come from JSON/CSV, never typed in new text |
| Figure drawing (report variant and slide variant) | Existing matplotlib scripts + `plots_style.py` | Manifest mapping figure to make target | D-08: same code, two styles |
| Report HTML | Python builder `analysis/informe.py` (stdlib + Markdown) | Artifact tool (publish only) | D-11: script builds, publishing is manual |
| Slide content files | Python builder `analysis/slides.py` | Artifact Slides type (publish only) | Slides type input format is unverified |
| Publishing the two Artifacts | Top-level session (has `Artifact` tool) | Human reviewing the live page | Executors may lack the tool |
| Reproduction docs | Hand-written `README.md`, `CLAUDE.md`, `DECISIONS.md` | pytest that fails if missing or if a documented `make` target does not exist | TP3 lost its docs on delivery day |
| "Regenerate missing results" | Root `Makefile` file-sentinel targets | `sweep.py`-style drivers (already exist) | All current targets are `.PHONY`, so plain dependency chaining re-runs everything |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12.15 (`.venv`) | all builders | already the project interpreter [VERIFIED: `.venv/bin/python --version` printed `Python 3.12.15`] |
| matplotlib | 3.11.2 (pinned) | report and slide figures, SVG with `svg.fonttype=path` | already pinned in `analysis/requirements.txt`; D-08/D-09 |
| Pillow | 13.0.0 (pinned) | only if a PNG fallback is needed | already pinned |
| pytest | 9.1.1 (pinned) | tests of the builders | already pinned; baseline 230 tests pass in ~14 s [VERIFIED: ran `pytest analysis/tests -q`, `230 passed in 14.37s`] |
| Python-Markdown (`markdown`) | **3.11** (pin; 3.11.2 is 6 days old) | convert the five fragments to HTML (`tables`, `fenced_code`, `toc`) | fragments use headings, pipe tables, lists, fenced blocks, bold, code spans; no nested lists and no list directly after a paragraph (checked by script), which are the cases where Python-Markdown differs from CommonMark. Use of `toc` slugify is documented [CITED: python-markdown.github.io/extensions/toc/] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| stdlib `html`, `json`, `csv`, `base64`, `hashlib`, `subprocess` | - | escaping, facts, data URIs, git stamp | always; no extra dependency |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Python-Markdown | a ~80-line own converter | rejected: hand-rolling a Markdown converter ("Don't Hand-Roll"); only choose it if the human refuses the new dependency |
| Python-Markdown | `markdown-it-py` 4.x / `mistune` | both flagged SUS by the seam as well (see audit); CommonMark-compliant, but no advantage for these fragments |
| Own synthesis text for the whole report | hybrid (recommended) | a full rewrite risks divergence from fragments and loses the detail the fragments carry; see Architecture Pattern 1 |
| HTML Artifact report | "Docs" Artifact type | Docs exports to PDF/.docx and is editable, but figures there are expected as rows or uploaded files and 31 k words of fragments would need a new conversion path; no strong reason found. Revisit only if the teacher asks for PDF/Word (Open Question 4) |
| Python `plotly` JS in the report | none | out by D-09 |

**Installation:**
```bash
# analysis/requirements.txt gets one new line:  Markdown==3.11
# NOTE: uv is NOT installed on this machine (see Environment Availability), so `make venv`
# will fail once requirements.txt changes. Use the documented fallback:
.venv/bin/python -m pip install -r analysis/requirements.txt && touch .venv/.installed
```

**Version verification:** `curl https://pypi.org/pypi/markdown/json` this session: 64 releases, first 1.7 on 2008-02-18, 3.11 on 2026-09-25, 3.11.1 on 2026-10-13, 3.11.2 on 2026-10-19, `requires_python >=3.11`, repository `github.com/Python-Markdown/markdown` [VERIFIED: PyPI JSON API]. Weekly downloads 26 576 225 [CITED: pypistats.org/api/packages/markdown/recent].

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| markdown | PyPI | first release 2008-02-18 (about 18 yrs); latest 2026-10-19 | 26.6M/week (pypistats) ; the seam reports `unknown-downloads` | github.com/Python-Markdown/markdown | SUS (reasons `too-new`, `unknown-downloads`: the seam judged the 2026-10-19 release date, not the project age) | `Markdown==3.11` `[WARNING: flagged as suspicious by the legitimacy seam - verify before using.]` Planner must add a `checkpoint:human-verify` before installing; pin an older release (3.11, 30 days old), not 3.11.2 |
| mistune | PyPI | - | unknown | github.com/lepture/mistune | SUS (`too-new`, `unknown-downloads`) | Not recommended (alternative only) |
| markdown-it-py | PyPI | - | unknown | github.com/executablebooks/markdown-it-py | SUS (`unknown-downloads`) | Not recommended (alternative only) |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** `markdown` (recommended, behind a human-verify checkpoint), `mistune`, `markdown-it-py` (not recommended)

`gsd_run query package-legitimacy check --ecosystem pypi markdown mistune markdown-it-py` was run this session; `postinstall: null` for all three (not applicable to PyPI wheels). Package-name provenance: `markdown` was named from training knowledge and cross-checked against the PyPI JSON (project_urls point to Python-Markdown.github.io) and the official docs pages fetched above; because the seam returned SUS, the install stays gated. [ASSUMED] for the claim that "no hidden build step runs": wheels have no install-time scripts, but the human should glance at the PyPI page.

## Architecture Patterns

### System Architecture Diagram

```
 results chain (slow, run once)                       fast assembly (re-runnable in seconds)
 ------------------------------                       -------------------------------------------------
 make results  (file-sentinel targets)                 make deliverables
   venv -> prepare -> eda -> pca                          |
   -> som-stage1 -> som-stage2 -> som-figures             |  1. check sentinels (fail with exact make cmds)
   -> som-profiles -> oja -> campaigns -> maintenance     |  2. redraw "slide" variant of every figure
   -> letters -> hopfield-letters -> hopfield-figures     |     (figure scripts loop over variants)
   -> qr -> hopfield-qr -> hopfield-qr-limits             v
   -> hopfield-qr-figures                          analysis/facts.py  <-- reads JSON/CSV in analysis/results/**
        |                                                  |
        v                                                  v
 analysis/results/**  (JSON, CSV, SVG, PNG)         analysis/deliverables_manifest.py
   not versioned (analysis/.gitignore: results/)      (questions Q1.1.., figures -> make target,
        |                                              slide outline: title, figure key, notes template)
        +----------------------+---------------------------+
                               |                           |
                               v                           v
                    analysis/informe.py          analysis/slides.py
                    front section (facts)        one slide file per outline entry
                    + 5 fragments via Markdown   + notes (facts) + figure <img>
                    + figures as data-URI <img>  + notes.md (fallback / annex)
                    + question table w/ anchors
                               |                           |
                               v                           v
              analysis/results/informe/informe.html   analysis/results/slides/*
                               |                           |
                               +-----------+---------------+
                                           v
                          CHECKPOINT (top-level session, Artifact tool)
                          quickstart(slides) -> publish slides; publish informe;
                          read back; human opens both URLs; URLs recorded in README/CLAUDE.md
```

### Recommended Project Structure
```
analysis/
├── facts.py                  # read JSON/CSV -> dict of display strings (decimal comma); the only place that formats numbers
├── deliverables_manifest.py  # QUESTIONS, FIGURES (key, svg path, make target, slide size), SLIDES outline
├── informe.py                # builds analysis/results/informe/informe.html
├── slides.py                 # builds analysis/results/slides/ (format fixed after the Wave 0 probe)
├── plots_style.py            # gains: variant state, caption helper, slide font scale (see Pattern 3)
└── tests/
    ├── test_facts.py
    ├── test_deliverables_manifest.py
    ├── test_informe.py
    ├── test_slides.py
    └── test_repro_docs.py    # fails if README/CLAUDE.md/DECISIONS.md are missing or document a make target that does not exist
README.md                     # new (TP4 has none at the root today)
CLAUDE.md                     # new
DECISIONS.md                  # new
.planning/phases/06-slides-e-informe/06-ARTIFACT-FORMAT.md   # output of the Wave 0 probe
```

### Pattern 1: Hybrid report (recommended)
**What:** `informe.html` = (a) generated front matter: 8-line "Qué encontramos" summary, the DELIV-02 table, one "Cómo trabajamos" block (pre-registered rules, sha256 guard, 10 seeds, permutation nulls); numbers via `facts`. (b) "Ejercicio 1" with fragments 01, 02, 03 and "Ejercicio 2" with 04, 05 converted to HTML and titled "Detalle técnico (Fase N)". (c) A build stamp (short git HEAD, dirty flag; no date, so the file stays byte-stable).
**Why:** The fragments are the verified record (each went through verification) and already contain the answers; rewriting 31 000 words risks divergence. D-11's "numbers are not typed" is honoured for everything new; for the fragments, a **curated drift test** pins about 25 key numbers (for example `r2_pc1` 0,961, `chosen_k` 5, `n_regions` 1, Hebb 0 % exact recovery, mean overlap 0,67) by formatting the JSON value and asserting it appears in the fragment.
**Risk:** the fragments contain internal jargon the reader of a report should not see: 131 `D-NN` references, 9 `Pitfall N`, and requirement IDs (`HOP-04`...) [VERIFIED: grep counts per file]. Mitigation options for the planner: (i) leave as is, with `DECISIONS.md` defining `D-NN`; (ii) a render-time pass that links `D-NN` to a glossary anchor. Do not edit the fragments (see Pitfall 1).
**When to use:** default. If the human wants a pure synthesis, D-11 still holds but divergence from fragments becomes a manual-review burden.

### Pattern 2: Question table with stable anchors
**What:** `QUESTIONS` in the manifest holds `id`, literal text, answering fragment and heading number, optional slide number. The builder derives anchors from heading numbers with a custom `slugify` passed to the `toc` extension: heading `### 6.4 ...` of fragment 2 becomes `id="f2-s6-4"`. Only plain anchors (letters, digits, `.`, `_`, `~`, `-`) reach `location.hash` inside an Artifact [CITED: Artifact page contract in the loaded `artifact-design` skill], so ids must stay in that alphabet. Duplicate headings get `_1` suffixes from Python-Markdown (underscore is allowed) [CITED: python-markdown.github.io/extensions/toc/].
**Test:** every `QUESTIONS` entry resolves to an `id=` present in the generated HTML; every literal question text is non-empty.

### Pattern 3: One figure code, two variants (D-08)
**What:** add module state to `analysis/plots_style.py`: `use_variant("report"|"slide")`, `caption(fig, text)` (no-op in slide), and a slide font scale applied inside `apply_style()`. `save_figure` writes to `<dir>/` for report and `<dir>/slide/` for slide, and for slide can call `fig.set_size_inches(*SLIDE_SIZE[stem])` from the manifest before `savefig`. Each figure script's `main` loops `for variant in ("report", "slide")` over the plot calls after computing data once.
**Where the seam already exists:** `som_figures.py`, `som_profiles.py`, `hopfield_figures.py`, `hopfield_qr_figures.py` read result files and only draw, so they can be re-run in seconds. `eda.py`, `pca.py`, `oja.py`, `campaigns.py` compute and plot in one `main`, so the loop must wrap the plot calls inside `main` (data stays computed once).
**Findings that constrain it:** every `plot_*` hard-codes `figsize` (for example `plt.subplots(1, 2, figsize=(11.5, 6.4))` in `som_figures.py`, `figsize=(21, 17)` for the EDA distributions) and three scripts carry their own 125-character `_caption(fig, text, ...)` helper (`som_figures.py`, `hopfield_figures.py`, `hopfield_qr_figures.py`). A pure `rcParams` change cannot fix either; the variant must also override size and suppress captions. Some figures are not slide material at all (26-panel `planes_appendix`, 6x6 `distributions`); keep them report-only.
**Guard safety:** none of `plots_style.py`, `som_figures.py`, `som_profiles.py`, `hopfield_figures.py`, `hopfield_qr_figures.py`, `oja.py`, `campaigns.py`, `pca.py`, `eda.py` is in a hashed code set. Verified hashed sets: `hopfield_qr.py` `CODE_FILES = ("neuron/models/hopfield.c", "neuron/models/hopfield_core.c", "neuron/models/hopfield_core.h", "neuron/io/config.c", "analysis/hopfield.py", "analysis/hopfield_qr.py")`; `hopfield_letters.py` same list with `analysis/hopfield_letters.py`; `hopfield_qr_limits.py` `LIMITS_CODE_FILES = ("analysis/hopfield_qr_limits.py", "analysis/hopfield.py")`. **Editing any of those files invalidates the Hopfield results and their figure scripts refuse to draw** (rerun cost up to ~46 min).

### Pattern 4: Embed figures as `<img>` data URIs, not inline `<svg>`
Matplotlib SVG verified this session in `analysis/results/som/figures/map.svg`: line 19 is `<style type="text/css">*{stroke-linejoin: round; stroke-linecap: butt}</style>` (a global `*` rule that would leak into the page), 241 `id=` attributes of the form `ytick_9` / `figure_1` / `patch_1` (these repeat across figures, so ids collide when several SVGs share a document), an XML prolog + DOCTYPE + RDF `<metadata>` block, and 4 embedded `<image` rasters. Loading each SVG through `<img src="data:image/svg+xml;base64,...">` isolates CSS and ids, embedded rasters still render, and an SVG in `<img>` cannot run scripts. The Artifact contract states a 16 MB page limit that counts data URIs and that images from `data:` URLs are fine [CITED: Artifact page contract]. Measured sizes of the 7 SOM SVGs: 59 KB to 294 KB each, about 940 KB in total [VERIFIED: `ls -la`]; 35 figures base64-encoded should land near 6 to 8 MB [ASSUMED] A4, so the builder asserts a size ceiling (for example 12 MB) and fails loudly.

### Pattern 5: File-sentinel targets for "regenerate what is missing" (D-11)
All existing targets are in `.PHONY` [VERIFIED: Makefile line 13]. A `deliverables: <phony chain>` would re-run everything every time (SOM stage 1 is 140 runs + about 7 000 LOO trainings; one `make hopfield-qr` took ~46 min). Add a `results` target made of real file targets, GNU Make 3.81 compatible (installed Make is GNU Make 3.81 [VERIFIED]):
```make
RES := analysis/results
$(RES)/pca/audited/decision.json: ; $(MAKE) pca
$(RES)/som/series_som_stage1/selection.json: ; $(MAKE) som-stage1
...
results: <all sentinels>          # idempotent: only runs steps whose sentinel is missing
deliverables: results             # then fast assembly
```
Sentinel files, each confirmed by reading the line that writes it:

| Step | Sentinel | Evidence |
|------|----------|----------|
| pca | `analysis/results/pca/audited/decision.json` | `pca.py:483` `(out / "decision.json").write_text(` |
| som-stage1 | `analysis/results/som/series_som_stage1/selection.json` | `som_stage.py:221` `_write_json(out / "selection.json", result)`; file exists locally |
| som-stage2 | `analysis/results/som/series_som_stage2/robustness.json` | `som_stage.py:254`; file exists locally |
| som-figures | `analysis/results/som/figures/map.svg` | exists locally |
| som-profiles | `analysis/results/som/profiles/pca_contrast.json` | exists locally |
| oja | `analysis/results/oja/index.csv` | `oja.py:645` `_write_table(out / "index.csv", ...` ; `campaigns.py:49` reads `analysis/results/oja/index.csv` |
| campaigns | `analysis/results/campaigns/selection_identity.json` | `campaigns.py:448` |
| maintenance | `analysis/results/maintenance/report_demo.md` | `maintenance_demo.py:232` |
| hopfield-letters | `analysis/results/hopfield/letters/selection.json` | `hopfield_letters.py:657`, `RESULTS_SUBDIR = Path("hopfield") / "letters"` |
| hopfield-figures | `analysis/results/hopfield/figures/spurious.svg` | figure list in `analysis/README.md` [CITED] |
| hopfield-qr | `analysis/results/hopfield/qr/verdict.json` | `hopfield_qr.py:621`, `RESULTS_SUBDIR = Path("hopfield") / "qr"` |
| hopfield-qr-limits | `analysis/results/hopfield/qr_limits/majority.json` | `hopfield_qr_limits.py:302` |
| hopfield-qr-figures | `analysis/results/hopfield/qr/figures/majority.svg` | deliverable 05 section 7 [CITED] |
| eda | `analysis/results/eda/audit_table.md` | deliverable 01 section 8 [CITED] |

Sentinels do not detect stale results after a code change; document `rm -rf analysis/results/<step>` as the way to force a step. Only the SOM results exist locally today (`analysis/results/` holds `som/` and three `series_*` folders, 20 MB), so the first full run is long. [ASSUMED] A5 for any total time estimate: the summaries report ~3 min for one Hopfield-QR run in Plan 05-03 and ~46 min in Plan 05-04 [CITED: 05-03-SUMMARY.md:250, 05-04-SUMMARY.md:264].

### Anti-Patterns to Avoid
- **Editing `deliverables/0X-*.md`** to fix links or jargon. `som_select.rule_guard` refuses to run SOM stages unless every guarded path (including `deliverables/02-kohonen.md`) is tracked and has no uncommitted change [VERIFIED: `som_select.py` `rule_guard`, `git status --porcelain` per path]; `campaigns_select.rule_identity` and the Hopfield guards also compare the text between markers. Do any text transformation at render time in the builder.
- **Inline `<svg>` of matplotlib output** (id collisions, global style leak).
- **Hand-typing numbers in new text** (D-11).
- **Making `deliverables` depend on the `.PHONY` chain directly** (re-runs 10 to 60 minutes every time).
- **Treating the Artifact as source of truth.** TP3 notes: the Artifact work folder "está en un directorio temporal que no sobrevive: no es fuente de verdad" [CITED: TP3 CLAUDE.md at 7ff59c3]. The source of truth is the generator plus `analysis/results`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Markdown to HTML (tables, lists, code) | regex converter | Python-Markdown (`tables`, `fenced_code`, `toc`) | table and span edge cases; but gated by the SUS checkpoint |
| Number formatting | ad-hoc `f"{x:.3f}".replace(".", ",")` in each script (there are already 6+ private `_decimal`/`_fmt` helpers in `oja.py`, `campaigns.py`, `som_profiles.py`, `maintenance_demo.py`...) | one `facts.py` formatter with unit tests | D-11 and the decimal-comma convention need one implementation |
| HTML escaping | string concatenation of creator handles and JSON strings | `html.escape` on every value | creator names and JSON strings are data |
| SVG isolation | id-prefixing regex over SVG text | `<img>` data URI | removes the whole class of collision |
| Static plots | hand-painted HTML bars as in TP3 `plots_presentation.py` | matplotlib slide variant | D-08 |
| Pre-registration checks | re-implementing guards in the builder | call the existing identity commands (`som_stage.require_same_rule`, `hopfield_select.py identity`, `hopfield_qr_select.py identity`, `campaigns_select.rule_identity`) | already tested; the builder only needs to report their status in the stamp |

**Key insight:** the expensive part of this phase is not generating HTML; it is keeping text, numbers, figures and reproduction commands from drifting apart. Every drift risk should be turned into a failing test.

## Runtime State Inventory

Not applicable. Phase 6 is not a rename, refactor or migration; no stored data, services, OS registrations or env vars embed a string being renamed. Omitted per the template rule.

## Literal Questions of the Enunciado and Where They Are Answered

Source: `docs/Archivo SIATP 42026.pdf` (pdfTeX, 6 pages). `pdftoppm`/`pdftotext` are not installed, so the Read tool could not render it; the text was extracted by decompressing the page streams with Python `zlib` and decoding the TeX `TJ` operators. TeX accent glyphs come out as octal escapes, so **accents below are reconstructed** [ASSUMED] A6: the planner must have a human compare each quote against the PDF before the table is published, because the success criterion says "literal". Optional: `brew install poppler` then `pdftotext -layout`.

The enunciado states which items are mandatory ("se debe", "como mínimo") and marks the rest as "Preguntas disparadoras de ejemplo" and "Se recomienda". It adds: "El foco del ejercicio está en los métodos de aprendizaje no supervisado y en la interpretación de los resultados obtenidos. No se espera que se realice un análisis de marketing exhaustivo y se pueden asumir ciertos supuestos sobre las features si es necesario."

| ID | Literal question or instruction (enunciado section) | Answered in (fragment, section) |
|----|----------------------------------------------------|---------------------------------|
| Q1.1 | "Analizar el conjunto de datos y seleccionar qué variables serán utilizadas para resolver el problema. Para ello, se debe realizar un Exploratory Data Analysis (EDA) y un Análisis de Componentes Principales (PCA)." (1.1) | 01 sections 2, 3, 4 and 6 |
| Q1.2 | "Justificar si se realiza una reducción de dimensionalidad y cómo se interpretan las componentes." (1.1) | 01 sections 5, 6, 6.1 and 7 |
| Q1.3 | "Variar los hiperparámetros correspondientes a la red y justificar la elección final evaluando la performance del modelo." (1.2) | 02 sections 2, 3 and 4 |
| Q1.4 | "Analizar la grilla de neuronas y la distribución de los creadores de contenido en la misma y analizar la Matriz U." (1.2) | 02 section 5 |
| Q1.5 | "¿Qué perfiles de creadores reúne cada región de la grilla seleccionada?" (1.2) | 02 sections 6.1, 6.2, 6.3 |
| Q1.6 | "¿Coinciden con los perfiles observados en la PC1 y PC2 (biplot)?" (1.2) | 02 section 6.4 |
| Q1.7 | "¿Qué indica una distancia alta entre neuronas vecinas en la matriz U?" (1.2) | 02 section 6.5 |
| Q1.8 | "¿qué representa este índice?" (1.3, Oja) | 03 sections 1 and 3 |
| Q1.9 | "¿Cómo se puede interpretar?" (1.3) | 03 section 3 |
| Q1.10 | "¿Sería correcto elegir automáticamente al creador con el valor más alto para cualquier campaña?" (1.3) | 03 section 3 |
| Q1.11 | "Comparar el resultado con la proyección sobre PC1 obtenida mediante PCA." (1.3) | 03 section 2 |
| Q1.12 | "Para una campaña de fútbol, ¿conviene priorizar alcance masivo, descubrimiento o profundidad educativa? Fundamentar la elección según los resultados obtenidos previamente." (1.4) | 03 section 5.1 |
| Q1.13 | "Comparar la selección obtenida con una estrategia basada únicamente en followers. ¿Qué ventajas y/o desventajas tiene cada estrategia?" (1.4) | 03 section 5.5 |
| Q1.14 | "¿Qué implica el mantenimiento del sistema desarrollado? ¿Qué ocurre cuando llega a la agencia una nueva campaña?" (1.4) | 03 section 6 ("Campaña nueva") |
| Q1.15 | "¿Qué cambios serían necesarios en caso de tener que actualizar la cantidad de creadores de contenido o se desean incorporar nuevas variables?" (1.4) | 03 section 6 ("Creadores nuevos", "Variables nuevas") |
| Q1.16 | "¿Qué implicancias tiene la actualización de los datos de los creadores de contenido a fin de mes?" (1.4) | 03 section 6 ("Actualización mensual", demo SYN001) |
| Q1.17 | "A lo largo de todo el trabajo se deben interpretar los resultados obtenidos y en base a la evidencia tomar decisiones para las campañas de marketing de los clientes de la agencia." (1.4; clients named in the intro: refugios de perros, ropa de fútbol, belleza, materiales de arte) | 03 sections 5.2, 5.3, 5.4 and 5.6 |
| Q2.1 | "Representar cada uno mediante una matriz binaria de 37×37" (2.1, QR) | 05 section 2 |
| Q2.2 | "Almacenar los cinco vectores en la red y construir patrones de consulta." (2.1) | 05 sections 3 and 4 |
| Q2.3 | "Analizar la alteración de los códigos QR mediante la adición de ruido aleatorio con distintos niveles de ruido, simulando el deterioro de los mismos." (2.1) | 05 sections 4 and 5 |
| Q2.4 | "Analizar la cantidad de iteraciones y la energía en cada paso de la red." (2.1) | 05 section 4 ("Energía por paso") |
| Q2.5 | "Explicar las limitaciones del caso de uso." (2.1) | 05 section 6 |
| Q2.6 | "Almacenar 4 patrones de letras. Implementar el modelo de Hopfield para asociar matrices de 5×5 con los patrones de las letras almacenadas." (2.2, recomendación) | 04 sections 1, 2 and 5 |
| Q2.7 | "Realizar un análisis de ortogonalidad y de la capacidad de almacenamiento de la red." (2.2) | 04 sections 4 and 6 |
| Q2.8 | "Ingresar un patrón muy ruidoso e identificar un estado espurio." (2.2) | 04 section 7 |

Answering sections were checked against the fragment headings printed by `grep -nE '^#{1,4} '` this session (for example `### 6.4 ¿Coinciden las regiones con PC1 y PC2 (biplot)?` and `### 5.5 Comparación con la estrategia solo por followers`). The "Answered in" column is a research proposal; the planner/executor must confirm each by reading the section.

## Slides

### What is known and what is not
- **Known** [CITED: 06-CONTEXT.md D-06, TP3 CLAUDE.md]: TP3 used the Slides Artifact type, one section per exercise; HTML snippets were "pegados en los archivos de cada slide"; fonts do not load inside SVG; the Slides type has its own design system. The source of truth was the Artifact itself, read back with the Artifact tool and republished with the same `url`.
- **Known (convention)**: TP1, TP2, TP3 each keep a PDF export `docs/Slides_TPn_G9.pdf` in the repo [VERIFIED: `git log --all --name-only` lists `TP1/docs/Slides_TP1_G9.pdf`, `TP2/docs/Slides_TP2_G9.pdf`, `TP3/docs/Slides_TP3_G9.pdf`]. Ask whether `docs/Slides_TP4_G9.pdf` is expected (Open Question 3).
- **NOT verified (blocker)**: how the Slides type receives content (one file per slide? a manifest? how a slide references an image), whether `<img src="data:image/svg+xml...">` renders, the canvas size (TP3 used 24 to 28 px type and 420/760 px bar widths, suggesting a 1280x720 or 1920x1080 canvas [ASSUMED] A2), whether speaker notes exist, and the export path to .pptx/PDF. The researcher has no Artifact tool and the bundled `artifact-design` and `artifact-capabilities` skills describe HTML pages and runtime capabilities, not the Slides type.

### Wave 0 probe (top-level session, before any slide code)
Run `Artifact` `quickstart` with intent "slides" and record answers in `.planning/phases/06-slides-e-informe/06-ARTIFACT-FORMAT.md`. Checklist:
1. Exact content contract (files per slide, naming, ordering, title field).
2. Canvas size and type scale; default design system tokens (so figure cards match).
3. Does a slide accept `<img>` with a `data:image/svg+xml;base64` source and with a relative file in a multi-file publish? Publish a 2-slide smoke deck with one real figure.
4. Speaker notes: supported field, or none.
5. Whether the executor can build the files locally and the top-level session publish them (multi-file `files` publish) without re-authoring.
6. Redeploy: same file path reuses the same URL [CITED: orchestrator message]. Record the URL in `README.md`.
7. Export to PDF/.pptx works and keeps images.
8. Default visibility is private [CITED: orchestrator message]; decide with the user how the teacher sees it.

### Notes fallback (D-06)
If the type has no notes field: (a) keep the notes in `analysis/results/slides/notes.md` generated from the same outline, (b) append them to the report as an annex "Guion de la presentación" (same source, no divergence), (c) tell the user. Do not put notes in visible slide bodies.

### Indicative outline (fits D-01, D-02, D-05, D-07; numbers come from `facts`, never from this table)
Order follows D-02: PCA, SOM, Oja, campaigns, letters, QR. Exercise 1 = 14 slides, Exercise 2 = 9, plus cover and method = 25. Titles below are placeholders for conclusion-style titles.

| # | Slide (conclusion-style) | Figure source | Unfavorable result "de frente" (D-04) |
|---|---------------------------|---------------|-----------------------------------------|
| 1 | Portada TP4 SIA Grupo 9 | - | |
| 2 | Método: reglas fijadas antes de ver resultados, sha256, 10 seeds, nulos por permutación | - | |
| 3 | Datos: las 5 dependencias exactas dejan 26 variables | `eda` audit table | |
| 4 | PCA: no alcanza con 2 componentes | `pca/audited/eigenvalues_variance` | |
| 5 | PC1 es escala y precio | `pca/audited/biplot` | |
| 6 | La grilla se eligió por regla fijada, no por menor QE | `som/figures/stage1_curves` | |
| 7 | Etapa 2: la elección no es robusta | table from `robustness.json` | yes |
| 8 | Mapa y matriz U de 5x5 | `som/figures/map` | |
| 9 | Una sola región con la regla fijada | `som/profiles/regions` | yes |
| 10 | El mapa sigue a PC1 pero no a PC2 | `som/profiles/pc_planes` | |
| 11 | Oja converge a PC1 | `oja/oja_vs_pc1` | |
| 12 | El máximo del índice no sirve para cualquier campaña | table (correlation with followers) | |
| 13 | Fútbol: profundidad educativa primero | `campaigns/shortlists_som` or `shortlists_biplot` | |
| 14 | Perros, maquillaje y arte: una tabla (criterio, top-5, costo por mil argentinos) | table | |
| 15 | Contra solo followers (overlap@k, costo por alcance argentino) | table/figure | |
| 16 | Mantenimiento: creador nuevo, variables nuevas, mes a mes | `maintenance/report_demo` facts | |
| 17 | Conclusiones Ej. 1 | - | |
| 18 | Letras: el set separado y el correlacionado | `hopfield/figures/letters`, `overlaps` | |
| 19 | Ruido y capacidad | `recall_noise`, `capacity_p4` | |
| 20 | Un estado espurio | `spurious` | |
| 21 | QR: cinco códigos muy parecidos entre sí | `hopfield/qr/figures/qr`, `overlaps` | |
| 22 | Hebb falla incluso sin ruido | `majority`, `recovery` | yes |
| 23 | Pseudo-inversa recupera, y un lookup de Hamming la iguala o supera con ruido alto | `recovery` | yes |
| 24 | La energía nunca sube; un corrimiento de 1 a 2 px rompe la recuperación | `energy_trace`, `shift` | |
| 25 | Conclusiones Ej. 2: limitaciones de Hopfield para QR | - | |

The planner may merge or drop slides; D-01 asks for roughly 20 to 25.

## Common Pitfalls

### Pitfall 1: Touching frozen files trips the pre-registration guards
**What goes wrong:** `make som-stage1` aborts with "the pre-registered rule and its series must be committed and unchanged"; Hopfield figure scripts refuse to draw.
**Why it happens:** `som_select.rule_guard` requires each guarded path (rule file `deliverables/02-kohonen.md`, `analysis/som_select.py`, series files) to be tracked and clean in `git status --porcelain`; `campaigns_select.rule_identity` requires `analysis/campaigns_select.py` clean and the text between markers equal to the rule commit; Hopfield drivers hash `CODE_FILES` / `LIMITS_CODE_FILES` (listed in Pattern 3).
**How to avoid:** never edit the five fragments, `som_select.py`, `campaigns_select.py`, `hopfield*.py` (except figure scripts), `hopfield_qr*.py` (except `hopfield_qr_figures.py`), `scripts/qr.py` in this phase. Do all text changes at render time. Commit any intentional edit before running `make`.
**Warning signs:** `SystemExit` messages ending in `(D-07)`, `(D-10)`, `(D-04)`, or "changed since the run" from a figure script.

### Pitfall 2: `uv` is not installed here, so touching `requirements.txt` breaks `make venv`
**What goes wrong:** adding `Markdown==3.11` makes `.venv/.installed` older than `analysis/requirements.txt`; `make venv` then calls `uv`, which is missing.
**Evidence:** `command -v uv` printed nothing; `make -n venv` currently says "Nothing to be done"; `.venv/.installed` is dated 2026-10-21 14:33.
**How to avoid:** change the Makefile `venv` recipe to fall back to `$(PY) -m pip install` when `uv` is absent (or document the pip command), then `touch .venv/.installed`. The README already needs the no-`uv` path (fragments mention `python3.12 -m venv .venv` + pip).

### Pitfall 3: Phase 3 is not human-verified
**What goes wrong:** campaign numbers get frozen into slides and report, then change.
**Evidence:** `03-VERIFICATION.md` has `status: human_needed`; `03-UAT.md` has `status: testing`; STATE.md says "Phase complete - ready for verification"; ROADMAP still shows Phase 3 unchecked; `03-REVIEW-DISPOSITION.md` is untriaged; CONTEXT.md asks to verify before freezing. Phase 5 and Phase 4 have `VERIFICATION.md` files; Phase 2 has 11 open review findings that must go through `/gsd-discuss-phase`, not in-place edits.
**How to avoid:** first plan includes a human checkpoint to finish `/gsd-verify-work 3` (or record an explicit waiver) before the campaign slides and the campaign part of the report are built.

### Pitfall 4: Wide tables and long pages break phone width
**What goes wrong:** the audit table (31 rows) and several 5-column tables push the page sideways; Artifact contract forbids horizontal body scroll.
**How to avoid:** wrap every converted `<table>` in a div with `overflow-x:auto` (post-process); `img{max-width:100%}`; `min-width:0` on flex/grid children [CITED: Artifact page contract].

### Pitfall 5: Theme tokens
**What goes wrong:** figures unreadable in dark mode, or page background transparent.
**How to avoid:** define every colour token on bare `:root`, redefine in the two dark blocks, give `body` an explicit token background; figures always sit on a card with `#fcfcfb` (D-10; `SURFACE = "#fcfcfb"` [VERIFIED: `analysis/plots_style.py` line `SURFACE = "#fcfcfb"`]) plus border [CITED: Artifact page contract].

### Pitfall 6: Absolute paths, secrets or personal data in published pages
**What goes wrong:** a build stamp or JSON excerpt leaks `/Users/<name>/...` or an email.
**How to avoid:** the stamp carries short git HEAD and a dirty flag only; builder asserts no output contains `/Users/` or `@gmail`; `sweep.py` is documented to write relative paths only [CITED: `analysis/README.md`], but assert anyway.

### Pitfall 7: Fragment numbers and JSON numbers diverge silently
**How to avoid:** the curated drift test (Pattern 1) runs inside `make deliverables` as a build-time assertion, not only in `pytest`, because `pytest` cannot see results that are not versioned.

### Pitfall 8: Docs deleted on delivery day (TP3 history)
Commits `31958a4` ("Delete TP3/CLAUDE.md") and `bcce0da` ("Delete TP3/DECISIONS.md") exist [VERIFIED: `git log --all --oneline`]. Add `test_repro_docs.py` so `make test` fails if `README.md`, `CLAUDE.md` or `DECISIONS.md` is missing, empty, or documents a `make` target that is not in the Makefile.

### Pitfall 9: The enunciado quotes are reconstructed, not copied
See the questions section. A wrong accent or a paraphrase breaks success criterion 2 ("pregunta literal").

## Code Examples

### Figure embed (report)
```python
# Source: this research; Artifact page contract (img data URIs allowed, 16 MB cap)
import base64, html
from pathlib import Path

def figure_card(svg_path: Path, alt: str, caption: str) -> str:
    data = base64.b64encode(svg_path.read_bytes()).decode("ascii")
    return (
        '<figure class="fig">'
        f'<img src="data:image/svg+xml;base64,{data}" alt="{html.escape(alt, quote=True)}" loading="lazy">'
        f'<figcaption>{html.escape(caption)}</figcaption></figure>'
    )
```

### Markdown conversion with number-based anchors
```python
# Source: python-markdown.github.io/extensions/toc/ (slugify, baselevel options)
import re, markdown

def make_slugify(fragment_no: int):
    def slugify(value, separator):
        m = re.match(r"(\d+(?:\.\d+)*)\b", value.strip())
        return f"f{fragment_no}-s{m.group(1).replace('.', '-')}" if m else f"f{fragment_no}-" + re.sub(r"[^a-z0-9]+", separator, value.lower()).strip(separator)
    return slugify

def render_fragment(text: str, fragment_no: int) -> str:
    md = markdown.Markdown(
        extensions=["tables", "fenced_code", "toc"],
        extension_configs={"toc": {"slugify": make_slugify(fragment_no), "baselevel": 2}},
    )
    return md.convert(text)
```

### Facts with decimal comma
```python
# Source: this research; numbers must come from JSON (D-11)
def dec(x: float, digits: int = 3) -> str:
    return f"{x:.{digits}f}".replace(".", ",")

def facts(results: Path) -> dict:
    pc = json.loads((results / "som/profiles/pca_contrast.json").read_text())
    return {"som.r2_pc1": dec(pc["r2_pc1"]), "som.r2_pc2": dec(pc["r2_pc2"])}
# pca_contrast.json keys read this session: r2_pc1 0.9613..., p_r2_pc1 0.000999..., r2_pc2 0.0552...
```

### Slide-variant plumbing
```python
# plots_style.py additions (sketch)
_VARIANT = "report"
def use_variant(name): global _VARIANT; _VARIANT = name
def variant(): return _VARIANT
def caption(fig, text, **kw):
    if _VARIANT == "slide": return          # slides carry no long captions
    ...
def save_figure(fig, path_without_suffix):  # slide -> <dir>/slide/<stem>.svg and applies SLIDE_SIZE[stem]
    ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| TP3: charts hand-painted as HTML divs, pinned `<p>` labels | matplotlib SVG with `svg.fonttype=path` | TP4 STACK.md / D-08 | fonts no longer an issue in the Slides format; figures embed as images |
| TP3: Artifact was the source of truth | generator + `analysis/results` are the source; Artifact is the publication | TP3 note + D-11 | slides regenerate from code |
| plotly interactive report | static report | D-09 | no JS, no CDN |

**Deprecated/outdated:** `STACK.md` and `ARCHITECTURE.md` mention `slides_*.py` "stdlib div/SVG fragments" renderers; D-08 supersedes that (slides use the matplotlib variant).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The Slides Artifact type accepts per-slide HTML that can contain `<img src="data:image/svg+xml;base64,...">` and a speaker-notes field | Slides | Slide builder output format changes; notes go to the fallback |
| A2 | Slide canvas is about 1280x720 or 1920x1080 (inferred from TP3 px sizes) | Slides | Slide figure sizes and font scale need redoing |
| A3 | Python-Markdown converts the five fragments faithfully (checked syntax by script, did not run it) | Standard Stack | Wave 0 smoke render needed; broken tables or lists |
| A4 | The report with about 35 base64 SVGs stays under 16 MB (only the 7 SOM SVGs, about 940 KB, were measured) | Pattern 4 | Must switch some figures to PNG at lower resolution or drop appendix figures |
| A5 | Result-chain wall time is between 10 and 60 minutes (summaries report ~3 min and ~46 min for one step) | Pattern 5 | Planner sizes the "run everything" step wrong |
| A6 | Enunciado accents and wording in the question table are right (reconstructed from TeX glyph escapes) | Questions | Criterion 2 "literal" fails; human must compare with the PDF |
| A7 | `eda`, `hopfield-figures`, `hopfield-qr-figures` sentinel names (`audit_table.md`, `spurious.svg`, `majority.svg`) exist exactly as documented | Pattern 5 | Wrong sentinel never satisfied, so the step reruns each time |
| A8 | An SVG with embedded `<image>` rasters renders when loaded through `<img>` in the viewer | Pattern 4 | Use PNG for the 4 imshow-based figures |
| A9 | Overriding `figsize` plus dropping captions yields acceptable 16:9 slide figures without per-figure layout work | Pattern 3 | Per-figure slide layouts needed; more effort |
| A10 | `TP4/CLAUDE.md` is the right location although `config.json` points to `./.claude/CLAUDE.md` | Constraints | GSD tooling may create or read a different file |
| A11 | Python-Markdown 3.11 has no install-time scripts or unexpected behavior beyond what its PyPI page shows | Package audit | Supply-chain risk; gated by human-verify |

## Open Questions (RESOLVED)

Every question below has a resolution: five by a user decision or a plan task, and Q1 by a plan that answers it from a real probe at execution time (its answer cannot be known before the probe runs, so the planning-level resolution is the gate, not the answer).

1. **What does the Slides Artifact type accept, and does it support speaker notes?**
   - Known: TP3 filled it with HTML snippets per slide; STATE.md lists it as an open blocker.
   - Unclear: input contract, canvas, notes, image embedding, export.
   - Recommendation: Wave 0 probe by the top-level session (checklist above); gate slide-builder work on `06-ARTIFACT-FORMAT.md`.
   - **RESOLVED (planning; answer pending the 06-02 probe):** 06-02 has the top-level session publish and read back a 2-slide smoke deck and record content_unit, canvas, figure_area, image_embed, notes_supported, notes_field, export formats, redeploy behaviour, default visibility and share_mode in `06-ARTIFACT-FORMAT.md`. 06-05 (slide figure size) and 06-10 (slide file layout, notes field) read those keys and depend on 06-02; if notes are not supported, the D-06 fallback is `notes.md` plus the informe annex "Guion de la presentación" (06-09 `--notes`).
2. **Should the report be pure synthesis or hybrid?**
   - Recommendation: hybrid (Pattern 1). Confirm with the user because D-11 is marked costly to reverse.
   - **RESOLVED by D-12:** hybrid report (generated front section with numbers from facts, then the five fragments rendered as "Detalle técnico (Fase N)", with a drift test pinning fragment numbers to the JSON). Implemented by 06-04 (tracer), 06-08 (facts and drift pins) and 06-09 (full informe).
3. **Is a PDF `docs/Slides_TP4_G9.pdf` expected like TP1-TP3?** Ask the user; if yes, add an export step to the publish checkpoint.
   - **RESOLVED by D-14:** slides are delivered only as an Artifact; no slides PDF or .pptx is exported or versioned in `docs/`. 06-11's test_repro_docs fails if one is added; 06-12 publishes without an export step.
4. **Does the teacher need the report as PDF/Word, or must it be viewable by people outside the account?** Artifacts are private by default; sharing must be set at publish time. If PDF/Word is required, reconsider the Docs type.
   - **RESOLVED by D-15:** the informe reaches the teacher as a shared link of the HTML Artifact; no PDF/Word export and no Docs type. How the link is shared is the share_mode the user records in 06-02; 06-12 Task 3 shares both Artifacts by link and keeps them out of any public listing.
5. **Where does `CLAUDE.md` live and should GSD's `claude_md_path` be updated?** Recommend `TP4/CLAUDE.md` and updating the config key.
   - **RESOLVED by 06-11 Task 2:** `CLAUDE.md` is written at the TP4 root and `.planning/config.json` `claude_md_path` is set to `./CLAUDE.md` (research assumption A10).
6. **How should the front matter treat internal jargon (`D-NN`, `Pitfall N`, `HOP-04`) that appears 131+ times in fragments?** Options in Pattern 1; needs a user call.
   - **RESOLVED by D-13:** jargon is linked at render time to a glossary annex generated from `DECISIONS.md`; the fragments stay untouched. 06-03 writes `DECISIONS.md` with the heading grammar the parser reads; 06-09 implements `parse_glossary` and `link_jargon`.

## Who does what (Artifact tool availability)

| Step | Performed by | Why |
|------|--------------|-----|
| Slides type probe (`quickstart`, smoke deck) | Top-level session | needs the `Artifact` tool |
| Finish Phase 3 verification / waiver | User (human checkpoint) | UAT is a human judgement |
| Human verify of `markdown` install, human compare of quotes with the PDF | User | package gate; "literal" requirement |
| Facts, manifest, figure variants, `informe.py`, `slides.py`, tests, Makefile, docs | Executors | local files only |
| Run `make results` (long) | Executor or user in terminal | long-running; needs `.venv` and `gcc` |
| Publish slides and report, read back, record URLs in README/CLAUDE.md | Top-level session | `Artifact` tool; republish by reusing the same `file_path` |
| Visual review of published pages (desktop, phone, light, dark) | User | judgement; only the Artifact preview can render |

## Reproduction Docs (DELIV-03)

- **README.md** (new; TP4 has none at the root, only `analysis/README.md` and `neuron/README.md`): quick start (`make`), a table "resultado -> figura/tabla -> comando -> config -> seed" generated or checked from the manifest (every figure in the manifest names its `make` target; a test fails if a manifest target is not in the README table), expected run times, the no-`uv` fallback, how to build and publish slides and report, published Artifact URLs.
- **CLAUDE.md** (TP3 shape at `git show 7ff59c3:TP3/CLAUDE.md`): where the TP is today, code layout, what the enunciado asks, closed design decisions (link to `DECISIONS.md`), delivery state with Artifact URLs, pending items, how to reproduce, known traps (the four in this document: frozen files, ~46 min step, no `uv`, results not versioned), conventions (identifiers in English, prose in Spanish, decimal comma, algorithms by hand).
- **DECISIONS.md** (TP3 shape: "Decisiones que nos pueden preguntar en la defensa", index per exercise, one entry "Qué / Por qué"): consolidates the 65 `D-xx` entries counted in the five CONTEXT files (13 + 15 + 19 + 7 + 11) and the 6 PROJECT.md Key Decisions, each with a link to its CONTEXT.md or fragment section. Hand-curated, not generated.
- Seeds: each documented command lists the config and seed it uses (series files `analysis/series_*.json`; SOM figure seed and Oja seed 1 are in the result JSON, for example `figure_seed` in `selection.json` and `pca_contrast.json`).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 (`.venv`) | all builders | yes | 3.12.15 | - |
| GNU Make | targets | yes | 3.81 (use 3.81-compatible syntax only) | - |
| gcc / clang | `neuron/build/neuron` | yes | Apple clang 21.0.0; binary already built | - |
| `uv` | `make venv` | **no** | - | `python3.12 -m venv .venv` + `.venv/bin/python -m pip install -r analysis/requirements.txt` + `touch .venv/.installed` |
| `pdftotext` / `pdftoppm` (poppler) | reading the enunciado | no | - | zlib extraction (done); `brew install poppler` optional |
| Node | not needed | yes (v26.12.0) | - | - |
| `Artifact` tool | publishing | not in the researcher's tools; the orchestrating session has it | - | Google Slides connector or `anthropic-skills:pptx` as last resort (outside D decisions) |
| `analysis/results/` for steps other than SOM | builders | no (only `som/` and 3 `series_*` folders) | - | `make results` |

**Missing dependencies with no fallback:** none for building; the Artifact publish step needs the top-level session.
**Missing dependencies with fallback:** `uv` (pip path above); poppler.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 (pinned in `analysis/requirements.txt`) |
| Config file | none; `analysis/tests/conftest.py` adds `analysis/` and `scripts/` to `sys.path` |
| Quick run command | `.venv/bin/python -m pytest analysis/tests/test_facts.py analysis/tests/test_deliverables_manifest.py analysis/tests/test_informe.py analysis/tests/test_slides.py analysis/tests/test_repro_docs.py -q` |
| Full suite command | `.venv/bin/python -m pytest analysis/tests -q` (baseline: 230 passed in 14.4 s) |

Tests must not require the unversioned results: use small synthetic result folders in `tmp_path`; the real-results checks run as build-time assertions inside `make deliverables`.

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DELIV-01 | slide outline has 20 to 25 entries, every slide has a title, non-empty notes, and a figure key present in the manifest; build output has one entry per slide | unit | `pytest analysis/tests/test_slides.py -q` | Wave 0 |
| DELIV-01 | published Slides Artifact opens, has a section per exercise | manual (top-level session + user) | n/a | manual |
| DELIV-02 | every `QUESTIONS` id has non-empty literal text and its anchor exists in generated HTML | unit | `pytest analysis/tests/test_informe.py::test_question_anchors -q` | Wave 0 |
| DELIV-02 | informe has no unresolved `{{` placeholders, no `/Users/`, size under ceiling, every `<img>` data URI decodes to SVG | unit/build-time | `pytest analysis/tests/test_informe.py -q` | Wave 0 |
| DELIV-02 | curated numbers in fragments equal formatted JSON values | build-time + unit with fixtures | `pytest analysis/tests/test_facts.py::test_fragment_numbers -q` | Wave 0 |
| DELIV-03 | README/CLAUDE.md/DECISIONS.md exist and are non-trivial; every `make X` they mention exists in the Makefile; every manifest figure's make target is in the README table | unit | `pytest analysis/tests/test_repro_docs.py -q` | Wave 0 |
| DELIV-03 | `make deliverables` on a populated `analysis/results` regenerates figures and HTML with identical bytes on a second run | integration (manual or `make`) | `make deliverables && sha256sum analysis/results/informe/informe.html` twice | Wave 0 |

### Sampling Rate
- **Per task commit:** the quick run command (seconds).
- **Per wave merge:** full suite.
- **Phase gate:** full suite green plus `make deliverables` on real results plus the two published Artifact URLs opened by the user, before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `analysis/tests/test_facts.py`, `test_deliverables_manifest.py`, `test_informe.py`, `test_slides.py`, `test_repro_docs.py`
- [ ] `analysis/facts.py`, `analysis/deliverables_manifest.py` (so tests have something to import)
- [ ] `Markdown==3.11` in `analysis/requirements.txt` after the human-verify checkpoint; install via the pip fallback
- [ ] `06-ARTIFACT-FORMAT.md` from the Slides probe

## Security Domain

`security_enforcement` is enabled in `.planning/config.json` (`"security_enforcement": true`, ASVS level 1).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Artifacts are private by default; sharing is a publish-time choice (no code) |
| V3 Session Management | no | static pages |
| V4 Access Control | yes (light) | decide visibility at publish; do not make public by default |
| V5 Input Validation | yes | `html.escape` for every JSON/CSV value placed in HTML; Markdown fragments are trusted repo text; no `eval`/`exec` |
| V6 Cryptography | no | sha256 only for existing guards |
| V14 Configuration / dependencies | yes | pinned `Markdown==3.11` behind human-verify; no CDN scripts; no network fetch at build |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Script injection through a creator handle or JSON string | Tampering | `html.escape` on all interpolated data; figures loaded via `<img>` (SVG in `<img>` cannot execute script) |
| Leaking local paths or personal data in the build stamp or JSON excerpts | Information disclosure | stamp = short git HEAD + dirty flag; builder asserts no `/Users/` or email string |
| Supply-chain: newly released dependency | Tampering | pin an older release; human-verify checkpoint; no postinstall on PyPI wheels |
| Published private page shared too widely | Information disclosure | choose visibility explicitly; note the creator dataset is course data |

## Sources

### Primary (HIGH confidence)
- Repo files read this session: `06-CONTEXT.md`, `REQUIREMENTS.md`, `STATE.md`, `Makefile`, `analysis/plots_style.py`, `analysis/README.md`, `analysis/.gitignore`, `analysis/requirements.txt`, `analysis/som_select.py` (`rule_guard`), `analysis/campaigns_select.py` (`rule_identity`), `analysis/hopfield_qr.py` / `hopfield_letters.py` / `hopfield_qr_limits.py` (code sets), `deliverables/*.md` headings and "Cómo reproducir" sections, `analysis/results/som/**` (SVG structure, JSON keys), `03-VERIFICATION.md`, `05-03-SUMMARY.md`, `05-04-SUMMARY.md`.
- `docs/Archivo SIATP 42026.pdf` via zlib stream extraction (accents reconstructed).
- PyPI JSON API for `markdown`; `gsd_run query package-legitimacy check`.
- Artifact page contract and design guidance as loaded through the `artifact-design` and `artifact-capabilities` skills (CSP, 16 MB, `<img>` data URIs, hash anchors, theme tokens, no horizontal scroll).
- `git show 7ff59c3:TP3/CLAUDE.md` and `TP3/DECISIONS.md`; `git log --all` for deleted-docs commits and TP1-3 slide PDFs.

### Secondary (MEDIUM confidence)
- python-markdown.github.io/extensions/ and /extensions/toc/ (WebFetch summaries).
- pypistats.org recent downloads for `markdown`.

### Tertiary (LOW confidence)
- Slides Artifact type behavior: inferred only from CONTEXT.md and TP3 notes; not verified.

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM. Existing stack HIGH; the one new dependency is flagged SUS by the seam and not yet rendered against the fragments.
- Architecture: MEDIUM. Report path and Makefile design are grounded in read code; slide path depends on the unverified Slides contract.
- Pitfalls: HIGH. Guards, `uv`, SVG structure and Phase 3 status were each verified by reading or running.

**Research date:** 2026-10-25
**Valid until:** about 2026-11-08 for Artifact-tool facts (fast-moving); repo facts stay valid until the files change.
