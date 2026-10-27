# Phase 6: Slides e informe - Pattern Map

**Mapped:** 2026-10-25
**Files analyzed:** 17 (11 new, 6 modified)
**Analogs found:** 15 / 17 (2 have no analog)

All analog paths below were confirmed tracked by `git ls-files` (analysis/*.py, analysis/tests/*, Makefile, deliverables/*). No gitignored mirror paths are used. `analysis/results/**` is gitignored and is an input only, never an analog.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `analysis/facts.py` (new) | utility | transform (JSON/CSV -> display strings) | `analysis/campaigns.py` `_decimal` (l.227-231) + `analysis/som_figures.py` `_fmt` (l.107) | role-match (consolidates 6+ private helpers) |
| `analysis/deliverables_manifest.py` (new) | config | batch (static tables: QUESTIONS, FIGURES, SLIDES) | `analysis/som_figures.py` module constants + `Plane` dataclass | partial |
| `analysis/informe.py` (new) | service/builder | batch, file-I/O (fragments + figures -> HTML) | `analysis/som_figures.py` `main` (argparse, guards, out dir) | role-match |
| `analysis/slides.py` (new) | service/builder | batch, file-I/O | `analysis/som_figures.py` `main` | role-match; output format blocked on Wave 0 probe |
| `analysis/plots_style.py` (modify) | utility | transform (variant state, caption, slide size) | itself (`apply_style`, `save_figure`) | exact |
| `analysis/som_figures.py`, `som_profiles.py`, `hopfield_figures.py`, `hopfield_qr_figures.py` (modify) | figure script | file-I/O (read results, draw only) | `analysis/som_figures.py` | exact |
| `analysis/eda.py`, `pca.py`, `oja.py`, `campaigns.py`, `maintenance_demo.py` (modify) | figure script | batch (compute + plot in one `main`) | same files | exact (loop must wrap plot calls only) |
| `Makefile` (modify) | config | batch | root `Makefile` targets (`oja: pca`, `campaigns: oja som-stage1`) | exact for phony style; sentinel targets have no analog |
| `analysis/requirements.txt` (modify) | config | - | itself | exact |
| `analysis/tests/test_facts.py` (new) | test | transform | `analysis/tests/test_som_figures.py` | role-match |
| `analysis/tests/test_deliverables_manifest.py` (new) | test | transform | `analysis/tests/test_som_figures.py` | role-match |
| `analysis/tests/test_informe.py` (new) | test | file-I/O | `analysis/tests/test_som_figures.py` | role-match |
| `analysis/tests/test_slides.py` (new) | test | file-I/O | `analysis/tests/test_som_figures.py` | role-match |
| `analysis/tests/test_repro_docs.py` (new) | test | file-I/O | `analysis/tests/test_som_figures.py` (tmp_path, TP_DIR) | partial |
| `README.md`, `CLAUDE.md`, `DECISIONS.md` (new, repo root) | docs | - | `deliverables/05-hopfield-qr.md` section 7; TP3 `CLAUDE.md` via `git show 7ff59c3:TP3/CLAUDE.md` | role-match |
| `.planning/phases/06-slides-e-informe/06-ARTIFACT-FORMAT.md` (new) | docs | - | none | no analog |
| Sentinel `results` targets | config | batch | none | no analog |

## Pattern Assignments

### `analysis/plots_style.py` (modify: add variant state, caption helper, slide size)

**Analog:** itself. Existing structure to extend.

**Module docstring and imports** (l.1-15): `from __future__ import annotations`, stdlib imports only at top; matplotlib is imported lazily inside functions.

**Style entry point** (l.54-85), the single place rcParams are set, so a slide font scale goes here:
```python
def apply_style():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        ...
        "svg.fonttype": "path",
        "svg.hashsalt": "tp4",
    })
    return plt
```

**Save pattern** (l.88-103), to be made variant-aware (slide writes to `<dir>/slide/<stem>`, applies `fig.set_size_inches` before `savefig`):
```python
def save_figure(fig, path_without_suffix):
    base = Path(path_without_suffix)
    base.parent.mkdir(parents=True, exist_ok=True)
    svg_path = base.with_suffix(".svg"); png_path = base.with_suffix(".png")
    fig.savefig(svg_path, format="svg", metadata={"Date": None})
    fig.savefig(png_path, format="png", dpi=PNG_DPI)
    plt.close(fig)
    return svg_path, png_path
```
Keep determinism (no date, fixed hashsalt). `SURFACE = "#fcfcfb"` (l.28) is the D-10 card background; import it in `informe.py`, do not retype it. Add `use_variant()`, `variant()`, `caption(fig, text, ...)` (no-op for slide) as module state per RESEARCH "Slide-variant plumbing".

---

### Figure scripts (modify): `som_figures.py`, `som_profiles.py`, `hopfield_figures.py`, `hopfield_qr_figures.py`, `eda.py`, `pca.py`, `oja.py`, `campaigns.py`

**Analog:** `analysis/som_figures.py`

**Imports** (l.14-35): sys.path-relative bare imports with `# noqa: E402`:
```python
import numpy as np
import pca  # noqa: E402
import plots_style  # noqa: E402
import som  # noqa: E402
import som_stage  # noqa: E402
from creadores import load_creadores  # noqa: E402
```

**Private caption helper to replace with `plots_style.caption`** (l.103-105; same `_caption` is duplicated in `hopfield_figures.py` and `hopfield_qr_figures.py`):
```python
def _caption(fig, text: str, width: int = 125, y: float = 0.01) -> None:
    fig.text(0.01, y, textwrap.fill(text, width), ha="left", va="bottom", fontsize=8,
             color=plots_style.TEXT_SECONDARY)
```
Hard-coded `figsize` per plot (l.119 `figsize=(11.5, 6.4)`, l.224 `(13.0, 7.6)`, l.273 `(8.5, 4.6)`) must be overridable by the variant (size from manifest).

**Plot-function signature** (l.113-150): `plot_xxx(data..., title, caption, out_stem)`, calls `plots_style.apply_style()`, draws, calls `_caption(...)`, ends with `plots_style.save_figure(fig, out_stem)`. Add the variant loop in `main`, after data is computed once:
```python
for variant in ("report", "slide"):
    plots_style.use_variant(variant)
    plot_map(run.hits, U, k, title, caption, out / "map")
```

**main/guard pattern** (l.315-345): argparse with `--out`, `SystemExit` with an actionable message when an input is missing, rule guard before drawing:
```python
if not selection_path.is_file():
    raise SystemExit(f"{selection_path} not found; run `make som-stage1` first")
som_stage.require_same_rule(selection_path, RULE_FILE)
```
**Hard constraint:** do not touch files in hashed sets (`hopfield.py`, `hopfield_qr.py`, `hopfield_letters.py`, `hopfield_qr_limits.py`, `hopfield_select.py`, `hopfield_qr_select.py`, `som_select.py`, `campaigns_select.py`, `neuron/**`, `deliverables/0X-*.md`). Only the figure scripts listed above are safe. Seam note: `eda/pca/oja/campaigns` compute and plot in one `main`, so wrap only the plot calls.

---

### `analysis/facts.py` (utility, transform)

**Analog:** `analysis/campaigns.py` l.227-231 (and `som_figures.py` `_fmt` l.107-108).

**Formatter to consolidate**:
```python
def _decimal(value: float, digits: int) -> str:
    """Spanish decimals for the report lines: comma instead of point; NaN is written n/d."""
    if math.isnan(value):
        return "n/d"
    return f"{value:.{digits}f}".replace(".", ",")
```
Copy NaN -> `n/d` behaviour (not in the RESEARCH sketch). Loader shape per RESEARCH: `json.loads((results / "<path>.json").read_text(encoding="utf-8"))` returning a flat dict `"som.r2_pc1" -> "0,961"`. Fail loudly (`SystemExit` with the `make` command to run) when a result file is missing, same style as `som_figures.main`. Only the facts module formats numbers; other modules must not.

Unit-test with literals, no result files (see test pattern below).

---

### `analysis/informe.py` and `analysis/slides.py` (builders, batch/file-I/O)

**Analog:** `analysis/som_figures.py` `main` (l.315-345) for CLI shape; `analysis/campaigns.py` report-line writers (l.300-325) for text built from metrics dicts.

**CLI skeleton to copy**:
```python
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="...")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output folder (default: analysis/results/informe)")
    args = parser.parse_args(argv)
    ...
    out.mkdir(parents=True, exist_ok=True)
```
Use `TP_DIR`-relative defaults (imported from `creadores`), outputs under `analysis/results/informe/` and `analysis/results/slides/` (gitignored by `analysis/.gitignore` `results/`).

**Figure embed**, from RESEARCH Code Examples: base64 `<img src="data:image/svg+xml;base64,...">` inside a card whose background is `plots_style.SURFACE`. Do not inline `<svg>` (ids collide, global `*` style leak). Assert page size below a ceiling and no `/Users/` or `@gmail` in output.

**Markdown conversion**: `markdown.Markdown(extensions=["tables","fenced_code","toc"], extension_configs={"toc": {"slugify": ..., "baselevel": 2}})`, anchors `f{N}-s{a-b}` limited to `[A-Za-z0-9._~-]`. Read fragments with `Path.read_text(encoding="utf-8")`, never write them (sha256 guard). Wrap `<table>` in `overflow-x:auto` div; define colour tokens on `:root` plus two dark blocks.

**Jargon links (D-13)**: render-time regex of `D-\d+` to glossary anchors generated from `DECISIONS.md`; fragments stay untouched.

**Drift test (D-12)**: ~25 key numbers; format JSON values through `facts` and assert the string appears in the fragment text (e.g. `r2_pc1` 0,961 from `som/profiles/pca_contrast.json`).

`slides.py` output format is undefined until `06-ARTIFACT-FORMAT.md` exists (Wave 0 probe by the top-level session); planner must gate it.

---

### `Makefile` (modify)

**Analog:** root `Makefile`.

**Phony target style with Spanish comment above and tab-indented recipe** (l.44-47, 68-71, 73-78):
```make
# PCA por autovalores ...
pca: prepare
	$(PY) analysis/pca.py

oja: pca
	$(PY) analysis/oja.py

campaigns: oja som-stage1
	$(PY) analysis/campaigns.py
```
Add every new target name to the `.PHONY` line (l.10). GNU Make 3.81 compatible only (no `.ONESHELL`, no `$(file ...)`).

**venv rule needs a no-`uv` fallback** (l.29-34, currently fails when `uv` is absent):
```make
.venv/.installed: analysis/requirements.txt
	test -x .venv/bin/python || $(UV) venv --python 3.12 .venv
	$(UV) pip install --python .venv/bin/python -r analysis/requirements.txt
	touch $@
```
Add `Markdown==3.11` to `analysis/requirements.txt` only after the human-verify checkpoint (package flagged SUS).

**No analog:** file-sentinel targets (`$(RES)/pca/audited/decision.json: ; $(MAKE) pca`). Use the sentinel table in RESEARCH Pattern 5 (each path confirmed by reading the writer line). New phony `deliverables: results` runs variant figure scripts, then `informe.py`, then `slides.py`.

---

### Tests (new): `test_facts.py`, `test_deliverables_manifest.py`, `test_informe.py`, `test_slides.py`, `test_repro_docs.py`

**Analog:** `analysis/tests/test_som_figures.py` and `analysis/tests/conftest.py`.

**conftest** (already puts `analysis/` and `scripts/` on `sys.path`; `TP_DIR = Path(__file__).resolve().parent.parent.parent`). New tests need no extra setup.

**Test style** (test_som_figures.py l.1-40): module docstring, `from __future__ import annotations`, bare module imports (`import som_figures`), `from creadores import TP_DIR`, plain functions with literal-built inputs and `np.allclose`/`assert`, `tmp_path` for outputs:
```python
from creadores import TP_DIR
...
def test_adjacent_pairs():
    ...
    assert len(set(pairs)) == 12
```
Important: pytest must not depend on `analysis/results/` (not versioned). Test builders against tiny fixture JSON written into `tmp_path`; the real-results drift check runs inside `make deliverables` as a build-time assertion.

`test_repro_docs.py` (no direct analog): read `TP_DIR / "README.md"`, `CLAUDE.md`, `DECISIONS.md`; assert non-empty; regex `make ([a-z0-9-]+)` in README/CLAUDE.md and assert each target appears in `TP_DIR / "Makefile"`. Guards the TP3 deletion history (commits `31958a4`, `bcce0da`).

`test_deliverables_manifest.py`: every `QUESTIONS` entry resolves to an `id=` anchor in a generated HTML from fixture fragments; question texts non-empty; every figure key maps to a Makefile target.

---

### `README.md`, `CLAUDE.md`, `DECISIONS.md` (new, root)

**Analog (README reproduce block):** `deliverables/05-hopfield-qr.md` section 7 (l.93-107):
```
make venv
make qr
make hopfield-qr
make hopfield-qr-limits
make hopfield-qr-figures
make test
```
followed by a bullet per target (`- **`make qr`.** Convierte ...`). Replicate this form per figure/table: command, config/series file, seed. Source the per-phase commands from the "Cómo reproducir" section of each `deliverables/0X-*.md`; also `analysis/README.md` has the series table.

**Analog (CLAUDE.md):** `git show 7ff59c3:TP3/CLAUDE.md`. Structure: title, one-paragraph "contexto vivo", materia/grupo/enunciado line, "Estado técnico (código)" with an annotated tree, conventions (identifiers in English, prose in Spanish rioplatense), pointers to DECISIONS.md. Put at `TP4/CLAUDE.md` (the GSD config points to `./.claude/CLAUDE.md`; planner should resolve which).

**DECISIONS.md:** consolidate D-xx from `.planning/phases/0{1..5}-*/0X-CONTEXT.md` plus PROJECT.md Key Decisions, each with a link to its CONTEXT.md and fragment. This file is also the glossary source for the D-13 render-time links; keep one heading per `D-NN`, with a stable anchor scheme the builder can generate.

---

## Shared Patterns

### Spanish decimal comma, no ad-hoc formatters
**Source:** `analysis/campaigns.py` l.227-231 (`_decimal`)
**Apply to:** `facts.py`, `informe.py`, `slides.py`; all new text. Numbers are read from `analysis/results/**` JSON/CSV, never typed (D-11).

### Actionable `SystemExit` when an input is missing
**Source:** `analysis/som_figures.py` l.328-329
```python
raise SystemExit(f"{selection_path} not found; run `make som-stage1` first")
```
**Apply to:** `facts.py`, `informe.py`, `slides.py`, the drift assertion.

### Pre-registration guard safety
**Source:** RESEARCH Pattern 3 and Pitfall 1 (`som_select.rule_guard`, hashed `CODE_FILES`)
**Apply to:** every plan. Never edit `deliverables/0X-*.md` or hashed Hopfield/SOM/campaign selection code; commit any edit to figure scripts before running `make`.

### Deterministic figure output
**Source:** `analysis/plots_style.py` l.81-82, 100 (`svg.fonttype=path`, `svg.hashsalt`, `metadata={"Date": None}`)
**Apply to:** variant figures and any build stamp (short git HEAD plus dirty flag only, no dates, no absolute paths).

### Results are not versioned
**Source:** `analysis/.gitignore` (`results/`); Makefile comments "(no se versiona)".
**Apply to:** informe/slides outputs go under `analysis/results/`.

### Make target documentation
**Source:** Makefile Spanish comment above every target describing inputs, output dir, and refusal conditions.
**Apply to:** each new target.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `06-ARTIFACT-FORMAT.md` + the Slides Artifact output layout of `analysis/slides.py` | docs/builder | file-I/O | Slides type contract unverified; needs probe by a session with the Artifact tool. `../TP3/analysis/plots_presentation.py` is reference only (D-08 forbids copying hand-painted HTML) |
| Makefile file-sentinel `results` targets | config | batch | All existing targets are `.PHONY`; use RESEARCH Pattern 5 sentinel table |

## Metadata

**Analog search scope:** `analysis/*.py`, `analysis/tests/`, root `Makefile`, `deliverables/`, TP3 `CLAUDE.md` at commit 7ff59c3, `git ls-files` listing
**Files scanned:** ~12 read in whole or in part (plots_style.py, Makefile, som_figures.py, test_som_figures.py, conftest.py, campaigns.py excerpt, deliverables/05 section 7, TP3 CLAUDE.md head); RESEARCH.md read lines 1-492 of 602 (remaining lines not needed for patterns)
**Pattern extraction date:** 2026-10-25
