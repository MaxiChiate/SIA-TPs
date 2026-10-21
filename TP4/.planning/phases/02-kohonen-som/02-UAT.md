---
status: testing
phase: 02-kohonen-som
source: [02-VERIFICATION.md]
started: 2026-10-21T19:15:00Z
updated: 2026-10-21T19:15:00Z
---

## Current Test

number: 1
name: Decide whether a single region (R1 = all 50 creators) satisfies the goal "read creator profiles by region"
expected: |
  Either accept the pre-registered region rule as honestly reported (profiles are then read per neuron, which the deliverable does), or open a new discussion to define regions differently. Do NOT edit the rule in place (it would void "fijada de antemano").
awaiting: user response

## Tests

### 1. Decide whether a single region (R1 = all 50 creators) satisfies the goal "read creator profiles by region"
expected: Either accept the pre-registered region rule as honestly reported (profiles are then read per neuron, which the deliverable does), or open a new discussion to define regions differently. Do NOT edit the rule in place (it would void "fijada de antemano").
result: [pending]

### 2. Read section 2 of deliverables/02-kohonen.md (between <!-- regla:inicio --> and <!-- regla:fin -->) against D-10..D-15 in 02-CONTEXT.md
expected: Prose and the executable som_select.py implement the same rule (filters TE<=0.05, empty<=20%, >=2 creators/occupied; lowest QE-LOO; 1-SD band then stability then smaller k; TE-only relaxation; no grid if occupancy fails).
result: [pending]

### 3. Open analysis/results/som/figures/*.svg|png and analysis/results/som/profiles/*.svg|png and judge legibility
expected: Hit map, U-matrix, component planes, stage-1 curves, trace, regions, PC planes are legible at presentation size. Known minor issue: in stage1_curves the annotation "menor QE: k = 8" overlaps the k=6-7 step curve, and +/-SD error bars dip below 0 for TE and % empty.
result: [pending]

### 4. Read sections 5, 6 and 7 of the deliverable against the Phase 1 biplot (analysis/results/pca/audited/biplot.svg and deliverables/01-datos-pca.md section 6)
expected: "Yes for PC1, no for PC2" is consistent with the biplot reading (PC1 = scale/price axis; PC2 = Argentine audience / dogs) and the creator-pair disagreements are real.
result: [pending]

### 5. Review the judgment-tier prohibitions (non-authoritative LLM-judge verdicts in 02-VERIFICATION.md)
expected: Reviewer confirms the 12 prohibitions across plans 02-01..02-06 held.
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
