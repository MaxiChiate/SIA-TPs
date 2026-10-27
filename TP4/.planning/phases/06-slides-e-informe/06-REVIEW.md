---
phase: 06-slides-e-informe
reviewed: 2026-10-26T00:00:00Z
depth: standard
files_reviewed: 26
files_reviewed_list:
  - CLAUDE.md
  - DECISIONS.md
  - Makefile
  - README.md
  - analysis/campaigns.py
  - analysis/deliverables_manifest.py
  - analysis/facts.py
  - analysis/hopfield_figures.py
  - analysis/hopfield_qr_figures.py
  - analysis/informe.py
  - analysis/oja.py
  - analysis/pca.py
  - analysis/plots_style.py
  - analysis/requirements.txt
  - analysis/slides.py
  - analysis/som_figures.py
  - analysis/som_profiles.py
  - analysis/tests/test_deliverables_manifest.py
  - analysis/tests/test_facts.py
  - analysis/tests/test_hopfield_figures.py
  - analysis/tests/test_hopfield_qr_figures.py
  - analysis/tests/test_informe.py
  - analysis/tests/test_plots_style.py
  - analysis/tests/test_repro_docs.py
  - analysis/tests/test_slides.py
  - analysis/tests/test_variants_ej1.py
findings:
  critical: 0
  warning: 8
  info: 6
  total: 14
status: issues_found
---

# Phase 6: Code Review Report

**Reviewed:** 2026-10-26
**Depth:** standard
**Files Reviewed:** 26
**Status:** issues_found

## Summary

I reviewed the Phase 6 changes since `918fdd3`. That covers the deck and informe builders, the facts layer, the manifest, the slide variants of the figure drivers, the Makefile targets, the docs and their tests.

I ran the nine Phase 6 test files (`test_deliverables_manifest`, `test_facts`, `test_hopfield_figures`, `test_hopfield_qr_figures`, `test_informe`, `test_plots_style`, `test_repro_docs`, `test_slides`, `test_variants_ej1`). All 260 tests pass. I did not run the full `make test`.

I also cross-checked the slide and informe claims against the real `analysis/results/` (`facts.py dump`, `recovery_table.csv`, `recall.csv`, `comparison.csv`, `robustness.csv`, `selection.json`). Every number I traced matches the results. I found no security problem: output text is html-escaped, and home-path and email scans run before writing. I found no blocker.

The weaknesses are of four kinds:
- **Hidden coupling in facts:** facts are pinned to hard-coded levels, and some lookups fail with a bare exception instead of the promised message.
- **Static prose beyond numbers:** the D-11 guard covers only numbers, so qualitative conclusions and a few typed numbers can go stale without the build noticing.
- **One misleading slide:** the SOM rule slide describes the selection rule incompletely.
- **Doc contradictions:** several docs contradict each other on delivery state, and the new slide-variant code has no tests in several drivers.

## Warnings

### WR-01: facts.py fails with a bare StopIteration/ValueError instead of the promised "run make ..." message

**File:** `analysis/facts.py:225`, `:265`, `:274`, `:359`, `:371-373`
**Issue:** The module docstring says that a missing result "stops the build with the make command to run". These lookups use `next(...)` with no default, or `max()`/`min()` on a possibly empty list, so a changed or partial result raises a bare `StopIteration` or `ValueError`.
- `followers = next(row for row in correlations if ...)` (225)
- `row = next(...)` and `baseline = next(...)` in `_campaign_facts` (265, 274)
- `first_shift = next(...)` (359)
- `max(pinv_full)` raises `ValueError` if no noise level has pinv exactly 1.0 (371)
- `max(pinv_alive)` raises `ValueError` if pinv is never above 0 (372)
- `min(majority["hamming_to_targets"])` raises `ValueError` on an empty list (373)

`informe.py` and `slides.py` only catch `SystemExit`, so the user gets a traceback with no hint.
**Fix:** Pass a default to `next` and raise a clear error, as `_row_at` already does:
```python
followers = next((r for r in correlations if r["target"] == "followers" and r["sign"] == "+1"), None)
if followers is None:
    raise SystemExit("no followers/+1 row in oja/evidence_correlations.csv; run `make results` (step oja)")
```
Guard each `max`/`min` the same way.

### WR-02: `qr.noise_high` is derived from the data but slides and informe pair it with hard-coded 0,45 / 0,50 facts

**File:** `analysis/facts.py:372`, `:381-385`; `analysis/slides.py:404-409`; `analysis/informe.py:378-381`
**Issue:** `qr.noise_high = max(level where pinv > 0)` is 0,45 today only because pinv at 0,50 is exactly 0. The texts that use it are tied to fixed levels:
- The slide `qr-lookup` says "Con ruido alto (nivel {qr.noise_high}): Hamming {qr.hamming_at_0_45}, pseudo-inversa {qr.pinv_at_0_45}".
- Its notes call level 0,50 "el último nivel".
- The informe finding says "en el nivel {qr.noise_high} cae a {qr.pinv_at_0_45}".

If a rerun makes pinv at 0,50 slightly positive, `noise_high` becomes 0,50. The text would then show the 0,45 figures labelled as level 0,50, with no error. `DRIFT_PINS` does not cover the slide or the front section.
**Fix:** Make the fact explicit and fixed, for example `qr.noise_high = dec(0.45, 2)` documented as a chosen reporting level. Or add `qr.hamming_at_high` and `qr.pinv_at_high` derived from the same level and use only those in the templates.

### WR-03: The "som-rule" slide describes the grid-selection rule incompletely

**File:** `analysis/slides.py:154-162`
**Issue:** The notes say "La regla filtra por error topográfico, neuronas vacías y creadores por neurona ocupada, y no por QE". The title says k = 5 "sale de la regla fijada ... y no del menor QE". The real rule is `selection.json` with `decided_by: qe_loo`. Among the k that pass the three filters, the one with the lowest leave-one-out QE wins (`deliverables/02-kohonen.md` lines 36 and 39). Only the training QE is excluded.

"No por QE" is misleading for a defense. The jury can reasonably ask "so what decides between k = 4 and k = 5?", and the slide has no answer. The informe findings are accurate here; the slide is not.
**Fix:** Edit the notes, and the body line if needed. For example: "... filtra por TE, neuronas vacías y creadores por neurona ocupada; entre las que pasan gana el menor QE-LOO (leave-one-out). El QE de entrenamiento no decide: baja siempre al agrandar la grilla."

### WR-04: Qualitative conclusions are hard-coded; D-11 and the drift pins guard only numbers

**File:** `analysis/slides.py:402` (title of `qr-lookup`), `:176-184` (notes of `som-map`), `:363-376` (notes of `espurio`); `analysis/informe.py:322-323`, `:380-381`
**Issue:** Claims whose truth depends on the results are plain text, so the build passes if the results change.
- "Un lookup de Hamming iguala o supera a la pseudo-inversa con ruido alto" (slide title).
- "iguala o supera a la red en todo el rango evaluado" (informe finding).
- "la ocupación de las neuronas no se degrada" (informe finding).
- "En las tres hay una neurona con un solo creador" (som-map notes).
- "creadores chicos y baratos arriba a la izquierda" (som-one-region notes).

They are true today. I verified that hamming >= pinv at all 11 noise levels, and that passes_empty and passes_creators are True in all stage-2 variants. But a regenerated run (the project explicitly allows republishing after Phase 3 and Phase 2 verification) could falsify a slide title with `make deliverables` still green.
**Fix:** Add facts that gate the claims. For example, `facts.load_facts` can raise `SystemExit` if `any(float(r["pinv"]) > float(r["hamming"]) for r in table)`. Likewise check that all stage-2 variants pass the occupancy filters before the "no se degrada" text is built. Or soften the prose to what the numbers show.

### WR-05: Numbers typed in slide notes contradict D-11 and the project convention

**File:** `analysis/slides.py:369` ("10 a 12 píxeles invertidos de 25"), `:345` ("25 de los 26 glifos"), `:357` ("de las 4 letras"), `:351`/`:355` ("3, 6 y 9 píxeles")
**Issue:** CLAUDE.md says "Los números del texto no se tipean: salen de `analysis/results/` por `analysis/facts.py`". These numbers are typed. At least "10 a 12 de 25" is derivable: `spurious.json` has `levels [0.4, 0.44, 0.48]` times N = 25. The test guard (`TYPED_NUMBER`) only catches numbers with a decimal comma or a percent sign, so it cannot see integers.
**Fix:** Add facts such as `letters.spur_flip_min`, `letters.spur_flip_max` and `letters.n_letters_stored`, computed from `spurious.json` and `selection.json`. For numbers that really are fixed design constants (k = 3, 6, 9), declare them as constants shared with the fact keys, or extend the test to flag bare integers outside an allow-list.

### WR-06: `summary_section` and `notes_section` put template text into HTML without escaping

**File:** `analysis/informe.py:430`, `:605`
**Issue:** `method_section` escapes the template first (`_inline_markup`) and then fills the facts. `summary_section` calls `facts.fill(finding.text, ..., wrap=fact_span)` on the raw `Finding.text`. Only the fact values are escaped (by `fact_span`). Any `<`, `&` or `>` added to a `FINDINGS` text later is emitted as markup. `notes_section` also renders `notes.md` with `markdown.markdown`, which passes raw HTML through. Notes contain creator names and handles from the CSV (`camp.*.top5`, `oja.max_name`), and the `<script` check is the only protection. No current text triggers this, but the two sibling functions are inconsistent and the failure would be silent.
**Fix:** In `summary_section`, use `facts.fill(html.escape(finding.text, quote=False), ...)`. Escape the notes before rendering, or build them from an escaped source and test it with a fact value containing `<b>`.

### WR-07: Documents contradict each other on delivery state and on the slides PDF

**File:** `CLAUDE.md:11` vs `:93-100`; `README.md` ("Las slides se entregan solo como Artifact" vs "el deck se entrega como su PDF exportado"); `DECISIONS.md:707-713` (F6 D-14)
**Issue:**
- CLAUDE.md line 11 says Phase 6 "tiene todo armado salvo la publicación". The Entrega and Pendientes sections of the same file say both Artifacts are already published, with their URLs. CLAUDE.md is the bootstrap for every new session, so the stale line misleads.
- F6 D-14 is titled "Las slides se entregan solo como Artifact" and says no PDF is exported. Its Por qué says the exported PDF is the deliverable and should be added "bajo `deliverables/`, no en `docs/`". No PDF is in `deliverables/` or anywhere versioned. README says both things in two paragraphs. `test_repro_docs` only checks that `docs/` has no export, so it cannot detect a missing deliverable.

For a defense, the team cannot tell whether the deck is delivered as a link or as a PDF, or where the PDF lives.
**Fix:** Rewrite CLAUDE.md line 11 to "...todo armado y publicado; falta compartir el link del informe". Rewrite D-14 (title and Qué) to state the final decision, which is both the Artifact and its exported PDF, delivered outside the repo. Remove the contradictory README sentence.

### WR-08: Slide-variant branches of several drivers have no test

**File:** `analysis/som_figures.py:116-150`, `:163-205`, `:224-275`; `analysis/som_profiles.py:268-328`; `analysis/campaigns.py:364-435`; `analysis/hopfield_qr_figures.py` (`plot_recovery` and `plot_shift` in the slide variant)
**Issue:** `test_variants_ej1`, `test_hopfield_qr_figures` and `test_hopfield_figures` exercise the slide variant of the PCA, Oja, letters and part of the QR figures. They do not exercise these slide paths:
- `plot_map`
- `plot_planes`
- `plot_stage1_curves`
- `plot_regions` (the new two-axis layout with `legend_ax`)
- both campaign plots (a 1x4 grid and a legend placed outside the axes)
- the QR `plot_recovery` slide legend
- the QR `plot_shift` one-row layout

These branches contain new control flow, for example `axes.flat[4 if slide else 0].legend` and `fig.legend` taken from `recall_ax` handles, so a regression would only show up in the real `make results` run.
**Fix:** Add synthetic-data tests in the style of `test_variants_ej1.py`: draw both variants into `tmp_path` and assert that the files exist and that the aspect ratio is about 12.8/4.85.

## Info

### IN-01: `slides._figure_height` ignores tables

**File:** `analysis/slides.py:542-551`
**Issue:** The height left for the figure subtracts the title, the body and the meta line but not a table. No current slide has both a table and a figure, so nothing breaks. `build_deck` also never checks the rendered height of a table slide. It only caps columns (4) and rows (5), so long cells that wrap could overflow the 824 px box with no error.
**Fix:** Estimate the table height with `_wrap_lines` per cell in `_figure_height` and `build_deck`, or forbid a slide with both a table and a figure.

### IN-02: `write_deck` deletes the previous output before writing the new one; asset-map input is under-validated

**File:** `analysis/slides.py:720-729`, `:690`, `:742`, `:55-56`
**Issue:**
- `shutil.rmtree` of `project/slides` and `assets` runs after validation but before the writes. A failure during the write or copy leaves no deck.
- `json.loads(asset_map)` is assumed to be a dict, so a list gives an unhelpful `AttributeError` at `asset_map.get`.
- `SLIDE_ID` and `BLOB_URL` use `match` with `$`, which accepts a trailing newline (`"id\n"`). Use `fullmatch`.

**Fix:** Write to a temporary folder and swap it in. Check `isinstance(asset_map, dict)`. Use `fullmatch`.

### IN-03: Percentage formatting is inconsistent across fact families

**File:** `analysis/facts.py:310-311`, `:102-110`; `analysis/hopfield_qr_figures.py` (annotation "100% exacto")
**Issue:** Letter recall rates always carry one decimal ("100,0 %"). QR rates use `pct_short` ("100 %"). The figure annotation writes "100%" without a space. The three conventions appear together in slides 20 to 22, while the fragments use "100 %".
**Fix:** Use one formatter for rates, or document the reason the two differ.

### IN-04: The "Regla fijada de antemano" tag is on `camp-futbol` although its notes say the recommendation is a judgment

**File:** `analysis/slides.py:240-242`
**Issue:** The notes of the slide say "La recomendación es un juicio y no un resultado de la regla", but the slide carries the pre-registered-rule tag. A viewer reads the tag as covering the recommendation.
**Fix:** Remove the tag from this slide, or tag only the overlap and cost figures.

### IN-05: Permutation p-values shown as equalities

**File:** `analysis/slides.py:198-205`; `analysis/facts.py:191`
**Issue:** The slide shows "p = 0,001" and the notes say "ninguna de las 1000 permutaciones lo alcanza (p = 0,001)". That value is the floor 1/1001 (0,000999), not an estimate. "p ≤ 0,001" is the usual wording when no permutation reaches the observed value.
**Fix:** Format the fact as "≤ 0,001" when the p-value equals 1/(n+1).

### IN-06: `make informe` alone produces a different page from `make deliverables`

**File:** `Makefile:208-210`, `:262-263`
**Issue:** `make informe` omits `INFORME_FLAGS`, so it overwrites `informe.html` without the "Guion de la presentación" annex. CLAUDE.md says the published informe carries the script. README mentions this, but running the isolated target silently drops it.
**Fix:** Make the `informe` target pass `$(INFORME_FLAGS)` (and depend on `slides` when the notes file is missing), or have `informe.py` warn when the annex is absent.

---

_Reviewed: 2026-10-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
