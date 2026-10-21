# Phase 2: Kohonen SOM - Research

**Researched:** 2026-10-21
**Domain:** Self-organizing map in C (strict-config binary) + multi-seed sweep, leave-one-out and stability orchestration in Python (numpy/matplotlib only), written selection rule, U-matrix / hit map / component planes, PCA contrast
**Confidence:** HIGH on codebase integration, algorithm mechanics and Python metrics (read the sources, compiled and ran reference snippets this session); MEDIUM on schedule details left to discretion (R/sigma decay shape, stage-2 values, region rule)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Algoritmo y vecindad (C)**
- **D-01:** Vecindad configurable por clave en la config: **escalón del curso** (camino principal) y **gaussiana** (variante). Escalón: se actualizan las neuronas con distancia en la grilla `||n − n_k|| ≤ R(t)`, con `≤` (no el `<` estricto de las slides) para que R=1 actualice los 4 vecinos pegados y no solo la ganadora; R(0) configurable y decrece hasta 1 inclusive. Gaussiana: `h = exp(−d²/2σ²)` con σ decreciente y un piso > 0 (nunca 0). La regla de Kohonen es `W_j += η(t)·h_j·(x − W_j)` (h ∈ {0,1} en escalón). — **Reversibility:** costly — las claves de config, las series y el texto del informe dependen de los dos modos.
- **D-02:** η decrece **exponencialmente** de η0 a ηf: `η(t) = η0·(ηf/η0)^(t/T)`, con η0 < 1 y ηf en la config (baseline 0,5 → 0,01).
- **D-03:** Entrenamiento por **épocas barajadas**: cada época recorre los 50 creadores en un orden barajado con el `Rng` de la seed (splitmix64, Fase 1); T = épocas · n pasos. Baseline del orden del 500·N del curso (N = 26 ⇒ ~13 000 pasos ≈ 260 épocas).
- **D-04:** Adyacencia de **4 vecinos** (R=1 del curso) para el TE y para la matriz U. TE = fracción de creadores cuya primera y segunda BMU no son 4-vecinas. Matriz U = promedio de la distancia euclídea entre el prototipo de cada neurona y los de sus 4-vecinos (los bordes promedian los vecinos que existen).
- **D-05:** Inicialización con muestras del conjunto de entrenamiento (SOM-01, recomendación de las slides para evitar unidades muertas). Distancia euclídea sobre las 26 variables auditadas con z-score.

**Diseño del barrido**
- **D-06:** Barrido en **dos etapas**. Etapa 1: k ∈ {2,…,8} × vecindad ∈ {escalón, gaussiana} con un schedule baseline fijo (R0 ≈ k/2 o su equivalente σ0, η 0,5 → 0,01, ~260 épocas); la regla de D-10..D-14 elige k. Etapa 2: sobre la k elegida (vecindad escalón) se varían R0, η0 y épocas **de a uno** para mostrar que la elección es robusta. Las series usan `sweep.py` existente (`vary`/`values` o `variants` con varias claves). — **Reversibility:** reversible.
- **D-07:** Rango k = 2 a 8. Incluye grillas con más neuronas que creadores (8×8 = 64 > 50) a propósito: la curva debe mostrar que el QE baja siempre mientras la ocupación colapsa. Hay que **levantar el tope k² ≤ n** que tiene hoy `read_grid_k` en el stub.
- **D-08:** **10 seeds** por configuración; se reporta media ± desvío, no la mejor seed.
- **D-09:** QE leave-one-out calculado **en Python** como k-fold con **k = n = 50** (LOO exacto, cumple SOM-03 tal como está escrito): por cada seed y configuración, 50 entrenamientos con un creador excluido y la distancia del excluido a su BMU; QE-LOO = promedio. El binario de C no gana un modo LOO; Python arma los CSV de entrenamiento y orquesta las corridas.

**Regla de elección de grilla (fijada antes de ver resultados)**
- **D-10:** La regla se escribe en el fragmento de la Fase 2 (estilo `deliverables/01-datos-pca.md` §5) y se **commitea antes de correr el barrido de la etapa 1**; el commit es la evidencia de SOM-03. — **Reversibility:** one-way — una vez vistos los resultados, cambiar la regla invalida la afirmación "fijada de antemano" del informe.
- **D-11:** Forma = **filtros + desempate**, aplicada solo sobre las corridas con **vecindad escalón**; la gaussiana se reporta al lado como comparación y no participa de la elección.
  1. Se descartan las k con TE medio > 0,05 o con ocupación insuficiente (D-12).
  2. Entre las que quedan gana el **menor QE-LOO medio**.
  3. Si otra k sobreviviente está a menos de 1 desvío (entre seeds) del QE-LOO ganador, gana la **más estable entre seeds** (D-13); si siguen empatadas, la **k más chica**.
- **D-12:** Ocupación suficiente = las dos condiciones sobre la media entre seeds: **≤ 20 % de neuronas vacías** y **≥ 2 creadores por neurona ocupada** en promedio.
- **D-13:** Estabilidad entre seeds = para cada seed, matriz 50×50 de distancias en la grilla entre las BMU de cada par de creadores; estabilidad = promedio del **Spearman** entre las matrices de todos los pares de seeds (45 pares con 10 seeds). Invariante a rotación y reflexión del mapa, comparable entre k.
- **D-14:** Si ninguna k pasa los filtros: se **quita solo el filtro de TE**, se aplica el resto de la regla sin cambios y el informe dice explícitamente que ninguna grilla cumplió TE ≤ 0,05. La ocupación no se relaja nunca.
- **D-15:** QE (de entrenamiento) se reporta y se grafica contra k, pero no decide: el texto dice que por QE solo ganaría la grilla más grande (fuera de alcance en REQUIREMENTS: "Elegir la grilla del SOM por menor QE").

### Claude's Discretion
- Forma del decaimiento de R (escalón) y de σ (gaussiana) entre R0/σ0 y su final, mientras R termine en 1 y σ tenga piso > 0; nombres de las claves nuevas de la config y de `metrics.json` (validación estricta como en Fase 1 D-02).
- Traza por época (QE/TE contra época) para mostrar que el entrenamiento se aplanó: recomendada por la investigación, formato a criterio.
- Cómo obtiene Python la distancia del creador excluido en LOO (p. ej., leyendo `prototypes.csv` de la corrida y calculando la BMU en Python, o una entrada de test en C); el resultado debe ser el mismo.
- Valores concretos de la etapa 2 (R0, η0, épocas) y del baseline exacto, siempre que se fijen en la serie antes de correrla.
- Regiones y contraste con PCA (área no discutida): seguir `.planning/research/PITFALLS.md` Pitfall 6 — hit map + matriz U + planos juntos; perfiles con medias des-estandarizadas de los creadores asignados (unidades originales), marcando neuronas con < 2 miembros; contraste con PC1/PC2 cuantificado (p. ej., PC1/PC2 medios por neurona o proyección de los prototipos sobre el biplot), no a ojo; no afirmar que los temas "validan" los clusters (son entradas); seed fija para las figuras y la aclaración de que la orientación del mapa es arbitraria. Planos de las variables excluidas (en particular `topic_art_pct`) como promedio de la variable cruda por neurona (Fase 1 D-09).
- Corrida de sensibilidad con las 31 columnas para el SOM: opcional, solo si es barata; no entra a la regla.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope. (Grilla hexagonal ya figura como SOM-06 en v2.)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SOM-01 | SOM en C con grilla k×k, vecindad y η decrecientes, e inicialización con muestras | "C core specification" (config keys, schedule, init that wraps when k² > n, step/gaussian update, fp-safe radius clamp); reference loop compiled and timed |
| SOM-02 | El SOM reporta QE, TE y ocupación por neurona | "C core specification" outputs (`metrics.json` keys, `occupancy.csv`, `trace.csv`, `assignments.csv` with second BMU); Python recomputation test from `prototypes.csv` |
| SOM-03 | Barrido multi-seed con regla multicriterio fijada antes de ver resultados | "Selection rule: pre-registration checklist", "Sweep and LOO orchestration", tie-aware Spearman (existing `pca.spearman` is wrong for ties), arithmetic feasibility of D-12, commit guard |
| SOM-04 | Mapa de hits, matriz U y planos de componentes de la grilla elegida | "Figures" pattern: U-matrix from `prototypes.csv`, empty-neuron masking, raw-mean planes for excluded variables, shared colour scales, fixed figure seed |
| SOM-05 | Perfiles por región interpretados y contrastados con PC1/PC2; respuesta sobre distancia alta en la matriz U | "Profiles and PCA contrast" (orientation-invariant statistics: R² on grid coordinates, Mantel-type Spearman, edge-wise U vs ΔPC1, permutation nulls) |
</phase_requirements>

## Summary

The phase is mostly integration work on a codebase that already has every seam it needs. The C binary has a strict `KeySpec` config table, a sample-based prototype initializer, a lowest-index-wins BMU search, writers for `prototypes.csv` / `assignments.csv` / `metrics.json`, and a seeded splitmix64 `Rng` with `rng_shuffle`. Replacing the stub body means adding config rows, a training loop, TE/occupancy/trace outputs, and lifting the `k² ≤ n` cap. A compiled reference of the training loop (k = 8, 26 features, 13 000 steps) runs in about 18 ms, so the whole LOO design (about 7 000 short trainings) is minutes of wall time, not hours. The expensive part is not compute; it is process-spawn volume, results-directory hygiene and keeping the written selection rule honest.

Four things the planner would otherwise discover late. (1) `analysis/pca.py::spearman` ranks with `argsort(argsort())` and its own docstring says "no ties expected"; grid distance vectors are saturated with ties, so D-13 needs a new average-rank Spearman (verified against scipy this session) that returns NaN for a constant vector. (2) The rule's own arithmetic makes k ≥ 6 unable to pass D-12 (≥ 2 creators per occupied neuron needs ≤ 25 occupied neurons, ≤ 20 % empty needs ≥ 0.8 k² occupied, so k² ≤ 31.25), so the eligible set is effectively {2, 3, 4, 5} and k = 5 only passes if mean occupancy lands in [20, 25]; D-14's fallback only removes the TE filter, so the rule can still return "nothing eligible" and the text needs a sentence for that. (3) `results_create` gives a run directory a `_N` suffix when the same model+seed+second collides and stops at `MAX_DIR_ATTEMPTS 100`, so a LOO driver that fires thousands of same-seed runs from one working directory can hit the cap; run each LOO training in its own temporary working directory. (4) The environment on this machine has no `.venv`, no `datos/prepared/`, and no `uv`, so `make venv` as written fails; `python3.12` exists and the pinned requirements install fine into a plain venv.

The selection rule (D-10) must be committed before stage 1 runs, and several of its terms are ambiguous as written (whose standard deviation, which statistic enters the filters, how ties are broken, how to treat NaN stability). The checklist below lists each one so the planner can resolve them in the text that gets committed, not afterwards. I ran only mechanics-level checks on the real data (shapes, finiteness, hit counts summing to 50); I did **not** compute QE, TE, occupancy, LOO or stability per k, and nothing in this document is derived from those outcomes. The planner should not tune D-11..D-14 using any number from this file.

**Primary recommendation:** Tracer first: implement the C SOM (step neighborhood only) with the full output set and one Python recomputation test on one seed; then commit the written rule plus a pure `select_grid()` function with unit tests on synthetic summaries; only then run stage 1 behind a "rule file is committed and clean" guard.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| SOM training (init, schedules, update, BMU) | C binary (`neuron/models/kohonen.c`) | — | Course constraint: Kohonen is implemented by hand in C; seeded `Rng` lives there |
| QE / TE / occupancy of a run | C binary | Python recomputation (test only) | SOM-02 asks the run to report them; Python recomputes from CSVs as an independent cross-check |
| Per-epoch trace (QE, TE, eta, R) | C binary (`trace.csv`) | — | Only the binary sees the weights each epoch |
| Multi-seed stage 1 / stage 2 series | `analysis/sweep.py` (existing) | — | INFRA-03; `variants` handles k-dependent R0 |
| QE leave-one-out (50 folds x seed x config) | Python orchestrator | C binary (one training per fold) | D-09: no LOO mode in C |
| Seed stability (tie-aware Spearman of grid-distance matrices) | Python | — | Pure post-processing of `assignments.csv` |
| Grid selection rule (`select_grid`) | Python (pure function) | Written rule in `deliverables/` | Rule text is committed first; code encodes it verbatim |
| U-matrix, hit map, component planes, profiles | Python (numpy + matplotlib) | — | Visual/analytic layer over `prototypes.csv`, `assignments.csv`, scaler meta |
| PC1/PC2 contrast | Python (reuses `pca.py` scores) | — | Scores/orientation already defined in Phase 1 |
| Deliverable fragment | `deliverables/02-kohonen.md` (name [ASSUMED], mirrors `01-datos-pca.md`) | — | Rule written before results; results appended after |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| C11, system compiler (Apple clang 21.0.0 reported as `gcc`) | existing | SOM core | Existing build: `CFLAGS := -std=c11 -Wall -Wextra -Wpedantic -O2` [VERIFIED: neuron/Makefile] |
| cJSON (vendored) | existing | Config parsing | Phase 1 D-01; `KeySpec` tables already wrap it |
| numpy | 2.5.4 | LOO, stability, U-matrix, profiles, regression | Pinned in `analysis/requirements.txt`; installed OK in a scratch venv this session [VERIFIED: pip install in scratch venv] |
| matplotlib | 3.11.2 | Figures via `analysis/plots_style.py` | Pinned; Phase 1 D-06; installed OK in a scratch venv this session [VERIFIED: pip install in scratch venv] |
| pytest | 9.1.1 | Python tests | Pinned in requirements |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `analysis/sweep.py` | existing | Stage 1 and stage 2 series | Anything that is "variants x seeds" with `summary.csv` |
| `analysis/pca.py` (`scores`, `read_prepared`, `pca_eigh`) | existing | PC1/PC2 scores for the contrast | Reuse the sign convention; do **not** reuse its `spearman` |
| `scripts/creadores.py` (`load_creadores`, `scaler_from_meta`, `inverse_transform`) | existing | De-standardized profiles, raw excluded variables (`topic_art_pct`) | Profiles in original units |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Own tie-aware Spearman (about 12 lines) | scipy | D-06 limits the analysis stack to numpy + matplotlib; scipy would be a new dependency for one function. Hand-roll once, test against known values (checked against scipy this session, agreement to 1e-16) |
| Sweep through `sweep.py` for LOO | Own temp-dir driver | `sweep.py` would keep 7 000 run directories (est. 0.3-0.5 GB, my estimate) and share one `results/` cwd; own driver keeps only distances |

**Installation:** nothing new. `analysis/requirements.txt` already pins everything. No new packages are introduced, so the package-legitimacy gate has nothing to check.

**Version verification:** `numpy==2.5.4` and `matplotlib==3.11.2` resolved and imported in a fresh python3.12 venv this session (`numpy 2.5.4` printed). I also installed `scipy` and `pypdf` into that scratch venv for cross-checks and PDF reading only; neither is recommended for the project.

## Package Legitimacy Audit

No external packages are added by this phase (numpy, matplotlib, pytest are already pinned from Phase 1). Audit not applicable.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none new) | — | — | — | — | — | — |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
datos/creadores.csv --(make prepare, Phase 1)--> datos/prepared/creadores_zscore.csv (50x26) + .meta.json (scaler, ids, names)
                                                    |
          +-----------------------------------------+---------------------------+
          |                                         |                           |
   STAGE 1 series (sweep.py)                 LOO driver (Python)         fold CSVs (49 rows) written once
   14 variants x 10 seeds = 140 runs         per (config, seed, fold):   (drop row i)
          |                                  tmp cwd + config.json -> neuron
          v                                         |
   neuron/build/neuron  <------------------------- +   [C: init(samples) -> T = epochs*n shuffled steps ->
   config.json (strict KeySpec)                         BMU, h(d,R(t)|sigma(t)), W += eta(t)*h*(x-W) ->
          |                                             per-epoch trace -> final QE/TE/occupancy]
          v                                         |
   run dir: config.json, metrics.json,              v
   prototypes.csv, assignments.csv,          prototypes.csv only -> BMU of held-out creator (Python)
   occupancy.csv, trace.csv                         |
          |                                         v
          +--> summary.csv ----------> aggregate per (k, neighborhood): mean +/- sd over seeds of
          |                              QE, TE, empty fraction, creators/occupied, QE-LOO
          +--> assignments (row,col) -> 50x50 grid-distance vectors per seed -> tie-aware Spearman, 45 pairs -> stability
                                                    |
                              select_grid()  (step runs only; D-11..D-14; rule text committed BEFORE this runs)
                                                    |
                                          chosen k, selection.json (+ gaussian side-by-side table)
                                                    |
        STAGE 2 (sweep.py, one-at-a-time on chosen k, step): R0, eta0, epochs   ---> robustness table
                                                    |
        figure seed = pre-declared (max mean Spearman to the other seeds) -> run of chosen k
                                                    |
   hit map + U-matrix + component planes (26 trained + excluded raw means) + profiles (raw units) +
   PC1/PC2 contrast statistics + written answer on high U distance  ---> deliverables/02-kohonen.md
```

### Recommended Project Structure
```
neuron/
├── models/kohonen.c               # replaces kohonen_stub.c (git mv); keeps pick_prototypes/nearest/writers
├── io/config.c                    # KOHONEN_KEYS rows (+ per-neighborhood validation)
└── tests/test_main.c              # kohonen checks (see Validation Architecture)
analysis/
├── som.py                         # library: read_run, bmu/qe/te, umatrix, adjacency, average_ranks, spearman_ties, stability
├── som_loo.py                     # QE-LOO driver (own tmp cwd per training)
├── som_select.py                  # aggregate summary.csv + LOO + stability -> select_grid() -> selection.json
├── som_figures.py                 # hit map, U-matrix, component planes, profiles, PCA contrast
├── series_som_stage1.json         # committed with the rule, before it is run
├── series_som_stage2.json         # written after stage 1 (needs chosen k), committed before it is run
└── tests/test_som.py
deliverables/02-kohonen.md         # §rule first (commit), results later
```

### Pattern 1: C core specification (prescriptive)

**Config keys** (each is one more `KeySpec` row; unknown/missing/wrong-type aborts per Phase 1 D-02 and config.h: "Nothing falls back to a silent default"):

| Key | Type | Validation | Note |
|-----|------|-----------|------|
| `grid_k` | KEY_INT | 2 <= k <= 32 (sanity cap only; the old `k*k <= n` cap goes away, D-07) | already exists |
| `neighborhood` | KEY_STRING | `"step"` or `"gaussian"` | value must pass `is_plain` to appear in `metrics.json` (letters/digits/_ . -) |
| `radius0` | KEY_NUMBER | >= 1 | R(0) for step, sigma(0) for gaussian |
| `radius_final` | KEY_NUMBER | step: must be >= 1 (example 1); gaussian: > 0 (floor, never 0) | one pair of keys for both modes keeps the config strict without an optional `sigma_final` |
| `eta0` | KEY_NUMBER | 0 < eta0 < 1 | D-02 |
| `eta_final` | KEY_NUMBER | 0 < eta_final <= eta0 | D-02 |
| `epochs` | KEY_INT | >= 1 | D-03; T = epochs * n_rows |

Why one `radius_final`: the existing table API has no conditional requirement, and adding an always-required `sigma_final` that step mode ignores is a silent-ignore smell. Validation of the mode-dependent bound happens in `run_kohonen` before allocation, like `read_grid_k` does today.

**Initialization.** `pick_prototypes` as written reads `order[neuron]` for `neuron < n_neurons` over an `order` array of length `n_rows`; with k = 8 (64 neurons) on 50 rows it reads past the buffer. Fix: fill neuron `i` from a shuffle, and when `i` reaches `n_rows` draw a fresh shuffle (or use `order[i % n]`). Also needed for k = 7 in LOO (49 neurons, 49 rows is exactly enough; k = 8 is not). Duplicated initial prototypes are expected for k = 8 and are intentional (D-07); they diverge because their grid positions differ.

**Schedule** (f = step / (T - 1), so the last step lands exactly on the final values; T > 1 guaranteed because n >= 2 and epochs >= 1):
- `eta = eta0 * pow(eta_final / eta0, f)` (D-02)
- step R: `R = radius0 * pow(radius_final / radius0, f)` then **clamp `R = fmax(R, radius_final)`** (decay shape is discretion; exponential reaches the end value and is one line; linear `radius0 + (radius_final - radius0) * f` is equally valid). The clamp matters because `pow` can return 0.9999999999999999 at f = 1, and then `d <= R` silently excludes the 4 neighbors in the last steps.
- gaussian sigma: same formula with `radius_final` as the floor.
- Neighborhood test on **squared integer grid distance** `d2 = dr*dr + dc*dc`: step `d2 <= R*R + 1e-12`; gaussian `h = exp(-d2 / (2 sigma^2))`. With `<=`, R = 1 gives the winner plus the 4 adjacent cells; R in [sqrt 2, 2) also takes diagonals; k = 2 with `radius0 = 1` is a constant R = 1 schedule (fine, that is what D-06 "R0 ~ k/2" gives).

**Training order.** After the initialization shuffle, each epoch does `rng_shuffle` on a 0..n-1 order array and walks it. One shared `Rng`, so a seed fixes everything (D-03). Use the existing `nearest()` (lowest index wins ties) for the BMU.

**Final measures** (on the final prototypes, over the training set):
- `qe` = mean Euclidean distance sample-to-BMU (not squared; matches the stub's `mean_bmu_distance` and the numbers quoted in PITFALLS.md Pitfall 5). Keep the stub's name out of the summary to avoid two columns meaning the same.
- `te` = fraction of samples whose first and second BMU are **not** 4-adjacent: `|dr| + |dc| != 1`. Second BMU = second-smallest distance, lowest index on ties. Diagonal neighbors count as errors (D-04). Note for k = 2: diagonal neurons are not 4-adjacent, so TE can be above 0 even on a faithful 2 x 2 map.
- occupancy: `occupied_neurons`, `empty_fraction = 1 - occupied/k²`, `mean_hits_occupied = n / occupied` (guard `occupied > 0`), `max_hits`, `singleton_neurons`.

**Outputs.** Keep `prototypes.csv` (neuron,row,col,features) and `assignments.csv` (add a `bmu2` column; keep sample,bmu,row,col,distance); add `occupancy.csv` (neuron,row,col,hits) so SOM-02's "ocupación por neurona" is in a CSV, and `trace.csv` (epoch,eta,radius,qe,te) with epoch 0 = initial state. `metrics.json` keys, all plain tokens: `model, seed, n_samples, n_features, grid_k, n_neurons, neighborhood, epochs, radius0, radius_final, eta0, eta_final, qe, te, occupied_neurons, empty_fraction, mean_hits_occupied, max_hits, singleton_neurons`. `sweep.py` takes `summary.csv` columns from these keys, and the varied keys that duplicate metric keys are not repeated. `METRICS_COUNT` is a fixed array size in the stub and must be updated with the list.

**U-matrix** is computed in Python from `prototypes.csv` (one implementation, D-04 definition, tested against a hand-computed 2 x 2); C keeps TE and occupancy.

### Pattern 2: Reference C training loop (compiled and timed this session)

```c
// Source: reference written and compiled for this research (scratchpad bench.c), -O2, k = 8, 26 features,
// 50 samples, 260 epochs: 0.018 s. The planner's version replaces the demo order and adds outputs.
int T = epochs * n;                              // total steps
for (int ep = 0, step = 0; ep < epochs; ep++) {
  rng_shuffle(rng, order, n);
  for (int s = 0; s < n; s++, step++) {
    double f   = T > 1 ? (double) step / (T - 1) : 1.0;
    double eta = eta0 * pow(eta_final / eta0, f);
    double R   = fmax(radius0 * pow(radius_final / radius0, f), radius_final);   // clamp: fp can land below 1
    const double * x = input->data + (size_t) order[s] * n_cols;
    double dist; int bmu = nearest(x, W, n_neurons, n_cols, &dist);
    int br = bmu / k, bc = bmu % k;
    for (int u = 0; u < n_neurons; u++) {
      int dr = u / k - br, dc = u % k - bc, d2 = dr * dr + dc * dc;
      double h = step_mode ? (d2 <= R * R + 1e-12 ? 1.0 : 0.0) : exp(-d2 / (2.0 * R * R));
      if (h == 0.0) continue;
      for (int j = 0; j < n_cols; j++) W[(size_t) u * n_cols + j] += eta * h * (x[j] - W[(size_t) u * n_cols + j]);
    }
  }
  /* trace row: eta, R, qe, te of the current W over all samples */
}
```

### Pattern 3: Sweep design with `sweep.py` (stage 1)

`vary`/`values` cannot express "R0 depends on k", so use `variants` (supported: `{"label", "set"}`, several keys each, labels become run-directory slugs). Base config is the updated `neuron/config.json.kohonen.example`; `seeds` is `[1..10]`; paths are relative to `neuron/` as today.

```json
{
  "_comment": "Stage 1: k x neighborhood, fixed baseline schedule (D-06). Rule in deliverables/02-kohonen.md is committed before this runs.",
  "base_config": "../neuron/config.json.kohonen.example",
  "seeds": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
  "variants": [
    {"label": "k2_step",     "set": {"grid_k": 2, "neighborhood": "step",     "radius0": 1.0, "radius_final": 1.0}},
    {"label": "k3_step",     "set": {"grid_k": 3, "neighborhood": "step",     "radius0": 1.5, "radius_final": 1.0}},
    {"label": "k3_gaussian", "set": {"grid_k": 3, "neighborhood": "gaussian", "radius0": 1.5, "radius_final": 0.5}}
  ]
}
```
(complete with k = 4..8 and both neighborhoods: 14 variants x 10 seeds = 140 runs; R0 = sigma0 = max(1, k/2). `radius_final` 0.5 for gaussian is [ASSUMED], see A2.) Stage 2 is one `variants` list where every variant changes exactly one of `radius0`, `eta0`, `epochs` away from the baseline; its values can only be written after the chosen k is known, so that file is committed after stage 1 and before stage 2 runs. Suggested ladders (discretion, [ASSUMED]): `radius0` in {max(1, k/4), k/2, k}, `eta0` in {0.1, 0.25, 0.5, 0.9}, `epochs` in {50, 130, 260, 520, 1040}.

### Pattern 4: LOO driver (D-09)

Per configuration x seed x fold: write `config.json` into a fresh temporary directory, run `neuron/build/neuron config.json` with that directory as `cwd` (argument list, no shell, as `sweep.py` does), read `results/*/prototypes.csv`, compute the held-out creator's nearest-prototype distance in Python, delete the directory. Reasons: (a) `results_create` names dirs `results/<timestamp>_<model>_seed<N>` and retries `_2.._100`; same model and seed within one second collide, and thousands of same-seed folds from one cwd can exceed `MAX_DIR_ATTEMPTS 100` [VERIFIED: neuron/io/results.c:12 `#define MAX_DIR_ATTEMPTS 100`]; (b) it avoids keeping about 7 000 run folders. Write the 50 fold CSVs (header + 49 rows, same 26 columns, `%.17g`) once and share them across all configs and seeds. Each fold uses the same `seed` value as its full-data run; the epochs setting stays the same, so T differs slightly (49 vs 50 per epoch), which should be stated. Parallelize with `ThreadPoolExecutor` like `sweep.py`. Cost: 7 (k) x 2 (neighborhoods) x 10 (seeds) x 50 (folds) = 7 000 trainings; at roughly 20-30 ms plus spawn that is a few minutes on this 10-core machine (my estimate from the 18 ms worst-case benchmark). Computing LOO for the gaussian too is cheap and gives the side-by-side comparison D-11 wants; the rule only reads the step rows.

Caveat to write in the deliverable: the z-score scaler was fit on all 50 creators, so the held-out creator's coordinates were standardized with a mean/std that include itself. It is a mild leak, acceptable, but it must be stated.

### Pattern 5: Verified Python metrics (all run this session against scipy / invariance checks)

```python
# Source: written and executed for this research; spearman_ties agrees with scipy.stats.spearmanr to 1e-16,
# average_ranks equals scipy.stats.rankdata, stability is exactly 1.0 under 90-degree rotation and reflection
# of the grid, and a constant vector returns NaN.
import numpy as np

def average_ranks(v):
    v = np.asarray(v, dtype=float)
    order = np.argsort(v, kind="stable"); sv = v[order]
    new = np.r_[True, sv[1:] != sv[:-1]]
    group = np.cumsum(new) - 1
    first = np.flatnonzero(new); last = np.r_[first[1:], len(v)] - 1
    mean_rank = (first + last) / 2.0 + 1.0
    ranks = np.empty(len(v)); ranks[order] = mean_rank[group]
    return ranks

def spearman_ties(a, b):
    ra, rb = average_ranks(a), average_ranks(b)
    ra -= ra.mean(); rb -= rb.mean()
    den = np.sqrt((ra @ ra) * (rb @ rb))
    return float("nan") if den == 0 else float(ra @ rb / den)

def grid_distance_vector(bmu, k):               # upper triangle of the 50x50 matrix: 1225 values
    r, c = bmu // k, bmu % k
    d = np.hypot(r[:, None] - r[None, :], c[:, None] - c[None, :])
    return d[np.triu_indices(len(bmu), 1)]

def stability(bmus_by_seed, k):                  # mean over the 45 seed pairs; skip NaN pairs explicitly
    v = [grid_distance_vector(b, k) for b in bmus_by_seed]
    vals = [spearman_ties(v[i], v[j]) for i in range(len(v)) for j in range(i + 1, len(v))]
    return float(np.nanmean(vals)), int(np.isnan(vals).sum())

def metrics_from_prototypes(X, protos, k):       # independent recomputation of the C measures
    d = np.linalg.norm(X[:, None, :] - protos[None, :, :], axis=2)
    order = np.argsort(d, axis=1, kind="stable") # lowest index wins ties, like nearest() in C
    b1, b2 = order[:, 0], order[:, 1]
    qe = d[np.arange(len(X)), b1].mean()
    te = 1.0 - ((np.abs(b1 // k - b2 // k) + np.abs(b1 % k - b2 % k)) == 1).mean()
    return qe, te, np.bincount(b1, minlength=k * k), b1

def umatrix(protos, k):                          # D-04: mean distance to existing 4-neighbors
    W = protos.reshape(k, k, -1); U = np.zeros((k, k))
    for r in range(k):
        for c in range(k):
            ds = [np.linalg.norm(W[r, c] - W[r + dr, c + dc]) for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))
                  if 0 <= r + dr < k and 0 <= c + dc < k]
            U[r, c] = np.mean(ds)
    return U
```

### Pattern 6: Selection rule: pre-registration checklist

The text committed under D-10 must pin each term below, because each is currently open to two readings:

1. **Unit of the filters.** Per-seed value, then mean over the 10 seeds (D-12 says "media entre seeds"). `creators per occupied neuron` = per-seed `50 / occupied`, then averaged (not `50 / mean(occupied)`; the two differ by Jensen). State which.
2. **Whose "desvío" in D-11 step 3.** Recommend: the sample SD (ddof = 1) across seeds of the **winner's** QE-LOO, where each seed contributes its own mean over the 50 folds. Candidates: every survivor `k'` with `QE_LOO(k') - QE_LOO(winner) < SD(winner)`; the winner is in the set; among the set the highest mean stability wins; only if stabilities are exactly equal does the smaller k win.
3. **NaN stability.** If every creator lands on one neuron in some seed, the distance vector is constant and Spearman is NaN. Define: pairs with NaN are dropped from the mean and their count is reported; if all are NaN, stability = 0 for that k.
4. **TE filter** compares the seed-mean TE to 0.05 with `>` (a k with mean TE exactly 0.05 survives).
5. **Fallback (D-14)** removes only the TE filter; the text must also say what happens if the occupancy filter alone leaves nothing: report "no eligible grid", do not relax it (D-14 forbids relaxing occupancy), and name the pre-declared fallback decision (planner/user must choose now; this is an open question below).
6. **Figure seed.** Pre-declare how the seed for the deliverable figures is picked: recommend "the seed with the highest mean Spearman to the other nine on the chosen k" (a medoid by D-13, not by QE), so nobody can say it was cherry-picked.
7. **Arithmetic consequence to state openly.** D-12 needs `occupied <= 25` (>= 2 per occupied) and `occupied >= 0.8 k²` (<= 20 % empty). Both hold only if `k² <= 31.25`, so k >= 6 cannot pass D-12 and k = 5 passes only with mean occupied in [20, 25]. Pure arithmetic, no results involved [VERIFIED: arithmetic from D-12]. The text should say the 6-8 rows exist to draw the QE / occupancy curve (D-07), not to compete.
8. **Guard.** The stage-1 driver records `git rev-parse HEAD` and refuses to run if `git status --porcelain deliverables/02-kohonen.md analysis/series_som_stage1.json` is non-empty or the file has no commit: this makes "committed before looking" mechanical.

### Pattern 7: Profiles and the PCA contrast (SOM-05)

Figures: hit map with creator handles or counts, U-matrix, and component planes together (PITFALLS.md Pitfall 6). All colour scales full range (U-matrix not truncated), same scale across compared panels, seed and config in each caption, an explicit note that orientation is arbitrary. Mask neurons with 0 hits (hatch or grey), because a ridge in the U-matrix between empty neurons is interpolation, not a boundary.

Planes: for the 26 trained variables show the prototype component (z units, diverging colormap centered at 0, `plots_style.DIVERGING`); for dropped variables (`topic_art_pct`, `content_showcase_pct`, and the three exact-dependency columns if wanted) plot the **mean raw value of the creators assigned to each neuron** (Phase 1 D-09), empty neurons NaN. Pick 8-10 key planes for the main figure and put the rest in an appendix grid.

Profiles: per occupied neuron and per region: n creators (flag < 2), raw-unit means via `scaler_from_meta` / `inverse_transform` or directly from `datos/creadores.csv`, dominant topic share using all four raw topic columns (descriptive only, never "validation": topics are inputs). A **region rule must also be written before looking at the map** (discretion area). Recommended: regions = connected components of occupied neurons under 4-adjacency after cutting every edge whose prototype distance exceeds the 75th percentile of all 4-adjacent prototype distances; regions with < 2 creators are labelled "not interpretable". The 75th percentile is [ASSUMED].

PCA contrast, all orientation-invariant (the grid can be rotated/reflected between seeds):
1. R² of PC1 and PC2 scores regressed on `[1, row, col]` of each creator's BMU (R² is unchanged by any invertible affine map of the regressors, hence by grid rotation/reflection). Compare to a permutation null (shuffle BMU assignments among creators, 1 000 permutations) so a small-n coincidence is visible.
2. Mantel-type tie-aware Spearman between the 1 225-pair grid-distance vector and the 1 225-pair distance vector in the (PC1, PC2) plane; same permutation null (permute creator labels on one side). Add the same statistic against the full 26-D z-distance as a reference ceiling.
3. Edge-wise U vs PCA: for each pair of 4-adjacent occupied neurons, Spearman between prototype distance (U-edge) and |difference of neuron-mean PC1| and of PC2. This answers "does a high U distance coincide with a PC1/PC2 gap?" with a number.
4. For the written answer "qué indica una distancia alta entre neuronas vecinas": high U = adjacent prototypes far apart in the 26-D space, i.e. a boundary between dissimilar profiles; low = homogeneous region (Kohonen slides: "Si el método funciona entonces deberían observarse distancias pequeñas" inside a region) [CITED: docs/Kohonen Model.pdf p.36]. Support it with the top-3 variables that differ across the highest-U edges (difference of the two prototypes in raw units), and add the caveat that walls next to empty neurons are interpolation.
Where the SOM and PC1/PC2 disagree, report it; a nonlinear map can legitimately separate what PC1/PC2 mix (PC1 is 53.2 % and PC1+PC2 61.7 % of variance [CITED: deliverables/01-datos-pca.md §6]).

### Anti-Patterns to Avoid
- **Choosing k by lowest QE** (out of scope in REQUIREMENTS; D-15). QE is plotted against k and the text says QE alone would pick the largest grid.
- **Reporting the best seed** (D-08): mean +/- SD only; figure seed is chosen by the pre-declared stability medoid rule.
- **Reusing `pca.spearman` for D-13** (ties, see Pitfall 1).
- **Describing a region from 1-2 members** or naming "premium zone" from singletons.
- **Declaring that the SOM "coincides" with the biplot by eye**, or that clusters "validate" topics.
- **Silent defaults for the new config keys** (breaks Phase 1 D-02).
- **A sigma that can reach 0** (`radius_final > 0` validated for gaussian).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON config parsing/validation | A new parser or ad-hoc `getenv`/argv flags | cJSON + `KeySpec` rows + `config_get_*` | Strict validation and error messages already exist and are tested |
| RNG / shuffling | `rand()` or a second generator | `Rng` + `rng_shuffle` (splitmix64) | Same seed => same bytes is a Phase 1 test |
| CSV / metrics output | `fprintf` of tables in the model | `results_write_table`, `results_write_metrics` | `%.17g` round trip, no timestamps, `is_plain` key check |
| Multi-seed sweeps | A bespoke loop for stage 1/2 | `analysis/sweep.py` `variants` | `summary.csv`, workers, deterministic layout |
| Figure style / save | Per-figure rcParams | `plots_style.apply_style`, `save_figure`, `palette_for`, `DIVERGING` | Deterministic SVG (fixed hash salt, no date) |
| PCA scores / sign convention | Re-running eigendecomposition with another orientation | `pca.pca_eigh`, `pca.scores`, `orient` convention (or read `analysis/results/pca/audited/scores.csv`) | PC1/PC2 must carry the Phase 1 sign convention |
| De-standardization | Re-implementing mean/std | `creadores.scaler_from_meta`, `inverse_transform` | One scaler, ddof = 1, in the meta file |
| Spearman with ties | `argsort(argsort())` ranks | `average_ranks` + `spearman_ties` (Pattern 5), written once in `analysis/som.py`, tested | The existing helper is wrong with ties; scipy is not in the pinned stack |

**Key insight:** The only things that really must be written are the SOM update loop, the tie-aware rank correlation, and the rule. Everything else is wiring existing seams; a hand-built variant of those seams risks breaking the byte-identical-rerun guarantee.

## Runtime State Inventory

Not a rename/refactor/migration phase (greenfield replacement of a stub). Omitted by the template's rule. Stubs consumers to update: `neuron/config.json.kohonen.example`, `analysis/series_smoke_kohonen.json` (it varies `grid_k` over [2, 3, 4], still valid once the example has the new keys), the Kohonen cases in `neuron/tests/test_main.c` (lines 206, 215, 217 and 306-308), `neuron/README.md` (config table, test description), `neuron/models/models.h` comment, and the `analysis/README.md` series table row.

## Common Pitfalls

### Pitfall 1: Spearman with ties silently wrong
**What goes wrong:** `analysis/pca.py::spearman` is `argsort(argsort())` and its docstring says "no ties expected" [VERIFIED: analysis/pca.py:168 `"""Pearson correlation of the ranks (argsort of argsort; no ties expected)."""`]. Grid distances take few distinct values (for k = 2 only 0, 1 and sqrt 2), so ties are the norm and tied ranks would be assigned by array order, making the stability depend on creator order.
**How to avoid:** `average_ranks` (Pattern 5). Test it against a hand-checked tied example (`[1,1,1,2,2,3]` must rank `[2,2,2,4.5,4.5,6]`) and with a constant vector (NaN).
**Warning signs:** stability exactly 1.0 for small k, or different values after permuting creator order.

### Pitfall 2: Selection rule changed after seeing results
**What goes wrong:** D-10 is one-way: edits after the sweep void the "fijada de antemano" claim.
**How to avoid:** commit the rule text plus `select_grid()` plus tests on synthetic summaries first; the stage-1 driver refuses to run with a dirty or uncommitted rule file; the deliverable cites the commit hash.
**Warning signs:** `git log` shows the rule file modified after the sweep directory's timestamp.

### Pitfall 3: Radius floating-point undershoot
**What goes wrong:** `R = R0 * pow(1/R0, f)` can equal 0.9999999999999999 at the end; with `d2 <= R*R` the four neighbors drop out in the last steps and the final map is trained as winner-take-all.
**How to avoid:** `fmax(R, radius_final)` and an epsilon on the comparison; unit test that the last row of `trace.csv` has `radius == radius_final` and that at R = 1 a winner's four neighbors are updated.

### Pitfall 4: Prototype init overflows when k² > n
**What goes wrong:** `pick_prototypes` indexes `order[neuron]` with `neuron` up to k²-1 over an array of length n. With the cap lifted for k = 8 (64 > 50, and 64 > 49 in LOO) this is a heap read overflow.
**How to avoid:** refill from a fresh shuffle each time the index passes n (or `% n`); a C test with k = 3 on the 6-row fixture (9 neurons > 6 rows) and `make debug` (ASan/UBSan) over it.

### Pitfall 5: Run-directory collisions and volume in LOO
**What goes wrong:** same model + seed within one second get `_2`, `_3`, ... and then fail after 100 [VERIFIED: neuron/io/results.c:12,25 `#define MAX_DIR_ATTEMPTS 100`, `for (int attempt = 1; attempt <= MAX_DIR_ATTEMPTS; attempt++)`].
**How to avoid:** one temp cwd per training; delete after reading `prototypes.csv`. Stage 1 through `sweep.py` is fine (at most 14 same-seed runs per second).

### Pitfall 6: "More creators per neuron" read from the wrong denominator
**What goes wrong:** dividing 50 by k² (all neurons) instead of by occupied neurons; or averaging the ratio of means instead of the mean of per-seed ratios.
**How to avoid:** the metric is `n / occupied_neurons` per seed (guard occupied > 0), then mean across seeds; the rule text says so (checklist item 1).

### Pitfall 7: QE-LOO not comparable to QE
**What goes wrong:** QE-LOO uses a map trained on 49 creators and measures one held-out distance; its mean over folds and over seeds is not the same quantity as training QE. SD for the tie band must come from per-seed LOO means, not from the 500 raw fold distances.
**How to avoid:** aggregate fold -> seed -> config, in that order, and label both columns.

### Pitfall 8: Empty-neuron walls and orientation
**What goes wrong:** interpreting U-matrix ridges between empty or singleton neurons as cluster boundaries; comparing "top-left" across seeds.
**How to avoid:** mask zero-hit neurons, flag < 2-member neurons, state arbitrary orientation, use the pre-declared figure seed, and use orientation-invariant statistics for the PCA contrast.

### Pitfall 9: Environment is not ready on this machine
**What goes wrong:** `make` fails at `make venv` because `uv` is not on PATH [VERIFIED: `uv not found`, no `.venv`, no `datos/prepared/` in the working tree this session; Makefile line 32-33 call `$(UV)`].
**How to avoid:** executors run `/opt/homebrew/bin/python3.12 -m venv .venv && .venv/bin/pip install -r analysis/requirements.txt && touch .venv/.installed`, then `make prepare`; or install uv. I confirmed the pinned versions install under python3.12 in a scratch venv.

### Pitfall 10: Strict config makes the old stub tests and smoke series fail
**What goes wrong:** every Kohonen config now needs the new required keys; `test_main.c` lines 206, 306-308 and the smoke series' base config break until updated.
**How to avoid:** update the example config first and the tests in the same task as the key rows.

## Code Examples

### Config rows (shape; names are discretion)
```c
// Source: pattern of neuron/io/config.c KOHONEN_KEYS (read this session); new rows are the only change
static const KeySpec KOHONEN_KEYS[] = {
  { "grid_k",       KEY_INT,    1, NULL },
  { "neighborhood", KEY_STRING, 1, NULL },
  { "radius0",      KEY_NUMBER, 1, NULL },
  { "radius_final", KEY_NUMBER, 1, NULL },
  { "eta0",         KEY_NUMBER, 1, NULL },
  { "eta_final",    KEY_NUMBER, 1, NULL },
  { "epochs",       KEY_INT,    1, NULL },
  { NULL, KEY_INT, 0, NULL },
};
```
The existing stub had `{ "grid_k", KEY_INT, 1, NULL }` at config.c:21 [VERIFIED: neuron/io/config.c:20-23].

### Baseline example config (updated `neuron/config.json.kohonen.example`)
```json
{
  "model": "kohonen",
  "seed": 1,
  "input": "../datos/prepared/creadores_zscore.csv",
  "grid_k": 4,
  "neighborhood": "step",
  "radius0": 2.0,
  "radius_final": 1.0,
  "eta0": 0.5,
  "eta_final": 0.01,
  "epochs": 260
}
```
Current example content, for reference: `"model": "kohonen"`, `"seed": 1`, `"input": "../datos/prepared/creadores_zscore.csv"`, `"grid_k": 3` [VERIFIED: neuron/config.json.kohonen.example]. 260 epochs x 50 = 13 000 steps = 500 x 26 variables (D-03).

### Existing-code facts the C task depends on
- `read_grid_k` caps k via `integer_sqrt(n_samples)` [VERIFIED: neuron/models/kohonen_stub.c:15-31] and the stub's `METRICS_COUNT` is `#define METRICS_COUNT 8` [VERIFIED: neuron/models/kohonen_stub.c:11].
- `nearest()` "the lowest index wins a tie" comment at the function head [VERIFIED: neuron/models/kohonen_stub.c, "Index of the prototype closest to sample; the lowest index wins a tie"].
- `models.c` dispatch row: `{ "kohonen", run_kohonen }` [VERIFIED: neuron/models/models.c], so renaming the file needs no dispatch change as long as `run_kohonen` keeps its signature; the Makefile compiles `$(wildcard ... models/*.c)` [VERIFIED: neuron/Makefile `SOURCES`], so a renamed file is picked up automatically.
- `Results`/`Metric` limits: keys and text values only letters, digits, `_ . -`; non-finite numbers are written as `null` [VERIFIED: neuron/io/results.h].

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pick SOM grid by lowest QE or by the elbow | Multi-criterion rule with a held-out estimate (here LOO QE), topographic error, occupancy and seed stability | This project, D-10..D-15 | QE alone always prefers the biggest map (50 samples) |
| `<` (strict) radius in course slides | `<=` so R = 1 updates the 4 neighbors | CONTEXT D-01 | Resolves the slide ambiguity noted in STATE.md; document it in the deliverable |

**Deprecated/outdated:** nothing relevant; hexagonal grid is SOM-06 (v2).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Exponential decay of R and sigma (same form as eta) is an acceptable discretion choice; linear is equivalent for the purpose | Pattern 1 | Low: only affects ordering behavior, both end at the required values |
| A2 | Gaussian `radius_final = 0.5` (sigma floor) and `radius0 = max(1, k/2)` | Pattern 3 | Medium: floor of 0.5 is the lower end of PITFALLS.md's 0.5-1 range; neighbor weight at d = 1 is exp(-2) = 0.135. User may prefer 1.0 for closer parity with the step mode |
| A3 | Stage-2 ladders: R0 {max(1,k/4), k/2, k}, eta0 {0.1,0.25,0.5,0.9}, epochs {50,130,260,520,1040} | Pattern 3 | Low: discretion item, must be fixed in the series file before running |
| A4 | Region rule: cut 4-adjacent edges above the 75th percentile of prototype distances, components with < 2 creators not interpretable | Pattern 7 | Medium: the cut-off is arbitrary; it must be fixed before looking at the map. Alternative is to describe regions only from the U-matrix visually, which is less defensible |
| A5 | Deliverable file name `deliverables/02-kohonen.md` and module names `som*.py` | Project structure | Low |
| A6 | LOO wall time is "a few minutes" on this machine | Pattern 4 | Low: derived from one 18 ms benchmark with synthetic data, plus an assumed spawn overhead; the real number is measured on first run |
| A7 | LOO for the gaussian is worth running although the rule ignores it | Pattern 4 | Low: cost is the same order as step; skipping halves the runs |
| A8 | Per-run disk use of about 0.3-0.5 GB if LOO went through `sweep.py` | Alternatives | Low: only motivates the custom driver |
| A9 | 8-10 key component planes in the main figure, rest in an appendix grid | Pattern 7 | Low |

## Open Questions

1. **What is the pre-declared outcome if D-12 leaves no eligible k?**
   - What we know: D-14 removes only the TE filter and never relaxes occupancy. By arithmetic, eligible k are limited to {2,3,4,5}; k = 2 and 3 have 12.5 and 5.6 creators per neuron, so the occupancy filter will almost surely admit them, and "nothing eligible" is unlikely but not impossible.
   - What's unclear: the text does not say what the report does in that case.
   - Recommendation: write one sentence in the rule: "if no k passes occupancy, the chosen grid is the largest k whose mean empty fraction is <= 20 % regardless of creators per neuron, and the report says so", or declare a hard stop. User/planner decision before the commit.
2. **Stage-2 requires the chosen k, so its series file cannot be written up front.** Recommendation: commit `series_som_stage2.json` after stage 1 and before running it; the plan should have that as an explicit step.
3. **Should the figure seed come from the stage-1 seeds 1-10?** Recommendation: yes, the stability medoid among those 10 on the chosen k (rule item 6), so figures need no extra runs.
4. **Optional 31-column sensitivity run for the SOM** (discretion): the existing `creadores_zscore_all31.csv` works with the same binary; one extra series on the chosen k is cheap. Not part of the rule. Recommend skipping unless time remains.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| C compiler (`gcc` is Apple clang) | binary, tests | yes | Apple clang 21.0.0 | — |
| GNU Make | build, targets | yes | 3.81 (Makefile is written for it) | — |
| python3.12 | `.venv`, analysis | yes | /opt/homebrew/bin/python3.12 | — |
| system python3 | `sweep.py` (stdlib only) | yes | 3.9.6 | — |
| uv | `make venv` | **no** | — | `python3.12 -m venv .venv` + `pip install -r analysis/requirements.txt` + `touch .venv/.installed` |
| `.venv` | all analysis, `make test` | **no** (not created in this checkout) | — | create as above |
| `datos/prepared/` | binary input, tests | **no** (generated, git-ignored) | — | `make prepare` after the venv exists |
| numpy / matplotlib | analysis | no globally; pinned versions install | 2.5.4 / 3.11.2 verified in scratch venv | venv |
| CPU cores | LOO/sweep workers | yes | 10 | — |
| poppler (`pdftoppm`) | reading PDFs with the Read tool | no | — | `pypdf` in a scratch venv (used for research only) |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** `uv`, `.venv`, `datos/prepared/` (all recreatable; first task of the phase should be environment bring-up).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | C: dependency-free `check()`/`check_close()` in `neuron/tests/test_main.c`; Python: pytest 9.1.1 |
| Config file | none (pytest default; `analysis/tests/conftest.py` puts `analysis` and `scripts` on `sys.path`) |
| Quick run command | `make -C neuron test-c` (C only, reads `tests/fixtures`) |
| Full suite command | `make test` (from `TP4/`; needs `.venv` and `datos/prepared/`) ; `make -C neuron debug` for ASan/UBSan |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SOM-01 | Config validation of the new keys (missing, wrong type, bad `neighborhood`, `radius_final` bound per mode, `eta0 >= 1`) | C unit | `make -C neuron test-c` | extend `test_main.c` (Wave 0) |
| SOM-01 | k² > n init does not overflow (k = 3 on the 6-row fixture); k = 8 on 50 rows runs | C unit + ASan | `make -C neuron debug` | Wave 0 |
| SOM-01 | eta and R endpoints in `trace.csv` (first = eta0/radius0, last = eta_final/radius_final); step R = 1 updates exactly the 4 neighbors | C unit | `make -C neuron test-c` | Wave 0 |
| SOM-01/02 | Same seed => identical bytes (all new CSVs and metrics); seed+1 changes `prototypes.csv` | C unit (reuse `same_seed_same_bytes`) | `make -C neuron test-c` | update existing case lines 306-308 |
| SOM-02 | `metrics.json` qe/te/occupied/empty_fraction equal Python recomputation from `prototypes.csv` + input (tolerance 1e-12) | pytest integration (runs the binary in a tmp dir) | `.venv/bin/python -m pytest analysis/tests/test_som.py -q -k recompute` | Wave 0 |
| SOM-02 | `occupancy.csv` hits sum to n; hits match `assignments.csv` counts | pytest | same | Wave 0 |
| SOM-03 | `average_ranks`/`spearman_ties` on tied example, constant vector, scipy-checked constants; stability = 1.0 under rotation/reflection | pytest | `-k stability` | Wave 0 |
| SOM-03 | `select_grid()` on synthetic summaries: TE filter, occupancy filter (both conditions), tie band picks most stable, smaller-k tie, D-14 fallback, no-eligible case | pytest | `-k select` | Wave 0 |
| SOM-03 | Rule file committed before stage 1: driver aborts on dirty/uncommitted rule file | pytest (tmp git repo) | `-k guard` | Wave 0 |
| SOM-03 | LOO driver on the 6-row fixture: 6 folds, distances finite, no leftover run dirs | pytest | `-k loo` | Wave 0 |
| SOM-04 | U-matrix on a hand-computed 2 x 2 (edge cells average only existing neighbors); figures written, non-empty, deterministic SVG on rerun | pytest | `-k umatrix`, `-k figures` | Wave 0 |
| SOM-05 | R² on grid coordinates is invariant to grid rotation/reflection; permutation null seeded | pytest | `-k pca_contrast` | Wave 0 |
| SOM-05 | Written answer and region profiles exist in the deliverable | manual (checkpoint, human_verify_mode end-of-phase) | read `deliverables/02-kohonen.md` | manual |

### Sampling Rate
- **Per task commit:** `make -C neuron test-c` for C tasks; `.venv/bin/python -m pytest analysis/tests/test_som.py -q` for Python tasks
- **Per wave merge:** `make test` plus `make -C neuron debug`
- **Phase gate:** full suite green, a same-seed `diff -r` of two single runs clean, and a one-seed smoke of stage 1 before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `neuron/tests/test_main.c` additions for the Kohonen checks above (existing file; kohonen cases need the new keys)
- [ ] `analysis/tests/test_som.py` (covers SOM-02..05 helpers) and a tiny fixture of tied/constant vectors
- [ ] Environment bring-up (`.venv`, `make prepare`) since this checkout has none

## Security Domain

`security_enforcement` is enabled (absent = enabled), ASVS level 1.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | local CLI, no accounts |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | Strict `KeySpec` validation of every new key (type, range, enum for `neighborhood`); `matrix_load` validates the CSV; sanity cap on `grid_k` before allocation |
| V6 Cryptography | no | — |
| V12 Files/Resources | yes | Run dir names go through `is_plain`; LOO driver uses `tempfile` directories, never user-provided names; subprocess via argument list, no shell |

### Known Threat Patterns for C binary + Python orchestration

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Heap overflow from k² > n in init or from an unchecked `grid_k` | Tampering / DoS | Fresh-shuffle refill, cap `grid_k`, `size_t` arithmetic as in the stub, run `make debug` (ASan/UBSan) |
| Integer overflow in `epochs * n` | DoS | compute `T` as `long long`, reject epochs above a documented cap |
| NaN/inf from `eta`, sigma or empty-neuron division | Integrity | validate ranges up front; `results_write_metrics` already writes non-finite as `null`; guard `occupied > 0` |
| Command injection from config-derived strings in LOO | Elevation | `subprocess.run([...])` with a list, `cwd` a temp directory, no `shell=True` (same call shape as `sweep.py`) |
| Path traversal via variant labels | Tampering | `Task.name` slugs labels to `[A-Za-z0-9.-]` (sweep.py); keep labels plain |

## Sources

### Primary (HIGH confidence)
- Repository sources read this session: `neuron/models/kohonen_stub.c`, `neuron/io/config.c/.h`, `neuron/io/results.c/.h`, `neuron/io/matrix.h`, `neuron/rng.c/.h`, `neuron/main.c`, `neuron/Makefile`, `neuron/tests/test_main.c`, `analysis/sweep.py`, `analysis/pca.py`, `analysis/plots_style.py`, `analysis/README.md`, `scripts/creadores.py`, `Makefile`, `deliverables/01-datos-pca.md`
- `docs/Kohonen Model.pdf` (text extracted with pypdf): pp. 15 (R = 1 for 4 neighbors, sqrt 2 for 8), 24-27 (init, `Nk(i) = {n / ||n - nk|| < R(i)}`, R(0) given, R -> 1, eta(i) -> 0, e.g. 1/i, update rule), 30-31 (init with samples against dead units, 500*N iterations, R(0) up to the grid size), 36-37 (U-matrix, single-variable plane)
- `docs/Archivo SIATP 42026.pdf` p. 3: Kohonen task text, including "¿Qué indica una distancia alta entre neuronas vecinas en la matriz U?" and "¿Coinciden con los perfiles observados en la PC1 y PC2 (biplot)?"
- Executed this session in a scratch venv (python3.12, numpy 2.5.4, matplotlib 3.11.2, scipy for cross-check only): tie-aware Spearman vs scipy, rotation/reflection invariance, constant-vector NaN, 64-neuron init on 50 rows, hit counts sum to 50; compiled C training-loop benchmark (0.018 s worst case)

### Secondary (MEDIUM confidence)
- `.planning/research/PITFALLS.md` Pitfalls 5, 6, 7 (earlier measured research; its figures are quoted from there, not reproduced here)

### Tertiary (LOW confidence)
- None used.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH, nothing new; versions pinned and installed this session
- Architecture: HIGH for C integration points and Python metrics (read, compiled, executed); MEDIUM for the region rule and stage-2 ladders (discretion, flagged as A3/A4)
- Pitfalls: HIGH for items 1-5, 9, 10 (verified in source or by execution); MEDIUM for 6-8 (derived from the rule text)

**Disclosure on results:** I ran no per-k statistics (QE, TE, occupancy, LOO, stability) on the real data. The only real-data checks were mechanical (shape, finiteness, hits sum to n). Nothing here should be used to adjust D-11..D-14.

**Research date:** 2026-10-21
**Valid until:** stable for the length of the phase (no external dependencies); revisit only if `neuron/io/config.c` or `sweep.py` change before planning.
