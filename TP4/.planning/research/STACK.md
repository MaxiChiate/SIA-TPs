# Technology Stack

**Project:** TP4 SIA - Unsupervised learning (Kohonen, PCA, Oja) and associative memory (Hopfield)
**Researched:** 2026-10-20
**Mode:** Ecosystem (greenfield, constrained by PROJECT.md: C core by hand, Python analysis, no ML libraries for Kohonen/Oja/Hopfield)

## Summary

Reuse the TP3 skeleton (`neuron/` C core, `analysis/` + `scripts/` Python, `Makefile`, splitmix64 RNG, `sweep.py`, plotly style helpers) and change only four things: (1) vendor cJSON instead of extending TP3's flat hand-written JSON parser, because TP4 configs are nested and carry float lists; (2) drop `-fassociative-math`/`-march=native` so C results can be compared bit-for-bit-ish against numpy; (3) put Python in a pinned `.venv` (the machine's global Python has none of numpy, pandas, plotly or matplotlib); (4) use matplotlib for every static figure that goes into the report and slides, and keep plotly for interactive exploration only, because Kaleido 1.x needs a Chrome that is not installed here.

Environment facts checked on this machine (2026-10-20): `gcc` is Apple clang 21.0.0 (arm64), GNU Make is 3.81 (2006), Python 3.12.13 (Homebrew), `uv` is installed, Node 26.8.1 and pandoc are installed, Chrome/Chromium is NOT installed, and no scientific Python package is installed globally. The five QR PNGs are 37x37, 8-bit grayscale, pure binary (values only 0 and 255, about 52% black each).

## Recommended Stack

### C core (`neuron/`)

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| C11, `gcc` (resolves to Apple clang on macOS, GCC on Linux) | `-std=c11` + `#define _POSIX_C_SOURCE 200809L` where needed | Kohonen, Oja, Hopfield | Mandated by the course/PROJECT.md; identical to TP3 so the Makefile and the `_POSIX_C_SOURCE` convention in `io/results.c` (mkdir, clock_gettime) carry over. | HIGH |
| GNU Make | 3.81-compatible Makefile only | Build, run, test, clean | The installed make is 3.81. Do not use grouped targets (`&:`), `.ONESHELL`, `$(file ...)`, or `--output-sync`. TP3's Makefile is already 3.81-safe; copy its structure (`SOURCES := $(wildcard ...)`, `-MMD -MP` dependency files, `CONFIG ?=`). | HIGH |
| cJSON (vendored `cJSON.c` + `cJSON.h`) | v1.7.19 (released 2025-09-09, latest) | Parse config JSON | TP4 configs are nested (grid size, per-phase radius/learning-rate schedules, list of noise levels, list of pattern files, arrays of floats). TP3's `config.c` is 450 lines of flat-object parsing that only supports int arrays and must be re-edited for every new key. cJSON is MIT, two files, no build system, C89-compatible, and gives `cJSON_GetObjectItemCaseSensitive` plus typed checks so strict "unknown key / missing key" validation (TP3 style) is ~60 lines on top. Vendor it under `neuron/vendor/cjson/` and compile that one file without `-Wextra -Wpedantic` noise (per-file `CFLAGS` override). It is a parsing utility, not an ML library, so it does not violate the "no libraries that solve it" constraint. | HIGH (version from GitHub releases API) / MEDIUM (choice) |
| splitmix64 RNG (`rng.c/rng.h` from TP3) | copy as-is | Seeded init of weights, input order, bit-flip noise, async update order | Already written, already shuffles, reproducible across platforms (unlike `rand()`/`drand48()`, whose sequence differs by libc). Never use `rand()`. | HIGH |
| Hand-rolled C test runner (`tests/test_main.c`, as TP3) | n/a | Unit tests of the three algorithms | No dependency; `make test`. Test: Hopfield energy non-increasing under asynchronous update, Oja weight converges to leading eigenvector of a small known covariance, Kohonen winner selection and neighborhood on a 3x3 toy. | HIGH |
| `-fsanitize=address,undefined` (via a `make debug` target) | compiler built-in | Catch out-of-bounds on the 1369x1369 weight matrix and grid indexing | Verified it links and runs on this machine's compiler. Hopfield's flat `n*n` indexing is the classic place for silent overruns. | HIGH (verified locally) |

Recommended `CFLAGS`: `-std=c11 -Wall -Wextra -Wpedantic -O2 -MMD -MP` and `LDLIBS := -lm`.

Deliberate difference from TP3: do NOT carry over `-O3 -march=native -fassociative-math -fno-signed-zeros -fno-trapping-math`. Those flags were justified in TP3 by a 90%-of-runtime dot product in a large training loop. Here the workloads are tiny (49x31 SOM/Oja data; one Hopfield sweep is about 1.9M multiply-adds for N=1369), and reassociation makes C results drift from the numpy/PCA reference, which is exactly what the Oja-vs-PC1 and SOM cross-checks need to compare. Also avoid `M_PI` under strict `-std=c11` (not defined by glibc without feature macros); define your own constant.

### Data interchange (C <-> Python)

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| CSV / whitespace text files, one run directory per run (`results/<timestamp>/`, with a copy of the `config.json` that produced it) | n/a | Everything C reads and writes | Same contract as TP3 (`results.c`, `run_report.py`); human-inspectable, no binary-format dependency in C. Python prep scripts write the C inputs (`creadores_prepared.csv`, `qr_*.csv` as +1/-1 values, one row per image or one line per pattern); C writes weights, per-epoch metrics, per-step Hopfield energy and state snapshots as CSV. Do NOT use `.npy`, HDF5 or protobuf. | HIGH |

Preprocessing split (important for the roadmap): Python does z-scoring of `creadores.csv` (dropping `creator_id`/`name`, handling collinear derived columns) and writes the prepared CSV; C reads numbers only. This mirrors TP3's `prepare_*_dataset.py` -> `neuron/data/*.csv` flow and keeps C free of string handling. Keep the scaler's mean/std in a sidecar JSON so the Python side can un-standardize SOM/Oja weights for interpretation.

### Python analysis (`analysis/`, `scripts/`)

Python 3.12 is installed; numpy 2.5.4 and scipy 1.18.1 both require >=3.12, so pin `requires-python >= 3.12`.

| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|-------------|------------|
| numpy | 2.5.4 (2026-10-10) | PCA by hand-check (`np.linalg.eigh` on the correlation matrix, or `np.linalg.svd` of the z-scored matrix), alignment of Oja weights with PC1, noise generation for Hopfield reference, orthogonality/overlap matrices (`P @ P.T / N`) | Always. PCA via eigendecomposition is about 10 lines and is the ground truth for Oja; the course docs teach PCA through eigenvalues/eigenvectors, so show it explicitly rather than hide it behind sklearn. | HIGH |
| pandas | 3.0.6 | Read `creadores.csv`, EDA (describe, correlation matrix, distributions), join SOM neuron assignment back to creator names | EDA and reporting only. Note pandas 3 defaults to Copy-on-Write and a dedicated `str` dtype; do not write code that relies on chained assignment. Needs Python >= 3.11. | HIGH |
| Pillow | 13.0.0 | PNG -> grid -> +1/-1 matrix for the 5 QRs (`np.array(Image.open(p).convert("L"))`, then `np.where(a < 128, 1, -1)`) | Preprocessing script only. Verified locally that all 5 PNGs are 37x37 grayscale with values {0, 255}, so a fixed threshold at 128 is exact; assert `set(np.unique(a)) <= {0, 255}` and fail loudly if a future image is antialiased or resized. Also writes noisy/recovered grids back to PNG if needed. Matplotlib already depends on Pillow, so it adds no new install weight. | HIGH |
| matplotlib | 3.11.2 | All static figures for the report and slides: biplot (scatter + loading arrows), scree, U-matrix and hit-map (`imshow`/`pcolormesh`), component planes (small multiples), QR grids (`imshow(cmap="gray", interpolation="nearest")`), Hopfield energy-vs-step and state evolution strips | Anything that ends up in the Artifact report or the slides. Default `svg.fonttype = "path"` converts text to glyph paths, so SVG output is immune to the "fonts never load inside an svg" problem TP3 hit with the Slides format. | HIGH (version) / MEDIUM (slide embedding, see below) |
| plotly | 7.1.0 (2026-09-15) | Interactive EDA and sweep comparison charts (hover over creator names on PC1/PC2, error bars across seeds), reusing TP3's `plots_style.py` (`write_html(..., include_plotlyjs="directory")`) | Exploratory analysis and the sweep reports, same as TP3. Plotly 7 breaking changes to know: Kaleido < 1.0 unsupported and Orca removed, so `fig.write_image` needs Kaleido >= 1 AND a Chrome install; `create_annotated_heatmap` and eleven other figure factories were removed (use `go.Heatmap` with `texttemplate`); decimal `rgb(0.1,0.2,0.3)` color strings are no longer accepted (TP3's hex palette is fine). | HIGH |
| pytest | 9.1.1 | A few Python-side regression tests (Oja vs eigh alignment on the real data, Hopfield energy monotonic on C output, QR preprocessing shape/values) | Optional but cheap; TP3 has none on the Python side. Keep to under 10 tests. | MEDIUM |
| Python stdlib (`argparse`, `csv`, `json`, `subprocess`, `concurrent.futures`, `html`, `pathlib`) | 3.12 | `sweep.py`, run reports, HTML generation | Copy TP3's `sweep.py` (ThreadPoolExecutor launching the C binary, seeds x variants, series JSON with `base_config`/`vary`/`values`/`seeds`) and `run_report.py` pattern. Stdlib-only generators are what TP3 uses for HTML; no Jinja2 needed. | HIGH |

Optional, only if a specific question needs it: scipy 1.18.1 (`scipy.cluster.hierarchy` to cross-check SOM-derived clusters against hierarchical clustering; `scipy.stats` for Spearman between Oja index and PC1 score). Do not add it by default.

### Environment management

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| `uv` (already installed) or `python3 -m venv` | uv present at `/opt/homebrew/bin/uv` | Create `.venv` and install `analysis/requirements.txt` | Global Python is Homebrew-managed and has none of the packages, and pip installs into it are blocked/undesirable. `.venv/` is already in the repo `.gitignore`. Makefile targets that call Python should use `PY ?= .venv/bin/python` instead of TP3's bare `python3`. | HIGH |

`analysis/requirements.txt` should pin with compatible-release specifiers (`numpy~=2.5`, `pandas~=3.0`, `plotly~=7.1`, `matplotlib~=3.11`, `Pillow~=13.0`, `pytest~=9.1`) rather than TP3's open `plotly>=5.18`, because plotly 5 -> 7 and pandas 2 -> 3 both changed behavior and this project must be reproducible ("series versionadas, seeds fijas").

### Deliverables: report and slides

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Report: single self-contained HTML published as a claude.ai Artifact, generated by a stdlib Python script from run outputs | n/a | "Informe para entender el proyecto" (PROJECT.md decision) | Decided in PROJECT.md. Embed matplotlib figures as inline SVG (or base64 PNG for heatmap-heavy ones); keep plotly out of the report unless the Artifact sandbox is confirmed to allow its JS. Write the generator so the report is rebuilt from `results/` rather than hand-edited. | MEDIUM (Artifact sandbox limits not verified here) |
| Slides: HTML snippets in the Artifact "Slides" format, one section per exercise, generated like TP3's `analysis/plots_presentation.py` | n/a | "Slides para presentar" | TP3 already did this successfully (painted divs and a pinned-label SVG, dataviz palette slots 1-5). For TP4 prefer matplotlib SVG per chart instead of hand-painting every chart; hand-painted divs are only worth it for simple bars. Verify the Slides snippet format in the first slides phase (it is defined by the Artifact tooling, not by anything in this repo). | MEDIUM |
| Fallback if a `.pptx`/PDF file is demanded: Marp CLI | 4.5.1 (npm, 2026-09-06) | Markdown -> HTML/PPTX/PDF | Node 26.8.1 is installed. Only needed as a fallback; PDF/PPTX export needs a Chrome, which is not installed. HTML export does not. Alternatively use the `pptx` skill. | MEDIUM |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| JSON in C | cJSON 1.7.19 vendored | Extend TP3's hand-written flat parser | Cannot do nested objects or float arrays without a rewrite; every new key means editing parser code. Acceptable only if configs are kept flat (one JSON per exercise); then it is zero-dependency and already strict. |
| JSON in C | cJSON | jsmn | Tokenizer only (no tree, no number conversion); last release v1.1.0 in 2019. More glue code than cJSON for no benefit. |
| JSON in C | cJSON | json-c, jansson | Need autotools/CMake and a system install; breaks "gcc + make, clone and build". |
| Compiler flags | plain `-O2` | TP3's `-O3 -march=native -fassociative-math` | Speed is irrelevant at this size; reassociation changes sums and weakens C-vs-numpy comparisons. |
| Static plots | matplotlib 3.11.2 | plotly + Kaleido `write_image` | Kaleido 1.x (current 1.5.0) requires Chrome; none is installed on this machine, and plotly 7 dropped Orca and Kaleido < 1.0. Adds an install step that can fail for graders/teammates. |
| Interactive plots | plotly 7.1.0 | bokeh, altair, seaborn | TP3's `plots_style.py`, `sweep_report.py` and palette already target plotly. No gain from a third plotting library. |
| PCA reference | numpy `eigh`/`svd` | scikit-learn 1.9.1 `PCA` | Fine as a one-line sanity check, but a ~15-package-weight dependency for something the course derives from eigenvalues; numpy keeps the eigenvalue story explicit. Use only if the team wants a second independent cross-check. |
| Image loading | Pillow | `imageio` 2.38.1, `matplotlib.image.imread`, `cv2` | Pillow is what the others wrap; OpenCV is overkill for 37x37 pixels. |
| Hopfield/SOM/Oja | hand-written C | minisom, somoclu, scikit-learn (`PCA`/`Oja` variants), neurodynex, hopfieldnetwork packages | Forbidden by PROJECT.md (the algorithms are the object of study). Using them even as a "reference" in the delivered code blurs the deliverable; if a cross-check is wanted, keep it in a test, not in the pipeline. |
| Environment | `.venv` + pinned requirements | Conda | Adds a second package manager; `uv`/venv is already how this machine is set up. |
| Slides | Artifact Slides snippets (TP3 style) | Marp, reveal.js via pandoc, PowerPoint by hand | The user already published TP3 as an Artifact; Marp/pandoc are fallbacks if a file is required. |

## What NOT to Use

- `rand()` / `srand()` / `drand48()` in C: libc-dependent sequences break "seeds fijas y reproducibles" across machines. Use the TP3 splitmix64.
- `-ffast-math`, `-fassociative-math` in TP4: see above.
- Any ML library inside the pipeline for Kohonen/Oja/Hopfield, including "just to compare".
- `plotly.figure_factory.create_annotated_heatmap` and other factories removed in plotly 7.
- `fig.write_image()` on this machine without first running `kaleido_get_chrome` (or avoid it entirely, as recommended).
- Global `pip install` into Homebrew Python.
- GNU Make 4-only syntax (the machine has 3.81).
- Committing generated results (PROJECT.md: results are not versioned). Follow TP3: version only `series_*.json`, configs and scripts.

## Installation

```bash
# Python environment (from TP4/)
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r analysis/requirements.txt

# analysis/requirements.txt
numpy~=2.5
pandas~=3.0
plotly~=7.1
matplotlib~=3.11
Pillow~=13.0
pytest~=9.1        # optional

# C: no installs. Vendor cJSON once
mkdir -p neuron/vendor/cjson
curl -L https://raw.githubusercontent.com/DaveGamble/cJSON/v1.7.19/cJSON.c -o neuron/vendor/cjson/cJSON.c
curl -L https://raw.githubusercontent.com/DaveGamble/cJSON/v1.7.19/cJSON.h -o neuron/vendor/cjson/cJSON.h

# Build / run (Makefile modeled on TP3's)
make -C neuron            # release
make -C neuron test
make -C neuron debug      # -fsanitize=address,undefined
```

## Sources

- PyPI JSON API (registry, primary source), queried 2026-10-20: numpy 2.5.4 (uploaded 2026-10-10, requires Python >= 3.12), pandas 3.0.6, plotly 7.1.0 (7.0.0 on 2026-08-25, 7.1.0 on 2026-09-15), matplotlib 3.11.2, scipy 1.18.1, scikit-learn 1.9.1, Pillow 13.0.0, kaleido 1.5.0, pytest 9.1.1, imageio 2.38.1. Confidence HIGH.
- GitHub releases API: DaveGamble/cJSON latest v1.7.19 (2025-09-09); zserge/jsmn latest v1.1.0 (2019-06-23). Confidence HIGH.
- npm registry: `@marp-team/marp-cli` 4.5.1 (also GitHub release 2026-09-06). Confidence HIGH.
- plotly.py GitHub releases page (via WebFetch): 7.0.0 removals (Kaleido < 1.0, Orca, `engine` arg, figure factories incl. `create_annotated_heatmap`, color string formats) and 7.1.0 notes. Confidence MEDIUM (fetched summary, not read line by line).
- Kaleido PyPI page (via WebFetch): Kaleido >= 1.0 requires an installed Chrome; `kaleido_get_chrome` / `kaleido.get_chrome_sync()` installs one; needs plotly >= 6.1.1. Confidence MEDIUM.
- Local inspection: `/Users/gonzalocuri/Documents/dev/repos/SIA/SIA-TPs/TP3/neuron/Makefile`, `io/config.c`, `rng.h`, `io/results.c`, `analysis/sweep.py`, `analysis/requirements.txt`, `analysis/plots_presentation.py`; `gcc`/`make`/`python3`/`uv`/Chrome presence; PNG inspection of `datos/hopfield/*.png` (37x37, values {0,255}). Confidence HIGH.
- Not verified from an authoritative source: the exact constraints of the Artifact Slides format and whether Artifact pages can run plotly.js. Treat the slide and report embedding choices as MEDIUM until the first deliverable phase tests them.
- Note on the confidence seam: `classify-confidence` rates built-in `webfetch`/`websearch` providers LOW (MEDIUM when verified). Tool-free registry queries (PyPI, npm, GitHub releases) are treated here as primary sources; claims that rest only on WebFetch summaries are marked MEDIUM.
