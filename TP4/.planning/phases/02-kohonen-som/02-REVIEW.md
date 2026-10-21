---
phase: 02-kohonen-som
reviewed: 2026-10-21T15:20:00Z
depth: standard
files_reviewed: 23
files_reviewed_list:
  - Makefile
  - analysis/README.md
  - analysis/series_som_stage1.json
  - analysis/series_som_stage2.json
  - analysis/som.py
  - analysis/som_figures.py
  - analysis/som_loo.py
  - analysis/som_profiles.py
  - analysis/som_select.py
  - analysis/som_stage.py
  - analysis/tests/test_som.py
  - analysis/tests/test_som_figures.py
  - analysis/tests/test_som_profiles.py
  - analysis/tests/test_som_select.py
  - analysis/tests/test_som_stage.py
  - analysis/tests/test_som_stats.py
  - deliverables/02-kohonen.md
  - neuron/README.md
  - neuron/config.json.kohonen.example
  - neuron/io/config.c
  - neuron/models/kohonen.c
  - neuron/models/models.h
  - neuron/tests/test_main.c
findings:
  critical: 0
  warning: 4
  info: 7
  total: 11
status: issues_found
---

# Phase 2: Code Review Report

**Reviewed:** 2026-10-21T15:20:00Z
**Depth:** standard
**Files Reviewed:** 23
**Status:** issues_found

## Summary

Reviewed the C Kohonen trainer (`kohonen.c`, config keys, tests), the Python measurement/selection/stage/figure/profile modules, their tests, the Makefile, the READMEs and the deliverable. `make test` passes (118 C checks, 48 pytest) and `make debug` (ASan/UBSan) is clean. I cross-checked the C `nearest_two` tie rules against the numpy stable-argsort recomputation, the training schedule against the formulas written in section 1 of the deliverable, and a sample of the numbers quoted in sections 3 to 6 against `analysis/results/` (k = 5 TE per seed, stage-2 aggregate, selection.json); they agree. I also confirmed that the rule block, `som_select.py` and `series_som_stage1.json` in the working tree are byte-identical to the versions in the rule commit `ea7a0b1`, so the pre-registration was in fact respected in this run.

No blocker was found. The four warnings are: the pre-registered code does not deliver the "equality passes" semantics it promises (verified to misfire in about 4 percent of exact-boundary cases), the "committed before looking" guard does not actually compare against the rule commit's content, the stage-2 robustness verdict never checks that the series is on the chosen k, and the gaussian kernel can silently write NaN prototypes for a tiny `radius_final`.

Pre-registration note (D-10): `analysis/som_select.py`, `analysis/series_som_stage1.json` and the text between `<!-- regla:inicio -->` and `<!-- regla:fin -->` in `deliverables/02-kohonen.md` are the pre-registered artifacts. A finding that says "PRE-REGISTERED" below means that fixing it in place would change a file covered by the rule digest and would void the pre-registration; it needs a new discussion phase, not an in-place edit. Findings that are not marked can be fixed freely.

## Warnings

### WR-01: "Equality passes" at the filter thresholds is not guaranteed under floating point (PRE-REGISTERED)

**File:** `analysis/som_select.py:116-122` (comparisons), `analysis/som_select.py:94,101-103` (the means)
**Issue:** The rule text says "La igualdad pasa: un TE medio de exactamente 0,05, un 20 % exacto de vacías y exactamente 2 creadores por neurona ocupada no excluyen". The code compares `np.mean` of ten per-seed values with `<=` / `>=` against 0.05, 0.20 and 2.0 with no tolerance. Per-seed TE is `count / 50`, and the mean of ten such floats is not exact. I simulated 20 000 random ten-seed TE profiles whose true mean is exactly 0.05 (counts summing to 25): 764 of them (3.8 percent) give a mean above 0.05, for example per-seed counts `[1, 4, 1, 5, 4, 5, 1, 1, 1, 2]` give `0.05000000000000001`, and the grid is wrongly excluded. The same applies to `empty_fraction_mean` at 0.20 and `creators_per_occupied_mean` at 2.0. Impact in this run: none. I checked `aggregate.csv` of stage 1 and stage 2; no value sits on a boundary except `epochs-1040`, whose `te_mean` is exactly `'0.05'` and passes by luck of the summation order. The stage-2 verdict "no robusta (5 variantes)" does therefore not depend on this. The unit test `test_select_filters_boundaries` only uses literal floats, so it cannot catch the aggregation error.
**Fix:** Fixing this in place voids the pre-registration (it edits `som_select.py`, whose sha256 is recorded in `selection.json`) and needs a new discussion phase. If reopened, compare exact quantities: keep integer counts (sum of per-seed TE counts, sum of occupied neurons) and compare rationals, or compare with a fixed tolerance, e.g.:
```python
EPS = 1e-12
"te": row["te_mean"] <= TE_MAX + EPS,
"empty": row["empty_fraction_mean"] <= EMPTY_MAX + EPS,
"creators": row["creators_per_occupied_mean"] >= CREATORS_MIN - EPS,
```
and add a boundary test that goes through `aggregate()` with ten per-seed values like the example above. Until then, the deliverable could state that equality is decided in double precision.

### WR-02: The rule guard never compares the current rule text or code with the rule commit; `rule_commit` can mislabel what actually ran

**File:** `analysis/som_stage.py:70-98` (`rule_identity`), `analysis/som_stage.py:101-113` (`require_same_rule`)
**Issue:** `rule_identity` requires the three files to be tracked and clean and to have been added in one commit, then records `rule_commit` (the adding commit) next to `rule_sha256` / `select_sha256` computed from the current working tree. Nothing checks that the content at `rule_commit` equals the current content. If the text between the markers, or `som_select.py`, is edited and committed in a later commit (clean tree, still tracked), a stage-1 run passes the guard and `selection.json` and section 3 of the deliverable report `rule_commit` = the original commit while the digest is of the edited text. The test `test_rule_identity_guards_code` even asserts that later commits "never move the rule commit", but never exercises an edit inside the markers. `require_same_rule` only compares with whatever the last stage-1 run recorded, so it cannot detect this either. In this repository the rule block, `som_select.py` and the stage-1 series are byte-identical to `ea7a0b1` (I checked), so the claim is true today; the guard just does not enforce it, contrary to the "committed before looking is mechanical" intent in the `som_select.py` docstring.
**Fix:** This lives in `som_stage.py`, which is not pre-registered, and the rule's own "Control" bullet describes only the weaker clean-and-tracked guarantee, so strengthening it does not change the registered text. In `rule_identity`, after computing `rule_commit`, compare against the committed blobs:
```python
def _blob(commit, path, repo_dir):
    return subprocess.run(["git", "show", f"{commit}:{subprocess.check_output(['git','rev-parse','--show-prefix'], cwd=repo_dir, text=True).strip()}{path}"],
                          cwd=repo_dir, capture_output=True, check=True).stdout

# rule text
at_commit = hashlib.sha256(<text between markers of _blob(rule_commit, RULE_FILE)>).hexdigest()
if at_commit != som_select.rule_digest(repo_dir / som_select.RULE_FILE):
    raise SystemExit("rule text differs from the rule commit (D-10)")
# code and series
for path in (som_select.SELECT_FILE, som_select.STAGE1_SERIES):
    if _blob(rule_commit, path, repo_dir) != (repo_dir / path).read_bytes():
        raise SystemExit(f"{path} differs from the rule commit (D-10)")
```
(`rule_digest` needs a variant that takes text instead of a path.) Add a test that edits the text inside the markers, commits, and expects `SystemExit`.

### WR-03: Stage-2 robustness verdict never checks that the series is on the chosen k

**File:** `analysis/som_stage.py:229-255` (`_write_robustness`), `analysis/som_stage.py:147-157` (`run_stage`)
**Issue:** For stage 2, `run_stage` only checks the rule digests (`require_same_rule`); `_write_robustness` reads `chosen_k` from the stage-1 selection only to test `is None`. Nothing verifies that the rows of `aggregated` have `grid_k == chosen_k` (or that the stage-2 series equals `som_select.stage2_series(chosen_k)`). A stale or hand-edited `analysis/series_som_stage2.json` (it is committed and clean, so the guard passes) written for another k would yield a `robustness.json` that the deliverable would present as "robustez de k = 5". The deliverable states the series "lo generó `write-stage2` a partir de la k elegida", but this is not enforced when `make som-stage2` runs.
**Fix:** In `_write_robustness`, before computing flags:
```python
chosen_k = int(stage1["chosen_k"])
wrong = sorted({int(row["grid_k"]) for row in aggregated} - {chosen_k})
if wrong:
    raise SystemExit(f"stage-2 series has grid_k {wrong}, stage 1 chose k = {chosen_k} (D-06)")
```
and optionally compare the loaded series against `som_select.stage2_series(chosen_k)` in `run_stage` when `not select`.

### WR-04: Gaussian kernel writes NaN prototypes (and exits 0) for a tiny `radius_final`

**File:** `neuron/models/kohonen.c:176-178` (`kohonen_neighbor_weight`), `neuron/models/kohonen.c:69-79` (range checks)
**Issue:** The validation only requires `radius_final > 0` for the gaussian. The weight is `exp(-d2 / (2 * radius * radius))`; when `radius * radius` underflows to 0 (radius below about 1e-162) and `d2 == 0` this is `0.0 / 0.0 = NaN`, so the winner's update `weights[j] += eta * NaN * ...` corrupts its prototype. I reproduced it with the 6-row fixture, `neighborhood: gaussian`, `radius0: 2`, `radius_final: 1e-170`: the binary exits 0, `prototypes.csv` contains `4,1,1,nan,nan,nan`, and `metrics.json` reports plausible-looking `qe` 0.587 and `te` 0.833 because `d < best` is false for NaN distances. The error is silent, which is worse than a rejected config. Input is unrealistic for the assignment's grid, but the code claims `(> 0)` is a sufficient domain and the project's config policy is strict validation.
**Fix:** Reject values for which the kernel is not representable, or make the weight robust:
```c
// kohonen.c, read_params: gaussian floor
if (params->gaussian && params->radius_final < 1e-3) { /* error: radius_final must be >= 0.001 */ }
```
or in `kohonen_neighbor_weight` return `d2 == 0 ? 1.0 : exp(-d2 / (2 * radius * radius))` (which also makes the winner's weight exactly 1 for any radius), and add a C test case for a tiny `radius_final`.

## Info

### IN-01: QE-LOO never discriminates between eligible grids, so "gana la de menor QE-LOO" is "gana la k más grande que pasa los filtros" (PRE-REGISTERED)

**File:** `analysis/series_som_stage1.json`, `deliverables/02-kohonen.md` (rule block, bullet "Ganadora y desempate"), `analysis/som_select.py:187-197`
**Issue:** In the stage-1 results the step QE-LOO mean is strictly decreasing in k (3.944, 3.638, 3.422, 3.295, 3.253, 3.226, 3.213). With a monotone criterion the winner is always the largest k that survives the occupancy and TE filters, so the filters (thresholds 0.05, 20 %, 2 creators, all fixed without a stated derivation) decide the outcome, and the QE-LOO band and the stability tie-break are inert here (the band had one member). The deliverable presents the choice as QE-LOO-driven; section 3 itself shows k = 5 passes TE only by 0.046 vs 0.05 and stage 2 then fails TE in 5 of 10 variants. This is a design observation, not a bug, and the deliverable already reports the limitation honestly.
**Fix:** Pre-registered, so no in-place edit; if the rule is reopened in a new discussion phase, state in the report that QE-LOO is monotone in k here and the result is effectively "largest k passing the filters", or use a criterion that has an interior optimum.

### IN-02: `measure()` has a dead allocation branch with an unchecked `calloc`

**File:** `neuron/models/kohonen.c:199-206,216,227-234`
**Issue:** Every caller (`trace_row`, `write_outputs`) passes a non-NULL `hits`, so the `own = calloc(...)` branch is never taken. If it were, a failed `calloc` would silently produce `counts == NULL` and zero occupancy statistics with no error. The comment "Each output array is optional" also overstates what the callers use.
**Fix:** Drop the optional-`hits` path (make `hits` required) or check the `calloc` result and return an error.

### IN-03: Three copies of the same CSV writer and two of the same decimal formatter

**File:** `analysis/som_stage.py:131-136`, `analysis/som_loo.py:131-136`, `analysis/som_profiles.py:324-329`; `analysis/som_figures.py:108-109` and `analysis/som_profiles.py:332-333`
**Issue:** `_write_csv` / `write_csv` repeat the same `repr(float)` logic (the profiles copy also handles `np.floating`, the others do not), and `_fmt` / `_decimal` both implement the Spanish decimal comma. A fix in one (for example numpy floats, which `som_stage._write_csv` would write via `str` with full numpy repr) will not reach the others.
**Fix:** Put one `write_csv` and one `fmt_es` in `som.py` or `plots_style.py` and import them.

### IN-04: `plot_regions` has an unused parameter and reaches into a private name

**File:** `analysis/som_profiles.py:254` (`cut_pairs`), `analysis/som_profiles.py:265` (`plots_style._SERIES`)
**Issue:** `cut_pairs` is accepted and passed by `main` but never read (the function iterates `result.cut`); `plots_style._SERIES` is a private attribute of another module.
**Fix:** Remove `cut_pairs` from the signature and the call, and expose a public `plots_style.SERIES_COUNT` (or equivalent).

### IN-05: `test_umatrix_2x2` builds `expected` twice, the second time overwriting entries with literals

**File:** `analysis/tests/test_som_figures.py:14-24`
**Issue:** `expected` is created with the right values and then `expected[0, 0], expected[0, 1] = 3.0, 5.0` re-assigns the same numbers, with a comment that restates them. It reads as if the first construction were wrong; the test still checks the right thing but is confusing to maintain.
**Fix:** Delete the redundant reassignment and keep one derivation with the comment.

### IN-06: LOO fold files and `read_matrix` assume the input has no blank or quoted lines

**File:** `analysis/som_loo.py:42-60`
**Issue:** `write_folds` splits the input with `splitlines()` and `read_matrix` re-reads it with `csv.reader`; the held-out row is matched by index (`x[fold]`). A trailing blank line yields an extra empty data line in the folds (the C loader may reject or accept it) and an empty row in `read_matrix` (a ragged array error), and a blank line in the middle would shift the index silently. The generated `creadores_zscore.csv` has neither, so this is latent.
**Fix:** Drop empty lines in both functions (`if line.strip()`), and assert `len(data) == len(x)` before building the folds.

### IN-07: `read_run` raises bare `ValueError` from `int()` / `float()` without naming the file

**File:** `analysis/som.py:91,99-101,117`
**Issue:** The docstring promises "A header or neuron-numbering mismatch raises ValueError naming the file (T-02-04)". Header and numbering mismatches do, but a non-numeric cell (a `nan` is fine, a truncated run is not) raises `invalid literal for int()` with no path. `aggregate` in `som_select.py:67-108` likewise does not check that every label has the same seeds and the same `n_samples` (PRE-REGISTERED; any change there needs the new discussion phase).
**Fix:** Wrap the parsing of each table in `try/except ValueError as error: raise ValueError(f"{path}: {error}") from error`.

---

_Reviewed: 2026-10-21T15:20:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
