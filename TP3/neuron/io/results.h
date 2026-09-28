#ifndef __RESULTS_H__
#define __RESULTS_H__

// Every run writes into its own directory, results/<date>_<time>_<activation>/, next to a copy of
// the config that produced it:
//   config.json      the config file, byte for byte
//   weights.csv      one row per weight: layer, neuron, weight (0 = bias), initial and final value
//   predictions.csv  validation inputs, zeta and the network's prediction
//   epochs.csv       E, MSE, MAE and max |e| on train and validation after every epoch (0 = initial weights)
//   predictions_by_epoch.csv  validation zeta and the prediction at a few epochs, one column per epoch
// With several outputs every zeta and prediction column becomes one per output: zeta_0, zeta_1, ...,
// prediction_0, ..., epoch_<e>_0, ...

#include "../network.h"

#define RESULTS_ROOT "results"
#define RESULTS_PATH_MAX 512

typedef struct {
  char dir[RESULTS_PATH_MAX];
} Results;

// Creates the run directory and copies the config into it.
// Returns 1 on success; on failure prints the reason to stderr and returns 0.
int results_create(const char * config_path, const char * activation, Results * results);

// sizes has n_layers + 1 elements (sizes[0] = inputs). initial and final hold the weights layer by
// layer and neuron by neuron, each neuron as w0 (bias), w1, ..., wn.
int results_write_weights(const Results * results, int n_layers, const int sizes[], const double initial[],
                          const double final[]);

// zetas and predictions are row-major n_samples x n_outputs
int results_write_predictions(const Results * results, int n_inputs, int n_outputs, const double inputs[][n_inputs],
                              const double zetas[], const double predictions[], int n_samples);

// train and validation have n_epochs + 1 elements; epoch 0 is the untrained network
int results_write_epochs(const Results * results, int n_epochs, const ErrorMetrics train[],
                         const ErrorMetrics validation[]);

// zetas is n_samples x n_outputs and predictions n_snapshots x n_samples x n_outputs, both row-major:
// predictions[k] holds every prediction at epochs[k]
int results_write_snapshots(const Results * results, int n_snapshots, const int epochs[], int n_samples,
                            int n_outputs, const double zetas[], const double predictions[]);

#endif //__RESULTS_H__
