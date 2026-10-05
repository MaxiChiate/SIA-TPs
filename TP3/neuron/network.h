#ifndef __NETWORK_H__
#define __NETWORK_H__

#include "activation/activation.h"
#include "optimizer/optimizer.h"
#include "rng.h"

typedef struct network * Network;

// sizes has n_layers + 1 elements: sizes[0] = inputs, sizes[l] = neurons in layer l (the last one is
// the output). {2, 2, 1} is the 2-2-1 net; {n, 1} is a simple perceptron.
// Every neuron gets its own optimizer built from optimizer (same name and hyperparameters, its own state).
// draw_weight(context) is called once per weight, layer by layer and neuron by neuron, bias first.
Network network_new(int n_layers, const int sizes[], const Activation * activation, const OptimizerConfig * optimizer,
                    double (*draw_weight)(void * context), void * context);

void network_free(Network network);

int network_n_inputs(const Network network);

int network_n_outputs(const Network network);

// Weight count across every neuron, for network_get_weights
int network_n_weights(const Network network);

// out gets every weight, layer by layer and neuron by neuron, each neuron as w0 (bias), w1, ..., wn
void network_get_weights(const Network network, double out[]);

// Inverse of network_get_weights: weights is laid out the same way
void network_set_weights(Network network, const double weights[]);

// The learning rate, shared by every neuron's optimizer
double network_eta(const Network network);

// Changes it in every neuron's optimizer at once
void network_set_eta(Network network, double eta);

// output must have room for network_n_outputs elements
void network_predict(Network network, const double input[], double output[]);

// Averages are over every output value, n_samples * n_outputs (with one output, per sample)
typedef struct {
  double energy;        // E = 1/2 * sum((zeta - O)^2), what training minimizes
  double mse;           // sum((zeta - O)^2) / n
  double mae;           // sum(|zeta - O|) / n
  double max_abs_error; // max |zeta - O|
} ErrorMetrics;

// Error of the network with its current weights. Doesn't train.
// zetas is row-major n_samples x n_outputs.
ErrorMetrics network_error(Network network, const double inputs[], const double zetas[], int n_samples);

// Samples whose prediction is off by more than 0.5 on any output. Meant for discrete activations (sign),
// where a prediction is either right or wrong.
int network_misclassified(Network network, const double inputs[], const double zetas[], int n_samples);

// Called after every epoch (numbered from 1), once the epoch's last batch is applied.
// Returns nonzero to stop training (converged).
typedef int (*EpochCallback)(int epoch, Network network, void * context);

// zetas is row-major n_samples x n_outputs.
// batch_size = 1 is online, batch_size >= n_samples is full batch, anything between is mini-batch:
// Δw is accumulated over the batch and the weights change once at its end.
// shuffle_rng may be NULL: the samples then go in the order given, every epoch. Otherwise they are
// reshuffled with it at the start of each epoch (the batches change from one epoch to the next).
// on_epoch may be NULL. Returns the number of epochs run: less than epochs if on_epoch asked to stop.
int network_train(Network network, const double inputs[], const double zetas[], int n_samples,
                  int epochs, int batch_size, Rng * shuffle_rng, EpochCallback on_epoch, void * context);

#endif //__NETWORK_H__
