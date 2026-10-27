# Requirements: TP4 SIA — Aprendizaje no supervisado y memoria asociativa

**Defined:** 2026-10-20
**Core Value:** Interpretar correctamente los resultados de los métodos no supervisados para tomar decisiones de campaña fundamentadas en evidencia

## v1 Requirements

### Infraestructura

- [x] **INFRA-01**: Un solo binario en C despacha por la clave `model` (kohonen / oja / hopfield) a partir de un `config.json`, compilable con `make`
- [x] **INFRA-02**: Cada corrida escribe en su directorio una copia de la config, un `metrics.json` plano y los CSV propios del modelo, con seed fija y reproducible
- [x] **INFRA-03**: `sweep.py` corre series con varias seeds para cualquier modelo y arma un `summary.csv` con las claves de `metrics.json` y las claves variadas
- [x] **INFRA-04**: Existe un `.venv` con dependencias fijadas y tests del núcleo en C con `make test`

### Datos y PCA

- [x] **DATA-01**: El loader verifica n=50 filas y 33 columnas, y falla si no coinciden
- [x] **DATA-02**: EDA de distribuciones y correlaciones, con tabla de auditoría de variables que documenta las 5 dependencias lineales exactas y la regla de selección
- [x] **DATA-03**: Z-score en Python con scaler guardado (`.meta.json`) para mapear creadores nuevos
- [x] **DATA-04**: PCA por autovalores con scree, loadings y biplot, y justificación escrita de reducir o no la dimensionalidad
- [x] **DATA-05**: Corrida de sensibilidad con las 31 columnas, etiquetada, comparada contra el conjunto auditado

### Kohonen

- [x] **SOM-01**: SOM en C con grilla k×k, vecindad y η decrecientes, e inicialización con muestras
- [x] **SOM-02**: El SOM reporta QE, TE y ocupación por neurona
- [x] **SOM-03**: Barrido multi-seed de hiperparámetros con regla de elección de grilla multicriterio (QE, TE, ocupación, QE leave-one-out, estabilidad entre seeds), fijada antes de ver los resultados
- [x] **SOM-04**: Mapa de hits, matriz U y planos de componentes de la grilla elegida
- [x] **SOM-05**: Perfiles por región interpretados para el caso de uso y contrastados con PC1/PC2 (biplot); respuesta escrita a qué indica una distancia alta en la matriz U

### Oja

- [x] **OJA-01**: Oja en C sobre datos centrados, con η chico y decreciente, pesos renormalizados y convención de signo fija
- [x] **OJA-02**: Comparación del índice contra la proyección sobre PC1 con |cos| y correlación de rangos
- [x] **OJA-03**: Interpretación del índice con evidencia (correlación con followers y temas) de por qué elegir el máximo para cualquier campaña es incorrecto

### Decisiones de campaña

- [x] **CAMP-01**: Recomendación por campaña (fútbol, perros, maquillaje, arte) justificada con los resultados de Kohonen, Oja y PCA
- [x] **CAMP-02**: Comparación contra la estrategia solo por `followers` con el mismo k (overlap@k, proporción por tema, costo por alcance argentino), sin afirmaciones de ROI
- [x] **CAMP-03**: Respuestas concretas de mantenimiento: nueva campaña, creadores o variables nuevas, actualización mensual

### Hopfield

- [x] **HOP-01**: Hopfield en C con W entera, actualización síncrona y asíncrona, energía por paso, detección de ciclos y clasificación del estado final
- [x] **HOP-02**: 4 letras de 5×5 almacenadas y recuperadas, con análisis de ortogonalidad y capacidad sobre varios subconjuntos de letras
- [x] **HOP-03**: Un patrón muy ruidoso que converge a un estado espurio identificado y clasificado (inverso, mezcla u otro)
- [x] **HOP-04**: Preparación de los 5 QR de 37×37 a ±1 con aserción de que son 0/255 puros, y matriz de solapamientos
- [x] **HOP-05**: QR con regla de Hebb: test de estabilidad a ruido cero y al menos 8 niveles de ruido con 30 o más ensayos cada uno, con energía e iteraciones por paso; el fallo se reporta como hallazgo
- [x] **HOP-06**: Regla de pseudo-inversa para los QR, comparada contra Hebb y contra la línea base de Hamming al patrón más cercano
- [x] **HOP-07**: Limitaciones del caso de uso explicadas (correlación entre QR, sensibilidad a corrimientos, corrección de errores propia del QR, tabla de búsqueda equivalente)

### Entregables

- [x] **DELIV-01**: Slides en Artifact para presentar, una sección por ejercicio
- [x] **DELIV-02**: Informe en Artifact para entender el proyecto, con tabla que mapea cada pregunta del enunciado a dónde se responde
- [x] **DELIV-03**: `CLAUDE.md`, `DECISIONS.md` y README con cómo reproducir cada resultado, como en TP3

## v2 Requirements

### Kohonen

- **SOM-06**: Grilla hexagonal comparada con la cuadrada

### Hopfield

- **HOP-08**: Daño estructurado en QR (oclusión, rayones, manchas)
- **HOP-09**: Chequeo con un decodificador de QR de los patrones recuperados (requiere spike)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Análisis de marketing exhaustivo | El enunciado aclara que el foco son los métodos no supervisados |
| Librerías de ML para Kohonen, Oja o Hopfield | Son el objeto de estudio y se implementan a mano |
| QR de tamaño distinto de 37×37 | El enunciado fija ese tamaño |
| Dashboards o UIs | Fuera del alcance de un TP |
| Elegir la grilla del SOM por menor QE | El QE baja siempre al agrandar la grilla con 50 muestras |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 1 | Complete |
| INFRA-02 | Phase 1 | Complete |
| INFRA-03 | Phase 1 | Complete |
| INFRA-04 | Phase 1 | Complete |
| DATA-01 | Phase 1 | Complete |
| DATA-02 | Phase 1 | Complete |
| DATA-03 | Phase 1 | Complete |
| DATA-04 | Phase 1 | Complete |
| DATA-05 | Phase 1 | Complete |
| SOM-01 | Phase 2 | Complete |
| SOM-02 | Phase 2 | Complete |
| SOM-03 | Phase 2 | Complete |
| SOM-04 | Phase 2 | Complete |
| SOM-05 | Phase 2 | Complete |
| OJA-01 | Phase 3 | Complete |
| OJA-02 | Phase 3 | Complete |
| OJA-03 | Phase 3 | Complete |
| CAMP-01 | Phase 3 | Complete |
| CAMP-02 | Phase 3 | Complete |
| CAMP-03 | Phase 3 | Complete |
| HOP-01 | Phase 4 | Complete |
| HOP-02 | Phase 4 | Complete |
| HOP-03 | Phase 4 | Complete |
| HOP-04 | Phase 5 | Complete |
| HOP-05 | Phase 5 | Complete |
| HOP-06 | Phase 5 | Complete |
| HOP-07 | Phase 5 | Complete |
| DELIV-01 | Phase 6 | Complete |
| DELIV-02 | Phase 6 | Complete |
| DELIV-03 | Phase 6 | Complete |

**Coverage:**
- v1 requirements: 30 total
- Mapped to phases: 30 ✓
- Unmapped: 0

---
*Requirements defined: 2026-10-20*
*Last updated: 2026-10-20 after roadmap creation*
