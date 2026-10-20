---
status: testing
phase: 01-fundaci-n-auditor-a-de-datos-y-pca
source: [01-VERIFICATION.md]
started: 2026-10-20T23:27:56Z
updated: 2026-10-20T23:27:56Z
---

## Current Test

number: 1
name: Figuras de EDA legibles (distributions.png, correlation.png)
expected: |
  Las figuras en analysis/results/eda/ se leen bien (ejes, etiquetas, paleta).
awaiting: user response

## Tests

### 1. Figuras de EDA legibles
expected: distributions.png y correlation.png legibles
result: [pending]

### 2. Loadings y biplot
expected: loadings.png y el biplot de all31_sensitivity legibles; en el biplot auditado la etiqueta "followers" se superpone con puntos y flechas, decidir si es aceptable
result: [pending]

### 3. Secciones 3 y 5 de deliverables/01-datos-pca.md
expected: la regla de selección de variables y la regla de PCA se leen como fijadas antes de ver los resultados
result: [pending]

### 4. Secciones 6 y 7 de deliverables/01-datos-pca.md
expected: la interpretación de PC1/PC2, la decisión de no reducir y la conclusión de sensibilidad son convincentes
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
