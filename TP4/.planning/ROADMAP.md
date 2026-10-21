# Roadmap: TP4 SIA — Aprendizaje no supervisado y memoria asociativa

## Overview

El TP4 tiene dos ejercicios que comparten una sola base técnica: un binario en C que despacha por la clave `model` y análisis en Python. La Fase 1 deja lista esa base y deja decididas las variables de `creadores.csv` (auditoría, z-score, PCA). Con eso, el Ejercicio 1 avanza en serie: Kohonen (Fase 2) y después Oja junto con las decisiones de campaña (Fase 3), que consumen Kohonen, Oja y PCA. El Ejercicio 2 depende solo de la Fase 1: primero el núcleo de Hopfield validado con letras 5×5 (Fase 4) y después los cinco QR de 37×37, donde se espera que Hebb falle y la pseudo-inversa sea el remedio (Fase 5). La Fase 6 ensambla slides e informe con los fragmentos que emitió cada fase y documenta cómo reproducir cada resultado.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Fundación, auditoría de datos y PCA** - Pipeline C/Python reproducible, `creadores.csv` auditado y estandarizado, PCA con decisión escrita (completed 2026-10-20)
- [ ] **Phase 2: Kohonen SOM** - Mapa de los 50 creadores con grilla elegida por regla multicriterio fijada de antemano y perfiles por región
- [ ] **Phase 3: Oja y decisiones de campaña** - Índice de Oja contra PC1, recomendaciones por campaña, comparación contra solo `followers` y mantenimiento
- [ ] **Phase 4: Hopfield núcleo y letras** - Núcleo validado con 4 letras 5×5: energía, ortogonalidad, capacidad y un estado espurio identificado
- [ ] **Phase 5: Hopfield con QR** - Cinco QR de 37×37 con Hebb (falla reportada), pseudo-inversa, línea base de Hamming y limitaciones
- [ ] **Phase 6: Slides e informe** - Slides e informe en Artifact con mapa pregunta→respuesta, y documentación para reproducir todo

## Phase Details

### Phase 1: Fundación, auditoría de datos y PCA

**Goal:** As a campaign analyst, I want to run a reproducible C/Python pipeline over an audited, standardized creadores.csv with PCA, so that every later result rests on justified variables.
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, DATA-01, DATA-02, DATA-03, DATA-04, DATA-05
**Success Criteria** (what must be TRUE):
  1. `make` compila un solo binario y, con un `config.json` cuya clave `model` es `kohonen`, `oja` o `hopfield`, la corrida escribe en su directorio una copia de la config, un `metrics.json` plano y los CSV del modelo; repetir la corrida con la misma seed da archivos idénticos (lazo extremo a extremo con un modelo trivial).
  2. `sweep.py` corre una serie con varias seeds para cualquier modelo y deja un `summary.csv` con las claves de `metrics.json` y las claves variadas; el `.venv` se recrea con dependencias fijadas y `make test` pasa.
  3. El loader falla con un error claro si `creadores.csv` no tiene n=50 filas y 33 columnas; el EDA muestra distribuciones y correlaciones, y la tabla de auditoría documenta las 5 dependencias lineales exactas y la regla escrita de selección de variables.
  4. Existe la matriz z-scored con su scaler guardado (`.meta.json`), y un creador nuevo se puede mapear al mismo espacio usando solo ese archivo.
  5. La PCA por autovalores muestra scree, loadings y biplot PC1/PC2 con una justificación escrita de si se reduce dimensionalidad y cómo se leen las componentes; la corrida de sensibilidad con las 31 columnas está etiquetada como tal y comparada contra el conjunto auditado.

**Plans:** 8/8 plans complete

Plans:
**Wave 1**
- [x] 01-01-PLAN.md — Walking skeleton (tracer): config.json → binario C (stub oja) → directorio de corrida reproducible; validación estricta de config por modelo
- [x] 01-02-PLAN.md — Chequeo de legitimidad de paquetes, `.venv` fijado con `uv` y Makefile raíz (solo `venv`)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 01-03-PLAN.md — `sweep.py`: serie multi-seed → `summary.csv` reproducible, corridas fallidas registradas, `--dry-run`
- [x] 01-04-PLAN.md — Loader 50×33, auditoría, z-score con `.meta.json`, variante de 31 columnas, mapeo de creador nuevo y 5 tests de pytest

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 01-05-PLAN.md — Stubs kohonen y hopfield con claves estrictas por modelo; configs de oja y kohonen sobre `datos/prepared`
- [x] 01-06-PLAN.md — EDA (distribuciones, correlaciones, dependencias), tabla de auditoría generada, `make prepare`/`make eda` y fragmento escrito con la regla de PCA fijada antes del scree

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 01-07-PLAN.md — Una serie por modelo desde la raíz, `make`/`make sweep`/`make clean`, `make test` (3 tests de C + pytest) y `make debug`

**Wave 5** *(blocked on Wave 4 completion)*
- [x] 01-08-PLAN.md — PCA por autovalores (scree, loadings, biplot, decisión 80 %/Kaiser), sensibilidad con 31 columnas e interpretación escrita

### Phase 2: Kohonen SOM

**Goal:** As a campaign analyst, I want to train a Kohonen map of the 50 creators with a grid chosen by a rule fixed beforehand, so that I can read creator profiles by region and contrast them with PC1/PC2.
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: SOM-01, SOM-02, SOM-03, SOM-04, SOM-05
**Success Criteria** (what must be TRUE):
  1. Una corrida del SOM sobre los datos z-scored (grilla k×k, vecindad y η decrecientes, inicialización con muestras) reporta QE, TE y ocupación por neurona en `metrics.json` y en sus CSV, de forma reproducible por seed.
  2. El barrido multi-seed de hiperparámetros produce un resumen y la regla de elección de grilla (QE, TE, ocupación, QE leave-one-out, estabilidad entre seeds) está escrita y commiteada antes de mirar los resultados; la grilla elegida se justifica con esa regla y no por menor QE.
  3. Para la grilla elegida existen el mapa de hits, la matriz U y los planos de componentes.
  4. Los perfiles por región están interpretados para el caso de uso de la agencia y contrastados con PC1/PC2 del biplot, con una respuesta escrita a qué indica una distancia alta en la matriz U.

**Plans:** 4/6 plans executed

Plans:
**Wave 1**
- [x] 02-03-PLAN.md — Regla de elección de grilla: checkpoint de decisión (aprobar o editar los términos fijados; sin grilla elegible no se elige ninguna, D-14), select_grid y guardia git testeados, regla y serie de la etapa 1 commiteadas antes de entrenar el SOM sobre los datos

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 02-01-PLAN.md — SOM real en C (tracer, después del commit de la regla): 7 claves estrictas, entrenamiento escalón/gaussiana, QE/TE/ocupación, occupancy.csv y trace.csv, tests C bajo ASan/UBSan y neuron/README

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 02-02-PLAN.md — Lector de corridas y recomputación en numpy de QE/TE/ocupación, estabilidad entre seeds (Spearman con empates, medoide) y driver de QE leave-one-out con un directorio temporal por entrenamiento

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 02-04-PLAN.md — Driver de etapas con guardia: etapa 1 (140 corridas + LOO + estabilidad + selección), serie de la etapa 2 generada y commiteada, robustez; secciones 3 y 4

**Wave 5** *(blocked on Wave 4 completion)*
- [ ] 02-05-PLAN.md — Mapa de hits, matriz U, planos de componentes, curvas de la etapa 1 y traza de la grilla elegida; sección 5

**Wave 6** *(blocked on Wave 5 completion)*
- [ ] 02-06-PLAN.md — Regiones por regla, perfiles en unidades originales, contraste cuantificado con PC1/PC2, respuesta sobre la matriz U y cómo reproducir; secciones 6 y 7

### Phase 3: Oja y decisiones de campaña

**Goal:** As a campaign analyst, I want to build an Oja index and recommend creators per campaign against a followers-only strategy, so that I can choose with evidence and know when the index misleads.
**Mode:** mvp
**Depends on**: Phase 2 (también Phase 1: datos centrados y PCA)
**Requirements**: OJA-01, OJA-02, OJA-03, CAMP-01, CAMP-02, CAMP-03
**Success Criteria** (what must be TRUE):
  1. Oja corre en C sobre datos centrados con η chico y decreciente, pesos renormalizados y convención de signo fija, y deja el índice de los 50 creadores con evidencia de convergencia.
  2. Una tabla compara el índice de Oja con la proyección sobre PC1 usando |cos| entre vectores y correlación de rangos.
  3. Hay una interpretación escrita del índice, con evidencia (correlación con `followers` y con temas), de por qué elegir el máximo para cualquier campaña es incorrecto.
  4. Para cada campaña (fútbol, perros, maquillaje, arte) hay una recomendación justificada con Kohonen, Oja y PCA, comparada contra elegir solo por `followers` con el mismo k (overlap@k, proporción por tema, costo por alcance argentino) y sin afirmaciones de ROI.
  5. Hay respuestas concretas de mantenimiento para una campaña nueva, creadores o variables nuevas y la actualización mensual, apoyadas en el scaler guardado y en las decisiones de re-entrenamiento.

**Plans**: TBD

### Phase 4: Hopfield núcleo y letras

**Goal:** As a student, I want to validate a Hopfield core on four 5x5 letters, so that I understand recovery, energy, capacity and spurious states before moving to QR codes.
**Mode:** mvp
**Depends on**: Phase 1 (independiente del Ejercicio 1; puede intercalarse con las Fases 2 y 3)
**Requirements**: HOP-01, HOP-02, HOP-03
**Success Criteria** (what must be TRUE):
  1. Hopfield en C (W entera, actualización síncrona y asíncrona) registra la energía en cada paso, detecta ciclos y clasifica el estado final como almacenado, inverso, mezcla o espurio.
  2. Las 4 letras 5×5 se almacenan y se recuperan a partir de consultas con ruido, y los CSV muestran la energía por paso (no creciente en el modo asíncrono).
  3. El análisis de ortogonalidad (matriz de solapamientos) y de capacidad se hace sobre varios subconjuntos de letras, no solo sobre un conjunto.
  4. Un patrón muy ruidoso converge a un estado espurio que queda identificado y clasificado (inverso, mezcla u otro).

**Plans**: TBD

### Phase 5: Hopfield con QR

**Goal:** As a student, I want to store the five 37x37 QR codes in a Hopfield network and query them under noise, so that I can explain why Hebb fails and what the pseudo-inverse and a Hamming baseline show.
**Mode:** mvp
**Depends on**: Phase 4
**Requirements**: HOP-04, HOP-05, HOP-06, HOP-07
**Success Criteria** (what must be TRUE):
  1. Los 5 QR de 37×37 se convierten a vectores ±1 de 1369 con una aserción de que los PNG son 0/255 puros, y una matriz de solapamientos muestra la correlación entre ellos.
  2. Con la regla de Hebb existe un test de estabilidad a ruido cero y una curva con al menos 8 niveles de ruido y 30 o más ensayos por nivel, con energía e iteraciones por paso; si Hebb falla, el fallo se reporta como hallazgo.
  3. La regla de pseudo-inversa se compara contra Hebb y contra la línea base de Hamming al patrón almacenado más cercano, en los mismos niveles de ruido.
  4. Las limitaciones del caso de uso están explicadas con evidencia: correlación entre QR, sensibilidad a corrimientos, corrección de errores propia del QR y equivalencia con una tabla de búsqueda.

**Plans**: TBD

### Phase 6: Slides e informe

**Goal:** As a presenter, I want to deliver slides and a report as Artifacts with reproduction docs, so that I can present both exercises and anyone can understand and re-run the project.
**Mode:** mvp
**Depends on**: Phase 3, Phase 5
**Requirements**: DELIV-01, DELIV-02, DELIV-03
**Success Criteria** (what must be TRUE):
  1. Las slides están publicadas como Artifact, con una sección por ejercicio, y se pueden recorrer para presentar.
  2. El informe está publicado como Artifact y su tabla mapea cada pregunta literal del enunciado a la sección donde se responde.
  3. `CLAUDE.md`, `DECISIONS.md` y el README indican cómo reproducir cada resultado (comando, config y seed), y esos pasos regeneran las figuras y tablas que muestran slides e informe.

**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6. Las Fases 4 y 5 (Ejercicio 2) solo dependen de la Fase 1 y pueden intercalarse con las Fases 2 y 3 (Ejercicio 1).

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Fundación, auditoría de datos y PCA | 8/8 | Complete    | 2026-10-20 |
| 2. Kohonen SOM | 4/6 | In Progress | - |
| 3. Oja y decisiones de campaña | 0/TBD | Not started | - |
| 4. Hopfield núcleo y letras | 0/TBD | Not started | - |
| 5. Hopfield con QR | 0/TBD | Not started | - |
| 6. Slides e informe | 0/TBD | Not started | - |
