---
phase: 04-hopfield-n-cleo-y-letras
plan: 02
subsystem: data-preparation
tags: [hopfield, letters, converter, python, numpy]
requires: []
provides:
  - "scripts/letters.py: parse/encode/render/prepare for the D-01 5x5 alphabet text, D-02 refusals"
  - "scripts/prepare_letters.py: CLI writing alphabet_pm1.csv + meta, --show glyph display"
  - "make letters target (refuses while datos/letters/alphabet_5x5.txt does not exist)"
affects: [04-03, 04-05]
tech-stack:
  added: []
  patterns: ["library + thin argparse CLI (as creadores / prepare_creadores)", "atomic writes, byte-identical reruns"]
key-files:
  created:
    - scripts/letters.py
    - scripts/prepare_letters.py
    - analysis/tests/test_letters.py
  modified:
    - Makefile
decisions:
  - "Identical and exactly-inverse letter pairs are both refused (inverse beyond D-02)"
  - "Trailing whitespace on a row is an error ('unexpected' char), not stripped"
metrics:
  tasks: 2
  files: 4
  tests: 20
status: complete
commits: 0
actuals:
  tasks: 2
  commits: 0
---

# Phase 4 Plan 02: Alphabet converter Summary

Converter from the hand-drawn 5x5 alphabet text ('*' = +1, '.' = -1, row-major) to the 26 x 25 ±1 CSV the C binary reads, with every D-02 refusal and the statement's J under test, proven only on a synthetic alphabet.

## What was built

- `scripts/letters.py`: `parse_alphabet`, `load_alphabet`, `encode`, `render`, `write_prepared`, `prepare`, `LettersError`, `Alphabet`, constants (`ALPHABET_PATH`, `PREPARED_CSV`, ...). Output `alphabet_pm1.csv` (header p0..p24, 26 rows A..Z) and `alphabet_pm1.meta.json` (source, source_sha256, letters, encoding, n_patterns, n_pixels), written atomically and byte-identical on rerun. A refused alphabet writes nothing.
- `scripts/prepare_letters.py`: `--source`, `--out-dir`, `--show`; on `LettersError` prints `letters: <message>` to stderr and exits 1.
- `Makefile`: `letters: venv` target appended at the end, `letters` appended to `.PHONY`. `make letters` fails naming `alphabet_5x5.txt` until the approved alphabet exists.
- `analysis/tests/test_letters.py`: 20 tests (synthetic fixture `synthetic_text()`, roundtrip, CSV/meta, determinism, CLI, 10 parametrised refusals, `test_j_matches_statement`, `--show`, CLI refusal).

## Verification

- All `<automated>` checks pass: CONVERTER_OK, MAKE_LETTERS_OK, LETTER_TESTS_OK (20 collected, selected 12 pass), SHOW_OK; full `pytest analysis/tests/test_letters.py` 20 passed.
- `git diff --cached --quiet` exits 0 (nothing staged); `datos/letters/alphabet_5x5.txt` does not exist (D-04b).

## Deviations from Plan

### Auto-fixed Issues

**1. [Minor ordering] Character check precedes length check inside a row**
- **Issue:** the plan lists length before character, but also requires a trailing space to report the same message as a bad character. Checking characters first within each row satisfies both.
- **Files:** scripts/letters.py
- A row of valid characters with the wrong length still reports "expected 5 characters".

No other deviations. Commit policy override: nothing staged or committed, so `commits: 0` and there is no plan commit ledger; all changes are unstaged working-tree changes for the user to commit in plan 04-03 Task 3. STATE.md and ROADMAP.md untouched (orchestrator owns them).

## Known Stubs

None.

## Threat Flags

None. T-04-04 (malformed alphabet) mitigated by the refusals under test; T-04-05 by `source_sha256` in the meta; T-04-SC: no package installed.

## Self-Check: PASSED

- scripts/letters.py, scripts/prepare_letters.py, analysis/tests/test_letters.py exist; Makefile has `letters:` and `.PHONY` entry.
- No commits expected (override); nothing staged.
