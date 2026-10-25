---
phase: "6"
slug: "slides-e-informe"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-25"
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (pinned in `analysis/requirements.txt`) |
| **Config file** | none — `analysis/tests/conftest.py` adds `analysis/` and `scripts/` to `sys.path` |
| **Quick run command** | `.venv/bin/python -m pytest analysis/tests/test_facts.py analysis/tests/test_deliverables_manifest.py analysis/tests/test_informe.py analysis/tests/test_slides.py analysis/tests/test_repro_docs.py -q` |
| **Full suite command** | `.venv/bin/python -m pytest analysis/tests -q` (baseline: 230 passed in 14.4 s) |
| **Estimated runtime** | ~20 seconds |

Tests must not require the unversioned results: use small synthetic result folders in `tmp_path`; real-results checks run as build-time assertions inside `make deliverables`.

---

## Sampling Rate

- **After every task commit:** Run the quick run command
- **After every plan wave:** Run the full suite command
- **Before `/gsd-verify-work`:** Full suite green, plus `make deliverables` on real results, plus both published Artifact URLs opened by the user
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-T2 | 06-01 | 1 | DELIV-02, DELIV-03 | T-06-SC | Markdown==3.11 installed only after the blocking-human legitimacy checkpoint (06-01-T1) | env | `.venv/bin/python -c 'import importlib.metadata as m; assert m.version("Markdown") == "3.11"'` | n/a | ⬜ pending |
| 06-01-T3 | 06-01 | 1 | DELIV-03 | T-06-01 | sentinel recipes call the guarded drivers, never edit rules | integration | sentinel loop (SENTINELS_OK) + `make -n results` lists no Python step (RESULTS_IDEMPOTENT) | n/a | ⬜ pending |
| 06-02-T2 | 06-02 | 1 | DELIV-01 | T-06-04 | smoke deck kept private | doc check | FORMAT_DOC_OK (frontmatter keys of 06-ARTIFACT-FORMAT.md) | ❌ W1 (written by 06-02-T1) | ⬜ pending |
| 06-03-T2 | 06-03 | 1 | DELIV-03 | — | N/A | doc check | DECISIONS_COVER_OK (D-ID sets equal CONTEXT.md, pitfalls and REQ IDs covered) | ❌ W1 | ⬜ pending |
| 06-04-T1 | 06-04 | 2 | DELIV-02 | T-06-08, T-06-09, T-06-10, T-06-11 | facts escaped; figures only as img data URIs; no home paths or emails; size ceiling | e2e (tracer) | `make informe` + TRACER_OK | ❌ W2 | ⬜ pending |
| 06-04-T2 | 06-04 | 2 | DELIV-02 | T-06-08 | escape of a "<b>" value; no script element; no skeleton tags | unit | `.venv/bin/python -m pytest analysis/tests/test_facts.py analysis/tests/test_informe.py -q` | ❌ W2 | ⬜ pending |
| 06-05-T1 | 06-05 | 2 | DELIV-01 | T-06-12 | report SVG bytes unchanged | unit + integration | `.venv/bin/python -m pytest analysis/tests/test_plots_style.py -q` + `shasum -a 256 -c analysis/results/variant_baseline/som.sha256` | ❌ W2 | ⬜ pending |
| 06-05-T2 | 06-05 | 2 | DELIV-01 | T-06-12 | guarded SOM files untouched | integration | SLIDE_SOM_OK + GUARDED_UNTOUCHED | n/a | ⬜ pending |
| 06-06-T1 | 06-06 | 3 | DELIV-01 | T-06-14 | — | unit + integration | `.venv/bin/python -m pytest analysis/tests/test_variants_ej1.py -q` + EJ1_SLIDES_PCA_OJA | ❌ W3 | ⬜ pending |
| 06-06-T2 | 06-06 | 3 | DELIV-01 | T-06-14, T-06-15 | campaign rule untouched; no SOM stage-1 rerun | integration | EJ1_REPORT_BYTES_UNCHANGED + CAMPAIGN_RULE_UNTOUCHED | n/a | ⬜ pending |
| 06-07-T1 | 06-07 | 3 | DELIV-01 | T-06-16 | — | unit + integration | `.venv/bin/python -m pytest analysis/tests/test_hopfield_figures.py -q` + LETTER_SLIDES_OK | ✅ (extended) | ⬜ pending |
| 06-07-T2 | 06-07 | 3 | DELIV-01 | T-06-16 | Hopfield code identity untouched | unit + integration | `.venv/bin/python -m pytest analysis/tests/test_hopfield_qr_figures.py -q` + EJ2_REPORT_BYTES_UNCHANGED + HOPFIELD_CODE_UNTOUCHED | ❌ W3 | ⬜ pending |
| 06-08-T1 | 06-08 | 3 | DELIV-02, DELIV-03 | T-06-18 | question texts flagged False until the PDF checkpoint (06-08-T2); review sheet printed for it | unit + CLI | `.venv/bin/python -m pytest analysis/tests/test_deliverables_manifest.py -q` + MANIFEST_FULL_OK + REVIEW_SHEET_OK (`.venv/bin/python analysis/deliverables_manifest.py questions`) | ❌ W3 | ⬜ pending |
| 06-08-T2 | 06-08 | 3 | DELIV-02 | T-06-18 | blocking-human word-by-word comparison of the 25 texts with docs/Archivo SIATP 42026.pdf, before 06-09 builds the informe | manual (blocking-human checkpoint) | resume signal "approved" or `Q<id>: <texto>` lines, recorded in the checkpoint log | n/a | ⬜ pending |
| 06-08-T3 | 06-08 | 3 | DELIV-02, DELIV-03 | T-06-17, T-06-18 | reported texts applied verbatim and flag set True; fragment numbers pinned to JSON | unit + CLI | `.venv/bin/python -m pytest analysis/tests/test_facts.py analysis/tests/test_deliverables_manifest.py -q` + QUESTIONS_CHECKED_OK + `.venv/bin/python analysis/facts.py check` (DRIFT_OK) + FACTS_FULL_OK | ✅ (extended) | ⬜ pending |
| 06-09-T1 | 06-09 | 4 | DELIV-02 | T-06-22, T-06-23, T-06-33 | build refuses unchecked question texts (QUESTIONS_CHECKED_AGAINST_PDF not True); drift gate in build; no typed numbers in the summary; size ceiling | unit + e2e | `.venv/bin/python -m pytest analysis/tests/test_informe.py -q` + INFORME_FULL_OK | ✅ (extended) | ⬜ pending |
| 06-09-T2 | 06-09 | 4 | DELIV-02 | T-06-20 | glossary titles escaped; links never rewrite attributes | unit + e2e | JARGON_LINKED + SOURCES_UNTOUCHED | ✅ (extended) | ⬜ pending |
| 06-10-T1 | 06-10 | 4 | DELIV-01 | T-06-24, T-06-25, T-06-26 | slide text escaped; no home paths | unit + e2e | `.venv/bin/python -m pytest analysis/tests/test_slides.py -q` + DECK_OK | ❌ W4 | ⬜ pending |
| 06-10-T2 | 06-10 | 4 | DELIV-01 | T-06-26 | — | integration | SLIDES_REPRODUCIBLE (two builds, `diff -r`) | n/a | ⬜ pending |
| 06-11-T1 | 06-11 | 5 | DELIV-03 | — | N/A | integration | DELIVERABLES_REPRODUCIBLE (`make deliverables` twice, hashes equal) + NO_SLOW_RERUN | n/a | ⬜ pending |
| 06-11-T3 | 06-11 | 5 | DELIV-03 | T-06-28, T-06-29 | no home paths or emails in docs; no slides PDF in docs/ | unit | `.venv/bin/python -m pytest analysis/tests/test_repro_docs.py -q` + `make test` | ❌ W5 | ⬜ pending |
| 06-12-T2 | 06-12 | 6 | DELIV-01, DELIV-02, DELIV-03 | T-06-31, T-06-32 | final build after the Phase 3 decision (06-12-T1), guarded by QUESTIONS_CHECKED_AGAINST_PDF (set in 06-08) | integration | QUESTIONS_CHECKED_OK + FINAL_BUILD_OK + MAKE_TEST_OK | n/a | ⬜ pending |
| 06-12-T3 | 06-12 | 6 | DELIV-01, DELIV-02 | T-06-30 | link sharing per share_mode | manual (top-level session) | URLs present in README.md and CLAUDE.md; `make test` | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*"❌ Wn" in File Exists means the test or document is created by that wave's plan.*

---

## Wave 0 Requirements

- [ ] `analysis/tests/test_facts.py`, `test_informe.py` (06-04), `test_plots_style.py` (06-05), `test_variants_ej1.py` (06-06), `test_hopfield_qr_figures.py` (06-07), `test_deliverables_manifest.py` (06-08), `test_slides.py` (06-10), `test_repro_docs.py` (06-11)
- [ ] `analysis/facts.py`, `analysis/deliverables_manifest.py` (06-04 tracer, so tests have something to import)
- [ ] `Markdown==3.11` in `analysis/requirements.txt` after the human-verify checkpoint; installed via the pip fallback (06-01)
- [ ] `06-ARTIFACT-FORMAT.md` from the Slides probe (06-02)
- [ ] Populated `analysis/results/` from `make results` (06-01), so later waves verify on real results

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Published Slides Artifact opens and has one section per exercise | DELIV-01 | Publishing needs the top-level session's Artifact tool | Open the slides URL recorded in README; step through every slide |
| Published informe Artifact opens; question table links resolve | DELIV-02 | Same as above | Open the informe URL; click each question link |
| Literal enunciado quotes match the PDF | DELIV-02 | Accents were reconstructed from TeX escapes (research A6) | At the 06-08 Task 2 blocking-human checkpoint, before 06-09 builds the informe: compare each of the 25 lines printed by `.venv/bin/python analysis/deliverables_manifest.py questions` with `docs/Archivo SIATP 42026.pdf`, word by word and accent by accent; 06-08 Task 3 applies the corrections and sets `QUESTIONS_CHECKED_AGAINST_PDF = True` |
| `make deliverables` is byte-reproducible on real results | DELIV-03 | Needs the full, slow results chain | Run `make deliverables` twice and compare `sha256sum` of outputs |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
