---
phase: "6"
slug: "slides-e-informe"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-25"
validated: "2026-10-26"
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
| **Full suite command** | `.venv/bin/python -m pytest analysis/tests -q` (baseline at plan time: 230 passed in 14.4 s; 481 passed in 24.3 s on 2026-10-26) |
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
| 06-01-T2 | 06-01 | 1 | DELIV-02, DELIV-03 | T-06-SC | Markdown==3.11 installed only after the blocking-human legitimacy checkpoint (06-01-T1) | env | `.venv/bin/python -c 'import importlib.metadata as m; assert m.version("Markdown") == "3.11"'` | n/a | ✅ green |
| 06-01-T3 | 06-01 | 1 | DELIV-03 | T-06-01 | sentinel recipes call the guarded drivers, never edit rules | integration | sentinel loop (SENTINELS_OK) + `make -n results` lists no Python step (RESULTS_IDEMPOTENT) | n/a | ✅ green |
| 06-02-T2 | 06-02 | 1 | DELIV-01 | T-06-04 | smoke deck kept private | doc check | FORMAT_DOC_OK (frontmatter keys of 06-ARTIFACT-FORMAT.md) | ✅ | ✅ green |
| 06-03-T2 | 06-03 | 1 | DELIV-03 | — | N/A | doc check | DECISIONS_COVER_OK (D-ID sets equal CONTEXT.md, pitfalls and REQ IDs covered) | ✅ | ✅ green |
| 06-04-T1 | 06-04 | 2 | DELIV-02 | T-06-08, T-06-09, T-06-10, T-06-11 | facts escaped; figures only as img data URIs; no home paths or emails; size ceiling | e2e (tracer) | `make informe` + TRACER_OK | ✅ | ✅ green |
| 06-04-T2 | 06-04 | 2 | DELIV-02 | T-06-08 | escape of a "<b>" value; no script element; no skeleton tags | unit | `.venv/bin/python -m pytest analysis/tests/test_facts.py analysis/tests/test_informe.py -q` | ✅ | ✅ green |
| 06-05-T1 | 06-05 | 2 | DELIV-01 | T-06-12 | report SVG bytes unchanged | unit + integration | `.venv/bin/python -m pytest analysis/tests/test_plots_style.py -q` + `shasum -a 256 -c analysis/results/variant_baseline/som.sha256` | ✅ | ✅ green |
| 06-05-T2 | 06-05 | 2 | DELIV-01 | T-06-12 | guarded SOM files untouched | integration + unit | SLIDE_SOM_OK + GUARDED_UNTOUCHED; `.venv/bin/python -m pytest analysis/tests/test_variants_som.py -q` (plot_planes, plot_stage1_curves, plot_regions in both variants; added 2026-10-26, WR-08) | ✅ | ✅ green |
| 06-06-T1 | 06-06 | 3 | DELIV-01 | T-06-14 | — | unit + integration | `.venv/bin/python -m pytest analysis/tests/test_variants_ej1.py -q` + EJ1_SLIDES_PCA_OJA | ✅ | ✅ green |
| 06-06-T2 | 06-06 | 3 | DELIV-01 | T-06-14, T-06-15 | campaign rule untouched; no SOM stage-1 rerun | integration + unit | EJ1_REPORT_BYTES_UNCHANGED + CAMPAIGN_RULE_UNTOUCHED; `.venv/bin/python -m pytest analysis/tests/test_variants_ej1.py -q -k campaign` (plot_shortlists_biplot, plot_shortlists_som 1x4; added 2026-10-26, WR-08) | ✅ | ✅ green |
| 06-07-T1 | 06-07 | 3 | DELIV-01 | T-06-16 | — | unit + integration | `.venv/bin/python -m pytest analysis/tests/test_hopfield_figures.py -q` + LETTER_SLIDES_OK | ✅ (extended) | ✅ green |
| 06-07-T2 | 06-07 | 3 | DELIV-01 | T-06-16 | Hopfield code identity untouched | unit + integration | `.venv/bin/python -m pytest analysis/tests/test_hopfield_qr_figures.py -q` (slide plot_recovery and plot_shift added 2026-10-26, WR-08) + EJ2_REPORT_BYTES_UNCHANGED + HOPFIELD_CODE_UNTOUCHED | ✅ | ✅ green |
| 06-08-T1 | 06-08 | 4 | DELIV-02, DELIV-03 | T-06-18, T-06-35 | question texts and answering sections flagged False (QUESTIONS_CHECKED_AGAINST_PDF, ANSWER_SECTIONS_CHECKED) until the checkpoint (06-08-T2); review sheet printed for it, each question followed by its anchors with their section headings; runs after 06-06/06-07 rewrote the results it checks, and every slide=True figure's slide variant exists | unit + CLI | `.venv/bin/python -m pytest analysis/tests/test_deliverables_manifest.py -q` + MANIFEST_FULL_OK + REVIEW_SHEET_OK (`.venv/bin/python analysis/deliverables_manifest.py questions`) | ✅ | ✅ green |
| 06-08-T2 | 06-08 | 4 | DELIV-02 | T-06-18, T-06-35 | blocking-human word-by-word comparison of the 25 texts with docs/Archivo SIATP 42026.pdf, and confirmation that every linked section answers its question, before 06-09 builds the informe | manual (blocking-human checkpoint) | resume signal "approved", `Q<id>: <texto>` lines and/or `Q<id> secciones: <ancla>, ...` lines, recorded in the checkpoint log | n/a | ✅ green |
| 06-08-T3 | 06-08 | 4 | DELIV-02, DELIV-03 | T-06-17, T-06-18, T-06-35 | reported texts and section lists applied verbatim and both flags set True; fragment numbers pinned to JSON | unit + CLI | `.venv/bin/python -m pytest analysis/tests/test_facts.py analysis/tests/test_deliverables_manifest.py -q` + QUESTIONS_CHECKED_OK + `.venv/bin/python analysis/facts.py check` (DRIFT_OK) + FACTS_FULL_OK | ✅ (extended) | ✅ green |
| 06-09-T1 | 06-09 | 5 | DELIV-02 | T-06-22, T-06-23, T-06-33 | build refuses unchecked question texts or unconfirmed answering sections (QUESTIONS_CHECKED_AGAINST_PDF or ANSWER_SECTIONS_CHECKED not True); drift gate in build; no typed numbers in the summary; size ceiling | unit + e2e | `.venv/bin/python -m pytest analysis/tests/test_informe.py -q` + INFORME_FULL_OK | ✅ (extended) | ✅ green |
| 06-09-T2 | 06-09 | 5 | DELIV-02 | T-06-20 | glossary titles escaped; links never rewrite attributes | unit + e2e | JARGON_LINKED + SOURCES_UNTOUCHED | ✅ (extended) | ✅ green |
| 06-10-T1 | 06-10 | 5 | DELIV-01 | T-06-24, T-06-25, T-06-26 | slide text escaped; no home paths; every slide=True figure placed once or listed in UNPLACED_SLIDE_FIGURES | unit + e2e | `.venv/bin/python -m pytest analysis/tests/test_slides.py -q` + DECK_OK + FIGURES_PLACED_OK | ✅ | ✅ green |
| 06-10-T2 | 06-10 | 5 | DELIV-01 | T-06-26 | — | integration | SLIDES_REPRODUCIBLE (two builds, `diff -r`) | n/a | ✅ green |
| 06-11-T1 | 06-11 | 6 | DELIV-03 | — | N/A | integration | DELIVERABLES_REPRODUCIBLE (`make deliverables` twice, hashes equal) + NO_SLOW_RERUN | n/a | ✅ green |
| 06-11-T3 | 06-11 | 6 | DELIV-03 | T-06-28, T-06-29 | no home paths or emails in docs; no slides PDF in docs/ | unit | `.venv/bin/python -m pytest analysis/tests/test_repro_docs.py -q` + `make test` | ✅ | ✅ green |
| 06-12-T1 | 06-12 | 7 | DELIV-01, DELIV-02 | T-06-31, T-06-34 | blocking-human decision on Phase 3 verification and on the open Phase 2 review findings that touch the grid rule (WR-01, WR-02, WR-03, WR-04, IN-01) before publication | manual (blocking-human checkpoint) | resume signal with one Fase 3 and one Fase 2 answer, recorded in the checkpoint log | n/a | ✅ green |
| 06-12-T2 | 06-12 | 7 | DELIV-01, DELIV-02, DELIV-03 | T-06-31, T-06-32, T-06-34 | final build after the Phase 3 and Phase 2 decisions (06-12-T1), guarded by QUESTIONS_CHECKED_AGAINST_PDF and ANSWER_SECTIONS_CHECKED (set in 06-08), by 03-UAT.md complete or the Phase 3 waiver line, and by no SOM-rule finding left open unwaived | integration | QUESTIONS_CHECKED_OK + PHASE3_SETTLED_OK + PHASE2_SETTLED_OK + PHASE2_FILES_UNTOUCHED + FINAL_BUILD_OK + MAKE_TEST_OK | n/a | ✅ green |
| 06-12-T3 | 06-12 | 7 | DELIV-01, DELIV-02 | T-06-30 | link sharing per share_mode | manual (top-level session) | URLs present in README.md and CLAUDE.md; `make test` | n/a | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*"❌ Wn" in File Exists meant the test or document is created by that wave's plan; all exist now.*

Observed on 2026-10-26: all 55 `<automated>` blocks of plans 06-01 to 06-12 re-run from `TP4/` (`make venv` left out of 06-01-T2, only the installed `Markdown` version checked). 54 printed their token as written. 06-12-T2 PHASE2_SETTLED_OK looks for the literal waiver text "- Fase 2 (decisión 06-12): publicado con hallazgos abiertos", which commit `84166e4` reworded; the same check with the current prefix "- Fase 2 (decisión 06-12" prints PHASE2_SETTLED_OK and PHASE2_FILES_UNTOUCHED, and it passed as written at build time (06-12-SUMMARY). Other tokens: DECISIONS_COVER_OK 80, FACTS_FULL_OK 153, INFORME_FULL_OK 6924363, JARGON_LINKED 154, DRIFT_REAL_OK, DELIVERABLES_REPRODUCIBLE, FINAL_BUILD_OK, MAKE_TEST_OK. The published local builds were restored afterwards (deck.json `c6a74fc7…`, notes.md `6febb9a9…`, informe.html `73535142…`); the rest of `analysis/results/` is byte-identical except `oja/runs.json`, which `make oja` points at its new series folder.

Gap filled on 2026-10-26 (review WR-08): the slide branches of `som_figures.plot_planes`, `plot_stage1_curves`, `som_profiles.plot_regions`, `campaigns.plot_shortlists_biplot`, `plot_shortlists_som`, `hopfield_qr_figures.plot_recovery` and `plot_shift` were checked only on real results; 8 synthetic-data tests now draw both variants and assert the files, the slide aspect `SLIDE_FIGSIZE` (12.8 x 4.85) and that report and slide differ. They do not detect a clipped legend; that stays a visual check.

---

## Wave 0 Requirements

- [x] `analysis/tests/test_facts.py`, `test_informe.py` (06-04), `test_plots_style.py` (06-05), `test_variants_ej1.py` (06-06), `test_hopfield_qr_figures.py` (06-07), `test_deliverables_manifest.py` (06-08), `test_slides.py` (06-10), `test_repro_docs.py` (06-11)
- [x] `analysis/facts.py`, `analysis/deliverables_manifest.py` (06-04 tracer, so tests have something to import)
- [x] `Markdown==3.11` in `analysis/requirements.txt` after the human-verify checkpoint; installed via the pip fallback (06-01)
- [x] `06-ARTIFACT-FORMAT.md` from the Slides probe (06-02)
- [x] Populated `analysis/results/` from `make results` (06-01), so later waves verify on real results

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Published Slides Artifact opens and has one section per exercise | DELIV-01 | Publishing needs the top-level session's Artifact tool | Open the slides URL recorded in README; step through every slide |
| Published informe Artifact opens; question table links resolve | DELIV-02 | Same as above | Open the informe URL; click each question link |
| Literal enunciado quotes match the PDF | DELIV-02 | Accents were reconstructed from TeX escapes (research A6) | At the 06-08 Task 2 blocking-human checkpoint, before 06-09 builds the informe: compare each of the 25 lines printed by `.venv/bin/python analysis/deliverables_manifest.py questions` with `docs/Archivo SIATP 42026.pdf`, word by word and accent by accent; 06-08 Task 3 applies the corrections and sets `QUESTIONS_CHECKED_AGAINST_PDF = True` |
| Each question links to the section that answers it, not only to a section that exists | DELIV-02 | Whether a section answers a question is a reading judgement; the anchor tests only prove the section exists, and the research "Answered in" column is a proposal | At the same 06-08 Task 2 blocking-human checkpoint: read the anchors and section headings printed under each question by `.venv/bin/python analysis/deliverables_manifest.py questions`, open the fragment where a heading does not settle it, and reply `Q<id> secciones: ...` for each correction; 06-08 Task 3 applies them and sets `ANSWER_SECTIONS_CHECKED = True`, and the 06-09 and 06-12 builds refuse to run while it is False |
| Published SOM and campaign numbers rest on a decided Phase 2 and Phase 3 state | DELIV-01, DELIV-02 | Settling open review findings in a pre-registered rule and a pending UAT is a human judgement | At the 06-12 Task 1 blocking-human checkpoint, answer one Fase 3 option and one Fase 2 option (p2-resolved, p2-changed-and-rebuilt, p2-waive); 06-12 Task 2's PHASE3_SETTLED_OK refuses the final build while 03-UAT.md is not complete without the CLAUDE.md Phase 3 waiver line, and PHASE2_SETTLED_OK refuses the final build while WR-01, WR-02, WR-03, WR-04 or IN-01 is open without the CLAUDE.md waiver line |
| `make deliverables` is byte-reproducible on real results | DELIV-03 | Needs the full, slow results chain | Run `make deliverables` twice and compare `sha256sum` of outputs (re-observed 2026-10-26: DELIVERABLES_REPRODUCIBLE, FINAL_BUILD_OK) |
| Slide legends not clipped (`plot_regions` legend_ax, `plot_recovery` fig.legend, square cells in `plot_shortlists_som` 1x4) | DELIV-01 | The aspect tests prove the slide branch runs at the contract size, not that the layout is legible | Look at the slide PNGs under `analysis/results/**/slide/` or at the published deck (`06-UAT.md` test 1, pass) |

---

The checkpoints (06-01-T1, 06-02-T1, 06-08-T2, 06-12-T1, 06-12-T3) were resolved during execution (see the SUMMARY files), and the hosted deck, hosted informe, exported PDF and sharing decision passed in `06-UAT.md` (4/4, 2026-10-26). Open review findings (`06-REVIEW-DISPOSITION.md`, WR-01 to WR-07 and IN-01 to IN-06) are robustness and wording caveats, not uncovered requirements; WR-08 is covered by the tests above.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-10-26

## Validation Audit 2026-10-26

| Metric | Count |
|---|---|
| Gaps found | 3 |
| Resolved | 3 |
| Escalated | 0 |
