---
phase: 01-fundaci-n-auditor-a-de-datos-y-pca
reviewed: 2026-10-20T20:30:00Z
depth: standard
files_reviewed: 38
files_reviewed_list:
  - Makefile
  - analysis/eda.py
  - analysis/pca.py
  - analysis/plots_style.py
  - analysis/sweep.py
  - analysis/README.md
  - analysis/requirements.txt
  - analysis/series_smoke_hopfield.json
  - analysis/series_smoke_kohonen.json
  - analysis/series_smoke_oja.json
  - analysis/tests/conftest.py
  - analysis/tests/test_creadores.py
  - analysis/tests/test_pca.py
  - neuron/Makefile
  - neuron/README.md
  - neuron/main.c
  - neuron/rng.c
  - neuron/rng.h
  - neuron/config.json.hopfield.example
  - neuron/config.json.kohonen.example
  - neuron/config.json.oja.example
  - neuron/io/config.c
  - neuron/io/config.h
  - neuron/io/matrix.c
  - neuron/io/matrix.h
  - neuron/io/results.c
  - neuron/io/results.h
  - neuron/models/models.c
  - neuron/models/models.h
  - neuron/models/oja_stub.c
  - neuron/models/kohonen_stub.c
  - neuron/models/hopfield_stub.c
  - neuron/tests/test_main.c
  - scripts/creadores.py
  - scripts/map_creator.py
  - scripts/prepare_creadores.py
  - datos/.gitignore
  - deliverables/01-datos-pca.md
findings:
  critical: 0
  warning: 5
  info: 6
  total: 11
status: issues_found
---

# Phase 1: Code Review Report

**Reviewed:** 2026-10-20T20:30:00Z
**Depth:** standard
**Files Reviewed:** 38
**Status:** issues_found

## Summary

The C walking skeleton, the Python loader and audit, the PCA by `eigh` and the sweep runner were read in full. I also ran them in a scratch copy: `make test-c` and `make debug` (ASan/UBSan) pass with 63 checks and 0 failures, all three smoke sweeps run, and `map_creator.py` reproduces `creadores_zscore.csv` byte for byte. The C core is careful: every `strcpy` is preceded by a length check, the CSV parser rejects short, long, empty and non-finite fields, there are no integer overflows in the allocations, and the sweep uses argument lists, never a shell string. I found no security vulnerabilities and no crash or data-loss bug.

The defects are in result reporting and in input validation at the edges. The most important is a generated sensitivity report that shows a signed Pearson of -0.999 next to an absolute cosine of 0.99998 for the same component. A sweep series can also silently ignore a swept `seed`, and a failed run leaves a directory that looks like a run.

## Warnings

### WR-01: Sensitivity report mixes signed and absolute agreement measures

**File:** `analysis/pca.py:414-435` and `analysis/pca.py:457-464`
**Issue:** `sensitivity()` reports `abs_cos_pc*` as an absolute value but `pearson_pc*` and `spearman_pc*` signed. The two runs orient their eigenvectors independently (largest-magnitude coefficient positive), and in the 31-column run that coefficient belongs to another variable. The sign of PC1 therefore flips between runs. Running the code gives `abs_cos_pc1 = 0.99998` and `pearson_pc1 = -0.9992` in `sensitivity.json` and `sensitivity.md`. A reader of the generated table sees that PC1 is both nearly identical and almost perfectly anti-correlated. `deliverables/01-datos-pca.md:179` explains the flip in prose, but the generated artifacts (the ones the report and slides will be rebuilt from) carry no note, and a signed number invites misreading.
**Fix:** Make the comparison sign-invariant, or align the sign before comparing:
```python
for c in (0, 1):
    sign = np.sign(audited.eigenvectors[:, c] @ sub) or 1.0
    out[f"pearson_pc{c + 1}"] = abs(_pearson(a_scores[:, c], s_scores[:, c]))
    out[f"spearman_pc{c + 1}"] = abs(spearman(a_scores[:, c], s_scores[:, c]))
```
Name the keys `abs_pearson_pc*` and `abs_spearman_pc*`, or keep the signed values and add a "sign flipped" column to `sensitivity.md`.

### WR-02: A swept or fixed `seed` in a series is silently ignored

**File:** `analysis/sweep.py:172-181`
**Issue:** `plan()` applies the overrides and then runs `config["seed"] = seed` from `series.seeds`. A series with `"vary": "seed"` or `"set": {"seed": 9}` (or a variant `set` containing `seed`) therefore runs every variant with the seeds of the `seeds` list, not the swept values. `varied_keys` still lists `seed` as a varied key, and `run_task` then overwrites the `seed` column with the real seed. The labels (`"3"`, `"4"`, ...) claim values the runs never used, and the summary looks like a valid study. This is easy to hit, since a seed study is the main use of `sweep.py` in Phases 2 to 5.
**Fix:** Reject the key in `load_series`/`series_variants`:
```python
RESERVED_KEYS = {"seed"}
bad = RESERVED_KEYS & ({spec.get("vary")} | set(shared) | {k for v in variants for k in v.overrides})
if bad:
    raise SystemExit(f'{path}: "{", ".join(sorted(bad))}" is controlled by "seeds"; do not set or vary it')
```

### WR-03: A failed run leaves a directory that looks like a run

**File:** `neuron/main.c:51-63` (with `neuron/io/results.c:92-113`)
**Issue:** `results_create` makes `results/<ts>_<model>_seed<N>/` and copies `config.json` before `model->run` loads the input. If the input is missing, malformed, or not ±1 (all expected failures), `main` exits with an error but leaves a directory holding only `config.json`. Under `make run` nothing cleans it up, and a later `diff -r` or glob over `results/*` treats it as a run with no metrics. `sweep.py` has `clean_leftovers` to work around this, which shows the problem is known, but the binary itself is the right place to fix it.
**Fix:** In `main`, remove the run directory when `model->run` returns 0. Alternatively, load and validate the model's input before `results_create`. A minimal version:
```c
if (!model->run(&config, &rng, &results)) {
  fprintf(stderr, "%s: the %s run failed\n", path, config.model);
  results_discard(&results);   // new: removes the files it wrote and the directory
  config_free(&config);
  return EXIT_FAILURE;
}
```

### WR-04: `map_creator.py` accepts non-finite values and fails with raw tracebacks

**File:** `scripts/creadores.py:236-247` and `scripts/map_creator.py:30-36`
**Issue:** `transform_new_creator` does `float(raw[name])` with no finiteness check. `nan`, `inf` or a huge value is accepted and written to the output CSV as `nan` or `inf`. The C `matrix_load` then rejects the file, so the failure shows up a step later and far from the cause. `load_creadores` checks this for the training data (`creadores.py:122-129`), so the new-creator path is inconsistent with it. An empty cell or a short row raises a bare `ValueError` or `TypeError` traceback (`DictReader` gives `None` for a missing field), and a missing feature gives a `KeyError` traceback with a 26-name message.
**Fix:** Check `math.isfinite` inside `transform_new_creator` and raise `ValueError` naming the feature. In `map_creator.main`, catch `(KeyError, ValueError, TypeError)` per row and exit with `row N: <reason>`.

### WR-05: Audit table can overwrite the drop reason of a near-redundant variable

**File:** `analysis/eda.py:204-216`
**Issue:** When `near_row is not None`, the code sets `reason = "; ".join(notes)`, replacing whatever `reason` held. For the current data none of the four near-redundant variables is also dropped, so the table is right today. But if a dropped variable (for example `price_ars`, perfectly correlated with `price_usd`, which has r = 0.82 with `followers`) ever crosses `NEAR_THRESHOLD`, its row would say `sale (reconstruible)` with a reason that is only the near-redundancy note, and the reconstruction formula would be lost from the audit table (DATA-02). The same branch also labels `estimated_argentina_reach` (r = 0.798, below the 0.9 threshold) as "casi redundante" in the Relación column. This follows D-10, but the label contradicts the threshold shown in the same row.
**Fix:** Append instead of replacing: `reason = "; ".join([reason, *notes])`. Set the Relación label from the actual condition (`abs(r) > NEAR_THRESHOLD`), and use a separate label such as "aproximación no exacta" for the estimate.

## Info

### IN-01: Header guards use reserved identifiers

**File:** `neuron/io/config.h:1`, `neuron/io/matrix.h:1`, `neuron/io/results.h:1`, `neuron/models/models.h:1`, `neuron/rng.h:1`
**Issue:** `__CONFIG_H__` and the others start with a double underscore, which C11 7.1.3 reserves for the implementation. It works today, but it is undefined behavior in principle.
**Fix:** Use `CONFIG_H`, `MATRIX_H`, and so on, or `TP4_NEURON_CONFIG_H`.

### IN-02: Unknown-model check in `main.c` is unreachable

**File:** `neuron/main.c:44-49`
**Issue:** `config_load` already rejects any model not in `MODEL_KEYS` (`config.c:270-276`), and `test_dispatch_by_model` pins both tables to the same names. The `model == NULL` branch in `main` therefore never runs, and its message duplicates the one in `config.c`. It is harmless defensive code, but it is a second source for the "available models" text.
**Fix:** Keep it as an `assert`-style guard with a short message, or drop it and rely on the dispatch test.

### IN-03: `sweep.py` series validation has gaps that end in tracebacks

**File:** `analysis/sweep.py:130-135` and `analysis/sweep.py:364`
**Issue:** `"vary"` is never checked to be a string. A list or number gets past `series_variants` and fails in `set_dotted` with `AttributeError` or `TypeError`. `--workers -1` passes `args.workers or series.workers` and fails inside `ThreadPoolExecutor` after the binary was built and the sweep directory created, leaving an empty directory. `--workers 0` is silently replaced by the series value.
**Fix:** `if not isinstance(spec["vary"], str) or not spec["vary"]: raise SystemExit(...)`. Add `type=positive_int` to the `--workers` argument.

### IN-04: C CSV parser rejects whitespace around the last field

**File:** `neuron/io/matrix.c:81-94`
**Issue:** `strtod` skips leading whitespace, but `separator_ok` requires `*end == ',' ` or `'\0'` with no tolerance for trailing spaces. A row like `1.0, 2.0 ` fails with "expected N numeric columns", which points at the wrong cause. The header is trimmed (`trimmed_copy`) and rows are not, so the two are inconsistent. Python writes no spaces, so nothing breaks today. The Phase 4 QR files may be produced by a different script.
**Fix:** Skip trailing `isspace` characters after `strtod` before testing the separator, and say "unexpected character '%c' at column %d" in the message.

### IN-05: `plot_scree` reads a private palette slot

**File:** `analysis/pca.py:262`
**Issue:** `plots_style._SERIES[1]` reaches into a private constant, while the blue is obtained through `palette_for`. The orange will break silently if the palette is reordered.
**Fix:** `orange = plots_style.palette_for(["a", "b"])["b"]`, or export a named `HIGHLIGHT` constant from `plots_style.py`.

### IN-06: Smaller validation and test gaps

**File:** `scripts/creadores.py:98-131`, `scripts/creadores.py:252-260`, `neuron/tests/test_main.c:120-142`
**Issue:**
- `load_creadores` does not check for duplicate column names. A repeated name makes `columns.index(name)` use the first column without any error. A stray blank line in the data gives a confusing "expected 50 rows" message.
- `_atomic_write` uses `tempfile.mkstemp`, so the prepared files are created with mode 0600 (confirmed with `ls -l datos/prepared`). Other users or containers on the same machine cannot read them. The CSV and the `.meta.json` are each replaced atomically, but not as a pair.
- `compare_dirs` only iterates `dir_a`, so an extra file in `dir_b` goes unnoticed. The hopfield same-seed test also passes `NULL` for the seed-dependence check, as its comment says, so the Rng is not covered on that path.
**Fix:** Add `if len(set(header)) != len(header)` to the loader. Call `os.chmod(temp_name, 0o644)` before `os.replace`. Have `compare_dirs` also count the entries of `dir_b` and compare the two counts.

---

_Reviewed: 2026-10-20T20:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
