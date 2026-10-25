---
phase: 05-hopfield-con-qr
reviewed: 2026-10-25T00:00:00Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - Makefile
  - analysis/hopfield.py
  - analysis/hopfield_qr.py
  - analysis/hopfield_qr_figures.py
  - analysis/hopfield_qr_limits.py
  - analysis/hopfield_qr_select.py
  - analysis/tests/test_hopfield.py
  - analysis/tests/test_hopfield_qr.py
  - analysis/tests/test_qr.py
  - deliverables/05-hopfield-qr.md
  - neuron/config.json.hopfield_pinv.example
  - neuron/io/config.c
  - neuron/models/hopfield.c
  - neuron/models/hopfield_core.c
  - neuron/models/hopfield_core.h
  - neuron/tests/test_main.c
  - scripts/prepare_qr.py
  - scripts/qr.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 05: Code Review Report

**Reviewed:** 2026-10-25T00:00:00Z
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

I read every listed file in full, traced the pinv math (both the C `hopfield_pinv`/`invert_gram` Gauss-Jordan
implementation and the numpy `hopfield.pinv`/`hopfield.margins`/`hopfield.energy` control) by hand against the
documented formulas, re-derived the incremental async energy update (`E += 2 s_i h_i - 2 w_ii`) from the
quadratic form to confirm it against `hopfield_async_run`, traced the sync two-cycle detection against its own
unit test, verified the Hebb/pinv/Hamming aggregation pipeline in `hopfield_qr.py` column-by-column against the
C-written CSV schemas, and independently re-derived several of the numbers quoted in
`deliverables/05-hopfield-qr.md` (the majority-attractor Hamming distances against the quoted `mean_final_overlap`
of 0.791) to check internal consistency. I did not find a correctness bug in the numerical core: the
Hebb/pinv weight construction, the async/sync dynamics, the classifier, the stability-margin check, and the
Python↔C cross-validation in `analysis/hopfield.py` (`check_recall`/`check_capacity`) are mutually consistent and
match the hand-computed test fixtures (`test_course_example`, `test_pinv_fixes_correlated_fixture_hebb_cannot`,
the C `test_hopfield_core` pinv block). Memory-safety patterns in the C files (bounds checks before every
`malloc`-sized write, header-table allocation/free pairing, `copy_string`/`read_file` length checks) are also
sound.

What I found instead are two real robustness/maintainability gaps (WARNING) and three minor quality items
(INFO), detailed below. There are no BLOCKER findings in this phase's files.

## Warnings

### WR-01: `hopfield_qr_select._git_stdout` can crash with a raw traceback instead of the guaranteed clean refusal

**File:** `analysis/hopfield_qr_select.py:110-113`
**Issue:** `rule_identity()`'s own docstring promises "Every refusal is a SystemExit ending in `(D-01)`.", and the
sibling helpers in the other two modules that call out to git honor that contract defensively:
`analysis/hopfield_qr.py:524-530`'s `_git_text` and `analysis/hopfield_qr_limits.py:258-263`'s `_git_text` both
wrap `subprocess.run` in `try/except OSError: return None`, so a missing git binary degrades to a `None` that
callers turn into a clean message. `_git_stdout` in `hopfield_qr_select.py`, used by `_added_commit` and
`rule_identity` (the actual D-01 guard that every driver calls before touching the network), has no such
guard:
```python
def _git_stdout(args: list[str], repo_dir: Path) -> str:
    """Argument list, no shell, run in repo_dir (T-05-05)."""
    return subprocess.run(["git", *args], cwd=repo_dir, capture_output=True, text=True,
                          check=True).stdout.strip()
```
`check=True` means any git invocation that exits non-zero for a reason other than "nothing found" (e.g.
`git merge-base --is-ancestor` on an unrelated/unborn branch combination inside `_is_ancestor` is handled
separately without `check=True`, but `_git_stdout` itself is also called directly in `rule_identity` for
`git log -1 --format=%H -- path`, `git show <rev>:./file`, etc.) will raise `subprocess.CalledProcessError`
unhandled, and a missing `git` executable raises `FileNotFoundError` unhandled. Either propagates as an
uncaught Python traceback through `rule_identity()` → every driver's `run()` (`hopfield_qr.py`,
`hopfield_qr_limits.py`) instead of the documented, actionable `SystemExit(...) (D-01)` message.
**Fix:**
```python
def _git_stdout(args: list[str], repo_dir: Path) -> str:
    try:
        done = subprocess.run(["git", *args], cwd=repo_dir, capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"git {' '.join(args)} failed in {repo_dir}: {error} (D-01)") from None
    return done.stdout.strip()
```

### WR-02: The five-QR ordering is duplicated across three modules with no test or runtime check tying them together

**File:** `scripts/qr.py:32-38`, `analysis/hopfield_qr_select.py:45-51,63`, `analysis/hopfield_qr_limits.py:80`
**Issue:** `scripts/qr.py`'s `SOURCES` tuple (the authoritative fixed order: beverages, dessert, food,
specials, wine) is relied on by `analysis/hopfield_qr_select.py`'s `PNG_FILES` tuple and `SUBSET = (0, 1, 2, 3,
4)`, and by `analysis/hopfield_qr_limits.py`'s `SHIFT_SOURCE = 0` (meant to mean "beverages"), purely by
in-comment convention ("Fixed order (matches scripts/qr.py SOURCES)"). The integrity check in
`analysis/hopfield_qr.py:571` (`_check_prepared_qr`) pairs them positionally:
```python
for name, path in zip(qr.SOURCES, hopfield_qr_select.PNG_FILES):
    if source_sha256.get(name) != identity["png_sha256"].get(path):
```
Today the two tuples agree (I compared them element by element), so this is not presently a correctness bug —
but nothing enforces the invariant: no test in `analysis/tests/test_qr.py` or
`analysis/tests/test_hopfield_qr.py` asserts that the basenames of `hopfield_qr_select.PNG_FILES` equal
`qr.SOURCES` in order, and there is no runtime assertion in `_check_prepared_qr` itself. If a future edit
reorders one tuple without the other (e.g. adding a sixth QR, or alphabetizing one list), `zip()` silently
pairs the wrong name with the wrong path; the most likely visible symptom is `_check_prepared_qr` refusing to
run with a confusing "was not written from the committed PNGs" message even though the data is actually fine
(a fail-closed break, not a silent wrong-accept, but still a maintenance trap that would cost real debugging
time given three independently-edited files hold pieces of the same invariant).
**Fix:** Derive `PNG_FILES` from `qr.SOURCES` instead of re-listing it (e.g.
`PNG_FILES = tuple(f"datos/hopfield/{name}" for name in qr.SOURCES)`), or add a one-line test/assertion:
`assert [Path(p).name for p in hopfield_qr_select.PNG_FILES] == list(qr.SOURCES)`.

## Info

### IN-01: Duplicated sha256/git-identity boilerplate across three modules

**File:** `analysis/hopfield_qr.py:511-547`, `analysis/hopfield_qr_limits.py:246-275`,
`analysis/hopfield_qr_select.py:79-80,110-113`
**Issue:** `_sha256_file`, the `_git_text`/`_git_stdout` subprocess wrapper pattern, and the `code_identity`/
`code_file_hashes`/`changed_code_files` trio are each re-implemented nearly verbatim in `hopfield_qr.py` and
`hopfield_qr_limits.py` (and the hashing/subprocess primitives a third time in `hopfield_qr_select.py`).
**Fix:** Factor the shared `_sha256_file`, `_git_text`, and the identity/changed-files pattern into one small
helper module (e.g. `analysis/code_identity.py`) imported by all three, which would also have made WR-01's
inconsistent error handling impossible to introduce.

### IN-02: `plot_energy_trace` can mislabel its primary y-axis if only one dynamical rule has data

**File:** `analysis/hopfield_qr_figures.py:251-312`
**Issue:** `rules = [rule for rule in DYNAMICAL_RULES if any(r["rule"] == rule for r in rows)]` (line 260) and
`twin = ax.twinx() if "pinv" in rules else None` (line 274) are gated only on whether "pinv" is present. In the
case where `rows` contains pinv data but no hebb data (not reachable in the current driver, since
`hopfield_qr.py::run()` always produces both `hebb_ran` and `pinv_ran` before writing `energy_trace.csv`, but
nothing in `plot_energy_trace` itself enforces that), the function still creates a twin axis for pinv and
leaves the primary axis `ax` unused, yet unconditionally labels it `"energia hebb"` (line 295) since that
label is keyed only on `c == 0`, not on whether `"hebb"` is actually in `rules`.
**Fix:** Guard the ylabel the same way the plotting loop is guarded, e.g. `if c == 0 and "hebb" in rules:`.

### IN-03: `neuron/README.md` (outside this review's file list) was not updated for the new `rule: "pinv"` option

**File:** `neuron/README.md:80` (not in this phase's reviewed file set; noted for completeness since it documents the files under review)
**Issue:** `neuron/io/config.c`'s `HOPFIELD_KEYS` comment (reviewed, correct) and `neuron/models/hopfield.c`'s
`read_params` (reviewed, correct) both document/accept `rule` as `"hebb"` or `"pinv"`. `neuron/README.md` line
80 still reads: `` `hopfield` | `rule` | `"hebb"` | Regla de aprendizaje... `` — a stale line that undersells
the feature this phase added. Since `neuron/README.md` is not among the files given for this review, I am not
counting it toward the finding totals, but flagging it because it is the user-facing doc for exactly the
config surface two of the reviewed files changed.
**Fix:** Update the `rule` row of the config table to `"hebb"` o `"pinv"`, matching the `config.c` comment.

---

_Reviewed: 2026-10-25T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
