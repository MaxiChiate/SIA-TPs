# Análisis: series de corridas

Corre el mismo binario (`neuron/build/neuron`) varias veces, con varias seeds por variante, y junta una fila
por corrida en un `summary.csv`. Cada corrida es una corrida normal del binario: su carpeta tiene el
`config.json` que la produjo, el `metrics.json` y los CSV del modelo. Todo estudio de hiperparámetros o de seeds
de las fases 2 a 5 pasa por acá.

```sh
python3 analysis/sweep.py analysis/series_smoke_oja.json             # desde TP4/
python3 analysis/sweep.py analysis/series_smoke_oja.json --dry-run   # solo muestra el plan
python3 analysis/sweep.py analysis/series_smoke_oja.json --workers 4 # corridas en paralelo (default: todos los cores)
```

Compila el binario si hace falta (`make -s -C neuron`). `sweep.py` solo usa la biblioteca estándar de Python, así
que corre con el `python3` del sistema, sin `.venv`. `--dry-run` imprime el plan (nombre de la serie, variantes,
seeds y una línea que termina en `= N runs`) y vuelve antes de compilar o crear nada.

## La serie

Un JSON por serie. Las claves que empiezan con `_` se ignoran (sirven de comentario); cualquier otra clave que no
esté en la tabla corta la ejecución con un mensaje que nombra la clave y el archivo.

| Clave         | Descripción |
|---------------|-------------|
| `base_config` | Config de la corrida, relativo al JSON de la serie (p. ej. `../neuron/config.json.oja.example`) |
| `set`         | Opcional. Claves del config que se pisan en todas las corridas |
| `vary` + `values` | La clave que varía y sus valores: una variante por valor |
| `variants`    | En lugar de `vary`: lista de `{"label", "set"}`, para variantes que cambian más de una clave a la vez |
| `seeds`       | Seeds de cada variante; todas las variantes usan las mismas. Sin `seeds`, la del `base_config` |
| `workers`     | Opcional. Corridas en paralelo |

- Sin `vary` ni `variants` la serie tiene una sola variante, `base`, sin cambios: sirve para repetir una config
  con varias seeds.
- Las claves de `set`, de `vary` y de cada `variants[].set` pueden ser con puntos, p. ej. `"noise.fraction"`: se
  crean los objetos intermedios que falten. Cada corrida parte de una copia profunda del config base.
- Las rutas del config (hoy solo `input`) se escriben relativas a `neuron/`, como con `make run`. Como las
  corridas se ejecutan desde la carpeta del sweep, `sweep.py` las reescribe relativas a esa carpeta (nunca
  absolutas), así que ningún archivo de una corrida guarda una ruta absoluta.
- El binario valida el config con rigor: una clave que el modelo no declara hace fallar la corrida.

## Salida

Todo va a `analysis/results/<serie>_<fecha>_<hora>/` (si la carpeta ya existe, se agrega `_2`, `_3`, …). `results/`
no se versiona.

| Archivo | Contenido |
|---------|-----------|
| `series.json` | Copia del JSON de la serie |
| `plan.json` | La serie resuelta: config base, `set`, `vary`, variantes y seeds |
| `configs/` | Un config por corrida, `{NNN}_{variante}_seed{N}.json` |
| `runs/` | Una carpeta por corrida con el mismo nombre (`config.json`, `metrics.json`, CSV del modelo) |
| `summary.csv` | Una fila por corrida, ordenada por nombre de corrida |

Dos sweeps de la misma serie dan `summary.csv` idéntico y `runs/` idéntico (`cmp` y `diff -r`): la fecha solo
está en el nombre de la carpeta del sweep.

## Columnas de `summary.csv`

1. Fijas: `run`, `variant` (índice), `label`, `seed`, `status`.
2. Las claves que varían: cada clave que aparece en los overrides de alguna variante, en orden de aparición.
   Las listas y los objetos van codificados como JSON.
3. Las claves del `metrics.json`: en el orden del `metrics.json` de la primera corrida ok (por nombre), seguidas de
   las claves que solo tienen otras corridas, ordenadas. Una clave que ya es columna (`seed`, `model`) no se repite.

Las celdas sin valor quedan vacías.

## Corridas que fallan

Si el binario sale con código distinto de cero, la fila queda con `status` igual a `error: ` más la última línea de
su stderr (o `error: exit code N` si no escribió nada), las claves que varían y ninguna métrica. Una corrida cuyo
`metrics.json` no existe también cuenta como fallida. Las demás corridas siguen, el `summary.csv` se escribe igual,
la última línea de stdout sigue siendo `summary -> <ruta>` y el comando termina con estado 1.

## Series existentes

| Serie | Qué corre | Pregunta |
|---|---|---|
| `series_smoke_oja` | La regla de Oja (ya no es un stub) sobre los datos auditados (`datos/prepared/creadores_zscore.csv`, 50 x 26; `make prepare` lo genera, no se versiona), 3 seeds | ¿Funciona el lazo config, binario, `summary.csv`? |
| `series_oja` | La regla de Oja con el config de ejemplo (`neuron/config.json.oja.example`: η0 = 0,001, ηf = 0,0001, 500 épocas) y 10 seeds; la seed 1 produce las tablas y las figuras de la Fase 3 | ¿Converge `w` al primer componente de la PCA y con qué dispersión entre seeds? (`make oja`) |
| `series_smoke_kohonen` | El SOM de Kohonen entrenado (vecindad `step`, 260 épocas) sobre los mismos datos, `grid_k` en 2, 3 y 4, 3 seeds (9 corridas). `summary.csv` trae ahora `qe`, `te` y `empty_fraction`, más `occupied_neurons`, `mean_hits_occupied`, `max_hits` y `singleton_neurons` de `metrics.json` | ¿La clave que varía (`grid_k`) y las medidas del mapa quedan como columnas de `summary.csv`? |
| `series_smoke_hopfield` | La red de Hopfield real (Fase 4) sobre `neuron/tests/fixtures/patterns_mix.csv`, variantes `low` (0.0 y 0.12), `high` (0.32 y 0.48) y `sync` (`update` `sync`, 0.24 y 0.4), 2 seeds (6 corridas) | ¿Llega a `summary.csv` una variante que cambia una lista y un string? |
| `series_som_stage1` | La etapa 1 de la regla de elección de grilla del SOM (sección 2 de `deliverables/02-kohonen.md`): 14 variantes (k de 2 a 8, vecindad escalón y gaussiana) x 10 seeds = 140 corridas, sobre los mismos datos auditados | ¿Qué grilla elige la regla fijada de antemano? (`make som-stage1`) |
| `series_som_stage2` | La etapa 2: robustez del schedule (R0, η0 y épocas, 10 variantes) x 10 seeds sobre la k que eligió la etapa 1; la genera `som_stage.py write-stage2` | ¿La k elegida sigue pasando los filtros al mover el schedule? (`make som-stage2`) |

Desde la raíz de TP4 también se corre con `make sweep SERIES=analysis/series_smoke_kohonen.json` (por defecto,
`series_smoke_oja.json`); `make sweep` genera antes `datos/prepared/` si falta.

## SOM (Fase 2)

El mapa de Kohonen se estudia en dos etapas con la regla de elección de grilla commiteada antes de ver resultados
(sección 2 de `deliverables/02-kohonen.md`). Las salidas van a `analysis/results/som/` (no se versiona). Desde la
raíz de TP4:

| Archivo | Qué hace |
|---|---|
| `som.py` | Lee una corrida del binario y calcula lo común: QE, TE, rangos con empates (Spearman), estabilidad entre seeds, adyacencia de la grilla y matriz U |
| `som_loo.py` | QE de leave-one-out de cada variante (reentrena sin un creador y mide el QE de ese creador) |
| `som_select.py` | La regla de elección de grilla como código; su sha256 queda en `selection.json` |
| `som_stage.py` | Maneja las dos etapas y se niega a correr si la regla no está commiteada o cambió |
| `som_figures.py` | Figuras de la grilla elegida: mapa de hits con matriz U, planos de componentes, curvas de la etapa 1 y traza |
| `som_profiles.py` | Regiones de la regla, perfiles en unidades originales, contraste con PC1/PC2 con 1000 permutaciones, lectura de las aristas altas de la matriz U y discrepancias mapa-plano |

| Target | Escribe |
|---|---|
| `make som-stage1` | `analysis/results/som/series_som_stage1/` con `selection.json` (la grilla elegida) |
| `make som-stage2` | `analysis/results/som/series_som_stage2/` (robustez del schedule) |
| `make som-figures` | `analysis/results/som/figures/` |
| `make som-profiles` | `analysis/results/som/profiles/` |

## Oja y campañas (Fase 3)

La regla de Oja corre en C (`series_oja`); Python compara su vector con PC1, arma las listas por campaña con la regla commiteada en la sección 4 de `deliverables/03-oja-campanas.md` y corre la demo de mantenimiento. Las salidas van a `analysis/results/` (no se versiona). Desde la raíz de TP4:

| Target | Escribe |
|---|---|
| `make oja` | `analysis/results/oja/` (`weights.csv`, `index.csv`, comparación con PC1, convergencia y evidencia del máximo) |
| `make campaigns` | `analysis/results/campaigns/` (listas por campaña, líneas base por followers, métricas y dos figuras); se niega a correr si la regla o `analysis/campaigns_select.py` cambiaron desde su commit |
| `make maintenance` | `analysis/results/maintenance/` (demo con un creador sintético `SYN001`: mapeo con `scripts/map_creator.py`, neurona ganadora, índice de Oja y chequeo de deriva) |

## Hopfield (Fase 4)

La red de Hopfield se estudia sobre las 26 letras de 5 × 5 con la regla de elección de letras y el diseño de los experimentos commiteados antes de correr la red (sección 3 de `deliverables/04-hopfield-letras.md`). Las salidas van a `analysis/results/hopfield/` (no se versiona). Desde la raíz de TP4:

| Archivo | Qué hace |
|---|---|
| `scripts/letters.py` y `scripts/prepare_letters.py` | Leen `datos/letters/alphabet_5x5.txt` (26 letras de 5 × 5, `*` = +1 y `.` = −1) y escriben `datos/prepared/alphabet_pm1.csv` con su `.meta.json` (`make letters`) |
| `hopfield_select.py` | La regla de la sección 3 como código: los dos sets de letras, las constantes del diseño, la identidad de la regla (`rule_identity`) y la guardia `require_same_rule`; `python analysis/hopfield_select.py identity` termina con código 0 si la regla no cambió |
| `hopfield.py` | Control con numpy de las salidas de C. Recalcula en todas las corridas los pesos, `stored.csv`, los solapamientos y las columnas de estabilidad de la capacidad (solapamientos, letras estables, fracción estable, margen mínimo), y repite paso a paso los ensayos trazados (el primero de cada letra y nivel de recuperación: 2080 de 62 400; y los 1200 de la búsqueda de espurios). De los demás ensayos de recuperación (clase, convergencia, barridos, píxeles invertidos, `correct`) y de la `recall_rate` y la `mean_sweeps` de la capacidad solo comprueba rangos y consistencia; esas columnas son las que escribió C |
| `hopfield_letters.py` | Driver con guardia: arma en código las series de recuperación, capacidad (p = 4 y por p, con la extensión escrita en la regla) y estado espurio a partir de las constantes congeladas, corre el binario, pasa cada corrida por `hopfield.py` (con el alcance de la fila anterior), registra en `run.json` la identidad del código de la red (`code_identity`) y agrega los resultados |
| `hopfield_figures.py` | Las nueve figuras: glifos, solapamientos, histograma del solapamiento máximo en valor absoluto, margen por píxel, recuperación frente al ruido, energía, capacidad con p = 4, capacidad por p y estado espurio |

| Target | Escribe |
|---|---|
| `make letters` | `datos/prepared/alphabet_pm1.csv` y `alphabet_pm1.meta.json` |
| `make hopfield-letters` | `analysis/results/hopfield/letters/`: `selection.json`, `orthogonality.json`, `recall.csv`, `recall_by_pattern.csv`, `capacity_p4.csv`, `capacity_by_p.csv`, `capacity.json`, `spurious.json`, `run.json` y `sweeps/` (las corridas de C) |
| `make hopfield-figures` | `analysis/results/hopfield/figures/` (`letters`, `overlaps`, `max_overlap_hist`, `cross_terms`, `recall_noise`, `energy`, `capacity_p4`, `capacity_by_p`, `spurious`, cada una en `.svg` y `.png`); necesita los resultados de `make hopfield-letters` |

La guardia: `make hopfield-letters` y `make hopfield-figures` comparan el sha256 del texto entre los marcadores de la sección 3 del entregable, del código de selección, del alfabeto y del conversor con los del commit de la regla, y se niegan a correr o a dibujar (el mensaje termina en `(D-04)`) si alguno cambió o si `alphabet_pm1.csv` no es el alfabeto commiteado; una corrida que falla o que no coincide con numpy no deja ninguna salida. La guardia no fija el código de la red (el núcleo en C, el driver y el control en numpy): `run.json` guarda en `code_identity` el commit, si hay cambios sin commitear (`dirty`), el sha256 de `neuron/models/hopfield.c`, `hopfield_core.c`, `hopfield_core.h`, `neuron/io/config.c`, `analysis/hopfield.py` y `analysis/hopfield_letters.py`, y el sha256 del binario; `make hopfield-figures` se niega a dibujar si alguno de esos archivos cambió desde la corrida (el mensaje manda a repetir `make hopfield-letters`). Con las mismas seeds, todos los CSV, JSON y SVG salen idénticos en una reejecución.

Las series de la corrida de letras se generan en código a partir de las constantes congeladas de `hopfield_select.py` (no hay un archivo de series para editar), así que no aparecen en "Series existentes"; `series_smoke_hopfield` sigue siendo la serie chica sobre el fixture de `neuron/tests/fixtures/`.
