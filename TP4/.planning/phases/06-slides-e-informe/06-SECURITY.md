---
phase: "06"
slug: "slides-e-informe"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-26"
---

# Phase 06 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| PyPI -> .venv | third-party code enters the environment through pip | Python packages (Markdown==3.11) |
| Makefile recipes -> shell | recipes run project scripts with the user's permissions | local commands |
| result JSON/CSV -> HTML and slide files | data values interpolated into pages that will be published | course data (creator handles, numbers) |
| repo text (fragments, DECISIONS.md, notes.md) -> published HTML | trusted, versioned repo text rendered by Markdown | course prose, low sensitivity |
| figure code -> published evidence | figures must match the pre-registered results | SVG/PNG figures |
| human reply -> QUESTIONS texts and anchors | text typed by the user that becomes published quotes and links | enunciado quotes |
| repo docs -> anyone who clones | instructions people will run | README.md, CLAUDE.md, DECISIONS.md |
| local build -> claude.ai Artifacts | both deliverables leave the machine | informe HTML, slide deck, PNG assets |
| Artifact link -> teacher | who can open the published pages | private by default; shared by the owner |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-06-SC | Tampering | pip install of Markdown | high | mitigate | `analysis/requirements.txt:6` pins `Markdown==3.11`; legitimacy checkpoint in 06-01; plans 06-02 to 06-12 install nothing | closed |
| T-06-01 | Tampering | pre-registered rules and results | high | mitigate | Sentinel recipes only call the guarded drivers; `git status --porcelain` on `deliverables/`, the four `*_select.py` and `series_*.json` is empty | closed |
| T-06-02 | Denial of service | make results wall time | low | accept | See Accepted Risks Log (AR-06-01) | closed |
| T-06-03 | Tampering | stale results after a code change | medium | accept | See Accepted Risks Log (AR-06-02) | closed |
| T-06-04 | Information disclosure | smoke deck visibility | medium | mitigate | Published at default private visibility (06-02 SUMMARY) | closed |
| T-06-05 | Information disclosure | content of the smoke deck | low | accept | See Accepted Risks Log (AR-06-03) | closed |
| T-06-06 | Repudiation | decision record | low | accept | See Accepted Risks Log (AR-06-04) | closed |
| T-06-07 | Information disclosure | DECISIONS.md content | low | accept | See Accepted Risks Log (AR-06-05) | closed |
| T-06-08 | Tampering | informe.py interpolation | high | mitigate | `html.escape` on alt, caption, question text and facts (`analysis/informe.py:167-268`); `<b>` test in `analysis/tests/test_informe.py` | closed |
| T-06-09 | Tampering | embedded figures | medium | mitigate | Figures only as `img` data URIs (`analysis/informe.py:167`); build refuses any `<script` (`analysis/informe.py:625`) | closed |
| T-06-10 | Information disclosure | build stamp and page text | medium | mitigate | `HOME_PATH` and `EMAIL` checks before writing (`analysis/informe.py:58-59,634-637`) | closed |
| T-06-11 | Denial of service | page size | low | mitigate | `MAX_BYTES = 12_000_000` (`analysis/informe.py:54,628`) | closed |
| T-06-12 | Tampering | SOM evidence (grid rule) | high | mitigate | `som_figures.py:339` runs `require_same_rule`; rule, series and fragments untouched | closed |
| T-06-13 | Repudiation | slide vs report figure divergence | low | accept | See Accepted Risks Log (AR-06-06) | closed |
| T-06-14 | Tampering | campaign rule and selector | high | mitigate | `campaigns.py:445` runs `campaigns_select.rule_identity`; `campaigns_select.py` untouched | closed |
| T-06-15 | Denial of service | accidental SOM stage-1 rerun | low | mitigate | Deliverable paths call `analysis/campaigns.py` directly through the sentinel (`Makefile:195-196`), not the phony `campaigns` target | closed |
| T-06-16 | Tampering | Hopfield code identity and QR protocol | high | mitigate | `require_same_rule` and `require_same_code` in `hopfield_qr_figures.py:481-510` and `hopfield_figures.py:698` | closed |
| T-06-17 | Repudiation | numbers shown vs results | medium | mitigate | `facts.check_fragment_numbers` (`analysis/facts.py:497`), run inside the informe build (`analysis/informe.py:673`) | closed |
| T-06-18 | Repudiation | literal question texts | medium | mitigate | `QUESTIONS_CHECKED_AGAINST_PDF = True` (`analysis/deliverables_manifest.py:29`) set after the blocking-human checkpoint of 06-08 | closed |
| T-06-19 | Tampering | creator handles from CSV | low | accept | See Accepted Risks Log (AR-06-07) | closed |
| T-06-20 | Tampering | glossary titles in link attributes | medium | mitigate | `html.escape(..., quote=True)` on titles (`analysis/informe.py:531`) | closed |
| T-06-21 | Tampering | raw HTML inside fragments | low | accept | See Accepted Risks Log (AR-06-08) | closed |
| T-06-22 | Repudiation | report numbers vs results | medium | mitigate | Drift gate in the build (`analysis/informe.py:673`) | closed |
| T-06-23 | Denial of service | page size above 16 MB | low | mitigate | `MAX_BYTES` and the PNG fallback above `EMBED_SVG_MAX` (`analysis/informe.py:54-55,157`) | closed |
| T-06-24 | Tampering | slide text interpolation | high | mitigate | `html.escape` on every filled text (`analysis/slides.py:564-589`); `<b>`/`<script>` tests in `analysis/tests/test_slides.py` | closed |
| T-06-25 | Information disclosure | slide files and deck.json | medium | mitigate | Home-path and email refusal before writing (`analysis/slides.py:640-644`) | closed |
| T-06-26 | Repudiation | slide numbers vs results | medium | mitigate | Unknown fact key stops the build (`analysis/facts.py:405`); missing slide figure stops it (`analysis/slides.py`) | closed |
| T-06-27 | Tampering | reproduction instructions vs guards | medium | mitigate | README only describes deleting a results folder; guards keep refusing changed rules | closed |
| T-06-28 | Information disclosure | README.md, CLAUDE.md | medium | mitigate | `analysis/tests/test_repro_docs.py:29-30` scans the three documents for home paths and emails | closed |
| T-06-29 | Repudiation | docs drifting from Makefile and manifest | low | mitigate | `check_make_targets` and the figure-row check in `analysis/tests/test_repro_docs.py` | closed |
| T-06-30 | Information disclosure | Artifact visibility | medium | mitigate | Both Artifacts published private; sharing decided by the owner (06-UAT test 4 passed) | closed |
| T-06-31 | Repudiation | published numbers vs verified results | high | mitigate | Blocking-human Phase 3 decision recorded as the waiver line in `CLAUDE.md:114`; final build gated on it | closed |
| T-06-32 | Repudiation | question texts and answering-section links | medium | mitigate | Both flags True (`analysis/deliverables_manifest.py:29,34`); informe build refuses otherwise (`analysis/informe.py:658-665`) | closed |
| T-06-33 | Repudiation | question table in the built informe | medium | mitigate | Build raises `SystemExit` unless both flags are True (`analysis/informe.py:658-665`) | closed |
| T-06-34 | Repudiation | SOM numbers vs open Phase 2 findings | high | mitigate | Blocking-human Phase 2 decision recorded as the waiver line in `CLAUDE.md:115` naming the 11 open findings; guarded files untouched | closed |
| T-06-35 | Repudiation | question -> answering-section links | medium | mitigate | `ANSWER_SECTIONS_CHECKED = True` (`analysis/deliverables_manifest.py:34`) set after the blocking-human checkpoint of 06-08 | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-06-01 | T-06-02 | A full `make results` runs once; sentinels skip finished steps afterwards; documented in README | plan 06-01 | 2026-10-26 |
| AR-06-02 | T-06-03 | Sentinels do not detect stale results by design; README documents deleting `analysis/results/<step>` to force a rerun | plan 06-01 | 2026-10-26 |
| AR-06-03 | T-06-05 | The smoke deck held only the aggregate SOM map and a cover title | plan 06-02 | 2026-10-26 |
| AR-06-04 | T-06-06 | Each DECISIONS.md entry links to the CONTEXT.md that recorded it; the file is versioned and tested | plan 06-03 | 2026-10-26 |
| AR-06-05 | T-06-07 | DECISIONS.md holds course data only; no paths, emails or credentials | plan 06-03 | 2026-10-26 |
| AR-06-06 | T-06-13 | Slide and report variants use the same plot function and data; only size, type scale and captions differ | plan 06-05 | 2026-10-26 |
| AR-06-07 | T-06-19 | Facts are plain strings; escaping happens at render in the informe and slides builds | plan 06-08 | 2026-10-26 |
| AR-06-08 | T-06-21 | Fragments are versioned team-written text under sha256 guards; HTML comments are stripped | plan 06-09 | 2026-10-26 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-26 | 36 | 36 | 0 | /gsd-secure-phase 06 (orchestrator, ASVS L1 grep-depth; register authored at plan time, auditor skipped by the short-circuit rule) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-26
