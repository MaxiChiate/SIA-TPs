#ifndef __RESULTS_H__
#define __RESULTS_H__

// Every run writes into its own directory, results/<date>_<time>_<activation>/, next to a copy of
// the config that produced it:
//   config.json      the config file, byte for byte
//   weights.csv      one row per weight: layer, neuron, weight (0 = bias), initial and final value
//   predictions.csv  validation inputs, zeta and the network's prediction

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

int results_write_predictions(const Results * results, int n_inputs, const double inputs[][n_inputs],
                              const double zetas[], const double predictions[], int n_samples);

#endif //__RESULTS_H__
