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


static int shared_n_outputs(const Dataset train, const Dataset validation) {
  int n_outputs = dataset_n_outputs(train);
  if (dataset_n_outputs(validation) != n_outputs) {
    die("output count mismatch: train has %d zetas, validation has %d", n_outputs, dataset_n_outputs(validation));
  }
  return n_outputs;
}


// Uniform in [-0.5, 0.5]. rand is seeded once in main, so every neuron gets different weights.
static double random_weight(void) {
  return (double) rand() / RAND_MAX - 0.5;
}


// {n_inputs, hidden_layers..., n_outputs}: one output neuron per zeta column of the dataset
static int layer_sizes(const Config * config, int n_inputs, int n_outputs, int sizes[]) {
  sizes[0] = n_inputs;
  for (int i = 0; i < config->n_hidden_layers; i++) {
    sizes[i + 1] = config->hidden_layers[i];
  }
  int n_layers = config->n_hidden_layers + 1;
  sizes[n_layers] = n_outputs;
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


#define SNAPSHOT_INTERVALS 10 // validation predictions saved at 0%, 10%, ..., 100% of the epochs


// What training leaves besides the weights: errors after every epoch (index 0 is the untrained
// network) and the validation predictions at a few snapshot epochs
typedef struct {
  Dataset train;
  Dataset validation;
  ErrorMetrics * train_errors;
  ErrorMetrics * validation_errors;
  int snapshot_epochs[SNAPSHOT_INTERVALS + 1];
  int n_snapshots;
  int next_snapshot;
  double * snapshot_predictions; // n_snapshots x validation samples x outputs, row-major
} TrainingHistory;


static ErrorMetrics dataset_error(Network network, const Dataset dataset) {
  return network_error(network, dataset_inputs(dataset), dataset_zetas(dataset), dataset_n_samples(dataset));
}


// predictions gets n_samples x n_outputs, row-major
static void predict_dataset(Network network, const Dataset dataset, double predictions[]) {
  int n_inputs = dataset_n_inputs(dataset);
  int n_outputs = dataset_n_outputs(dataset);
  const double * inputs = dataset_inputs(dataset);
  for (int i = 0; i < dataset_n_samples(dataset); i++) {
    network_predict(network, &inputs[i * n_inputs], &predictions[i * n_outputs]);
  }
}


static void record_epoch(int epoch, Network network, void * context) {
  TrainingHistory * history = context;
  history->train_errors[epoch] = dataset_error(network, history->train);
  history->validation_errors[epoch] = dataset_error(network, history->validation);

  if (history->next_snapshot < history->n_snapshots && history->snapshot_epochs[history->next_snapshot] == epoch) {
    int n_values = dataset_n_samples(history->validation) * dataset_n_outputs(history->validation);
    predict_dataset(network, history->validation, &history->snapshot_predictions[history->next_snapshot * n_values]);
    history->next_snapshot++;
  }
}


// Evenly spaced; with fewer epochs than intervals some would repeat, so those are dropped
static int snapshot_epochs(int epochs, int out[]) {
  int n = 0;
  for (int k = 0; k <= SNAPSHOT_INTERVALS; k++) {
    int epoch = (int) ((long) k * epochs / SNAPSHOT_INTERVALS);
    if (n == 0 || out[n - 1] != epoch) out[n++] = epoch;
  }
  return n;
}


static TrainingHistory new_training_history(const Dataset train, const Dataset validation, int epochs) {
  TrainingHistory history = {
    .train = train,
    .validation = validation,
    .train_errors = malloc((epochs + 1) * sizeof(ErrorMetrics)),
    .validation_errors = malloc((epochs + 1) * sizeof(ErrorMetrics)),
  };
  history.n_snapshots = snapshot_epochs(epochs, history.snapshot_epochs);
  history.snapshot_predictions = malloc((size_t) history.n_snapshots * dataset_n_samples(validation)
                                        * dataset_n_outputs(validation) * sizeof(double));
  if (history.train_errors == NULL || history.validation_errors == NULL || history.snapshot_predictions == NULL) {
    die("couldn't allocate training history");
  }
  return history;
}


static void free_training_history(TrainingHistory * history) {
  free(history->train_errors);
  free(history->validation_errors);
  free(history->snapshot_predictions);
}


static void train_network(Network network, const Dataset train, const Config * config, TrainingHistory * history) {
  record_epoch(0, network, history);
  network_train(network, dataset_inputs(train), dataset_zetas(train), dataset_n_samples(train),
                config->epochs, config->batch_size, record_epoch, history);
}


static void save_history(const Results * results, const TrainingHistory * history, int epochs) {
  int ok = results_write_epochs(results, epochs, history->train_errors, history->validation_errors)
        && results_write_snapshots(results, history->n_snapshots, history->snapshot_epochs,
                                   dataset_n_samples(history->validation), dataset_n_outputs(history->validation),
                                   dataset_zetas(history->validation),
                                   history->snapshot_predictions);
  if (!ok) exit(EXIT_FAILURE);
}


static void validate_network(Network network, const Dataset validation, const Results * results) {
  int n_inputs = dataset_n_inputs(validation);
  int n_outputs = dataset_n_outputs(validation);
  int n_samples = dataset_n_samples(validation);
  const double (*inputs)[n_inputs] = (const double (*)[n_inputs]) dataset_inputs(validation);

  double * predictions = malloc((size_t) n_samples * n_outputs * sizeof(double));
  if (predictions == NULL) die("couldn't allocate predictions");
  predict_dataset(network, validation, predictions);

  int ok = results_write_predictions(results, n_inputs, n_outputs, inputs, dataset_zetas(validation), predictions,
                                     n_samples);
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
  int n_outputs = shared_n_outputs(train, validation);

  int sizes[CONFIG_HIDDEN_LAYERS_MAX + 2];
  int n_layers = layer_sizes(&config, n_inputs, n_outputs, sizes);

  srand(config.seed);
  Network network = network_new(n_layers, sizes, activation, config.eta, random_weight);
  double * initial_weights = snapshot_weights(network);

  Results results = create_results(path, config.activation);
  TrainingHistory history = new_training_history(train, validation, config.epochs);
  train_network(network, train, &config, &history);
  save_history(&results, &history, config.epochs);
  save_weights(&results, n_layers, sizes, initial_weights, network);
  validate_network(network, validation, &results);
  printf("results -> %s\n", results.dir);

  free_training_history(&history);
  free(initial_weights);
  network_free(network);
  dataset_free(train);
  dataset_free(validation);
  return 0;

}
