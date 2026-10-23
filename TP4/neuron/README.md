# Neurona

Núcleo en C del TP4: un solo binario, `build/neuron`, que corre el modelo que diga el config (`kohonen`, `oja` o
`hopfield`). En la Fase 1 los tres eran stubs deterministas que ejercitan todo el lazo (config, entrada, `Rng`,
escritura de resultados); la Fase 2 reemplazó el cuerpo de `kohonen` por el mapa autoorganizado real, la Fase 3
reemplazó el de `oja` por la regla de Oja y la Fase 4 reemplazó el de `hopfield` por la red real.

## Requisitos

`gcc` y `make`. Para los tests de Python y los datos preparados, además, el `.venv` de la raíz (`make venv`).

## Uso

Desde `TP4/`, un `make` solo deja todo listo en un clone nuevo: crea `.venv`, genera `datos/prepared/` y compila:

```sh
make                       # TP4/: venv + prepare + neuron/build/neuron
cd neuron
make run CONFIG=config.json.kohonen.example   # compila si hace falta y corre
./build/neuron config.json.oja.example        # o directamente
```

Los configs de ejemplo (`config.json.kohonen.example`, `config.json.oja.example`, `config.json.hopfield.example`) se
copian a `config.json` para usarlos como propios (`config.json` no se versiona); `config.json.hopfield_capacity.example`
es el de la tarea `capacity`. Los de kohonen y oja leen
`../datos/prepared/creadores_zscore.csv` (50 x 26, los z-scores de los creadores auditados), que genera
`make prepare` (o un `make` solo) en `TP4/` y **no se versiona**: un clone nuevo no lo tiene hasta que se genera. El
de hopfield (`config.json.hopfield.example` y `config.json.hopfield_capacity.example`) leen
`tests/fixtures/patterns_mix.csv` (seis patrones sintéticos de 25 píxeles en ±1, sin relación con las letras).

Otros targets: `make clean` borra `build/`.

## Tests

```sh
make test       # tests de C y después pytest (../analysis/tests); también desde TP4/
make test-c     # solo los tests de C (incluidos `oja training`, `hopfield run`, `hopfield core` y `hopfield capacity`; leen solo tests/fixtures)
make debug      # los tests de C con AddressSanitizer y UndefinedBehaviorSanitizer, en build/debug
```

`make test` regenera `datos/prepared/` si falta (lo leen los tests de Python). Los tests de C escriben solo dentro de
`build/test_tmp/` y borran lo que crearon. `make debug` termina con error si hay un reporte de los sanitizers.

Los cinco tests de C: `config strict validation` (configs válidos e inválidos, objetos anidados, claves con puntos),
`same seed, same bytes` (los tres modelos, dos corridas con la misma seed dan los mismos bytes; el caso de kohonen tiene
más neuronas que muestras), `dispatch by model` (la tabla de modelos y la de claves coinciden) y `kohonen training`
(vecindad de paso con R = 1 sin diagonales, vecindad gaussiana, decaimiento, las 6 muestras de la fixture repartidas
entre 9 neuronas, `trace.csv` de principio a fin y todos los valores de config que el modelo rechaza) y
`oja training` (el helper de orientación, la convergencia al autovector principal sobre la fixture, `trace.csv` de
principio a fin y los valores que el modelo rechaza, incluida la cota de estabilidad `eta0 x max |x|^2 < 1`).

## Config

Un JSON por corrida. Las tres claves comunes:

| Clave   | Tipo    | Significado |
|---------|---------|-------------|
| `model` | string  | `kohonen`, `oja` o `hopfield` |
| `seed`  | entero >= 0 | Siembra el único `Rng` de la corrida (splitmix64, nunca `rand()`) |
| `input` | string  | CSV numérico con encabezado, relativo a la carpeta desde donde corre el binario (`neuron/`) |

La validación es estricta (D-02): una clave que el modelo no declara, repetida, faltante o de tipo equivocado aborta
la corrida antes de empezar, con un mensaje que nombra la clave. No hay valores por defecto silenciosos.

Claves de cada modelo:

| Modelo | Clave | Tipo | Significado |
|--------|-------|------|-------------|
| `kohonen` | `grid_k` | entero entre 2 y 32 | Lado de la grilla `k x k` de neuronas; puede haber más neuronas que muestras |
| `kohonen` | `neighborhood` | `"step"` o `"gaussian"` | Vecindad del ganador: `step` actualiza las neuronas a distancia de grilla `<= R` (con `<=`, no `<`: R = 1 alcanza a las cuatro vecinas y no a las diagonales); `gaussian` las pesa con `exp(-d^2 / 2 sigma^2)` |
| `kohonen` | `radius0` | número >= 1 | `R` (o `sigma`) en el primer paso; decae exponencialmente |
| `kohonen` | `radius_final` | número, `>= 1` en `step`, `> 0` en `gaussian`, `<= radius0` | `R` (o `sigma`) en el último paso: es el piso, nunca baja de ahí |
| `kohonen` | `eta0` | número, `0 < eta0 < 1` | Tasa de aprendizaje en el primer paso |
| `kohonen` | `eta_final` | número, `0 < eta_final <= eta0` | Tasa de aprendizaje en el último paso; decae exponencialmente |
| `kohonen` | `epochs` | entero entre 1 y 100000 | Pasadas sobre las muestras, cada una en orden barajado |
| `oja` | `eta0` | número, `0 < eta0 < 1` y `eta0 x max \|x\|^2 < 1` | Tasa de aprendizaje en el primer paso. La segunda condición es la cota de estabilidad (Pitfall 8): `max \|x\|^2` es el mayor cuadrado de la norma de una fila de la entrada, y el valor se escribe como `eta0_max_x2` |
| `oja` | `eta_final` | número, `0 < eta_final <= eta0` | Tasa de aprendizaje en el último paso; `eta` decae exponencialmente entre las dos a lo largo de `epochs x n` pasos |
| `oja` | `epochs` | entero entre 1 y 100000 | Pasadas sobre las muestras, cada una en orden barajado; fijo, sin parada por tolerancia |
| `hopfield` | `task` | `"recall"` o `"capacity"` | `recall`: guarda los patrones de `subset` y recupera versiones ruidosas; `capacity`: guarda `p` patrones por subconjunto y mide cuántos son puntos fijos y cuántos se recuperan |
| `hopfield` | `rule` | `"hebb"` | Regla de aprendizaje: W = suma de xi xi^T con diagonal cero y sin 1/N |
| `hopfield` | `update` | `"async"` o `"sync"` | `async` (referencia): una neurona por vez en orden aleatorio nuevo en cada barrido; `sync` (comparación): todas a la vez, con detección de ciclos de 2 |
| `hopfield` | `max_sweeps` | entero entre 1 y 10000 | Tope de barridos (async) o pasos (sync) |
| `hopfield` | `trials` | entero entre 1 y 100000 | Consultas ruidosas por patrón guardado y nivel de ruido |
| `hopfield` | `noise_levels` | lista de 1 a 64 números en [0, 1] | Fracciones de píxeles que se invierten; se invierten exactamente `lround(nivel x N)` píxeles distintos; `capacity` toma un solo nivel |
| `hopfield` | `subset` | lista de índices de fila distintos de la entrada | Solo `recall`: los patrones que se guardan |
| `hopfield` | `trace_trials` | entero entre 0 y `trials` | Solo `recall`: ensayos por patrón y nivel cuyo trace paso a paso y cuyos estados se escriben |
| `hopfield` | `p` | entero entre 1 y 64, como mucho las filas de la entrada | Solo `capacity`: patrones guardados por subconjunto |
| `hopfield` | `n_subsets` | entero entre 0 y 10000 | Solo `capacity`: 0 = todos los subconjuntos de `p` filas en orden lexicográfico (hasta 200 000); si no, esa cantidad de subconjuntos distintos sorteados con la seed antes de los ensayos, menos que C(filas, p) |

La tarea `recall` toma `subset` y `trace_trials` y rechaza `p` y `n_subsets`; la tarea `capacity` toma `p`, `n_subsets` y un
solo nivel de ruido, y rechaza `subset` y `trace_trials`.

## Salida

Cada corrida escribe en su carpeta, `results/<fecha>_<hora>_<modelo>_seed<N>/`, y por stdout imprime solo
`results -> <carpeta>`. Si dos corridas caen en el mismo segundo, la segunda lleva sufijo `_2`. Dentro:

- `config.json`: el config, byte a byte.
- `metrics.json`: un objeto plano, una línea `"clave": valor` por métrica, números con 17 cifras significativas.
- los CSV del modelo: encabezado y después valores `%.17g`.

Regla de reproducibilidad (D-04): la fecha vive solo en el nombre de la carpeta. Ningún archivo guarda una hora, una
duración o una ruta absoluta (la duración va a stderr). Dos corridas con el mismo config y la misma seed dan carpetas
que `diff -r` declara idénticas.

Archivos y métricas de cada modelo:

| Modelo | CSV | `metrics.json` |
|--------|-----|----------------|
| `kohonen` | `prototypes.csv` (una fila por neurona: `neuron,row,col` y una columna por variable), `assignments.csv` (`sample,bmu,row,col,distance,bmu2`), `occupancy.csv` (`neuron,row,col,hits`, una fila por neurona), `trace.csv` (`epoch,eta,radius,qe,te`, la época 0 más una fila por época) | `model, seed, n_samples, n_features, grid_k, n_neurons, neighborhood, epochs, radius0, radius_final, eta0, eta_final, qe, te, occupied_neurons, empty_fraction, mean_hits_occupied, max_hits, singleton_neurons` |
| `oja` | `weights.csv` (una fila: el vector `w` de la neurona, de largo 1 y orientado para que su coeficiente de mayor valor absoluto sea positivo, la convención del PCA de la Fase 1; una columna por variable), `index.csv` (`sample,index` con `index = x . w`), `trace.csv` (`epoch,eta,w_norm,delta_w` y una columna por variable: la época 0 más una fila por época, con `w` al final de cada época antes de renormalizar) | `model, seed, n_samples, n_features, epochs, eta0, eta_final, eta0_max_x2, w_norm_final, delta_w_final, w_norm, sign_flipped, pivot, pivot_weight, index_mean, index_std` |
| `hopfield` (`recall`) | `stored.csv` (`pattern,source_row,fixed,min_margin,wrong_pixels,energy`), `overlaps.csv` (`pattern,m_0..`), `trials.csv` (`trial,pattern,source_row,noise,flipped,overlap,converged,sweeps,updates,flips,cycle,class,match_a,match_b,match_c,sign_a,sign_b,sign_c,correct,e_start,e_final,hamming_final,m_0..`), `trace.csv` (`trial,step,sweep,neuron,changed,energy`; el paso 0 es la consulta, con neurona -1), `states.csv` (`trial,kind,s_0..`; `kind` 0 es la consulta y 1 el estado final) | `model, seed, task, update, rule, n_patterns, n_neurons, n_levels, trials, stored_fixed, max_abs_overlap, recall_rate, wrong_stored_rate, inverse_rate, mixture_rate, other_rate, cycle_rate, mean_sweeps, mean_flips, energy_increases` |
| `hopfield` (`capacity`) | `capacity.csv` (`subset,idx_0..idx_{p-1},max_abs_overlap,mean_abs_overlap,n_stable,stable_fraction,min_margin,recall_rate,mean_sweeps`) | `model, seed, task, update, rule, n_patterns, n_neurons, n_rows, n_subsets, noise, trials, mean_stable_fraction, all_stable_fraction, mean_recall_rate` |

Códigos de `class` en `trials.csv`: 0 almacenado, 1 inverso, 2 mezcla, 3 otro (`match_*` y `sign_*` dicen qué patrones y con qué signo).

Los nombres de archivo y de columna son el contrato con el análisis: cuando una fase reemplaza un stub, los conserva. El
`queries.csv` del stub de Hopfield no tenía lector, así que la Fase 4 lo reemplazó por `trials.csv`, donde `pattern`,
`noise`, `flipped` y `overlap` conservan su significado.

## Series de corridas

`analysis/sweep.py` corre este mismo binario con varias seeds y variantes (ver `analysis/README.md`); desde `TP4/`:
`make sweep SERIES=analysis/series_smoke_kohonen.json`.

## Cómo extender

- **Una clave nueva en un modelo**: una fila más en la tabla `KeySpec` de ese modelo en `io/config.c` (por ejemplo
  `KOHONEN_KEYS`), y se lee en el runner con `config_get_int`, `config_get_number`, `config_get_string` o
  `config_get_number_array` (claves anidadas con puntos, `"vecindad.radio"`). Un objeto es una fila `KEY_OBJECT` con
  su tabla `children`. Agregá un caso a `config strict validation` en `tests/test_main.c`.
- **Reemplazar el cuerpo de un stub**: mantené la firma `int run_{modelo}(const Config *, Rng *, const Results *)`
  (en `models/models.h`) y los nombres de los archivos que escribe. El despacho y las tablas de claves no cambian.
- **Un modelo nuevo**: un runner en `models/`, una fila en `MODELS` (`models/models.c`) y una en `MODEL_KEYS`
  (`io/config.c`), en el mismo orden en las dos tablas; el test `dispatch by model` falla si no coinciden.
- Los números salen siempre del `Rng` que recibe el runner (nunca `rand()`), y el binario se compila con `-O2` sin
  banderas que reordenen sumas, para poder comparar el C con numpy.
