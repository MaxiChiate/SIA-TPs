---
phase: 04
review: 04-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "\"Every run is recomputed in numpy\" is true for about 3% of the trials, and for none of the capacity recall numbers"
  - id: WR-02
    severity: warning
    disposition: open
    title: "The pre-registration guard does not cover the code that defines success, and `run.json` records no code identity"
  - id: IN-01
    severity: info
    disposition: open
    title: "Error line number is off by one for a doubled blank line (frozen file)"
  - id: IN-02
    severity: info
    disposition: open
    title: "Alphabet file is not protected against CRLF checkouts (frozen file parses it)"
  - id: IN-03
    severity: info
    disposition: open
    title: "`prepare_letters.py --show` help text says \"before writing\" but prints after writing (frozen file)"
  - id: IN-04
    severity: info
    disposition: open
    title: "The \"every refusal is a SystemExit ending in (D-04)\" contract has two holes"
  - id: IN-05
    severity: info
    disposition: open
    title: "Incremental async energy is only valid for symmetric W, and the header does not say so"
  - id: IN-06
    severity: info
    disposition: open
    title: "Hard-coded design numbers in figure captions and N in the recall plot"
  - id: IN-07
    severity: info
    disposition: open
    title: "`plot_max_overlap_hist` derives bar width and N from the first histogram bins"
  - id: IN-08
    severity: info
    disposition: open
    title: "Small statistical and CLI inaccuracies in the driver"
---

# Phase 04 — Code review disposition

All findings start `open`. WR-01/WR-02 and the frozen-file items (IN-01, IN-03, IN-04) need a decision from the user.
