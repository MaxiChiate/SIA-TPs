---
phase: 03
review: 03-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "The pre-registration guard does not pin the code it depends on (frozen file)"
  - id: WR-02
    severity: warning
    disposition: open
    title: "The Oja alignment and orientation \"gates\" are never enforced"
  - id: WR-03
    severity: warning
    disposition: open
    title: "Section 5.5 presents a result guaranteed by construction as evidence"
  - id: WR-04
    severity: warning
    disposition: open
    title: "`make campaigns` and `make maintenance` re-run every upstream stage on each call"
  - id: WR-05
    severity: warning
    disposition: open
    title: "The drift demo cannot exercise the retrain branch and the threshold is an in-sample statistic"
  - id: IN-01
    severity: info
    disposition: open
    title: "Unused import"
  - id: IN-02
    severity: info
    disposition: open
    title: "Magic constants and hard-coded counts in the maintenance demo"
  - id: IN-03
    severity: info
    disposition: open
    title: "Duplicated helpers across three modules"
  - id: IN-04
    severity: info
    disposition: open
    title: "Cross-module use of private names"
  - id: IN-05
    severity: info
    disposition: open
    title: "Path from `selection.json` is joined without validation"
  - id: IN-06
    severity: info
    disposition: open
    title: "Palette built from a list with a repeated key, and a hard-coded count in a legend"
  - id: IN-07
    severity: info
    disposition: open
    title: "NaN or inf can leak into JSON or reports"
  - id: IN-08
    severity: info
    disposition: open
    title: "Frozen file: git output depends on the user's git configuration"
  - id: IN-09
    severity: info
    disposition: open
    title: "Reader robustness and test coverage gaps"
open: 14
total: 14
recorded: 2026-10-22T15:05:10.423147Z
---

# Phase 03: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| WR-05 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |
| IN-07 | info | open | - |
| IN-08 | info | open | - |
| IN-09 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved.
