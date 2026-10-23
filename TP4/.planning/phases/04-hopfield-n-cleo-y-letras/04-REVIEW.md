---
phase: 04-hopfield-n-cleo-y-letras
reviewed: 2026-10-23T18:30:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - neuron/models/hopfield_core.h
  - neuron/models/hopfield_core.c
  - neuron/models/hopfield.c
  - neuron/io/config.c
  - neuron/models/models.h
  - scripts/letters.py
  - scripts/prepare_letters.py
  - analysis/hopfield_select.py
  - analysis/hopfield.py
  - analysis/hopfield_letters.py
  - analysis/hopfield_figures.py
  - Makefile
findings:
  critical: 0
  warning: 2
  info: 8
  total: 10
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-10-23T18:30:00Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

I read the C core (`hopfield_core.c/h`), the I/O layer (`hopfield.c`), the `HOPFIELD_KEYS` diff in `config.c`, the Python
checker, driver, selection module and figures, and the frozen scripts. `make test` passes (C: 1100 checks, 0 failed;
pytest: 141 passed).

I traced the following by hand and found them correct:
- the incremental async energy update `E += 2 s_i h_i` and the field update `h[j] += w[j*n+i]*delta`;
- the sync two-cycle detection (`previous` is written at the end of step 1 and only read from step 2);
- the `capacity.csv` column offsets in C against the Python checker;
- the stored/inverse/mixture classification order, which matches between C and numpy;
- `binomial_capped`, `next_combination` and `draw_subsets`;
- the size limits, whose arithmetic is done in `long long` before use.

I found no bug that produces a wrong number in the current results, and no security issue. The `git` and `sha256` guard
uses argument lists with no shell, and the commit hashes are validated as 40 hex characters before they reach a command.

The two warnings are about what the verification and the pre-registration actually cover. The code claims more than it
delivers there. The info items are latent fragility and small inaccuracies, several of them in frozen files.

## Warnings

### WR-01: "Every run is recomputed in numpy" is true for about 3% of the trials, and for none of the capacity recall numbers

**File:** `analysis/hopfield.py:373-537` (also the claims at `analysis/hopfield.py:1-8` and `analysis/hopfield_letters.py:9-11`)
**Issue:** The driver docstring says "Every run of the neuron binary is recomputed by analysis/hopfield.py before
anything is aggregated". `hopfield.py` opens with "Nothing downstream trusts those numbers until this module reproduces
them". That holds only for the traced trials.

- `TRACE_TRIALS = 1` in `hopfield_select.py:55`. So `check_recall` replays 1 of 30 trials per (letter, level) cell.
  The other 29 get only range and consistency checks (`hopfield.py:499-507`: `updates == sweeps*n`, async `e_final <= e_start`, `flips <= updates`).
- For those untraced trials, `class`, `match_*`, `converged`, `sweeps` and `flips` are never recomputed. Their final
  state is not saved, so numpy cannot classify it.
- `correct` is "checked" at `hopfield.py:495-497` only against the class and `match_a` of the same row. That check is
  circular for the untraced rows.
- `recall.csv`, the headline recall-vs-noise figure, aggregates exactly those C-written `correct` and `class` columns.
- In `check_capacity` (`hopfield.py:242-245`) the `recall_rate` column is only tested to lie in [0, 1], and `mean_sweeps`
  only to be at least 1. `capacity_p4.csv` and `capacity_by_p.csv`, and the recall panels of both capacity figures,
  rest entirely on unverified C output.

The run is independently verified for stability, margins, W and energies. It is not independently verified for the
recall rates that the report and figures lead with. A bug in the C trial loop (for example in `corrupt` or in the
`correct` expression) would pass the whole checker.

**Fix:** Either of these, or both.
1. Make the trace cover every trial. The recall series would hold about 4 x 13 x 30 = 1560 trials per run at about 56
   trace rows each, which is about 90k rows, far under `TRACE_ROWS_MAX` = 1,000,000. Set `trace_trials` equal to
   `trials` in `_recall_base`. **This needs a deliberate decision:** `TRACE_TRIALS` is in the pre-registered
   `hopfield_select.py`, and editing it breaks the rule guard. `hopfield_letters.py` is outside the guard, so a local
   override there would silently change the registered design, which is worse.
2. Narrow the claims. Say in both docstrings, and in the deliverable fragment, that rates are recomputed for the traced
   trials and sanity-checked elsewhere. For the capacity `recall_rate`, say that it is not recomputed.

### WR-02: The pre-registration guard does not cover the code that defines success, and `run.json` records no code identity

**File:** `analysis/hopfield_select.py:259` (`guarded` list), `analysis/hopfield_letters.py:573-576` and `623-632`
**Issue:** `rule_identity` pins the rule text, `hopfield_select.py`, the alphabet and `scripts/letters.py`. The code
that turns the pre-registered success criterion into numbers is outside the guard:
- `neuron/models/hopfield.c` (the `correct` expression at line 488 and the `k = lround(level*N)` flip count);
- `neuron/models/hopfield_core.c` (the classifier and the dynamics);
- `analysis/hopfield_letters.py` (the aggregation and the pooling);
- `analysis/hopfield.py`.

`run.json` and `selection.json` record `rule_commit` and four sha256 values, but no commit or hash of any of those. The
`D-04` claim "elegido de antemano" is therefore enforced for the letter sets and the design constants only. After the
numbers are seen, the recall criterion, the classifier or the aggregation can change, and a rerun passes every check
and looks identical in provenance. There is also no way to tell afterwards which binary produced `results/`.

**Fix:** In `hopfield_letters.run()`, which is not frozen, add to the identity written to `selection.json` and `run.json`:
- `git rev-parse HEAD`;
- a dirty flag for `neuron/models/hopfield*.c|h`, `analysis/hopfield*.py` and `neuron/io/config.c`;
- the sha256 of those files.

`require_same_rule` could then compare those hashes as well. If the intent is that they are allowed to change, say so
in the fragment and record them anyway, so the reviewer of the deliverable can see which code version produced the
numbers.

## Info

### IN-01: Error line number is off by one for a doubled blank line (frozen file)

**File:** `scripts/letters.py:113-114`
**Issue:** After `i += 1`, `i` is the 0-based index of the line after the separator. The message `line {i}` therefore
names the first blank line (1-based), not the extra one. For two consecutive blank lines it points at the legitimate
separator. It is correct only for a trailing blank at EOF.
**Fix:** `f"line {i + 1}: unexpected empty line ..."` for the doubled-blank case. **Needs a deliberate decision:** the
file is frozen by 23c3563, so editing it breaks the guard. The message is cosmetic, so leaving it is a reasonable choice.

### IN-02: Alphabet file is not protected against CRLF checkouts (frozen file parses it)

**File:** `scripts/letters.py:99-103`, `datos/letters/alphabet_5x5.txt`
**Issue:** On a machine with `core.autocrlf=true` the checkout has `\r\n`. Every glyph row then contains `'\r'`, so
`parse_alphabet` raises `unexpected '\r'`. The label comparison `label != expected` fails the same way. Even if it were
tolerant, `source_sha256` and the guard's file hash would differ between platforms. The failure is loud, not silent.
**Fix:** Add `datos/letters/*.txt text eol=lf` to `.gitattributes`. That file is not frozen, so the parser needs no edit.

### IN-03: `prepare_letters.py --show` help text says "before writing" but prints after writing (frozen file)

**File:** `scripts/prepare_letters.py:222` and `231-236`
**Issue:** `letters.prepare()` writes both files first, then `--show` prints. A refused alphabet writes nothing, which
is correct, but the help string misstates the order. `main` also does not catch `OSError` from the writes, so a
read-only `--out-dir` gives a traceback.
**Fix:** Change the help to "print the 26 glyphs". **Needs a deliberate decision** because the file is frozen.

### IN-04: The "every refusal is a SystemExit ending in (D-04)" contract has two holes

**File:** `analysis/hopfield_select.py:228-231` and `286-295`
**Issue:** The docstring of `rule_identity` promises that every refusal is a `SystemExit` ending in "(D-04)".
- `_git_stdout` uses `check=True`, and the `git show` call at line 288 does too. If git is missing or the tree is not
  a repository, they raise `CalledProcessError` or `FileNotFoundError` with a traceback.
- `som_select.rule_digest` raises `ValueError` if the markers are damaged. That call is not wrapped.

The run still fails closed, so no unguarded experiment runs. It is a message-quality issue.
**Fix:** Catch `(subprocess.CalledProcessError, OSError, ValueError)` in `rule_identity` and re-raise as
`SystemExit(... "(D-04)")`. **Needs a deliberate decision** because the file is frozen.

### IN-05: Incremental async energy is only valid for symmetric W, and the header does not say so

**File:** `neuron/models/hopfield_core.h:57-63`, `neuron/models/hopfield_core.c:102`
**Issue:** The field update `h[j] += w[j*n+i]*delta` is correct for any W. The energy step `E += 2 s_i h_i` equals the
change in `-1/2 sᵀWs` only when W is symmetric. The header presents the core as generic ("never assumes N = 25"; Phase 5
adds the pseudo-inverse rule). Hebb and the pseudo-inverse are both symmetric, but nothing documents or checks the
requirement.
**Fix:** Add one line to the `hopfield_async_run` comment ("W must be symmetric: the incremental energy assumes it").
Optionally add a debug check, or an end-of-run `assert(fabs(energy - hopfield_energy(...)) < tol)` in the unit tests
for any non-Hebb W.

### IN-06: Hard-coded design numbers in figure captions and N in the recall plot

**File:** `analysis/hopfield_figures.py:261` (`n_pixels = 25`), `306-309` ("30 por letra, 4 letras, 10 seeds"),
`121`, `126-127`, `181`, `185-187` ("ruido 0,12", "k = 3", "200 subconjuntos", "10 seeds")
**Issue:** `draw()` reads `run.json["design"]`, but these figure texts and the k/N axis do not. If a design constant
changes, which is possible through a deliberate reopening of the rule, the captions go stale without any error.
**Fix:** Read `design["recall_trials"]`, `design["seeds"]`, `design["capacity_samples"]`, `design["capacity_level"]` and
`orthogonality["n_pixels"]` and format them into the captions. Keep them in one place.

### IN-07: `plot_max_overlap_hist` derives bar width and N from the first histogram bins

**File:** `analysis/hopfield_figures.py:182-184`
**Issue:** `n = round(histogram[0]["max_abs_dot"] / histogram[0]["max_abs_overlap"])` divides by the first bin's
overlap, which is zero for any alphabet with even N and an orthogonal pair. `step = overlaps[1] - overlaps[0]` assumes
the first two present bins are adjacent. With a gap, the bars become twice as wide and overlap. On the current data
(d = 1, 3, ..., 21 with no gaps) it works.
**Fix:** Take `n` from `selection["n_pixels"]`, or from `orthogonality`. Use `step = min(np.diff(overlaps))` or the
constant `2 / n`.

### IN-08: Small statistical and CLI inaccuracies in the driver

**File:** `analysis/hopfield_letters.py:243`, `312`, `642-644`
**Issue:**
1. `np.std` uses ddof=0 for the "sd over 10 seeds" columns. The population SD under-reports the spread of 10 seeds by
   about 5%. It is not stated anywhere, and the figures label the band "± desvío entre seeds".
2. For exhaustive p (25, 26) the SD is pure float noise: `capacity_by_p.csv` p=25 shows `6.938893903907228e-18`
   instead of 0.
3. `--workers 0` silently falls back to every core (`workers or os.cpu_count()`), and a negative value reaches the
   `ThreadPoolExecutor`.
4. On any failure, `run()` removes the whole output tree (`except BaseException: shutil.rmtree`). That includes the run
   directory that disagreed with numpy, which is the evidence needed to debug the disagreement.
**Fix:** Use `ddof=1` (and say so in the header), or document ddof=0. Round or special-case the SD when the per-seed
values are identical. Validate `--workers >= 1` with an argparse `type`. On failure, move the tree to
`<out>.failed` instead of deleting it.

---

_Reviewed: 2026-10-23T18:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
