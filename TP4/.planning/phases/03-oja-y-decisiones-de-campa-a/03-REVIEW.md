---
phase: 03-oja-y-decisiones-de-campa-a
reviewed: 2026-10-22T00:00:00Z
depth: standard
files_reviewed: 19
files_reviewed_list:
  - Makefile
  - analysis/README.md
  - analysis/campaigns.py
  - analysis/campaigns_select.py
  - analysis/maintenance_demo.py
  - analysis/oja.py
  - analysis/series_oja.json
  - analysis/series_smoke_oja.json
  - analysis/tests/test_campaigns.py
  - analysis/tests/test_campaigns_select.py
  - analysis/tests/test_maintenance_demo.py
  - analysis/tests/test_oja.py
  - deliverables/03-oja-campanas.md
  - neuron/README.md
  - neuron/config.json.oja.example
  - neuron/io/config.c
  - neuron/models/models.h
  - neuron/models/oja.c
  - neuron/tests/test_main.c
findings:
  critical: 0
  warning: 5
  info: 9
  total: 14
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-10-22
**Depth:** standard
**Files Reviewed:** 19
**Status:** issues_found

## Summary

Reviewed the Oja rule in C (`oja.c`, `config.c`, `models.h`, C tests), the Python analysis (`oja.py`, `campaigns.py`, `maintenance_demo.py`), the frozen rule module (`campaigns_select.py`), the tests, the Makefile, both READMEs and the deliverable.

Checks run beyond reading:
- `pytest` on `test_campaigns`, `test_campaigns_select`, `test_maintenance_demo` and `test_oja`: 35 passed.
- `make -C neuron debug` (ASan and UBSan): 176 checks, 0 failed, no sanitizer report.
- `campaigns_select.rule_identity()` at HEAD returns commit `a6212e89...`, so the pre-registration guard still passes.
- Every line of `report_pc1.md`, `report_convergence.md`, `report_evidence.md`, `report_campaigns.md`, `report_reading.md` and `report_demo.md` appears verbatim in the deliverable.
- Spot-recomputed from `datos/creadores.csv`:
  - The filter sizes (15, 13, 11, 11).
  - The follower and price figures quoted in section 5 (`@crearenreels`, `@entrelienzos`, `@creatividadaldia`, the profundidad list's 15556 to 60817 followers).
  - The two football creators whose dominant topic is football (`@makeupconsejos` 59,1 %, `@vidaperruna` 69,5 %).
  - The claim of no exact ties in any criterion or in `followers`.
  - The `price_ars = 1500 * price_usd` and `estimated_argentina_reach = round(average_reach * audience / 100)` relations.
  - The convergence numbers of section 1.
  All match.

No correctness bug, security vulnerability or data-loss risk was found, so there are no Critical findings. The C code is sound: allocations are freed on every path, the metric count is 16 as declared, the stability guard runs before anything is allocated, and the orientation helper is correct. The warnings concern the strength of the pre-registration guard, the missing enforcement of the Oja gates, an overstated comparison in the deliverable, build-system behaviour, and the informativeness of the drift demo.

**Pre-registration note (D-07).** `analysis/campaigns_select.py` and the text between `<!-- regla:inicio -->` and `<!-- regla:fin -->` in `deliverables/03-oja-campanas.md` are frozen by commit a6212e8. WR-01 and IN-08 are reported against the frozen file. Any fix inside it would change `select_sha256` or `rule_sha256` and void the pre-registration (one-way door). Both entries give a fix that stays outside the frozen files.

## Warnings

### WR-01: The pre-registration guard does not pin the code it depends on (frozen file)

**File:** `analysis/campaigns_select.py:31, 211-231`
**Issue:** `rule_identity` proves that the select file and the rule text did not change. It does this with `rule_digest`, `RULE_START` and `RULE_END`, which are imported from `analysis/som_select.py` (line 31). That module is not part of the hashed or committed-together set. `scripts/creadores.py` (`load_creadores`, which supplies the data the rule runs on) is not pinned either. If `som_select.rule_digest` changes (for example it starts normalising whitespace or changes the marker strings), the guard would accept an edited rule text, or refuse a valid one, without any change to `campaigns_select.py`. The recorded `select_sha256` would not show it. The identity written to `selection_identity.json` therefore does not fully identify "the rule as it was when committed".
**Fix:** Do NOT edit `campaigns_select.py`; that would void the pre-registration. Close the gap in the non-frozen consumer `analysis/campaigns.py`: after `rule_identity()`, add to `selection_identity.json` the sha256 of `analysis/som_select.py` and `scripts/creadores.py`, and refuse if `git status --porcelain` reports either as modified. Alternatively, state the limitation in section 5 of the deliverable (outside the markers).

### WR-02: The Oja alignment and orientation "gates" are never enforced

**File:** `analysis/oja.py:3-11, 43, 605-678`
**Issue:** The module docstring says a seed whose `w` disagrees in sign with PCA "is reported as it is and fails the gates". The only gate is `COS_MIN = 0.99`, and it is only counted in `dispersion()` (`n_abs_cos_above`). `main()` never raises or returns non-zero. If a re-run on other data gave a flipped sign or a poorly converged `w`, `make oja` would succeed and write `index.csv`. `campaigns.py` and `maintenance_demo.py` would then consume that index silently, including its D-02 sign, which is the tie-break and the maintenance rank. The threshold is also very loose: the observed values are 0.9999997 or better, while 0.99 would let an index with errors of order one pass. The only automated check is `test_smoke_run_matches_pc1`, and it covers a single seed.
**Fix:** After `dispersion(...)`, fail loudly (a `SystemExit` after writing the reports is fine) when `n_abs_cos_above != n_seeds` or `n_same_orientation != n_seeds`. Tighten `COS_MIN`, for example to 0.9999, if the stricter value is acceptable for the data. Otherwise remove the "fails the gates" wording from the docstring.

### WR-03: Section 5.5 presents a result guaranteed by construction as evidence

**File:** `deliverables/03-oja-campanas.md:266` (outside the frozen markers)
**Issue:** The bullet "Métrica objetivo" says that in every objective the own list beats both baselines on the mean of its criterion, except reach against the global baseline. Each own list is, by construction, the top 5 of the criterion inside the topic filter. The "followers in topic" baseline is a subset of that same filter, so it can never score higher. The bullet therefore carries no information about that baseline. Only the comparison with the global baseline, which is not restricted to the topic, is informative. Section 5.1 says "por construcción" for one case, but 5.5 presents the whole bullet as a finding. A reader or grader could take it as empirical support for the rule.
**Fix:** Reword the bullet: against the in-topic baseline the criterion mean is higher by construction, since the list is the argmax of the criterion inside the filter, so only the global baseline comparison and the cost and overlap columns say anything. Keep the exception for reach.

### WR-04: `make campaigns` and `make maintenance` re-run every upstream stage on each call

**File:** `Makefile:51-52, 70-71, 77-78, 83-84`
**Issue:** `oja`, `pca` and `som-stage1` are `.PHONY` and have no file targets, so each `make campaigns` or `make maintenance` re-runs the 10 Oja runs and the 140 SOM runs of stage 1. Each run creates a new timestamped sweep directory (`analysis/results/series_oja_*`, `series_som_stage1_*`). The results folder already holds 15 `series_oja_*` and 3 `series_som_stage1_*` directories from one afternoon, and nothing prunes them. The cost is also slow feedback for the short Python-only targets. Besides disk growth, `runs.json` and `selection.json` change on every call, which defeats the byte-stable claim for anything downstream.
**Fix:** Make the outputs the targets. For example `analysis/results/oja/index.csv: analysis/oja.py neuron/models/oja.c analysis/series_oja.json $(PCA_STAMP)` with the recipe `$(PY) analysis/oja.py`, and `analysis/results/som/series_som_stage1/selection.json:` likewise. Then `campaigns` and `maintenance` depend on those files. Alternatively, have `sweep.create_sweep_dir` reuse or prune old directories of the same series.

### WR-05: The drift demo cannot exercise the retrain branch and the threshold is an in-sample statistic

**File:** `analysis/maintenance_demo.py:62-76, 111-121, 214-215`; `deliverables/03-oja-campanas.md:307-315`
**Issue:** The synthetic creator is built from column medians. In the generated report it is closer to its BMU (1,329) than any of the 50 training creators ("el 0,0 % de esas distancias es menor o igual"), so the verdict "no hace falta re-entrenar" is foregone and only the "no drift" branch is shown. The retrain branch is covered by a unit test on toy numbers, never end to end. The training distances (`run.distance`) are measured on the same 50 creators the prototypes were fitted to, so they are optimistic. A held-out creator from the same distribution will exceed the maximum of 50 in-sample distances with probability of at least 1/51 (about 2 %), and more because of the optimism. A monthly "retrain only above the max" check can therefore trigger spuriously, and section 6 does not say so. `som_loo.py` already provides leave-one-out distances.
**Fix:** Add a second synthetic case (for example the medians with two or three variables at several SD) so the demo shows the retrain verdict too. Add one sentence in section 6 about the in-sample bias, or compute the threshold from leave-one-out BMU distances.

## Info

### IN-01: Unused import

**File:** `analysis/maintenance_demo.py:32`
**Issue:** `import pca` is never used (no `pca.` reference in the module). The `# noqa: E402` hides only the import-position warning, not the unused-import one.
**Fix:** Remove the line.

### IN-02: Magic constants and hard-coded counts in the maintenance demo

**File:** `analysis/maintenance_demo.py:72, 164, 174`
**Issue:** `1500.0` (the ARS/USD rate behind `price_ars`) is hard-coded; the data confirm the ratio is exactly 1500, but nothing ties the code to it. The report text hard-codes "31 columnas" and "50 creadores".
**Fix:** Derive the rate from the data (`median(price_ars / price_usd)`) or name it as a constant. Format the counts from `len(data.columns)` and `len(training_indices)`.

### IN-03: Duplicated helpers across three modules

**File:** `analysis/oja.py:188, 416, 468`; `analysis/campaigns.py:76, 227, 223`; `analysis/maintenance_demo.py:155`
**Issue:** `_decimal` exists three times with slightly different NaN handling. `_write_lines` and the CSV writer are duplicated, and `overlap` is defined in both `oja.py` and `campaigns.py` with different argument types.
**Fix:** Move the shared formatting and writing helpers into one small module (for example `analysis/report_io.py`) that all three import.

### IN-04: Cross-module use of private names

**File:** `analysis/oja.py:37`; `analysis/campaigns.py:389, 414`
**Issue:** `pca._pearson`, `som_figures._caption` and `som_figures._grid_axes` are private by name but used from other modules. A rename in the owner module breaks these without warning.
**Fix:** Export them under public names in their owner modules.

### IN-05: Path from `selection.json` is joined without validation

**File:** `analysis/campaigns.py:195`; `analysis/maintenance_demo.py:197`
**Issue:** `TP_DIR / selection["figure_run"]`: an absolute path or one with `..` in that generated file escapes `TP_DIR`, because `Path` division replaces the left side for an absolute right operand. The file is locally generated, so the risk is low, but the pattern is a path-traversal shape.
**Fix:** Resolve the path and check `candidate.resolve().is_relative_to(TP_DIR)` before `som.read_run`.

### IN-06: Palette built from a list with a repeated key, and a hard-coded count in a legend

**File:** `analysis/campaigns.py:368-369, 373`
**Issue:** `objectives` has `profundidad` twice (football and makeup). `palette_for` is a dict comprehension, so the second index wins and slot 2 is never used. Harmless today (6 entries, 8 slots), but it is accidental. The legend label "los 50 creadores" is hard-coded.
**Fix:** Pass `list(dict.fromkeys(objectives))` and use `len(pc)` in the label.

### IN-07: NaN or inf can leak into JSON or reports

**File:** `analysis/oja.py:193-205, 408-409, 633`; `analysis/campaigns.py:85-111, 229-231`
**Issue:** `som.spearman_ties` returns NaN when a rank vector is constant, and `json.dumps` writes it as the invalid token `NaN` in `comparison.json`. In `campaigns.list_metrics`, a member with zero Argentine reach gives an infinite criterion for `costo_por_mil`, so `criterion_mean` is `inf` and `_decimal` prints "inf" (only NaN is mapped to "n/d"). Neither happens on the current data.
**Fix:** Pass `allow_nan=False` to `json.dumps` (or map NaN to `None`), and treat `math.isinf` like NaN in `_decimal`.

### IN-08: Frozen file: git output depends on the user's git configuration

**File:** `analysis/campaigns_select.py:173-187` (frozen; any edit voids D-07)
**Issue:** `_added_commit` parses the whole stdout of `git log --format=%H`. A user config such as `log.showSignature=true` adds signature text to stdout, so the 40-hex match fails and the run is refused with a misleading message. This fails closed, so it is not a correctness risk, only a usability one.
**Fix:** Do not edit the file. Document the behaviour in `analysis/README.md`, or run the guard with `GIT_CONFIG_GLOBAL=/dev/null` from the non-frozen `campaigns.py` before calling `rule_identity`.

### IN-09: Reader robustness and test coverage gaps

**File:** `analysis/oja.py:139-161`; `analysis/campaigns.py:134-147, 168-178`; `analysis/tests/test_campaigns_select.py:72-74`
**Issue:**
- `_read_pca_table` and `_read_columns` index `rows[0]` and fixed cell positions. An empty or short file gives a bare `IndexError`, and `read_explained` gives a bare `KeyError`. The rest of the module promises errors that name the file (T-03-07).
- Tests cover none of `main()`, `shortlist_rows` (its 20 cells must match `SHORTLIST_COLUMNS + READING_COLUMNS`), the `read_*` error paths, `report_lines` or `read_weights`.
- The comment at `test_campaigns_select.py:72-74` mixes notes about rows 3, 4 and 5 with the separate `tie` case and is hard to follow. The assertions are correct.
**Fix:** Raise `SystemExit` or `ValueError` with the file name on empty or short input. Add one test that builds the shortlist rows for a toy dataset and checks the row width against the header. Rewrite the comment as one note per row.
