---
phase: 04-hopfield-n-cleo-y-letras
plan: 03
subsystem: testing
tags: [hopfield, pre-registration, alphabet, letters, selection-rule, guard]

requires:
  - phase: 04-hopfield-n-cleo-y-letras
    provides: "plan 04-02 converter scripts/letters.py and the guard pattern (som_select.rule_digest / rule_guard) reused by rule_identity"
provides:
  - "datos/letters/alphabet_5x5.txt: new 26-letter 5x5 alphabet, drawn network-free and approved by the user"
  - "analysis/hopfield_select.py: integer selection of both 4-letter sets, capacity extension rule, spurious pick, report/identity CLIs, rule_identity, require_same_rule"
  - "deliverables/04-hopfield-letras.md section 3: pre-registered rule text between the regla markers, with the reinforced disclosure"
  - "The user's rule commit 23c35639151d9899c9bc6c3958672c24c51e2831 freezing all of the above before any network run on the letters"
affects: [04-05, 04-06, 04-07, hopfield-letters-driver, capacity, spurious-states]

actuals:
  tokens: 14055
  tasks: 3
  commits: 1
plan_head_before: 609de8759965ac1b4738643c33d86db9c6bd70ea
plan_head_after: 23c35639151d9899c9bc6c3958672c24c51e2831

tech-stack:
  added: []
  patterns:
    - "Pre-registration by commit: rule text, selection code, alphabet and converter frozen in one user pathspec commit; later steps call require_same_rule, which recompares four digests"
    - "Selection from bitmaps alone in integer dot products with tie-breaks fixed by principle"

key-files:
  created:
    - datos/letters/alphabet_5x5.txt
    - analysis/hopfield_select.py
    - analysis/tests/test_hopfield_select.py
    - analysis/tests/test_letters.py
    - scripts/letters.py
    - scripts/prepare_letters.py
  modified:
    - deliverables/04-hopfield-letras.md

key-decisions:
  - "Separated set = min max|d|, then min sum|d|, then smallest index tuple: GRTV"
  - "Correlated set = max max|d|, then max sum|d|, then smallest index tuple: HMNW (the tie-break was fixed knowing the discarded prototype; disclosed)"
  - "Capacity by p pre-registered as p = 1..8, 200 random subsets per p and seed, extended one p at a time while the mean stable fraction at the last p exceeds 0.05, up to p = 26"
  - "User approved the alphabet, the rule and the design with a reinforced disclosure"

patterns-established:
  - "Disclosure of non-independence from a discarded prototype stated in the rule text itself, with the count of coinciding glyphs"

requirements-completed: [HOP-02, HOP-03]

duration: not measured (spans two executor sessions and two user checkpoints)
completed: 2026-10-23
status: complete
---

# Phase 4 Plan 03: Pre-registered letter rule and alphabet Summary

**A network-free 5x5 alphabet, the integer selection of the GRTV and HMNW sets with fixed tie-breaks, and the rule text, frozen in the user's single rule commit 23c3563 with a four-digest guard.**

## Performance

- **Tasks:** 3 (1 auto tracer, 1 checkpoint:decision, 1 checkpoint:human-action)
- **Files in the rule commit:** 7 (1384 insertions)
- **Rule commit time:** 2026-10-23T15:16:26-03:00

## Accomplishments

- New 26-glyph alphabet drawn for legibility without running any network code on it, approved by the user, and committed. `alphabet_sha256 = fafc49320008b77a02a0fedf3e3fb455a0188b10fcc1503d6f080d9feb37afdd`.
- `analysis/hopfield_select.py` picks both 4-letter sets from the bitmaps alone over all C(26,4) = 14950 subsets, never computing a network quantity. The report CLI prints bitmap facts only.
- Rule text pre-registers the recall, capacity (p = 4 and p = 1..8 with the written extension) and spurious designs, the spurious pick, the guard and the disclosure.
- Guard (`rule_identity` / `require_same_rule`) reuses `som_select.rule_digest` and `som_select.rule_guard`. It refuses unless the rule text and the code were added in one commit, with the alphabet and converter in that commit or an ancestor, nothing touched after it, and the text equal to the committed one.

## Rule commit and identity (Task 3, verified)

`.venv/bin/python analysis/hopfield_select.py identity` exits 0 and prints:

| Field | Value |
|-------|-------|
| rule_commit | `23c35639151d9899c9bc6c3958672c24c51e2831` |
| rule_sha256 | `27c1b24315c31eada1d9930847c681dd29f451108e654075e86383f0d9208859` |
| alphabet_sha256 | `fafc49320008b77a02a0fedf3e3fb455a0188b10fcc1503d6f080d9feb37afdd` |
| select_sha256 | `214d310ab7ff89c84d432a112767d00658bee6299775499d178f098376df09d1` |
| letters_sha256 | `ba0d68349e16bdd26731d86d7bd265258539b6132498985784738c0741b09caf` |

Task 3 verification block, run exactly:
- `rule_commit` (40 characters) equals `git log --diff-filter=A --format=%H -- deliverables/04-hopfield-letras.md`: PASS.
- `alphabet_sha256` equals the sha256 of `git show <rule_commit>:./datos/letters/alphabet_5x5.txt`: PASS (both `fafc4932...37afdd`).
- `git status --porcelain -- analysis/hopfield_select.py datos/letters/alphabet_5x5.txt scripts/letters.py` prints nothing: PASS.
- `pytest analysis/tests/test_hopfield_select.py analysis/tests/test_letters.py -q`: 47 passed.

## Selected sets (integer keys, bitmaps only)

| Set | Letters | Indices | max abs d | sum abs d | Tie-break |
|-----|---------|---------|-----------|-----------|-----------|
| Separated | G R T V | [6, 17, 19, 21] | 1 | 6 | min max, then min sum, then smallest index tuple; unique at (1, 6) |
| Correlated | H M N W | [7, 12, 13, 22] | 21 | 110 | max max, then max sum, then smallest index tuple; 1575 subsets share max 21, unique at (21, 110) |

All six pairwise d in GRTV are +/-1 (overlap +/-0.04). In HMNW the pairwise d are HM 17, HN 17, HW 17, MN 21, MW 17, NW 21 (overlap 0.68 to 0.84). The max abs d histogram over the 14950 subsets runs from 1 (one subset) to 21 (1575 subsets).

## User decision at Task 2

The user answered "approve + reinforced disclosure". The orchestrator then edited the Divulgación item of `deliverables/04-hopfield-letras.md` (between the markers) so that it states:
- the two selected sets GRTV and HMNW are the same ones the research had already seen on the discarded draft;
- the correlated-set tie-break (higher sum of |d|) was fixed knowing that prototype: on the draft the literal tie-break (lower sum) picked a stable set and the mirrored one picks a set that fails;
- the choice of that tie-break is therefore not independent of the prototype and must be read that way.

No glyph was redrawn or changed at the checkpoint. Tests re-ran after the edit (47 passed) before the commit.

## Coincidence with the discarded draft (k)

k = 25 of 26 glyphs coincide with the discarded research draft (all letters except Q). This is disclosed in the rule text: 5x5 capitals leave little room to differ. The alphabet's sha256 differs from the draft's. The draft was read only after the file was written, only to count coinciding glyphs (D-04b).

## Task Commits

1. **Task 1: Tracer (alphabet, converter, integer selection, rule text, guard)** - no executor commit. The files were left unstaged and frozen in the Task 3 commit.
2. **Task 2: checkpoint:decision (approval)** - no commit. The user's answer is recorded above.
3. **Task 3: Rule commit (checkpoint:human-action)** - `23c3563` (feat), made by the orchestrator on the user's instruction with exactly the 7 files.

**Plan metadata:** none. This SUMMARY is left unstaged by instruction.

## Files Created/Modified

- `datos/letters/alphabet_5x5.txt` - the 26 approved glyphs, the only versioned source of the bitmaps
- `scripts/letters.py` - converter from the alphabet to the neuron input format (plan 04-02 converter, committed with the rule)
- `scripts/prepare_letters.py` - command-line wrapper for the converter
- `analysis/hopfield_select.py` - integer selection, design constants, capacity extension, spurious pick, report and identity CLIs, guard
- `analysis/tests/test_hopfield_select.py` - selection and guard tests, including ten guard tests in a temporary repository
- `analysis/tests/test_letters.py` - real-alphabet tests
- `deliverables/04-hopfield-letras.md` - title and section 3, the rule text between the regla markers

## Decisions Made

- Tie-breaks fixed by principle (D-04b), not offered to the user. The correlated set's tie-break is not independent of the discarded prototype, and the rule says so.
- The capacity extension is written in the rule, so it is never decided by hand (D-05).
- No 0.138N or 0.15N threshold is stated anywhere in the rule, only orders of magnitude (D-05).

## Deviations from Plan

None - plan executed exactly as written. The user's reinforced-disclosure request at Task 2 was an edit to the rule text before the commit, which the plan's resume path allows.

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None. The only git calls pass argument lists with paths from module constants (T-04-09).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 04-05 can call `require_same_rule` and pin `rule_commit` and `alphabet_sha256` into its `selection.json` and `run.json`, using the values above.
- The committed files must not be touched. Any later change makes the guard refuse (D-04).
- No network quantity on the real letters exists in the repository. Plan 04-04 runs the binary only on the synthetic fixture.

## Self-Check: PASSED

- All 7 committed files exist and have no uncommitted change.
- Commit `23c3563` is an ancestor of HEAD.
- The identity CLI exits 0 with the values above.

---
*Phase: 04-hopfield-n-cleo-y-letras*
*Completed: 2026-10-23*
