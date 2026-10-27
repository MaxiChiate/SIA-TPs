---
status: complete
phase: 03-oja-y-decisiones-de-campa-a
source: [03-VERIFICATION.md]
started: 2026-10-22T15:08:20Z
updated: 2026-10-26T03:44:46.389Z
---

## Current Test

[testing complete]

## Tests

### 1. Fairness of section 5 (campaign recommendations, fútbol 5.1)
expected: Every recommendation follows from the pasted numbers and the stated assumptions; the followers comparison is fair (both baselines, same k, advantages of followers stated); nothing implies a commercial outcome (judge 'la ropa de entrenamiento es un producto que se elige viéndolo en uso' and 'es la lista más barata en total').
result: pass

### 2. Section 7 regeneration pipeline runs in order
expected: From TP4/, make venv, prepare, pca, som-stage1, oja, campaigns, maintenance regenerate every number and figure; make campaigns refuses only if the rule files changed. Run tests as .venv/bin/python -m pytest analysis/tests -q and make -C neuron test|debug (make test breaks on spaces in the path, pre-existing).
result: pass

### 3. Sections 1-3 and 6 faithful to reports and figures
expected: Prose matches convergence.svg, oja_vs_pc1.svg and the report files; section 3 answers "No." with evidence; the four maintenance answers in section 6 are concrete and actionable.
result: pass

## Summary

total: 3
passed: 3
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
