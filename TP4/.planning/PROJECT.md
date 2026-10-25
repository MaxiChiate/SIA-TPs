# TP4 SIA — Aprendizaje no supervisado y memoria asociativa

## What This Is

TP4 de Sistemas de Inteligencia Artificial (ITBA, 2026, Grupo 9). Dos ejercicios: (1) seleccionar creadores de contenido para campañas de marketing de una agencia usando EDA, PCA, red de Kohonen y regla de Oja sobre `datos/creadores.csv` (50 creadores, 31 variables); (2) memoria asociativa con red de Hopfield para recuperar códigos QR deteriorados (5 QR de 37×37) y patrones de letras 5×5. Entregables: código, análisis, slides para presentar e informe para entender el proyecto.

## Core Value

Interpretar correctamente los resultados de los métodos no supervisados para tomar decisiones de campaña fundamentadas en evidencia: el foco del enunciado es el método y su interpretación, no el análisis de marketing exhaustivo.

## Requirements

### Validated

- ✓ EDA de `creadores.csv` y PCA: justificar si se reduce dimensionalidad y cómo se interpretan las componentes (biplot PC1/PC2) — Phase 1
- ✓ Red de Kohonen sobre todas las variables: variar hiperparámetros y justificar la elección con métricas de performance — Phase 2
- ✓ Análisis de la grilla de neuronas, distribución de creadores en ella y matriz U; interpretar perfiles por región y contrastar con PC1/PC2 — Phase 2
- ✓ Hopfield sobre los 5 QR (37×37, ±1): almacenar, consultar con distintos niveles de ruido aleatorio, analizar iteraciones y energía por paso, explicar limitaciones del caso de uso — Phase 5

### Active

- [ ] Regla de Oja para generar un índice de creadores, interpretarlo (¿es correcto elegir el máximo para cualquier campaña?) y compararlo con la proyección sobre PC1
- [ ] Decisiones de campaña (fútbol, perros, maquillaje, arte): alcance vs descubrimiento vs profundidad; comparar contra estrategia solo por `followers`; mantenimiento del sistema (nueva campaña, nuevos creadores/variables, actualización mensual)
- [ ] Hopfield con caso simple previo: 4 letras 5×5, análisis de ortogonalidad y capacidad de almacenamiento, patrón muy ruidoso con estado espurio identificado
- [ ] Núcleo en C (Kohonen, Oja, Hopfield) con config JSON y Makefile, análisis y gráficos en Python, estructura análoga a TP3 (`neuron/`, `analysis/`, `scripts/`)
- [ ] Slides para presentar (una sección por ejercicio) e informe en Artifact para entender el proyecto

### Out of Scope

- Análisis de marketing exhaustivo — el enunciado aclara que el foco está en los métodos no supervisados y su interpretación; se pueden asumir supuestos sobre las features
- Imágenes de QR de mayor tamaño que 37×37 — el enunciado fija ese tamaño por costo computacional y preprocesamiento
- Librerías de ML que implementen Kohonen, Oja o Hopfield — son el objeto de estudio; se implementan a mano

## Context

- Repo `SIA-TPs`, rama `dev-tp4`; TP4 vive en `TP4/`. Material: `docs/` (enunciado, teoría de PCA, Kohonen, Oja/Sanger, Hopfield, autovalores) y `datos/` (`creadores.csv`, `hopfield/*.png` con los 5 QR).
- TP3 es la referencia de estructura y estilo: núcleo en C configurable por JSON, `sweep.py` para series con varias seeds, reportes HTML, gráficos con plotly, presentación publicada como Artifact. Se puede reutilizar su infraestructura (rng, parseo de config, sweeps, estilo de gráficos).
- `creadores.csv` tiene variables derivadas (`estimated_argentina_reach`, `total_engagement_per_1000`, `price_ars`, pares sponsored/organic) que introducen colinealidad; el EDA/PCA debe tratarlas.
- Los clientes de la agencia: refugios de perros, ropa de entrenamiento de fútbol, belleza, materiales de arte. Cada uno necesita audiencia y contenido distintos.

## Constraints

- **Tech stack**: Núcleo en C (gcc + make), análisis en Python — consistencia con TP3
- **Implementación**: Kohonen, Oja y Hopfield sin librerías que los resuelvan — requisito pedagógico del TP
- **Entregables**: código, análisis, slides, informe (Artifact) — pedido por el usuario
- **Reproducibilidad**: resultados reproducibles con seeds fijas y series versionadas; los resultados generados no se versionan (como TP3)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Núcleo en C + análisis en Python | Misma estructura que TP3 y reutilización de su infraestructura | — Pending |
| Informe como Artifact + slides aparte | Slides para presentar; informe para entender el proyecto | — Pending |
| Regla de elección de grilla del SOM fijada y commiteada antes de ver resultados (commit ea7a0b1, `rule_digest` verificado en cada paso posterior) | Evitar elegir k a posteriori; la regla "fijada de antemano" no se edita in situ, cualquier cambio pasa por discusión | ✓ Good — Phase 2: eligió k = 5 (step) por QE-LOO |
| Reportar el resultado de la regla tal cual aunque sea poco favorable | Honestidad del análisis: etapa 2 "no robusta" (TE > 0,05 en 5 variantes) y una sola región (R1 = 50 creadores) con el percentil fijado | ✓ Good — Phase 2: UAT aceptó leer perfiles por neurona |
| Contraste SOM vs PCA con nulos por permutación (seed 2026, 1000 permutaciones) | Afirmar "el mapa sigue PC1" con evidencia y no a ojo | ✓ Good — Phase 2: sí para PC1 (R² 0,961, p = 0,001), no para PC2 (R² 0,055, p = 0,267) |
| Protocolo de los 5 QR pre-registrado y commiteado antes de correr la red (D-01/D-02, guardia sha256 sobre protocolo + 5 PNG) | Evitar que el hallazgo "Hebb falla" se vea elegido a posteriori; el umbral de veredicto se fija antes de ver resultados | ✓ Good — Phase 5: Hebb 0% recuperación exacta incluso a ruido cero (QR correlacionados, solapamiento medio 0,67); pseudo-inversa 100% a ruido 0, sostiene hasta 0,30; Hamming 1-NN casi igual de bueno hasta ruido 0,40 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-10-25 after Phase 5*
