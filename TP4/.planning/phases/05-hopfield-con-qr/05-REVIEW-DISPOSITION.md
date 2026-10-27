---
phase: 05-hopfield-con-qr
review: 05-REVIEW.md
generated: 2026-10-25T00:00:00Z
---

# Phase 05 — Code Review Disposition Ledger

> One row per finding. Default disposition is `open` until a human or fixer records otherwise.

| ID | Title | Severity | Disposition | Source |
|----|-------|----------|--------------|--------|
| WR-01 | `hopfield_qr_select._git_stdout` can crash with a raw traceback instead of the guaranteed clean refusal | warning | open | |
| WR-02 | The five-QR ordering is duplicated across three modules with no test or runtime check tying them together | warning | open | |
| IN-01 | Duplicated sha256/git-identity boilerplate across three modules | info | open | |
| IN-02 | `plot_energy_trace` can mislabel its primary y-axis if only one dynamical rule has data | info | open | |
| IN-03 | `neuron/README.md` (outside this review's file list) was not updated for the new `rule: "pinv"` option | info | open | |

**Counts:** 0 critical, 2 warning, 3 info — 0 fixed, 0 skipped, 5 open.

No BLOCKER findings. This is advisory — the phase is not blocked on these. Consider addressing WR-01 (exception handling parity with sibling `_git_text` helpers) and WR-02 (an assertion tying `qr.SOURCES`/`hopfield_qr_select.PNG_FILES` ordering together) in a future pass.
