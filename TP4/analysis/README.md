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
| `series_smoke_oja` | El stub de Oja sobre los datos auditados (`datos/prepared/creadores_zscore.csv`, 50 x 26; `make prepare` lo genera, no se versiona), 3 seeds | ¿Funciona el lazo config, binario, `summary.csv`? |
| `series_smoke_kohonen` | El SOM de Kohonen entrenado (vecindad `step`, 260 épocas) sobre los mismos datos, `grid_k` en 2, 3 y 4, 3 seeds (9 corridas). `summary.csv` trae ahora `qe`, `te` y `empty_fraction`, más `occupied_neurons`, `mean_hits_occupied`, `max_hits` y `singleton_neurons` de `metrics.json` | ¿La clave que varía (`grid_k`) y las medidas del mapa quedan como columnas de `summary.csv`? |
| `series_smoke_hopfield` | El stub de Hopfield sobre las letras de `neuron/tests/fixtures/patterns_small.csv`, dos variantes de `noise_levels` (`low`: 0.0 y 0.1; `high`: 0.3 y 0.5), 2 seeds (4 corridas) | ¿Funciona una variante que cambia una lista? (`noise_levels` va codificada como JSON en la columna) |

Desde la raíz de TP4 también se corre con `make sweep SERIES=analysis/series_smoke_kohonen.json` (por defecto,
`series_smoke_oja.json`); `make sweep` genera antes `datos/prepared/` si falta.
