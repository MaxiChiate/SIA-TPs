# Phase 3: Oja y decisiones de campaña - Pattern Map

**Mapped:** 2026-10-21
**Files analyzed:** 14 (paths relative to TP4/; all analogs verified git-tracked)
**Analogs found:** 13 / 14

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `neuron/models/oja_stub.c` (rename to `oja.c`, real rule) | model | batch / online training | `neuron/models/kohonen.c` (train, trace, read_params) + the stub's own writers | exact |
| `neuron/io/config.c` (`OJA_KEYS` rows) | config | request-response | `KOHONEN_KEYS` in same file | exact |
| `neuron/config.json.oja.example` | config | - | `neuron/config.json.kohonen.example` | exact |
| `neuron/Makefile` (source rename) | config | - | existing rule for `kohonen.c` | exact |
| `neuron/tests/test_main.c` (oja cases) | test | - | existing oja/kohonen cases (lines 205-216, 306) | exact |
| `analysis/oja.py` (Oja vs PC1, evidence table, seed dispersion, convergence figure) | utility | transform | `analysis/pca.py` (`read_prepared`, `orient`, `spearman`) + `analysis/som_figures.py` | role-match |
| `analysis/campaigns_select.py` (rule as code, `rule_digest`/`rule_guard` reuse) | utility | transform | `analysis/som_select.py` | exact |
| `analysis/campaigns.py` (shortlists, baselines, metrics) | service | batch/transform | `analysis/som_profiles.py` (reads SOM + raw + PCA, writes tables) | role-match |
| `analysis/maintenance_demo.py` (synthetic creator, BMU, index, drift) | utility | request-response | `scripts/map_creator.py` + `scripts/creadores.py::transform_new_creator` | role-match |
| `analysis/series_smoke_oja.json` (+ maybe `series_oja.json`) | config | batch | `analysis/series_smoke_oja.json`, `series_som_stage2.json` | exact |
| `analysis/tests/test_oja.py`, `test_campaigns_select.py`, `test_campaigns.py` | test | - | `analysis/tests/test_som_select.py`, `test_pca.py` | exact |
| `deliverables/03-oja-campanas.md` | doc | - | `deliverables/02-kohonen.md` (§2 rule between markers, §7 reproduce) | exact |
| `Makefile` (`oja`, `campaigns` targets) | config | - | `som-profiles` / `som-figures` targets | exact |
| Convergence figure across 10 seeds | - | - | no direct analog beyond `som_figures.py` trace plot | partial |

## Pattern Assignments

### `neuron/models/oja_stub.c` -> real Oja (model, online batch)

**Analog:** `neuron/models/kohonen.c` plus the stub's own helpers (keep `norm`, `random_unit_vector`, `project`, `mean_and_std`; lines 13-51 of the stub).

**Param reading and validation** (kohonen.c 37-47, 80-87): read every key with `config_get_*` first, then range-check, printing `"%s: <key> must ..."` with `config->path`:
```c
if (!config_get_number(config, "eta0", &params->eta0)
    || !config_get_number(config, "eta_final", &params->eta_final)
    || !config_get_int(config, "epochs", &params->epochs)) { return 0; }
if (!(params->eta0 > 0 && params->eta0 < 1)) {
  fprintf(stderr, "%s: eta0 must be > 0 and < 1\n", config->path); return 0; }
if (!(params->eta_final > 0 && params->eta_final <= params->eta0)) { ... }
```
Also validate `epochs` in [1, EPOCHS_MAX]. Optionally warn/reject if `eta0 * max|x|^2` is not << 1 (Pitfall 8).

**Decay** (kohonen.c 161-164; `kohonen_decay` is non-static, declared in `models.h`/kohonen.c, reusable):
```c
double kohonen_decay(double start, double end, double fraction) { return start * pow(end / start, fraction); }
```
Use `fraction = step / (steps - 1)` as in line 278 (guard `steps > 1`).

**Epoch loop with shuffled order and trace** (kohonen.c 255-299): `order[]` malloc'd, `rng_shuffle(rng, order, n)` once per epoch, per-step eta from fraction, trace buffer of `epochs+1` rows written through `results_write_table`. For Oja the per-sample update is `y = w.x; w[j] += eta * y * (x[j] - y * w[j])`. Trace row per D-01/D-04: `epoch, |w| (before renormalizing), ||dw||, eta, w_0..w_25`. Row 0 = initial state. Header from `input->names` for the w columns (see stub line 81 `(const char * const *) input->names`).

**Final steps (D-01, D-02):** renormalize w to norm 1; orient so the coefficient of largest |value| is positive (same as `pca.py::orient`, lines 77-83); then `project()` so `index.csv` is already oriented. Never compute cosine to PC1 in C (D-05).

**Writers** (stub 54-86): keep `write_outputs`; extend `METRICS_COUNT` and the `Metric` array (`{ "name", NULL, value }`; strings use `{ "model", "oja", 0 }`). Add `w_norm_final`, `delta_w_final`, `epochs`, `eta0`, `eta_final`; add `write_trace` like kohonen.c 417-420:
```c
static int write_trace(const Results * results, int epochs, const double trace[]) {
  const char * header[] = { "epoch", "eta", ... };
  return results_write_table(results, "trace.csv", TRACE_WIDTH, header, epochs + 1, trace);
}
```
Header for the trace with 26 w columns needs a built `const char *` array (names are dynamic), unlike kohonen's fixed header.

**Allocation/cleanup pattern** (stub 89-106): all-or-nothing `ok` chain, free everything at the end, `matrix_free(&input)`. Dispatch in `neuron/models/models.c` (`"oja"` -> `run_oja`) is unchanged if the function name stays. If the file is renamed, update `neuron/Makefile` sources.

### `neuron/io/config.c` (`OJA_KEYS`)

Replace lines 34-37 (the "Phase 3 appends the rows" comment and empty table) with rows copied from `KOHONEN_KEYS` (lines 23-32):
```c
static const KeySpec OJA_KEYS[] = {
  { "eta0", KEY_NUMBER, 1, NULL },
  { "eta_final", KEY_NUMBER, 1, NULL },
  { "epochs", KEY_INT, 1, NULL },
  { NULL, KEY_INT, 0, NULL },
};
```
Final column of `KeySpec` is the sentinel terminator pattern. Strict validation (unknown/missing/wrong type aborts) comes for free.

### `neuron/config.json.oja.example`
Copy `config.json.kohonen.example` shape: add `"eta0"`, `"eta_final"`, `"epochs"` after `"input": "../datos/prepared/creadores_zscore.csv"`.

### `neuron/tests/test_main.c`
Existing oja cases at 205-216 (valid load, unknown key, duplicate key, missing seed, wrong type) will now need the new keys in the valid JSON and a case for each new key missing; line 218 (kohonen key on oja) stays rejected. `same_seed_same_bytes("oja", ..., "weights.csv")` (306-307) must be extended with the new keys, and ideally also checks `trace.csv`. Add a C test: |w| ~ 1 after training on `tests/fixtures/zscore_small.csv`.

### `analysis/oja.py` (Oja vs PC1, evidence table)

**Analog:** `analysis/pca.py`. Reuse rather than rewrite:
- `read_prepared("creadores_zscore")` (130-155) returns `(features, Z, meta)`; `meta["creator_id"]`, `meta["name"]`.
- `orient`, `spearman`, `_pearson` (77-83, 157-174) for cosine sign conventions, Pearson and Spearman (D-05). overlap@k via `np.argsort`.
- Header pattern for any analysis module: `from __future__ import annotations`, `TP_DIR = Path(__file__).resolve().parent.parent`, `sys.path.insert(0, str(TP_DIR / "scripts"))` and `"analysis"` (som_select.py 23-25; som_figures.py 27-29). numpy only, no pandas; figures via `plots_style` (`save_figure`, deterministic SVG).
- Reference PC1 from `analysis/results/pca/audited/` (`loadings.csv`, scores), produced by `make pca` (directory is untracked and generated: target must depend on `pca`).
- Tests: |cos(w, v1)| > 0.99 on a smoke run (D-05), tests style as in `analysis/tests/test_pca.py`.
- Evidence table (D-06): correlations of index vs `followers` and raw `topic_*_pct` (read via `scripts/creadores.py::load_creadores`, 91-100 validates 50x33), top-10 overlap with both signs.

### `analysis/campaigns_select.py` (the pre-registered rule as code)

**Analog:** `analysis/som_select.py`. Copy the structure and reuse its guard functions by import (`from som_select import rule_digest, rule_guard`), only changing constants:
```python
RULE_FILE = "deliverables/03-oja-campanas.md"
SELECT_FILE = "analysis/campaigns_select.py"
RULE_START = "<!-- regla:inicio -->"; RULE_END = "<!-- regla:fin -->"
```
- `rule_digest(path)` (214-224): sha256 of the text strictly between markers, requires exactly one of each. Note: the markers already exist once in `deliverables/02-kohonen.md`; the Phase 3 fragment is a separate file, so no clash.
- `rule_guard(paths, repo_dir=TP_DIR)` (230-247): `git ls-files --error-unmatch`, `git status --porcelain`, `git log -1`; raises `SystemExit` unless tracked and unmodified. Paths to guard: rule file, `campaigns_select.py` and any campaign series/config file. The git toplevel is the parent `SIA-TPs`, but `repo_dir=TP_DIR` works because git runs inside the subdirectory.
- Record `rule_sha256` and `select_sha256` into a `selection.json` and check with `som_stage.require_same_rule(selection_path, rule_file, select_file)` (som_stage.py 101-113) in the later scripts.
- Rule as code: constants at the top (K = 5, topic argmax filter, per-campaign ranking criterion and composite as mean of z of each variable), pure functions over plain dicts/arrays, with the tie-break of D-13 (Oja index with D-02 sign, then `creator_id`). Dominant topic = argmax of the 4 raw `topic_*_pct` (same label as `pca.py::dominant_topics`, line 327).
- Planner note: the rule text (checkpoint approval by the user, as in 02-03) and this file must be committed together BEFORE `campaigns.py` is ever run. User makes the final commit manually (memory), so the checkpoint must tell the user to commit these before running the compute step.

### `analysis/campaigns.py` (shortlists, baselines, metrics)

**Analog:** `analysis/som_profiles.py` / `som_figures.py` (read generated SOM results, call the guard first, write CSV/MD tables and SVG). Pattern:
1. `argparse` main; call `rule_guard` and digest check first, refuse otherwise (som_figures docstring 3-8).
2. Load raw `datos/creadores.csv` via `load_creadores`; Oja `index.csv` from the figures run; SOM `assignments.csv` of the `k5-step` figure run (BMU row/col, D-14) from `analysis/results/som/`.
3. For each campaign: filter by dominant topic, rank, take k = 5; two followers baselines (global and within-topic); metrics of D-17 (overlap@5, topic share, total Argentine reach, total cost, cost per thousand Argentines = `price_usd / estimated_argentina_reach * 1000`, objective metric).
4. Write tables as CSV with the `_write_table`/`_fmt` style of `pca.py` (181-186, 177) so reruns are byte-identical.

### `analysis/maintenance_demo.py` (D-19)

**Analog:** `scripts/map_creator.py` (CLI) with `scripts/creadores.py::transform_new_creator(meta, raw)` (236-248), `scaler_from_meta`, `load_meta` (220-234). Flow: synthetic raw creator (flagged `synthetic` in output) -> z-score with the saved scaler -> BMU in the Phase 2 `k5-step` prototypes (`prototypes.csv`) -> index = x.w with saved `weights.csv` -> distance to BMU vs the QE distribution of `assignments.csv`. Read `map_creator.py` fully before planning (not excerpted here).

### `analysis/series_smoke_oja.json` / sweep
Existing file: `{ "_comment", "base_config": "../neuron/config.json.oja.example", "seeds": [1,2,3] }`. Update its comment (no longer a stub). For the 10-seed run copy `analysis/series_som_stage2.json` shape (`"set"`, `"seeds": list(range(1, 11))`, base_config) as generated by `som_select.stage2_series` (lines 250-262); a plain JSON file is enough since there are no variants. `sweep.py` already handles `seeds`; check that it tolerates a trace with extra columns.

### `analysis/tests/test_campaigns_select.py`
**Analog:** `analysis/tests/test_som_select.py`: pytest with synthetic row builders (`make_row`, lines 17-34), boundary cases for each filter, and a git-guard test that builds a temp repo with `subprocess` and checks `rule_digest` and `rule_guard` (the file imports `hashlib`, `subprocess`, `pytest`). Imports work via `analysis/tests/conftest.py` which puts `analysis/` and `scripts/` on `sys.path`.

### `deliverables/03-oja-campanas.md`
**Analog:** `deliverables/02-kohonen.md`. Reproduce: a section "Regla fijada antes de mirar resultados" with the text between `<!-- regla:inicio -->` / `<!-- regla:fin -->` that states "Esta sección fija la regla; los resultados se agregan después y no figuran acá" (line 30-31 pattern), and bullet style `- **Término.** ...`; later sections for results; final "Cómo reproducir" section (like §7). Results go AFTER the rule in a later commit; rule block contains no results. Spanish prose, respond with "no" first for OJA-03 and avoid the word "mejor" for the index.

### `Makefile` (root)
**Analog:** lines 46-47 (`pca: prepare`) and 60-66 (`som-figures`, `som-profiles`), each with a Spanish comment line and `$(PY) analysis/<script>.py`:
```make
# <comment in Spanish, what it writes, what it needs>
oja: pca
	$(PY) analysis/oja.py
campaigns: oja som-stage1
	$(PY) analysis/campaigns.py
```
Targets that need the commit-guarded rule should say so in the comment, like `som-stage1` (lines 52-54).

## Shared Patterns

### Strict config validation
**Source:** `neuron/io/config.c` `KeySpec` tables + `kohonen.c::read_params`. **Apply to:** all new C keys and params.

### Determinism (no timestamps, same seed => `diff -r` clean)
**Source:** `Results` writers (`results_write_table`, `results_write_metrics`), `plots_style.save_figure`, `rng_shuffle`. **Apply to:** all C outputs and every Python figure/table. Note: `som_stage.py::_create_sweep_dir` names sweep folders with `time.strftime` (line 118-123) but files inside have no timestamps.

### Pre-registered rule guard
**Source:** `analysis/som_select.py` 214-247 and `som_stage.py::require_same_rule` 101-113. **Apply to:** `campaigns.py`, `maintenance_demo.py` (if it reads shortlists) and the Makefile `campaigns` target.

### Sign convention
**Source:** `analysis/pca.py::orient` 77-83 (largest |coef| positive). **Apply to:** C Oja output (D-02) and Python comparison/opposite-sign evidence table.

### Python module header
`from __future__ import annotations`, module docstring citing decision ids, `TP_DIR` + `sys.path.insert` for `scripts` and `analysis`, numpy only, no pandas (F1 D-06).

## No Analog Found

| File | Role | Reason |
|---|---|---|
| Multi-seed convergence figure (|cos| per epoch for 10 seeds) | plot | Only `som_figures.py` trace plots (single run) exist; reuse `plots_style` and the approach but the multi-run overlay is new |
| `SomParams`-like check of `eta * |x|^2` stability bound | validation | New for Oja (Pitfall 8); no analog |

## Notes for the planner

- No tracked mirror issue: every analog above is a normal tracked source (`git ls-files` verified for the oja stub, kohonen.c, som_select.py, deliverables/02-kohonen.md, Makefile, series json). `analysis/results/` and `datos/prepared/` are generated and untracked (they do not exist until `make pca`/`make prepare`/SOM stages run), so Phase 3 Makefile targets must depend on them.
- `kohonen_decay` in kohonen.c is a non-static public function; check `models.h` for its declaration before reusing it from the Oja file, otherwise add it there or duplicate the one-liner.
- The git toplevel is `SIA-TPs/`, project files are under `TP4/`; `rule_guard` already handles this by running git with `cwd=TP_DIR`.

## Metadata

**Analog search scope:** `neuron/`, `analysis/`, `scripts/`, `deliverables/`, `Makefile`
**Files scanned:** ~25 (targeted reads of oja_stub.c, kohonen.c, config.c, som_select.py, som_stage.py, pca.py, creadores.py, 02-kohonen.md)
**Pattern extraction date:** 2026-10-21
