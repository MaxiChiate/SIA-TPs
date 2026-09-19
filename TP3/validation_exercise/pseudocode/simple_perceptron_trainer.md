# Perceptrón simple — pseudocódigo

## MÓDULO: trainer

```
# Vocabulario:
#   época   = una pasada completa por todo el dataset
#   batch   = cuántas muestras antes de tocar los pesos una vez
#   update  = una modificación efectiva de los pesos
#
#   batch = 1  → online     (N updates por época)
#   batch = N  → batch full (1 update por época)
#   intermedio → mini-batch


ESTRUCTURA EpochRecord:
    epoch, error, misclassified, weights, n_updates


ESTRUCTURA TrainingResult:
    history, best_weights, best_error, best_epoch, converged, epochs_run


CLASE Trainer:

    CONSTRUCTOR(model, eta, batch_size, max_epochs, tolerance, shuffle, seed):
        guardar parámetros
        self.update_rule = select_update_rule(model.activation)


    FUNCIÓN train(x, y):
        resultado = TrainingResult vacío

        PARA epoch DESDE 1 HASTA max_epochs:

            SI shuffle ENTONCES orden = permutación aleatoria de las muestras
            SI NO           orden = 0, 1, 2, ..., N-1

            PARA CADA batch EN partir(orden, batch_size):

                acumulado = vector de ceros

                PARA CADA mu EN batch:
                    h   = model.excitation(x[mu])
                    O   = model.activation.theta(h)
                    x_b = model.with_bias(x[mu])

                    acumulado += self.update_rule(eta, y[mu], O, x_b, h, activation)

                # Un solo update por batch
                model.weights = model.weights + acumulado

            # Métricas sobre TODO el dataset, con los pesos ya actualizados
            predicciones = model.predict(x)
            error        = squared_error(y, predicciones)
            mal_clasif   = contar_mal_clasificadas(y, predicciones)

            guardar EpochRecord en resultado.history

            # El error NO baja monótonamente: una corrección puede romper
            # otra muestra. Por eso guardamos el mejor visto, no el último.
            SI error < resultado.best_error ENTONCES
                resultado.best_error   = error
                resultado.best_weights = copia de model.weights
                resultado.best_epoch   = epoch

            SI has_converged(error, mal_clasif) ENTONCES
                resultado.converged = verdadero
                CORTAR

        DEVOLVER resultado


    FUNCIÓN has_converged(error, mal_clasif):
        SI la activación es discreta (escalón) ENTONCES
            DEVOLVER mal_clasif == 0
        SI NO
            # Con floats un 0 exacto no pasa nunca
            DEVOLVER error < tolerance


    FUNCIÓN contar_mal_clasificadas(y, predicciones):
        # Solo tiene sentido con targets discretos
        SI y no es todo ±1 ENTONCES DEVOLVER 0
        DEVOLVER cantidad de muestras con signo(predicción) != signo(y)
```
