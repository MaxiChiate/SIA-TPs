---
phase: 05-hopfield-con-qr
plan: 01
subsystem: ai-ml
tags: [hopfield, pseudo-inverse, numpy, c, gauss-jordan, linear-algebra]

# Dependency graph
requires:
  - phase: 04-hopfield-n-cleo-y-letras
    provides: generic P x N Hopfield core (hopfield_core.c/.h), hopfield.c rule dispatch stub, HOPFIELD_KEYS with
      "rule" already a required KEY_STRING, analysis/hopfield.py's hebb-only recomputation
provides:
  - hopfield_pinv (C): W = X^T (X X^T)^-1 X via Gauss-Jordan inversion of the Gram matrix with partial pivoting,
    diagonal left non-zero, returns 0 on a singular Gram
  - hopfield.c rule dispatch for "hebb" or "pinv" at both weight-build sites (recall and capacity), with a clear
    abort message and no output when the Gram is singular
  - hopfield_async_run's energy increment corrected for a non-zero diagonal (2*s_i*h_i - 2*w_ii)
  - hopfield_min_margin's wrong-pixel count tolerant of float rounding (< -ENERGY_TOLERANCE instead of < 0)
  - analysis/hopfield.py: pinv(P), weights(rule, P), and fields/energy/is_fixed/margins now float64-safe (no int64
    truncation of a real-valued W); check_recall selects the rule from the run and _replay_async mirrors the C
    diagonal correction
affects: [05-02, 05-03, 05-04, 05-05, 05-06 (parallel), any later plan running pinv on the real QR patterns]

# Actuals (#2632)
actuals:
  tokens: 9571
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Gauss-Jordan elimination with partial pivoting for a small Gram inversion, singular/ill-conditioned detected
      by the smallest-available-pivot-magnitude test (no new dependency; hand-written per PROJECT.md)
    - float64 throughout in numpy recomputation (no dtype branch) instead of an int64/float64 split, since the
      magnitudes involved never exceed float64's exact-integer range for either rule

key-files:
  created:
    - neuron/config.json.hopfield_pinv.example
  modified:
    - neuron/models/hopfield_core.c
    - neuron/models/hopfield_core.h
    - neuron/models/hopfield.c
    - neuron/io/config.c
    - neuron/tests/test_main.c
    - analysis/hopfield.py
    - analysis/tests/test_hopfield.py

key-decisions:
  - "hopfield_pinv mallocs a small p x n temp buffer internally (freed before return) rather than requiring a
    second caller-provided scratch array, computing w = X^T (Ginv X) in O(p^2 n + p n^2) instead of the O(p^2 n^2)
    direct double sum; the plan's 'scratch (at least 2*p*p doubles)' sizing covers only the Gram inversion, so this
    keeps the function fast for capacity's larger p without changing its documented contract."
  - "analysis/hopfield.py computes fields/energy/is_fixed/margins in float64 throughout (no int64/float64 dtype
    branch) rather than keeping a separate exact-int64 path for Hebb: the magnitudes involved (N <= 2048, Gram
    entries, overlaps) stay far inside float64's exact-integer range, so Hebb loses nothing and pinv's fractional
    entries are no longer silently truncated to (mostly) zero."
  - "The pinv config example ships as a new sibling file (neuron/config.json.hopfield_pinv.example), following the
    existing neuron/config.json.hopfield_capacity.example convention, rather than editing the single hebb example
    in place; nothing in the codebase loads either .example file, so this is a pure documentation addition."

patterns-established:
  - "A model rule with a real-valued W (pinv) is handled by making the *shared* dynamics/margin/energy code
    tolerance-aware and dtype-general, not by forking a parallel pinv-only code path in either C or numpy."

requirements-completed: [HOP-06]

coverage:
  - id: D1
    description: "hopfield_pinv in the C core (rule=\"pinv\") makes every stored pattern of a correlated synthetic
      fixture an exact fixed point where Hebb leaves at least one non-fixed, with the diagonal left non-zero"
    requirement: "HOP-06"
    verification:
      - kind: unit
        ref: "neuron/tests/test_main.c#test_hopfield_core (section h)"
        status: pass
      - kind: integration
        ref: "neuron/tests/test_main.c#test_hopfield_run (pinv full-run stored.csv fixed==1 block)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Async dynamics under pinv never raise the energy; the C incremental energy formula matches the
      from-scratch energy at every logged step for a non-zero diagonal"
    requirement: "HOP-06"
    verification:
      - kind: unit
        ref: "neuron/tests/test_main.c#test_hopfield_core (section h, 100 runs x up to ~100 sweeps)"
        status: pass
    human_judgment: false
  - id: D3
    description: "hopfield_pinv (and the hopfield.c model layer) reports a singular Gram (two identical stored
      rows) with a clear message instead of inventing weights, writing nothing"
    requirement: "HOP-06"
    verification:
      - kind: unit
        ref: "neuron/tests/test_main.c#test_hopfield_core (section h, duplicate-row check)"
        status: pass
      - kind: integration
        ref: "neuron/tests/test_main.c#test_hopfield_run (dup_fragment hopfield_run_accepts == 0)"
        status: pass
    human_judgment: false
  - id: D4
    description: "analysis/hopfield.py's numpy pinv(P) and float-tolerant fields/energy/is_fixed/margins agree with
      a pinv run produced by the C binary (W, stored, overlaps and traced async replay) within tolerance"
    requirement: "HOP-06"
    verification:
      - kind: unit
        ref: "analysis/tests/test_hopfield.py#test_pinv_fixes_correlated_fixture_hebb_cannot"
        status: pass
      - kind: unit
        ref: "analysis/tests/test_hopfield.py#test_energy_not_truncated_for_fractional_w"
        status: pass
      - kind: integration
        ref: "analysis/tests/test_hopfield.py#test_check_recall_pinv_run"
        status: pass
    human_judgment: false

duration: 46min
completed: 2026-10-24
status: complete
---

# Phase 5 Plan 1: Pseudo-inverse Hopfield rule (C core + numpy twin) Summary

**Pseudo-inverse learning rule `W = X^T (X X^T)^-1 X` in the C core (Gauss-Jordan Gram inversion, non-zero diagonal, singular-Gram abort) wired through `rule="pinv"`, with a float-tolerant numpy recomputation that no longer truncates a real-valued W to int64 — proven end-to-end on a small synthetic fixture under ASan/UBSan, not run against the real QR.**

## Performance

- **Duration:** 46 min
- **Started:** 2026-10-24T17:10:00-03:00 (approx.)
- **Completed:** 2026-10-24T17:25:02-03:00
- **Tasks:** 2
- **Files modified:** 7 modified + 1 created

## Accomplishments

- `hopfield_pinv` in `hopfield_core.c`/`.h`: builds the Gram matrix, inverts it with Gauss-Jordan elimination and
  partial pivoting, assembles `W` with the diagonal left intact (D-07), and returns 0 (leaving `W` unwritten)
  when the largest available pivot falls below a fixed tolerance (D-06, HOP-06's singular-Gram case)
- `hopfield_async_run`'s incremental energy now subtracts `2*w_ii` on a flip, so it matches the from-scratch
  energy for any diagonal (reduces to Hebb's old formula when `w_ii == 0`); `hopfield_min_margin`'s wrong-pixel
  count uses `< -ENERGY_TOLERANCE` so a true pinv fixed point landing a hair below 0 from rounding still counts
- `hopfield.c` accepts `rule` `"hebb"` or `"pinv"`, dispatches the weight build accordingly at both the recall and
  capacity sites, and aborts with a config-path-prefixed message naming the singular Gram, writing nothing further
- `analysis/hopfield.py` gained `pinv(P)` and `weights(rule, P)`; `fields`/`energy`/`is_fixed`/`margins` now compute
  in float64 throughout (no int64 cast that silently truncated a real-valued W to near-zero), with a tolerance on
  the fixed-point tests; `check_recall` reads the run's rule and builds `W` accordingly; `_replay_async` mirrors
  the C diagonal correction so the from-scratch cross-check still catches a wrong C increment
- New tests prove: pinv fixes a correlated fixture Hebb cannot (C and numpy); async energy never rises under pinv
  and the incremental formula matches from-scratch at every step; a singular Gram (duplicate stored rows) is
  reported in both the core call and the full model run; `check_recall` passes end-to-end on a C-produced pinv run
  with `stored.csv` `fixed == 1` for every pattern; `energy()` no longer truncates a fractional W

## Task Commits

Each task was committed atomically:

1. **Task 1: pseudo-inverse rule in the C core, wired through rule="pinv", proven end-to-end on a synthetic
   fixture** - `a6369f6` (feat)
2. **Task 2: float-tolerant numpy recomputation (hopfield.pinv and tolerant checks)** - `6bac1f0` (feat)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified

- `neuron/models/hopfield_core.c` - `hopfield_pinv` (Gauss-Jordan Gram inversion), corrected async energy
  increment, tolerant `hopfield_min_margin`
- `neuron/models/hopfield_core.h` - `hopfield_pinv` declaration and updated doc comments for the two-rule core
- `neuron/models/hopfield.c` - rule dispatch (`params->pinv`), singular-Gram abort message at both weight-build
  sites, `rule` metric reflects the active rule
- `neuron/io/config.c` - `HOPFIELD_KEYS` doc comment now names `"pinv"` next to `"hebb"` (no new KeySpec row)
- `neuron/config.json.hopfield_pinv.example` - new committed illustrative example (not loaded by any code/test)
- `neuron/tests/test_main.c` - flipped the pinv-rejection assertion to acceptance, added a rule="bogus" rejection
  check, a pinv core unit test (section h), and full-run pinv/hebb/duplicate-row integration checks
- `analysis/hopfield.py` - `pinv`, `weights`, float64-throughout `fields`/`energy`/`is_fixed`/`margins`, rule
  dispatch in `check_recall`, diagonal-corrected `_replay_async`, relative-tolerance support in `_expect`
- `analysis/tests/test_hopfield.py` - three new tests covering the pinv behaviors above

## Decisions Made

- `hopfield_pinv` mallocs its own small `p x n` temp buffer (freed before return) to assemble `W` in
  `O(p^2 n + p n^2)` rather than a direct `O(p^2 n^2)` sum; the plan's scratch sizing (`2*p*p` doubles) covers only
  the Gram inversion, and this keeps the function fast for capacity's larger `p` without changing its signature.
- `analysis/hopfield.py`'s `fields`/`energy`/`is_fixed`/`margins` compute in float64 throughout rather than
  branching on `W.dtype`: the magnitudes involved (N up to 2048, Gram entries, overlaps) stay far inside float64's
  exact-integer range, so Hebb's exactness is unaffected while pinv's fractional entries are no longer truncated.
- The pinv config example is a new sibling file (`neuron/config.json.hopfield_pinv.example`), matching the existing
  `config.json.hopfield_capacity.example` convention, instead of editing the hebb example in place. Nothing loads
  either file; this is a minor expansion beyond the plan's literal `files_modified` list (which named only
  `neuron/config.json.hopfield.example`), done to avoid cramming two distinct example shapes into one file.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - missing critical functionality] Added a rule="bogus" rejection check**
- **Found during:** Task 1
- **Issue:** The plan's behavior list says "rule bogus still rejected" but the only existing bogus-value test in
  `test_main.c` covered `task="bogus"`, not `rule="bogus"`.
- **Fix:** Added `check(hopfield_run_accepts(HOP_FRAGMENT("recall", "bogus", ...)) == 0);` next to the pinv
  acceptance check.
- **Files modified:** `neuron/tests/test_main.c`
- **Committed in:** `a6369f6` (Task 1 commit)

**2. [Rule 2 - missing critical functionality] Created a new sibling example file instead of editing one JSON object**
- **Found during:** Task 1
- **Issue:** The plan's `files_modified` named only `neuron/config.json.hopfield.example`, but the action text
  requires "a second object or a sibling example file" for the pinv example, and the existing single-object hebb
  example cannot hold two distinct config shapes without becoming a JSON array (which nothing in the repo reads
  that way) or losing the straightforward hebb reference.
- **Fix:** Added `neuron/config.json.hopfield_pinv.example`, following the existing
  `config.json.hopfield_capacity.example` naming pattern; the original hebb example is untouched.
- **Files modified:** `neuron/config.json.hopfield_pinv.example` (new)
- **Committed in:** `a6369f6` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 2, both trivial additions with no architectural impact)
**Impact on plan:** No scope creep; both fill a literal gap in the plan's behavior/action text.

## Issues Encountered

None beyond the two deviations above.

## Known Stubs

None.

## Threat Flags

None - the plan's `<threat_model>` already covers hopfield_pinv's Gram inversion (T-05-03) and the rule
key validation (T-05-01); no new surface was introduced beyond what was anticipated.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `rule="pinv"` is proven end-to-end (C + numpy, under ASan/UBSan) on a small synthetic fixture only; it has
  **not** been exercised against the real 5 QR patterns, consistent with the plan's prohibition (the pre-registered
  experiment protocol for Phase 5 is not yet frozen).
- Plan 05-06 (parallel wave-1, PNG-to-pm1 QR converter) shares no files with this plan and has no dependency on it.
- Any later plan that runs pinv on the real QR patterns inherits: the float-tolerant numpy recomputation, the
  diagonal-corrected incremental energy, and the singular-Gram abort path, all already tested.
- Pre-existing, unrelated: `analysis/tests/test_hopfield_select.py` and `analysis/tests/test_letters.py` have 6
  failing tests caused by CRLF line endings in `datos/letters/alphabet_5x5.txt` (a Phase 4 data file), surfaced by
  this environment's `core.autocrlf=input` setting. Out of scope for this plan (file not touched here, unrelated
  to the pinv rule); confirmed present before this plan's changes.

## Self-Check: PASSED

- FOUND: neuron/config.json.hopfield_pinv.example
- FOUND: .planning/phases/05-hopfield-con-qr/05-01-SUMMARY.md
- FOUND: .planning/phases/05-hopfield-con-qr/deferred-items.md
- FOUND commit a6369f6 (Task 1) on HEAD
- FOUND commit 6bac1f0 (Task 2) on HEAD

---
*Phase: 05-hopfield-con-qr*
*Completed: 2026-10-24*
