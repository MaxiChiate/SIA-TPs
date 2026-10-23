---
phase: 04-hopfield-n-cleo-y-letras
verified: 2026-10-23T21:00:00Z
status: passed
score: 10/10 must-haves verified
covered_files:
  - ".planning/phases/04-hopfield-n-cleo-y-letras/04-01-PLAN.md"
  - ".planning/phases/04-hopfield-n-cleo-y-letras/04-01-SUMMARY.md"
  - ".planning/phases/04-hopfield-n-cleo-y-letras/04-02-PLAN.md"
  - ".planning/phases/04-hopfield-n-cleo-y-letras/04-02-SUMMARY.md"
  - ".planning/phases/04-hopfield-n-cleo-y-letras/04-03-PLAN.md"
  - ".planning/phases/04-hopfield-n-cleo-y-letras/04-03-SUMMARY.md"
  - ".planning/phases/04-hopfield-n-cleo-y-letras/04-04-PLAN.md"
  - ".planning/phases/04-hopfield-n-cleo-y-letras/04-04-SUMMARY.md"
  - ".planning/phases/04-hopfield-n-cleo-y-letras/04-05-PLAN.md"
  - ".planning/phases/04-hopfield-n-cleo-y-letras/04-05-SUMMARY.md"
  - ".planning/phases/04-hopfield-n-cleo-y-letras/04-06-PLAN.md"
  - ".planning/phases/04-hopfield-n-cleo-y-letras/04-06-SUMMARY.md"
  - ".planning/phases/04-hopfield-n-cleo-y-letras/04-07-PLAN.md"
  - ".planning/phases/04-hopfield-n-cleo-y-letras/04-07-SUMMARY.md"
  - ".planning/phases/04-hopfield-n-cleo-y-letras/04-08-SUMMARY.md"
  - "Makefile"
  - "analysis/README.md"
  - "analysis/hopfield.py"
  - "analysis/hopfield_figures.py"
  - "analysis/hopfield_letters.py"
  - "analysis/hopfield_select.py"
  - "datos/letters/alphabet_5x5.txt"
  - "deliverables/04-hopfield-letras.md"
  - "neuron/io/config.c"
  - "neuron/models/hopfield.c"
  - "neuron/models/hopfield_core.c"
  - "neuron/models/hopfield_core.h"
  - "neuron/models/models.h"
  - "neuron/tests/test_main.c"
  - "scripts/letters.py"
  - "scripts/prepare_letters.py"
covered_digest: "v3:sha256:1c8b636d83b05844339fb627d7947a282d837f91f7786c9922b174f4851e097b"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 9/10
  gaps_closed:
    - "WR-01: every claim that the numpy control recomputes every run/trial narrowed to what hopfield.py actually recomputes"
  gaps_remaining: []
  regressions: []
gaps: []
deferred: []
advisory: []
human_verification:
  - test: "Confirm that no network quantity (Hebb matrix, fields, energies, recall) was computed on the real 26-letter alphabet before the rule commit 23c3563"
    expected: "Yes: the first run of the network on the real letters happened after the commit. The deliverable (sections 2 and 3) already discloses the discarded draft alphabet and the prototype run on it."
    why_human: "Judgment-tier prohibition (unverified-prohibition, human review recommended). The repo is consistent with it (commit 23c3563 holds only converter, selection code, tests, alphabet and rule; result files carry later timestamps) but cannot prove an ordering of events that happened outside git."
---

# Phase 4: Hopfield nucleo y letras - Verification Report (re-verification)

**Phase Goal:** As a student, I want to validate a Hopfield core on four 5x5 letters, so that I understand recovery, energy, capacity and spurious states before moving to QR codes.
**Verified:** 2026-10-23
**Status:** human_needed (all behavioral truths and the previous gap are verified; one judgment-tier prohibition is flagged for the user, non-blocking)
**Re-verification:** Yes, after gap closure 04-08 (previous status gaps_found, 9/10)
**Mode:** mvp (user-story goal, valid)

## Previous gap: closed

**WR-01 (numpy cross-check claims overstated): CLOSED.** I read every place the previous report named and grepped the whole repo outside `.planning/` and `analysis/results/` for the claim family (every run/trial, todos los ensayos, cada corrida, recomputes all, independently, cross-check, nothing downstream, recalcula, reproduce).

| Place | Now says | Matches what `hopfield.py` does |
|-------|----------|---------------------------------|
| `deliverables/04-hopfield-letras.md` section 1 "Control en Python" (line 21) | Recomputes "solo una parte": W, `stored.csv`, overlaps for every run; stability columns of capacity rows; step-by-step replay of the first trial per letter and level (2080 of 62,400) and the 1200 spurious trials; the other 60,320 recall trials and capacity `recall_rate`/`mean_sweeps` only range/consistency checked; `correct` check called circular; recall rates "descansan, salvo en los ensayos trazados, en lo que C escribio" | Yes. Numbers re-derived from `run.json` design: 10 seeds x 4 letters x 13 levels x 30 trials x 4 sets-runs = 62,400; `trace_trials = 1`; spurious 4 x 3 x 100 = 1200; 62,400 - 2,080 = 60,320 |
| `analysis/hopfield.py` module docstring (lines 1-23), `check_capacity`, `check_recall` docstrings | Explicit "Recomputed" vs "Only range and consistency checks" lists; states the RNG is never replayed | Yes |
| `analysis/hopfield_letters.py` module docstring, `run_series` docstring | "narrower than 'every trial'", lists scope, points to hopfield.py docstring | Yes |
| `analysis/README.md` lines 117, 118, 127 | Same narrowed scope, `code_identity` described | Yes |
| 04-04 / 04-05 SUMMARY | Correction notes added under the original sentences (the original "recomputes all ... 63,600 recall trials" line remains, but is followed directly by a blockquote correction) | Acceptable: planning history, corrected in place |

Repo-wide grep result: no remaining unqualified overclaim in code, tests, Makefile, READMEs or the deliverable. Remaining hits are qualified ("every run" for W/stored/overlaps, which is true; "recalcula ... cada corrida" in the driver sentence of section 1, which is followed by the scope paragraph) or belong to other phases (Kohonen/sweep).

**Known leftover `cross_checked_trials` (63,600): judged NOT a remaining overclaim, INFO level.** It is a machine-readable counter in the unversioned `run.json`. It is not cited by the deliverable, README or any narrative; the only consumer is a `> 0` test assertion. A code comment at the assignment (`hopfield_letters.py` lines ~694-696) and the 04-05 correction note say it counts trials that went through `check_recall`, only the traced ones being replayed. The name is looser than the scope, and a reader of `run.json` alone, without the comment, could read it as "63,600 replayed". The cost of fixing it is non-trivial (renaming changes `hopfield_letters.py`, hence its sha256 in `code_identity`, hence a re-run to keep the figures guard green), and the harm is nil while nothing reports the number. Recommended optional follow-up, not a gap: if the number is ever quoted anywhere, quote it as "trials checked (range/consistency)", or rename to `checked_trials` plus a `replayed_trials` count in the same commit as a re-run. `cross_checked_capacity_rows` (196,030) is accurate for the stability columns, which are what it feeds.

**WR-02 (code identity not recorded): CLOSED, as a decision taken by the user.**
- `run.json` now carries `code_identity` = `{head: 23c35639, dirty: true, files: {6 sha256}, binary_sha256}`. `CODE_FILES` = `hopfield.c`, `hopfield_core.c`, `hopfield_core.h`, `config.c`, `hopfield.py`, `hopfield_letters.py`.
- `hopfield_figures.require_same_code` runs inside `draw` (parameter `check_code=True`) after reading `run.json` and before creating the output directory. I verified on the real results: current files match (`changed_code_files == []`, guard passes); with one recorded hash falsified the guard refuses naming `neuron/models/hopfield_core.c`; a `run.json` with no `code_identity` is refused with all files named. Six new tests cover this and pass.
- Deliverable section 8 "Que fija la guardia y que no" states honestly what is pinned (rule, alphabet, selection code, design constants), that the network code is not part of the pre-registration, that identity is recorded by sha256, that `dirty` is `true` in the reported run, and that the recorded commit therefore does not identify the code (the hashes do). README line 127 repeats this. No overclaim.
- Residual scope notes (INFO): `analysis/sweep.py` and `analysis/hopfield_figures.py` are not in `CODE_FILES` (sweep is the shared runner; the figure script only draws). The binary sha256 is recorded but not compared by the figures guard (the binary is rebuilt by `make test`). Both consistent with the text, which lists exactly the six files.

## Regression checks on previously verified items

| Item | Check | Result |
|------|-------|--------|
| Pre-registration guard | `.venv/bin/python analysis/hopfield_select.py identity` | exit 0, rule_commit 23c35639, same four sha256 as before |
| 7 frozen files untouched | `git status --porcelain` on selection code, alphabet, `letters.py`, `prepare_letters.py` | empty; commit 23c3563 still the only commit |
| Nothing staged / committed by gap closure | `git diff --cached --stat` | empty |
| Python suite | `.venv/bin/python -m pytest analysis -q` | 147 passed (re-run by me) |
| C suite under sanitizers | `make -C neuron debug` | 1100 checks, 0 failed (re-run by me) |
| Figures guard on real results | `require_same_code(run.json)` | passes |
| Headline results (set selection, 14,950-subset stable counts, recall rates, async energy monotonicity, spurious picks) | Independently reproduced in the previous round with code that does not use the repo; `run.json` shows the gap-closure re-run changed only the `code_identity` block (04-08 `diff -rq`), and no number in the deliverable changed | still VERIFIED |

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| SC1 | Hopfield in C (integer W, sync and async) logs energy at every step, detects cycles, classifies final state | VERIFIED | `hopfield_core.c`/`.h` unchanged in substance, 1100 C checks pass |
| SC2 | 4 letters stored and recovered from noisy queries; energy per step in CSV, non-increasing async | VERIFIED | recall series, `energy_increases = 0` in the async runs; independent re-simulation (previous round) |
| SC3 | Orthogonality and capacity across several subsets | VERIFIED | two sets, all 14,950 subsets, p = 1..26 |
| SC4 | Very noisy pattern converges to an identified, classified spurious state | VERIFIED | `spurious.json`, independently replayed |
| T05-1 | Driver refuses unless rule commit/digests match | VERIFIED | `identity` exit 0, guard tests pass |
| T05-2 | Strict config, same seed same bytes, core generic in N | VERIFIED | determinism tests pass |
| T04-1 | Capacity cross-checked against an independent computation | VERIFIED | Stability columns recomputed row by row (196,030 rows); claim now correctly scoped |
| T06/07 | Figures guarded, deliverable sections 1-8 complete, rule markers untouched | VERIFIED | 9 figures; `identity` exit 0; section 8 now also documents the code-identity guard |
| T05-7 | Numpy-control coverage claims | VERIFIED (was PARTIAL) | Claims now match `check_recall`/`check_capacity` scope; leftover key name judged INFO |
| PROH | Judgment-tier MUST NOTs (no Hopfield library, no network quantity on real letters before the rule commit, correct = exact match, no 0.138N threshold, no "spurious always higher energy", rule text untouched, no pandas) | VERIFIED (non-authoritative judgment), one item flagged | All verified from the repo except the ordering item, flagged below |

**Score:** 10/10 truths verified; 0 behavior-unverified; 1 flagged prohibition.

### Requirements Coverage

| Requirement | Source Plan(s) | Status | Evidence |
|-------------|----------------|--------|----------|
| HOP-01 | 04-01, 04-04, 04-07 | SATISFIED | `hopfield_core.c`, C tests |
| HOP-02 | 04-02..04-07 | SATISFIED | sets, recall, 14,950-subset and p = 1..26 capacity |
| HOP-03 | 04-03, 04-05, 04-07 | SATISFIED | `spurious.json` |

No orphaned requirements (HOP-04..07 belong to Phase 5). Bookkeeping for the orchestrator: REQUIREMENTS.md and ROADMAP still show HOP-01..03 as pending and Phase 4 as incompletely executed; these are not code gaps.

### Anti-Patterns Found

None new. No TBD/FIXME/XXX markers or stubs in the files touched by 04-08. INFO items IN-01..IN-08 from the review are unchanged (cosmetic or latent; none produces a wrong number).

### Probe Execution

SKIPPED: the phase declares no `probe-*.sh` scripts.

### Human Verification Required (non-blocking)

1. **Pre-registration ordering (flagged judgment-tier prohibition, "unverified-prohibition - human review recommended").**
   **Test:** Confirm that no network quantity (Hebb matrix, fields, energies, recall) was computed on the real alphabet before commit 23c3563.
   **Expected:** Confirmed. The deliverable already discloses the discarded draft alphabet and the prototype run on it, and the correlated-set tie-break caveat.
   **Why human:** The repo shows consistent evidence but cannot prove the order of events outside git.

Optional, user's call (already decided or cosmetic, no action required to close the phase): INFO items on frozen files (IN-01, IN-03, IN-04) are better left alone since editing them would break the guard; IN-02 (`.gitattributes` for CRLF) is cheap and not frozen.

### Gaps Summary

No gaps. The one gap of the previous verification (documentation overclaiming the numpy control) is closed by narrowing the claim in every place it appeared, and the code-identity warning (WR-02) is closed with a recorded identity, a working figures guard and an honest section 8. The phase goal holds: the C core is real and tested, all four success criteria are demonstrated, the headline numbers were independently reproduced, and the pre-registration guard passes. The status is human_needed only because of the single flagged judgment-tier prohibition, which does not block moving to Phase 5.

---

_Verified: 2026-10-23_
_Verifier: Claude (gsd-verifier)_
