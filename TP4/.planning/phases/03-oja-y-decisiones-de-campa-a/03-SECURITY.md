---
phase: "03"
slug: "oja-y-decisiones-de-campa-a"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-26"
---

# Phase 03 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| config.json -> neuron binary (oja) | user-edited parameters drive allocation sizes and the update rule | epochs, eta0, eta_final |
| results/ files -> Python analysis | run outputs and PCA tables read back as evidence | CSV/JSON results |
| git history -> rule_identity | commit hashes and file contents at the rule commit | rule text, campaigns_select.py |
| Python -> subprocesses (git, binary, map_creator) | commands built from module constants and argparse paths | argument lists |
| repo -> deliverables/03-oja-campanas.md | report lines pasted into the written fragment | course data (creator handles, numbers) |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-03-SC | Tampering | package installs | high | mitigate | No new package in plans 03-01 to 03-06; only the Phase 1 pins of `analysis/requirements.txt` | closed |
| T-03-01 | Denial of service / Tampering | read_params in oja.c | medium | mitigate | `EPOCHS_MAX 100000` checked before allocation (`neuron/models/oja.c:15,48-49`) | closed |
| T-03-02 | Tampering | Oja update and eta schedule | medium | mitigate | `eta_final` range and `eta0_max_x2 < STABILITY_MAX` (`neuron/models/oja.c:69,73`); non-finite weight fails the run (`oja.c:139`); non-finite metrics written as null (`neuron/io/results.c:116-121`) | closed |
| T-03-03 | Tampering (memory safety) | write_trace header and per-epoch copies | medium | mitigate | `make -C neuron debug` builds with `-fsanitize=address,undefined` (`neuron/Makefile:65-66`) | closed |
| T-03-04 | Repudiation / Tampering | rule text and campaigns_select.py | high | mitigate | `rule_identity` (`analysis/campaigns_select.py:190`) refuses split commits and any change of code or rule text; ran clean on 2026-10-26 (rule commit a6212e8) | closed |
| T-03-05 | Elevation of privilege | git calls in rule_identity | low | mitigate | `subprocess.run(["git", *args], cwd=...)` without shell; commit checked against `_HEX40` (`analysis/campaigns_select.py:65,175,185`) | closed |
| T-03-06 | Tampering | rule commit sweeping unrelated changes | medium | mitigate | Pathspec commit of the three files, verified at Task 3 of 03-02 (SUMMARY) | closed |
| T-03-07 | Tampering | read_oja_run, read_pca | medium | mitigate | Header, width and file checks raise `ValueError` naming the file (`analysis/oja.py:78-94`) | closed |
| T-03-08 | Tampering | sign convention Oja vs PCA | medium | mitigate | `w @ v1 > 0` asserted on the real data (`analysis/tests/test_oja.py:68`); orientation fixed in C | closed |
| T-03-09 | Elevation of privilege | run_series / som.run_binary | low | mitigate | Argument lists, no `shell=True` in `oja.py`, `sweep.py`, `som.py` | closed |
| T-03-10 | Tampering / Repudiation | campaigns.py on a changed rule | high | mitigate | `rule_identity()` is the first call of main (`analysis/campaigns.py:445`); `test_main_refuses_without_rule` (`analysis/tests/test_campaigns.py:82`) | closed |
| T-03-11 | Information disclosure | creator names in outputs | low | accept | See Accepted Risks Log (AR-03-01) | closed |
| T-03-12 | Tampering | index.csv, scores.csv, selection.json | medium | mitigate | Creator order checked against `datos/creadores.csv` (`analysis/campaigns.py:135-151`); `require_same_rule` on the Phase 2 rule and `grid_k` match (`campaigns.py:189,197`) | closed |
| T-03-13 | Spoofing / Repudiation | the synthetic creator | medium | mitigate | `SYN001`, `@sintetico_demo`, `synthetic: true` (`analysis/maintenance_demo.py:37-38`); written only under `analysis/results/maintenance/` | closed |
| T-03-14 | Elevation of privilege | map_with_cli | low | mitigate | `subprocess.run([sys.executable, str(MAP_CREATOR), ...])` without shell (`analysis/maintenance_demo.py:91`) | closed |
| T-03-15 | Tampering | evidence() and sections 1-3 | medium | mitigate | SECTION3_OK / SECTIONS123_OK at plan time; fragment frozen by sha256 guard and clean in `git status`; no "mejor" in `deliverables/03-oja-campanas.md` | closed |
| T-03-16 | Tampering | rule markers while sections 1-3 were inserted | high | mitigate | `rule_identity()` passes on 2026-10-26 (rule sha256 90113af5…, select sha256 1d1bfe77…) | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-03-01 | T-03-11 | Creator names come from the tracked `datos/creadores.csv` of the statement; no personal data beyond what the course provides | plan 03-05 | 2026-10-26 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-26 | 17 | 17 | 0 | /gsd-secure-phase 03 (orchestrator, ASVS L1 grep-depth; register authored at plan time, auditor skipped by the short-circuit rule) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-26
