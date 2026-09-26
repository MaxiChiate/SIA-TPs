#ifndef __NEURON_H__
#define __NEURON_H__

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "config.h"

typedef struct neuron * Neuron;

#define EPSILON 0.000001

// weights has n_inputs + 1 elements (weights[0] = w0, the bias weight)
Neuron neuron_new(int n_inputs, double (*func)(double), double (*func_prime)(double), const double weights[], double eta);

void neuron_free(Neuron neuron);

int neuron_get_n_inputs(const Neuron neuron);

double neuron_predict(const Neuron neuron, const double input[], double * h_out);

int neuron_learn(Neuron neuron, const double input[], double zeta);

__attribute__((deprecated("neuron_train is deprecated")))
int neuron_train(Neuron neuron, int n_inputs, const double dataset[][n_inputs], const double zetas[], int n_samples, int max_epochs);

int neuron_train_by_epoch(Neuron neuron, int n_inputs, const double dataset[][n_inputs], const double zetas[], int n_samples);

// out must have room for n_inputs + 1 elements
void neuron_get_weights(const Neuron neuron, double out[]);

void plot_neuron_validation(const Neuron neuron, int n_inputs, const double dataset[][n_inputs], const double zetas[], int n_samples);

#endif //__NEURON_H__
