# Project Research Summary

**Project:** TP4 SIA — Aprendizaje no supervisado y memoria asociativa
**Domain:** Trabajo práctico académico: PCA / Kohonen / Oja sobre datos tabulares y red de Hopfield sobre imágenes binarias, núcleo en C + análisis en Python
**Researched:** 2026-10-20
**Confidence:** MEDIUM-HIGH

## Executive Summary

TP4 tiene dos partes. El Ejercicio 1 hace EDA, PCA, un SOM de Kohonen y la regla de Oja sobre 50 creadores de contenido, y termina en decisiones de campaña. El Ejercicio 2 usa una red de Hopfield sobre cinco QR de 37×37 (N=1369) y letras de 5×5. Los algoritmos se escriben a mano en C; Python se usa para preprocesamiento, PCA, sweeps y figuras.

La construcción recomendada reutiliza el esqueleto de TP3 con cambios: un solo binario que despacha por la clave `"model"`; cada corrida es una función pura (config entra, un directorio de CSV y `metrics.json` sale); `sweep.py` se generaliza para leer `metrics.json`; compilar con `-O2` sin `-fassociative-math` ni `-march=native`; `.venv` con versiones fijadas; matplotlib para figuras estáticas, porque Kaleido necesita un Chrome que no está instalado. La selección de variables y el z-score ocurren en Python; C solo lee números.

Riesgos principales: la colinealidad exacta del dataset (rango 26 de 31 columnas numéricas); elegir la grilla del SOM por menor error de cuantización, que cae monótonamente con el tamaño; Oja con datos sin centrar o con η alto; y Hopfield con regla de Hebb sobre los QR, que falla aunque P/N sea 0,004 porque los patrones están muy correlacionados (solapamientos 0,58–0,86).

## Key Findings

### Recommended Stack

C11 con gcc y make (compatible con Make 3.81), modelado sobre TP3 y reutilizando su `rng`. Python con numpy, matplotlib, plotly y Pillow en un `.venv`. PCA con `eigh`/`svd` de numpy, no sklearn, para mantener explícita la derivación de autovalores del curso. Detalle en `STACK.md`.

**Core technologies:**
- C11 + gcc/make: núcleo de Kohonen, Oja y Hopfield — consistencia con TP3 y requisito de implementar a mano
- numpy: PCA, EDA y validación cruzada de los resultados de C
- matplotlib: figuras estáticas del informe y las slides (biplot, matriz U, grillas de QR, curvas de energía)
- plotly 7: reportes interactivos de EDA y sweeps; sin `write_image` (no hay Chrome), heatmaps con `go.Heatmap`
- Parser JSON: mantener el parser plano de TP3 y sumar cJSON solo si una config necesita anidamiento (decidir en fase 1)

### Expected Features

Detalle en `FEATURES.md`.

**Must have (table stakes):**
- EDA con regla escrita de selección de variables, z-score y PCA con eigenvalues plot, loadings y biplot
- Kohonen con barrido de hiperparámetros multi-seed, QE y TE, mapa de hits, matriz U, planos de componentes y perfiles por región contrastados con PC1/PC2
- Oja con evidencia de convergencia, índice ordenado y comparación contra PC1
- Decisiones de campaña, comparación contra la estrategia solo por `followers` y respuestas sobre mantenimiento
- Hopfield con letras y QR: energía e iteraciones por paso, distintos niveles de ruido, análisis de ortogonalidad/capacidad y un estado espurio identificado

**Should have (competitive):**
- Curvas de robustez al ruido de Hopfield con muchos ensayos y barras de error
- Matriz de solapamientos de los QR y daño estructurado (esquina faltante, bloques, manchas)
- Estabilidad del SOM entre seeds y ablación de preprocesamiento/colinealidad
- Comparación cuantitativa contra `followers` (overlap@k, proporción por tema, costo por alcance argentino)
- Catálogo de estados espurios

**Defer (v2+):**
- Grilla hexagonal (solo cuadrada)
- Verificación de decodificación del QR recuperado (requiere un spike)

### Architecture Approach

Un binario con despacho por `"model"` (kohonen / oja / hopfield). Cada corrida escribe una copia de `config.json`, un `metrics.json` plano y CSV por modelo; `sweep.py` es agnóstico del modelo y arma `summary.csv` con las claves de `metrics.json` y las claves variadas. El preprocesamiento queda fuera de C: `prepare_creators.py` escribe la matriz z-scored y un `.meta.json` con el scaler, lo que permite responder las preguntas de mantenimiento. Detalle en `ARCHITECTURE.md`.

**Major components:**
1. Núcleo C (`neuron/`) — rng, config, matriz, resultados, despacho y los tres modelos
2. Preparación de datos (`scripts/`) — CSV de creadores con scaler guardado y PNG de QR a ±1
3. Análisis (`analysis/`) — sweeps generalizados, EDA/PCA, figuras
4. Entregables — slides e informe como Artifacts, ensamblados desde los fragmentos de cada fase

### Critical Pitfalls

Detalle en `PITFALLS.md`.

1. **El dataset tiene 50 filas, no 49** — el archivo no termina en newline y un contador de saltos de línea da 49; verificar n=50 y 33 columnas al cargar
2. **Colinealidad exacta** — 5 dependencias lineales (`price_ars`, `organic_posts_pct`, `total_engagement_per_1000`, suma de temas, suma de contenidos); hacer una auditoría de variables escrita y una corrida de sensibilidad con las 31 columnas
3. **Grilla del SOM elegida por QE** — usar QE, TE, ocupación, QE leave-one-out y estabilidad entre seeds; rango candidato aproximadamente 3×3 a 5×5
4. **Oja mal condicionado** — datos centrados, η chico y decreciente, renormalizar pesos, fijar convención de signo y comparar |cos| con PC1
5. **Hebb sobre los QR falla** — hacer primero un test de estabilidad con ruido cero, reportar la falla como hallazgo y agregar la regla de pseudo-inversa como remedio

## Implications for Roadmap

### Phase 1: Foundation y auditoría de datos
**Rationale:** Todo lo demás depende del entorno, del contrato C/Python y de las decisiones de variables.
**Delivers:** `.venv`, esqueleto C, `sweep.py` generalizado, lazo extremo a extremo con un modelo trivial; EDA, tabla de auditoría de variables, z-score y scaler; PCA con eigenvalues plot, loadings y biplot.
**Addresses:** EDA, preprocesamiento, PCA.
**Avoids:** pitfalls 2, 3, 4, 16, 17, 18, 21.

### Phase 2: Kohonen SOM
**Rationale:** Necesita el preprocesamiento y las métricas antes del barrido.
**Delivers:** QE, TE, ocupación y QE leave-one-out; regla multicriterio de elección de grilla; mapa de hits, matriz U, planos de componentes, perfiles por región, contraste con PC1/PC2 y estabilidad entre seeds.
**Avoids:** pitfalls 5, 6, 7, 19.

### Phase 3: Oja vs PC1
**Rationale:** Requiere datos centrados y la PCA de la fase 1.
**Delivers:** índice, |cos| contra PC1 y evidencia de que elegir el máximo para cualquier campaña es incorrecto.
**Avoids:** pitfalls 8, 9.

### Phase 4: Decisiones de campaña y mantenimiento
**Rationale:** Solo Python; consume Kohonen, Oja y PCA.
**Delivers:** comparación contra `followers` con k igual, sin afirmaciones de ROI, y respuestas concretas de mantenimiento.
**Avoids:** pitfalls 10, 20, 23.

### Phase 5: Hopfield núcleo y letras
**Rationale:** Valida los invariantes del núcleo antes de los QR, como recomienda el enunciado.
**Delivers:** W entera, actualización síncrona y asíncrona, energía por paso, detección de ciclos, clasificador almacenado/inverso/mezcla/espurio, matriz de solapamientos, barrido de capacidad sobre varios subconjuntos de letras y un estado espurio identificado.
**Avoids:** pitfalls 11, 12, 14, 26.

### Phase 6: Hopfield QR
**Rationale:** Se espera que Hebb falle, y la pseudo-inversa es una tarea planificada.
**Delivers:** test de estabilidad a ruido cero, reporte honesto de la falla, regla de pseudo-inversa, al menos 30 ensayos por nivel de ruido de 0 a 0,5, oclusión estructurada, línea base de Hamming al patrón más cercano y limitaciones.
**Avoids:** pitfalls 1, 13, 15, 22.

### Phase 7: Slides e informe
**Rationale:** Cada fase emite sus figuras y texto; esta fase solo ensambla.
**Delivers:** slides para presentar e informe en Artifact, con una tabla que mapea cada pregunta literal del enunciado a dónde se responde.
**Avoids:** pitfalls 6, 15, 23 a 25.

### Phase Ordering Rationale

- Las pistas del Ejercicio 1 y del Ejercicio 2 son independientes después de la fase 1, así que pueden intercalarse.
- Letras antes que QR.
- Fijar la regla de selección del SOM y el criterio de éxito de Hopfield antes de mirar los resultados.
- Registrar energía, solapamiento y trayectorias de pesos desde la primera implementación en C; agregarlo después entre seeds es caro.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2:** estrictez de la vecindad en R=1, topología y definiciones de QE/TE contra los PDF del curso
- **Phase 6:** pseudo-inversa bajo oclusión y disponibilidad de un decodificador de QR
- **Phase 7:** formato de Slides en Artifacts y si plotly JS corre en Artifacts

Phases with standard patterns (skip research-phase):
- **Phases 1, 3, 4, 5:** patrones estándar y bien documentados

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Versiones verificadas en registros y chequeo del entorno local; el embebido en Artifacts es MEDIUM |
| Features | MEDIUM-HIGH | El enunciado da lo obligatorio, pero no se leyeron los PDF del curso en esa pasada |
| Architecture | HIGH | Código de TP3 leído directamente; QR y costo de Hopfield medidos |
| Pitfalls | HIGH | Comportamientos reproducidos con prototipos en numpy |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- Filas del dataset: PROJECT.md dice 49 creadores pero hay 50; corregir PROJECT.md y verificar n=50 en el parser
- cJSON vs parser plano de TP3 (STACK y ARCHITECTURE difieren): default parser plano, cJSON solo si hace falta anidamiento; decidir en fase 1
- pandas (STACK lo incluye, ARCHITECTURE no): omitirlo por defecto
- Modo de actualización de Hopfield: el curso usa síncrono, el asíncrono garantiza energía monótona; implementar ambos con asíncrono como referencia
- «Todas sus variables» frente a la auditoría de variables: tratar la selección auditada como el conjunto «todas» y correr las 31 columnas con z-score como sensibilidad etiquetada
- Sin verificar: límites de Slides en Artifacts, decodificadores de QR y si las imágenes de 37×37 recuperadas decodifican, pseudo-inversa bajo oclusión, y las cifras de capacidad de letras (se usaron bitmaps propios del investigador)

## Sources

### Primary (HIGH confidence)
- Enunciado `docs/Archivo SIATP 42026.pdf`, `datos/` (medición directa) y código fuente de TP3
- Registros PyPI, npm y GitHub — versiones de las dependencias

### Secondary (MEDIUM confidence)
- PDF del curso de Kohonen y Hopfield — convenciones de vecindad y actualización
- arXiv: Dynamic Capacity Estimation in Hopfield Networks — capacidad de Hopfield

### Tertiary (LOW confidence)
- Decodificadores de QR y límites de Artifacts — sin verificar, requieren validación

---
*Research completed: 2026-10-20*
*Ready for roadmap: yes*
