# Deferred Items — Phase 5

Out-of-scope discoveries logged during execution, not fixed (Scope Boundary rule: only auto-fix issues directly
caused by the current task's changes).

## 05-01

- **Pre-existing CRLF line endings in `datos/letters/alphabet_5x5.txt`** (committed in Phase 4, `23c3563`). This
  environment has `core.autocrlf=input` configured, which surfaces as 6 pre-existing pytest failures unrelated to
  this plan's changes:
  - `analysis/tests/test_hopfield_select.py::test_selection_matches_brute_force`
  - `analysis/tests/test_hopfield_select.py::test_real_alphabet_histogram`
  - `analysis/tests/test_hopfield_select.py::test_report_is_bitmap_only`
  - `analysis/tests/test_letters.py::test_real_alphabet_letters_in_order`
  - `analysis/tests/test_letters.py::test_real_alphabet_j_matches_statement`
  - `analysis/tests/test_letters.py::test_real_alphabet_has_no_identical_or_inverse_pairs`
  All six fail with `letters.LettersError: line 1: expected label 'A' (letter A), found 'A\r'` — a CRLF `\r`
  appended to every label line. Not touched by this plan (`neuron/*`, `analysis/hopfield.py`,
  `analysis/tests/test_hopfield.py` only). `analysis/tests/test_hopfield.py`,
  `analysis/tests/test_hopfield_letters.py` and `analysis/tests/test_hopfield_figures.py` (the files this plan's
  scope actually touches or depends on) all pass cleanly. Fix would be normalizing
  `datos/letters/alphabet_5x5.txt` to LF (e.g. `.gitattributes` entry or a one-time re-commit) — a Phase 4 data
  file, out of this plan's scope.
