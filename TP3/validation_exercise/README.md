# Ejercicio (validación)

Casos del enunciado (`../docs/Enunciado TP3 - 2Q 2026.pdf`) que sirven para validar las
herramientas implementadas. No se presentan, pero fijan el contrato de cada módulo.

| Herramienta | Caso de validación |
| --- | --- |
| Perceptrón simple escalón | AND lógico: `x = {(-1,1), (1,-1), (-1,-1), (1,1)}`, `y = {-1,-1,-1,1}` |
| Perceptrón simple lineal | ~50 muestras de una función lineal (p. ej. `y = x`) |
| Perceptrón simple no lineal | ~50 muestras de una función no lineal (p. ej. `y = tanh(x)`) |
| Perceptrón multicapa | XOR lógico: mismas `x`, `y = {1, 1, -1, -1}`; arquitecturas `[2,2,1]` y `[2,3,2,1]` |

## Pseudocódigo

Diseño del perceptrón simple, un archivo por módulo:

- [`pseudocode/simple_perceptron_activation_functions.md`](pseudocode/simple_perceptron_activation_functions.md) — `activations`: θ, θ' y rango de salida de cada activación.
- [`pseudocode/simple_perceptron_update_rules.md`](pseudocode/simple_perceptron_update_rules.md) — `update_rules`: regla de Rosenblatt vs. descenso por gradiente y el error cuadrático.
- [`pseudocode/simple_perceptron_model.md`](pseudocode/simple_perceptron_model.md) — `model`: pesos con bias, excitación, predicción y frontera de decisión.
- [`pseudocode/simple_perceptron_trainer.md`](pseudocode/simple_perceptron_trainer.md) — `trainer`: épocas, batches, historial y criterio de convergencia.
