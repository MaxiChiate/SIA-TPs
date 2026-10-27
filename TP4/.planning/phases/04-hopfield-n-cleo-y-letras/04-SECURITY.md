---
phase: "4"
slug: "hopfield-n-cleo-y-letras"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-23"
---

# Phase 4 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| config JSON → C reader | `neuron` reads a user-written config (subset, trace_trials, p, n_subsets, noise levels) | untrusted sizes and indices |
| alphabet text → parser | `scripts/letters.py` parses `datos/letters/alphabet_5x5.txt` | glyph bitmaps |
| rule commit → drivers | `analysis/hopfield_select.py` guards the pre-registered rule, alphabet and selection code | integrity of the pre-registration |
| C results → Python | `analysis/hopfield.py` re-reads every CSV/JSON the C binary writes | result integrity |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-04-01 | Tampering / DoS | read_params (subset, trace_trials, n_cols) | medium | mitigate | `NEURONS_MAX 2048`, subset range/distinct checks before allocation; refusals in `test_hopfield_run`; ASan/UBSan via `make -C neuron debug` | closed |
| T-04-02 | DoS | trials table, trace buffer | medium | mitigate | `TRIAL_ROWS_MAX 2000000`, `TRACE_ROWS_MAX 1000000`, `TABLE_DOUBLES_MAX` in `neuron/models/hopfield.c` | closed |
| T-04-03 | Tampering | async energy, classification | medium | mitigate | `energy_increases` metric; incremental vs from-scratch energy and classifier branches in `test_hopfield_core`; numpy recomputation in `analysis/hopfield.py` | closed |
| T-04-04 | Tampering | parse_alphabet | medium | mitigate | D-02 and inverse-pair refusals in `scripts/letters.py`; `test_refuses_malformed` | closed |
| T-04-05 | Repudiation | alphabet_pm1.meta.json | low | mitigate | `source_sha256` in the meta, compared with the committed alphabet by `hopfield_letters._check_prepared_alphabet` | closed |
| T-04-06 | Tampering | rule_identity / require_same_rule | high | mitigate | `analysis/hopfield_select.py` guard; ten identity tests in `test_hopfield_select.py` | closed |
| T-04-07 | Repudiation | rule commit | high | mitigate | commit 23c3563 after the glyph-by-glyph checkpoint; identity recorded in selection.json/run.json | closed |
| T-04-08 | Information disclosure | alphabet, checkpoint, report CLI | high | mitigate | draft discarded (D-04b); `test_report_is_bitmap_only`; Divulgación item in section 3 states the 25/26 coincidence and the tie-break history | closed |
| T-04-09 | Elevation of privilege | git calls | low | mitigate | argument lists, no `shell=True` anywhere in `analysis/` or `scripts/` | closed |
| T-04-10 | DoS | capacity read_params | medium | mitigate | `CAPACITY_ROWS_MAX 200000`, `CAPACITY_SAMPLES_MAX 10000`, `CAPACITY_WORK_MAX 50000000`; refusals in `test_hopfield_capacity` | closed |
| T-04-11 | Tampering | capacity/trials/trace/states CSVs | medium | mitigate | `check_recall`/`check_capacity` recompute values; tampering tests in `test_hopfield.py` | closed |
| T-04-12 | Tampering | hopfield_letters.run | high | mitigate | `rule_identity` first, then prepared CSV sha256 vs committed alphabet; refusal tests | closed |
| T-04-13 | Tampering | run_series / aggregates | medium | mitigate | `HopfieldCheckError` stops the driver and removes the output | closed |
| T-04-14 | DoS / data loss | rmtree of the output | low | mitigate | removed path is `results_dir / RESULTS_SUBDIR`, from constants; tests use tmp_path | closed |
| T-04-15 | Tampering | hopfield_figures.draw | medium | mitigate | `require_same_rule` before drawing; `test_draw_refuses_changed_rule` | closed |
| T-04-16 | Repudiation | energy panels | medium | mitigate | panels fixed by index; `test_energy_panels_are_the_first_traced_trials` | closed |
| T-04-17 | Repudiation | section 6, capacity_by_p.svg | medium | mitigate | 0,138·N and 0,15·N labelled "orden de magnitud" in figure legend and text | closed |
| T-04-18 | Repudiation | section 7, spurious.svg | medium | mitigate | figure and text read only spurious.json picks; `test_plot_spurious_picks_and_absence` | closed |
| T-04-19 | Tampering | deliverable rule region | high | mitigate | identity re-run after every edit; diff against 23c3563 has no removed lines; byte-identical rerun | closed |
| T-04-20 | Tampering | alphabet_5x5.txt | high | mitigate | glyphs drawn before reading the research, user approval per glyph, sha256 compared with the draft (04-03-SUMMARY) | closed |
| T-04-21 | Repudiation | capacity_by_p extension | medium | mitigate | extension driven only by frozen `capacity_needs_next_p`; rows flagged base/extension; `test_capacity_extension_follows_rule` | closed |
| T-04-SC | Tampering | package installs | high | mitigate | no new package; `analysis/requirements.txt` unchanged since 23c3563 | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

No accepted risks.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-23 | 22 | 22 | 0 | orchestrator (ASVS L1 short-circuit: register authored at plan time, all mitigations located) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-23
