#ifndef __NEURON_H__
#define __NEURON_H__

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "optimizer/optimizer.h"

typedef struct neuron * Neuron;

// weights has n_inputs + 1 elements (weights[0] = w0, the bias weight). The neuron gets its own optimizer,
// built from optimizer; aborts if there's no optimizer with that name.
Neuron neuron_new(int n_inputs, double (*func)(double), double (*func_prime)(double), const double weights[],
                  const OptimizerConfig * optimizer);

void neuron_free(Neuron neuron);

int neuron_get_n_inputs(const Neuron neuron);

double neuron_predict(const Neuron neuron, const double input[], double * h_out);

// Adds delta * input to the accumulated gradient, without touching the weights. That sum is the descent
// direction -dE/dw: eta isn't applied here but by the optimizer, in neuron_apply.
// delta already includes theta'(h): (zeta - O) * theta'(h) at the output, backpropagated otherwise.
void neuron_accumulate(Neuron neuron, const double input[], double delta);

// The optimizer moves the weights with the accumulated gradient, which is then cleared
void neuron_apply(Neuron neuron);

double neuron_eta(const Neuron neuron);

void neuron_set_eta(Neuron neuron, double eta);

double neuron_theta_prime(const Neuron neuron, double h);

// i = 0 is the bias weight
double neuron_get_weight(const Neuron neuron, int i);

// out must have room for n_inputs + 1 elements
void neuron_get_weights(const Neuron neuron, double out[]);

// weights has n_inputs + 1 elements; drops any gradient still accumulated
void neuron_set_weights(Neuron neuron, const double weights[]);

#endif //__NEURON_H__
