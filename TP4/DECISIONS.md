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

### F1 D-12 — PCA por autovalores con regla de decisión escrita antes del scree

**Qué:** la PCA se hace sobre la matriz de correlación (= covarianza del z-score) por autovalores, verificada con `np.linalg.eigh`. El criterio de 80 % de varianza acumulada fija k; Kaiser (autovalor > 1) funciona como control, y si difieren se reporta la discrepancia.

**Por qué:** la regla se escribió antes de mirar el scree para no elegir k a posteriori.

**Dónde:** [01-CONTEXT.md](.planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-CONTEXT.md) · [fragmento 01 §5](deliverables/01-datos-pca.md)

### F1 D-13 — La PCA es diagnóstica

**Qué:** la PCA justifica por escrito si se podría reducir y cómo leer PC1 y PC2 (biplot), pero Kohonen y Oja corren sobre la matriz z-scored completa del conjunto auditado, como pide el enunciado. No se agrega una corrida del SOM sobre k PCs.

**Por qué:** respetar el enunciado (los métodos usan todas las variables) sin ampliar el alcance de la Fase 2.

**Dónde:** [01-CONTEXT.md](.planning/phases/01-fundaci-n-auditor-a-de-datos-y-pca/01-CONTEXT.md) · [fragmento 01 §5 y §6](deliverables/01-datos-pca.md)

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

