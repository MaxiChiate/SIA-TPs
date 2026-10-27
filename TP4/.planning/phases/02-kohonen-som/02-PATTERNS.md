# Phase 2: Kohonen SOM - Pattern Map

**Mapped:** 2026-10-21
**Files analyzed:** 17 (new or modified)
**Analogs found:** 15 / 17
All analog paths were checked with `git ls-files`; every one is tracked source, none is a mirror.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `neuron/models/kohonen.c` (git mv from `kohonen_stub.c`) | model | batch (training loop) + file-I/O | `neuron/models/kohonen_stub.c` | exact (same file) |
| `neuron/io/config.c` (KOHONEN_KEYS rows) | config | request-response (validation) | `neuron/io/config.c` lines 12-34 | exact |
| `neuron/config.json.kohonen.example` | config | n/a | itself | exact |
| `neuron/tests/test_main.c` (Kohonen checks) | test | request-response | `neuron/tests/test_main.c` lines 204-217, 274-311 | exact |
| `neuron/README.md`, `neuron/models/models.h` comment, `analysis/README.md` | docs | n/a | existing rows | exact |
| `analysis/som.py` | utility | transform | `analysis/pca.py` (helpers, `from __future__`, numpy only) | role-match |
| `analysis/som_loo.py` | service/driver | batch, subprocess | `analysis/sweep.py` `run_task`, `run_all` | role-match |
| `analysis/som_select.py` | utility + CLI | transform | `analysis/pca.py` `decision` and `main` | role-match |
| `analysis/som_figures.py` | utility | file-I/O (plots) | `analysis/pca.py` `plot_biplot`, `run_variant`, `main` | role-match |
| `analysis/series_som_stage1.json`, `series_som_stage2.json` | config | batch | `analysis/series_smoke_kohonen.json` + `variants` support in `sweep.py` | exact |
| `analysis/series_smoke_kohonen.json` (update) | config | batch | itself | exact |
| `analysis/tests/test_som.py` | test | transform | `analysis/tests/test_pca.py`, `conftest.py` | exact |
| `deliverables/02-kohonen.md` | doc | n/a | `deliverables/01-datos-pca.md` section 5 and 6 | exact |
| `Makefile` targets (som, optional) | config | n/a | root `Makefile` `pca` target | role-match |
| `neuron/models/kohonen.c` occupancy.csv and trace.csv writers | model | file-I/O | `write_prototypes` in the stub | exact |
| U-matrix, hit map, planes (inside `som_figures.py`) | utility | transform | none (no SOM-specific code yet) | no analog |
| tie-aware Spearman (inside `som.py`) | utility | transform | `analysis/pca.py::spearman` (wrong with ties; use as signature only) | partial |

## Pattern Assignments

### `neuron/models/kohonen.c` (model, batch + file-I/O)

**Analog:** `neuron/models/kohonen_stub.c` (rename with `git mv`; `models.c` dispatch and Makefile `wildcard` need no change).

**Keep verbatim** (`nearest`, `distance`, writers). Imports (lines 5-9):
```c
#include "../io/matrix.h"
#include "models.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
```

**BMU with lowest-index tie** (lines 61-73) is the only BMU routine; reuse it for training, for QE/TE and for the second BMU (extend with a `second` variant, same tie rule).

**Table writer pattern** (lines 77-102): malloc table and header, `ok = a != NULL && b != NULL`, `fprintf(stderr, "kohonen: couldn't allocate ...")`, `results_write_table(results, name, width, header, n_rows, table)`, free both. Copy this shape for `occupancy.csv` (neuron,row,col,hits) and `trace.csv` (epoch,eta,radius,qe,te). `write_assignments` (lines 106-152) adds a `bmu2` column; keep sample,bmu,row,col,distance.

**Metrics pattern** (lines 135-147): fixed array `Metric metrics[METRICS_COUNT]`, entries `{ "model", "kohonen", 0 }`, `{ "seed", NULL, config->seed }`, then `results_write_metrics`. Update `#define METRICS_COUNT 8` (line 11) to the new key count (RESEARCH Pattern 1 lists 19 keys: model, seed, n_samples, n_features, grid_k, n_neurons, neighborhood, epochs, radius0, radius_final, eta0, eta_final, qe, te, occupied_neurons, empty_fraction, mean_hits_occupied, max_hits, singleton_neurons). String values must pass `is_plain`.

**Validation before allocation** (lines 23-31; replace the `integer_sqrt` cap, D-07):
```c
static int read_grid_k(const Config * config, int n_samples, int * grid_k) {
  if (!config_get_int(config, "grid_k", grid_k)) return 0;
  ...
    fprintf(stderr, "%s: grid_k must be between 1 and %d\n", config->path, max);
    return 0;
```
New version: `2 <= k <= 32`, no dependency on n. Add the same style of reader for `neighborhood` (`"step"` or `"gaussian"`), `radius0 >= 1`, `radius_final` (step >= 1, gaussian > 0), `0 < eta0 < 1`, `0 < eta_final <= eta0`, `epochs >= 1`; compute `T` as `long long`.

**Init fix (Pitfall 4)**: `pick_prototypes` (lines 35-51) reads `order[neuron]` past `n_rows` when k*k > n. Use `order[neuron % n_rows]`, or reshuffle with `rng_shuffle(rng, order, n)` each time the index wraps.

**Core training loop**: copy RESEARCH Pattern 2 (lines 215-237 of 02-RESEARCH.md) verbatim, with `fmax(R, radius_final)` clamp and `d2 <= R*R + 1e-12`. `rng_shuffle(rng, order, n)` per epoch is the same call used at line 42 of the stub.

**Run skeleton** (lines 155-176): load, validate, malloc, `ok = ok && step(...)` chain, then `free` and `matrix_free`. Keep this early-exit style; add training between `pick_prototypes` and the writers.

---

### `neuron/io/config.c` (config, validation)

**Analog:** same file, lines 19-23 (replace the comment "Phase 2 appends the rows" and add rows):
```c
static const KeySpec KOHONEN_KEYS[] = {
  { "grid_k", KEY_INT, 1, NULL },
  { NULL, KEY_INT, 0, NULL },
};
```
Add rows `neighborhood` (KEY_STRING), `radius0`, `radius_final`, `eta0`, `eta_final` (KEY_NUMBER), `epochs` (KEY_INT), all `1` (required). `KEY_NUMBER`, `KEY_STRING`, `KEY_INT` are all in `type_description` (lines 59-69). Mode-dependent bounds are checked in `run_kohonen`, not in the table.

---

### `neuron/tests/test_main.c` (test, C unit)

**Analog:** same file.

**Strict config test** (lines 204-217): `check(loads("{...}"))` for valid and `check(!loads("{...}"))` for each missing, mistyped or unknown key. Update the valid Kohonen string at line 206 and the invalid ones at 215 and 217 to carry the new required keys; add negatives for bad `neighborhood`, `eta0 >= 1`, `radius_final < 1` in step mode.

**Same-seed test** (lines 274-311): `same_seed_same_bytes("kohonen", "<config>", "prototypes.csv")` at 306-308; update the config text with new keys (use `grid_k: 3` on the 6-row fixture to cover k*k > n). Add checks for trace endpoints (`check_close(actual, expected, tol)` macro at line 33) and that R=1 updates exactly the 4 neighbours. Run with `make -C neuron debug` (ASan/UBSan).

---

### `analysis/som.py` (utility, transform)

**Analog:** `analysis/pca.py` (module header and numpy-only style).

**Header/imports** (pca.py lines 17-33):
```python
from __future__ import annotations
import csv, json, sys
from pathlib import Path
import numpy as np
import plots_style  # noqa: E402
from creadores import PREPARED_DIR, load_creadores, load_meta  # noqa: E402
```
(pca.py inserts `scripts/` into `sys.path` before the creadores import; copy that exact mechanism.)

**Do not reuse** `pca.spearman` (lines 157-174: `argsort(argsort())`, "no ties expected"). Implement `average_ranks`, `spearman_ties`, `grid_distance_vector`, `stability`, `metrics_from_prototypes`, `umatrix` from RESEARCH Pattern 5 (verified against scipy). Same function shape as `pca.py`: small pure functions with `np.ndarray` annotations.

**CSV reading**: follow `pca.read_prepared` (line 130) and `creadores.load_meta`/`scaler_from_meta`/`inverse_transform` (scripts/creadores.py lines 215-235) for raw-unit profiles.

---

### `analysis/som_loo.py` (driver, batch + subprocess)

**Analog:** `analysis/sweep.py`.

**Constants and paths** (lines 32-36): `ANALYSIS_DIR`, `TP_DIR`, `NEURON_DIR`, `BINARY = NEURON_DIR / "build" / "neuron"`.

**Subprocess call** (lines 217-221): argument list, no shell, `cwd` set, `capture_output=True, text=True`; parse stdout lines starting with `RESULT_PREFIX = "results -> "` (lines 223-226). For LOO use `tempfile.TemporaryDirectory()` as cwd per training (avoids `MAX_DIR_ATTEMPTS 100` collision), read `prototypes.csv`, compute distance of the held-out row in Python, discard the directory.

**Parallelism** (lines 243-261): `ThreadPoolExecutor(max_workers=workers)` plus `as_completed`, catch per-future `Exception` so one failure does not stop the series, progress to stderr.

**Build** (lines 194-198): `subprocess.run(["make", "-s", "-C", str(NEURON_DIR)], check=True)` with `SystemExit` on failure.

**Stage-1 guard (SOM-03)**: before running, `git status --porcelain -- deliverables/02-kohonen.md analysis/series_som_stage1.json` must be empty and the file committed; use `subprocess.run(["git", ...])` list form.

---

### `analysis/som_select.py` (utility + CLI)

**Analog:** `analysis/pca.py::decision` (line 221) and `main` (lines 488-512).

Pattern: a pure `select_grid(summary)` function returning a dict, mirrored on `decision()`; `main(argv)` with `argparse` (`--out-dir`, default under `analysis/results/`), writes `selection.json` with `json.dumps(dec, indent=2, ensure_ascii=False) + "\n"`, returns `0`, and ends with `raise SystemExit(main())`. Reading `summary.csv` uses stdlib `csv.DictReader` (sweep.py writes it with `csv.DictWriter`, lines 298-303). Encode D-11..D-14 verbatim and the checklist from RESEARCH Pattern 6.

---

### `analysis/som_figures.py` (utility, plots)

**Analog:** `analysis/pca.py::plot_biplot` (lines 342-412) and `run_variant` (473-485).

Pattern:
```python
plt = plots_style.apply_style()
colors = plots_style.palette_for(order)
fig, ax = plt.subplots(figsize=(11, 8.5))
ax.axhline(0, color=plots_style.GRID, linewidth=1, zorder=0)
...
plots_style.save_figure(fig, out_path_without_suffix)   # deterministic SVG
```
Use `plots_style.DIVERGING` for component planes. PC1/PC2 for the contrast: `pca_eigh(z, features)`, `scores(result, z)[:, :2]` (pca.py lines 86, 115), or read `analysis/results/pca/audited/scores.csv`. `dominant_topics(meta["creator_id"])` (line 327) is reusable for the descriptive topic share.

---

### `analysis/series_som_stage1.json` / `series_som_stage2.json` (config, batch)

**Analog:** `analysis/series_smoke_kohonen.json` for keys and `sweep.py` `series_variants` (lines 118-136) for `variants`.
```json
{
  "_comment": "...",
  "base_config": "../neuron/config.json.kohonen.example",
  "seeds": [1,2,3,4,5,6,7,8,9,10],
  "variants": [ {"label": "k3_step", "set": {"grid_k": 3, "neighborhood": "step", "radius0": 1.5, "radius_final": 1.0}} ]
}
```
Only keys in `SERIES_KEYS` (`base_config, set, vary, values, variants, seeds, workers`) plus `_`-prefixed comments are allowed (sweep.py lines 85-87). `vary` and `variants` are mutually exclusive (line 122). Labels become run-dir slugs `[A-Za-z0-9.-]`; do not use underscores expecting them to be preserved (line 72: `_` is replaced by `-`). Update `series_smoke_kohonen.json` only if the example config changes incompatibly (it varies `grid_k`, still valid).

---

### `analysis/tests/test_som.py` (test, pytest)

**Analog:** `analysis/tests/test_pca.py` and `conftest.py` (puts `analysis` and `scripts` on `sys.path`).
```python
from __future__ import annotations
import numpy as np
import creadores
from creadores import PREPARED_DIR, RAW_PATH
from pca import pca_eigh, read_prepared, scores
STEM = "creadores_zscore"
def test_...():
    if not (PREPARED_DIR / f"{STEM}.csv").exists():
        creadores.prepare(RAW_PATH, PREPARED_DIR)
    features, z, _meta = read_prepared(STEM)
    assert z.shape == (50, 26)
    assert np.allclose(..., atol=1e-10)
```
Plain `assert` functions, no classes; self-prepare the data if missing. Tests listed in RESEARCH Validation Architecture (`-k recompute`, `stability`, `select`, `guard`, `loo`, `umatrix`, `figures`, `pca_contrast`).

---

### `deliverables/02-kohonen.md` (doc)

**Analog:** `deliverables/01-datos-pca.md`.

Copy the section 5 structure (line 112): title "regla de decisión (fijada antes de mirar ...)", opening sentence "Esta sección fija la regla; los resultados se agregan después y no figuran acá. Las decisiones D-xx ... están escritas en `.planning/phases/.../CONTEXT.md` antes de que existiera ninguna salida", then bold-labelled bullets (**Método.**, **Cantidad ...**, **Control.**, **Rol.**). Section 6 (line 122) opens with the source of figures (`Las cifras salen de analysis/results/.../`) and "con la regla de la sección 5 aplicada sin cambios". Final section "Cómo reproducir" (line 183). The rule section must be committed alone before stage 1 runs.

---

## Shared Patterns

### Strict config, no silent defaults
**Source:** `neuron/io/config.c` lines 12-34 (`KeySpec` tables), `config.h` doc.
**Apply to:** `kohonen.c`, `config.c`, example config, tests, series files. Unknown, missing or mistyped key aborts.

### Deterministic output, no timestamps inside files
**Source:** `neuron/io/results.c` (`results_write_table`, `results_write_metrics`, `%.17g`), `plots_style.save_figure`.
**Apply to:** every new CSV (`occupancy.csv`, `trace.csv`, `selection.json`, figures). Same seed implies `diff -r` clean.

### Error and allocation style in C
**Source:** `kohonen_stub.c` lines 36-40, 80-83, 164-171.
```c
int ok = table != NULL && header != NULL;
if (!ok) fprintf(stderr, "kohonen: couldn't allocate the prototype table\n");
...
ok = ok && step(...);
free(...); return ok;
```
**Apply to:** all new C functions; return 0/1, no `exit`.

### Subprocess invocation
**Source:** `analysis/sweep.py` lines 217-221 (list args, `cwd`, no shell).
**Apply to:** `som_loo.py`, git guard.

### Python module conventions
**Source:** `analysis/pca.py` lines 17-33: `from __future__ import annotations`, numpy and stdlib only (no pandas/scipy, Phase 1 D-06), `main(argv) -> int` with `raise SystemExit(main())`.
**Apply to:** all `som*.py`.

### Pre-registered rule
**Source:** `deliverables/01-datos-pca.md` section 5.
**Apply to:** `deliverables/02-kohonen.md`, `series_som_stage1.json`, `select_grid()` (committed together, before the sweep).

## No Analog Found

| File / function | Role | Data Flow | Reason |
|---|---|---|---|
| SOM training loop (inside `kohonen.c`) | model | batch | Only a stub exists; use RESEARCH Pattern 2 |
| `average_ranks` / `spearman_ties` / `stability` | utility | transform | Existing `pca.spearman` cannot handle ties; use RESEARCH Pattern 5 |
| `umatrix`, hit map, component planes, region rule, PCA contrast statistics | utility / plots | transform | No SOM or map plotting yet; use RESEARCH Pattern 5 and 7 with `plot_biplot` only for style |
| Git-clean guard for the committed rule | utility | request-response | No git-aware code in the repo; use RESEARCH Pattern 6 item 8 |

## Metadata

**Analog search scope:** `neuron/`, `analysis/`, `scripts/`, `deliverables/`, root `Makefile` (all tracked files from `git ls-files`).
**Files scanned:** about 25 read or grepped.
**Pattern extraction date:** 2026-10-21
