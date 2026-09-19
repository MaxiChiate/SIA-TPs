# Perceptrón simple — pseudocódigo

## MÓDULO: activations

```
ESTRUCTURA Activation:
    theta          # θ(h): salida de la neurona
    theta_prime    # θ'(h): derivada
    uses_gradient  # falso solo para el escalón
    output_range   # rango de salida


ACTIVACIÓN step:
    theta(h)        = 1 si h >= 0, si no -1
    theta_prime(h)  = 0            # inútil: mataría el update
    uses_gradient   = falso
    output_range    = (-1, 1)


ACTIVACIÓN linear:
    theta(h)        = h
    theta_prime(h)  = 1
    uses_gradient   = verdadero
    output_range    = (-inf, inf)


ACTIVACIÓN tanh(beta):
    theta(h)        = tanh(beta * h)
    theta_prime(h)  = beta * (1 - theta(h)^2)
    uses_gradient   = verdadero
    output_range    = (-1, 1)


ACTIVACIÓN logistic(beta):
    theta(h)        = 1 / (1 + exp(-2 * beta * h))
    theta_prime(h)  = 2 * beta * theta(h) * (1 - theta(h))
    uses_gradient   = verdadero
    output_range    = (0, 1)        # la que sirve para probabilidades


ACTIVACIÓN relu:
    theta(h)        = max(0, h)
    theta_prime(h)  = 1 si h > 0, si no 0
    uses_gradient   = verdadero
    output_range    = (0, inf)


FUNCIÓN build_activation(nombre, beta):
    DEVOLVER la activación que corresponda al nombre
```
