# Phase 5: Hopfield con QR - Pattern Map

**Mapped:** 2026-10-24
**Files analyzed:** 14 (new/modified)
**Analogs found:** 14 / 14 (all tracked in git)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `scripts/qr.py` (PNG -> +-1 library, new) | utility | file-I/O, transform | `scripts/letters.py` | exact |
| `scripts/prepare_qr.py` (CLI, new) | utility/CLI | file-I/O | `scripts/prepare_letters.py` | exact |
| `neuron/models/hopfield_core.c/.h` (add `hopfield_pinv`) | model core | transform | `hopfield_hebb` in same file | exact |
| `neuron/models/hopfield.c` (rule dispatch, `rule` metric) | model | batch | same file, lines 230 / 569 / 585 / 733 / 829 | exact |
| `neuron/io/config.c` (new KeySpec rows only if needed) | config | request-response | `HOPFIELD_KEYS` lines 50-62 | exact |
| `neuron/config.json.hopfield.example` | config | - | itself | exact |
| C tests for pinv (`neuron/tests/`) | test | - | existing hopfield core C tests (not read; locate with `ls neuron/tests`) | role-match |
| `analysis/hopfield.py` (numpy `pinv`, float-W checks) | utility | transform | `hebb`/`energy`/`is_fixed` lines 98-120 | role-match |
| `analysis/hopfield_qr_select.py` (frozen protocol, `rule_identity`) | utility/guard | request-response | `analysis/hopfield_select.py` `rule_identity` (253+) + `som_select.rule_digest/rule_guard` | exact |
| `analysis/hopfield_qr.py` (guarded driver, series, Hamming 1-NN, overlaps, shift) | service/driver | batch | `analysis/hopfield_letters.py` | exact |
| `analysis/hopfield_qr_figures.py` | utility | transform | `analysis/hopfield_figures.py` + `plots_style.py` | exact |
| `analysis/tests/test_hopfield_qr*.py` | test | - | `analysis/tests/test_hopfield_letters.py`, `test_hopfield_select.py` | exact |
| `Makefile` (`qr`, `hopfield-qr`, `hopfield-qr-figures`) | config | - | Makefile lines 88-99 (+ `.PHONY` line 10) | exact |
| `deliverables/05-hopfield-qr.md` | doc | - | `deliverables/04-hopfield-letras.md` | exact |

## Pattern Assignments

### `scripts/qr.py` + `scripts/prepare_qr.py` (utility, file-I/O)

**Analog:** `scripts/letters.py`, `scripts/prepare_letters.py`.

Library has no side effects on import; custom error class; `_atomic_write`; no timestamps or absolute paths in outputs; prepare returns (data, paths).

Constants and header (letters.py 18-31):
```python
TP_DIR = Path(__file__).resolve().parent.parent
PREPARED_DIR = TP_DIR / "datos" / "prepared"
...
ENCODING = "row-major 5x5, '*' = +1, '.' = -1"
```
Atomic write + meta (letters.py 146-184):
```python
def _atomic_write(path, text):
    handle, temp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    ... os.replace(temp_name, path)
header = ",".join(f"p{k}" for k in range(N_PIXELS))
body = [",".join(str(int(v)) for v in row) for row in alphabet.patterns]
meta = {"source": _source_label(source), "source_sha256": ..., "encoding": ENCODING,
        "n_patterns": ..., "n_pixels": ...}
_atomic_write(csv_path, "\n".join([header, *body]) + "\n")
```
CLI (prepare_letters.py 28-48): `argparse` with `--source/--out-dir/--show`, catch `LettersError` -> `print(..., file=sys.stderr); sys.exit(1)`, print `wrote <relpath>`.

Adaptations: sources are `datos/hopfield/{beverages,dessert,food,specials,wine}_menu_qr.png` (tracked). Output `datos/prepared/qr_pm1.csv` (5 rows x p0..p1368) + meta with per-PNG sha256. Assert shape 37x37 and all values in {0,255} (no resampling); fix an explicit file order. Polaridad: document (e.g. dark = +1). PNG reading: `analysis` deps are numpy+matplotlib only, so use `matplotlib.image.imread` / `PIL` (matplotlib dependency) and do not add a new dependency. Verify which is already in `requirements.txt` before choosing.

### `neuron/models/hopfield_core.c/.h` (add pinv)

**Analog:** `hopfield_hebb` (core.c 43-53), declared in core.h line 49. The header comment (lines 4-8) says W is integer and held exactly in a double; the new rule breaks that, so the comment and the doc for `hopfield_hebb` must be updated.
```c
void hopfield_hebb(const double patterns[], int p, int n, double w[]) {
  for (int i = 0; i < n; i++) {
    for (int j = 0; j < n; j++) {
      double sum = 0;
      if (i != j) { for (int a = 0; a < p; a++) sum += patterns[(size_t) a * n + i] * patterns[(size_t) a * n + j]; }
      w[(size_t) i * n + j] = sum;
    }
  }
}
```
New: `int hopfield_pinv(const double patterns[], int p, int n, double w[], double scratch[])` returning 0 if the Gram matrix is singular. Build G = X Xᵀ (p x p, integers), invert (Gauss-Jordan with partial pivoting; report singular), then w_ij = sum_ab X_ai (G^-1)_ab X_bj, diagonal NOT zeroed (D-07). Same signature style: flat row-major, `(size_t)` casts, no I/O in core.

**Float-W risks the planner must handle (not present in Hebb):**
- Dynamics rule "h_i == 0 keeps the state" (core.h 6-7) and `hopfield_min_margin` "wrong == 0 iff fixed point" rely on exact integer fields; with float W they need a tolerance (eps) or the fixed-point test mis-fires. Energy uses incremental `E += 2 s_i h_i` and `energy_increases` uses a 1e-9 threshold (core.h line 36); with pinv diagonal != 0 the async incremental energy formula changes (diagonal term: dE = 2 s_i h_i - w_ii ... check and recompute from scratch to validate).
- Sync mode: pinv diagonal nonzero; keep two-cycle detection unchanged.
- N = 1369: W is 1369^2 doubles (~15 MB); check allocations/`TRACE_ROWS_MAX` in hopfield.c, and the `write_stored` / `states.csv` output width (1369 columns) and trace size (energy per visit = 1369 rows per sweep).

### `neuron/models/hopfield.c` (rule dispatch)

**Analog:** itself. Edit points:
- Lines 230-233, validation currently hard-fails: `if (strcmp(rule, "hebb") != 0) { fprintf(stderr, "%s: rule must be \"hebb\"\n", config->path); return 0; }` -> accept `"hebb"` or `"pinv"`, store `params->pinv`, message `rule must be "hebb" or "pinv"`.
- Lines 569 and 733: `hopfield_hebb(buf.patterns, p, n, buf.w);` -> dispatch by rule (recall and capacity paths).
- Lines 585 and 829: metric `{ "rule", "hebb", 0 }` -> `params->pinv ? "pinv" : "hebb"`.
- Error style: `fprintf(stderr, "%s: ...\n", config->path); return 0;` with all keys validated before allocating. Allocation check pattern at 555-557.
- Hamming 1-NN: either implement in Python (numpy; no dynamics, trivial) or as `task` in C. D-08 gives no language; Python is lower risk. If a C task is added, `task` validation is at lines 224-228 and `config.c` comment at 43.

### `neuron/io/config.c` (HOPFIELD_KEYS)

**Analog:** lines 50-62; rows are `{ "name", KEY_TYPE, required, NULL }`, terminator `{ NULL, KEY_INT, 0, NULL }`. `rule` already exists as required `KEY_STRING`; likely NO new keys needed (rule "pinv" is just a value). Update the doc comment at line 43 ("rule: the learning rule; \"hebb\"") to mention "pinv".

### `neuron/config.json.hopfield.example`

Flat JSON: `"model","seed","input","task","rule","update","max_sweeps","trials","noise_levels","subset","trace_trials"`. Add a pinv/QR example (input `datos/prepared/qr_pm1.csv`, `"rule": "pinv"`, `"subset": [0,1,2,3,4]`). Strict validation means any example key must be in `HOPFIELD_KEYS`.

### `analysis/hopfield.py` (numpy recomputation)

**Analog:** lines 98-127, int64-exact:
```python
def hebb(P): P = np.asarray(P, dtype=np.int64); W = P.T @ P; np.fill_diagonal(W, 0); return W
def energy(W, s): s = np.asarray(s, dtype=np.int64); return float(-0.5 * (s @ np.asarray(W, dtype=np.int64) @ s))
def is_fixed(W, s): return bool(np.all(s * fields(W, s) >= 0))
```
These cast W to int64: that would silently truncate a pinv W. Add `pinv(P)` returning float64 `P.T @ np.linalg.inv(P @ P.T) @ P` (numpy linalg is OK as an independent check), and make `fields/energy/is_fixed/margins` and the `_replay_async/_replay_sync` / `check_recall` / `_check_stored` comparisons float-aware with tolerance (`_expect(..., tol=...)` already supports `tol`, line 173). Also `load_patterns` and the `rule` read from `read_metrics/read_config`.

### `analysis/hopfield_qr_select.py` (frozen protocol and guard)

**Analog:** `analysis/som_select.py` 214-247 and `analysis/hopfield_select.py:253+` (`rule_identity`).
```python
def rule_digest(path) -> str:   # sha256 of text strictly between RULE_START / RULE_END markers (exactly one of each)
def rule_guard(paths, repo_dir=TP_DIR) -> str:  # git ls-files --error-unmatch + git status --porcelain per path; returns last commit
```
`rule_identity` pattern: `som_select.rule_guard(guarded, repo_dir)` over `[SELECT_FILE, ALPHABET_FILE, LETTERS_FILE]`; re-raise as `SystemExit(f"{error}; Phase N: ... (D-04)") from None`; check `RULE_FILE` tracked; `_added_commit` for the rule and select files must be the same commit; data files must be in that commit or an ancestor. Adaptation (D-01): guarded set = protocol file code + the 5 PNGs (`datos/hopfield/*_menu_qr.png`) + `scripts/qr.py` (+ `deliverables/05-hopfield-qr.md` rule text). Recorded identity should include the 5 PNG hashes. Also reuse `som_stage.require_same_rule` if comparing against a recorded digest.

Frozen protocol constants (D-02/D-03/D-05): 11 levels 0..0.5 step 0.05, 30 trials, seeds 1..10, success = exact 1369-pixel match, numeric verdict thresholds, literal hypothesis.

### `analysis/hopfield_qr.py` (guarded driver)

**Analog:** `analysis/hopfield_letters.py` (docstring lines 1-23, imports 25-49, constants 51-63). Reuse structure:
- Header: `TP_DIR = Path(__file__).resolve().parent.parent; sys.path.insert(0, ...scripts); sys.path.insert(0, ...analysis)`; `import hopfield, sweep` (`# noqa: E402`).
- `RESULTS_SUBDIR = Path("hopfield") / "letters"` -> `Path("hopfield") / "qr"`; `RECALL_COLUMNS` list (set, update, noise, flipped, n_trials, recall_rate, recall_sd_seeds, ..., mean_sweeps, mean_final_overlap) -> replace `set` by `rule` (hebb/pinv/hamming) and add final energy columns (D-09).
- Frozen `Design` dataclass via `default_design()` (line 89); series built in code (`recall_series`, 184) with `_make_series`, `run_series` (192), `aggregate_recall` (229); `sweep.Variant`/`sweep.Series` from `analysis/sweep.py`.
- `run()` (637-660): `identity = hopfield_select.rule_identity(repo_dir)` when `check_rule`; `shutil.rmtree(out)` before a re-run; try/except removing output on failure; `_write_json`; `selection.json` -> `protocol.json`, `run.json` with `code_identity` (`CODE_FILES` tuple, lines 61-63, add the QR files; `code_file_hashes`, `code_identity`, `changed_code_files`).
- Every C run passes through `hopfield.check_recall` before aggregation.
- Noise: the C core flips exactly k = lround(level*N) distinct pixels via `rng_shuffle`; with N = 1369 and 0.05 steps, k = lround(68.45...) etc.; state the rounding in the protocol.
- Hamming 1-NN, 5x5 overlap matrix, identical-pixel fraction (69.8% expected), min pair Hamming distance (96 expected), shift test (np.roll or padded shift of 1-2 px): numpy-only, computed in this driver (or a sibling `hopfield_qr_limits.py`).

### `analysis/hopfield_qr_figures.py`

**Analog:** `analysis/hopfield_figures.py` (refuses to draw if rule or code files changed: uses `hopfield_letters.changed_code_files` / WR-02) and `analysis/plots_style.py` for style. Figures: QR images, 5x5 overlap matrix, recovery vs noise (3 rules), continuous |m|, energy/sweeps per level, shift triptych, majority attractor of Hebb. Read `hopfield_figures.py` imports and style calls when planning; I did not extract excerpts from it.

### `Makefile`

**Analog:** lines 86-99 (and `.PHONY` line 10):
```make
letters: venv
	$(PY) scripts/prepare_letters.py
hopfield-letters: letters
	$(PY) analysis/hopfield_letters.py
hopfield-figures: venv
	$(PY) analysis/hopfield_figures.py
```
Add `qr`, `hopfield-qr` (depends on `qr`), `hopfield-qr-figures`, with Spanish comments naming `deliverables/05-hopfield-qr.md`, and add to `.PHONY`. `make test` already covers C (ASan/UBSan) + pytest.

### `deliverables/05-hopfield-qr.md`

**Analog:** `deliverables/04-hopfield-letras.md`: section layout `## 1. Algoritmo y salidas`, ..., `## 3. Regla ... (fijada antes de correr la red)` containing:
```
<!-- regla:inicio -->
Esta sección fija la regla; los resultados se agregan después y no figuran acá. ...
- **Éxito.** Solo el match exacto: ...
- **Ruido.** Se invierten exactamente k = lround(nivel × 25) píxeles distintos ...
- **Guardia.** El sha256 del texto entre los marcadores más el commit; ... quedan congelados con él.
- **Divulgación.** ...
<!-- regla:fin -->
```
and a final `## N. Cómo reproducir`. Style: Spanish, bullet per bolded concept, one `**Guardia.**` and one `**Divulgación.**` bullet. Disclose that the research (PITFALLS.md Pitfall 1) already measured Hebb 0% / pinv remedy before this protocol (honest framing, as Phase 4 did with its draft). Commit protocol text and guarded files BEFORE running (one-way, D-01).

## Shared Patterns

- **Guard before run (D-01):** `som_select.rule_guard` + `rule_identity`-style wrapper, `SystemExit` messages ending in the decision tag.
- **Per-run determinism:** one folder per run, no timestamps, `diff -r` clean for same seed; `_atomic_write` for prepared files.
- **Strict config:** every key in a run config must exist in `HOPFIELD_KEYS`; errors as `"%s: ...\n", config->path`.
- **Independent numpy recomputation:** every C output is verified by `analysis/hopfield.py` before aggregation (must be made float-tolerant for pinv).
- **No pandas; matplotlib figures via `plots_style.py`; results under `analysis/results/` not versioned.**
- **Tracked-source gate:** all analog paths above were listed by `git ls-files` (analysis, scripts, Makefile, deliverables, datos/hopfield PNGs, neuron/io, neuron/config.json.hopfield.example). `neuron/models/*.c|h` and `Makefile` are tracked by the same repo layout but were not individually confirmed with `git ls-files`.

## No Analog Found

| File / capability | Reason |
|---|---|
| Gauss-Jordan inversion of the 5x5 Gram in C | No matrix inversion exists in the C code; write from scratch (check conditioning / singular -> return error). |
| Float-valued W handling (tolerant fixed-point and tie tests) | All existing Hopfield code assumes exact integer W. |
| PNG reader | No image-reading code in the repo; use a library already in `analysis/requirements.txt` (check) rather than add a dependency. |

## Metadata

**Analog search scope:** `neuron/models`, `neuron/io`, `scripts`, `analysis`, `deliverables`, `Makefile`, `datos/hopfield`
**Files read:** hopfield_core.h, hopfield_core.c (43-62), hopfield.c (205-244, 555-594), config.c (40-70), prepare_letters.py, letters.py (1-32, 146-200), som_select.py (205-247), hopfield_select.py (253-278), hopfield.py (98-127), hopfield_letters.py (1-63, 637-660), Makefile (85-99), deliverables/04 (46-67), config example
**Pattern extraction date:** 2026-10-24
