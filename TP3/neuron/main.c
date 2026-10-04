#define _POSIX_C_SOURCE 200809L // clock_gettime

#include "activation/activation.h"
#include "io/config.h"
#include "io/dataset.h"
#include "io/results.h"
#include "network.h"
#include "rng.h"
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

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


// validation_dataset is its own file; otherwise train_dataset is split, with its own seed so the split
// stays the same while seed (the initial weights, the shuffling) varies
static void load_datasets(const Config * config, Dataset * train, Dataset * validation) {
  *train = load_dataset(config->train_dataset);
  if (config->validation_dataset[0] != '\0') {
    *validation = load_dataset(config->validation_dataset);
    return;
  }

  Dataset all = *train;
  Rng split_rng = rng_new(config->split_seed);
  if (!dataset_split(all, config->validation_split, &split_rng, train, validation)) exit(EXIT_FAILURE);
  fprintf(stderr, "split %s: %d train / %d validation samples\n", config->train_dataset, dataset_n_samples(*train),
          dataset_n_samples(*validation));
  dataset_free(all);
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


// Uniform in [-0.5, 0.5], drawn from the run's single Rng
static double random_weight(void * context) {
  return rng_uniform(context) - 0.5;
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


// Keeps training an earlier run: its final weights replace the random ones
static void load_initial_weights(const char * path, Network network, int n_layers, const int sizes[]) {
  double * weights = malloc(network_n_weights(network) * sizeof(double));
  if (weights == NULL) die("couldn't allocate weights");
  if (!results_read_weights(path, n_layers, sizes, weights)) exit(EXIT_FAILURE);
  network_set_weights(network, weights);
  free(weights);
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


static double now_seconds(void) {
  struct timespec now;
  clock_gettime(CLOCK_MONOTONIC, &now);
  return now.tv_sec + now.tv_nsec * 1e-9;
}


#define SNAPSHOT_INTERVALS 10 // validation predictions saved at 0%, 10%, ..., 100% of the epochs


#define PROGRESS_INTERVAL 1.0 // seconds between progress lines


// What training leaves besides the weights: errors and training time after every epoch (index 0 is
// the untrained network) and the validation predictions at a few snapshot epochs
typedef struct {
  Dataset train;
  Dataset validation;
  int epochs;          // planned
  int epochs_run;      // actually trained: fewer when it converged
  int discrete;        // activation's outputs are classes
  double tolerance;    // train MSE that counts as converged (continuous activations); 0 = never
  double best_mse;     // lowest train MSE seen, and the weights and epoch it happened at
  int best_epoch;
  double * best_weights;
  ErrorMetrics * train_errors;
  ErrorMetrics * validation_errors;
  double * elapsed;    // seconds spent training up to each epoch; evaluating the errors is left out
  double started_at;   // wall clock, error evaluation included
  double resumed_at;   // when training last resumed after record_epoch
  double reported_at;  // when progress was last printed
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


// On stderr, since make run reads the run directory from stdout. At most one line per
// PROGRESS_INTERVAL, plus the last epoch.
static void report_progress(TrainingHistory * history, int epoch) {
  double now = now_seconds();
  int last = epoch == history->epochs;
  if (!last && now - history->reported_at < PROGRESS_INTERVAL) return;
  history->reported_at = now;

  double wall = now - history->started_at;
  fprintf(stderr, "epoch %d/%d (%3.0f%%)  train MSE %.4g  validation MSE %.4g  %.1fs", epoch, history->epochs,
          100.0 * epoch / history->epochs, history->train_errors[epoch].mse, history->validation_errors[epoch].mse,
          wall);
  if (!last && epoch > 0) fprintf(stderr, ", ~%.1fs left", wall / epoch * (history->epochs - epoch));
  fputc('\n', stderr);
}


// The error doesn't fall monotonically, so training keeps the best weights it saw, not the last ones
static void keep_if_best(TrainingHistory * history, int epoch, Network network) {
  double mse = history->train_errors[epoch].mse;
  if (epoch > 0 && mse >= history->best_mse) return;
  history->best_mse = mse;
  history->best_epoch = epoch;
  network_get_weights(network, history->best_weights);
}


// Discrete: every train sample classified right. Continuous: train MSE under the tolerance.
static int has_converged(const TrainingHistory * history, int epoch, Network network) {
  if (history->discrete) {
    return network_misclassified(network, dataset_inputs(history->train), dataset_zetas(history->train),
                                 dataset_n_samples(history->train)) == 0;
  }
  return history->tolerance > 0 && history->train_errors[epoch].mse < history->tolerance;
}


static int record_epoch(int epoch, Network network, void * context) {
  TrainingHistory * history = context;
  double paused_at = now_seconds();
  history->elapsed[epoch] = epoch == 0 ? 0.0 : history->elapsed[epoch - 1] + paused_at - history->resumed_at;

  history->train_errors[epoch] = dataset_error(network, history->train);
  history->validation_errors[epoch] = dataset_error(network, history->validation);

  if (history->next_snapshot < history->n_snapshots && history->snapshot_epochs[history->next_snapshot] == epoch) {
    int n_values = dataset_n_samples(history->validation) * dataset_n_outputs(history->validation);
    predict_dataset(network, history->validation, &history->snapshot_predictions[history->next_snapshot * n_values]);
    history->next_snapshot++;
  }

  keep_if_best(history, epoch, network);
  int converged = epoch > 0 && has_converged(history, epoch, network);

  report_progress(history, converged ? history->epochs : epoch);
  history->resumed_at = now_seconds();
  return converged;
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


static TrainingHistory new_training_history(const Dataset train, const Dataset validation, const Network network,
                                            const Config * config, const Activation * activation) {
  int epochs = config->epochs;
  TrainingHistory history = {
    .train = train,
    .validation = validation,
    .epochs = epochs,
    .epochs_run = epochs,
    .discrete = activation->discrete,
    .tolerance = config->tolerance,
    .best_weights = malloc(network_n_weights(network) * sizeof(double)),
    .train_errors = malloc((epochs + 1) * sizeof(ErrorMetrics)),
    .validation_errors = malloc((epochs + 1) * sizeof(ErrorMetrics)),
    .elapsed = malloc((epochs + 1) * sizeof(double)),
  };
  history.n_snapshots = snapshot_epochs(epochs, history.snapshot_epochs);
  history.snapshot_predictions = malloc((size_t) history.n_snapshots * dataset_n_samples(validation)
                                        * dataset_n_outputs(validation) * sizeof(double));
  if (history.train_errors == NULL || history.validation_errors == NULL || history.elapsed == NULL
      || history.snapshot_predictions == NULL || history.best_weights == NULL) {
    die("couldn't allocate training history");
  }
  return history;
}


static void free_training_history(TrainingHistory * history) {
  free(history->train_errors);
  free(history->validation_errors);
  free(history->elapsed);
  free(history->snapshot_predictions);
  free(history->best_weights);
}


static void train_network(Network network, const Dataset train, const Config * config, Rng * rng,
                          TrainingHistory * history) {
  history->started_at = history->reported_at = now_seconds();
  record_epoch(0, network, history);
  history->epochs_run = network_train(network, dataset_inputs(train), dataset_zetas(train),
                                      dataset_n_samples(train), config->epochs, config->batch_size,
                                      config->shuffle ? rng : NULL, record_epoch, history);
  network_set_weights(network, history->best_weights);
  fprintf(stderr, "%s after %d epochs; keeping the weights of epoch %d (train MSE %.4g)\n",
          history->epochs_run < config->epochs ? "converged" : "finished", history->epochs_run,
          history->best_epoch, history->best_mse);
}


static void save_history(const Results * results, const TrainingHistory * history) {
  int ok = results_write_epochs(results, history->epochs_run, history->train_errors, history->validation_errors,
                                history->elapsed)
        && results_write_snapshots(results, history->next_snapshot, history->snapshot_epochs,
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
  Dataset train, validation;
  load_datasets(&config, &train, &validation);
  int n_inputs = shared_n_inputs(train, validation);
  int n_outputs = shared_n_outputs(train, validation);

  int sizes[CONFIG_HIDDEN_LAYERS_MAX + 2];
  int n_layers = layer_sizes(&config, n_inputs, n_outputs, sizes);

  Rng rng = rng_new(config.seed);
  Network network = network_new(n_layers, sizes, activation, config.eta, random_weight, &rng);
  if (config.initial_weights[0] != '\0') load_initial_weights(config.initial_weights, network, n_layers, sizes);
  double * initial_weights = snapshot_weights(network);

  Results results = create_results(path, config.activation);
  TrainingHistory history = new_training_history(train, validation, network, &config, activation);
  train_network(network, train, &config, &rng, &history);
  save_history(&results, &history);
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
