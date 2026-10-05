# Roadmap — Optimizadores (Ejercicio 2)

## Estado (5/10, para quien siga)

- **Pasos 0 a 8: hechos y en `dev-perceptron`.** Los cinco optimizadores (`gd`, `momentum`, `rmsprop`,
  `adam`, `adaptive_eta`) están implementados, con tests, y elegibles desde el config.
- **Etapa 1 (η por optimizador): hecha.** Se amplió la grilla hacia arriba hasta encontrar el pico de cada
  uno (`analysis/series_eta_{gd,adaptive,momentum,rmsprop,adam}.json` y `series_eta_edges*.json`). Mejor η:
  GD 0.5, η adaptativo 0.5, momentum 0.05, RMSProp 0.001, Adam 0.0005.
- **Etapa 2 (los cinco con su mejor η, 5 seeds): hecha.** `analysis/series_optimizer.json` (validación) y
  `series_optimizer_test.json` (entrenando con `more_digits`, sobre `digits_test`). Sin diferencias
  significativas; ver `DECISIONS.md`.
- **Falta (paso 9, documentar):** `neuron/README.md`. `DECISIONS.md` y `CLAUDE.md` ya están.
- **Ideas si se sigue:** más épocas o `tolerance`; otras arquitecturas con cada optimizador; más seeds
  (con 5, el p mínimo del test exacto es 0.0625: para poder rechazar a 0.05 hacen falta 6 o más).

Plan para sumar a la red los optimizadores de la Clase 12.1: **momentum**, **η adaptativo**, **RMSProp**
y **Adam**. El enunciado pide como mínimo comparar "variantes de mecanismos de optimización" en dígitos,
y son también la base de las técnicas del Ejercicio 3.

**Objetivo de diseño:** que el optimizador no sepa nada del problema ni de la red. Recibe un vector de
pesos y un vector de gradiente, y devuelve el paso. No conoce dígitos, fraude, capas ni neuronas: si mañana
cambia el objeto del TP, el optimizador no se toca.

---

## 1. Dónde estamos hoy

- `neuron.c` guarda `eta` adentro de cada neurona y en `neuron_accumulate` suma **η·δ·x** a `pending`.
  `neuron_apply` hace `weights += pending`.
- O sea, hoy el η está "cocinado" en el acumulador: el Δw ya sale hecho. Para meter un optimizador,
  esto hay que separarlo.
- `network_train` llama a `apply_updates` una vez por batch (online, mini-batch o batch: mismo camino).
- `main.c` mide el error de train y validación al final de cada época en `record_epoch`.
- El config es JSON plano (`io/config.c`, tabla `FIELDS`): no hay objetos anidados.
- `neuron_learn`, `neuron_learn_only` y `neuron_train` no se usan en ningún lado (código muerto).

## 2. El diseño en una imagen

```
backprop (network.c)          acumula  d = δ·x          ← la dirección de descenso, SIN η
   │
   ▼  al cerrar el batch
optimizer_step(state, weights, d, n)                     ← no sabe qué son esos n números
   │
   ▼
weights += Δw                                            ← Δw lo decide el optimizador

η adaptativo (main.c, una vez por época)                 ← mira solo el error E
   └─ optimizer_set_eta(...)
```

**Separación clave:** backprop calcula el gradiente; el optimizador decide qué hacer con él (la frase
de la 12.1: *"backprop te da el gradiente; el optimizador decide cómo usarlo"*).

### Convención de signo

Acumulamos **d = δ·x = −∂E/∂w**, la dirección en la que **baja** el error (es lo que ya calcula
`neuron_accumulate`, sin el η). Con esa convención todas las fórmulas quedan con **+**:

| Optimizador | Estado por peso | Paso (con d = −∂E/∂w) |
|---|---|---|
| GD | — | Δw = η·d |
| Momentum | v (Δw anterior) | v = α·v + η·d ; Δw = v |
| RMSProp | S | S = γ·S + (1−γ)·d² ; Δw = η·d / √(S + ε) |
| Adam | m, v, t | m = β1·m + (1−β1)·d ; v = β2·v + (1−β2)·d² ; m̂ = m/(1−β1ᵗ) ; v̂ = v/(1−β2ᵗ) ; Δw = η·m̂ / (√v̂ + ε) |

Ojo (lo marca el apunte de la 12.1): el paper de Adam **resta** porque usa g = +∂E/∂w. Como d = −g,
m cambia de signo, v no (está al cuadrado), y el paso queda con +. Es el error más probable de toda la
implementación: los tests del paso 3 lo cazan.

### η adaptativo: un optimizador más (`"optimizer": "adaptive_eta"`)

**Decidido:** es el quinto valor de `optimizer`, al lado de `gd`, `momentum`, `rmsprop` y `adam`. Es GD
con un η que cambia, como lo presenta la clase.

La diferencia con los otros: no decide el paso con el gradiente de cada peso, sino que ajusta **un solo η
para toda la red** mirando el **error E por época**. Por eso tiene dos partes:

- **El paso** es el de GD: Δw = η·d, dentro de `optimizer_step` como cualquier otro.
- **El ajuste de η** pasa una vez por época, desde `record_epoch` en `main.c`, que es donde ya se mide E.
  `main` solo lo llama si el optimizador elegido es `adaptive_eta`.

---

## 3. Config (claves nuevas, todas opcionales)

Sin ninguna clave nueva, la red tiene que hacer **exactamente lo mismo que hoy** (GD con η fijo). Así no
se rompe ningún config ni serie existente.

| Clave | Tipo | Cuándo | Qué es |
|---|---|---|---|
| `optimizer` | string | opcional, default `"gd"` | `gd`, `momentum`, `rmsprop`, `adam` o `adaptive_eta` |
| `momentum` | número | obligatoria con `momentum` | α, en [0, 1). Típico 0.9 |
| `rmsprop_decay` | número | obligatoria con `rmsprop` | γ, en [0, 1). Típico 0.9 |
| `adam_beta1`, `adam_beta2` | número | obligatorias con `adam` | Típicos 0.9 y 0.999 |
| `optimizer_epsilon` | número | obligatoria con `rmsprop` y `adam` | Típico 1e-8 |
| `eta_increase` | número | obligatoria con `adaptive_eta` | **a**: se suma a η tras `eta_patience_up` épocas seguidas bajando |
| `eta_decrease` | número | obligatoria con `adaptive_eta` | **b**: η ← η·(1 − b) tras `eta_patience_down` épocas seguidas subiendo |
| `eta_patience_up`, `eta_patience_down` | entero | obligatorias con `adaptive_eta` | **k** y **k′** de la clase |

**Decidido: obligatorias, sin default.** Por qué:
- El parser deja en 0 las claves que faltan, y α = 0 o β = 0 son valores válidos que cambian el
  algoritmo (momentum con α = 0 es GD): un default en 0 sería un error silencioso.
- Un default "de la clase" (α = 0.9) correría, pero el `config.json` copiado en `results/` no diría con qué
  α corrió. Obligatorias, cada corrida queda autoexplicada.
- Mismo criterio que `split_seed`, obligatoria con `validation_split`.

Para que no sea molesto, **el error recomienda el valor de la clase**:

```
config.json: missing key "momentum" for optimizer "momentum" (typical: 0.9)
config.json: missing key "adam_beta2" for optimizer "adam" (typical: 0.999)
```

| Clave | Valor típico que sugiere el error | De dónde sale |
|---|---|---|
| `momentum` | 0.9 | Clase 12.1 (0.8 o 0.9) |
| `rmsprop_decay` | 0.9 | Clase 12.1 (Hinton) |
| `adam_beta1` / `adam_beta2` | 0.9 / 0.999 | Paper de Adam |
| `optimizer_epsilon` | 1e-8 | Paper de Adam |
| `eta_increase`, `eta_decrease` | sin típico universal: el mensaje pide elegirlo | Clase 12.1 (solo da la forma +a, −bη) |

Una clave de un optimizador que no está elegido también es un error (`"momentum"` con
`"optimizer": "adam"`), igual que hoy `split_seed` sin `validation_split`.

---

## 4. Pasos

Cada paso termina con `make test` en verde y es un commit chico. **No avanzar al siguiente si la
validación del paso no pasa.**

### Paso 0 — Medir el "antes"

Antes de tocar nada, correr y guardar fuera de `results/` (para comparar después):

- `config.json.xor.example` con 6 seeds → cuántas convergen y en cuántas épocas.
- `config.json.fraud.example` con seed 1 → `epochs.csv`.

**Valida:** nada todavía; es la referencia del paso 1.

### Paso 1 — Separar η del acumulador (refactor sin cambio de comportamiento)

- `neuron_accumulate` suma **δ·x** (sin η) a un buffer `gradient`.
- `neuron_apply` hace `weights += η·gradient` y lo limpia. Todavía no hay optimizador: es GD a mano.
- Borrar `neuron_learn`, `neuron_learn_only` y `neuron_train` (no los usa nadie).

**Valida:**
- `make test` sin tocar ningún test (el de backprop contra el gradiente numérico y el de update a mano
  tienen que seguir pasando tal cual).
- Las corridas del paso 0 dan lo mismo: `epochs.csv` igual hasta ~1e-12. No da idéntico al bit porque
  ahora es η·Σ(δx) en vez de Σ(η·δx), y el orden de las cuentas en punto flotante cambia.

### Paso 2 — Módulo `optimizer/` con GD

Archivos nuevos `neuron/optimizer/optimizer.c/h`, con el mismo patrón que `activation/` (se elige por
nombre). La interfaz trabaja sobre arreglos planos y no incluye nada de `neuron.h` ni `network.h`:

```c
typedef struct { const char * name; double eta, momentum, decay, beta1, beta2, epsilon; } OptimizerConfig;
typedef struct optimizer * Optimizer;

Optimizer optimizer_new(const OptimizerConfig * config, int n_weights); // estado en 0
void optimizer_step(Optimizer optimizer, double weights[], const double descent[], int n_weights);
void optimizer_set_eta(Optimizer optimizer, double eta);  // para el η adaptativo
double optimizer_eta(const Optimizer optimizer);
void optimizer_free(Optimizer optimizer);
```

- Cada neurona tiene **su propio** `Optimizer` (el estado es por peso, y cada neurona tiene sus pesos).
  `neuron_apply` llama a `optimizer_step(opt, weights, gradient, n_inputs + 1)`.
- `network_new` recibe un `const OptimizerConfig *` en lugar de `double eta`.
- `network_set_eta(network, eta)` recorre las neuronas (lo usa el paso 7).

**Valida:**
- Las mismas comparaciones del paso 1 (con `gd` tiene que dar lo mismo que el paso 1).
- Test nuevo, **sin red**: GD sobre f(w) = ½(w − 3)² (d = 3 − w) llega a w ≈ 3. Este test es la prueba de
  que el optimizador es genérico: no hay ninguna neurona en juego.

### Paso 3 — Momentum, RMSProp y Adam

Una función de paso por optimizador, más su estado (v; S; m, v, t).

- `t` cuenta **actualizaciones**, no épocas (en online o mini-batch son muchas por época).
- El estado arranca en 0 y vive mientras viva la red.

**Valida (tests a mano, con los números del apunte de la 12.1):**

| Test | Esperado |
|---|---|
| Momentum, η = 0.1, α = 0.9, d = 1 constante | Δw = 0.1, 0.19, 0.271, 0.344 … → 1.0 |
| Momentum, d alternando +1 / −1 | \|Δw\| = 0.1, 0.01, 0.091, 0.018 … → 0.053 |
| Momentum con α = 0 | Idéntico a GD, paso a paso |
| RMSProp, γ = 0.9, primer paso | \|Δw\| ≈ 3.16·η (el sesgo del arranque que explica la clase) |
| Adam, primer paso con d = 100, 1 y 0.01 | \|Δw\| = η en los tres (no depende de la escala) |
| Adam, signo | Con d > 0 el peso **sube** (caza el error de signo del paper) |
| Los cuatro sobre f(w) = ½(w − 3)² | Todos llegan a w ≈ 3 |

### Paso 4 — Config

- Claves de la sección 3 en `Config` y en `FIELDS` (`io/config.c`).
- Validaciones: nombre de optimizador conocido; hiperparámetros obligatorios según el optimizador; clave
  de otro optimizador → error; α, γ, β en [0, 1); ε > 0.
- `main.c` arma el `OptimizerConfig` y se lo pasa a `network_new`.
- Agregar `config.json.adam.example` (o similar).

**Valida:**
- `test_config_loading` cubre: sin `optimizer` → `gd`; `adam` sin `adam_beta2` → error que menciona 0.999; `momentum` con
  `"optimizer": "rmsprop"` → error; optimizador desconocido → error con la lista de nombres.
- Todos los `config.json.*.example` y las `series_*.json` existentes siguen corriendo sin cambios.

### Paso 5 — Integración con la red

**Valida:**
- El test de backprop contra el gradiente numérico **no se toca** (backprop no cambió).
- XOR `[2,2,1]` con 6 seeds y cada optimizador: hoy con GD convergen 3 de 6. Anotar cuántas convergen y en
  cuántas épocas con momentum y Adam. No hay un número "correcto", pero si Adam o momentum convergen en
  **menos** seeds que GD, hay que sospechar del signo o de η.
- `same_seed_same_result` con cada optimizador: misma seed ⇒ mismo resultado.
- Con `batch_size` = N (batch completo), cambiar el orden de las muestras no cambia nada, también con Adam
  (ya existe ese test para GD).

### Paso 6 — η en la salida

- `epochs.csv` suma una columna `eta`: el η vigente en cada época. Con η fijo es constante, pero deja todo
  listo para el paso 7 y para graficarlo.
- `run_report.py` y `sweep_report.py` leen con `DictReader`, así que una columna extra no los rompe.
  Opcional: graficar η por época en el reporte.

**Valida:** una corrida vieja (sin columna `eta`) sigue abriendo en el reporte.

### Paso 7 — η adaptativo

Módulo chico `optimizer/eta_schedule.c/h`, que tampoco sabe nada de la red:

```c
EtaSchedule eta_schedule_new(double a, double b, int k_up, int k_down);
double eta_schedule_update(EtaSchedule * s, double eta, double error); // devuelve el η nuevo
```

- `adaptive_eta` se registra en `optimizer/` como los demás; su paso es el de GD.
- Si el optimizador es `adaptive_eta`, `record_epoch` llama a `eta_schedule_update` con el **E de train**
  de esa época, y si η cambió, `network_set_eta`.
- Sube **sumando** a; baja **multiplicando** por (1 − b). Crecer despacio y frenar rápido, como en la clase.
- E de **train** y no de validación: si el η se ajustara mirando validación, la validación pasaría a ser
  parte del entrenamiento (mismo criterio que la mejor época en `DECISIONS.md`).

**Valida:**
- Test sin red, con una secuencia de errores inventada: `[10, 9, 8, 7]` con k = 3 → η sube una vez en +a;
  `[1, 2, 3]` con k′ = 2 → η·(1 − b); `[5, 4, 5, 4]` → no cambia (no hay racha).
- `adaptive_eta` con a = 0 y b = 0 da lo mismo que `gd`.
- En una corrida real, la columna `eta` de `epochs.csv` muestra los escalones.

### Paso 8 — Comparación de optimizadores en dígitos

**El problema:** el mismo η significa cosas distintas en cada optimizador. En GD el paso es η × gradiente;
en momentum (α = 0.9) los pasos se acumulan hasta ~10 veces; en Adam y RMSProp cada peso se mueve ≈ η por
paso, sin importar el gradiente. Con un único η para todos, la comparación favorece al optimizador para
el que se eligió ese η, y la conclusión sería sobre el η y no sobre el método.

**Decidido:** cada optimizador con su mejor η (etapas 1 y 2) más un gráfico de sensibilidad (etapa 3).

#### Lo que se mantiene fijo en todas las corridas

La regla de oro del TP2: **una perilla por vez**.

- **Datos:** train `digits.csv`, validación con `validation_split` + `split_seed` (la misma `split_seed`
  en todas). `digits_test.csv` **no se usa** para elegir nada: el enunciado dice que es "producción".
- **Red:** misma arquitectura, misma activación, mismo `batch_size`, mismo `shuffle`.
- **Seeds:** las mismas en todas las variantes de todas las series. Con la misma seed, todos los
  optimizadores arrancan con exactamente los mismos pesos iniciales.
- **Épocas fijas y sin `tolerance`:** si cada corrida corta cuando converge, no hacen el mismo trabajo y
  no se comparan (mismo criterio que en el TP2 con las generaciones).
- **Hiperparámetros del optimizador:** los típicos de la clase (α = 0.9, γ = 0.9, β1 = 0.9, β2 = 0.999,
  ε = 1e-8). Lo único que se busca es η; el resto queda fijo para no multiplicar las corridas.

#### Etapa 1 — Una serie de η por optimizador

Cinco series, una por optimizador, con una grilla de η adaptada a su escala. Son cinco series y no una
porque `sweep.py` admite hasta 8 variantes por serie.

| Serie | Optimizador | Grilla de η | Por qué esa escala |
|---|---|---|---|
| `series_eta_gd.json` | `gd` | 0.001 · 0.005 · 0.01 · 0.05 | La de `series_eta.json`, pasada a `digits.csv` + split |
| `series_eta_adaptive.json` | `adaptive_eta` | 0.001 · 0.005 · 0.01 · 0.05 | Es el η **inicial**; después se mueve solo |
| `series_eta_momentum.json` | `momentum` | 0.0005 · 0.001 · 0.005 · 0.01 | ~10 veces más chica que GD, porque α = 0.9 acelera hasta ×10 |
| `series_eta_rmsprop.json` | `rmsprop` | 0.0001 · 0.0005 · 0.001 · 0.005 | Alrededor del default de la clase (0.001) |
| `series_eta_adam.json` | `adam` | 0.0001 · 0.0005 · 0.001 · 0.005 | Alrededor del default del paper (0.001) |

Con 3 seeds son 5 × 4 × 3 = 60 corridas.

**Cómo se elige el mejor η:** la **accuracy de validación** final, promediada entre seeds. Accuracy y no
MSE porque es un problema de clasificación y es la métrica que se reporta (Ej. 3 pide ≥ 98%). Si dos η
quedan con las seeds pisándose, se elige el más chico (más estable).

> **Ojo con los bordes:** si el mejor η de un optimizador es el **extremo** de su grilla (el más chico o
> el más grande), el óptimo puede estar afuera. Se agrega un valor más en esa dirección antes de pasar a
> la etapa 2.

#### Etapa 2 — La comparación final

`series_optimizer.json`: cinco variantes (`gd`, `adaptive_eta`, `momentum`, `rmsprop`, `adam`), cada
una con el η que ganó en la etapa 1. Se usa `variants` (no `vary`), porque cada variante cambia
`optimizer` y `eta` a la vez. Conviene más seeds que en la etapa 1 (por ejemplo 5), porque es el
resultado que se presenta.

Qué mirar:
- **Curva de validación por época:** quién baja más rápido y quién llega más abajo.
- **Resultado final, un punto por seed:** si los puntos de dos optimizadores se pisan, no se puede afirmar
  que uno sea mejor (la tabla con el test pareado de `plots_main.py` lo dice).
- **Tiempo** (`elapsed_s`): Adam hace más cuentas por paso; si gana, ¿gana también en segundos o solo
  en épocas?
- **`adaptive_eta`:** la columna `eta` de `epochs.csv`, para mostrar cómo se movió η.

#### Etapa 3 — Gráfico de sensibilidad a η

No necesita corridas nuevas: sale de los `summary.csv` de la etapa 1.

- Eje x: η (escala logarítmica). Eje y: accuracy de validación final. Una línea por optimizador, con un
  punto por seed o una banda entre seeds.
- Responde **qué tan delicado es elegir η** en cada optimizador. Lo esperable es que Adam y RMSProp anden
  bien en un rango ancho y GD solo en uno angosto. Si se confirma, es un argumento fuerte para la
  presentación; si no, también hay que contarlo.
- No existe todavía: es un script nuevo, por ejemplo `analysis/plots_eta_sensitivity.py`, que recibe las
  cinco carpetas de resultados. Con plotly, como `plots_main.py`.

**Valida:**
- Las seis series corren con `sweep.py` y sus gráficos salen con `plots_main.py`.
- En el `config.json` de cada corrida (`runs/<corrida>/config.json`) se ve el optimizador, el η y los
  hiperparámetros: cualquier punto de un gráfico se puede reproducir.
- Ningún config de estas series menciona `digits_test.csv`.

### Paso 9 — Documentar

- `DECISIONS.md`: una entrada por decisión (ver sección 5).
- `neuron/README.md`: las claves nuevas en la tabla de configuración.
- `CLAUDE.md`: estado.

---

## 5. Entradas para `DECISIONS.md`

Cada una con **Qué** y **Por qué**. Son preguntas probables en la defensa:

1. **El optimizador recibe vectores planos y no conoce la red.** Por qué: lo pide el diseño genérico,
   y se puede testear solo (los tests sobre f(w) = ½(w − 3)²).
2. **Se acumula d = −∂E/∂w sin η, y η lo aplica el optimizador.** Por qué: si η queda dentro del
   acumulador, RMSProp y Adam no pueden reescalar cada peso.
3. **Convención de signo** y cómo queda Adam respecto del paper.
4. **Un estado de optimizador por neurona**, y `t` cuenta actualizaciones, no épocas.
5. **η adaptativo como quinto optimizador** (GD con η variable, como en la clase), ajustado sobre el E
   de train una vez por época. Por qué la asimetría (+a, ×(1−b)).
6. **Hiperparámetros obligatorios, sin defaults escondidos.**
7. **Con `initial_weights`, el estado del optimizador arranca en 0** (no se guarda m, v ni S). Es una
   limitación: retomar con Adam no es exactamente seguir la misma corrida.
8. **Comparación justa:** cada optimizador con su mejor η, elegido por accuracy de validación (nunca
   con `digits_test.csv`), con grillas adaptadas a la escala de cada uno. Más el gráfico de sensibilidad,
   que muestra cuánto depende cada optimizador de acertarle a η.

## 6. Fuera de este roadmap (anotado para no olvidarlo)

- **Inicialización Xavier** (Clase 11): hoy los pesos son U[−0.5, 0.5] en todas las capas; con 784
  entradas puede saturar la primera capa. Se puede sumar como otra perilla después.
- **Regularización** (Clase 13: early stopping por validación, L2, ruido como data augmentation): es lo
  natural para el Ejercicio 3, pregunta (b).
- **Promediar en vez de sumar los Δw del batch:** sigue abierto en `DECISIONS.md`. Con Adam importa
  menos, porque el paso no depende de la escala del gradiente.
