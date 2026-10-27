# Phase 4: Hopfield núcleo y letras - Pattern Map

**Mapped:** 2026-10-23
**Files analyzed:** 22 new/modified
**Analogs found:** 21 / 22 (all analogs verified git-tracked; paths relative to `TP4/`)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `neuron/models/hopfield_core.h` / `.c` | model (pure core) | transform | pure helpers of `neuron/models/kohonen.c` (`kohonen_decay`, `nearest`, exported in `models.h`) | role-match |
| `neuron/models/hopfield.c` (git mv from `hopfield_stub.c`) | model (runner) | batch + file-I/O | `neuron/models/kohonen.c` (`read_params`, `write_*`, `run_kohonen`) + the stub itself | exact |
| `neuron/models/models.h` (modify) | config | n/a | itself (Kohonen helper block) | exact |
| `neuron/io/config.c` (modify `HOPFIELD_KEYS`, add `config_has`) | config | request-response | `KOHONEN_KEYS` block, lines 19-32 | exact |
| `neuron/tests/test_main.c` (modify) | test | request-response | `test_kohonen_training`, `same_seed_same_bytes`, `tests[]` | exact |
| `neuron/tests/fixtures/patterns_mix.csv` | test fixture | file-I/O | `neuron/tests/fixtures/patterns_small.csv` | exact |
| `neuron/config.json.hopfield.example` (modify) | config | n/a | itself / `config.json.kohonen.example` | exact |
| `datos/letters/alphabet_5x5.txt` | data | file-I/O | none (new text format) | no analog |
| `scripts/letters.py` | utility | transform | `scripts/creadores.py` (library, no side effects, TP_DIR constants) | role-match |
| `scripts/prepare_letters.py` | utility (CLI) | file-I/O | `scripts/prepare_creadores.py` | exact |
| `analysis/hopfield_select.py` | utility (rule as code + guard) | transform | `analysis/som_select.py` | exact |
| `analysis/hopfield.py` | utility (run reader + numpy recompute) | file-I/O + transform | `analysis/som.py` (`read_run`, `metrics_from_prototypes`, `run_binary`) | exact |
| `analysis/hopfield_letters.py` | service (guarded driver) | batch | `analysis/som_stage.py` (`rule_identity`, `require_same_rule`, `run_stage`) | exact |
| `analysis/hopfield_figures.py` | utility (figures) | file-I/O | `analysis/som_figures.py` | exact |
| `analysis/series_hopfield_*.json`, `series_smoke_hopfield.json` (modify) | config | batch | `analysis/series_smoke_hopfield.json`, `series_som_stage1.json` | exact |
| `analysis/tests/test_letters.py` | test | transform | `analysis/tests/test_creadores.py` | role-match |
| `analysis/tests/test_hopfield_select.py` | test | transform | `analysis/tests/test_som_select.py` | exact |
| `analysis/tests/test_hopfield.py` | test | request-response | `analysis/tests/test_som.py` | exact |
| `analysis/tests/test_hopfield_figures.py` | test | file-I/O | `analysis/tests/test_som_figures.py` | exact |
| `deliverables/04-hopfield-letras.md` | doc | n/a | `deliverables/02-kohonen.md` (rule between markers, sec. 2) | exact |
| `Makefile` (append targets) | config | n/a | `som-stage1`/`som-figures` targets | exact |
| `neuron/README.md`, `analysis/README.md` (modify) | doc | n/a | existing sections | exact |

## Pattern Assignments

### `neuron/models/hopfield.c` (runner; model, batch + file-I/O)

**Analog:** `neuron/models/kohonen.c` (structure) and `neuron/models/hopfield_stub.c` (pieces to keep).

**Header comment + includes + limits** (kohonen.c lines 1-20):
```c
// Kohonen self-organising map: ... (what it does, what it writes)
#include "../io/matrix.h"
#include "models.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define GRID_K_MAX 32
#define EPOCHS_MAX 100000
#define METRICS_COUNT 19
```

**Params struct + `read_params`** (kohonen.c 22-90): a typed struct, one `config_get_*` chain with `||`, then one range check per key printing `"%s: <key> must ..."` with `config->path` and `return 0`:
```c
if (!config_get_int(config, "grid_k", &params->grid_k)
    || !config_get_string(config, "neighborhood", &neighborhood) ... ) { return 0; }
if (params->epochs < 1 || params->epochs > EPOCHS_MAX) {
  fprintf(stderr, "%s: epochs must be between 1 and %d\n", config->path, EPOCHS_MAX);
  return 0;
}
if (strcmp(neighborhood, "step") == 0) { ... } else {
  fprintf(stderr, "%s: neighborhood must be \"step\" or \"gaussian\"\n", config->path); return 0; }
```
Apply to `task` ("recall"|"capacity"), `rule` ("hebb"), `update` ("async"|"sync"), `max_sweeps`, `trials`, `subset`, `trace_trials`, `p`, `n_subsets`. Task-specific keys use `config_has` (new helper) and reject keys of the other task.

**Keep from the stub** (hopfield_stub.c 15-51): `is_pm_one`, `read_noise_levels` (levels in [0,1], `CONFIG_ARRAY_MAX`), `corrupt` (flip first k of a shuffled order via `rng_shuffle`), `overlap`; `k = (int) lround(levels[l] * n)` (stub line 70).

**Write pattern** (stub 54-91 and kohonen.c 303-330): malloc the whole `double` table, `ok = table != NULL && ...`, print `"hopfield: couldn't allocate ..."`, header as `const char * header[]`, then `results_write_table(results, "trials.csv", width, header, n_rows, table)`; free in all paths. Dynamic headers (m_0..m_{P-1}) use `malloc`'d `const char **` (kohonen `write_prototypes`, 303-327); header strings must outlive the call.

**Metrics** (kohonen.c 363-383, stub 109-117): fixed-size `const Metric metrics[METRICS_COUNT] = { { "model", "hopfield", 0 }, { "seed", NULL, config->seed }, ... }; results_write_metrics(results, metrics, METRICS_COUNT)`. Strings go as `{key, "str", 0}`, numbers as `{key, NULL, value}`. Add `task`, `update`, `rule` as string metrics.

**Run function skeleton** (kohonen.c 421-448): load matrix, `read_params`, allocate, chain steps with `ok = ok && step(...)`, free, `matrix_free(&input)`, return `ok`:
```c
int run_hopfield(const Config * config, Rng * rng, const Results * results) {
  Matrix patterns;
  if (!matrix_load(config->input, &patterns)) return 0;
  int ok = is_pm_one(&patterns);
  if (!ok) fprintf(stderr, "%s: patterns must contain only -1 and 1\n", config->input);
  ...
  matrix_free(&patterns);
  return ok;
}
```
The async sweep, classifier and sync step come from RESEARCH.md "Pattern 1" and "Classifier" code (design, not copied code) and live in `hopfield_core.c`.

---

### `neuron/models/hopfield_core.h|.c` (pure core; transform)

**Analog:** pure helpers of `kohonen.c` exported through `models.h` (lines 301-310 of models.h: "Kohonen helpers, exported for tests/test_main.c") and `static double distance/nearest` style (kohonen.c 115-134: small static function, one-line comment on tie rule: "the lowest index wins a tie").

Copy: no I/O, no `fprintf` except via runner; signature style with `const double w[]`, `int n`, out-parameters (`double * best`); comment states tie behaviour. Export prototypes in a header (new `hopfield_core.h`, or a block in `models.h` like Kohonen's) so `tests/test_main.c` calls them with tiny arrays. Keep W as `double` with integer values (RESEARCH). Use RESEARCH "Pattern 1" `async_sweep` and "Classifier" excerpts verbatim as the design.

---

### `neuron/io/config.c` (modify; config)

**Analog:** `KOHONEN_KEYS` (config.c 19-32) and current `HOPFIELD_KEYS` (39-43).

```c
// grid_k: ... (one comment line per key meaning; ranges are checked in models/kohonen.c)
static const KeySpec KOHONEN_KEYS[] = {
  { "grid_k", KEY_INT, 1, NULL },
  { "neighborhood", KEY_STRING, 1, NULL },
  ...
  { NULL, KEY_INT, 0, NULL },
};
```
Replace `HOPFIELD_KEYS` with: `task`/`rule`/`update` KEY_STRING required, `max_sweeps`/`trials` KEY_INT required, `noise_levels` KEY_NUMBER_ARRAY required (existing), `subset` KEY_NUMBER_ARRAY / `trace_trials`/`p`/`n_subsets` KEY_INT with required `0`. Keep terminator row `{ NULL, KEY_INT, 0, NULL }`. Update the comment "Phases 4 and 5 append the rows". Add `config_has` declared in `config.h` (config.h:17-18 has `CONFIG_ARRAY_MAX 64`, `CONFIG_KEYS_MAX 32`).

---

### `neuron/tests/test_main.c` (modify; test)

**Analog:** itself.

**Registration** (lines 514-524): add entries to `tests[]`:
```c
{ "kohonen training", test_kohonen_training },
```
-> `{ "hopfield core", test_hopfield_core }, { "hopfield run", test_hopfield_run }, { "hopfield capacity", test_hopfield_capacity }`.

**Must change in same plan (breaks otherwise):**
- Strict validation (lines 209-210 `loads("{\"model\": \"hopfield\" ... \"noise_levels\": [0.0, 0.5]}")` valid case; lines 221-222 invalid cases): rewrite with the new required keys.
- `same_seed_same_bytes("hopfield", ..., NULL)` at 316-319, with the comment at 314-315: pass `"trials.csv"` as `seed_file`; update JSON to the new keys.
- Helpers: `check`, `check_close_at`, `write_tmp`, `load_quiet`, `PATTERNS_FIXTURE`, `same_seed_same_bytes(name, config_text, seed_file)` (line 276). Tests that need tolerances use `check_close_at(actual, expected, tol, ...)`.

New tests to write (from RESEARCH): course example (xi1=(1,1,-1,-1), xi2=-xi1, W entries, one sync step), integrality/symmetry/zero diagonal, tie keeps state, incremental vs from-scratch energy, async energy non-increasing (1e-9), N=2 sync two-cycle vs async convergence, classifier precedence (stored > inverse > mixture > other).

---

### `scripts/prepare_letters.py` (CLI; file-I/O)

**Analog:** `scripts/prepare_creadores.py` (whole file, 60 lines).

```python
from __future__ import annotations
import argparse
from pathlib import Path
import creadores

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=creadores.RAW_PATH)
    parser.add_argument("--out-dir", type=Path, default=creadores.PREPARED_DIR)
    args = parser.parse_args()
    audit, paths = creadores.prepare(args.source, args.out_dir)
    for path in paths:
        print(f"wrote {display(path)}")
if __name__ == "__main__":
    main()
```
Copy: docstring listing outputs ("generated, not versioned"), `display()` helper relative to `TP_DIR`, thin `main()` that delegates to a library module (`letters.py`), `.meta.json` next to the CSV, no timestamps / absolute paths (creadores.py docstring: "rerun reproduces them byte for byte").

### `scripts/letters.py` (library; transform)

**Analog:** `scripts/creadores.py` lines 1-40: module docstring stating "Library only, no side effects on import", `TP_DIR = Path(__file__).resolve().parent.parent`, `PREPARED_DIR = TP_DIR / "datos" / "prepared"`, constants in module scope, no pandas, `csv` + numpy. Validation raises `ValueError` with a message naming the letter and line (D-02).

---

### `analysis/hopfield_select.py` (rule as code + guard)

**Analog:** `analysis/som_select.py`.

**Header/constants** (lines 1-37):
```python
TP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TP_DIR / "scripts"))
sys.path.insert(0, str(TP_DIR / "analysis"))
RULE_FILE = "deliverables/02-kohonen.md"
SELECT_FILE = "analysis/som_select.py"
RULE_START = "<!-- regla:inicio -->"
RULE_END = "<!-- regla:fin -->"
```
Use `RULE_FILE = "deliverables/04-hopfield-letras.md"`, `SELECT_FILE = "analysis/hopfield_select.py"`, plus `ALPHABET_FILE`. The docstring explains "executable twin" of the Spanish rule text; copy this framing.

**Reuse, do not copy:** `som_select.rule_digest(path)` (214-223, hashes text between markers) and `som_select.rule_guard(paths, repo_dir)` (230-247: `git ls-files --error-unmatch`, `git status --porcelain`, `git log -1`, all as argument lists with no shell). Import them: `import som_select`. Message mentions "D-10" (cosmetic; wrap or accept). Alphabet is NOT covered by `rule_digest`: record `alphabet_sha256 = hashlib.sha256(Path(...).read_bytes()).hexdigest()` separately (same as `select_sha256` in `som_stage.rule_identity`).

**Selection function style:** pure function over plain data, returns dict with `outcome`/`reason` fields (`select_grid`, 143-206), tie-breaks as sort keys `(value, k)`: use `(mx, total, combo)` and `(-mx, -total, combo)` on `int64` dot products per RESEARCH "Selection rule in integers".

---

### `analysis/hopfield_letters.py` (guarded driver; batch)

**Analog:** `analysis/som_stage.py`.

**Imports/bootstrap** (lines 22-40): `TP_DIR`, `sys.path.insert(...)`, `import som  # noqa: E402`, `import som_select  # noqa: E402`.

**Git helpers to copy (private upstream, so copy the 6 lines)** (55-67):
```python
def _git_stdout(args, repo_dir):
    return subprocess.run(["git", *args], cwd=repo_dir, capture_output=True, text=True, check=True).stdout.strip()

def _added_commit(path, repo_dir):
    out = _git_stdout(["log", "--diff-filter=A", "--format=%H", "--", path], repo_dir)
    if not HEX40.fullmatch(out):
        raise SystemExit(f"{path}: expected exactly one commit that added it, git reports {out!r} (D-10)")
    return out
```

**Identity** (`rule_identity`, 70-98): guard list via `dict.fromkeys([...])`, `rule_guard(guarded, repo_dir)`, rule/select/series must share the added commit. Change for Phase 4 (RESEARCH "Guard design"): the alphabet commit must be an ancestor of the rule commit (`git merge-base --is-ancestor`), and rule text + select code + series share one commit.

**Same-rule check** (`require_same_rule`, 101-115): read recorded `selection.json`, compare `rule_sha256`, `select_sha256` (add `alphabet_sha256`), `raise SystemExit(f"rule changed since ...")`.

**Run/outputs:** `run_stage` (147) writes under `analysis/results/<model>/<series name>/` with `_write_csv`, `_write_json`, `_relative`. Python `sweep.py` handles multi-seed.

---

### `analysis/hopfield.py` (run reader + numpy recompute)

**Analog:** `analysis/som.py`: `_read_table` (53), `read_run` (70), `metrics_from_prototypes` (130), `run_binary` (167-181).

```python
def run_binary(config: dict, cwd: Path) -> Path:
    (cwd / "config.json").write_text(json.dumps(config, indent=2) + "\n")
    process = subprocess.run([str(BINARY), "config.json"], cwd=cwd, capture_output=True, text=True)
    if process.returncode != 0:
        reason = process.stderr.strip().splitlines()[-1:] or [f"exit code {process.returncode}"]
        raise RuntimeError(reason[0])
    printed = [line for line in process.stdout.splitlines() if line.startswith(RESULT_PREFIX)]
    ...
    return cwd / printed[-1][len(RESULT_PREFIX):].strip()
```
Import and reuse `som.run_binary`, `som.BINARY`, `som.RESULT_PREFIX` rather than copying. Independent recompute functions (`hebb`, `energy`, `is_fixed`) from RESEARCH "Independent numpy recomputation".

---

### `analysis/hopfield_figures.py`

**Analog:** `analysis/som_figures.py`. Header docstring (guard, refuse when rule sha256 differs from recorded in `selection.json`), `TP_DIR`/`sys.path` bootstrap, `import plots_style`, `DEFAULT_OUT = TP_DIR/"analysis"/"results"/...`, all figures written via `plots_style.save_figure(fig, path_without_suffix)` (plots_style.py:88: writes `.svg` + `.png`, SVG metadata `Date None` so reruns are byte-identical). numpy + matplotlib only.

---

### Tests (`analysis/tests/test_hopfield*.py`, `test_letters.py`)

**Analog:** `analysis/tests/test_som_select.py` (synthetic rows via `make_row(...)` factory, one test per rule branch, `import som_select`, `TP_DIR = Path(__file__).resolve().parent.parent.parent`), `test_som.py` (runs binary in `tmp_path`, `input` as `os.path.relpath` because `sweep.py` rewrites `PATH_KEYS = ("input",)`), `conftest.py` (adds `analysis` and `scripts` to `sys.path`; no change needed). `test_letters.py`: hard-code the J matrix from RESEARCH and compare to converter row; one failing fixture per D-02 rule in `tmp_path`. `test_hopfield_select.py`: synthetic alphabet with exact ties; assert mirrored tie-break; guard tests copy the temp-git-repo approach already in `test_som_select.py` (uses `subprocess` + `hashlib`).

---

### `deliverables/04-hopfield-letras.md`

**Analog:** `deliverables/02-kohonen.md`: numbered Spanish sections (`## 1. Algoritmo y salidas`, `## 2. Regla de elección ... (fijada antes de mirar resultados)`), rule text strictly between `<!-- regla:inicio -->` and `<!-- regla:fin -->` (exactly one of each), results sections added after the rule commit, final "Cómo reproducir" section.

---

### `Makefile` (append)

**Analog:** targets `som-stage1`, `som-figures` (Makefile 46-66): Spanish comment line above each target, `prepare`-dependent, call through `$(PY)`:
```make
som-stage1: prepare
	$(PY) analysis/som_stage.py run analysis/series_som_stage1.json --select
```
Add `letters` (runs `scripts/prepare_letters.py`), `hopfield-letters` (guarded driver), `hopfield-figures`; append to `.PHONY` line 10 (merge hot spot with Phase 3: append only, do not alter `prepare:`).

---

## Shared Patterns

### Strict config
**Source:** `neuron/io/config.c` lines 12-17, 40-43, 51-55 (tables + `MODEL_KEYS`).
**Apply to:** all new config keys; unknown, missing or mistyped keys abort before any work. Ranges are checked in the runner (`read_params`), types in the table.

### Error handling in C
**Source:** `neuron/models/kohonen.c` 35-90, 95-112.
**Apply to:** all C files. Functions return `int` 1/0; on failure `fprintf(stderr, "<model>: ...\n")` or `"%s: <key> must ...\n", config->path`; allocation failure message `"<model>: couldn't allocate the ..."`; always free then return `ok`.

### Deterministic outputs
**Source:** `results_write_table` (`%.17g`, no timestamps), `results_write_metrics` (flat), `rng_shuffle` of `neuron/rng.c`. Strings cannot go in tables (class names as numeric codes: 0 stored, 1 inverse, 2 mixture, 3 other).
**Apply to:** every CSV; same seed gives identical bytes (`same_seed_same_bytes`).

### Pre-registration guard
**Source:** `analysis/som_select.py` 214-247 (`rule_digest`, `rule_guard`) plus `analysis/som_stage.py` 70-115.
**Apply to:** `hopfield_select.py`, `hopfield_letters.py`, `hopfield_figures.py`.

### Python script bootstrap
**Source:** `analysis/som_select.py` 23-25 / `som_stage.py` 29-31:
```python
TP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TP_DIR / "scripts"))
sys.path.insert(0, str(TP_DIR / "analysis"))
```
**Apply to:** every new `analysis/*.py` CLI/driver. Python: `from __future__ import annotations`, numpy and standard library only (no pandas).

### Sweeps
**Source:** `analysis/series_smoke_hopfield.json` (keys `_comment`, `base_config`, `variants: [{label, set}]`, `seeds`); `series_som_stage1.json`.
**Apply to:** new `series_hopfield_*.json`; update the smoke series with the new required keys, since `base_config` is `neuron/config.json.hopfield.example`.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `datos/letters/alphabet_5x5.txt` | data | file-I/O | No hand-drawn versioned text data exists; use RESEARCH draft alphabet (needs user approval at checkpoint) |
| Async/sync Hopfield dynamics, classifier, cycle detection (inside `hopfield_core.c`) | model | transform | No existing recurrent/energy model; use RESEARCH Pattern 1 and Classifier excerpts |
| `capacity` task enumeration of C(M,p) subsets | model | batch | No combinatorial enumeration in repo; use RESEARCH schema (lexicographic order matching `itertools.combinations`) |

## Merge-risk notes (Phase 3 on `dev-tp4`)
Shared hot spots: `neuron/io/config.c` (`OJA_KEYS` vs `HOPFIELD_KEYS`), `neuron/models/models.h`, `neuron/tests/test_main.c` (`tests[]`), root `Makefile` (`.PHONY`), both READMEs. Keep edits localized and append-only; put all new Python in new files. Other places the HOPFIELD_KEYS change breaks: `neuron/README.md` (lines 27, 73, 88, 94), `analysis/README.md:80`, stale stub comment in `models.h`.

## Metadata

**Analog search scope:** `neuron/`, `analysis/`, `scripts/`, `deliverables/`, root `Makefile` (all `git ls-files` tracked; no mirror paths).
**Files scanned:** ~45 listed, 12 read in full or in targeted ranges.
**Pattern extraction date:** 2026-10-23
