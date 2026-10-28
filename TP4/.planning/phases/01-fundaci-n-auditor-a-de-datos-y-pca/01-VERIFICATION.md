---
phase: 01-fundaci-n-auditor-a-de-datos-y-pca
verified: 2026-10-20T20:35:00Z
status: passed
score: 5/5 must-haves verified
covered_files:
  - .planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-01-PLAN.md
  - .planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-01-SUMMARY.md
  - .planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-02-PLAN.md
  - .planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-02-SUMMARY.md
  - .planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-03-PLAN.md
  - .planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-03-SUMMARY.md
  - .planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-04-PLAN.md
  - .planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-04-SUMMARY.md
  - .planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-05-PLAN.md
  - .planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-05-SUMMARY.md
  - .planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-06-PLAN.md
  - .planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-06-SUMMARY.md
  - .planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-07-PLAN.md
  - .planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-07-SUMMARY.md
  - .planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-08-PLAN.md
  - .planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-08-SUMMARY.md
  - Makefile
  - analysis/eda.py
  - analysis/pca.py
  - analysis/plots_style.py
  - analysis/sweep.py
  - analysis/tests/test_creadores.py
  - analysis/tests/test_pca.py
  - deliverables/01-datos-pca.md
  - neuron/Makefile
  - neuron/io/config.c
  - neuron/io/matrix.c
  - neuron/io/results.c
  - neuron/main.c
  - neuron/models/hopfield_stub.c
  - neuron/models/kohonen_stub.c
  - neuron/models/models.c
  - neuron/models/oja_stub.c
  - neuron/rng.c
  - neuron/tests/test_main.c
  - scripts/creadores.py
  - scripts/map_creator.py
  - scripts/prepare_creadores.py

covered_digest: "v2:sha256:ddacbe9c2bb75af128596af51dd55f6580f37b629ea13fc7e53c791d2546349b"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Abrir analysis/results/eda/distributions.png y correlation.png (make eda)"
    expected: "31 histogramas legibles con nombre y asimetria; heatmap con 31 etiquetas legibles y las celdas price_usd/price_ars y sponsored/organic en los extremos de la escala"
    why_human: "La legibilidad de multiples pequenos densos y de etiquetas no se verifica con grep (item diferido por el plan 01-06)"
  - test: "Abrir analysis/results/pca/audited/loadings.png y all31_sensitivity/biplot.png (make pca); el verificador solo vio eigenvalue plot y biplot auditado"
    expected: "Heatmap de loadings legible; figura de sensibilidad titulada SENSIBILIDAD; en el biplot auditado la etiqueta 'followers' se superpone a puntos y flechas (observado), confirmar si es aceptable"
    why_human: "Legibilidad de flechas, etiquetas y colores necesita ojos (item diferido por el plan 01-08)"
  - test: "Leer las secciones 3 y 5 de deliverables/01-datos-pca.md junto a las tablas generadas"
    expected: "La regla de seleccion y la regla de PCA se leen como fijadas antes de los resultados y las cifras coinciden con las tablas (el verificador comparo las cifras contra un recalculo independiente: coinciden)"
    why_human: "Si la justificacion escrita es convincente es un juicio, no un match de cadenas (item diferido por el plan 01-06)"
  - test: "Leer las secciones 6 y 7 de deliverables/01-datos-pca.md junto a las figuras"
    expected: "Los nombres de PC1/PC2 salen de las cargas impresas, la decision de reducir cita k_80 = 6 y mantiene Kohonen y Oja sobre las 26 variables, y la conclusion de sensibilidad esta respaldada por la tabla"
    why_human: "La correccion de una interpretacion es un juicio sobre los numeros (item diferido por el plan 01-08)"
---

# Phase 1: Fundacion, auditoria de datos y PCA - Verification Report

**Phase Goal:** As a campaign analyst, I want to run a reproducible C/Python pipeline over an audited, standardized creadores.csv with PCA, so that every later result rests on justified variables.
**Verified:** 2026-10-20T20:35:00Z
**Status:** human_needed
**Re-verification:** No - initial verification

La meta se cumple en el codigo: los 5 criterios de exito del ROADMAP quedan VERIFIED con evidencia propia (ejecute los comandos, no confie en los SUMMARY). El status es `human_needed` solo porque los planes 01-06 y 01-08 difirieron cuatro revisiones visuales/de interpretacion al fin de fase (regla del paso 8: cualquier item humano impide `passed`). No hay gaps ni blockers.

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `make` compila un solo binario; con `model` = kohonen/oja/hopfield la corrida escribe copia de config, `metrics.json` plano y CSV; misma seed => archivos identicos | VERIFIED | `make -C neuron` compila `build/neuron` sin warnings (-Wall -Wextra -Wpedantic). Corri los 3 ejemplos de config dos veces cada uno (con 1 s de separacion): `diff -r` entre corridas vacio para oja, kohonen y hopfield. Cada directorio tiene `config.json`, `metrics.json` plano y CSV (oja: index.csv, weights.csv; kohonen: assignments.csv, prototypes.csv; hopfield: queries.csv). Sin rutas absolutas ni fechas dentro de los archivos (`grep /Users` vacio). Oja y kohonen leen `creadores_zscore.csv` real (50x26). Config estricta probada a mano: clave desconocida, faltante, tipo erroneo, clave duplicada, modelo desconocido (lista kohonen, oja, hopfield), `grid_k` en oja y falta de `grid_k` en kohonen fallan con mensaje que nombra archivo y clave. |
| 2 | `sweep.py` corre series multi-seed para cualquier modelo y deja `summary.csv` con claves de metrics y claves variadas; `.venv` con deps fijadas; `make test` pasa | VERIFIED | `sweep.py analysis/series_smoke_kohonen.json` => 9 corridas ok, `summary.csv` con columnas run,variant,label,seed,status,grid_k,model,n_samples,...,mean_bmu_distance. Tres corridas de la serie dan el mismo sha1 de `summary.csv`. `.venv` contiene exactamente numpy 2.5.4, matplotlib 3.11.2, Pillow 13.0.0, pytest 9.1.1 (+ transitivas), sin pandas ni plotly. `make test`: "63 checks, 0 failed" (3 tests C) y "6 passed" (pytest). `make -C neuron debug` (ASan/UBSan) tambien pasa. |
| 3 | Loader falla claro si no hay n=50 y 33 columnas; EDA con distribuciones y correlaciones; tabla de auditoria con las 5 dependencias exactas y regla escrita | VERIFIED | `load_creadores` sobre un CSV de 48 filas y sobre uno de 32 columnas levanta `ValueError: ... expected 50 rows x 33 ...`. Recalculo independiente con numpy: residuos de las 5 relaciones <= 9.3e-10 (price_ars) y 1.4e-14 en el resto, rango de la correlacion de 31 columnas = 26 (5 autovalores nulos), varianzas topic/content coinciden con la seccion 3.2 (topic_art 457.8 y content_showcase 81.9 son las menores). `make eda` genera distributions, correlation, summary_stats, strong_correlations, exact_dependencies, near_redundant y `audit_table.md` (31 filas, 5 "sale", 26 "entra"). La regla esta escrita en `deliverables/01-datos-pca.md` 3.2 con anterioridad a la PCA (D-09). |
| 4 | Matriz z-scored con scaler guardado (`.meta.json`); un creador nuevo se mapea con solo ese archivo | VERIFIED | `datos/prepared/creadores_zscore.csv` (50x26) coincide con mi z-score independiente (ddof=1) con diferencia maxima 2.4e-15. `.meta.json` guarda features, mean, std, ddof, dropped. `map_creator.py --meta ... --input datos/creadores.csv` reproduce `creadores_zscore.csv` byte a byte (`cmp` OK) y mapea filas nuevas sin leer los datos de entrenamiento. `datos/prepared/` esta ignorado por git y se regenera con `make prepare`. |
| 5 | PCA por autovalores con eigenvalues plot, loadings, biplot PC1/PC2, justificacion escrita de reducir o no; sensibilidad de 31 columnas etiquetada y comparada | VERIFIED | `make pca`: auditado k_80 = 6, retired criterion = 6, concuerdan, 0 autovalores nulos; 31 columnas: k_80 = 6, retired criterion = 7, 5 autovalores nulos. Mis autovalores independientes (`eigvalsh` sobre `corrcoef` del z-score de las 26) = 13.84, 2.212, 1.855, 1.492, 1.17, 1.037, ..., suma 26.0; coinciden con `decision.json`. Genera eigenvalues plot, loadings, biplot (vi eigenvalue plot y biplot), eigenvalues/eigenvectors/loadings/scores CSV. Seccion 6 del entregable explica PC1 (escala y formato) y PC2 (audiencia argentina) desde las cargas impresas y la seccion 6.1 decide no reducir en el modelado (PCA diagnostica, D-13). Seccion 7 y `sensitivity.md` titulan "SENSIBILIDAD" y comparan contra el auditado. |

**Score:** 5/5 truths verified (0 behavior-unverified)

La reproducibilidad (verdad 1) es dependiente de comportamiento: la respalda un test nombrado ("same seed, same bytes" en `neuron/tests/test_main.c`, pasa) mas mi propio `diff -r` entre dos corridas reales.

### Deferred Items

Ninguno. No hay gaps que diferir.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `neuron/main.c`, `io/config.c`, `io/matrix.c`, `io/results.c`, `models/{models,oja_stub,kohonen_stub,hopfield_stub}.c` | Binario unico con despacho por `model` | VERIFIED | Existen, compilan, estan cableados (dispatch por tabla; corrida real de los 3 modelos) |
| `neuron/vendor/cjson/` | cJSON v1.7.19 vendored | VERIFIED | sha256 de los 3 archivos coincide con `VERSION` |
| `neuron/rng.c`, `rng.h` | splitmix64 de TP3 | VERIFIED | Identicos byte a byte a `../TP3/neuron/rng.c/h` |
| `neuron/tests/test_main.c` | 3 tests de C | VERIFIED | 63 checks, 0 failed, tambien bajo sanitizers |
| `analysis/sweep.py`, `series_smoke_{oja,kohonen,hopfield}.json` | Runner de series | VERIFIED | Corrida real, summary.csv reproducible |
| `analysis/requirements.txt`, `Makefile` raiz | .venv fijado, targets all/venv/prepare/eda/pca/sweep/test/clean | VERIFIED | Los targets corren |
| `scripts/creadores.py`, `prepare_creadores.py`, `map_creator.py` | Loader, auditoria, scaler, mapeo | VERIFIED | Ver verdades 3 y 4 |
| `analysis/eda.py`, `plots_style.py` | EDA y tabla de auditoria | VERIFIED | `make eda` genera las 9 salidas |
| `analysis/pca.py`, `analysis/tests/test_pca.py` | PCA por autovalores + test | VERIFIED | `make pca` y test pasan; sin pandas |
| `deliverables/01-datos-pca.md` | Fragmento narrativo de la Fase 1 (espanol) | VERIFIED | Secciones 1-8 sustantivas y con cifras que coinciden con el recalculo |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| main.c | models.c | `model_find(config.model)` | WIRED | Los 3 modelos corren |
| config.c | cJSON | `cJSON_Parse` | WIRED | Rechazos estrictos observados |
| sweep.py | neuron/build/neuron | subprocess + `metrics.json` | WIRED | 9 filas ok |
| config.json.{oja,kohonen}.example | datos/prepared/creadores_zscore.csv | ruta relativa a `neuron/` | WIRED | Corrida sobre 50x26 |
| map_creator.py | creadores_zscore.meta.json | `load_meta` + `transform_new_creator` | WIRED | Byte-igual |
| pca.py | datos/prepared/creadores_zscore*.csv | `read_prepared` | WIRED | Misma matriz que lee C |
| Makefile `test`/`all`/`sweep`/`pca` | `prepare` | prerequisito | WIRED | `make test` regenero `datos/prepared/` primero |
| deliverables/01-datos-pca.md | decision.json / audit_table.md | cifras citadas | WIRED | k_80 = 6, retired criterion = 6, 26 variables coinciden |

### Data-Flow Trace (Level 4)

| Artifact | Variable | Source | Real data | Status |
|----------|----------|--------|-----------|--------|
| kohonen/oja stubs | matriz 50x26 | `matrix_load` de `creadores_zscore.csv` | Si (metrics n_samples = 50, n_features = 26) | FLOWING |
| pca.py | autovalores/cargas | `eigh` sobre correlacion de la matriz preparada | Si (coinciden con mi recalculo) | FLOWING |
| eda.py audit_table | decisiones | `audit_variables` de `scripts/creadores.py` (misma regla que `prepare`) | Si | FLOWING |

Los stubs de oja/kohonen/hopfield son stubs deterministas por diseno (D-03): las Fases 2-5 reemplazan su cuerpo. No cuentan como gap de esta fase.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Suite completa | `make test` | 63 checks / 0 failed; 6 passed | PASS |
| Sanitizers | `make -C neuron debug` | 63 checks / 0 failed, sin reportes | PASS |
| e2e reproducible x3 modelos | binario x2 + `diff -r` | Sin diferencias | PASS |
| Config estricta | 7 configs invalidas | Todas abortan nombrando clave | PASS |
| Serie multi-seed | `sweep.py series_smoke_kohonen.json` x3 | summary.csv identico (mismo sha1) | PASS |
| Loader 50x33 | 2 CSV mal formados | `ValueError` nombrando 50 x 33 | PASS |
| Mapeo byte-igual | `map_creator.py` sobre creadores.csv + `cmp` | MAP-BYTE-EQUAL | PASS |
| PCA independiente | numpy `eigvalsh` propio | autovalores, k_80 = 6, retired criterion = 6 | PASS |

### Probe Execution

SKIPPED: la fase no declara probes (`probe-*.sh`) ni los hay en `scripts/`.

### Requirements Coverage

Todos los IDs de los PLAN estan en REQUIREMENTS.md y todos los IDs que REQUIREMENTS.md mapea a la Fase 1 aparecen en algun PLAN (sin huerfanos).

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|----------------|-------------|--------|----------|
| INFRA-01 | 01-01, 01-05 | Un binario C despacha por `model` | SATISFIED | 3 modelos corren desde un solo binario |
| INFRA-02 | 01-01, 01-05 | Directorio de corrida con config, metrics.json plano, CSV, seed reproducible | SATISFIED | `diff -r` vacio |
| INFRA-03 | 01-03, 01-07 | `sweep.py` multi-seed con `summary.csv` | SATISFIED | Serie corrida x3 |
| INFRA-04 | 01-02, 01-07 | `.venv` fijado y `make test` | SATISFIED | Pins exactos, `make test` verde |
| DATA-01 | 01-04 | Loader verifica 50x33 | SATISFIED | ValueError probado |
| DATA-02 | 01-04, 01-06 | EDA + tabla de auditoria con las 5 dependencias y la regla | SATISFIED | `make eda`, seccion 3 |
| DATA-03 | 01-04 | Z-score con scaler guardado | SATISFIED | meta + mapeo byte-igual |
| DATA-04 | 01-06, 01-08 | PCA por autovalores con eigenvalue plot/loadings/biplot y justificacion | SATISFIED | `make pca`, secciones 5-6 |
| DATA-05 | 01-04, 01-08 | Sensibilidad con 31 columnas, etiquetada y comparada | SATISFIED | `sensitivity.md/json`, seccion 7 |

**Bookkeeping para el orquestador:** `.planning/REQUIREMENTS.md` aun muestra DATA-02, DATA-03, DATA-04 y DATA-05 como `[ ]` / `Pending` (lineas 18-21 y 91-94) aunque el codigo los satisface. Actualizar el checkbox y la tabla de trazabilidad al cerrar la fase.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (fuentes de la fase) | - | `TBD`/`FIXME`/`XXX` | - | Ninguno encontrado en `neuron/`, `analysis/*.py`, `scripts/*.py`, Makefiles |

### Code-Review Findings (01-REVIEW.md, 0 critical / 5 warnings) vs must-haves

Ninguno invalida un must-have. Evalue cada uno:

| ID | Hallazgo | Efecto sobre la fase | Severidad aqui |
|----|----------|----------------------|----------------|
| WR-01 | `sensitivity.json/md` mezclan `abs_cos` con Pearson/Spearman con signo (PC1: 0.99998 vs -0.9992) | Confirmado en la salida generada. DATA-05 pide comparar y la comparacion existe; la seccion 7 del entregable explica la inversion de signo. Riesgo: quien lea solo el artefacto generado puede malinterpretar. | WARNING (cosmetico, reparar antes de reusar en slides) |
| WR-02 | Un `seed` variado/fijado en una serie se ignora en silencio | Confirmado: una serie con `"vary": "seed"` valores 7 y 8 corre ambas con seed 1 y lo etiqueta 7/8. No afecta SC2 (multi-seed via `seeds`) ni ninguna serie de la fase, pero es una trampa para los barridos de seeds de las Fases 2-5. | WARNING (arreglar al comenzar la Fase 2) |
| WR-03 | Una corrida fallida deja un directorio con solo `config.json` | No afecta SC1 (corridas exitosas); `sweep.py` limpia sobrantes. Observado al correr desde un cwd equivocado. | WARNING |
| WR-04 | `map_creator.py` acepta nan/inf y falla con tracebacks | SC4 se cumple para entradas validas; la validacion de borde es mas debil que la del loader. | WARNING |
| WR-05 | `audit_rows` puede pisar la razon de "sale" si una variable eliminada cruzara el umbral de casi-redundancia | Con los datos actuales la tabla es correcta (verificada). Latente. | WARNING |

### Deviaciones y decisiones a senalar al usuario (no son gaps)

- **D-05 relajado a "copiar y adaptar" (aviso, no gap).** `rng.c/h` son copias byte a byte de TP3 (verificado con `diff`). `neuron/Makefile`, `io/results.c` y `analysis/sweep.py` se copiaron y adaptaron; la desviacion esta registrada en 01-01-SUMMARY y 01-03-SUMMARY y `01-CONTEXT.md` ya lleva el texto enmendado. Honra la decision enmendada.
- **D-06 (sin pandas) honrada.** `.venv` sin pandas ni plotly; EDA/PCA con `csv` + numpy + matplotlib.
- **D-07 (menos de 10 tests) honrada.** 3 C + 6 pytest = 9.
- **D-08 a D-13 honradas** y verificadas con recalculo independiente (26 variables, mismas 5 eliminadas, z-score directo ddof=1, PCA sobre correlacion con eigh, 80 % con retired criterion de control, PCA diagnostica).
- **Dato curioso para el informe:** k_80 = 6 y retired criterion = 6 coinciden por margen minimo (5 PCs = 79.1 %, sexto autovalor = 1.04); el entregable ya lo dice.

### Human Verification Required

Ver los cuatro items del frontmatter (`human_verification`): revision visual de EDA (distributions/correlation), revision visual de loadings y de la figura de sensibilidad (incluye la superposicion de la etiqueta "followers" en el biplot auditado), y lectura critica de las secciones 3, 5, 6 y 7 del entregable. Son los items `<human-check>` que los planes 01-06 y 01-08 difirieron deliberadamente al fin de fase; el verificador valido las cifras contra un recalculo independiente, lo que queda para una persona es la legibilidad y si la justificacion convence.

### Gaps Summary

Sin gaps. El pipeline C/Python es reproducible, el `creadores.csv` esta auditado (5 dependencias exactas, 26 variables), estandarizado con scaler guardado y la PCA con su decision escrita esta hecha, con la sensibilidad de 31 columnas etiquetada. Pendiente solo la revision humana de figuras/redaccion y la actualizacion de los checkboxes DATA-02..05 en REQUIREMENTS.md.

---

_Verified: 2026-10-20T20:35:00Z_
_Verifier: Claude (gsd-verifier)_
