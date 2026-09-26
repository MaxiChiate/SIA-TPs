#include "activation/activation.h"
#include "io/config.h"
#include "io/dataset.h"
#include "neuron.h"
#include <stdarg.h>

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


static void init_random_weights(double weights[], int n_weights, unsigned int seed) {
  srand(seed);
  for (int i = 0; i < n_weights; i++) {
    weights[i] = (double) rand() / RAND_MAX - 0.5;
  }
}


static void print_weights(const char * title, const Neuron neuron) {
  int n_weights = neuron_get_n_inputs(neuron) + 1;
  double weights[n_weights];
  neuron_get_weights(neuron, weights);

  printf("%s:\n", title);
  for (int i = 0; i < n_weights; i++) {
    printf(i == 0 ? "%f" : ", %f", weights[i]);
  }
  printf("\n");
}


static void train_neuron(Neuron neuron, const Dataset train, int epochs) {
  int n_inputs = dataset_n_inputs(train);
  const double (*inputs)[n_inputs] = (const double (*)[n_inputs]) dataset_inputs(train);
  neuron_train_by_epoch(neuron, n_inputs, inputs, dataset_zetas(train), dataset_n_samples(train), epochs);
}


static void validate_neuron(const Neuron neuron, const Dataset validation) {
  int n_inputs = dataset_n_inputs(validation);
  const double (*inputs)[n_inputs] = (const double (*)[n_inputs]) dataset_inputs(validation);
  plot_neuron_validation(neuron, n_inputs, inputs, dataset_zetas(validation), dataset_n_samples(validation));
}


int main(int argc, char * argv[]) {

  Config config = load_config(config_path(argc, argv));
  const Activation * activation = load_activation(config.activation);
  Dataset train = load_dataset(config.train_dataset);
  Dataset validation = load_dataset(config.validation_dataset);
  int n_inputs = shared_n_inputs(train, validation);

  double initial_weights[n_inputs + 1];
  init_random_weights(initial_weights, n_inputs + 1, config.seed);
  Neuron neuron = neuron_new(n_inputs, activation->theta, activation->theta_prime, initial_weights, config.eta);

  print_weights("weights before training", neuron);
  train_neuron(neuron, train, config.epochs);
  print_weights("weights after training", neuron);
  validate_neuron(neuron, validation);

  neuron_free(neuron);
  dataset_free(train);
  dataset_free(validation);

  return 0;

}
