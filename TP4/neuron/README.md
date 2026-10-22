# Neurona

Núcleo en C del TP4: un solo binario, `build/neuron`, que corre el modelo que diga el config (`kohonen`, `oja` o
`hopfield`). En la Fase 1 los tres eran stubs deterministas que ejercitan todo el lazo (config, entrada, `Rng`,
escritura de resultados); la Fase 2 reemplazó el cuerpo de `kohonen` por el mapa autoorganizado real, la Fase 3
reemplazó el de `oja` por la regla de Oja (solo `hopfield` sigue siendo un stub) y las Fases 4 y 5 reemplazan el de
`hopfield`.

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
copian a `config.json` para usarlos como propios (`config.json` no se versiona). Los de kohonen y oja leen
`../datos/prepared/creadores_zscore.csv` (50 x 26, los z-scores de los creadores auditados), que genera
`make prepare` (o un `make` solo) en `TP4/` y **no se versiona**: un clone nuevo no lo tiene hasta que se genera. El
de hopfield lee `tests/fixtures/patterns_small.csv` (dos letras 5 x 5 en ±1).

Otros targets: `make clean` borra `build/`.

## Tests

```sh
make test       # tests de C y después pytest (../analysis/tests); también desde TP4/
make test-c     # solo los 5 tests de C (leen solo tests/fixtures)
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
| `hopfield` | `noise_levels` | lista de 1 a 64 números en [0, 1] | Fracciones de píxeles que se invierten por patrón |

## Salida

Cada corrida escribe en su carpeta, `results/<fecha>_<hora>_<modelo>_seed<N>/`, y por stdout imprime solo
`results -> <carpeta>`. Si dos corridas caen en el mismo segundo, la segunda lleva sufijo `_2`. Dentro:

- `config.json`: el config, byte a byte.
- `metrics.json`: un objeto plano, una línea `"clave": valor` por métrica, números con 17 cifras significativas.
- los CSV del modelo: encabezado y después valores `%.17g`.

Regla de reproducibilidad (D-04): la fecha vive solo en el nombre de la carpeta. Ningún archivo guarda una hora, una
duración o una ruta absoluta (la duración va a stderr). Dos corridas con el mismo config y la misma seed dan carpetas
que `diff -r` declara idénticas.

Archivos y métricas de cada modelo (hopfield sigue siendo un stub):

| Modelo | CSV | `metrics.json` |
|--------|-----|----------------|
| `kohonen` | `prototypes.csv` (una fila por neurona: `neuron,row,col` y una columna por variable), `assignments.csv` (`sample,bmu,row,col,distance,bmu2`), `occupancy.csv` (`neuron,row,col,hits`, una fila por neurona), `trace.csv` (`epoch,eta,radius,qe,te`, la época 0 más una fila por época) | `model, seed, n_samples, n_features, grid_k, n_neurons, neighborhood, epochs, radius0, radius_final, eta0, eta_final, qe, te, occupied_neurons, empty_fraction, mean_hits_occupied, max_hits, singleton_neurons` |
| `oja` | `weights.csv` (una fila: el vector `w` de la neurona, de largo 1 y orientado para que su coeficiente de mayor valor absoluto sea positivo, la convención del PCA de la Fase 1; una columna por variable), `index.csv` (`sample,index` con `index = x . w`), `trace.csv` (`epoch,eta,w_norm,delta_w` y una columna por variable: la época 0 más una fila por época, con `w` al final de cada época antes de renormalizar) | `model, seed, n_samples, n_features, epochs, eta0, eta_final, eta0_max_x2, w_norm_final, delta_w_final, w_norm, sign_flipped, pivot, pivot_weight, index_mean, index_std` |
| `hopfield` | `queries.csv` (`pattern,noise,flipped,overlap`) | `model, seed, n_patterns, n_neurons, n_levels, mean_overlap` |

Los nombres de archivo y de columna son el contrato con el análisis: cuando una fase reemplaza un stub, los conserva.

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
