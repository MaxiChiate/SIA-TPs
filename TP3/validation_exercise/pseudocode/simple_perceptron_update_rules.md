# Perceptrón simple — pseudocódigo

## MÓDULO: update_rules

```
# Convención: w_nuevo = w_viejo + Δw
# El menos del gradiente ya está adentro de Δw.


FUNCIÓN rosenblatt_update(eta, zeta, O, x, h, activation):
    # Regla del escalón. NO sale de derivar el error:
    # θ' = 0 daría Δw = 0 siempre.
    # Justificación: h se mueve hacia el lado correcto de la frontera.
    DEVOLVER eta * (zeta - O) * x


FUNCIÓN gradient_update(eta, zeta, O, x, h, activation):
    # E = ½(zeta - θ(h))²
    # dE/dw_i = -(zeta - θ(h)) * θ'(h) * x_i
    # Δw_i = -eta * dE/dw_i
    DEVOLVER eta * (zeta - O) * activation.theta_prime(h) * x


FUNCIÓN select_update_rule(activation):
    # La única bifurcación entre escalón y el resto.
    SI activation.uses_gradient ENTONCES
        DEVOLVER gradient_update
    SI NO
        DEVOLVER rosenblatt_update


FUNCIÓN squared_error(zeta, O):
    DEVOLVER ½ * suma sobre muestras de (zeta - O)²
```
