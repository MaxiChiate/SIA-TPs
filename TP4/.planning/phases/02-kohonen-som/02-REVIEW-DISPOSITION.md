---
phase: 02
review: 02-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "\"Equality passes\" at the filter thresholds is not guaranteed under floating point (PRE-REGISTERED)"
  - id: WR-02
    severity: warning
    disposition: open
    title: "The rule guard never compares the current rule text or code with the rule commit; `rule_commit` can mislabel what actually ran"
  - id: WR-03
    severity: warning
    disposition: open
    title: "Stage-2 robustness verdict never checks that the series is on the chosen k"
  - id: WR-04
    severity: warning
    disposition: open
    title: "Gaussian kernel writes NaN prototypes (and exits 0) for a tiny `radius_final`"
  - id: IN-01
    severity: info
    disposition: open
    title: "QE-LOO never discriminates between eligible grids, so \"gana la de menor QE-LOO\" is \"gana la k más grande que pasa los filtros\" (PRE-REGISTERED)"
  - id: IN-02
    severity: info
    disposition: open
    title: "`measure()` has a dead allocation branch with an unchecked `calloc`"
  - id: IN-03
    severity: info
    disposition: open
    title: "Three copies of the same CSV writer and two of the same decimal formatter"
  - id: IN-04
    severity: info
    disposition: open
    title: "`plot_regions` has an unused parameter and reaches into a private name"
  - id: IN-05
    severity: info
    disposition: open
    title: "`test_umatrix_2x2` builds `expected` twice, the second time overwriting entries with literals"
  - id: IN-06
    severity: info
    disposition: open
    title: "LOO fold files and `read_matrix` assume the input has no blank or quoted lines"
  - id: IN-07
    severity: info
    disposition: open
    title: "`read_run` raises bare `ValueError` from `int()` / `float()` without naming the file"
open: 11
total: 11
recorded: 2026-10-21T18:17:49.367Z
---

# Phase 02: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |
| IN-07 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
