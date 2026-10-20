# Phase 1: Fundación, auditoría de datos y PCA - Pattern Map

**Mapped:** 2026-10-20
**Analogs found:** 9 / 15 (all analogs live in sibling `../TP3`, git-tracked; verified with `git ls-files`)
**Note:** TP4 has no code. Paths below `TP3/` are relative to `/Users/gonzalocuri/Documents/dev/repos/SIA/SIA-TPs/TP3`. TP3 has NO `analysis/run_report.py`; run_report/report_server live in `TP3/scripts/` and are NOT needed in Phase 1 (do not copy).

## File Classification

| New file (TP4) | Role | Data Flow | Analog | Match |
|---|---|---|---|---|
| `neuron/Makefile` | config | build | `TP3/neuron/Makefile` | exact (adapt) |
| `neuron/rng.c`, `neuron/rng.h` | utility | transform | `TP3/neuron/rng.c/.h` | copy as-is |
| `neuron/io/results.c/.h` | utility | file-I/O | `TP3/neuron/io/results.c` | role-match (rewrite writers) |
| `neuron/io/config.c/.h` | config | file-I/O | `TP3/neuron/io/config.c` | partial (cJSON rewrite, keep strictness) |
| `neuron/vendor/cjson/cJSON.c/.h` | vendored lib | n/a | none | no analog |
| `neuron/main.c` (dispatch by `model`) | controller | request-response | `TP3/neuron/main.c` | role-match |
| `neuron/models/{kohonen,oja,hopfield}_stub.c` | service | batch | none (TP3 `network.c` only for shape) | no analog |
| `neuron/io/dataset.c` (CSV z-scored loader) | utility | file-I/O | `TP3/neuron/io/dataset.c` | role-match |
| `neuron/tests/test_main.c` | test | n/a | `TP3/neuron/tests/test_main.c` | exact (runner) |
| `analysis/sweep.py` | service | batch | `TP3/analysis/sweep.py` | exact (adapt) |
| `analysis/requirements.txt` | config | n/a | `TP3/analysis/requirements.txt` | adapt |
| `analysis/plots_style.py` | utility | n/a | `TP3/analysis/plots_style.py` | adapt (matplotlib, not plotly) |
| `scripts/prepare_creadores.py`, `analysis/eda.py`, `analysis/pca.py` | script | transform | none | no analog |
| `analysis/tests/test_*.py` (pytest) | test | n/a | none | no analog |
| `neuron/.gitignore` | config | n/a | `TP3/neuron/.gitignore` | exact |

## Pattern Assignments

### `neuron/Makefile`
**Analog:** `TP3/neuron/Makefile` (lines 1-50). Copy the structure; changes marked.
```make
CC      := gcc
CFLAGS  := -std=c11 -Wall -Wextra -O3 -march=native -fassociative-math ... -MMD -MP   # TP3 line 4
LDLIBS  := -lm
BUILD_DIR := build
TARGET    := $(BUILD_DIR)/neuron
SOURCES := $(wildcard *.c io/*.c activation/*.c optimizer/*.c)
OBJECTS := $(SOURCES:%.c=$(BUILD_DIR)/%.o)
TEST_TARGET  := $(BUILD_DIR)/tests/test_main
TEST_OBJECTS := $(filter-out $(BUILD_DIR)/main.o,$(OBJECTS)) $(BUILD_DIR)/tests/test_main.o
DEPS    := $(OBJECTS:.o=.d) $(BUILD_DIR)/tests/test_main.d
CONFIG ?= config.json
$(BUILD_DIR)/%.o: %.c
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) -c $< -o $@
test: $(TEST_TARGET)
	./$(TEST_TARGET)
-include $(DEPS)
```
TP4 differences:
- `CFLAGS := -std=c11 -Wall -Wextra -O2 -MMD -MP` (drop `-O3 -march=native -fassociative-math -fno-signed-zeros -fno-trapping-math`).
- `SOURCES := $(wildcard *.c io/*.c models/*.c vendor/cjson/*.c)`, then a per-file override for cJSON without `-Wextra -Wpedantic` (make 3.81 supports target-specific vars with pattern rules): `$(BUILD_DIR)/vendor/cjson/%.o: CFLAGS := -std=c11 -O2 -MMD -MP`.
- `PY ?= .venv/bin/python` (venv at TP4 root, so `../.venv/bin/python` relative to `neuron/`; prefer `PY ?= $(abspath ../.venv/bin/python)`). `test` target must also run pytest: `$(PY) -m pytest ../analysis/tests -q` after `./$(TEST_TARGET)`.
- Add `debug` target with `-fsanitize=address,undefined -g`.
- Drop `serve`/`REPORT` targets. Only 3.81 syntax: no `&:`, `.ONESHELL`, `$(file)`.
- Must run as `./build/neuron config.json` and print `results -> <run dir>` (TP3 convention, `run` target parses it).

### `neuron/rng.c`, `neuron/rng.h`
**Analog:** `TP3/neuron/rng.c` (1-25), `rng.h` (1-18). Copy byte for byte. API: `Rng rng_new(unsigned int seed)`, `double rng_uniform(Rng *)`, `void rng_shuffle(Rng *, int[], int)`. Core:
```c
rng->state += 0x9E3779B97F4A7C15ULL;
unsigned long long z = rng->state;
z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
z ^= z >> 31;
return (z >> 11) * (1.0 / 9007199254740992.0);
```
One `Rng` created in main and passed down.

### `neuron/io/results.c/.h`
**Analog:** `TP3/neuron/io/results.c` (lines 1-107 relevant). Keep: `#define _POSIX_C_SOURCE 200809L` first line, `make_dir`, `make_run_dir` (numeric suffix on collision), `open_in_run_dir`, `copy_file` (config.json copy), 17-digit printing `"%.17g"` for doubles.
```c
#define _POSIX_C_SOURCE 200809L // mkdir, localtime_r
...
static FILE * open_in_run_dir(const Results * results, const char * name) {
  char path[RESULTS_PATH_MAX + 64];
  snprintf(path, sizeof(path), "%s/%s", results->dir, name);
  FILE * file = fopen(path, "w");
  if (file == NULL) perror(path);
  return file;
}
```
TP4 differences (D-04): dir name `results/<timestamp>_<model>_seed<N>` (TP3 uses `%s/%s_%s` with timestamp + activation, lines 76-83); `results_create(config_path, model, seed, &results)`. The timestamp must appear ONLY in the directory name; never inside metrics.json/CSV, and `config.json` copy must be byte-identical with no absolute paths, so `diff -r` between same-seed runs passes (compare contents ignoring dir name). Replace `results_write_weights` with `results_write_metrics_json` (flat) and per-model typed CSV writers. Do not copy the weights read-back (lines 110+).

### `neuron/io/config.c/.h`
**Analog:** `TP3/neuron/io/config.c` (450 lines, hand-rolled flat parser). Reuse only the error-reporting style: every failure prints `"%s: ..."` with the config path to stderr and returns 0 (e.g. line 355: `fprintf(stderr, "%s: unknown key \"%s\"\n", parser->path, key);`, line 273 `unknown optimizer "%s" (available: ...)`). Do NOT copy the tokenizer. New: read file, `cJSON_Parse`, then a small strict layer (D-02): iterate `cJSON_ArrayForEach` over top-level object and reject keys not in the allowed list for the given `model`; require each expected key with `cJSON_IsNumber/IsString/IsArray` and abort with `path: missing key "x"` / `key "x" must be a number`. First required key: `model` in {kohonen, oja, hopfield}; plus `seed`, `input` path (relative to config or neuron/; keep paths relative so nothing absolute is written to outputs), `output`-related keys as needed. Use `cJSON_GetObjectItemCaseSensitive`. Always `cJSON_Delete` on every exit path.

### `neuron/main.c`
**Analog:** `TP3/neuron/main.c` (not read; follow its flow: load config, create `Rng`, `results_create`, run, print `results -> <dir>`). Dispatch: table `{ "kohonen", run_kohonen_stub }, { "oja", ... }, { "hopfield", ... }`; unknown model => error listing available models (same style as `unknown_optimizer`).

### `neuron/models/*_stub.c` (D-03)
No analog. Each stub: read real input (z-scored CSV for kohonen/oja; pattern CSV for hopfield — for Phase 1 a tiny fixture is fine), draw from `Rng` using the seed (e.g. random weight vector via `rng_uniform`, `rng_shuffle` of row order), write flat `metrics.json` (e.g. `{"model":"oja","seed":N,"n_rows":50,"n_cols":26,"checksum":...}` printed with `%.17g`) and one typical CSV. Deterministic given seed. Phases 2-5 replace bodies, so keep the signature `int run_<model>(const Config *, Rng *, const Results *)`.

### `neuron/io/dataset.c`
**Analog:** `TP3/neuron/io/dataset.c` (CSV load to double arrays; read it before writing). Adapt to: header line, 50 rows x n_cols doubles of `datos/prepared/creadores_zscore.csv`; fail clearly on wrong shape.

### `neuron/tests/test_main.c`
**Analog:** `TP3/neuron/tests/test_main.c` lines 1-39 (runner) and 940-983 (table). Copy the `check`/`check_close` macros and the `tests[]` table verbatim:
```c
static int checks = 0; static int failures = 0;
#define check(condition) check_at((condition), #condition, __FILE__, __LINE__)
...
int failures_before = failures;
tests[i].run();
printf("%s %s\n", failures == failures_before ? "ok  " : "FAIL", tests[i].name);
...
printf("%d checks, %d failed\n", checks, failures);
return failures == 0 ? 0 : 1;
```
TP4 C tests (D-07): config rejects unknown key / missing key / wrong type; same seed twice => identical metrics.json and CSV bytes (write to a temp dir, compare via fopen/fread; remove temp files at end like `remove(TMP_FILE)`); dispatch resolves each of 3 models and rejects an unknown one; RNG reproducibility. Includes use relative `"../io/config.h"` style.

### `analysis/sweep.py`
**Analog:** `TP3/analysis/sweep.py` (302 lines; read lines 1-150 here). Copy: module docstring style, `Variant`/`Series`/`Task` frozen dataclasses, `load_series` (`base_config`, `vary`/`values` or `variants`, `seeds`, `workers`), `series_variants`, `plan`, `build_binary` (`make -s -C neuron`), `run_task` (writes `configs/<name>.json`, runs `BINARY` with `cwd=sweep_dir` so `results/` is created there), `ThreadPoolExecutor` + `as_completed`. Key excerpt:
```python
ANALYSIS_DIR = Path(__file__).resolve().parent
TP_DIR = ANALYSIS_DIR.parent
NEURON_DIR = TP_DIR / "neuron"
BINARY = NEURON_DIR / "build" / "neuron"
...
process = subprocess.run([str(BINARY), str(config_path)], cwd=sweep_dir, capture_output=True, text=True)
if process.returncode != 0:
    reason = process.stderr.strip().splitlines()[-1:] or [f"exit code {process.returncode}"]
    return RunSummary(..., f"error: {reason[0]}")
```
TP4 differences: remove imports of `run_error`/`run_report` (they do not exist in TP4) and the TP3 metric fields in `RunSummary` (epochs/validation_mse/accuracy); summarise from flat `metrics.json` generically. `PATH_KEYS` must list TP4 input keys (e.g. `input`) since runs execute from the sweep dir, so paths are made absolute in the sweep's per-run config only. Stdlib only; skip HTML report in Phase 1 (`--dry-run` + summary.csv suffice). Series files `analysis/series_*.json` are versioned; `analysis/results/` is not.

### `analysis/requirements.txt`
**Analog:** `TP3/analysis/requirements.txt` (`plotly>=5.18` with a comment). TP4: pinned (D-06), no pandas:
```
numpy==2.5.4
matplotlib==3.11.2
Pillow==13.0.0
pytest==9.1.1
# plotly==7.1.0   # only if an interactive chart is needed
```
Create with `uv venv .venv && uv pip install -r analysis/requirements.txt`.

### `analysis/plots_style.py`
**Analog:** `TP3/analysis/plots_style.py` lines 19-50: `_SERIES` 8-colour hex palette, `SURFACE/TEXT_PRIMARY/TEXT_SECONDARY/GRID`, `FONT_FAMILY`, `palette_for()` raising `PaletteError` past 8 slots. Copy constants and `palette_for`; drop plotly import and plotly-specific layout helpers; add a matplotlib `apply_style()` (rcParams: facecolor SURFACE, grid GRID, `svg.fonttype="path"`).

### Python data/EDA/PCA scripts (no analog)
Use RESEARCH-free guidance from CONTEXT: `csv` stdlib loader asserting 50 rows x 33 cols (`creator_id`, `name` + 31 vars); z-score with `ddof` choice documented and saved in `datos/prepared/creadores_zscore.meta.json` (mean, std, column order, dropped columns); PCA via `np.linalg.eigh(corr)` sorted descending, check `eigvals.sum() == n_vars`; 80% cumulative variance sets k, Kaiser as control; with all 31 columns expect 5 eigenvalues ~0. Round-trip with `%.17g`-equivalent (`repr`) when writing CSV so C reads exact doubles. Dropped variables per D-09: `price_ars`, `organic_posts_pct`, `total_engagement_per_1000`, and the lowest-variance (original scale) of `topic_*` and of `content_*`; keep them in the raw CSV.

## Shared Patterns

- **Strict failure messages:** `fprintf(stderr, "%s: <problem>\n", path)` + return 0 (TP3 config.c 273, 355); main exits nonzero; sweep.py reads last stderr line as the reason.
- **Reproducibility:** one `Rng` from `seed`, doubles printed `%.17g`, no timestamps/abs paths inside files (D-04).
- **Run directory:** `results/<timestamp>_<model>_seed<N>/` with `config.json` copy; binary prints `results -> <dir>`.
- **Ignore files:** `TP3/neuron/.gitignore` = `build/`, `data/`, `config.json`, `results/`; TP4 same (plus `datos/prepared/` only if decided not to version; `.venv/` already ignored). Version `config.json.*.example`, `series_*.json`.
- **Tracked-source gate:** all analogs above are in tracked TP3 paths (`neuron/`, `analysis/`); none from gitignored mirrors.

## No Analog Found

`neuron/vendor/cjson/*` (download v1.7.19 once), model stubs, `scripts/prepare_creadores.py`, `analysis/eda.py`, `analysis/pca.py`, pytest tests. Use CONTEXT.md decisions D-06..D-12.

## Metadata

**Analog search scope:** `TP3/neuron`, `TP3/analysis` (via `git ls-files`)
**Files read:** Makefile, rng.c/h, results.c (1-120), sweep.py (1-150), test_main.c (1-70, tail), plots_style.py (1-60), requirements.txt, .gitignore
**Not read (read before implementing):** `TP3/neuron/main.c`, `io/dataset.c`, `io/results.h`, `sweep.py` 150-302
