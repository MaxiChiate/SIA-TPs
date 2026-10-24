---
phase: 05-hopfield-con-qr
plan: 06
subsystem: data-prep
tags: [qr, hopfield, preparation, hop-04]
dependency-graph:
  requires: []
  provides:
    - datos/prepared/qr_pm1.csv (generated, not versioned)
    - datos/prepared/qr_pm1.meta.json (generated, not versioned)
    - scripts/qr.py (QrSet, load_qr_set, prepare, SOURCES, encode)
    - make qr target
  affects:
    - 05-02 (guard hashes scripts/qr.py and the five PNGs)
    - 05-03..05-05 (drivers read datos/prepared/qr_pm1.csv and store subset [0,1,2,3,4])
tech-stack:
  added: []
  patterns:
    - mirrors scripts/letters.py / scripts/prepare_letters.py exactly (QrError, _atomic_write, _source_label, prepare() returning (data, paths))
key-files:
  created:
    - scripts/qr.py
    - scripts/prepare_qr.py
  modified:
    - Makefile
decisions:
  - "Polarity fixed and documented: dark pixel (0) maps to +1, light (255) maps to -1 (display-only; Hebb's W is invariant to a global pattern flip, Pitfall 22)."
  - "SOURCES is a fixed explicit tuple of the five real filenames (beverages, dessert, food, specials, wine _menu_qr.png) resolved under datos/hopfield; this fixed order is what the Plan 02 guard hashes and the later drivers index by subset [0,1,2,3,4]."
  - "No thresholding and no resampling: every PNG is asserted to be exactly 37x37 with pixel values only in {0, 255} (measured true for all five); any violation raises QrError and writes nothing."
metrics:
  duration: 12 min
  completed: 2026-10-24
actuals:
  tokens: 1900
  tasks: 1
  commits: 1
  plan_head_before: cd4084d80ce2cc361fa1e65d585dafc310b3b3e7
  plan_head_after: a165cd8a2545c4ad704e1b1717fe6bfd67cf73da
status: complete
---

# Phase 5 Plan 06: QR PNG-to-pm1 preparation Summary

Deterministic PNG-to-±1 converter for the five fixed 37×37 QR codes, producing `datos/prepared/qr_pm1.csv` (5×1369, byte-identical across reruns) and a hashed `qr_pm1.meta.json`, plus a `make qr` target — the input boundary HOP-04 needs before the guard (Plan 02) and the drivers (Plans 03-05) can run.

## What Was Built

- **`scripts/qr.py`** — side-effect-free library mirroring `scripts/letters.py`: `QrError(ValueError)`, `TP_DIR`/`HOPFIELD_DIR`/`PREPARED_DIR`/`PREPARED_CSV` path constants, `SIDE=37`/`N_PIXELS=1369`, a fixed `SOURCES` tuple (the five real filenames in explicit order), `ENCODING`/polarity documentation (dark=+1, light=-1). `encode()` reads one PNG via `PIL.Image` converted to mode `L`, asserts shape is exactly 37×37 and every pixel value is in `{0, 255}` (no thresholding, no resampling), and maps 0→+1, 255→-1. `load_qr_set()` builds the 5×1369 int64 matrix in `SOURCES` order with a per-PNG sha256. `_atomic_write`/`_source_label`/`write_prepared`/`prepare()` reuse the exact `letters.py` pattern (no timestamps, no absolute paths in outputs).
- **`scripts/prepare_qr.py`** — CLI mirroring `prepare_letters.py`: argparse with `--source-dir`/`--out-dir`/`--show`, catches `QrError` to stderr with `sys.exit(1)`, prints `wrote <relpath>` per output file.
- **`Makefile`** — new `qr` target (depends on `venv`, runs `$(PY) scripts/prepare_qr.py`) with a Spanish comment naming `datos/hopfield/*.png` and `deliverables/05-hopfield-qr.md`; `qr` added to `.PHONY`.

Verified against the actual repo PNGs before writing code: all five (`beverages_menu_qr.png`, `dessert_menu_qr.png`, `food_menu_qr.png`, `specials_menu_qr.png`, `wine_menu_qr.png`) are PIL mode `L`, exactly 37×37, with pixel values only in `{0, 255}`.

## Verification Results

All four automated `<verify>` checks from the plan passed:
- `make qr`-equivalent CLI run prints `wrote datos/prepared/qr_pm1.csv` / `wrote datos/prepared/qr_pm1.meta.json`; header starts with `p0,` → `QR_WRITTEN`.
- File has exactly 6 lines (header + 5 rows), every data row has exactly 1369 fields, every cell is `-1` or `1` → `SHAPE_OK`.
- Two consecutive runs produce byte-identical CSVs (`cmp -s`) → `DETERMINISTIC_OK`.
- `qr:` target exists at line start and `qr` is in `.PHONY` → `MK_OK`.

`datos/prepared/qr_pm1.meta.json` records per-PNG sha256 (matches `sha256sum` independently), the fixed `sources` order, `encoding`, `polarity`, `n_patterns: 5`, `n_pixels: 1369`. `datos/prepared/` is covered by `TP4/datos/.gitignore` (`prepared/`), so the generated CSV/meta were never staged.

## Deviations from Plan

None - plan executed exactly as written. No new dependency was added (`analysis/requirements.txt` unchanged); Pillow and numpy were already pinned and used as specified.

## Known Stubs

None.

## Threat Flags

None - the only new trust boundary (PNG bytes into `scripts/qr.py`) is exactly the one named in the plan's threat model and is mitigated by the shape/value-set assertions already implemented (T-05-02).

## Self-Check: PASSED

- FOUND: scripts/qr.py
- FOUND: scripts/prepare_qr.py
- Makefile contains `qr:` target and `qr` in `.PHONY`
- FOUND commit a165cd8 (feat(05-06): PNG to pm-one converter for the five QR and make qr) as ancestor of HEAD
