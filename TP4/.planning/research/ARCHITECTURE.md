# Architecture Research

**Domain:** Academic unsupervised-learning / associative-memory assignment (Kohonen SOM, Oja, Hopfield) with a C core and a Python analysis layer
**Researched:** 2026-10-20
**Confidence:** HIGH for the reuse map and the C/Python contract (read TP3 source directly, measured the QR files and read the course slides); MEDIUM for per-model config key names (design proposals, to be fixed in phase planning)

## Standard Architecture

The shape is the one TP3 already proved: a **run is a pure function** (`config.json` in, a directory of CSV/JSON files out), the C binary knows nothing about experiments, and Python orchestrates runs (sweeps), derives cross-run metrics and draws everything. TP4 changes three things: one binary serves three models (dispatch on a `"model"` key), the sweep runner becomes model-agnostic (reads `metrics.json` instead of a hard-coded MSE summary), and the figures have two renderers (plotly for exploration and the informe, stdlib HTML/SVG fragments for slides).

### System Overview

```
 INPUTS (given, read-only)                       datos/creadores.csv        datos/hopfield/*.png (5 x 37x37, 0/255)
                                                        |                              |
 PREPARATION (Python, deterministic, one-shot)          v                              v
                                          scripts/prepare_creators.py     scripts/prepare_qr.py   scripts/prepare_letters.py
                                                        |                              |                    |
                                                        v                              v                    v
 PREPARED DATA (small, committable)   neuron/data/creators_<variant>.csv      neuron/data/qr.csv     neuron/data/letters_*.csv
                                      neuron/data/creators_<variant>.meta.json (feature list, mean, std, ids)   (+ *.meta.json: shape, names)
                                                        |                              |                    |
 C CORE  (neuron/build/neuron <config.json>)            v                              v                    v
   +------------------------------------------------------------------------------------------------------------+
   | main.c: load config -> dispatch on "model" -> runner -> results dir        stdout: "results -> <dir>"       |
   |   kohonen/ (SOM)      oja/ (Oja + Sanger)       hopfield/ (store, energy, update, noise)                   |
   |   shared: rng, io/config, io/matrix, io/results, schedule                                                  |
   +------------------------------------------------------------------------------------------------------------+
                                                        |
 RUN DIRECTORY  results/<ts>_<model>/  config.json (copy) + metrics.json (flat scalars) + model CSVs
                                                        |
 ORCHESTRATION (Python, stdlib)                         v
   analysis/sweep.py <series.json> --> analysis/results/<series>_<ts>/{plan.json, configs/, runs/<run>/, summary.csv}
                                                        |
 ANALYSIS (Python, numpy)   <---- datos/creadores.csv (EDA, PCA run directly in Python, no C involved)
   ex1_eda / ex1_pca / ex1_kohonen / ex1_oja / ex1_campaigns / ex2_letters / ex2_qr
                                                        |
 RENDERING                                              v
   figure data (pure functions, no I/O styling) --> plots_*.py (plotly, interactive, informe)
                                               \--> slides_*.py (stdlib div/SVG fragments, slides)
                                                        |
 DELIVERABLES                                           v
   Informe (Artifact)   +   Slides (Artifact)   +   code + README
```

### Component Responsibilities

| Component | Responsibility | Talks to | Notes |
|-----------|----------------|----------|-------|
| `scripts/prepare_creators.py` | Select/transform features (drop collinear derivatives, log of heavy-tailed counts), z-score, write numeric matrix + `.meta.json` (feature names, mean, std, creator ids/names, row order) | reads `datos/`, writes `neuron/data/` | Owns every preprocessing decision. The C core never selects, scales or drops columns |
| `scripts/prepare_qr.py` | PNG -> 37x37 -> +1 (black) / -1 (white), flatten row-major, one pattern per row | reads `datos/hopfield/*.png`, writes `neuron/data/qr.csv` + meta | Files are 8-bit gray, pure 0/255, no quiet zone (measured), so no thresholding ambiguity |
| `scripts/prepare_letters.py` | Letters as ASCII art in the script -> ±1 5x5 patterns; emits several named sets (low-overlap vs high-overlap) | writes `neuron/data/letters_*.csv` | Makes the orthogonality/capacity study a data choice, not a code change |
| `neuron/` C core | Run one model from one config; write the run directory | config.json, `neuron/data/*.csv`; writes `results/` | Algorithms are I/O-free modules; runner files do the glue |
| `analysis/sweep.py` | Expand a series JSON (base config + variants/product + seeds) into runs, run them in parallel, collect `metrics.json` into `summary.csv` | spawns the C binary | Model-agnostic: summary columns = union of `metrics.json` keys + the varied config keys |
| `analysis/ex1_eda.py`, `ex1_pca.py` | EDA tables/plots, correlation structure, PCA (numpy `eigh` on the covariance), eigenvalues plot, loadings, biplot data | reads `datos/creadores.csv` and prepared CSV | Pure Python. PCA is the reference for Oja and the lens for reading the SOM |
| `analysis/ex1_kohonen.py` | Hyperparameter selection (QE, TE, empty units, seed stability), grid/hits/U-matrix views, profile per region, comparison with PC1/PC2 | summary.csv, runs/*/neurons.csv, assignments.csv, pca output | Cross-run metrics live here, not in C |
| `analysis/ex1_oja.py` | Convergence of w vs PC1 (|cos|, sign-aligned), index per creator, rank correlation with PC1 projection, "top-1 for any campaign?" argument | runs/*, pca output | |
| `analysis/ex1_campaigns.py` | Campaign scoring (football, dogs, makeup, art), reach/discovery/depth profiles, comparison against a followers-only ranking, maintenance scenarios (new creators via `epochs: 0` mapping) | everything above | Python-side decision logic over the model outputs |
| `analysis/ex2_letters.py`, `ex2_qr.py` | Overlap (Gram) matrix, capacity curves, noise curves, energy traces, spurious-state catalogue, QR renders | trials.csv, trace.csv, states.csv, summary.csv | |
| `analysis/plots_style.py` | Palette, layout, `write_html` with shared `plotly.min.js` | all plotly scripts | Copy from TP3 |
| `analysis/slides_*.py` | Same figure data as the plotly versions, rendered as stdlib HTML/SVG fragments | figure-data functions | TP3's `plots_presentation.py` reason: Slides artifacts cannot load plotly or webfonts |
| `deliverables/` | Narrative text (outline for slides and informe), exported figure fragments | analysis outputs | Final Artifacts are assembled from these; no generated results are versioned |

## Recommended Project Structure

```
TP4/
├── datos/                          # given, read-only
├── docs/                           # given PDFs
├── neuron/                         # C core (name kept from PROJECT.md; binary stays build/neuron so sweep.py ports unchanged)
│   ├── main.c                      # argv/config -> dispatch on config.model -> print "results -> <dir>"
│   ├── rng.c / rng.h               # COPY of TP3 (splitmix64). Add rng_below(n) only if needed
│   ├── io/
│   │   ├── config.c / config.h     # TP3 table-driven flat-JSON parser; "model" selects required/refused key sets
│   │   ├── matrix.c / matrix.h     # numeric CSV -> Matrix{rows, cols, header[]}; adapted from TP3 dataset.c (drop zeta/split logic)
│   │   └── results.c / results.h   # run dir, config copy, write_table(), write_metrics_json()
│   ├── schedule/schedule.c         # eta(t), radius(t): constant | linear | exponential | inverse (1/t as in the course)
│   ├── kohonen/kohonen.c           # init, bmu, update, qe, te, umatrix, hits. No printf, no files
│   ├── oja/oja.c                   # oja_step (1 component) / sanger_step (k components). No I/O
│   ├── hopfield/
│   │   ├── hopfield.c              # store (integer W), field, energy, sync step, async sweep, run-to-fixed-point
│   │   └── noise.c                 # flip k pixels, occlude a rectangle, random state
│   ├── run_kohonen.c / run_oja.c / run_hopfield.c   # glue: Config + Matrix -> algorithm -> results files + metrics
│   ├── tests/test_main.c           # TP3 check()/check_close() harness, tests per module
│   ├── Makefile                    # TP3's, wildcard adds new dirs; `make`, `make run`, `make test`, `make clean`
│   ├── data/                       # prepared inputs (small; recommend committing, see Decisions)
│   ├── config.json.<name>.example  # kohonen, oja, hopfield_letters, hopfield_qr
│   └── README.md                   # config keys per model, output files per model (TP3 neuron/README.md style)
├── scripts/                        # one-shot preparation + helpers, argparse + --name like TP3
│   ├── prepare_creators.py
│   ├── prepare_qr.py
│   ├── prepare_letters.py
│   ├── show_run.py                 # plotly page for ONE run (replaces TP3's 1000-line run_report.py), used by `make run`
│   └── reproduce.sh                # prepare -> build -> every series -> every figure, in order (reproducibility constraint)
├── analysis/
│   ├── requirements.txt            # numpy, plotly (+ Pillow only if prepare_qr uses it)
│   ├── sweep.py                    # generalized from TP3 (see Reuse Map)
│   ├── series_*.json               # one per question, versioned
│   ├── runs.py                     # load run dir / summary.csv into plain dicts+numpy (shared loader)
│   ├── pca.py                      # eigh PCA, scaler application, projection, loadings; used by ex1_*
│   ├── metrics.py                  # seed-stability (co-assignment / adjusted Rand across seeds), silhouette on assignments, overlap matrix
│   ├── paired_stats.py             # COPY of TP3 (permutation test, bootstrap CI, Holm), optional
│   ├── plots_style.py              # COPY of TP3 (+ sequential/diverging scales, black/white pixel scale)
│   ├── ex1_*.py / ex2_*.py         # one analysis script per exercise block; each writes tables + figures
│   ├── plots_*.py                  # plotly renderers
│   ├── slides_*.py                 # stdlib fragment renderers
│   ├── results/                    # gitignored
│   └── README.md                   # series table: file, what varies, question it answers (TP3 style)
├── deliverables/                   # outlines (text), exported fragments (gitignored or regenerated)
└── .planning/
```

### Structure Rationale

- **`neuron/` with one binary:** TP3's single-binary contract (`./build/neuron config.json` prints `results -> dir`) is what `sweep.py`, `make run` and the tests rely on. Three binaries would triplicate `rng`, `config`, `results` and the Makefile and force three sweep code paths. Dispatch on `"model"` keeps one code path. The directory name `neuron/` is kept because PROJECT.md says so; renaming to `core/` is cosmetic and can be decided in phase 1 at zero cost if wanted.
- **Algorithm modules vs runner files:** `kohonen.c`/`oja.c`/`hopfield.c` take plain arrays plus `Rng *` and return values, so unit tests need no files (TP3 did the same with `network.c`). `run_*.c` own the parsing-to-output glue.
- **`scripts/` vs `analysis/`:** `scripts/` = deterministic data transformation that produces C inputs; `analysis/` = anything that consumes C outputs. This split already exists in TP3 and keeps "what feeds the core" separate from "what reads the core".
- **Per-exercise analysis scripts (`ex1_*`, `ex2_*`):** TP3's flat `analysis/` grew to 30 files with no grouping. The prefix costs nothing and maps onto the enunciado sections and onto roadmap phases.
- **`runs.py` + figure-data functions separate from renderers:** every figure is needed twice (plotly for the informe, fragments for slides). Computing the numbers once and rendering twice avoids two diverging versions of the same chart.

## Architectural Patterns

### Pattern 1: Run as a pure function with a self-describing directory

**What:** `config.json` in, directory out. The directory contains a byte copy of the config, `metrics.json` (flat scalars) and the model's CSVs. Progress goes to stderr; the only stdout line is `results -> <dir>`.
**When to use:** Always. It makes every experiment re-runnable from its own folder and lets `sweep.py` stay ignorant of the model.
**Trade-offs:** Many small directories (thousands for big Kohonen grids). Each is a few KB, so acceptable; keep traces opt-in for Hopfield.

```c
// results.h (new, on top of TP3's results_create / open_in_run_dir)
int results_write_metrics(const Results *r, int n, const char *keys[], const double values[]); // flat {"qe": 1.23, ...}
int results_write_table(const Results *r, const char *name, int n_cols, const char *header[],
                        int n_rows, const double data[]);   // %.17g, header from feature names
```

### Pattern 2: Flat config with per-model key sets (generalizes TP3's optimizer check)

**What:** TP3's `config.c` already enforces "every key the optimizer reads is required, any other is refused". Replace the optimizer table by a model table: `{"kohonen", {grid_k, radius0, ...}}`, `{"oja", {...}}`, `{"hopfield", {...}}`. Keep the offsetof-driven `FIELDS[]` table and the tiny hand-written JSON parser; no nested JSON needed.
**When to use:** Always; a typo in a hyperparameter name fails loudly instead of silently running defaults, which matters when a sweep varies that key.
**Trade-offs:** One flat `Config` struct with fields unused by the other models; the parser refuses them, so no ambiguity.

Proposed keys (reuse names from the course slides):

| Model | Keys |
|-------|------|
| common | `model`, `seed`, `dataset` (or `patterns`) |
| kohonen | `grid_k` (k x k per the course), `iterations` (sample presentations), `eta0`, `eta_schedule`, `radius0`, `radius_schedule`, `neighborhood` (`step` as in the slides, `gaussian` optional), `distance` (`euclidean`, `exponential`), `init` (`sample`, `uniform`), `shuffle`, `record_every`, optional `initial_weights` (+ `iterations: 0` = map-only, for new creators) |
| oja | `epochs`, `eta`, `eta_schedule`, `n_components` (1 = Oja, >1 = Sanger), `shuffle`, `init`, optional `initial_weights` |
| hopfield | `patterns` or (`random_count`, `random_size`, `pattern_seed`; exactly one source), `n_stored`, `update` (`sync` = course default, `async`), `max_iterations`, `noise_type` (`flip`, `occlude`, `random`), `noise` (fraction of pixels), `trials`, `target` (index or -1 = all), `trace_trials`, `save_weights` |

### Pattern 3: I/O-free algorithm modules

**What:** `kohonen_train(const Matrix*, const KohonenParams*, Rng*, KohonenResult*)` and similar; no `printf`, no `fopen`. Runner files translate results into files.
**When to use:** Always; it is what makes the invariants below testable in milliseconds.
**Trade-offs:** A little more glue code.

### Pattern 4: Python never reimplements stochastic C logic

**What:** All randomness lives in C. When Python needs a noisy query or a trajectory (to plot it), C writes the actual states (`states.csv`) instead of Python re-deriving them from a seed. Python may recompute only deterministic math as a cross-check (PCA vs Oja, W from patterns, energy of a given state), as TP3's `model.py` did for the forward pass.
**When to use:** Always. Cross-language RNG parity is a trap.

### Pattern 5: Preprocessing outside the core, scaler persisted

**What:** `prepare_creators.py` writes the numeric matrix plus `.meta.json` holding feature order, mean, std and creator ids. Python de-standardizes SOM prototypes for profile interpretation and standardizes new rows with the *stored* parameters.
**When to use:** Required by the maintenance questions in the enunciado (new creators, new variables, monthly refresh): "new creators" = `scaler.transform` + `epochs: 0` mapping onto the trained grid; "new variables" = re-run `prepare_creators.py` with a new feature list and retrain.

### Pattern 6: Series spec as the unit of reproducibility

**What:** One `series_*.json` per question (base config + `vary`/`values`, `variants`, or new `product`, + `seeds`), exactly TP3's format. Results are not versioned; the series files plus fixed seeds are.
**When to use:** Every hyperparameter or noise-level study. `scripts/reproduce.sh` lists the series in dependency order.

## Data Flow

### C <-> Python data contract (the important part)

| Artifact | Producer -> Consumer | Format | Contents |
|----------|---------------------|--------|----------|
| `neuron/data/creators_<v>.csv` | prepare_creators -> C, Python | CSV, header = feature names, numeric only, one row per creator in `creadores.csv` order | z-scored (and optionally log-transformed) selected features. Row i = creator i; ids live in the meta file, Python joins by row index and asserts the row count |
| `neuron/data/creators_<v>.meta.json` | prepare_creators -> Python | JSON | `features`, `mean`, `std`, `log_features`, `dropped`, `creator_id[]`, `name[]` |
| `neuron/data/qr.csv`, `letters_*.csv` | prepare_* -> C, Python | CSV, one pattern per row, ±1 integers, row-major pixels | QR: 5 x 1369; letters: p x 25 |
| `*.meta.json` for patterns | prepare_* -> Python | JSON | `shape` [37,37] / [5,5], `names`, black = +1 convention |
| `config.json` | Python (sweep) or hand -> C | flat JSON | per-model keys; sweep rewrites dataset paths to absolute, as in TP3 |
| `results/<ts>_<model>/config.json` | C | byte copy | provenance |
| `metrics.json` | C -> sweep, Python | flat JSON of scalars | always `model`, `seed`, `elapsed_s`; Kohonen: `qe`, `te`, `empty_neurons`, `u_mean`, `u_max`, `iterations`; Oja: `epochs`, `w_norm`, `final_delta`; Hopfield: `n_neurons`, `n_stored`, `alpha`, `max_abs_overlap`, `stored_stable_frac`, `recall_rate`, `mean_iterations`, `spurious_rate` |
| `neurons.csv` (Kohonen) | C -> Python | CSV, one row per neuron | `row,col,hits,u,<one column per feature>` (weights in standardized space, `%.17g`) |
| `assignments.csv` (Kohonen) | C -> Python | CSV, one row per creator | `sample,row,col,distance,second_row,second_col` (second BMU gives TE and region membership) |
| `history.csv` (Kohonen) | C -> Python | CSV | `iteration,eta,radius,qe,te` at `record_every` |
| `weights.csv` (Oja) | C -> Python | CSV | `component,<features>` final w (unit-ish norm); `weights_history.csv` per epoch for convergence plots |
| `index.csv` (Oja) | C -> Python | CSV | `sample,y_1[,y_2...]` = w . x per creator |
| `trials.csv` (Hopfield) | C -> Python | CSV, one row per trial | `trial,target,noise_k,iterations,status(fixed/cycle/max),e_start,e_final,overlap_target,match,match_overlap,class(stored/inverse/spurious)` |
| `trace.csv`, `states.csv` (Hopfield) | C -> Python | CSV, only for `trace_trials` | `trial,step,energy,overlap_target,changed` and `trial,step,s_1..s_N` (initial query, every step, final) |
| `weights.csv` (Hopfield) | C -> Python | only when `save_weights` = 1 (letters) | Never for QR: W is 1369 x 1369 = 1.87M entries |
| `summary.csv` | sweep -> Python | CSV | `run,variant,label,seed,status` + every varied config key as its own column + union of `metrics.json` keys |
| `plan.json`, `series.json`, `configs/` | sweep | JSON | resolved series, exact config per run |

Rules: matrices are CSV with headers and `%.17g` doubles (TP3 round-trip rule, needed for `initial_weights` and for Python/C parity); scalars are JSON; ±1 states are written as integers. No binary formats.

### Key Data Flows

1. **Ex 1 main path:** `creadores.csv` -> EDA/PCA (Python) decides features -> `prepare_creators` -> `neuron/data` -> Kohonen/Oja runs (C) -> `sweep` -> `summary.csv` + `neurons.csv` + `assignments.csv` -> `ex1_kohonen` (selection, regions, U-matrix, biplot overlay) and `ex1_oja` (vs PC1) -> `ex1_campaigns` (decisions, followers-only baseline).
2. **Ex 2 letters:** `prepare_letters` -> `hopfield` runs (sync and async, noise sweep, random-pattern capacity sweep) -> `trials.csv`, `trace.csv`, `weights.csv` -> orthogonality (Gram matrix in Python), capacity curve, spurious catalogue.
3. **Ex 2 QR:** `prepare_qr` -> `hopfield` runs over noise levels and noise types (`flip`, `occlude` = the broken corner of the story) -> `trials.csv` + a few traced trials -> recall-vs-noise curves, energy per step, recovered images, limitations argument.
4. **Deliverables:** analysis scripts emit figure data once; `plots_*.py` and `slides_*.py` render it; outlines in `deliverables/` reference figure names; Artifacts are assembled from them.

### Model-specific facts that shape the design

- **Kohonen** (49 x ~31, k x k grid): a run takes milliseconds, so hyperparameter grids x 20-30 seeds are cheap. Maps from different seeds are rotations/reflections of each other, so cross-seed comparison must use **assignments** (which creators share a neuron/region), never raw weight grids. The course defines the neighborhood as a step function with radius R(i) tending to 1 and eta(i) tending to 0 (e.g. 1/i), init from random samples to avoid dead units, Euclidean or exponential similarity, and says to standardize: these map directly onto the config keys above. The strict `<` in the slide's N(i) = {n : ||n - n_k|| < R(i)} is ambiguous at R = 1; decide and document it (use `<=` so R = 1 means the 4-neighborhood, as the slide's example says).
- **Oja:** only finds PC1 on **centered** data; the C runner should warn on stderr when a column mean exceeds 1e-6. Sign is arbitrary, so compare |cos(w, PC1)| and sign-align before correlating the index with the PC1 projection. Sanger (n_components > 1) is nearly free once Oja exists and gives PC2 for the biplot comparison.
- **Hopfield:** the course algorithm is **synchronous** S(t+1) = sign(W S(t)), with h = 0 keeping the previous state, w_ii = 0, W = (1/N) sum xi xi^T. Implement `sync` as the baseline and `async` (random-order sweeps) as the comparison, because only async guarantees a non-increasing energy and sync can fall into 2-cycles (detect and report `status = cycle`). Store W as the **integer** matrix sum xi xi^T (scale 1/N applied only when reporting energy): fields are exact integers, so the h = 0 tie rule is deterministic and immune to compiler float reordering. Energy E = -1/2 sum w_ij S_i S_j per step is the required "energy per step" output.
- **The QR set is not random-pattern territory (measured):** the five PNGs are exactly a QR version 5 module matrix (37 = 17 + 4*5), pure 0/255, no quiet zone, ~52% black, and the pairwise overlaps (xi_a . xi_b / N) are 0.58 to 0.86 (finder patterns, timing lines, format bits, shared URL prefix). The p/N ratio is tiny (5/1369 = 0.004, far below the 0.138 rule of thumb), yet Hebbian crosstalk will be large because the patterns are highly correlated. This is the main thing the QR analysis and the "limitations" section must show, so the Gram matrix and per-pattern recall-vs-noise are first-class outputs, not extras. A pseudo-inverse learning rule (`learning: "pseudoinverse"`, needs inverting a 5 x 5 Gram matrix) is the natural optional comparison; flag as a differentiator, not a requirement.
- **Cost (measured here):** one full field computation W.s for N = 1369 with int32 W takes ~0.11 ms (`gcc -O3 -march=native`, this machine). A synchronous iteration is therefore ~0.1 ms and a few thousand trials per noise level run in seconds; maintaining local fields incrementally makes an async single flip O(N). No performance engineering is needed; determinism and exactness matter more.

## Reuse Map from TP3 (verified by reading the files)

| TP3 file | Action | Details |
|----------|--------|---------|
| `neuron/rng.c/.h` (splitmix64, `rng_uniform`, `rng_shuffle`) | Copy verbatim | `rng_shuffle` on an index array and taking the first k gives the "flip exactly k pixels" noise; add `rng_below(n)` only if sample picking needs it |
| `neuron/io/config.c/.h` | Adapt | Keep `Parser`, `parse_string/number/integer/bool`, the `FIELDS[]` offsetof table, optional flags, and the "exactly one of validation_dataset / validation_split" check (reuse for `patterns` vs `random_count`). Replace the optimizer tables by a model table. Drop `FIELD_INT_ARRAY` and the 4096-byte limit is fine for these configs |
| `neuron/io/dataset.c/.h` | Adapt into `matrix.c/.h` | TP3 requires zeta columns and has `dataset_split`; TP4 needs a plain numeric CSV (header optional, header names kept) |
| `neuron/io/results.c/.h` | Adapt | Keep `make_run_dir` (timestamp + collision suffix), `open_in_run_dir`, `copy_file`, the `%.17g` convention; add `write_table` and `write_metrics_json`; naming `<ts>_<model>` |
| `neuron/main.c` | Adapt | Keep `die()`, `config_path()`, `now_seconds()`, stderr progress, `results -> dir` on stdout; replace network wiring by dispatch |
| `neuron/Makefile` | Adapt | Keep wildcard sources, `-MMD -MP`, `test` target, `CONFIG ?=` `run` target. Drop `-fassociative-math -fno-signed-zeros -fno-trapping-math` (they exist for TP3's dot-product hot loop and are unwanted where exactness matters); point `run` at `scripts/show_run.py` |
| `neuron/tests/test_main.c` | Reuse harness | The `check()` / `check_close()` macros and exit-code convention; write new tests per module |
| `neuron/{network,neuron,activation,optimizer}*` | Drop | Perceptron-specific |
| `analysis/sweep.py` | Adapt (largest change) | Keep `Series/Variant/Task`, `load_series`, `plan`, `absolute_paths` (add `patterns`, `dataset`), `run_all` (ThreadPoolExecutor, move `results/<ts>` into `runs/<name>`), `print_progress`, CLI flags `--workers --dry-run`. Replace `RunSummary`, `summarize`, `converged`, `accuracy` and the `run_report/run_error` imports with a generic `metrics.json` reader. Drop `MAX_VARIANTS = 8` (a plotting limit, not a sweep limit; SOM grids are 2-D grids of hyperparameters). Add `product` (Cartesian over several keys) and write each varied key as its own `summary.csv` column so analysis never parses labels |
| `analysis/plots_style.py` | Copy verbatim | `palette_for` (<= 8 categorical slots, never cycled), `base_layout`, `end_label`, `translucent`, `write_html` with shared `plotly.min.js`. Add sequential/diverging scales (U-matrix, hits, biplot) and a black/white scale for ±1 pixel images |
| `analysis/plots_data.py` | Adapt ideas | `load_summary_rows`, `Band` (mean and min-max across seeds), `curve_bands`, `final_values` apply to QE vs iteration, recall vs noise |
| `analysis/paired_stats.py` | Copy | Permutation test, bootstrap CI, Holm; useful to compare Kohonen configs seed by seed |
| `analysis/plots_presentation.py` | Reuse the approach | stdlib div/SVG fragments with pinned labels, palette slots 1-5; new content |
| `analysis/sweep_report.py`, `scripts/run_report.py`, `report_server.py`, `run_error.py` | Drop | 1400+ lines of MSE/epoch-specific HTML and a live-reload server. Replace with plotly figures per question plus one small `show_run.py` |
| `analysis/{model,attribution,robustness,fraud_*,digits_ensemble}.py`, `scripts/prepare_{digits,fraud}*.py`, `perturb_dataset.py` | Drop | Domain-specific. Keep only the *style* of `prepare_*` scripts (argparse, `--name`, deterministic, write into `neuron/data/`) |
| `analysis/README.md` series table | Keep the format | File, what varies, question it answers |
| `.gitignore` (`build/`, `results/`, `config.json`) | Reuse | Prepared data is tiny and deterministic: recommend committing `neuron/data/*.csv` (unlike TP3's gitignored `data/`) so the C core runs without Python; this is the one deliberate deviation |

## Anti-Patterns

### Anti-Pattern 1: Three separate binaries (or three copies of config/rng/io)
**What people do:** `kohonen/`, `oja/`, `hopfield/` as three mini-projects.
**Why it's wrong:** Triplicated parser, rng and results code, three Makefiles, three sweep paths; the first bug fixed in one copy is missed in the others.
**Do this instead:** One binary, `"model"` key, shared `io/` and `rng`.

### Anti-Pattern 2: Preprocessing decisions inside the C core
**What people do:** Let C standardize, drop columns or read `creadores.csv` directly.
**Why it's wrong:** Feature selection is an EDA/PCA outcome that will change during the project (collinear derived variables, sponsored/organic pair summing to 100). Each change would need a C edit, and the scaler would not be available to Python for de-standardizing prototypes or transforming new creators.
**Do this instead:** `prepare_creators.py` with flags (`--drop`, `--log`, `--name`) and a `.meta.json`; datasets are variants in series, like TP3's `train_dataset` variants.

### Anti-Pattern 3: Hard-coded summary columns in the sweep runner
**What people do:** Copy TP3's `RunSummary` (MSE, accuracy, epochs) and bolt Kohonen fields on.
**Why it's wrong:** Three models, three metric sets; every new metric becomes a sweep.py edit.
**Do this instead:** C writes `metrics.json`; sweep takes the union of keys.

### Anti-Pattern 4: Comparing SOM weight grids across seeds
**What people do:** Average U-matrices or weights over seeds to "reduce variance".
**Why it's wrong:** Different seeds give rotated/mirrored/permuted maps; averaging destroys structure.
**Do this instead:** Compare via assignments (co-membership of creators, adjusted Rand) and via scalar metrics (QE, TE, empty units); pick one representative seed for the interpretation figures and say so.

### Anti-Pattern 5: Persisting the QR weight matrix
**What people do:** `weights.csv` for every Hopfield run.
**Why it's wrong:** 1.87M entries, ~30 MB of text per run, times hundreds of sweep runs.
**Do this instead:** `save_weights` only for letters (25 x 25); for QR the weights are reproducible from `qr.csv` in one line (`W = P^T P`, zero diagonal) if Python needs them.

### Anti-Pattern 6: Floating-point Hopfield fields with a tie rule
**What people do:** `w_ij = (1/N) sum xi xi` in doubles and test `h == 0` for "stay".
**Why it's wrong:** Summation order (and TP3's `-fassociative-math`) can turn an exact 0 into 1e-17, flipping a neuron and changing trajectories between builds.
**Do this instead:** Integer W (sum of products), integer fields, tie rule on exact integers.

### Anti-Pattern 7: Oja on uncentered data
**What people do:** Feed min-max scaled data to Oja and compare with PC1.
**Why it's wrong:** The rule then converges to the dominant direction of the uncentered second-moment matrix (mostly the mean), not PC1; the "index" is a size effect.
**Do this instead:** z-score (centered) dataset for Oja; warn in C if not centered; if min-max is used for Kohonen, give Oja a separate centered variant.

### Anti-Pattern 8: Building the slides and informe only at the end
**What people do:** Do all analysis, then draw figures in one push.
**Why it's wrong:** Figure code written late has no tests against real outputs; narrative gaps show up when it is too late to rerun series.
**Do this instead:** Each analysis phase also emits its figure fragments and a paragraph in the outline; the final phase assembles, not creates.

## Scaling Considerations

The data is tiny; what "scales" here is experiment count, not data volume.

| Concern | Small (one run) | Sweep (hundreds of runs) | Heavy (QR noise grid) |
|---------|----------------|--------------------------|----------------------|
| Kohonen 49 x ~31, k <= ~12 | ms | 5 grid sizes x 4 radii x 4 etas x 20 seeds = 1,600 runs, minutes with `--workers` all cores | n/a |
| Oja | ms | trivial | n/a |
| Hopfield letters (N = 25) | ms | capacity sweeps (random_count 1..10, 200 trials each) seconds | n/a |
| Hopfield QR (N = 1369) | ~0.1 ms per field computation (measured) | 5 targets x 10 noise levels x 100 trials = 5,000 trials, order of seconds to a minute (estimate from the measured field cost) | keep traces opt-in; states.csv for 3 traced trials x ~10 steps x 1369 ints is ~40 KB |

First bottleneck: number of run directories (thousands of tiny dirs) and plotly HTML size, not CPU. Mitigation: `trace_trials` default 0, one `plotly.min.js` per figure folder (TP3's `include_plotlyjs="directory"`), optional `--prune` of per-run CSVs after summary extraction. Second: Hopfield async at large N, solved by incremental local fields.

## Integration Points

### External Services

None. Everything runs locally; Artifacts (slides, informe) are published by the assistant from files in `deliverables/`.

| Tool | Integration Pattern | Notes |
|------|---------------------|-------|
| gcc + make | `neuron/Makefile` | Apple clang 21 is what `gcc` resolves to on this machine; TP3 flags work there |
| Python 3.12 | system `python3` | numpy, plotly, Pillow are NOT installed in the system interpreter (checked); create `.venv` and `pip install -r analysis/requirements.txt` in the foundation phase. `sweep.py` and the slide renderers stay stdlib-only like TP3 |
| QR decoding (optional) | Python-side check that a recovered 37x37 pattern still decodes (OpenCV `QRCodeDetector` or pyzbar, after adding a quiet zone and upscaling) | NOT verified; LOW confidence on library choice and on whether the module matrix decodes without a spike. Treat as an optional differentiator closing the story's "send it to a QR reader" loop |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| prepare scripts -> C core | CSV + meta JSON files in `neuron/data/` | C ignores meta files; names/ids are Python-side only |
| sweep.py -> C binary | subprocess, config path in, `results -> dir` on stdout, exit code | Same as TP3; failures recorded per run, series continues |
| C core -> analysis | files only (CSV/JSON) | No shared code, no FFI |
| analysis -> figures | figure-data functions return plain dicts/arrays; two renderers consume them | One source of numbers per figure |
| PCA (Python) <-> Oja (C) | `pca.py` output (eigenvectors, scores) vs `weights.csv` / `index.csv` | The only place where a Python result is the gold standard for a C result |

## Suggested Build Order (dependencies)

```
Foundation (rng, config, matrix, results, dispatch, Makefile, tests, venv, sweep generalization, plots_style)
   |
   +--> Ex1 track:  EDA/PCA (Python only, can start immediately, needs only venv)
   |                   |
   |                   v
   |               prepare_creators (features decided) --> Kohonen core --> Kohonen sweeps/analysis ---+
   |                                                    \-> Oja core ----> Oja vs PC1 ----------------+--> campaign decisions
   |
   +--> Ex2 track:  prepare_letters --> Hopfield core (sync, async, energy, noise) --> letters analysis (orthogonality, capacity, spurious)
                                         \--> prepare_qr --> QR noise sweeps --> QR analysis + limitations
                                                                                          |
 Deliverables (slides, informe): outlines and fragments emitted per phase; assembly last <-+
```

Order implications for the roadmap:

1. **Foundation first, and it must include the end-to-end loop on a trivial model.** Prove config -> run dir -> `metrics.json` -> sweep -> `summary.csv` -> one plotly figure before writing three algorithms. Everything else depends on this contract; changing it later touches every module.
2. **EDA/PCA can run in parallel with the C foundation** (pure Python on `creadores.csv`). Its decisions (which features, which transforms) gate `prepare_creators` and therefore the first *meaningful* Kohonen run, but the Kohonen core can be built and tested earlier on an all-features z-scored placeholder dataset.
3. **Kohonen before Oja:** Kohonen needs the most config surface and the most analysis; Oja is a ~50-line module whose value is the comparison with PCA, which already exists by then.
4. **Campaign decisions come after Kohonen, Oja and PCA** (they consume all three), and are Python-only.
5. **Hopfield is independent of Ex 1** and can be scheduled before, after or interleaved; do **letters before QR** (the enunciado recommends it, and letters validate the invariants: orthogonal patterns exactly stable, energy non-increasing under async, negative of a stored pattern is also an attractor, 2-cycles under sync).
6. **Slides/informe are the last phase, but their inputs are produced earlier** (Anti-Pattern 8).

Invariant tests worth writing alongside each core (cheap, catch most bugs): Kohonen with `grid_k = 1` gives QE = mean distance to the single prototype and TE = 0; radius/eta schedules hit their endpoints; Oja on a synthetic 2-D covariance with a known leading eigenvector converges to it (sign-aligned); Oja norm tends to 1; Hopfield W symmetric with zero diagonal; stored orthogonal patterns are fixed points; async energy never increases; same seed gives byte-identical `trials.csv`.

## Decisions to confirm in phase planning

| Decision | Recommendation | Why it may be revisited |
|----------|----------------|------------------------|
| Core directory name | Keep `neuron/` (PROJECT.md) | `core/` is clearer for a Kohonen binary, but changes nothing functionally |
| Commit `neuron/data/*.csv` | Yes (tiny, deterministic) | TP3 gitignored its data; here a committed 14 KB `qr.csv` makes the C core runnable and reviewable without Python |
| Grid shape | Square k x k, rectangular topology, 4- or 8-neighborhood | Course slides also show hexagonal; adds neighbor-definition complexity for little interpretive gain |
| PNG decoding | Pillow in `prepare_qr.py` (it is a one-shot script) | Stdlib `zlib` decoding of 8-bit gray non-interlaced PNG is ~30 lines if avoiding a dependency is preferred (verified feasible: all five files decode with filters 0/1/2/4) |
| pandas | Do not add | 49 x 31 matrix; numpy + stdlib `csv` are enough and plotly `graph_objects` does not need it |

## Sources

- TP3 source read directly (HIGH): `/Users/gonzalocuri/Documents/dev/repos/SIA/SIA-TPs/TP3/neuron/{main.c,rng.c,Makefile,io/config.c,io/results.c,io/dataset.h}`, `analysis/{sweep.py,plots_style.py,README.md,plots_data.py,sweep_report.py}`, `scripts/{prepare_digits_dataset.py,report_server.py}`
- Enunciado `docs/Archivo SIATP 42026.pdf` (HIGH): variables of `creadores.csv`, Kohonen/Oja/campaign questions, QR and letters requirements (5x5 +/-1, 4 letters, orthogonality, capacity, spurious state)
- Course slides `docs/Kohonen Model.pdf` (HIGH): k x k grid, step neighborhood R(i) -> 1, eta(i) -> 0, Euclidean/exponential similarity, sample init against dead units, standardization
- Course slides `docs/Modelo de Hopfield.pdf` (HIGH): synchronous update S(t+1) = sign(W S(t)), h = 0 keeps state, w_ii = 0, W = (1/N) sum xi xi
- Measured on `datos/hopfield/*.png` (HIGH): 37x37, 8-bit gray, values only 0/255, QR v5 module matrix with no quiet zone, pairwise overlaps 0.576 to 0.860
- Measured micro-benchmark (HIGH for this machine, not general): 1369 x 1369 int32 matrix-vector in ~0.11 ms at `-O3 -march=native`
- Environment check (HIGH): system Python 3.12.13 lacks numpy, plotly, Pillow; Apple clang 21
- Hopfield capacity ~0.138 N for random patterns and the pseudo-inverse rule: standard textbook results, not re-verified in this session (MEDIUM)
- QR decoding libraries for the optional check: unverified (LOW)

---
*Architecture research for: C core + Python analysis, unsupervised learning and associative memory (TP4 SIA)*
*Researched: 2026-10-20*
