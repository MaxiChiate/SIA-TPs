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
| 6-TBD | TBD | TBD | DELIV-01 | — | N/A | unit | `.venv/bin/python -m pytest analysis/tests/test_slides.py -q` | ❌ W0 | ⬜ pending |
| 6-TBD | TBD | TBD | DELIV-02 | — | every `<img>` is a data URI decoding to SVG; no `/Users/` paths | unit | `.venv/bin/python -m pytest analysis/tests/test_informe.py -q` | ❌ W0 | ⬜ pending |
| 6-TBD | TBD | TBD | DELIV-02 | — | N/A | unit | `.venv/bin/python -m pytest analysis/tests/test_facts.py -q` | ❌ W0 | ⬜ pending |
| 6-TBD | TBD | TBD | DELIV-03 | — | N/A | unit | `.venv/bin/python -m pytest analysis/tests/test_repro_docs.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*Task IDs are filled in once plans exist.*

---

## Wave 0 Requirements

- [ ] `analysis/tests/test_facts.py`, `test_deliverables_manifest.py`, `test_informe.py`, `test_slides.py`, `test_repro_docs.py`
- [ ] `analysis/facts.py`, `analysis/deliverables_manifest.py` (so tests have something to import)
- [ ] `Markdown==3.11` in `analysis/requirements.txt` after the human-verify checkpoint; installed via the pip fallback
- [ ] `06-ARTIFACT-FORMAT.md` from the Slides probe

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Published Slides Artifact opens and has one section per exercise | DELIV-01 | Publishing needs the top-level session's Artifact tool | Open the slides URL recorded in README; step through every slide |
| Published informe Artifact opens; question table links resolve | DELIV-02 | Same as above | Open the informe URL; click each question link |
| Literal enunciado quotes match the PDF | DELIV-02 | Accents were reconstructed from TeX escapes | Compare each quote in the table against `docs/` enunciado PDF |
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
