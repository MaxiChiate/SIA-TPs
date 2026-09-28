#ifndef __NETWORK_H__
#define __NETWORK_H__

#include "activation/activation.h"

typedef struct network * Network;

// sizes has n_layers + 1 elements: sizes[0] = inputs, sizes[l] = neurons in layer l (the last one is
// the output). {2, 2, 1} is the 2-2-1 net; {n, 1} is a simple perceptron.
// draw_weight is called once per weight, layer by layer and neuron by neuron, bias first.
Network network_new(int n_layers, const int sizes[], const Activation * activation, double eta,
                    double (*draw_weight)(void));

void network_free(Network network);

int network_n_inputs(const Network network);

int network_n_outputs(const Network network);

// Weight count across every neuron, for network_get_weights
int network_n_weights(const Network network);

// out gets every weight, layer by layer and neuron by neuron, each neuron as w0 (bias), w1, ..., wn
void network_get_weights(const Network network, double out[]);

// output must have room for network_n_outputs elements
void network_predict(Network network, const double input[], double output[]);

// zetas is row-major n_samples x n_outputs.
// batch_size = 1 is online, batch_size >= n_samples is full batch, anything between is mini-batch:
// Δw is accumulated over the batch and the weights change once at its end.
void network_train(Network network, const double inputs[], const double zetas[], int n_samples,
                   int epochs, int batch_size);

#endif //__NETWORK_H__
