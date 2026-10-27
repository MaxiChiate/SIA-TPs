---
phase: 06-slides-e-informe
plan: 10
subsystem: deliverables-slides
tags: [slides, deck, artifact-slides, facts, presenter-notes, d-01, d-02, d-04, d-05, d-06, d-11]

requires:
  - phase: 06-slides-e-informe
    provides: "06-02 06-ARTIFACT-FORMAT.md (Slides tree, canvas, PNG-only figures, notes in one aside)"
  - phase: 06-slides-e-informe
    provides: "06-05..06-07 slide-variant figures (SVG + PNG under slide/ next to each report figure)"
  - phase: 06-slides-e-informe
    provides: "06-08 facts.py, deliverables_manifest FIGURES/QUESTIONS/slide_path"
provides:
  - "analysis/slides.py: Slide, OUTLINE (24), UNPLACED_SLIDE_FIGURES (5), SLIDE_FORMAT, MAX_TITLE_CHARS, build_deck, write_deck, main (--results, --out, --asset-map)"
  - "analysis/results/slides/: deck.json (build manifest), notes.md (presenter script), project/deck.json (v4 index) + project/slides/<id>.html (24 files), assets/<figure key>.png (15 PNGs to upload)"
  - "facts.py: som.fail_<n>.variant/.te, camp.<c>.followers_global_cost_per_thousand_ar, letters.*_recall_k3/k6/k9, letters.*_n_stable, oja.max_opposite_topic"
affects: [06-11, 06-12]

actuals:
  tokens: 20200
  tasks: 2
  commits: 6
plan_head_before: 05cdf26f236920e0b9fc6fc547d6321cdb56aff0
plan_head_after: 54dd8215e25187949937470131a549f892526211

tech-stack:
  added: []
  patterns:
    - "The deck is a tuple of frozen Slide templates (title, body, table, notes) with {group.key} placeholders; build_deck fills them with facts.fill and the guards (title length, table and body size, outline size, slide figure files) stop the build with a message that names the slide and the make step"
    - "Figures are resolved by results-relative path through deliverables_manifest.FIGURES at import, never by a guessed key"
    - "write_deck builds every file text in memory, checks it (ids, 4000-char notes, asset map, home path, email) and only then replaces project/slides and assets, so a refused build leaves the previous output alone"

key-files:
  created:
    - analysis/slides.py
    - analysis/tests/test_slides.py
  modified:
    - analysis/facts.py
    - analysis/tests/test_facts.py

key-decisions:
  - "Two files are called deck.json: <out>/deck.json is this build's manifest (filled text, results-relative paths, the PNG asset list) and <out>/project/deck.json is the Slides v4 index. Only the project/ tree and the PNGs are published"
  - "Titles are 56 px (not the 72 px of the probe's scale) so a conclusion fits in two lines; MAX_TITLE_CHARS = 88 is derived from 0.6 x font size, and the figure box is sized from the real line counts (542 to 610 px high)"
  - "Slide srcs are the relative copy (../../assets/<key>.png) until --asset-map supplies {png name: /_blob/<id>}; the 06-12 publish step rebuilds with the map so the final HTML carries the blob urls verbatim"
  - "Slide files define no colour, font or palette; the figure PNG brings its own SURFACE panel (D-10)"

patterns-established:
  - "A table row that needs a list of five handles wraps inside its cell at spaces; the notes repeat the numbers, so no row needs short handles"

requirements-completed: []  # DELIV-01 stays pending: the deck is only files until 06-12 publishes it (the shared-ID gate also reports it blocked by 06-11 and 06-12)

duration: about 25 min (start time not recorded; first commit 23:39 local)
completed: 2026-10-26
status: complete
---

# Phase 6 Plan 10: Slide deck builder Summary

**A 24-slide deck (cover, method, 14 slides of exercise 1, 8 of exercise 2) regenerates from results in the probed Slides layout: every title is a conclusion, every number is a facts placeholder, the four unfavorable results have their own slide, and the same run writes the presenter script and the 15 PNGs to upload.**

## Performance

- **Tasks:** 2 of 2 (Task 1 as RED, GREEN; Task 2 as one commit)
- **Files modified:** 4 (analysis/slides.py, analysis/tests/test_slides.py, analysis/facts.py, analysis/tests/test_facts.py)
- **Tests:** `make test` 451 passed (398 before this plan: +48 in test_slides.py, +5 in test_facts.py) and 1282 C checks, 0 failed

## Accomplishments

- `OUTLINE` of 24 slides in method order (D-01, D-02, D-07). Exercise counts 2 / 14 / 8; no agenda, no general closing. Conclusion titles of at most 87 characters (limit 88), the longest being the matrix U slide.
- The four D-04 slides (`som-not-robust`, `som-one-region`, `qr-hebb-falla`, `qr-lookup`) say the unfavorable result in the title and carry one line of why; the four D-05 campaign slides (`camp-futbol`, `camp-table`, `camp-followers`, `camp-maintenance`) are in place.
- 15 distinct slide-variant figures placed (one figure at most per slide) plus the 5 `UNPLACED_SLIDE_FIGURES` with a reason each equal, disjointly, the 20 `slide=True` figures (tested). The 25 enunciado questions are covered by the union of the slides' question ids (tested).
- 11 slides carry the tag "Regla fijada de antemano"; the method slide states the pre-registration once (D-03). Every slide has 2 to 4 sentences of notes with the numbers as placeholders (D-06); the largest note is 829 characters, far below the 4000 cap.
- `write_deck` writes the layout of 06-ARTIFACT-FORMAT.md section 1, `notes.md` for the informe annex, and the PNG assets; two runs are byte-identical (`diff -r` clean); no slide file has a hex colour, `rgb(`, class, `<style>`, margin, `font-family` or font under 24 px.

## Where the files are and how 06-12 publishes them

All under `analysis/results/slides/` (not versioned), built by `.venv/bin/python analysis/slides.py`:

| Path | What it is |
|------|-----------|
| `project/deck.json` | Slides v4 index: `order` of the 24 ids, `cover` portada, 3 `sections` (inicio, ejercicio-1, ejercicio-2), `faces` {} and `designSystems` [] (publish this with `file_path`; send it again only if order, title or sections change) |
| `project/slides/<id>.html` | 24 files, one `<section id>` each, the notes in the last child `<aside>` |
| `assets/<figure key>.png` | the 15 slide PNGs to upload (for example `som_map.png`, `qr_recovery.png`), copied from `.../slide/<name>.png` |
| `notes.md` | "Guion de la presentación", `## <n>. <title>` plus the notes; `informe.py --notes analysis/results/slides/notes.md` appends it (06-11 wires it into the Makefile) |
| `deck.json` | the build manifest; its `assets` list gives `png` name, `file` and `slide` for each upload |

Mapping of PNGs to `/_blob/<id>` srcs, for 06-12:

1. Upload the 15 files of `assets/` with Artifact `publish`, `asset: true` and `file_paths` (up to 25 per call). Each upload returns a `/_blob/<id>` url.
2. Write `asset_map.json` as `{"<png name>": "/_blob/<id>", ...}` with the 15 names exactly as in `assets/` (the key is the figure key plus `.png`, e.g. `"som_map.png"`).
3. Rebuild: `.venv/bin/python analysis/slides.py --asset-map asset_map.json`. The build stops if a png has no entry or a value is not a `/_blob/<id>` url, and writes each url verbatim into the `img src` (without the flag the srcs are `../../assets/<name>.png`, for a local preview only).
4. Publish once to the one deck url with `root` = `analysis/results/slides`, `file_path` = `<root>/project/deck.json` and `files` = `project/slides/*.html`. Do not publish `deck.json` (root), `notes.md` or `assets/`. A changed PNG needs a new upload, a new blob id and a republish of its slide.

## Task Commits

1. **Facts for the slides (RED)** - `4463f5c` (test)
2. **Facts for the slides (GREEN)** - `de8acd4` (feat), refined by `45763f6` (fix, half-up rounding)
3. **Task 1 RED: outline, builder and writer tests** - `472cbe2` (test, with a skeleton of slides.py so the tests fail on assertions)
4. **Task 1 GREEN: deck builder** - `93db1a1` (feat)
5. **Task 2: fit checks and reproducibility** - `54dd821` (feat)

**Plan metadata:** recorded in the docs commit that follows this file.

## TDD Gate Compliance

RED commits `4463f5c` and `472cbe2` precede their GREEN commits `de8acd4` and `93db1a1`. Evidence format: pytest console output, which `check tdd-red-evidence` does not parse, so there is no classifier verdict; the semantic assessment follows.

- `4463f5c`: `test_slide_facts_failing_variants_are_labelled_by_what_moved` and `test_slide_facts_cover_followers_cost_letters_recall_and_opposite_topic` failed with `KeyError` on the planned keys (`som.fail_1.variant`, `camp.futbol.followers_global_cost_per_thousand_ar`); the 54 earlier tests passed. The target tests ran and failed for the intended reason (the facts did not exist).
- `472cbe2`: with a skeleton `slides.py` (names present, empty values), 32 of 40 tests failed on assertions about the planned behavior (24 slides, 15 + 5 figures, filled templates, written tree, byte identity) or on the missing `facts` attribute and `FORMAT` keys of the skeleton; 8 passed trivially on empty data. The 32 are the behavior tests, so GREEN was not authorized by a syntax or collection error.
- Task 2 added its tests (4 failing on the missing `MAX_TITLE_CHARS`, table and body guards) and the implementation in one commit, as the plan marks Task 2 `type="auto"` without `tdd`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Facts the slide tables need did not exist**
- **Found during:** Task 1 (outline)
- **Issue:** the plan requires "every number is a facts placeholder", but facts.py had no key for the stage-2 variants that failed (slide `som-not-robust`), the cost of the followers-only list (`camp-followers`), the letters recall rates and the number of stable correlated letters (`letras-ruido`), or the topic of the opposite-sign maximum (`oja-max`). Hand-typed numbers would have defeated D-11.
- **Fix:** added those facts (and the two sources `robustness.csv` and `recall.csv`) to `analysis/facts.py` with tests and fixture rows in `test_facts.py`; `facts.py check` still prints `DRIFT_OK 68 pins`.
- **Files modified:** analysis/facts.py, analysis/tests/test_facts.py (not in the plan's files_modified)
- **Committed in:** 4463f5c, de8acd4

**2. [Rule 1 - Bug] Half-way percentage rounded the other way from the fragment**
- **Found during:** Task 1 (reading the real facts)
- **Issue:** the recall at 9 flipped pixels is exactly 0,3225; `pct` printed 32,2 % while fragment 04 writes 0,323 (32,3 %).
- **Fix:** `letters.*_recall_*` round half-up on the decimal text (`Decimal`, `ROUND_HALF_UP`), so slide and fragment agree.
- **Files modified:** analysis/facts.py
- **Verification:** `letters.separated_recall_k9` is `32,3 %`; test_facts passes
- **Committed in:** 45763f6

**3. [Rule 3 - Blocking] The plan names `deck.json` twice**
- **Found during:** Task 1 (write_deck)
- **Issue:** the plan's verify reads `analysis/results/slides/deck.json` with a `slides` list of dicts, while 06-ARTIFACT-FORMAT.md fixes `project/deck.json` as the v4 index (`order`, `sections`, ...).
- **Fix:** write both: the root `deck.json` is the build manifest the verify reads, `project/deck.json` is the published index. No conflict between them; only the project tree is published.
- **Committed in:** 93db1a1

**4. [Rule 3 - Blocking] Title size**
- **Found during:** Task 1 (layout)
- **Issue:** at the probe's 72 px a title holds about 38 characters per line, too short for a conclusion title, and two lines would leave the figure under the 630 px of the probe's area.
- **Fix:** titles at 56 px (still above the 24 px minimum), `MAX_TITLE_CHARS = 88`, figure height computed from the real title and body line counts (542 to 610 px). The longest real title has 87 characters.
- **Committed in:** 93db1a1, 54dd821

---

**Total deviations:** 4 auto-fixed (1 missing critical, 1 bug, 2 blocking)
**Impact on plan:** no scope creep; the facts additions are the minimum the plan's own rule needs.

### Portability notes (not deviations)

`grep -c 'Regla fijada de antemano' analysis/slides.py` is 11 as the acceptance criterion needs (the literal is written in each tagged slide, not behind a constant).

## Issues Encountered

- A stray empty `TP4/.git` directory was created by a `mkdir -p .git` typed in a commit command; it was removed with `rmdir` before any further git command, and `git status` shows only `.planning/milestone.lock` untracked.
- `PLAN_START_TIME` was not captured at the start, so the duration is estimated from the commit times.

## Assumptions to confirm at publish time (06-12)

- `cover: "portada"` and each section's `start` hold a slide id: the probe did not record what the type expects in those two fields, so they follow the v4 shape written in 06-ARTIFACT-FORMAT.md section 1.
- With no design system attached, the slide files carry no colour, so the default text colour and background of the type apply; the figure PNGs bring their own light panel.
- Layout uses `display:flex` and `object-fit:contain` inline, which TP3's published deck also used; the probe's closed CSS subset lists no property by name.

## Known Stubs

None. Every title, body, table cell and note is filled from real facts; no placeholder text reaches the output.

## Human-check harvested at end of phase

Read the 24 titles in `analysis/results/slides/deck.json` (or the list below) and confirm each states a conclusion, the four unfavorable results are plain, and no title or note claims ROI, calls the Oja index "mejor" (the word is absent from every text, tested) or says a recovered QR scans (the last slide says the opposite: "No verificamos que un QR recuperado se decodifique").

1 TP4 SIA — Grupo 9 / 2 Fijamos cada regla antes de ver los resultados y los informamos como salieron / 3 6 componentes retienen 83,1 % de la varianza, pero no reducimos la dimensión / 4 PC1 (53,2 %) es un eje de tamaño y precio; PC2 (8,5 %) sigue la audiencia argentina / 5 La grilla sale de la regla fijada, k = 5, y no del menor QE (k = 8) / 6 La etapa 2 no es robusta: 5 variantes del schedule rompen el filtro de TE / 7 Las paredes altas de la matriz U separan perfiles distintos, sobre todo tamaño y precio / 8 Con la regla fijada el mapa da una sola región: no se parte en grupos de creadores / 9 El mapa coincide con PC1 (R² 0,961, p = 0,001) pero no con PC2 (R² 0,055) / 10 Oja aprendió PC1: su índice y el score de PC1 ordenan igual a los creadores / 11 Elegir el máximo del índice no es correcto: cambia con el signo y no mira el tema / 12 Para fútbol recomendamos profundidad: es el que más se aleja de elegir por followers / 13 Perros, maquillaje y arte se ordenan con su propio criterio, no con followers / 14 Solo por followers suele salir más barato por mil, pero ignora tema y objetivo / 15 Una campaña nueva no re-entrena nada; variables nuevas obligan a rehacer el modelo / 16 Cada método describe y la regla de la campaña decide quién entra / 17 El set GRTV casi no se solapa (máximo 0,04); el set HMNW llega a 0,84 / 18 El set separado resiste el ruido; el correlacionado nunca pasa de 25,0 % / 19 Con mucho ruido la red cae en estados espurios: 61,4 % de los ensayos / 20 Los QR son idénticos en 69,8 % de sus píxeles: están muy correlacionados / 21 Hebb recupera 0 % de los QR, ni siquiera sin ruido / 22 Un lookup de Hamming iguala o supera a la pseudo-inversa con ruido alto / 23 La energía baja en cada paso y la red converge, pero al estado común y no al QR / 24 Hopfield para QR: la correlación rompe Hebb y un lookup resuelve el mismo problema

The recommendation on slide 12 (profundidad educativa for football) is a judgment of fragment 03, not a rule result, and its notes say so.

## Threat Flags

None: no new network endpoint, auth path or file access beyond reading `analysis/results` and writing the output folder. T-06-24 (html.escape of every written text, tested with a `<b>` and a `<script>` value), T-06-25 (no home path, no email-shaped string, results-relative paths in deck.json, tested) and T-06-26 (unknown fact key or missing slide figure stops the build, tested) are mitigated; T-06-SC installs nothing.

## Next Phase Readiness

- 06-11 can add `make slides` (`analysis/slides.py`) and wire `informe.py --notes analysis/results/slides/notes.md`.
- 06-12 (top-level session) has the upload list, the asset map format and the publish order above.

---
*Phase: 06-slides-e-informe*
*Completed: 2026-10-26*

## Self-Check: PASSED

- Created files exist: analysis/slides.py, analysis/tests/test_slides.py, and the outputs deck.json, notes.md, project/deck.json, 24 slide files, 15 PNG assets.
- Commits exist on HEAD: 4463f5c, de8acd4, 45763f6, 472cbe2, 93db1a1, 54dd821.
- Plan verifications re-run: PYTEST_OK, DECK_OK, FIGURES_PLACED_OK, SLIDES_REPRODUCIBLE and SUITE_OK pass (`make test` 451 passed, 1282 checks, 0 failed); `facts.py check` DRIFT_OK 68 pins.
- Acceptance: `grep -c 'Regla fijada de antemano' analysis/slides.py` is 11.
