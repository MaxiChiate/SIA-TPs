---
phase: 03-oja-y-decisiones-de-campa-a
plan: 02
subsystem: campaigns
tags: [pre-registration, selection-rule, git-guard, numpy, pytest, sha256]

requires:
  - phase: 01-datos-y-pca
    provides: "datos/creadores.csv loader (Creadores), the topic labels and order of pca.TOPICS, the ddof = 1 scaler convention"
  - phase: 02-kohonen
    provides: "som_select.RULE_START / RULE_END / rule_digest and the 'added in one commit, unchanged since' guard pattern of som_stage.py"
provides:
  - "analysis/campaigns_select.py: the campaign rule as code (K = 5, TOPICS, criteria, D-13 tie-break, two followers baselines) and rule_identity, the guard every later step calls"
  - "deliverables/03-oja-campanas.md: title and section 4, the 16-term rule in Spanish between <!-- regla:inicio --> and <!-- regla:fin -->"
  - "analysis/tests/test_campaigns_select.py: 17 tests on synthetic creators and temporary git repositories"
  - "The rule commit a6212e89cdc654021cfda02d9d16237c8c21c332 (one commit, exactly the three files above), made before analysis/campaigns.py exists and before any list was computed"
affects: [03-03, 03-04, 03-05, 03-06]

actuals:
  tokens: 7800
  tasks: 3
  commits: 1

tech-stack:
  added: []
  patterns:
    - "Pre-registered rule: text between markers + executable twin + identity guard, all added in one commit (D-07)"
    - "rule_identity reads the rule text at the rule commit with git show <commit>:./<path> as bytes and compares its marker digest with the working file's"
    - "rank key = (criterion, -second key, -Oja index, creator_id): Oja index and id only break exact ties"

key-files:
  created:
    - analysis/campaigns_select.py
    - analysis/tests/test_campaigns_select.py
    - deliverables/03-oja-campanas.md
  modified: []

key-decisions:
  - "Task 1 checkpoint answered 'approve': terms 1-10 are in the committed rule exactly as written in the plan, no edits"
  - "Fútbol descubrimiento: non_follower_reach_pct descending with trend_posts_pct only as second key (exact ties)"
  - "Arte: 1/2 z(total_engagement_per_1000) + 1/2 x the depth score; z over all 50 creators with ddof = 1, never inside a filter"
  - "rule_identity compares git's view of the rule commit with the working tree, so text outside the markers can grow later (sections 1-3 and 5-7)"

patterns-established:
  - "Constants and TOPICS live in campaigns_select.py, not imported from pca.py, so the committed rule cannot change through another module; a test keeps them equal"
  - "Guard tests build throwaway repositories in tmp_path with git -c user.name=t -c user.email=t@t commit"

requirements-completed: [CAMP-01, CAMP-02]

coverage:
  - id: D1
    description: "Campaign rule in Spanish, section 4 of deliverables/03-oja-campanas.md between markers, with 16 bold-labelled terms matching the approved terms 1-10 and D-07..D-17"
    requirement: "CAMP-01"
    verification:
      - kind: other
        ref: "plan Task 2 RULE_DOC_OK command (markers, title, heading, 16 labels, key strings, 64-hex rule_digest)"
        status: pass
    human_judgment: true
    rationale: "Whether the Spanish text faithfully states the approved terms is a reading judgment; the user approved the terms at the Task 1 checkpoint, the wording is for the reviewer"
  - id: D2
    description: "The rule as pure functions: dominant topic with tie order, topic filter, ddof = 1 z-scores, cost per thousand with infinite cost on zero reach, six criteria, D-13 tie-break, k = 5 without padding, both followers baselines"
    requirement: "CAMP-02"
    verification:
      - kind: unit
        ref: "analysis/tests/test_campaigns_select.py (12 tests of the rule terms)"
        status: pass
    human_judgment: false
  - id: D3
    description: "rule_identity refuses untracked files, a split rule commit, a changed or later-changed campaigns_select.py and changed text between the markers, and ignores text outside them"
    requirement: "CAMP-02"
    verification:
      - kind: unit
        ref: "analysis/tests/test_campaigns_select.py::test_rule_identity_* (5 tests in temporary git repositories)"
        status: pass
      - kind: integration
        ref: "campaigns_select.rule_identity() on the real repo returns rule_commit a6212e89... and two sha256; SAME_RULE_COMMIT_OK; RULE_COMMIT_FILES_OK"
        status: pass
    human_judgment: false
  - id: D4
    description: "Nothing computed before the rule commit: analysis/campaigns.py and analysis/results/campaigns/ do not exist"
    requirement: "CAMP-01"
    verification:
      - kind: other
        ref: "test -e analysis/campaigns.py; test -e analysis/results/campaigns (both exit 1 after the rule commit)"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-10-22
status: complete
plan_head_before: 39a76614b0b28678166b922dc09255f11341322e
plan_head_after: a6212e89cdc654021cfda02d9d16237c8c21c332
commits: 1
---

# Phase 3 Plan 02: Campaign selection rule Summary

**Pre-registered campaign rule committed in one commit (a6212e8): Spanish section 4 between markers, its executable twin `campaigns_select.py` (topic filter + one criterion per list, k = 5, Oja/creator_id tie-break, two followers baselines) and the `rule_identity` git/sha256 guard, with 17 passing tests on synthetic data.**

## Performance

- **Duration:** ~25 min (continuation after the Task 1 checkpoint; the checkpoint wait is excluded)
- **Started:** 2026-10-22 (continuation session, Task 1 already resolved)
- **Completed:** 2026-10-22T14:22:25Z
- **Tasks:** 3 (Task 1 checkpoint resolved by the user, Task 2 TDD, Task 3 rule commit)
- **Files modified:** 3 created, 0 modified

## Task 1 checkpoint answer

The user answered `approve`: terms 1-10 of the plan's Task 1 went into the committed rule exactly as written, with no edits. No recorded edit exists, so no locked decision D-07..D-17 is contradicted (price does not filter, the SOM and the Oja index do not decide membership, k = 5, no general weighted score).

## Accomplishments

- Rule text: `deliverables/03-oja-campanas.md` holds the title, `## 4. Regla de selección por campaña (fijada antes de calcular las listas)`, exactly one start and one end marker and the 16 bold-labelled terms; sections 1-3 and 5-7 are added later outside the markers.
- Rule as code: `analysis/campaigns_select.py` with `K = 5`, `TOPICS`, `DEPTH_COLUMNS`, `ENGAGEMENT_COLUMN`, `OBJECTIVES`, `OBJECTIVE_COLUMNS`, `CAMPAIGNS` and the ten functions; K, topic order, criterion columns and the 1/2 + 1/2 weights repeat the numbers of the text.
- Guard: `rule_identity()` refuses (SystemExit naming the file) an untracked file, a split commit, a select file that changed uncommitted or in a later commit, and changed text between the markers; it returns `rule_commit`, `rule_sha256` and `select_sha256`.
- Post-commit evidence on the real repo: `rule_identity()` returns rule_commit `a6212e89cdc654021cfda02d9d16237c8c21c332`, rule_sha256 `90113af5bf39142df419beb94a034d88352689ca0b691842892be515d9ccc5f0`, select_sha256 `1d1bfe771f0b217401a9dd98d170b0e49622a0ee2353d1bfec2f516d8e311c26`. Plan 03-05 records these as the CAMP-01/CAMP-02 evidence.

## Task Commits

1. **Task 1: approve or edit terms 1-10** - checkpoint, resolved `approve` by the user (no commit)
2. **Task 2: the rule end to end (tests, code, section 4)** - written under TDD, deliberately left uncommitted until the rule commit (user override of the commit policy, see Deviations)
3. **Task 3: the rule commit** - `a6212e89cdc654021cfda02d9d16237c8c21c332` (feat), a pathspec commit of exactly `deliverables/03-oja-campanas.md`, `analysis/campaigns_select.py` and `analysis/tests/test_campaigns_select.py`

**Plan metadata:** the `docs(03-02): complete campaign selection rule plan` commit that follows this file.

## TDD record (Task 2)

- **RED:** the 17 tests were written first. `campaigns_select.py` did not exist, so a names-only stub (empty constants, every function raising `NotImplementedError`) was written so the tests would collect and execute instead of dying at import. `pytest analysis/tests/test_campaigns_select.py -q` gave `17 failed` (assertions on the empty constants and `NotImplementedError` from the stub functions). Semantic assessment: every test ran and failed for the missing behavior, not for a syntax, import or fixture fault. pytest's report format is not one of the `gsd_run check tdd-red-evidence` adapters, so the classifier was not run; the evidence is the console report above.
- **GREEN:** the real module replaced the stub; `17 passed in 0.63s`.
- **REFACTOR:** none.
- **Commits:** no separate RED/GREEN commits, by explicit user instruction: separate commits would split the three rule files across commits and break the "added in one commit" invariant that `rule_identity` enforces. This is why the git log shows no `test(03-02)` commit.

## Files Created/Modified

- `analysis/campaigns_select.py` - the campaign rule as pure functions plus `rule_identity` (executable twin of section 4)
- `analysis/tests/test_campaigns_select.py` - 17 tests: terms on synthetic `Creadores`, guard in temporary git repositories
- `deliverables/03-oja-campanas.md` - Phase 3 fragment: title and section 4 (the rule between markers)

## Decisions Made

- Terms 1-10 approved as written (`approve`); the 16 labels of section 4 carry them with the wording of the plan.
- `_added_commit` is reimplemented in `campaigns_select.py` (bytes output, SystemExit naming the file) rather than imported from `som_stage.py`, which imports the C-binary drivers and would couple the committed rule to the Kohonen stage.
- `shortlist` validates the objective and `topic_members` the campaign (ValueError on an unknown name); the pairing of campaign and objective is the `CAMPAIGNS` table, not enforced in `shortlist`.

## Deviations from Plan

### Instruction overrides (not auto-fixes)

**1. Executor makes the commits (user's explicit instruction)**
- **Plan said:** "the executor never commits"; Task 3 is a `checkpoint:human-action` where the user commits by hand.
- **Done instead:** the user's updated policy for this continuation: the executor makes the rule commit itself, still as a single pathspec commit of exactly the three rule files, after verifying the index was empty, with the message `feat(03-02): commit the campaign selection rule (section 4) and its executable twin` and the `Co-Authored-By` trailer. The plan's post-commit verifications were run unchanged and pass (SAME_RULE_COMMIT_OK, RULE_COMMIT_FILES_OK, `rule_identity` on the real repo, `analysis/campaigns.py` and `analysis/results/campaigns/` absent).
- **Consequence:** the plan's acceptance line "nothing is staged by the executor" held until the moment of the rule commit; `git diff --cached` was empty before staging only the three files.

**2. RED stub before the tests (Rule 3 - process)**
- **Found during:** Task 2
- **Issue:** with no module, the tests would fail at import (INVALID_RED, collection error).
- **Fix:** a throwaway names-only stub made them execute and fail; it was overwritten by the real module before anything was committed.
- **Files modified:** `analysis/campaigns_select.py` (same file, never committed in stub form)

---

**Total deviations:** 0 auto-fixed bugs; 1 commit-policy override by user instruction, 1 RED-stub process note
**Impact on plan:** none on the rule content. The single-commit invariant of the rule files holds.

## Issues Encountered

None.

## Known Stubs

None. (The RED-phase stub was replaced before the commit.)

## Threat Flags

None. The git calls in `rule_identity` are subprocess argument lists with `cwd` and no shell (T-03-05); the commit hash passed to `git show` comes from `git log` and is checked as 40 hex first.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plans 03-03 to 03-06 can import `campaigns_select` and must call `rule_identity()` before reading any data; `analysis/campaigns.py` (plan 03-05) must record `rule_commit`, `rule_sha256` and `select_sha256`.
- Do not edit the text between the markers or `analysis/campaigns_select.py` from now on (D-07); a later edit makes `rule_identity` refuse.
- Plan 03-04 inserts sections 1-3 between the title and section 4, outside the markers; plans 03-05 and 03-06 add sections 5-7 below.

## Self-Check: PASSED

- `analysis/campaigns_select.py`, `analysis/tests/test_campaigns_select.py`, `deliverables/03-oja-campanas.md`: FOUND
- Rule commit `a6212e89cdc654021cfda02d9d16237c8c21c332`: FOUND (ancestor of HEAD)
- `pytest analysis/tests/test_campaigns_select.py -q`: 17 passed
- `rule_identity()` on the real repo: passes; `analysis/campaigns.py` and `analysis/results/campaigns/`: absent

---
*Phase: 03-oja-y-decisiones-de-campa-a*
*Completed: 2026-10-22*
