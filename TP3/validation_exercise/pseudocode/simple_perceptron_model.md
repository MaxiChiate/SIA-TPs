# Perceptrón simple — pseudocódigo

## MÓDULO: model

```
CLASE SimplePerceptron:

    CONSTRUCTOR(n_inputs, activation, seed):
        self.activation = activation
        self.n_inputs   = n_inputs
        # weights[0] es el bias, va con la entrada fija x0 = 1
        self.weights    = aleatorios(n_inputs + 1) en [-0.5, 0.5]


    FUNCIÓN with_bias(x):
        # Agrega la columna fija de 1 adelante.
        # Así el bias se actualiza con la misma fórmula que el resto.
        DEVOLVER [1, x_1, x_2, ..., x_n]


    FUNCIÓN excitation(x):
        # h = w · x, vectorizado sobre todas las muestras
        DEVOLVER with_bias(x) · self.weights


    FUNCIÓN predict(x):
        DEVOLVER self.activation.theta(excitation(x))


    FUNCIÓN decision_boundary():
        # La recta h = 0. Solo tiene sentido con 2 entradas.
        SI n_inputs != 2 ENTONCES DEVOLVER nada
        (w0, w1, w2) = self.weights
        DEVOLVER "x2 = (-w1/w2) * x1 + (-w0/w2)"


    FUNCIÓN load_weights(pesos):
        # Para retomar un entrenamiento sin arrancar de cero.
        VERIFICAR que la dimensión coincida
        self.weights = pesos
```
