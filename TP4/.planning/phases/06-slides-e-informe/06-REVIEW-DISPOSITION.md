---
phase: 06
review: 06-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "facts.py fails with a bare StopIteration/ValueError instead of the promised \"run make ...\" message"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "`qr.noise_high` is derived from the data but slides and informe pair it with hard-coded 0,45 / 0,50 facts"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "The \"som-rule\" slide describes the grid-selection rule incompletely"
  - id: WR-04
    severity: warning
    disposition: fixed
    title: "Qualitative conclusions are hard-coded; D-11 and the drift pins guard only numbers"
  - id: WR-05
    severity: warning
    disposition: fixed
    title: "Numbers typed in slide notes contradict D-11 and the project convention"
  - id: WR-06
    severity: warning
    disposition: fixed
    title: "`summary_section` and `notes_section` put template text into HTML without escaping"
  - id: WR-07
    severity: warning
    disposition: fixed
    title: "Documents contradict each other on delivery state and on the slides PDF"
  - id: WR-08
    severity: warning
    disposition: fixed
    title: "Slide-variant branches of several drivers have no test"
  - id: IN-01
    severity: info
    disposition: open
    title: "`slides._figure_height` ignores tables"
  - id: IN-02
    severity: info
    disposition: open
    title: "`write_deck` deletes the previous output before writing the new one; asset-map input is under-validated"
  - id: IN-03
    severity: info
    disposition: open
    title: "Percentage formatting is inconsistent across fact families"
  - id: IN-04
    severity: info
    disposition: open
    title: "The \"Regla fijada de antemano\" tag is on `camp-futbol` although its notes say the recommendation is a judgment"
  - id: IN-05
    severity: info
    disposition: open
    title: "Permutation p-values shown as equalities"
  - id: IN-06
    severity: info
    disposition: open
    title: "`make informe` alone produces a different page from `make deliverables`"
open: 6
total: 14
recorded: 2026-10-26T03:24:07.127Z
---

# Phase 06: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | fixed | facts._first/_nonempty: every lookup and max/min stops with the make step; tests in test_facts.py |
| WR-02 | warning | fixed | qr.noise_high is the fixed QR_HIGH_NOISE (0,45) with qr.*_at_high from the same row; load_facts stops if the table does not end at QR_LAST_NOISE |
| WR-03 | warning | fixed | som-rule title and notes: among the grids that pass the filters the lowest QE-LOO wins; check_claims guards decided_by; needs republishing |
| WR-04 | warning | fixed | facts.check_claims stops the build when a result no longer supports the five qualitative sentences |
| WR-05 | warning | fixed | letters.flips_k*, set_size, alphabet_size, spur_flip_min/max and draft_matching_glyphs (drift pin on fragment 04) replace the typed numbers |
| WR-06 | warning | fixed | summary_section escapes the template; notes_section escapes & and < before Markdown; tests in test_informe.py |
| WR-07 | warning | fixed | D-14 rewritten (Artifact plus exported PDF, kept out of the repo); README and CLAUDE.md agree |
| WR-08 | warning | fixed | commit 46201f1: 8 synthetic-data tests of the slide variant (test_variants_som.py, test_variants_ej1.py, test_hopfield_qr_figures.py); legend clipping stays a visual check (06-VALIDATION.md) |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
