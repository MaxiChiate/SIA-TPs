# Decisiones del TP4

Decisiones que nos pueden preguntar en la defensa. Cada una dice qué decidimos, por qué y dónde quedó registrada.

Los IDs de decisión (`D-01`, `D-02`, ...) reinician en cada fase: cada fase tiene su propio `D-01`. Por eso acá todo ID se escribe con su fase: `F2 D-07` es la decisión D-07 de la Fase 2. Las "Decisiones del proyecto" (`KD-n`) son las filas de la tabla *Key Decisions* de `PROJECT.md`.

Este archivo también es la fuente del glosario del informe: al armar el informe, los `D-NN`, `Pitfall N` y IDs de requisito (`HOP-04`, `DATA-01`, ...) que aparecen en los fragmentos `deliverables/0X-*.md` se enlazan a las entradas de acá. Por eso los títulos siguen una gramática fija: `### F<n> D-<nn> — ...`, `### KD-<n> — ...`, `### Pitfall <n> — ...` y `### <ID de requisito> — ...`.

Cada entrada tiene tres líneas: **Qué** (lo decidido, fiel a la línea del `CONTEXT.md`), **Por qué** (la razón registrada) y **Dónde** (el `CONTEXT.md` que la registró y, cuando se aplica en un fragmento, la sección del fragmento).

## Índice

- [Decisiones del proyecto](#decisiones-del-proyecto)
- [Fase 1 — Datos, auditoría de variables y PCA](#fase-1--datos-auditoría-de-variables-y-pca)
- [Fase 2 — Kohonen (SOM)](#fase-2--kohonen-som)
- [Fase 3 — Oja y decisiones de campaña](#fase-3--oja-y-decisiones-de-campaña)
- [Fase 4 — Hopfield: núcleo y letras](#fase-4--hopfield-núcleo-y-letras)
- [Fase 5 — Hopfield: QR](#fase-5--hopfield-qr)
- [Fase 6 — Slides e informe](#fase-6--slides-e-informe)
- [Pitfalls citados en los fragmentos](#pitfalls-citados-en-los-fragmentos)
- [Requisitos citados en los fragmentos](#requisitos-citados-en-los-fragmentos)

## Decisiones del proyecto

### KD-1 — Núcleo en C + análisis en Python

**Qué:** el núcleo de los algoritmos (Kohonen, Oja, Hopfield) está en C con configuración JSON y Makefile; el análisis, los gráficos y la preparación de datos están en Python.

**Por qué:** es la misma estructura que TP3 y permite reutilizar su infraestructura (rng, parseo de config, sweeps, estilo de gráficos).

**Dónde:** [PROJECT.md](.planning/PROJECT.md) (tabla Key Decisions) · [01-CONTEXT.md](.planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-CONTEXT.md) (F1 D-01 a D-07)

### KD-2 — Informe como Artifact + slides aparte

**Qué:** las slides sirven para presentar y el informe, publicado como Artifact, sirve para entender el proyecto; son dos entregables separados.

**Por qué:** cada uno tiene un público y un uso distinto: la exposición oral frente a la lectura con calma.

**Dónde:** [PROJECT.md](.planning/PROJECT.md) (tabla Key Decisions) · [06-CONTEXT.md](.planning/phases/06-slides-e-informe/06-CONTEXT.md)

### KD-3 — Regla de elección de grilla del SOM fijada y commiteada antes de ver resultados

**Qué:** la regla de elección de la grilla del SOM se fijó y se commiteó (commit `ea7a0b1`, con `rule_digest` verificado en cada paso posterior) antes de correr el barrido. Resultado en la Fase 2: eligió k = 5 (escalón) por QE leave-one-out.

**Por qué:** evitar elegir k a posteriori. La regla "fijada de antemano" no se edita in situ: cualquier cambio pasa por discusión.

**Dónde:** [PROJECT.md](.planning/PROJECT.md) (tabla Key Decisions) · [02-CONTEXT.md](.planning/phases/02-kohonen-som/02-CONTEXT.md) (F2 D-10 a D-14) · [fragmento 02 §2](deliverables/02-kohonen.md)

### KD-4 — Reportar el resultado de la regla tal cual aunque sea poco favorable

**Qué:** el resultado de la regla se informa como salió: etapa 2 "no robusta" (TE > 0,05 en 5 variantes) y una sola región (R1 = 50 creadores) con el percentil fijado. En la Fase 2 el UAT aceptó leer los perfiles por neurona.

**Por qué:** honestidad del análisis; no se retoca la regla para obtener un resultado más lindo.

**Dónde:** [PROJECT.md](.planning/PROJECT.md) (tabla Key Decisions) · [02-CONTEXT.md](.planning/phases/02-kohonen-som/02-CONTEXT.md) (F2 D-14) · [fragmento 02 §3 y §6](deliverables/02-kohonen.md)

### KD-5 — Contraste SOM vs PCA con nulos por permutación

**Qué:** el contraste entre el mapa y las componentes principales se hace con nulos por permutación (seed 2026, 1000 permutaciones). Resultado en la Fase 2: el mapa sigue a PC1 (R² 0,961, p = 0,001) y no a PC2 (R² 0,055, p = 0,267).

**Por qué:** afirmar "el mapa sigue PC1" con evidencia y no a ojo.

**Dónde:** [PROJECT.md](.planning/PROJECT.md) (tabla Key Decisions) · [02-CONTEXT.md](.planning/phases/02-kohonen-som/02-CONTEXT.md) (contraste con PCA, criterio del planner) · [fragmento 02 §6.4](deliverables/02-kohonen.md)

### KD-6 — Protocolo de los 5 QR pre-registrado y commiteado antes de correr la red

**Qué:** el protocolo de los 5 QR se pre-registró y se commiteó con guardia sha256 sobre el protocolo y los 5 PNG (F5 D-01 y D-02) antes de correr la red. Resultado en la Fase 5: Hebb 0 % de recuperación exacta incluso a ruido cero (QR correlacionados, solapamiento medio 0,67); la pseudo-inversa da 100 % a ruido 0 y lo sostiene hasta 0,30; el vecino más cercano por Hamming casi la iguala hasta ruido 0,40.

**Por qué:** que el hallazgo "Hebb falla" no pueda verse como elegido a posteriori; el umbral de veredicto se fija antes de ver resultados.

**Dónde:** [PROJECT.md](.planning/PROJECT.md) (tabla Key Decisions) · [05-CONTEXT.md](.planning/phases/05-hopfield-con-qr/05-CONTEXT.md) (F5 D-01 y D-02) · [fragmento 05 §3](deliverables/05-hopfield-qr.md)

## Fase 1 — Datos, auditoría de variables y PCA

### F1 D-01 — Parser JSON: cJSON v1.7.19 vendored

**Qué:** el parser de configs es cJSON v1.7.19 vendored en `neuron/vendor/cjson/` (compilado sin `-Wextra -Wpedantic` por archivo). Resuelve la contradicción entre STATE.md ("plano por defecto") y CLAUDE.md.

**Por qué:** las configs de las fases siguientes son anidadas (grilla, schedules, listas de ruido). Es una decisión costosa de revertir: todas las configs y `config.c` de las Fases 2-5 dependen del formato.

**Dónde:** [01-CONTEXT.md](.planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-CONTEXT.md)

### F1 D-02 — Validación estricta de la config

**Qué:** una clave desconocida, faltante o de tipo incorrecto aborta con un mensaje claro, al estilo TP3. No hay defaults silenciosos.

**Por qué:** que un error de tipeo en una config no cambie un experimento sin avisar.

**Dónde:** [01-CONTEXT.md](.planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-CONTEXT.md)

### F1 D-03 — Modelo trivial de punta a punta: stubs deterministas por clave `model`

**Qué:** hay un stub determinista por cada clave `model` (kohonen, oja, hopfield). Cada uno lee su input real, usa el RNG splitmix64 con seed y escribe un `metrics.json` plano y un CSV tipo. Las Fases 2-5 reemplazan el cuerpo.

**Por qué:** prueba el despacho, la config, el RNG, la escritura y la reproducibilidad byte a byte antes de tener los algoritmos reales.

**Dónde:** [01-CONTEXT.md](.planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-CONTEXT.md)

### F1 D-04 — Convención de corrida y reproducibilidad con `diff -r`

**Qué:** Python escribe el input (`datos/prepared/creadores_zscore.csv` más `.meta.json`), la config apunta al input y C escribe `results/<timestamp>_<model>_seed<N>/` con la copia de `config.json`, `metrics.json` plano y los CSV. El timestamp aparece solo en el nombre de la carpeta y nunca dentro de un archivo (sin rutas absolutas).

**Por qué:** así un `diff -r` entre dos corridas con la misma seed sirve como prueba de reproducibilidad.

**Dónde:** [01-CONTEXT.md](.planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-CONTEXT.md) · [fragmento 01 §8](deliverables/01-datos-pca.md)

### F1 D-05 — Layout `neuron/`, `analysis/`, `scripts/` como TP3

**Qué:** se copia tal cual `rng.c/h`; se copian y adaptan el Makefile compatible con make 3.81 (`-MMD -MP`), `results.c`, `sweep.py` y el runner de tests; se rehacen la config (cJSON) y las métricas. La preparación de datos va en `scripts/` y el EDA, la PCA y los gráficos en `analysis/`. El `.venv` se crea con `uv` y el Makefile usa `PY ?= .venv/bin/python`.

**Por qué:** reutilizar la infraestructura probada de TP3. Las adaptaciones quedaron registradas en 01-01 y 01-03.

**Dónde:** [01-CONTEXT.md](.planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-CONTEXT.md) · [fragmento 01 §8](deliverables/01-datos-pca.md)

### F1 D-06 — Python sin pandas

**Qué:** el análisis usa `csv` de la biblioteca estándar y numpy para EDA, PCA y z-score; matplotlib para las figuras (plotly solo si hace falta un gráfico interactivo); Pillow para los QR. Las versiones se pinean en `analysis/requirements.txt`.

**Por qué:** fue una decisión del usuario y anula la mención de pandas en CLAUDE.md.

**Dónde:** [01-CONTEXT.md](.planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-CONTEXT.md) · [fragmento 01 §8](deliverables/01-datos-pca.md)

### F1 D-07 — `make test`: menos de 10 tests entre C y Python

**Qué:** `make test` cubre C (la config rechaza claves desconocidas, misma seed da los mismos bytes, despacho por `model`) y Python con pytest: el loader falla si no es 50×33; el z-score es invertible desde `.meta.json`; un creador nuevo se mapea usando solo el scaler; los autovalores de la matriz de correlación suman el número de variables y proyectar y reconstruir con todas las PCs devuelve los datos; las variables eliminadas son exactamente las 5 acordadas y la matriz resultante tiene rango completo. Con las 31 columnas, la matriz de correlación tiene 5 autovalores prácticamente cero.

**Por qué:** una red de seguridad chica pero que cubre lo que más cuesta recuperar si se rompe: dispatch, reproducibilidad, loader, scaler y auditoría.

**Dónde:** [01-CONTEXT.md](.planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-CONTEXT.md) · [fragmento 01 §1 y §8](deliverables/01-datos-pca.md)

### F1 D-08 — El conjunto auditado quita las 5 dependencias lineales exactas

**Qué:** el conjunto que entra a PCA, SOM y Oja quita las 5 dependencias lineales exactas (`price_ars = 1500·price_usd`, `organic = 100 − sponsored`, `total_engagement = likes+comments+saves+shares`, los 4 `topic_*` suman 100, los 4 `content_*` suman 100). Quedan alrededor de 26 de las 31 variables; las 31 con z-score corren como sensibilidad etiquetada (DATA-05).

**Por qué:** las dependencias son exactas (error ≤ 1e-13), lo que hace singular la matriz de correlación. La corrida de sensibilidad permite mostrar que la decisión es defendible.

**Dónde:** [01-CONTEXT.md](.planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-CONTEXT.md) · [fragmento 01 §3 y §7](deliverables/01-datos-pca.md)

### F1 D-09 — Regla fija por grupo para elegir qué variable se saca

**Qué:** la regla, escrita en la tabla de auditoría, saca `price_ars`, `organic_posts_pct`, `total_engagement_per_1000` y, de `topic_*` y `content_*`, la de menor varianza medida en escala original (antes del z-score). Las variables sacadas se conservan en el CSV crudo para reportar. El plano de componentes de las que no entran al entrenamiento (en particular la de `topic_*` que se saque) se calcula en la Fase 2 como el promedio de esa variable entre los creadores asignados a cada neurona.

**Por qué:** las variables sacadas se reconstruyen desde las restantes, y así las 4 campañas tienen su plano aunque el SOM se entrene con 3 topics.

**Dónde:** [01-CONTEXT.md](.planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-CONTEXT.md) · [fragmento 01 §3](deliverables/01-datos-pca.md)

### F1 D-10 — Las casi redundantes solo se documentan

**Qué:** las variables casi redundantes (no exactas) no se eliminan: `estimated_argentina_reach` (≈ `average_reach × argentina_audience_pct/100`, error ≤ 0,5 por redondeo) y los pares con |r| > 0,9 con `followers` (reach, impressions, views). Quedan en el conjunto y se discuten en la PCA (PC1 ≈ tamaño).

**Por qué:** no son dependencias exactas, así que no vuelven singular la matriz; sacarlas sería un juicio no respaldado por el álgebra.

**Dónde:** [01-CONTEXT.md](.planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-CONTEXT.md) · [fragmento 01 §3.3](deliverables/01-datos-pca.md)

### F1 D-11 — Z-score directo, sin log ni winsorizar

**Qué:** se estandariza con z-score directo. El sesgo máximo (≈ 2 en `estimated_argentina_reach`; followers, reach y precio ≈ 1) se documenta en el EDA. El log queda como sensibilidad opcional, no como camino principal. El scaler (media, desvío) se guarda en `.meta.json`.

**Por qué:** el sesgo es moderado y el camino directo es el más simple de explicar y de invertir para mapear creadores nuevos.

**Dónde:** [01-CONTEXT.md](.planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-CONTEXT.md) · [fragmento 01 §4](deliverables/01-datos-pca.md)

### F1 D-12 — PCA por autovalores con regla de decisión escrita antes de mirar los autovalores

**Qué:** la PCA se hace sobre la matriz de correlación (= covarianza del z-score) por autovalores, verificada con `np.linalg.eigh`. El criterio de 80 % de varianza acumulada fija k; ese umbral es una convención del equipo, porque la teoría del curso da la proporción de varianza de cada componente pero no fija un umbral.

**Por qué:** la regla se escribió antes de mirar los autovalores para no elegir k a posteriori.

**Dónde:** [01-CONTEXT.md](.planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-CONTEXT.md) · [fragmento 01 §5](deliverables/01-datos-pca.md)

### F1 D-13 — La PCA es diagnóstica

**Qué:** la PCA justifica por escrito si se podría reducir y cómo leer PC1 y PC2 (biplot), pero Kohonen y Oja corren sobre la matriz z-scored completa del conjunto auditado, como pide el enunciado. No se agrega una corrida del SOM sobre k PCs.

**Por qué:** respetar el enunciado (los métodos usan todas las variables) sin ampliar el alcance de la Fase 2.

**Dónde:** [01-CONTEXT.md](.planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-CONTEXT.md) · [fragmento 01 §5 y §6](deliverables/01-datos-pca.md)

### F1 D-14 — Sensibilidad de la PCA a podar por correlación (corrección posterior a la entrega)

**Qué:** además de las 5 dependencias exactas (F1 D-08), se probó podar por umbral de correlación sobre las 26 variables auditadas. La regla es iterativa: en cada umbral se toma el par con mayor |r| ≥ τ y sale la variable de ese par con mayor |r| medio con las demás (empate: la de columna mayor), hasta que ningún par llega a τ. Se calculó la PCA para τ = 0,95; 0,90; 0,85; 0,80; 0,70; 0,60 y 0,50 (`make corr-prune`, `analysis/corr_prune.py`) y la tabla va en la slide `pca-prune`. No se rehizo el SOM, Oja ni las campañas con ningún τ: el umbral que se use para rehacer el ejercicio 1 (0,70 u 0,80) se decide aparte.

**Por qué:** la corrección recibida fue que sacar solo las variables triviales no alcanza como criterio. El umbral no sale de la teoría del curso: es una decisión del equipo. Se justifica con la convención de |r| ≥ 0,8 como correlación fuerte (el mismo `STRONG_THRESHOLD` del EDA) y con el condicionamiento de la matriz (el número de condición baja de unos 856 con 0,95 a unos 108 con 0,80). A 0,80 `price_usd` sale con |r| = 0,822 con `followers`, así que ese resultado no es robusto en el borde. Un umbral muy bajo deja pocas variables y se pierde información real, no redundancia: con 0,50 no queda tamaño ni engagement por mil y PC1 baja al 27,8 %.

**Dónde:** [`analysis/corr_prune.py`](analysis/corr_prune.py) · slide `pca-prune` · F1 D-08 y D-10 siguen valiendo para el conjunto auditado de 26.

## Fase 2 — Kohonen (SOM)

### F2 D-01 — Vecindad configurable: escalón (principal) y gaussiana (variante)

**Qué:** la vecindad se elige por clave de config. Escalón del curso (camino principal): se actualizan las neuronas con distancia en la grilla `||n − n_k|| ≤ R(t)`, con `≤` y no el `<` estricto de las slides, y R(0) configurable decrece hasta 1 inclusive. Gaussiana (variante): `h = exp(−d²/2σ²)` con σ decreciente y un piso mayor que 0. La regla es `W_j += η(t)·h_j·(x − W_j)` (h ∈ {0, 1} en escalón).

**Por qué:** con `≤`, R = 1 actualiza los 4 vecinos pegados y no solo la ganadora. Es costosa de revertir: las claves de config, las series y el texto del informe dependen de los dos modos.

**Dónde:** [02-CONTEXT.md](.planning/phases/02-kohonen-som/02-CONTEXT.md) · [fragmento 02 §1](deliverables/02-kohonen.md)

### F2 D-02 — η decrece exponencialmente

**Qué:** `η(t) = η0·(ηf/η0)^(t/T)`, con η0 < 1 y ηf en la config (baseline 0,5 a 0,01).

**Por qué:** un decaimiento suave y con forma cerrada, fácil de fijar en la config y de explicar.

**Dónde:** [02-CONTEXT.md](.planning/phases/02-kohonen-som/02-CONTEXT.md) · [fragmento 02 §1](deliverables/02-kohonen.md)

### F2 D-03 — Entrenamiento por épocas barajadas

**Qué:** cada época recorre los 50 creadores en un orden barajado con el `Rng` de la seed (splitmix64, Fase 1); T = épocas · n pasos. El baseline es del orden del 500·N del curso (N = 26, unos 13 000 pasos, alrededor de 260 épocas).

**Por qué:** que el orden de presentación no sesgue el mapa y que la corrida sea reproducible con la seed.

**Dónde:** [02-CONTEXT.md](.planning/phases/02-kohonen-som/02-CONTEXT.md) · [fragmento 02 §1](deliverables/02-kohonen.md)

### F2 D-04 — Adyacencia de 4 vecinos para el TE y la matriz U

**Qué:** el error topográfico (TE) es la fracción de creadores cuya primera y segunda BMU no son 4-vecinas. La matriz U es el promedio de la distancia euclídea entre el prototipo de cada neurona y los de sus 4-vecinos (los bordes promedian los vecinos que existen).

**Por qué:** es la adyacencia que corresponde a R = 1 del curso, la misma que usa la actualización.

**Dónde:** [02-CONTEXT.md](.planning/phases/02-kohonen-som/02-CONTEXT.md) · [fragmento 02 §1](deliverables/02-kohonen.md)

### F2 D-05 — Inicialización con muestras del conjunto de entrenamiento

**Qué:** los prototipos arrancan en muestras del conjunto de entrenamiento (SOM-01). La distancia es euclídea sobre las 26 variables auditadas con z-score.

**Por qué:** es la recomendación de las slides para evitar unidades muertas.

**Dónde:** [02-CONTEXT.md](.planning/phases/02-kohonen-som/02-CONTEXT.md) · [fragmento 02 §1](deliverables/02-kohonen.md)

### F2 D-06 — Barrido en dos etapas

**Qué:** etapa 1: k ∈ {2, ..., 8} por vecindad ∈ {escalón, gaussiana} con un schedule baseline fijo (R0 ≈ k/2 o su equivalente σ0, η de 0,5 a 0,01, unas 260 épocas); la regla de F2 D-10 a D-14 elige k. Etapa 2: sobre la k elegida (vecindad escalón) se varían R0, η0 y épocas de a uno para mostrar que la elección es robusta. Las series usan el `sweep.py` existente.

**Por qué:** separar la elección de la grilla de la prueba de robustez del schedule. Es reversible.

**Dónde:** [02-CONTEXT.md](.planning/phases/02-kohonen-som/02-CONTEXT.md) · [fragmento 02 §2 y §4](deliverables/02-kohonen.md)

### F2 D-07 — Rango k = 2 a 8, incluidas grillas con más neuronas que creadores

**Qué:** k va de 2 a 8. Incluye a propósito grillas con más neuronas que creadores (8×8 = 64 > 50), por lo que hay que levantar el tope k² ≤ n que tenía `read_grid_k` en el stub.

**Por qué:** la curva tiene que mostrar que el QE baja siempre mientras la ocupación colapsa.

**Dónde:** [02-CONTEXT.md](.planning/phases/02-kohonen-som/02-CONTEXT.md) · [fragmento 02 §2 y §5](deliverables/02-kohonen.md)

### F2 D-08 — 10 seeds por configuración

**Qué:** se corren 10 seeds por configuración y se reporta media ± desvío, no la mejor seed.

**Por qué:** que la elección no dependa de una corrida afortunada.

**Dónde:** [02-CONTEXT.md](.planning/phases/02-kohonen-som/02-CONTEXT.md) · [fragmento 02 §2 y §3](deliverables/02-kohonen.md)

### F2 D-09 — QE leave-one-out exacto, calculado en Python

**Qué:** el QE leave-one-out es un k-fold con k = n = 50 (LOO exacto, SOM-03): por cada seed y configuración, 50 entrenamientos con un creador excluido y la distancia del excluido a su BMU; QE-LOO es el promedio. El binario de C no gana un modo LOO: Python arma los CSV de entrenamiento y orquesta las corridas.

**Por qué:** cumple SOM-03 tal como está escrito y mantiene simple el núcleo en C.

**Dónde:** [02-CONTEXT.md](.planning/phases/02-kohonen-som/02-CONTEXT.md) · [fragmento 02 §2](deliverables/02-kohonen.md)

### F2 D-10 — La regla de grilla se commitea antes de correr la etapa 1

**Qué:** la regla se escribe en el fragmento de la Fase 2 (estilo `deliverables/01-datos-pca.md` §5) y se commitea antes de correr el barrido de la etapa 1; el commit es la evidencia de SOM-03.

**Por qué:** es una decisión de una sola vía (*one-way*): una vez vistos los resultados, cambiar la regla invalida la afirmación "fijada de antemano" del informe.

**Dónde:** [02-CONTEXT.md](.planning/phases/02-kohonen-som/02-CONTEXT.md) · [fragmento 02 §2](deliverables/02-kohonen.md)

### F2 D-11 — Regla de forma filtros + desempate, solo sobre vecindad escalón

**Qué:** se aplica solo a las corridas con vecindad escalón; la gaussiana se reporta al lado y no participa. (1) Se descartan las k con TE medio > 0,05 o con ocupación insuficiente (F2 D-12). (2) Entre las que quedan gana el menor QE-LOO medio. (3) Si otra k sobreviviente está a menos de 1 desvío (entre seeds) del QE-LOO ganador, gana la más estable entre seeds (F2 D-13); si siguen empatadas, la k más chica.

**Por qué:** combinar un criterio de generalización (QE-LOO) con filtros de calidad del mapa y de ocupación, y desempatar por estabilidad y parsimonia.

**Dónde:** [02-CONTEXT.md](.planning/phases/02-kohonen-som/02-CONTEXT.md) · [fragmento 02 §2 y §3](deliverables/02-kohonen.md)

### F2 D-12 — Ocupación suficiente

**Qué:** ocupación suficiente son dos condiciones sobre la media entre seeds: a lo sumo 20 % de neuronas vacías y al menos 2 creadores por neurona ocupada en promedio.

**Por qué:** descartar grillas que tienen más neuronas que información, donde el QE baja a costa de neuronas vacías.

**Dónde:** [02-CONTEXT.md](.planning/phases/02-kohonen-som/02-CONTEXT.md) · [fragmento 02 §2](deliverables/02-kohonen.md)

### F2 D-13 — Estabilidad entre seeds por Spearman de distancias en la grilla

**Qué:** para cada seed se arma la matriz de 50×50 de distancias en la grilla entre las BMU de cada par de creadores; la estabilidad es el promedio del Spearman entre las matrices de todos los pares de seeds (45 pares con 10 seeds).

**Por qué:** es invariante a rotación y reflexión del mapa y comparable entre k.

**Dónde:** [02-CONTEXT.md](.planning/phases/02-kohonen-som/02-CONTEXT.md) · [fragmento 02 §2](deliverables/02-kohonen.md)

### F2 D-14 — Si ninguna k pasa los filtros, se quita solo el de TE

**Qué:** si ninguna k pasa los filtros, se quita solo el filtro de TE, se aplica el resto de la regla sin cambios y el informe dice explícitamente que ninguna grilla cumplió TE ≤ 0,05. La ocupación no se relaja nunca.

**Por qué:** dejar escrito de antemano qué se hace cuando la regla no encuentra ganadora, sin retocarla después. Es lo que pasó: etapa 2 no robusta y una sola región.

**Dónde:** [02-CONTEXT.md](.planning/phases/02-kohonen-som/02-CONTEXT.md) · [fragmento 02 §2 y §3](deliverables/02-kohonen.md)

### F2 D-15 — El QE de entrenamiento se reporta pero no decide

**Qué:** el QE de entrenamiento se reporta y se grafica contra k, pero no decide la grilla. El texto dice que por QE solo ganaría la grilla más grande.

**Por qué:** "elegir la grilla del SOM por menor QE" está fuera de alcance en REQUIREMENTS: premia la grilla más grande.

**Dónde:** [02-CONTEXT.md](.planning/phases/02-kohonen-som/02-CONTEXT.md) · [fragmento 02 §2, §3 y §5](deliverables/02-kohonen.md)

## Fase 3 — Oja y decisiones de campaña

### F3 D-01 — Oja de una neurona en C, con número fijo de épocas

**Qué:** Oja de una neurona en C sobre `datos/prepared/creadores_zscore.csv` (26 variables ya centradas), con η chico y decreciente, épocas barajadas con el `Rng` de la seed y número fijo de épocas (sin parada por tolerancia). Al final se renormaliza w a norma 1. La convergencia se muestra con una traza por época (`trace.csv`) que guarda |w|, ‖Δw‖ y w; el |cos(w, PC1)| se agrega en Python.

**Por qué:** hay que mantenerse en el rango estable del Pitfall 8 (η·|x|² ≪ 1; con 26 variables, |x|² ≈ 26), y el coseno con PC1 no se calcula en C porque no hay eigen-solver (ver F3 D-05).

**Dónde:** [03-CONTEXT.md](.planning/phases/03-oja-y-decisiones-de-campa-a/03-CONTEXT.md) · [fragmento 03 §1](deliverables/03-oja-campanas.md)

### F3 D-02 — Convención de signo igual a la de la PCA

**Qué:** después de renormalizar, w se orienta de modo que su coeficiente de mayor |valor| sea positivo (la misma convención de `deliverables/01-datos-pca.md` §5). Hoy ese coeficiente es `average_caption_words` (+0,94 en PC1): un índice alto es un creador chico, de epígrafes largos, tutorial y con más perros; uno bajo es grande, caro, de video corto. La convención se aplica en C, para que `index.csv` ya salga orientado.

**Por qué:** w y −w son igualmente estables, así que "el máximo" no significa nada sin una orientación declarada. Es costosa de revertir: las tablas de Oja contra PC1, la tabla de evidencia del máximo y el texto del informe se leen con este signo.

**Dónde:** [03-CONTEXT.md](.planning/phases/03-oja-y-decisiones-de-campa-a/03-CONTEXT.md) · [fragmento 03 §1, §3, §4, §5 y §6](deliverables/03-oja-campanas.md)

### F3 D-03 — 10 seeds y una seed fija para tablas y figuras

**Qué:** se corren 10 seeds (como F2 D-08) y se reporta la dispersión entre seeds una vez fijado el signo (|cos| entre los w de distintas seeds, rango del índice por creador). Una seed fija produce las tablas y figuras.

**Por qué:** mostrar que el índice no depende de la seed, igual que en el SOM.

**Dónde:** [03-CONTEXT.md](.planning/phases/03-oja-y-decisiones-de-campa-a/03-CONTEXT.md) · [fragmento 03 §1](deliverables/03-oja-campanas.md)

### F3 D-04 — Salidas de la corrida de Oja

**Qué:** `weights.csv` (w final orientado), `index.csv` (sample, index), `trace.csv` (época, |w| antes de renormalizar, ‖Δw‖, η) y un `metrics.json` plano (`w_norm_final`, `delta_w_final`, épocas, etc.). Las claves nuevas se validan estrictamente como el resto (F1 D-02).

**Por qué:** dejar todo lo necesario para que Python compare contra PC1 sin recalcular nada.

**Dónde:** [03-CONTEXT.md](.planning/phases/03-oja-y-decisiones-de-campa-a/03-CONTEXT.md) · [fragmento 03 §1](deliverables/03-oja-campanas.md)

### F3 D-05 — La comparación Oja vs PC1 se calcula en Python

**Qué:** Python lee `weights.csv`, `index.csv` y las cargas y scores de `analysis/results/pca/audited/` y reporta |cos| y cos con signo entre w y v1, Pearson y Spearman entre el índice y el score de PC1, y overlap@5 y overlap@10. Un pytest exige |cos(w, v1)| > 0,99 en la corrida smoke. No hay eigen-solver en C.

**Por qué:** la validación contra la PCA por autovalores queda independiente de la implementación de Oja.

**Dónde:** [03-CONTEXT.md](.planning/phases/03-oja-y-decisiones-de-campa-a/03-CONTEXT.md) · [fragmento 03 §2](deliverables/03-oja-campanas.md)

### F3 D-06 — "¿Elegir el máximo para cualquier campaña?" se responde con una tabla de evidencia

**Qué:** la tabla muestra las cargas de w (ordenadas por |valor|), la correlación del índice con `followers` y con cada uno de los 4 `topic_*_pct` crudos (incluido `topic_art_pct`, que no entra al entrenamiento), y cuántos de los top-10 de cada tema dominante caen en el top-10 del índice, con los dos signos (el de F3 D-02 y el opuesto). El texto empieza por la respuesta ("no") y sigue con la evidencia. El índice no se presenta con la palabra «mejor».

**Por qué:** mostrar que "el máximo" depende de una convención y no de un mérito de los creadores.

**Dónde:** [03-CONTEXT.md](.planning/phases/03-oja-y-decisiones-de-campa-a/03-CONTEXT.md) · [fragmento 03 §3](deliverables/03-oja-campanas.md)

### F3 D-07 — La regla de selección por campaña se commitea con guardia sha256

**Qué:** la regla se escribe en el fragmento de la Fase 3 entre marcadores `<!-- regla:inicio -->` y `<!-- regla:fin -->` y se commitea con guardia sha256 antes de calcular las shortlists, igual que la regla de grilla de F2 (`rule_digest`, `rule_guard` en `analysis/som_select.py`). El script de campañas se niega a correr si la regla cambió o no está commiteada. Antes del commit, un checkpoint de decisión en el que el usuario aprueba el texto.

**Por qué:** es de una sola vía: una vez vistas las shortlists, cambiar la regla invalida la afirmación "fijada de antemano".

**Dónde:** [03-CONTEXT.md](.planning/phases/03-oja-y-decisiones-de-campa-a/03-CONTEXT.md) · [fragmento 03 §4](deliverables/03-oja-campanas.md)

### F3 D-08 — Selección por filtro de tema más ranking

**Qué:** entra el creador cuyo tema dominante (argmax de los 4 `topic_*_pct` crudos de `datos/creadores.csv`) es el de la campaña, la misma etiqueta del biplot y de F2. El ranking usa un criterio por campaña (F3 D-10 y D-11). No hay score ponderado general ni Oja restringido por campaña.

**Por qué:** una regla simple, defendible y sin pesos arbitrarios que ajustar.

**Dónde:** [03-CONTEXT.md](.planning/phases/03-oja-y-decisiones-de-campa-a/03-CONTEXT.md) · [fragmento 03 §4](deliverables/03-oja-campanas.md)

### F3 D-09 — k = 5 por campaña y por lista

**Qué:** cada lista tiene 5 creadores, igual para la estrategia propia y para las de `followers`. Si un filtro deja menos de 5, se informan los que haya (la regla lo dice de antemano).

**Por qué:** el mismo k en todas las listas hace comparables los overlaps y los costos.

**Dónde:** [03-CONTEXT.md](.planning/phases/03-oja-y-decisiones-de-campa-a/03-CONTEXT.md) · [fragmento 03 §4](deliverables/03-oja-campanas.md)

### F3 D-10 — Fútbol: tres listas y una recomendación

**Qué:** una shortlist de 5 por objetivo: alcance masivo (`estimated_argentina_reach`), descubrimiento (`non_follower_reach_pct`, con `trend_posts_pct` como apoyo) y profundidad educativa (`content_tutorial_pct`, `saves_per_1000`, `average_watch_time_seconds`). Después, una recomendación escrita de qué objetivo conviene al cliente (ropa de entrenamiento de fútbol), con los supuestos explícitos.

**Por qué:** el enunciado pide contrastar alcance, descubrimiento y profundidad, y el cliente de fútbol es donde esos tres objetivos compiten.

**Dónde:** [03-CONTEXT.md](.planning/phases/03-oja-y-decisiones-de-campa-a/03-CONTEXT.md) · [fragmento 03 §4 y §5.1](deliverables/03-oja-campanas.md)

### F3 D-11 — Perros, maquillaje y arte: un objetivo por cliente

**Qué:** el objetivo de cada cliente se escribe como supuesto en la regla. Perros (refugios, poco presupuesto, alcance local): menor costo por mil argentinos alcanzados (`price_usd / estimated_argentina_reach · 1000`). Maquillaje (marca de belleza): profundidad (saves, tutorial, watch time). Arte (materiales de arte, nicho): engagement por 1000 más profundidad. Las combinaciones de varias variables se aprobaron en el checkpoint de F3 D-07.

**Por qué:** cada cliente necesita audiencia y contenido distintos, y el enunciado permite asumir supuestos sobre las features.

**Dónde:** [03-CONTEXT.md](.planning/phases/03-oja-y-decisiones-de-campa-a/03-CONTEXT.md) · [fragmento 03 §4, §5.2, §5.3 y §5.4](deliverables/03-oja-campanas.md)

### F3 D-12 — El precio no entra a la regla como tope

**Qué:** se reporta el costo total del top-5 y el costo por mil argentinos de cada lista, pero el precio no actúa como tope.

**Por qué:** el enunciado no da presupuestos.

**Dónde:** [03-CONTEXT.md](.planning/phases/03-oja-y-decisiones-de-campa-a/03-CONTEXT.md) · [fragmento 03 §4 y §5](deliverables/03-oja-campanas.md)

### F3 D-13 — Desempate: índice de Oja, después `creator_id`

**Qué:** si hay un empate exacto en el criterio de ranking, desempata el índice de Oja con el signo de F3 D-02 y, después, `creator_id`. Oja y PCA no filtran ni ordenan fuera de ese desempate.

**Por qué:** un desempate determinista y escrito de antemano, sin que Oja o PCA se vuelvan criterio de selección.

**Dónde:** [03-CONTEXT.md](.planning/phases/03-oja-y-decisiones-de-campa-a/03-CONTEXT.md) · [fragmento 03 §4 y §5](deliverables/03-oja-campanas.md)

### F3 D-14 — El SOM es solo descriptivo en las campañas

**Qué:** se indica en qué neurona (fila, col) cae cada elegido y se puede marcar en el mapa de hits, pero la neurona no cambia la selección ni impone diversificación.

**Por qué:** es coherente con F2: la regla de regiones dio una sola región (R1 = 50) y no se inventan regiones.

**Dónde:** [03-CONTEXT.md](.planning/phases/03-oja-y-decisiones-de-campa-a/03-CONTEXT.md) · [fragmento 03 §4 y §5](deliverables/03-oja-campanas.md)

### F3 D-15 — Oja y PCA dan la lectura, no el criterio

**Qué:** se reporta el índice de Oja de cada elegido para mostrar que la shortlist no coincide con el top del índice, y PC1 y PC2 ubican cada lista en el biplot (escala frente a nicho; audiencia argentina).

**Por qué:** así se cumple "justificada con Kohonen, Oja y PCA" (CAMP-01) sin que ninguno de los tres sea el criterio de selección.

**Dónde:** [03-CONTEXT.md](.planning/phases/03-oja-y-decisiones-de-campa-a/03-CONTEXT.md) · [fragmento 03 §4 y §5.6](deliverables/03-oja-campanas.md)

### F3 D-16 — Dos baselines por `followers`

**Qué:** ambos con k = 5: (a) el top-5 global por `followers`, la estrategia ingenua del enunciado, y (b) el top-5 por `followers` dentro del mismo filtro de tema, para aislar el efecto del criterio de ranking.

**Por qué:** evita la comparación de hombre de paja (Pitfall 10).

**Dónde:** [03-CONTEXT.md](.planning/phases/03-oja-y-decisiones-de-campa-a/03-CONTEXT.md) · [fragmento 03 §4 y §5.5](deliverables/03-oja-campanas.md)

### F3 D-17 — Métricas de la comparación y ventajas de `followers`

**Qué:** por campaña y por lista: overlap@5 contra cada baseline, proporción del tema de la campaña, alcance argentino total, costo total, costo por mil argentinos y la métrica objetivo de la campaña. Se listan también las ventajas de `followers` (simple, estable, sin modelo que mantener, correlacionado con alcance). No hay afirmaciones de ROI, ventas ni conversión, y se dice explícitamente que sin datos de resultado no se pueden hacer.

**Por qué:** una comparación honesta con la alternativa simple, sin sobreafirmar con 50 puntos y sin datos de resultado.

**Dónde:** [03-CONTEXT.md](.planning/phases/03-oja-y-decisiones-de-campa-a/03-CONTEXT.md) · [fragmento 03 §4 y §5.5](deliverables/03-oja-campanas.md)

### F3 D-18 — Mantenimiento: respuestas escritas y concretas

**Qué:** campaña nueva: no se re-entrena, es una regla nueva sobre el mismo filtro más ranking. Creadores nuevos: se estandarizan con el scaler guardado, se les asigna BMU e índice, y se re-entrena si su distancia a la BMU supera la distribución del QE de entrenamiento. Variables nuevas: se rehace la auditoría, se re-estandariza y se re-entrena desde cero porque cambia la dimensión. Actualización mensual: seed fija, scaler y codebook versionados, perfiles rotulados por contenido y no por posición, y la convención de signo de F3 D-02 para Oja.

**Por qué:** el enunciado pregunta cómo se mantiene el sistema; las respuestas se apoyan en el scaler guardado (F1 D-11) y en la convención de signo.

**Dónde:** [03-CONTEXT.md](.planning/phases/03-oja-y-decisiones-de-campa-a/03-CONTEXT.md) · [fragmento 03 §6](deliverables/03-oja-campanas.md)

### F3 D-19 — Demo chica con un creador nuevo sintético

**Qué:** un creador nuevo sintético, marcado como tal, se mapea con `scripts/map_creator.py` y el `.meta.json`; se le asigna BMU en el SOM de F2 (k = 5, `k5-step`, seed de las figuras) e índice de Oja con el w guardado, y su distancia a la BMU se compara contra la distribución del QE de entrenamiento como chequeo de drift. No hay simulación completa de un "mes nuevo".

**Por qué:** mostrar que el procedimiento de mantenimiento de F3 D-18 funciona sin ampliar el alcance.

**Dónde:** [03-CONTEXT.md](.planning/phases/03-oja-y-decisiones-de-campa-a/03-CONTEXT.md) · [fragmento 03 §6](deliverables/03-oja-campanas.md)

## Fase 4 — Hopfield: núcleo y letras

### F4 D-01 — Abecedario propio de 26 letras de 5×5 en un archivo versionado

**Qué:** se dibuja un abecedario completo de 26 letras (A-Z) de 5×5 en un archivo de texto legible (por ejemplo `datos/letters/alphabet_5x5.txt`; una letra por bloque, filas con `*` = +1 y `.` = −1, en orden row-major). Un script de Python lo convierte a una matriz ±1 (una fila por letra, 25 columnas) que lee el binario de C. La J del enunciado (`docs/Archivo SIATP 42026.pdf`, §2.2) se transcribe tal cual y un pytest verifica que la codificación coincide con la del enunciado (Pitfall 14).

**Por qué:** los solapamientos, la regla de selección de F4 D-03, el barrido de capacidad y las figuras dependen de estos bitmaps; una vez commiteada la regla, cambiar un bitmap obliga a rehacerla (costosa de revertir).

**Dónde:** [04-CONTEXT.md](.planning/phases/04-hopfield-n-cleo-y-letras/04-CONTEXT.md) · [fragmento 04 §2 y §3](deliverables/04-hopfield-letras.md)

### F4 D-02 — El conversor valida el alfabeto

**Qué:** el conversor valida que haya 26 letras, que cada una tenga exactamente 5 filas de 5 caracteres en `{*, .}` y que no haya dos letras idénticas. Falla con un error claro si algo no se cumple.

**Por qué:** que un bitmap mal tipeado no llegue a la red sin avisar.

**Dónde:** [04-CONTEXT.md](.planning/phases/04-hopfield-n-cleo-y-letras/04-CONTEXT.md) · [fragmento 04 §2 y §3](deliverables/04-hopfield-letras.md)

### F4 D-03 — Dos sets de 4 letras lado a lado: separado y correlacionado

**Qué:** se muestran el set separado (el subconjunto de 4 del alfabeto con menor max |solapamiento| fuera de la diagonal, con solapamiento = ξ^a·ξ^b / N) y el set correlacionado (el de mayor max |solapamiento|), que se espera que falle y sirve para explicar el término de cruce. Las dos reglas, con desempate escrito, se evalúan sobre los C(26, 4) = 14 950 subconjuntos y dependen solo de los bitmaps, no de la red. El set separado es el set principal de la demo de recuperación y del estado espurio. Con N impar no existe ortogonalidad exacta (Pitfall 14b): se habla de "|solapamiento| chico".

**Por qué:** mostrar con evidencia la diferencia entre letras casi ortogonales y letras correlacionadas, sin elegir las letras para que la demo salga bien.

**Dónde:** [04-CONTEXT.md](.planning/phases/04-hopfield-n-cleo-y-letras/04-CONTEXT.md) · [fragmento 04 §2 y §3](deliverables/04-hopfield-letras.md)

### F4 D-04 — La regla de las letras se fija y se commitea antes de correr Hopfield

**Qué:** el texto de la regla va en el fragmento de la fase entre marcadores `<!-- regla:inicio -->` y `<!-- regla:fin -->`, y la guardia sha256 más el commit (reusando `rule_digest` y `rule_guard` de `analysis/som_select.py`) impiden que el script de letras corra si la regla cambió o no está commiteada. Antes del commit hay un checkpoint de decisión en el que el usuario aprueba el texto. El digest incluye el archivo del alfabeto, para que tampoco se puedan retocar los bitmaps después de ver resultados.

**Por qué:** es el mismo patrón de rigor de F2 (D-10 y D-14) y F3 (D-07); de una sola vía: una vez vistos los resultados, cambiar la regla o los bitmaps invalida la afirmación "elegido de antemano".

**Dónde:** [04-CONTEXT.md](.planning/phases/04-hopfield-n-cleo-y-letras/04-CONTEXT.md) · [fragmento 04 §2 y §3](deliverables/04-hopfield-letras.md)

### F4 D-04b — El abecedario borrador se descarta y los desempates se fijan por principio

**Qué:** agregada en la planificación (2026-10-23). La investigación dibujó un abecedario borrador y corrió la red sobre él, así que ese borrador queda descartado como abecedario pre-registrado. En el checkpoint de la regla se dibuja un abecedario nuevo, sin ejecutar ningún código de red sobre él, y el usuario lo aprueba glifo por glifo. Los desempates se fijan por principio, no por resultado: el set separado minimiza max |d| y desempata por menor suma de |d|; el set correlacionado maximiza max |d| y desempata por mayor suma de |d| (simétrico). Todo se compara con productos punto enteros. Ningún número de la red sobre el abecedario nuevo se calcula ni se muestra antes del commit de la regla.

**Por qué:** el borrador ya había visto a la red, lo que rompería la afirmación de pre-registro; es de una sola vía por la misma razón que F4 D-04.

**Dónde:** [04-CONTEXT.md](.planning/phases/04-hopfield-n-cleo-y-letras/04-CONTEXT.md) · [fragmento 04 §2 y §3](deliverables/04-hopfield-letras.md)

### F4 D-05 — Capacidad: exhaustiva para p = 4, muestreada para p = 1 a 8

**Qué:** los 14 950 subconjuntos de 4 letras se almacenan (Hebb, W entera) y para cada uno se mide la fracción de patrones que son puntos fijos estables (y, a un nivel de ruido fijo, la tasa de recuperación), graficada contra el max |solapamiento|. Para p = 1 a 8 (confirmado por el usuario en la planificación; si la estabilidad no cae a cerca de 0 en p = 8, se extiende con una regla escrita en la regla de F4 D-04, no a mano) se toma una muestra al azar con seed de subconjuntos por p y se grafica la fracción estable contra p, marcando 0,138N ≈ 3,45 solo como orden de magnitud (Pitfall 26), nunca como umbral.

**Por qué:** a N = 25 el comportamiento depende de qué letras se eligen, así que la capacidad se mide y no se deduce de 0,138N.

**Dónde:** [04-CONTEXT.md](.planning/phases/04-hopfield-n-cleo-y-letras/04-CONTEXT.md) · [fragmento 04 §3 y §6](deliverables/04-hopfield-letras.md)

### F4 D-06 — Matriz de solapamientos y término de cruce de los dos sets

**Qué:** la matriz de solapamientos de 4×4 y el término de cruce de cada patrón se reportan para los dos sets de F4 D-03, y además un histograma de max |solapamiento| sobre los 14 950 sets de 4 ubica a ambos dentro de la distribución.

**Por qué:** explicar la diferencia de comportamiento entre los dos sets a través del término de cruce y mostrar qué tan extremos son dentro de todos los posibles.

**Dónde:** [04-CONTEXT.md](.planning/phases/04-hopfield-n-cleo-y-letras/04-CONTEXT.md) · [fragmento 04 §3 y §4](deliverables/04-hopfield-letras.md)
## Fase 5 — Hopfield: QR

### F5 D-01 — Se pre-registra el protocolo del experimento, con guardia sha256

**Qué:** a diferencia de la Fase 4, acá los 5 QR son fijos y dados: no hay selección. Lo que se pre-registra y se commitea con guardia sha256 antes de correr la red es el protocolo del experimento, entre marcadores `<!-- regla:inicio -->` y `<!-- regla:fin -->` en `deliverables/05-hopfield-qr.md`: criterio de éxito, niveles de ruido, número de ensayos, seeds, métricas reportadas y la hipótesis literal ("Hebb no estabiliza los 5 QR correlacionados; la pseudo-inversa es el remedio"). La guardia incluye el hash de los 5 PNG (reusando `rule_digest` y `rule_guard` de `analysis/som_select.py`).

**Por qué:** que ni el protocolo ni las imágenes se puedan retocar después de ver resultados; de una sola vía: cambiarlos invalida la afirmación "fijado de antemano".

**Dónde:** [05-CONTEXT.md](.planning/phases/05-hopfield-con-qr/05-CONTEXT.md) · [fragmento 05 §3 y §7](deliverables/05-hopfield-qr.md)

### F5 D-02 — Umbrales de veredicto numéricos explícitos

**Qué:** el protocolo incluye umbrales numéricos de qué cuenta como "Hebb falló" y "pinv funciona" (por ejemplo, "Hebb falla si la recuperación exacta a ruido 0 es menor que 100 %"), fijados antes de correr.

**Por qué:** que el veredicto no se ajuste después de ver la curva; de una sola vía por la misma razón que F5 D-01.

**Dónde:** [05-CONTEXT.md](.planning/phases/05-hopfield-con-qr/05-CONTEXT.md) · [fragmento 05 §1, §3, §4, §5 y §6](deliverables/05-hopfield-qr.md)

### F5 D-03 — Éxito = match exacto de los 1369 píxeles, más la curva continua de |m|

**Qué:** el criterio de éxito es el match exacto de los 1369 píxeles (|m| = 1 con el objetivo) como veredicto binario, y además se reporta la curva continua del solapamiento final |m| promedio por nivel de ruido. Este criterio entra en el protocolo de F5 D-01.

**Por qué:** ver qué tan cerca queda Hebb aunque nunca acierte exacto.

**Dónde:** [05-CONTEXT.md](.planning/phases/05-hopfield-con-qr/05-CONTEXT.md) · [fragmento 05 §3](deliverables/05-hopfield-qr.md)

### F5 D-04 — El ruido es solo flips i.i.d. de píxeles

**Qué:** la corrupción es solo flips i.i.d. de píxeles (una familia de ruido), como pide HOP-05. El daño estructurado (oclusión de bloque, rayón, manchas) no se corre como experimento; se puede nombrar como limitación o idea diferida, pero no genera figuras.

**Por qué:** cumplir HOP-05 al pie de la letra sin ampliar el alcance. Es reversible.

**Dónde:** [05-CONTEXT.md](.planning/phases/05-hopfield-con-qr/05-CONTEXT.md) · [fragmento 05 §3 y §6](deliverables/05-hopfield-qr.md)

### F5 D-05 — 11 niveles de ruido, 30 ensayos por nivel, 10 seeds

**Qué:** 11 niveles de 0 a 0,5 en pasos de 0,05 (el nivel 0 es la estabilidad a ruido cero de HOP-05), 30 ensayos por nivel y 10 seeds, consistente con F2 D-08, F3 y F4. Las tres reglas (Hebb, pinv, Hamming) se evalúan en esta misma grilla.

**Por qué:** supera cómodo el piso de HOP-05 (al menos 8 niveles por 30 ensayos) y hace comparables las tres reglas.

**Dónde:** [05-CONTEXT.md](.planning/phases/05-hopfield-con-qr/05-CONTEXT.md) · [fragmento 05 §3](deliverables/05-hopfield-qr.md)

### F5 D-06 — Pseudo-inversa implementada en C, despachada por `rule = "pinv"`

**Qué:** la regla de pseudo-inversa `W = Xᵀ(X Xᵀ)⁻¹ X` se implementa en C, despachada por la clave `rule = "pinv"` que la Fase 4 ya dejó prevista en `HOPFIELD_KEYS`. Requiere invertir la matriz de Gram de 5×5 (X Xᵀ). La dinámica, la energía y la clasificación del estado final reusan sin cambios el código del núcleo.

**Por qué:** mover la construcción de W a Python más tarde partiría el cómputo del modelo entre dos lenguajes (costosa de revertir).

**Dónde:** [05-CONTEXT.md](.planning/phases/05-hopfield-con-qr/05-CONTEXT.md) · [fragmento 05 §1](deliverables/05-hopfield-qr.md)

### F5 D-07 — En la pinv la diagonal de W no se anula

**Qué:** se deja la diagonal de W no nula (pseudo-inversa pura, regla de proyección), a diferencia de Hebb.

**Por qué:** es la propiedad que garantiza que los 5 QR sean puntos fijos exactos, que es justo el remedio que se quiere mostrar frente al fallo de Hebb.

**Dónde:** [05-CONTEXT.md](.planning/phases/05-hopfield-con-qr/05-CONTEXT.md) · [fragmento 05 §1 y §3](deliverables/05-hopfield-qr.md)

### F5 D-08 — Línea base de Hamming: vecino más cercano sin dinámica

**Qué:** un clasificador 1-NN sin dinámica: toma la consulta ruidosa y devuelve el QR almacenado de menor distancia de Hamming. Se grafica su tasa de acierto superpuesta con Hebb y pinv en la misma grilla de F5 D-05, más una tabla de recuperación exacta por nivel.

**Por qué:** demuestra que un lookup trivial ya resuelve el problema, insumo de la limitación de F5 D-11.

**Dónde:** [05-CONTEXT.md](.planning/phases/05-hopfield-con-qr/05-CONTEXT.md) · [fragmento 05 §3, §5 y §6](deliverables/05-hopfield-qr.md)

### F5 D-09 — Para Hebb y pinv, energía final e iteraciones por nivel de ruido

**Qué:** además de la tasa de acierto, se reportan la energía final y las iteraciones (barridos) por nivel de ruido, para Hebb y pinv.

**Por qué:** contrastar el costo dinámico de la red contra el lookup instantáneo de Hamming.

**Dónde:** [05-CONTEXT.md](.planning/phases/05-hopfield-con-qr/05-CONTEXT.md) · [fragmento 05 §3 y §5](deliverables/05-hopfield-qr.md)

### F5 D-10 — No se corre un decodificador de QR

**Qué:** no se corre un decodificador (pyzbar u OpenCV) sobre las imágenes recuperadas. La limitación de la corrección de errores propia del QR (Reed-Solomon L/M/Q/H, aproximadamente 7/15/25/30 %) y de que un recuperado pixel-exacto podría igual no decodificar se argumenta en texto, declarando explícitamente que la decodificación no se verificó.

**Por qué:** evita una dependencia nueva y un spike; alineado con el blocker de STATE ("decodificador de QR sin verificar, HOP-09 en v2"). Es reversible: agregar el decodificador después es aditivo.

**Dónde:** [05-CONTEXT.md](.planning/phases/05-hopfield-con-qr/05-CONTEXT.md) · [fragmento 05 §3 y §6](deliverables/05-hopfield-qr.md)

### F5 D-11 — Limitaciones del caso de uso demostradas empíricamente (sub-ítems D-11a a D-11d)

**Qué:** se demuestran con figura o número, además del texto: **D-11a**, correlación entre QR (matriz de solapamientos 5×5, fracción de píxeles idénticos en los 5 y distancia mínima de Hamming entre pares, causa raíz del fallo de Hebb); **D-11b**, sensibilidad a corrimientos (mover un QR 1 o 2 píxeles y mostrar que la recuperación pixel-wise se rompe, en un tríptico antes, desplazado y recuperado); **D-11c**, equivalencia con lookup (cubierta por la curva de Hamming de F5 D-08). El cuarto punto, **D-11d**, la corrección de errores propia del QR, queda solo en texto (F5 D-10); el `CONTEXT.md` lo menciona al cerrar la decisión sin ponerle letra, y acá se lo nombra así para completar la lista. El fragmento cita `D-11a`; el glosario enlaza un ID con letra que no tiene entrada propia a esta entrada madre.

**Por qué:** que las limitaciones se apoyen en números medidos sobre los datos reales y no solo en argumentos.

**Dónde:** [05-CONTEXT.md](.planning/phases/05-hopfield-con-qr/05-CONTEXT.md) · [fragmento 05 §2, §3, §5 y §6](deliverables/05-hopfield-qr.md)
## Fase 6 — Slides e informe

### F6 D-01 — Presentación de unos 20 minutos, 20-25 slides

**Qué:** unos 20 minutos y 20 a 25 slides. Reparto aproximado: Ejercicio 1 (EDA y PCA, Kohonen, Oja, campañas) unas 12 a 14 slides; Ejercicio 2 (letras, QR) unas 7 a 9. Una idea por slide.

**Por qué:** es lo que entra en la exposición oral con una idea por slide.

**Dónde:** [06-CONTEXT.md](.planning/phases/06-slides-e-informe/06-CONTEXT.md)

### F6 D-02 — Orden por método, con título-conclusión

**Qué:** el orden es por método (PCA, SOM, Oja, campañas, letras, QR) y cada slide tiene un título-conclusión: el título dice la conclusión, no el tema («El mapa sigue a PC1 pero no a PC2», no «Matriz U»). La pregunta del enunciado que responde la slide puede ir en chico, pero no ordena el guion.

**Por qué:** el guion sigue el hilo de los métodos y cada slide se entiende leyendo solo el título.

**Dónde:** [06-CONTEXT.md](.planning/phases/06-slides-e-informe/06-CONTEXT.md)

### F6 D-03 — El rigor metodológico: una slide de método y menciones cortas

**Qué:** el rigor entra como una slide de método al principio (reglas fijadas y commiteadas antes de ver resultados con guardia sha256, 10 seeds, nulos por permutación) y después menciones cortas en cada resultado (por ejemplo «regla fijada de antemano»). El detalle de cada regla queda en el informe.

**Por qué:** mostrar el rigor sin cargar cada slide con la metodología.

**Dónde:** [06-CONTEXT.md](.planning/phases/06-slides-e-informe/06-CONTEXT.md)

### F6 D-04 — Los resultados poco favorables van de frente

**Qué:** los resultados poco favorables tienen slide propia con título-conclusión y una línea del porqué: una sola región en el SOM (R1 = 50) con la regla fijada, etapa 2 «no robusta», Hebb con 0 % de recuperación exacta en los QR (solapamiento medio 0,67) y el lookup de Hamming 1-NN que iguala o supera a la pseudo-inversa con ruido alto.

**Por qué:** es coherente con la Key Decision de PROJECT.md (ver KD-4) de reportar el resultado de la regla tal cual.

**Dónde:** [06-CONTEXT.md](.planning/phases/06-slides-e-informe/06-CONTEXT.md)

### F6 D-05 — Campañas en unas 4 slides

**Qué:** fútbol aparte (alcance masivo, descubrimiento, profundidad educativa y la recomendación); una tabla resumen para perros, maquillaje y arte (criterio, top-5, costo por mil argentinos); una slide de comparación contra solo `followers`; y una de mantenimiento.

**Por qué:** fútbol es el único cliente con tres objetivos en competencia; los otros tres caben en una tabla.

**Dónde:** [06-CONTEXT.md](.planning/phases/06-slides-e-informe/06-CONTEXT.md)

### F6 D-06 — Notas del orador en cada slide

**Qué:** cada slide lleva notas del orador: 2 a 4 frases de qué decir y los números clave para responder preguntas. El cuerpo visible queda limpio. Si el formato Slides no soporta notas, el planner propone el equivalente más cercano y lo informa.

**Por qué:** el cuerpo limpio facilita la lectura y las notas respaldan al orador. La sonda del formato Slides ([06-ARTIFACT-FORMAT.md](.planning/phases/06-slides-e-informe/06-ARTIFACT-FORMAT.md)) encontró que el tipo soporta notas, en un `<aside>` por slide, pero que no son privadas del orador: las puede leer cualquiera que abra el deck.

**Dónde:** [06-CONTEXT.md](.planning/phases/06-slides-e-informe/06-CONTEXT.md) · [06-ARTIFACT-FORMAT.md](.planning/phases/06-slides-e-informe/06-ARTIFACT-FORMAT.md)

### F6 D-07 — Apertura con portada y slide de método; cada ejercicio cierra con sus conclusiones

**Qué:** la apertura es la portada (TP4 SIA, Grupo 9) y la slide de método (F6 D-03). Cada ejercicio cierra con su propia slide de conclusiones: el Ejercicio 1 dice qué aporta cada método a la decisión de campaña y el Ejercicio 2 dice qué limitaciones tiene Hopfield para los QR. No hay agenda ni cierre general.

**Por qué:** cada ejercicio queda como una unidad que se entiende por sí sola.

**Dónde:** [06-CONTEXT.md](.planning/phases/06-slides-e-informe/06-CONTEXT.md)

### F6 D-08 — Figuras de slides: variante «slide» del mismo código matplotlib

**Qué:** las figuras de las slides son una variante «slide» del mismo código matplotlib que dibuja las del informe: la misma función de datos con otro estilo (letra más grande, menos anotaciones, proporción 16:9). Los datos se calculan una vez y se dibujan dos. No se pintan gráficos a mano en HTML como en TP3.

**Por qué:** una sola fuente de verdad para los números de slides e informe. Es costosa de revertir: si después se cambia el renderer de las slides, hay que rehacer cada figura de slide.

**Dónde:** [06-CONTEXT.md](.planning/phases/06-slides-e-informe/06-CONTEXT.md) · [06-ARTIFACT-FORMAT.md](.planning/phases/06-slides-e-informe/06-ARTIFACT-FORMAT.md)

### F6 D-09 — El informe es todo estático

**Qué:** se usan los SVG de matplotlib existentes, inline. El informe no lleva plotly, JS de gráficos ni CDN para las figuras.

**Por qué:** una página autocontenida y estable al publicarse como Artifact.

**Dónde:** [06-CONTEXT.md](.planning/phases/06-slides-e-informe/06-CONTEXT.md)

### F6 D-10 — Cada figura va sobre un panel claro

**Qué:** cada figura va siempre sobre un panel claro (tarjeta con el fondo `SURFACE` de `analysis/plots_style.py` y borde), también en modo oscuro. La página alrededor sí cambia de tema. Hay una sola versión de cada figura y no se generan variantes oscuras.

**Por qué:** los QR, las letras y la matriz U se leen igual en los dos temas.

**Dónde:** [06-CONTEXT.md](.planning/phases/06-slides-e-informe/06-CONTEXT.md)

### F6 D-11 — Armado por script y `make`; los números se leen de los JSON y CSV

**Qué:** un target (por ejemplo `make deliverables`, o `make slides` más `make informe`) regenera los resultados que faltan, dibuja las figuras de informe y de slide y escribe el HTML del informe y los archivos de datos de las slides, listos para publicar. Los números del texto se leen de los JSON y CSV de `analysis/results/` y no se tipean a mano. La publicación de los Artifacts es manual (un paso aparte que se documenta).

**Por qué:** que el texto no diverja de los resultados. Es costosa de revertir: el texto de slides e informe pasa a depender de las claves de los JSON de cada fase.

**Dónde:** [06-CONTEXT.md](.planning/phases/06-slides-e-informe/06-CONTEXT.md)

### F6 D-12 — Informe híbrido: parte generada más los fragmentos como detalle técnico

**Qué:** una parte inicial generada (resumen «Qué encontramos», tabla pregunta a sección de DELIV-02, bloque «Cómo trabajamos») con los números leídos de los JSON vía un loader de facts, seguida de los cinco fragmentos `deliverables/0X-*.md` convertidos a HTML como «Detalle técnico (Fase N)». Un test de drift fija unos 25 números clave de los fragmentos contra los JSON. Los fragmentos no se editan (están bajo guardia sha256); todo cambio de texto se hace al renderizar.

**Por qué:** que el informe no diverja de los fragmentos ni de los números. Es costosa de revertir: pasar a síntesis pura obligaría a reescribir y revisar a mano todo el texto.

**Dónde:** [06-CONTEXT.md](.planning/phases/06-slides-e-informe/06-CONTEXT.md)

### F6 D-13 — La jerga interna se enlaza al renderizar a un glosario generado desde este archivo

**Qué:** la jerga de los fragmentos (`D-NN`, `Pitfall N`, IDs de requisito como `HOP-04`) se enlaza al renderizar a un anexo de glosario generado desde `DECISIONS.md`. Los fragmentos quedan intactos.

**Por qué:** que quien lee el informe pueda seguir cada sigla sin tocar los fragmentos. Por eso la gramática de los títulos de este archivo es un contrato.

**Dónde:** [06-CONTEXT.md](.planning/phases/06-slides-e-informe/06-CONTEXT.md)

### F6 D-14 — Las slides se publican como Artifact y se entregan como su PDF exportado, fuera del repo

**Qué:** el deck se publica como Artifact tipo Slides, privado, y al docente se le entrega el PDF que exporta ese Artifact. El PDF no se versiona, ni en `docs/` ni en `deliverables/`: después de republicar el deck se vuelve a exportar.

**Por qué:** la planificación de la fase (2026-10-25) registró "solo como Artifact". Al sondear el formato, el usuario respondió que al docente se le entrega el PDF exportado del deck (ver [06-ARTIFACT-FORMAT.md](.planning/phases/06-slides-e-informe/06-ARTIFACT-FORMAT.md), `share_mode`), y ese documento proponía agregarlo bajo `deliverables/`. Al final no se versionó: es una exportación del Artifact, que a su vez sale de `make deliverables`, y una copia en el repo podría quedar desactualizada respecto del deck publicado sin que nada lo detecte. `test_repro_docs.py` impide que aparezca una exportación de slides en `docs/`.

**Dónde:** [06-CONTEXT.md](.planning/phases/06-slides-e-informe/06-CONTEXT.md) · [06-ARTIFACT-FORMAT.md](.planning/phases/06-slides-e-informe/06-ARTIFACT-FORMAT.md)

### F6 D-15 — El informe llega al docente como link compartido del Artifact

**Qué:** el informe llega al docente como link compartido del Artifact (HTML). No hace falta exportar PDF o Word del informe; el tipo Docs no se usa. Compartir el link es un paso manual del checkpoint de publicación.

**Por qué:** decisión de entrega registrada en la planificación de la fase (2026-10-25).

**Dónde:** [06-CONTEXT.md](.planning/phases/06-slides-e-informe/06-CONTEXT.md)
## Pitfalls citados en los fragmentos

Los títulos completos y el análisis de cada trampa están en `.planning/research/PITFALLS.md`. Acá figuran solo los que citan los fragmentos.

### Pitfall 1 — Hopfield con Hebb sobre los 5 QR no funciona y la regla de capacidad lo esconde

**Qué:** con la regla de Hebb estándar, los 5 QR no son ni siquiera puntos fijos de la red: una consulta sin ruido ya cambia. La regla 0,138N ("5/1369, muy por debajo del límite") se deriva para patrones aleatorios independientes y no dice nada de patrones correlacionados.

**Por qué:** el proyecto hizo de la estabilidad a ruido cero el primer test de cada corrida, reportó el fallo de Hebb como hallazgo (no como error), midió la causa raíz (solapamientos de 0,58 a 0,86; 69,8 % de píxeles idénticos en los 5 QR) y mostró la pseudo-inversa como segundo experimento claramente rotulado.

**Dónde:** [fragmento 05 §3, §5](deliverables/05-hopfield-qr.md) · [05-CONTEXT.md](.planning/phases/05-hopfield-con-qr/05-CONTEXT.md) (F5 D-01, D-02, D-06, D-07)

### Pitfall 8 — Oja sin centrar, con tasa inestable y sin normalizar los pesos finales

**Qué:** tres fallas medidas: correr Oja sobre datos sin centrar converge a la dirección de la media y no a PC1; una tasa de aprendizaje grande diverge; y el signo y la norma de w son arbitrarios (w y −w son igualmente estables), así que "el índice más alto" no tiene sentido sin una orientación declarada.

**Por qué:** el proyecto usa la misma matriz z-scored que la PCA, η chico y decreciente con épocas barajadas, renormaliza w a norma 1, valida contra `eigh` (|cos(w, v1)| > 0,99) y fija la convención de signo de antemano.

**Dónde:** [fragmento 03 §1](deliverables/03-oja-campanas.md) · [03-CONTEXT.md](.planning/phases/03-oja-y-decisiones-de-campa-a/03-CONTEXT.md) (F3 D-01, D-02, D-05)

### Pitfall 14 — Letras 5×5: conclusiones erróneas sobre capacidad y ortogonalidad

**Qué:** usar 0,138N = 3,45 como umbral duro con N = 25, buscar ortogonalidad exacta (imposible con N impar, el producto punto es siempre impar) o elegir las letras que hacen lucir la demo sin decirlo.

**Por qué:** el proyecto muestra la matriz de solapamientos y el término de cruce, hace un experimento de capacidad exhaustivo para p = 4 y muestreado para p = 1 a 8, y compara lado a lado un set separado y uno correlacionado elegidos por una regla fijada antes de correr la red.

**Dónde:** [fragmento 04 §3](deliverables/04-hopfield-letras.md) · [04-CONTEXT.md](.planning/phases/04-hopfield-n-cleo-y-letras/04-CONTEXT.md) (F4 D-01, D-03, D-04, D-05)

### Pitfall 15 — La respuesta sobre las limitaciones del caso de uso omite las reales

**Qué:** decir solo "la capacidad es limitada" o "es lento". Las limitaciones defendibles son la correlación entre patrones, la sensibilidad a corrimientos y a imágenes no alineadas, que una tabla de búsqueda por Hamming resuelve lo mismo, la corrección de errores propia del QR (Reed-Solomon), los atractores espurios e inversos y el almacenamiento cuadrático.

**Por qué:** el proyecto agrega la línea base de Hamming 1-NN a la curva de ruido, demuestra con números la correlación y la sensibilidad a corrimientos, y declara que la decodificación de los QR recuperados no se verificó.

**Dónde:** [fragmento 05 §6](deliverables/05-hopfield-qr.md) · [05-CONTEXT.md](.planning/phases/05-hopfield-con-qr/05-CONTEXT.md) (F5 D-08, D-10, D-11)

### Pitfall 22 — Binarización y codificación de los PNG de los QR

**Qué:** umbral equivocado, polaridad equivocada al mostrar, o resampleo de imágenes que ya son 37×37 con valores 0 y 255.

**Por qué:** `scripts/qr.py` verifica la forma 37×37 y que los valores sean 0/255 puros (rechaza grises en lugar de umbralizarlos y no remuestrea), fija la polaridad oscuro = +1 y claro = −1, y un test comprueba que la codificación es exacta píxel a píxel.

**Dónde:** [fragmento 05 §2](deliverables/05-hopfield-qr.md) · [05-CONTEXT.md](.planning/phases/05-hopfield-con-qr/05-CONTEXT.md) (preparación de los PNG, criterio del planner)

### Pitfall 26 — Concluir de 0,138N como si fuera exacto

**Qué:** 0,138N es la carga crítica de la teoría de réplicas para patrones aleatorios y no correlacionados con aprendizaje hebbiano; el límite práctico para recuperación perfecta es menor y la pseudo-inversa sube el techo teórico a N para patrones linealmente independientes. Todos son enunciados asintóticos.

**Por qué:** el proyecto cita 0,138N solo como orden de magnitud y siempre junto con el experimento empírico.

**Dónde:** [fragmento 04 §3](deliverables/04-hopfield-letras.md) · [fragmento 05 §6](deliverables/05-hopfield-qr.md) · [04-CONTEXT.md](.planning/phases/04-hopfield-n-cleo-y-letras/04-CONTEXT.md) (F4 D-05)

## Requisitos citados en los fragmentos

El texto de cada requisito sale de `.planning/REQUIREMENTS.md`.

### DATA-01 — El loader verifica n=50 filas y 33 columnas, y falla si no coinciden

Responde la [sección 1 del fragmento 01](deliverables/01-datos-pca.md) (decisión relacionada: F1 D-07).

### DATA-03 — Z-score en Python con scaler guardado (`.meta.json`) para mapear creadores nuevos

Responde la [sección 4 del fragmento 01](deliverables/01-datos-pca.md) (decisión relacionada: F1 D-11).

### DATA-05 — Corrida de sensibilidad con las 31 columnas, etiquetada, comparada contra el conjunto auditado

Responde las [secciones 4 y 7 del fragmento 01](deliverables/01-datos-pca.md) (decisión relacionada: F1 D-08).

### HOP-03 — Un patrón muy ruidoso que converge a un estado espurio identificado y clasificado (inverso, mezcla u otro)

Responde la [sección 7 del fragmento 04](deliverables/04-hopfield-letras.md); la sección 3 lo cita al fijar el diseño de los experimentos.

### HOP-04 — Preparación de los 5 QR de 37×37 a ±1 con aserción de que son 0/255 puros, y matriz de solapamientos

Responde la [sección 2 del fragmento 05](deliverables/05-hopfield-qr.md) (decisión relacionada: F5 D-11).

### HOP-05 — QR con regla de Hebb: test de estabilidad a ruido cero y al menos 8 niveles de ruido con 30 o más ensayos cada uno, con energía e iteraciones por paso; el fallo se reporta como hallazgo

Responde las [secciones 3 y 4 del fragmento 05](deliverables/05-hopfield-qr.md) (decisiones relacionadas: F5 D-02, D-03, D-05, D-09).

### HOP-06 — Regla de pseudo-inversa para los QR, comparada contra Hebb y contra la línea base de Hamming al patrón más cercano

Responde la [sección 5 del fragmento 05](deliverables/05-hopfield-qr.md) (decisiones relacionadas: F5 D-06, D-07, D-08).

### HOP-07 — Limitaciones del caso de uso explicadas (correlación entre QR, sensibilidad a corrimientos, corrección de errores propia del QR, tabla de búsqueda equivalente)

Responde la [sección 6 del fragmento 05](deliverables/05-hopfield-qr.md) (decisiones relacionadas: F5 D-10, D-11).
