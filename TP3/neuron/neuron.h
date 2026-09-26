#ifndef __NEURON_H__
#define __NEURON_H__

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct neuron * Neuron;

#define N_INPUTS 2
#define WEIGHTS_AMOUNT (N_INPUTS + 1) //weights[0] = w0

Neuron neuron_new(double (*func)(double), double (*func_prime)(double), double weights[], double eta);

double neuron_predict(const Neuron neuron, const double input[N_INPUTS], double * h_out);

int neuron_learn(Neuron neuron, const double input[N_INPUTS], double zeta);

int neuron_train(Neuron neuron, const double dataset[][N_INPUTS], const double zetas[], int n_samples, int max_epochs);

void neuron_get_weights(const Neuron neuron, double out[WEIGHTS_AMOUNT]);

#endif //__NEURON_H__
