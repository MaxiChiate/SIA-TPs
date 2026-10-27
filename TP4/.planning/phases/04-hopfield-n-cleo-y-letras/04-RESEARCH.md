# Phase 4: Hopfield núcleo y letras - Research

**Researched:** 2026-10-23
**Domain:** Discrete Hopfield network (Hebb, integer W) in C, validated on 5x5 letters (N = 25); Python/numpy analysis layer with a pre-registered selection rule
**Confidence:** HIGH on the C core design, schemas and test strategy (all derived from code read this session and a working numpy/C prototype). MEDIUM on the experiment parameters (noise level, p range, trials), which are recommendations the planner/user confirm.

## User Constraints (from CONTEXT.md)

<user_constraints>

### Locked Decisions

**Alfabeto y bitmaps de letras**
- **D-01:** Se dibuja un **abecedario completo propio de 26 letras (A-Z) de 5×5** en un archivo de texto versionado y legible (una letra por bloque, filas con `*` = +1 y `.` = -1, en orden row-major), por ejemplo `datos/letters/alphabet_5x5.txt`. Un script de Python lo convierte a una matriz ±1 (una fila por letra, 25 columnas) que lee el binario de C. La **J del enunciado** (`docs/Archivo SIATP 42026.pdf`, §2.2) se transcribe tal cual y un pytest verifica que la codificación coincide con la matriz del enunciado (Pitfall 14). — **Reversibility:** costly — los solapamientos, la regla de selección de D-03, el barrido de capacidad y las figuras dependen de estos bitmaps. Una vez commiteada la regla, cambiar un bitmap obliga a rehacerla.
- **D-02:** El conversor valida que haya 26 letras, que cada una tenga exactamente 5 filas de 5 caracteres en `{*, .}` y que no haya dos letras idénticas. Falla con un error claro si algo no se cumple.

**Selección del set principal de 4 letras**
- **D-03:** Se muestran **dos sets de 4 letras lado a lado**: (a) el set **separado**, que es el subconjunto de 4 del alfabeto con **menor max |solapamiento|** fuera de la diagonal (solapamiento = ξ^a·ξ^b / N), y (b) el set **correlacionado**, el subconjunto con **mayor max |solapamiento|**, que se espera que falle y sirve para explicar el término de cruce. Las dos reglas, con un desempate escrito (por ejemplo, menor media de |solapamiento| y después orden alfabético), se evalúan sobre los C(26,4) = 14950 subconjuntos y dependen solo de los bitmaps, no de la red. El set separado es el "set principal" de la demo de recuperación y del estado espurio. Con N impar no existe ortogonalidad exacta (Pitfall 14b): se habla de "|solapamiento| chico".
- **D-04:** La regla de D-03 se **fija y se commitea antes de correr Hopfield**, con el mismo patrón de rigor de la F2 (D-10/D-14) y la F3 (D-07): el texto de la regla va en el fragmento de la fase (`deliverables/04-hopfield-letras.md` o similar) entre marcadores `<!-- regla:inicio -->`/`<!-- regla:fin -->`, y la guardia sha256 + commit (reusar `rule_digest`/`rule_guard` de `analysis/som_select.py`) impide que el script de letras corra si la regla cambió o no está commiteada. Antes del commit hay un checkpoint de decisión en el que el usuario aprueba el texto de la regla. Los bitmaps de D-01 entran en la guardia (por ejemplo, el digest incluye el archivo del alfabeto), para que tampoco se puedan retocar después de ver resultados. — **Reversibility:** one-way — una vez vistos los resultados de la red, cambiar la regla o los bitmaps invalida la afirmación "elegido de antemano".

**Capacidad y ortogonalidad**
- **D-05:** El análisis de capacidad es **exhaustivo para p = 4**: los 14950 subconjuntos de 4 letras se almacenan (Hebb, W entera) y para cada uno se mide la fracción de patrones que son puntos fijos estables (y, a un nivel de ruido fijo, la tasa de recuperación). Se grafica contra el max |solapamiento| del subconjunto. Para **p = 1..8** (o hasta donde la estabilidad caiga a ~0) se toma una **muestra al azar con seed** de subconjuntos por p y se grafica la fracción estable contra p, marcando 0,138N ≈ 3,45 **solo como orden de magnitud** (Pitfall 26), nunca como umbral.
- **D-06:** La matriz de solapamientos de 4×4 y el término de cruce de cada patrón se reportan para **los dos sets** de D-03, y además el histograma de max |solapamiento| sobre los 14950 sets de 4 ubica a ambos dentro de la distribución.

### Claude's Discretion

El usuario eligió discutir solo letras y alfabeto. Lo que sigue queda a criterio del researcher/planner, partiendo de los defaults de `.planning/research/PITFALLS.md` (Pitfalls 11, 12, 14 y 26):
- **Dinámica:** el modo asíncrono con una permutación aleatoria nueva por barrido (`Rng` de la seed) es la **referencia**, y el síncrono (`s = sign(W s)`, como el curso) queda como comparación etiquetada con detección de ciclos de período 2 (comparar con el estado en t-2). Si h_i = 0, la neurona mantiene su estado (así lo dice el curso). W entera = Σ ξξᵀ con diagonal 0 (el 1/N es opcional y no cambia la dinámica), con chequeo de simetría. La parada es un barrido completo sin cambios o un tope de barridos.
- **Energía e iteraciones:** E = -½ sᵀ W s. Se registra por actualización de neurona (asíncrono) y por paso (síncrono) en un CSV de traza, y se reportan las dos cuentas (actualizaciones y barridos). Hay un test de C que exige energía no creciente en el modo asíncrono (tolerancia 1e-9) y otro que recalcula E desde cero contra la versión incremental.
- **Clasificación del estado final:** se calculan los solapamientos m_μ = ξ^μ·s / N. El estado es "almacenado" si m = +1 para algún μ, "inverso" si m = -1, "mezcla" si coincide con sign(±ξ^a ± ξ^b ± ξ^c) para alguna terna (probado explícitamente) y "espurio (otro)" en cualquier otro caso. El vector de solapamientos se guarda siempre. El criterio de éxito de recuperación (match exacto vs |m| ≥ umbral) se fija antes de correr y se escribe en la regla de D-04.
- **Estado espurio (HOP-03):** se busca con consultas muy ruidosas sobre el set principal (por ejemplo, entre 40 % y 50 % de píxeles invertidos, con seeds barridas). Se guarda la seed y la consulta que lo producen, y se muestran el estado, sus solapamientos, su clasificación y la energía del espurio comparada con la de los almacenados.
- **Ruido y ensayos:** niveles de ruido, número de ensayos por nivel (al menos 30, alineado con HOP-05), 10 seeds como en F2/F3, claves exactas de config y de `metrics.json`, nombres de CSV y de targets del Makefile (por ejemplo `make letters`, `make hopfield-letters`), y figuras (letras, matriz de solapamientos, curvas de energía, recuperación vs ruido, capacidad).
- **Interfaz para la Fase 5:** el núcleo lee una matriz ±1 genérica (P × N) y no asume N = 25. La regla de pseudo-inversa puede dejarse prevista como valor de una clave `rule`, pero se implementa en la Fase 5.

### Deferred Ideas (OUT OF SCOPE)

None. La discusión no salió del alcance de la fase.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HOP-01 | Hopfield en C con W entera, actualización síncrona y asíncrona, energía por paso, detección de ciclos y clasificación del estado final | "C core design" (core API, incremental energy, async/sync loops, cycle detection, classifier), "Config keys", "Output schemas", C test list in Validation Architecture |
| HOP-02 | 4 letras de 5×5 almacenadas y recuperadas, con análisis de ortogonalidad y capacidad sobre varios subconjuntos de letras | "Alphabet, converter and the pre-registered rule", "Capacity task (exhaustive p = 4 in C, 0.9 s measured)", Pitfall 1 (tie-break), recall/noise design |
| HOP-03 | Un patrón muy ruidoso que converge a un estado espurio identificado y clasificado (inverso, mezcla u otro) | "Spurious-state search procedure", classifier + `states.csv`/`trace.csv`/`trials.csv`, measured spurious rates (mixture 37/120 and other 13/120 at 40 % noise) |
</phase_requirements>

## Summary

The phase is a pure-C-plus-numpy build with **no new third-party packages** (numpy 2.5.4, matplotlib 3.11.2, pytest 9.1.1 are already pinned in `analysis/requirements.txt`). The Hopfield stub (`neuron/models/hopfield_stub.c`) becomes a real network that follows the Kohonen structure: a pure core (train Hebb, fields, energy, async sweep, sync step, classifier) separate from a runner that owns config parsing and CSV writing, with strict `KeySpec` rows for every key. The core should keep W as `double` holding exact small integers (exact in IEEE doubles, so the `h == 0` tie rule is exact and Phase 5 keeps one interface); a test asserts every entry is integral, symmetric, and zero on the diagonal.

Two experiments were prototyped this session on a **draft** 5x5 alphabet (given below): the 14950-subset exhaustive capacity run takes **0.88 s in C at -O2** (including 30 noisy recalls per stored pattern), so it belongs in the C binary as a `capacity` task, with numpy recomputing the deterministic stability fraction independently (0.13 s) exactly like Phase 2 recomputed QE/TE. Async dynamics have strictly decreasing energy at every flip when ties keep the state (verified: assertion held over 1440 noisy trials), so cycles are impossible in async and only occur in sync (measured: 102/400 two-cycles at 30 % noise on the separated set).

**The most important finding for the plan is a trap in D-03.** Max |overlap| takes only multiples of 0.04 for N = 25, so ties are massive: on the draft alphabet 1326 of the 14950 sets share the maximum 0.84. The example tie-break in D-03 ("menor media de |solapamiento|") applied to the *correlated* rule picks the **least** correlated of those 1326 sets (GIPR), and that set is **fully stable** (all 4 letters are fixed points), contradicting "se espera que falle". A **mirrored** tie-break (higher sum of |overlap| for the correlated rule) picks HMNW, where only 1 of 4 letters is a fixed point. The rule text must state the tie-break for each of the two rules explicitly, compare in **integer dot products** (no float ties), and be approved by the user at the checkpoint with this trade-off in front of them.

**Primary recommendation:** Build `hopfield_core.[ch]` (pure, I/O-free) + `hopfield.c` runner with a `task` key (`recall` | `capacity`), per-trial deterministic CSVs (`trials.csv`, `trace.csv`, `states.csv`, `stored.csv`, `overlaps.csv`, `capacity.csv`), a pre-registered rule with integer-arithmetic selection and a guard that hashes the rule text **and** the alphabet file, and cross-check everything from the outputs in numpy (final state is a fixed point, energy recomputed, classification recomputed, stability fraction recomputed for all 14950 subsets).

## Architectural Responsibility Map

This is a C-binary + Python-analysis project, not a web stack, so the tiers are the project's own.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Hebb training, fields, energy, async/sync dynamics, cycle detection, classifier | C core (`neuron/models/hopfield_core.c`) | — | PROJECT.md: Hopfield implemented by hand in C, no library; Phase 5 reuses it unchanged |
| Per-trial noise, trial loops, capacity enumeration (14950 subsets), CSV/metrics writing | C runner (`neuron/models/hopfield.c`) | Python `sweep.py` for multi-seed | One run = one folder; deterministic from the seed; 0.88 s measured for the exhaustive run |
| Config validation (strict keys, ranges, subset indices) | C (`neuron/io/config.c` + runner `read_params`) | — | Established pattern: unknown/missing/mistyped key aborts before anything runs |
| Alphabet text -> ±1 matrix, validation (26 letters, 5x5, no duplicates), J check | Python (`scripts/`) | pytest | D-01/D-02; C only reads the CSV |
| Overlap matrix, set selection over 14950 subsets, rule guard (sha256 + commit) | Python (`analysis/hopfield_select.py`) | git | Depends only on bitmaps (D-03); guard reuses `som_select.rule_digest`/`rule_guard` |
| Independent recomputation (W, fixed-point check, energy, classification, stability) | Python numpy (`analysis/hopfield.py`) | pytest | Phase 2 pattern: C writes, numpy recomputes, tests compare |
| Figures (letters, overlap heatmaps, energy curves, recovery vs noise, capacity) | Python matplotlib (`analysis/hopfield_figures.py`) | `plots_style.py` | Same figure path as Phase 2 |
| Pre-registered rule text and results narrative | Versioned deliverable (`deliverables/04-hopfield-letras.md`) | — | Rule between `<!-- regla:inicio -->` / `<!-- regla:fin -->`, committed before results |

## Standard Stack

No new packages. Everything below is already in the repo.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| gcc / make | 13.3.0 / GNU Make 4.3 (Makefile claims 3.81 compatibility) | Build the C core | Existing toolchain [VERIFIED: `gcc --version`, `make --version` this session] |
| cJSON (vendored) | `neuron/vendor/cjson` | Config parsing | Already used by `config.c` |
| splitmix64 `Rng` | `neuron/rng.c` | Seeded noise and permutations | Reuse `rng_shuffle`, `rng_uniform`; never `rand()` |
| numpy | 2.5.4 (pinned) | Independent recomputation, selection over 14950 subsets | Already pinned in `analysis/requirements.txt` |
| matplotlib | 3.11.2 (pinned) | Static figures | Phase 1 decision D-06 |
| pytest | 9.1.1 (pinned) | Tests | Existing |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `analysis/sweep.py` | in repo | Multi-seed series -> `summary.csv` | Noise sweeps (10 seeds), capacity p sweep, sync vs async comparison |
| `analysis/som_select.py` `rule_digest`, `rule_guard` | in repo | Pre-registration guard | Letter-set rule (D-04); both functions take explicit paths so they are reusable as-is |
| `analysis/som.py` `run_binary`, `BINARY`, `RESULT_PREFIX` | in repo | Launch the binary from Python tests | Cross-check tests |
| `analysis/plots_style.py` | in repo | Palette and rcParams | Every figure |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Exhaustive capacity in C (`capacity` task) | numpy loop over 14950 subsets | numpy computes stability in 0.13 s but reimplementing the network's recall in numpy makes "Hopfield by hand in C" weaker and recall needs the RNG; C is 0.88 s including recall. Keep numpy as the independent check of the deterministic part only |
| `W` as `int` | `W` as `double` with integer values | Both exact. `double` keeps the Phase 5 interface (pseudo-inverse is non-integer) unchanged; a test enforces integrality for Hebb |
| One binary invocation per subset (14950 runs via `sweep.py`) | One `capacity` run writing `capacity.csv` | 14950 run directories and config copies for no benefit; one run per (p, seed) fits the one-run-one-folder convention |

**Installation:** none. `make venv` creates `.venv` from the pinned file (needs network once; see Environment Availability).

**Version verification:** `analysis/requirements.txt` read this session: `numpy==2.5.4`, `matplotlib==3.11.2`, `Pillow==13.0.0`, `pytest==9.1.1` [VERIFIED: analysis/requirements.txt]. No package is added in this phase.

## Package Legitimacy Audit

No external packages are installed or added in this phase, so the legitimacy gate has nothing to check. The pinned packages above were vetted in Phase 1 (plan 01-02).

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none added) | — | — | — | — | — | — |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
datos/letters/alphabet_5x5.txt  (versioned, A-Z, '*' = +1, '.' = -1)
        │  scripts/letters.py: validate 26 / 5x5 / {*,.} / no duplicates (and no inverses), J == statement
        ▼
datos/prepared/alphabet_pm1.csv (26 x 25, header p0..p24; generated, not versioned)
        │
        ├──► analysis/hopfield_select.py  (integer dots d_ab, 14950 subsets, tie rules)
        │         │  rule text in deliverables/04-hopfield-letras.md  + guard (rule + alphabet + select code + series)
        │         ▼
        │    separated set S, correlated set C, histogram of max|d|/N      [bitmaps only, no network]
        │
        ▼
neuron/build/neuron  config: model=hopfield, task=...
   ┌────────────────────────────────────────────────────────────────────────────┐
   │ task "recall":  subset ─► W = Hebb(subset)  (integer, zero diagonal)       │
   │    for pattern, level, trial: query = flip k=lround(level*N) pixels (Rng)  │
   │      async: fresh permutation per sweep, h kept incrementally,             │
   │             E += 2 s_i h_i on a flip, stop at a sweep with no change       │
   │      sync : s' = sign(W s) with ties keeping s; stop on s'==s or s'==s(t-1)│
   │      classify(final): stored / inverse / mixture(3 signs) / other          │
   │    ─► stored.csv overlaps.csv trials.csv trace.csv states.csv metrics.json │
   │ task "capacity": enumerate all C(M,p) subsets (n_subsets=0) or sample      │
   │    ─► stability, margin, recall rate per subset ─► capacity.csv metrics    │
   └────────────────────────────────────────────────────────────────────────────┘
        │  analysis/sweep.py (10 seeds) / analysis/hopfield_letters.py (guarded driver)
        ▼
analysis/results/hopfield/<series>/  ──► analysis/hopfield.py (numpy recompute) ──► tests
        │
        └──► analysis/hopfield_figures.py ──► deliverables/04-hopfield-letras.md (results sections)
```

### Recommended Project Structure
```
datos/letters/alphabet_5x5.txt          # D-01, versioned
scripts/letters.py                      # parse + validate + overlaps helper (importable, like creadores.py)
scripts/prepare_letters.py              # writes datos/prepared/alphabet_pm1.csv (+ .meta.json with names, sha256)
neuron/models/hopfield_core.h|.c        # pure functions, no I/O (HOP-01)
neuron/models/hopfield.c                # runner (git mv from hopfield_stub.c): params, tasks, writers
neuron/tests/test_main.c                # + test_hopfield_core, test_hopfield_run, test_hopfield_capacity
neuron/tests/fixtures/patterns_mix.csv  # small synthetic fixture independent of the real alphabet
analysis/hopfield_select.py             # rule as code (integer selection) + identity/guard
analysis/hopfield.py                    # run readers + independent numpy recomputation
analysis/hopfield_letters.py            # guarded driver: runs the series, writes selection.json etc.
analysis/hopfield_figures.py
analysis/series_hopfield_*.json         # committed in the rule commit (they are part of the registered design)
analysis/tests/test_letters.py, test_hopfield_select.py, test_hopfield.py, test_hopfield_figures.py
deliverables/04-hopfield-letras.md      # rule between markers, then results; "Cómo reproducir"
```

### Pattern 1: Pure core separated from the runner (as `kohonen.c` does)
**What:** `kohonen.c` keeps pure helpers (`kohonen_decay`, `kohonen_neighbor_weight`) exported through `models.h` for `tests/test_main.c`, and a runner (`run_kohonen`) that owns config, allocation and writers. Do the same: `hopfield_core.h` exposes train/field/energy/async/sync/classify; `test_main.c` calls them directly with tiny arrays.
**Example (the part that must be exactly right):**
```c
// Source: docs/Modelo de Hopfield.pdf slides 15 and 36-38 (h_i, keep-on-zero, H = -1/2 sum w s s,
// dH = 2 S_i sum w S < 0 when S_i flips). Design, not copied code.
// h[] = W s and *energy = -1/2 s^T W s are kept incrementally; w has zero diagonal, so a flip of i does not
// change h[i].
static int async_sweep(const double * w, int n, double * s, double * h, double * energy, int order[], Rng * rng,
                       int * flips /* out */) {
  rng_shuffle(rng, order, n);                      // fresh uniform permutation per sweep
  *flips = 0;
  for (int q = 0; q < n; q++) {
    int i = order[q];
    double hi = h[i];
    double next = hi > 0 ? 1.0 : hi < 0 ? -1.0 : s[i];   // tie keeps the state (course, slide 15)
    if (next != s[i]) {
      *energy += 2.0 * s[i] * hi;                  // strictly negative: s[i] * hi < 0 when it flips
      double delta = next - s[i];
      for (int j = 0; j < n; j++) h[j] += w[(size_t) j * n + i] * delta;
      s[i] = next;
      (*flips)++;
    }
    /* log one trace row per visit here: (trial, step, sweep, i, changed, *energy) */
  }
  return *flips;                                   // 0 => the whole sweep saw the same state: fixed point
}
```
A sweep with zero flips proves a fixed point (the state did not change during the sweep, so every `h_i` was evaluated on the same state).

### Pattern 2: Strict config with optional task-specific keys
**What:** `config.c` rows are `{name, type, required, children}`; `required = 0` is already supported by `config_validate_object`, but there is no "is the key present" helper and the typed getters print an error on a missing key. Add `config_has(const Config *, const char *)` (top-level `cJSON_HasObjectItem`) and in the runner reject keys of the other task (`"capacity" keys are not used by task "recall"`), so nothing is silently ignored.
**Config keys (all strict; CONFIG_KEYS_MAX = 32 leaves room, common 3 + 10):**

| Key | Type | Required | Notes |
|-----|------|----------|-------|
| `task` | string | yes | `"recall"` or `"capacity"` |
| `rule` | string | yes | only `"hebb"` accepted now; Phase 5 adds `"pinv"` as another accepted value, no table change |
| `update` | string | yes | `"async"` (reference) or `"sync"` (labelled comparison) |
| `max_sweeps` | int | yes | 1..10000; async cannot cycle (E strictly decreases at each flip), so the cap is a safety bound; sync counts steps |
| `trials` | int | yes | per (pattern, level); >= 1 |
| `noise_levels` | number array | yes (existing) | fractions in [0, 1]; flips `k = lround(level * N)`; the capacity task requires exactly one |
| `subset` | number array | recall only | distinct integer row indices into `input`, each in [0, n_rows); lets one binary read the 26-letter file or Phase 5's 5 QR |
| `trace_trials` | int | recall only | 0..`trials`: trials per (pattern, level) whose per-step trace and states are written |
| `p` | int | capacity only | 1..min(n_rows, 64) |
| `n_subsets` | int | capacity only | 0 = every C(n_rows, p) subset in lexicographic order; > 0 = that many random subsets drawn with the run's Rng |

[VERIFIED: neuron/io/config.h:17-18] `#define CONFIG_ARRAY_MAX 64     // most items of a number array` and `#define CONFIG_KEYS_MAX 32      // most rows of the table a config is validated against`.
[VERIFIED: neuron/io/config.c:40-42] the table today is `static const KeySpec HOPFIELD_KEYS[] = {` / `{ "noise_levels", KEY_NUMBER_ARRAY, 1, NULL },` / `{ NULL, KEY_INT, 0, NULL },`.

### Pattern 3: One run = one folder, per-trial deterministic CSVs
Reuse `results_write_table` (numeric `%.17g`, no timestamps) and `results_write_metrics` (flat). Strings cannot go in tables, so class names are numeric codes with the legend fixed in the rule/README: `0 stored, 1 inverse, 2 mixture, 3 other`. Python maps codes to names.

### Output schemas (recall task)
- `stored.csv`: `pattern, source_row, fixed, min_margin, wrong_pixels, energy` (one row per stored pattern; `min_margin = min_i xi_i * h_i`; `fixed = 1` iff every `xi_i * h_i >= 0`; `wrong_pixels = #{i : xi_i h_i < 0}`).
- `overlaps.csv`: `pattern, m_0..m_{P-1}` with `m = xi^a . xi^b / N` (exact: integer dot over N).
- `trials.csv` (one row per trial, order = pattern, then level, then trial index): `trial, pattern, source_row, noise, flipped, converged, sweeps, updates, flips, cycle, class, match_a, match_b, match_c, sign_a, sign_b, sign_c, correct, e_start, e_final, hamming_final, m_0..m_{P-1}`. `match_*` are indices into `subset` (-1 unused); stored/inverse use `match_a`/`sign_a`; a mixture uses all three. `correct = 1` iff `class == stored`, `match_a == pattern` and `converged` (exact match, see rule). `cycle` is 0 or the period (2).
- `trace.csv` (only trials with trial index < `trace_trials`): `trial, step, sweep, neuron, changed, energy`. Step 0 is the query (`neuron = -1`). Async: one row per neuron visit (including visits that do not change anything, where E repeats). Sync: one row per step (`neuron = -1`, `changed` = number of neurons that changed).
- `states.csv` (same trials): `trial, kind, s_0..s_{N-1}` with `kind` 0 = query, 1 = final. This is what lets HOP-03 "guardar la consulta" and lets numpy recompute everything.
- `metrics.json` (flat, values must satisfy `is_plain`): `model, seed, task, update, rule, n_patterns, n_neurons, n_levels, trials, stored_fixed, max_abs_overlap, recall_rate, wrong_stored_rate, inverse_rate, mixture_rate, other_rate, cycle_rate, mean_sweeps, mean_flips, energy_increases`. `energy_increases` is the C-side count of steps where E rose by more than 1e-9 in async mode; tests assert 0.

### Output schemas (capacity task)
- `capacity.csv`: `subset, idx_0..idx_{p-1}, max_abs_overlap, mean_abs_overlap, n_stable, stable_fraction, min_margin, recall_rate, mean_sweeps`.
- `metrics.json`: `model, seed, task, update, rule, n_neurons, p, n_subsets, noise, trials, mean_stable_fraction, all_stable_fraction, mean_recall_rate, mean_max_abs_overlap`.
- `stable_fraction` and `min_margin` do not depend on the seed; `recall_rate` does. Run the exhaustive p = 4 case with the 10 seeds and average `recall_rate` per subset in Python (1200 trials per subset, ~9 s total).

### Anti-Patterns to Avoid
- **One table row per neuron visit materialised up front:** `results_write_table` needs the whole `double[]` in memory. Use a growable buffer for `trace.csv` with a hard cap and a clear error, and keep `trace_trials` small for sweeps (the Phase 5 QR runs have N = 1369).
- **Judging success by energy or by "converged":** energy at a spurious state can be lower than at a stored one (PITFALLS 12c). Success is exact match to the source pattern.
- **Calling a "stored" outcome a success without checking which pattern:** on correlated sets a noisy query often ends in a *different* stored pattern (measured: 90 of 120 trials on HMNW at zero noise). Track `wrong_stored_rate` separately.
- **Floating-point overlap comparisons for the selection rule:** use integer dot products.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Random permutation per sweep, choosing which pixels to flip | A new shuffle | `rng_shuffle` (Fisher-Yates over `rng_uniform`) | Already deterministic and tested; `corrupt()` in the stub already does flips this way |
| JSON config parsing and type checks | Ad-hoc parsing | `KeySpec` rows in `config.c` + `config_get_*` | Strictness is a project decision (D-02 of Phase 1) |
| CSV in/out, metrics | `fprintf` of new formats | `matrix_load`, `results_write_table`, `results_write_metrics` | `%.17g`, no timestamps => `diff -r` clean |
| Multi-seed series and `summary.csv` | A bespoke loop | `analysis/sweep.py` with `vary`/`variants` | Handles strings (`update`) and lists |
| Pre-registration guard | A new hash/commit check | `som_select.rule_digest(path)` and `som_select.rule_guard(paths, repo_dir)` | Generic over paths; tested in Phase 2 |
| Subset enumeration in Python | Manual loops | `itertools.combinations(range(26), 4)` (lexicographic = the C order) | Order must match `capacity.csv` row order |
| Mixture detection | Clustering or "close to majority" heuristics | Explicit enumeration of `sign(±xi_a ± xi_b ± xi_c)` over triples | Odd count of ±1 terms never gives 0, so the sign is exact; cost 8·C(p,3)·N is trivial |

**Key insight:** every quantity here is an exact integer (W entries, fields, energies, dot products), so equality checks, tie rules and cross-checks against numpy can be exact. Introduce floats only for reported fractions.

## Alphabet, converter and the pre-registered rule

### Draft alphabet (for the user to approve or redraw at the checkpoint)
Verified this session: 26 distinct letters, no pair is an exact inverse, **J equals the statement matrix** [VERIFIED: numpy prototype]. The format is one block per letter (label line, five rows). **Disclosure:** stability and recall results were computed on this draft during research (below). If it is adopted unchanged, the deliverable must say the rule's tie-break was chosen with that knowledge; if the user redraws any letter, the numbers below no longer apply and the plan must not copy them as expected values.

```
A: .***. / *...* / ***** / *...* / *...*      B: ****. / *...* / ****. / *...* / ****.
C: .**** / *.... / *.... / *.... / .****      D: ****. / *...* / *...* / *...* / ****.
E: ***** / *.... / ****. / *.... / *****      F: ***** / *.... / ****. / *.... / *....
G: .**** / *.... / *..** / *...* / .***.      H: *...* / *...* / ***** / *...* / *...*
I: ***** / ..*.. / ..*.. / ..*.. / *****      J: ***** / ...*. / ...*. / *..*. / ***..
K: *...* / *..*. / ***.. / *..*. / *...*      L: *.... / *.... / *.... / *.... / *****
M: *...* / **.** / *.*.* / *...* / *...*      N: *...* / **..* / *.*.* / *..** / *...*
O: .***. / *...* / *...* / *...* / .***.      P: ****. / *...* / ****. / *.... / *....
Q: .***. / *...* / *.*.* / *..*. / .**.*      R: ****. / *...* / ****. / *..*. / *...*
S: .**** / *.... / .***. / ....* / ****.      T: ***** / ..*.. / ..*.. / ..*.. / ..*..
U: *...* / *...* / *...* / *...* / .***.      V: *...* / *...* / *...* / .*.*. / ..*..
W: *...* / *...* / *.*.* / **.** / *...*      X: *...* / .*.*. / ..*.. / .*.*. / *...*
Y: *...* / .*.*. / ..*.. / ..*.. / ..*..      Z: ***** / ...*. / ..*.. / .*... / *****
```
(`/` separates the five rows; the file itself uses one row per line and a blank line between letters.) The full file used in the prototype is at `/tmp/claude-1000/-home-mchiate-ITBA-2026-2Q-SIA-SIA-TPs/458160df-ec05-4327-91d1-478510ab1c19/scratchpad/alphabet_5x5.txt`.

### The J of the statement (transcribe exactly)
[VERIFIED: docs/Archivo SIATP 42026.pdf page 6, read as an image this session] The matrix is (rows top to bottom):
```
 1  1  1  1  1
-1 -1 -1  1 -1
-1 -1 -1  1 -1
 1 -1 -1  1 -1
 1  1  1 -1 -1
```
and the drawing under it is `* * * * *` / `. . . * .` / `. . . * .` / `* . . * .` / `* * * . .` (the vertical bar is in column 3, not 4). The pytest should hard-code this matrix and compare it with the converter's row for `J`, row-major, `*` = 1.

### Converter validation (D-02, plus two cheap additions)
Fail with a message naming the letter and line when: not exactly 26 blocks; a block is not 1 label + 5 rows; a row is not 5 characters in `{*, .}`; two letters identical. **Also reject** two letters where one is the exact negation of the other (they would be the same attractor; `overlap = -1`), and duplicate/missing labels. Tests: one failing fixture per rule, built in `tmp_path`.

### What the rule must pin down (all of it before the first Hopfield run)
Text goes between `<!-- regla:inicio -->` and `<!-- regla:fin -->` in `deliverables/04-hopfield-letras.md`. The items that were left open by CONTEXT and need a written value:
1. **Overlap definition in integers:** `d_ab = xi^a . xi^b` (odd integer for N = 25), `overlap = d_ab / 25`. All comparisons use the integer `|d_ab|` and integer sums.
2. **Set (a) separated:** minimise (max over the 6 pairs of `|d|`), then minimise the sum of the 6 `|d|`, then the lexicographically smallest index tuple.
3. **Set (b) correlated:** maximise (max `|d|`), then **maximise** the sum of the 6 `|d|` (mirrored tie-break), then the lexicographically smallest index tuple. See Pitfall 1 for why the non-mirrored version is wrong.
4. **Dynamics:** integer Hebb W, zero diagonal; tie keeps state; async reference with a fresh permutation per sweep; sync as labelled comparison; stop = a sweep (or step) with no change, `max_sweeps` cap; sync two-cycle = `s(t+1) == s(t-1)`, classified at the detection state.
5. **Success criterion:** exact match: `converged`, class stored and `match_a` equal to the source pattern. Overlap-threshold variants are reported only as secondary (the final overlap is in `trials.csv`).
6. **Noise operator:** exactly `k = lround(level * 25)` distinct pixels flipped, uniformly; note `lround(0.5 * 25) = 13` (> N/2), which is why plots stop at `k = 12` (0.48) or label 0.5 explicitly.
7. **Experiment parameters** (recommendations; see Assumptions): recovery levels `k = 0..12` (0, 0.04, ..., 0.48), 30 trials per (pattern, level), seeds 1..10; capacity noise level 0.12 (k = 3), 30 trials; sampled capacity `p = 1..12`, 200 random subsets per p, seeds 1..10; spurious search at levels 0.40, 0.44, 0.48, 100 trials per (pattern, level), all traced, one seed (1), re-run with another seed if no spurious state of a class appears.
8. **Spurious demo pick:** for each class present among {inverse, mixture, other}, the first trial in file order (pattern, level, trial) with that class; the config copy in the run folder is the seed record.
9. **Guarded files:** rule doc, `analysis/hopfield_select.py`, alphabet file, and every `analysis/series_hopfield_*.json`.

### Guard design (reuse, with one change)
`som_select.rule_digest(path)` hashes only the text between markers of **one** file, so the alphabet is not covered by it [VERIFIED: analysis/som_select.py:214-223] `def rule_digest(path) -> str:` / `"""sha256 of the text strictly between the two markers; the file needs exactly one of each."""`. Record separately `alphabet_sha256` (sha256 of the file bytes) in `selection.json`, include the alphabet in the `rule_guard` path list, and refuse to run when any recorded sha256 differs (the `som_stage.require_same_rule` pattern). Markers are the module constants [VERIFIED: analysis/som_select.py:34-35] `RULE_START = "<!-- regla:inicio -->"` and `RULE_END = "<!-- regla:fin -->"`.

Phase 2's `som_stage.rule_identity` demands that rule text, code and series were **added in one commit**. For Phase 4 the alphabet has to be approved (and tested) **before** the rule, so require instead: rule text, select code and series added in one commit (the rule commit); the alphabet commit must be an ancestor of (or equal to) the rule commit (`git merge-base --is-ancestor`); all four tracked and clean (`rule_guard`). `rule_guard` error text mentions Phase 2's "D-10"; wrap or accept the cosmetic mismatch. `som_stage._added_commit` is private; copy the 6-line helper rather than importing it.

## Common Pitfalls

### Pitfall 1: The correlated-set tie-break silently picks a *stable* set
**What goes wrong:** D-03(b) says "mayor max |solapamiento|" with the example tie-break "menor media". For N = 25 overlaps are multiples of 0.04 and the maximum is shared massively: on the draft alphabet the max is 0.84 and **1326 of 14950 sets tie** [VERIFIED: numpy prototype, draft alphabet]. Tie-break "lowest mean |overlap|" selects GIPR (mean 0.187): all 4 letters are fixed points. Tie-break "highest mean" selects HMNW (mean 0.733): 3 of 4 letters are **not** fixed points (stable fraction 0.25, min margin -34). Among the 1326 ties, stable fraction is 0 for 34 sets, 0.25 for 304, 0.5 for 526, 0.75 for 324 and 1.0 for 138, so the tie-break decides the story.
**Why it happens:** a single pair with |overlap| 0.84 is not enough to destabilise; instability needs the crosstalk of several patterns to accumulate. Mean |overlap| correlates with the minimum margin at -0.85, max |overlap| only at -0.65 [VERIFIED: numpy prototype, draft alphabet].
**How to avoid:** write the tie-break explicitly per rule (mirrored), compare integers, and show both options to the user at the checkpoint. If the user insists on the literal non-mirrored reading and the set turns out stable, report it as a finding (one highly similar pair is not sufficient to break recall), do not edit the rule.
**Warning signs:** the "correlated" set recalls perfectly; ties never mentioned in the rule text.

### Pitfall 2: Float ties in the selection
**What goes wrong:** `max|overlap|` and means computed in floating point can break exact ties differently across platforms/orderings.
**How to avoid:** compute `d = X @ X.T` as `int64`, compare `|d|` and integer sums; divide by 25 only for display. Test with a synthetic alphabet that has exact ties.

### Pitfall 3: Existing tests, config example and docs break the moment HOPFIELD_KEYS changes
**What goes wrong:** the strict config rejects a hopfield config with only `noise_levels`. These in-repo consumers must change in the same plan or `make test` fails: `neuron/tests/test_main.c` lines 209-210 and 221-222 (strict-validation cases) and 316-319 (`same_seed_same_bytes("hopfield", ..., NULL)`, whose comment says the Hopfield phases add a seed-dependent file: pass `"trials.csv"` now), `neuron/config.json.hopfield.example`, `analysis/series_smoke_hopfield.json`, `neuron/README.md` (lines 27, 73, 88, 94), `analysis/README.md:80`, and the stale stub comment in `neuron/models/models.h`. [VERIFIED: grep this session]

### Pitfall 4: "Iterations" and the stop test
**What goes wrong:** with a stop rule "a sweep with no change" every converging async run takes at least 2 sweeps (one that changes, one that confirms); "converged in 2 iterations" is a property of the stop test (PITFALLS 11c).
**How to avoid:** report `sweeps` (including the confirming one), `updates` (= visits = sweeps x N) and `flips` (actual sign changes) separately, and say which one the figures use.

### Pitfall 5: Cycles cannot happen in async
**What goes wrong:** claiming a cycle (or building a cycle test) in the async path. With symmetric W, zero diagonal and keep-on-tie, every flip has `ΔE = 2 s_i h_i < 0` strictly, so async always terminates; a cycle report in async would be a bug. Cycles belong to sync only (two-cycles; measured 102/400 at 30 % noise on the separated set, 0 on the correlated set) [VERIFIED: numpy prototype]. The sync two-cycle fact for symmetric W is the Goles-Olivos result [ASSUMED: training knowledge, not looked up this session].
**How to avoid:** the cycle test is an N = 2 case: store `xi = (1, -1)` so `W = [[0, -1], [-1, 0]]`; sync from `(1, 1)` alternates `(1,1) <-> (-1,-1)`; async from `(1, 1)` converges. Derived by hand this session.

### Pitfall 6: `h_i` is always even for N = 25, so ties are real
**What goes wrong:** each inner sum `sum_{j != i} xi_j s_j` has 24 terms, hence is even, so `h_i` is even and can be exactly 0 for any p. The tie rule is exercised by real data, not only by contrived cases. Overlaps `d_ab` are always odd (verified for all pairs of the draft alphabet), so exact orthogonality is impossible (PITFALLS 14b).
**How to avoid:** a C test with a constructed `h_i = 0` neuron; never write `sign(0)`.

### Pitfall 7: Stability margin has `N - p`, not `N`, as its signal
**What goes wrong:** with a zero diagonal, `xi_i^mu h_i(xi^mu) = (N - p) + sum_{nu != mu} xi_i^mu xi_i^nu d_{mu nu}` (derived this session from `w_ij = sum_nu xi_i^nu xi_j^nu`, `i != j`). Course slide 35 writes the signal as `xi_i/N` (diagonal included); the correction `-(p-1)` matters at N = 25 (signal 21 for p = 4, not 25). A pixel is unstable iff the cross term is below `-(N - p)`.
**How to avoid:** report `min_margin` (integer) in `stored.csv`/`capacity.csv` and, for D-06, the per-pattern cross term `sum_{nu != mu} xi_i^mu xi_i^nu d_{mu nu}` per pixel (numpy, from the bitmaps), so the explanation "why the correlated set fails" is numeric.

### Pitfall 8: Capacity reference value
**What goes wrong:** D-05 and PITFALLS 26 use 0.138N (3.45 for N = 25); the **course** slide 39 says "p ≤ 0,15 ∗ N" (3.75) [VERIFIED: docs/Modelo de Hopfield.pdf slide 39 read as image]. Report both as orders of magnitude, never as a threshold. Measured on the draft alphabet, letters degrade earlier than random patterns: mean stable fraction at p = 4 is 0.76 for letters vs 0.97 for random ±1 patterns of N = 25 [VERIFIED: numpy prototype]; letters are correlated, which is the point of Pitfall 14.

### Pitfall 9: Merge hot spots with Phase 3 (`dev-tp4`)
Phase 3 is still running on another branch. Files both phases touch: `neuron/io/config.c` (OJA_KEYS vs HOPFIELD_KEYS, different rows), `neuron/models/models.h`, `neuron/tests/test_main.c` (`tests[]` array and the dispatch test), root `Makefile` (`.PHONY` line and appended targets), `analysis/README.md`, `neuron/README.md`. Keep edits localized and append-only, add new targets instead of changing `prepare:`, and put every new Python module in new files (`hopfield_*.py`, `letters.py`). Do not edit any Phase 3 file.

### Pitfall 10: Trace volume
Async trace rows = visits = sweeps x N per traced trial. Fully traced spurious run: 4 patterns x 3 levels x 100 trials x ~75 visits ~ 90k rows, fine once; a 10-seed sweep must use `trace_trials` of 0 or 1. Cap the buffer and fail with a clear message.

### Pitfall 11: Sync "final state" of a two-cycle
A two-cycle has no single final state. Define it as the state at which the repeat was detected, set `cycle = 2`, `converged = 0`, `correct = 0`, and still classify it so the overlaps are recorded.

### Pitfall 12: Relative `input` paths in tests
Tests that run the binary from a temp directory must pass `input` as a path relative to that directory (`os.path.relpath`, as `analysis/tests/test_som.py` does) because `PATH_KEYS = ("input",)` is rewritten relative to the sweep dir by `sweep.py`.

## Code Examples

### Classifier (stored / inverse / mixture / other)
```c
// Source: design from PITFALLS 12 and CONTEXT "Clasificación del estado final". Order matters: stored, inverse,
// mixture, other. d = xi^mu . s is an exact integer in double; m = d / n is only for reporting.
typedef enum { CLASS_STORED = 0, CLASS_INVERSE = 1, CLASS_MIXTURE = 2, CLASS_OTHER = 3 } StateClass;

static StateClass classify(const double * patterns, int p, int n, const double * s, int match[3], int sign[3]) {
  match[0] = match[1] = match[2] = -1; sign[0] = sign[1] = sign[2] = 0;
  for (int a = 0; a < p; a++) {
    double d = dot(patterns + (size_t) a * n, s, n);
    if (d == n)  { match[0] = a; sign[0] =  1; return CLASS_STORED; }
    if (d == -n) { match[0] = a; sign[0] = -1; return CLASS_INVERSE; }
  }
  for (int a = 0; a < p; a++) for (int b = a + 1; b < p; b++) for (int c = b + 1; c < p; c++)
    for (int bits = 0; bits < 8; bits++) {
      int sa = bits & 1 ? -1 : 1, sb = bits & 2 ? -1 : 1, sc = bits & 4 ? -1 : 1;
      int equal = 1;
      for (int j = 0; j < n && equal; j++) {      // sum of three +-1 is odd: never 0, the sign is exact
        double v = sa * patterns[a * n + j] + sb * patterns[b * n + j] + sc * patterns[c * n + j];
        equal = (v > 0 ? 1.0 : -1.0) == s[j];
      }
      if (equal) { match[0] = a; match[1] = b; match[2] = c; sign[0] = sa; sign[1] = sb; sign[2] = sc; return CLASS_MIXTURE; }
    }
  return CLASS_OTHER;
}
```
Note `p >= 3` is needed for mixtures; with p < 3 the result is stored/inverse/other.

### Selection rule in integers (numpy)
```python
# Source: design; D-03 with explicit mirrored tie-breaks. d is int64 so every tie is exact.
import itertools, numpy as np

def select_sets(X: np.ndarray):                     # X: 26 x 25 of +-1 (int8/int64)
    d = (X.astype(np.int64) @ X.astype(np.int64).T)
    best = {"separated": None, "correlated": None}
    for combo in itertools.combinations(range(len(X)), 4):          # lexicographic
        pairs = [abs(int(d[a, b])) for a, b in itertools.combinations(combo, 2)]
        mx, total = max(pairs), sum(pairs)
        sep_key = (mx, total, combo)                                 # minimise all three
        cor_key = (-mx, -total, combo)                               # maximise mx and total, then smallest tuple
        if best["separated"] is None or sep_key < best["separated"][0]: best["separated"] = (sep_key, combo)
        if best["correlated"] is None or cor_key < best["correlated"][0]: best["correlated"] = (cor_key, combo)
    return best["separated"][1], best["correlated"][1]
```
On the draft alphabet this gives separated = (G, R, T, V) with max |overlap| 0.04 (unique) and correlated = (H, M, N, W) [VERIFIED: numpy prototype]. 14950 iterations of this loop run in well under a second.

### Independent numpy recomputation from a run directory (the cross-check)
```python
# Source: pattern of analysis/som.py (metrics_from_prototypes). No RNG replay is needed.
def hebb(P):                    # P: p x N int8 in {-1, 1}
    W = P.T.astype(np.int64) @ P.astype(np.int64); np.fill_diagonal(W, 0); return W

def energy(W, s): return -0.5 * float(s @ W @ s)

def is_fixed(W, s):             # tie keeps: fixed iff for every i, h_i == 0 or sign(h_i) == s_i
    h = W @ s
    return bool(np.all((h == 0) | (np.sign(h) == s)))
```
Checks per trial of `states.csv`/`trials.csv`: final state is a fixed point when `converged`; `energy(W, final) == e_final`; `energy(W, query) == e_start`; classification recomputed independently equals `class`/`match_*`; `trace.csv` energies equal `energy(W, state)` replayed from the query for the visits that flipped (optional, only for traced trials); async trace is non-increasing within 1e-9. For `capacity.csv`: `stable_fraction` and `min_margin` equal numpy over all 14950 subsets exactly.

### Course example as a C unit test
[CITED: docs/Modelo de Hopfield.pdf slides 26-32] Store `xi1 = (1, 1, -1, -1)`, `xi2 = (-1, -1, 1, 1)`; the expected W has `w12 = 2`, `w13 = -2`, `w14 = -2`, `w23 = -2`, `w24 = -2`, `w34 = 2` (computed by hand this session from `w_ij = sum xi_i xi_j`). The query `zeta = (1, -1, -1, -1)` has `h = (2, 6, -2, -2)` and one sync step gives `(1, 1, -1, -1) = xi1`, the slide's answer. (Here `xi2 = -xi1`, so the classifier must report *stored*, which also tests the precedence of stored over inverse.)

## Spurious-state search procedure (HOP-03)
1. Run the `recall` task on the **separated set**, `update = async`, levels `k = 10, 11, 12` (0.40, 0.44, 0.48), 100 trials per (pattern, level), `trace_trials = 100`, seed 1. Measured on the draft separated set GRTV: at 40 % noise 37/120 trials end in a **mixture**, 13/120 in **other**, 23/120 in an **inverse**, 26/120 in a **different stored** pattern, 21/120 in the right pattern; at 20 % noise already 7 mixtures and 4 "other" out of 120 [VERIFIED: numpy prototype]. So spurious states are plentiful; the search is not a hunt.
2. From `trials.csv` take the first trial of each class in {inverse, mixture, other} (file order). Report: seed (from the config copy), the pattern/level/trial, the query and final state from `states.csv`, the overlap vector, the mixture triple and signs, and the energy of the final state next to `stored.csv` energies and `e_start`.
3. Numpy recomputes the class independently and asserts the state is a fixed point of the same W. Mixtures are the rule rather than the exception for N = 25, p = 4, so the write-up should say "mixture of three" with the signs, not just "spurious".
4. Energy comparison is descriptive: do not claim spurious states are always higher; PITFALLS 12c measured the opposite for the QR majority state.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Synchronous `s = sign(W s)` as the main loop | Async with random order as reference, sync as labelled comparison | Hopfield's energy proof needs sequential updates | Monotone energy; cycles only in sync |
| 0.138N as a capacity threshold | Order of magnitude plus an empirical stability-vs-p curve over many subsets | n/a | Honest at N = 25 where choice of letters dominates |
| Single hand-picked letter set | Two sets picked by a pre-registered rule over all 14950 | This project (D-03/D-04) | No cherry-picking |

**Deprecated/outdated:** nothing; Hebb is the course rule, pseudo-inverse is Phase 5.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Sync dynamics with symmetric W end in cycles of length at most 2 (Goles-Olivos) | Pitfall 5 | Detecting only period 2 would miss longer cycles; mitigated by `max_sweeps` cap and `converged = 0` |
| A2 | Experiment parameters: levels k = 0..12, 30 trials, 10 seeds, capacity noise 0.12, sampled p = 1..12 with 200 subsets, spurious levels 0.40/0.44/0.48 with 100 trials | "What the rule must pin down" item 7 | Planner/user may prefer other values; they only need to be written in the rule before running |
| A3 | Mirrored tie-break for the correlated set | Pitfall 1, rule item 3 | User may prefer the literal D-03 reading; outcome would then be a stable "correlated" set reported as a finding |
| A4 | The draft alphabet is adopted as the starting point | Draft alphabet | If redrawn, every number quoted from the prototype (GRTV/HMNW, 1326 ties, rates) changes; and if adopted unchanged the research has already seen network results on it (disclose) |
| A5 | Capacity p range up to 12 reaches "stability ~ 0" (draft letters: mean stable fraction 0.11 at p = 12, 0.238 at p = 8) | Rule item 7 | D-05 says p = 1..8 "o hasta donde caiga a ~0"; with the final alphabet the range may need adjusting |
| A6 | Goles-Olivos, 0.138N and N/(2 ln N) are quoted from PITFALLS.md/training, not re-verified online | Pitfall 8 | Wrong constants in the write-up; low impact because they are only orders of magnitude |

## Open Questions

1. **Mirrored vs literal tie-break for the correlated set (needs the user at the D-04 checkpoint)**
   - What we know: literal D-03 + the example tie-break picks a stable set on the draft alphabet; mirrored picks one that fails.
   - What's unclear: the user's preference, and whether they see the mirrored choice as "choosing the set to fail".
   - Recommendation: present both with the integer evidence on the bitmaps only; default to mirrored; state in the rule that the correlated set is chosen by bitmap similarity, not by observed failure.
2. **Who draws the alphabet and in what order relative to the checkpoint**
   - What we know: D-01 requires the alphabet committed and guarded; letters are one-way after the rule commit.
   - Recommendation: Plan 1 creates the draft alphabet + converter + tests; the checkpoint approves alphabet and rule together; one commit adds rule doc, select code and series (alphabet already committed and approved).
3. **Is `p = 4` exhaustive recall rate averaged over 10 seeds acceptable?**
   - Recommendation: yes, ~9 s total, and it gives 1200 trials per subset.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| gcc | C core and tests | yes | 13.3.0 | — |
| GNU make | Build | yes | 4.3 | — |
| ASan/UBSan (`-fsanitize=address,undefined`) | `make debug` | yes (compile-and-run probe succeeded) | gcc 13.3 | — |
| python3 | Prototypes, sweep.py | yes | 3.12.3 | — |
| `TP4/.venv` | pytest, figures, analysis | no (absent; root-level `../.venv` has numpy 2.5.2 but no matplotlib) | — | `make venv` (uv 0.11.7 present) builds it from the pinned file; needs network once |
| pdftotext | Reading docs | yes | — | — |
| git | Guard (`ls-files`, `status`, `log`) | yes | — | — |
| Cores | `sweep.py` workers | 20 | — | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** `TP4/.venv` is absent in this checkout; the first `make` / `make test` creates it (network for `uv pip install`). Python tests cannot run before that.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | C: dependency-free `check()`/`check_close()` in `neuron/tests/test_main.c`, run under ASan/UBSan by `make debug`; Python: pytest 9.1.1 |
| Config file | `neuron/Makefile` (targets `test-c`, `debug`, `test`); `analysis/tests/conftest.py` puts `analysis/` and `scripts/` on `sys.path` |
| Quick run command | `make -C neuron test-c` |
| Full suite command | `make test` (from `TP4/`: `prepare`, C tests, then pytest) and `make -C neuron debug` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HOP-01 | W symmetric, zero diagonal, every entry integral; course example W and `zeta -> xi1` | C unit | `make -C neuron test-c` (`test_hopfield_core`) | ❌ Wave 0 |
| HOP-01 | Tie `h_i = 0` keeps the state | C unit | `make -C neuron test-c` | ❌ Wave 0 |
| HOP-01 | Async energy non-increasing (tol 1e-9) and strictly decreasing at flips over >= 200 random starts; `energy_increases == 0` | C unit | `make -C neuron test-c` | ❌ Wave 0 |
| HOP-01 | Incremental E equals from-scratch E after every step | C unit | `make -C neuron test-c` | ❌ Wave 0 |
| HOP-01 | Sync two-cycle detected on N = 2 (`xi = (1, -1)`, start `(1, 1)`), async converges from the same start | C unit | `make -C neuron test-c` | ❌ Wave 0 |
| HOP-01 | Classifier: stored, inverse, mixture (with signs), other; stored takes precedence over inverse/mixture | C unit | `make -C neuron test-c` | ❌ Wave 0 |
| HOP-01 | Strict config: unknown/missing/mistyped key, other task's key, bad `subset` indices (out of range, repeated), bad `noise_levels` | C unit | `make -C neuron test-c` | ❌ Wave 0 (rows in `HOPFIELD_KEYS`) |
| HOP-01 | Same seed gives identical bytes and `trials.csv` differs across seeds | C integration | `make -C neuron test-c` (`same_seed_same_bytes("hopfield", ..., "trials.csv")`) | ✅ extend existing |
| HOP-01 | No memory errors | sanitizer | `make -C neuron debug` | ✅ target exists |
| HOP-02 | Alphabet: 26 letters, shapes, no duplicates, no inverse pairs, J equals the statement matrix | pytest | `.venv/bin/python -m pytest analysis/tests/test_letters.py -q` | ❌ Wave 0 |
| HOP-02 | Selection rule on synthetic alphabets with exact ties; separated and correlated sets and tie-break order; expected sets of the committed alphabet | pytest | `.venv/bin/python -m pytest analysis/tests/test_hopfield_select.py -q` | ❌ Wave 0 |
| HOP-02 | Guard refuses on untracked/dirty rule, alphabet, code or series; `require_same_rule` detects a changed alphabet | pytest (tmp git repo, as `test_som_stage.py`) | same file | ❌ Wave 0 |
| HOP-02 | Recall run: every `trace.csv` trial is non-increasing in async; final states are fixed points; `e_final`, `e_start` recomputed; `stored.csv`/`overlaps.csv` match numpy | pytest cross-check | `.venv/bin/python -m pytest analysis/tests/test_hopfield.py -q` | ❌ Wave 0 |
| HOP-02 | Capacity run: `capacity.csv` has C(26,4) = 14950 rows in lexicographic order; `stable_fraction`/`min_margin` equal numpy for all rows; sampled run has `n_subsets` rows | C integration + pytest | `make -C neuron test-c` (tiny M = 5, p = 2 gives 10 rows) and `test_hopfield.py` | ❌ Wave 0 |
| HOP-03 | Spurious run contains at least one trial of class mixture or other; numpy reclassifies it identically and confirms a fixed point; overlaps and energy columns present | pytest | `test_hopfield.py` | ❌ Wave 0 |
| All | Reproducibility: two runs with the same config and seed give `diff -r` clean directories | shell/pytest | `.venv/bin/python -m pytest analysis/tests/test_hopfield.py -k reproducible -q` (runs twice, `filecmp.dircmp`) | ❌ Wave 0 |
| All | Figures build from run outputs without error | pytest smoke | `.venv/bin/python -m pytest analysis/tests/test_hopfield_figures.py -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `make -C neuron test-c` (C changes) or the relevant pytest file (Python changes), under 30 s.
- **Per wave merge:** `make test` and `make -C neuron debug`.
- **Phase gate:** full suite green plus the guarded driver (`make hopfield-letters`) run on a clean tree before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `neuron/models/hopfield_core.[ch]` and the rows in `HOPFIELD_KEYS` — they are the thing under test
- [ ] `neuron/tests/test_main.c` new tests + `neuron/tests/fixtures/patterns_mix.csv` (synthetic ±1 patterns, N = 25, p = 4, independent of the real alphabet so no network result is seen before the rule is committed)
- [ ] `analysis/tests/test_letters.py`, `test_hopfield_select.py`, `test_hopfield.py`, `test_hopfield_figures.py`
- [ ] Update the existing hopfield cases in `test_main.c` and the smoke series/config example (Pitfall 3)
- [ ] Framework install: `make venv` (no `TP4/.venv` in this checkout)

## Security Domain

`security_enforcement` is enabled (absent = enabled), ASVS level 1. This is an offline academic tool: no auth, sessions or cryptography. The relevant surface is untrusted-ish input (config, CSV, alphabet text) and memory safety in C.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | Strict `KeySpec` validation + range checks in `read_params`; `subset` indices bounded and distinct; `matrix_load` header/shape checks; alphabet converter validation (D-02) |
| V6 Cryptography | no (sha256 via `hashlib` only for the guard, never hand-rolled) | `hashlib.sha256` |
| V12 Files and Resources | yes | Output names are fixed strings; run dir names pass `is_plain` ([VERIFIED: neuron/io/results.c:82-90] `if (!isalnum(c) && c != '_' && c != '.' && c != '-') return 0;`); `metrics.json` keys/values restricted by the same function |
| V14 Configuration | yes | No silent defaults; config copied byte-for-byte into the run folder |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Out-of-bounds read/write from a config index (`subset`, `p`, `trace_trials`) | Tampering / DoS | Validate every index and count before allocating; ASan/UBSan run (`make debug`) |
| Integer overflow in `n * n * sizeof(double)` or trace row count | DoS | Use `size_t` arithmetic as the existing code does, cap `n_cols` for W and cap trace rows with an error |
| Unbounded trace/state output filling the disk | DoS | `trace_trials` cap + hard row limit |
| Malformed alphabet text (wrong row length, non-`*`/`.` characters) | Tampering | Converter fails with a message naming the letter; never pads or truncates |
| Git command injection in the guard | Elevation | Argument lists, no shell (existing pattern, `_git`) |
| Shell-string execution of the binary from Python | Elevation | `subprocess.run([...])` argument lists (existing `run_binary`, `sweep.py`) |

## Sources

### Primary (HIGH confidence)
- In-repo code read this session: `neuron/models/hopfield_stub.c`, `kohonen.c`, `models.c`, `models.h`, `neuron/io/config.c|h`, `matrix.h`, `results.c|h`, `rng.c|h`, `main.c`, `neuron/Makefile`, `neuron/tests/test_main.c`, `analysis/sweep.py`, `som_select.py`, `som_stage.py`, `som.py`, `plots_style.py`, `tests/`, root `Makefile`, `deliverables/02-kohonen.md`
- `docs/Archivo SIATP 42026.pdf` page 6 (J matrix and the three consignas), read as an image
- `docs/Modelo de Hopfield.pdf` slides 14, 15, 21-23, 35-39 (h_i, keep-on-zero, Hebb with 1/N and zero diagonal, crosstalk, energy and ΔH, capacity 15 %), read as images
- numpy and C prototypes run this session on the draft alphabet (scratchpad): exhaustive stability over 14950 subsets (0.135 s numpy), recall/spurious rates, sync cycle rates, C exhaustive capacity timing (0.88 s)

### Secondary (MEDIUM confidence)
- `.planning/research/PITFALLS.md` (Pitfalls 11, 12, 14, 26, Performance Traps) and `.planning/research/ARCHITECTURE.md` (proposed `trials.csv`/`trace.csv`/`states.csv` columns, integer-W argument); both written from domain knowledge in an earlier session

### Tertiary (LOW confidence)
- Goles-Olivos two-cycle theorem, 0.144N and N/(2 ln N) asymptotics: quoted from training/PITFALLS, not re-verified

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — nothing new; all pinned and already in use
- Architecture: HIGH — mirrors `kohonen.c`/`som.py`; core and schemas were exercised by prototypes
- Pitfalls: HIGH for 1-7 (measured or derived), MEDIUM for 8-12 (repo reading and reasoning)
- Experiment parameters: MEDIUM — recommendations on a draft alphabet

**Research date:** 2026-10-23
**Valid until:** 2026-11-22 (stable domain; invalidated earlier if the alphabet is redrawn)
