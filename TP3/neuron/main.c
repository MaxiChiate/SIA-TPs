#include "activation/activation.h"
#include "io/config.h"
#include "io/dataset.h"
#include "io/results.h"
#include "network.h"
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>

#define DEFAULT_CONFIG_PATH "config.json"


static void die(const char * format, ...) {
  va_list args;
  va_start(args, format);
  vfprintf(stderr, format, args);
  va_end(args);
  fputc('\n', stderr);
  exit(EXIT_FAILURE);
}


static const char * config_path(int argc, char * argv[]) {
  if (argc > 2) die("usage: %s [config.json]", argv[0]);
  return argc == 2 ? argv[1] : DEFAULT_CONFIG_PATH;
}


static Config load_config(const char * path) {
  Config config;
  if (!config_load(path, &config)) exit(EXIT_FAILURE);
  return config;
}


static const Activation * load_activation(const char * name) {
  const Activation * activation = activation_find(name);
  if (activation == NULL) die("unknown activation \"%s\" (available: %s)", name, activation_names());
  return activation;
}


static Dataset load_dataset(const char * path) {
  Dataset dataset = dataset_load(path);
  if (dataset == NULL) exit(EXIT_FAILURE);
  return dataset;
}


static int shared_n_inputs(const Dataset train, const Dataset validation) {
  int n_inputs = dataset_n_inputs(train);
  if (dataset_n_inputs(validation) != n_inputs) {
    die("input count mismatch: train has %d, validation has %d", n_inputs, dataset_n_inputs(validation));
  }
  return n_inputs;
}


// Uniform in [-0.5, 0.5]. rand is seeded once in main, so every neuron gets different weights.
static double random_weight(void) {
  return (double) rand() / RAND_MAX - 0.5;
}


// {n_inputs, hidden_layers..., 1}: the dataset has a single zeta column, so one output neuron
static int layer_sizes(const Config * config, int n_inputs, int sizes[]) {
  sizes[0] = n_inputs;
  for (int i = 0; i < config->n_hidden_layers; i++) {
    sizes[i + 1] = config->hidden_layers[i];
  }
  int n_layers = config->n_hidden_layers + 1;
  sizes[n_layers] = 1;
  return n_layers;
}


static Results create_results(const char * config_path, const char * activation) {
  Results results;
  if (!results_create(config_path, activation, &results)) exit(EXIT_FAILURE);
  return results;
}


static double * snapshot_weights(const Network network) {
  double * weights = malloc(network_n_weights(network) * sizeof(double));
  if (weights == NULL) die("couldn't allocate weights");
  network_get_weights(network, weights);
  return weights;
}


static void save_weights(const Results * results, int n_layers, const int sizes[], const double initial_weights[],
                         const Network network) {
  double * final_weights = snapshot_weights(network);
  int ok = results_write_weights(results, n_layers, sizes, initial_weights, final_weights);
  free(final_weights);
  if (!ok) exit(EXIT_FAILURE);
}


static void train_network(Network network, const Dataset train, const Config * config) {
  network_train(network, dataset_inputs(train), dataset_zetas(train), dataset_n_samples(train),
                config->epochs, config->batch_size);
}


static void validate_network(Network network, const Dataset validation, const Results * results) {
  int n_inputs = dataset_n_inputs(validation);
  int n_samples = dataset_n_samples(validation);
  const double (*inputs)[n_inputs] = (const double (*)[n_inputs]) dataset_inputs(validation);

  double * predictions = malloc(n_samples * sizeof(double));
  if (predictions == NULL) die("couldn't allocate predictions");
  for (int i = 0; i < n_samples; i++) {
    network_predict(network, inputs[i], &predictions[i]);
  }

  int ok = results_write_predictions(results, n_inputs, inputs, dataset_zetas(validation), predictions, n_samples);
  free(predictions);
  if (!ok) exit(EXIT_FAILURE);
}


int main(int argc, char * argv[]) {

  const char * path = config_path(argc, argv);
  Config config = load_config(path);
  const Activation * activation = load_activation(config.activation);
  Dataset train = load_dataset(config.train_dataset);
  Dataset validation = load_dataset(config.validation_dataset);
  int n_inputs = shared_n_inputs(train, validation);

  int sizes[CONFIG_HIDDEN_LAYERS_MAX + 2];
  int n_layers = layer_sizes(&config, n_inputs, sizes);

  srand(config.seed);
  Network network = network_new(n_layers, sizes, activation, config.eta, random_weight);
  double * initial_weights = snapshot_weights(network);

  Results results = create_results(path, config.activation);
  train_network(network, train, &config);
  save_weights(&results, n_layers, sizes, initial_weights, network);
  validate_network(network, validation, &results);
  printf("results -> %s\n", results.dir);

  free(initial_weights);
  network_free(network);
  dataset_free(train);
  dataset_free(validation);
  return 0;

}
