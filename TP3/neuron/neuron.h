#ifndef __NEURON_H__
#define __NEURON_H__

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct neuron * Neuron;

#define EPSILON 0.0001

// weights has n_inputs + 1 elements (weights[0] = w0, the bias weight)
Neuron neuron_new(int n_inputs, double (*func)(double), double (*func_prime)(double), const double weights[], double eta);

void neuron_free(Neuron neuron);

int neuron_get_n_inputs(const Neuron neuron);

double neuron_predict(const Neuron neuron, const double input[], double * h_out);

// Online update for a single neuron: accumulate + apply
void neuron_learn(Neuron neuron, const double input[], double zeta);

// Adds eta * delta * input to the pending Δw, without touching the weights.
// delta already includes theta'(h): (zeta - O) * theta'(h) at the output, backpropagated otherwise.
void neuron_accumulate(Neuron neuron, const double input[], double delta);

// weights += pending Δw, then clears it
void neuron_apply(Neuron neuron);

double neuron_theta_prime(const Neuron neuron, double h);

// i = 0 is the bias weight
double neuron_get_weight(const Neuron neuron, int i);

void neuron_train(Neuron neuron, int n_inputs, const double dataset[][n_inputs], const double zetas[], int n_samples, int epochs);

// out must have room for n_inputs + 1 elements
void neuron_get_weights(const Neuron neuron, double out[]);

// weights has n_inputs + 1 elements; drops any Δw still pending
void neuron_set_weights(Neuron neuron, const double weights[]);

#endif //__NEURON_H__
