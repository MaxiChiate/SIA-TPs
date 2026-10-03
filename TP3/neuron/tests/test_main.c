// Dependency-free tests: `make test`. Each test_* function reports through check(); the exit code is
// nonzero if any check failed.

#include "../activation/activation.h"
#include "../io/config.h"
#include "../io/dataset.h"
#include "../network.h"
#include "../rng.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int checks = 0;
static int failures = 0;

#define check(condition) check_at((condition), #condition, __FILE__, __LINE__)
#define check_close(actual, expected, tolerance) \
  check_close_at((actual), (expected), (tolerance), #actual, __FILE__, __LINE__)

static void check_at(int condition, const char * text, const char * file, int line) {
  checks++;
  if (!condition) {
    failures++;
    fprintf(stderr, "  FAIL %s:%d: %s\n", file, line, text);
  }
}

static void check_close_at(double actual, double expected, double tolerance, const char * text, const char * file,
                           int line) {
  checks++;
  if (!(fabs(actual - expected) <= tolerance)) {
    failures++;
    fprintf(stderr, "  FAIL %s:%d: %s = %.10g, expected %.10g (±%g)\n", file, line, text, actual, expected, tolerance);
  }
}

static double zero_weight(void * context) {
  (void) context;
  return 0.0;
}

static double random_weight(void * context) {
  return rng_uniform(context) - 0.5;
}

static Network new_network(int n_layers, const int sizes[], const char * activation, double eta, unsigned int seed) {
  Rng rng = rng_new(seed);
  return network_new(n_layers, sizes, activation_find(activation), eta, random_weight, &rng);
}

static void set_weights(Network network, const double * weights) {
  network_set_weights(network, weights);
}

static const double XOR_INPUTS[] = {-1, -1, -1, 1, 1, -1, 1, 1};
static const double XOR_ZETAS[] = {-1, 1, 1, -1};
static const double AND_ZETAS[] = {-1, -1, -1, 1};


// ---------- rng ----------

static void test_rng(void) {
  Rng a = rng_new(7), b = rng_new(7), c = rng_new(8);
  int all_equal = 1, differs = 0, in_range = 1;
  for (int i = 0; i < 1000; i++) {
    double x = rng_uniform(&a), y = rng_uniform(&b), z = rng_uniform(&c);
    if (x != y) all_equal = 0;
    if (x != z) differs = 1;
    if (x < 0.0 || x >= 1.0) in_range = 0;
  }
  check(all_equal);
  check(differs);
  check(in_range);

  Rng rng = rng_new(1);
  double sum = 0;
  for (int i = 0; i < 100000; i++) sum += rng_uniform(&rng);
  check_close(sum / 100000, 0.5, 0.01);
}


// ---------- activations ----------

static void test_activations(void) {
  check(activation_find("nope") == NULL);

  const Activation * sign = activation_find("sign");
  check(sign->discrete);
  check_close(sign->theta(0.0), 1.0, 0);
  check_close(sign->theta(-0.1), -1.0, 0);
  check_close(sign->theta_prime(3.0), 1.0, 0); // Rosenblatt: the delta rule needs no special case

  const Activation * logistic = activation_find("logistic");
  check(!logistic->discrete);
  check_close(logistic->theta(0.0), 0.5, 1e-12);
  check_close(logistic->theta(1000.0), 1.0, 1e-12); // no overflow
  check_close(logistic->theta(-1000.0), 0.0, 1e-12);

  const char * smooth[] = {"lineal", "tanh", "logistic"};
  for (int i = 0; i < 3; i++) {
    const Activation * activation = activation_find(smooth[i]);
    for (double h = -2.0; h <= 2.0; h += 0.5) {
      double numeric = (activation->theta(h + 1e-6) - activation->theta(h - 1e-6)) / 2e-6;
      check_close(activation->theta_prime(h), numeric, 1e-6);
    }
  }
}


// ---------- network ----------

static void test_weights_roundtrip(void) {
  int sizes[] = {3, 4, 2};
  Network network = new_network(2, sizes, "tanh", 0.1, 1);
  check(network_n_weights(network) == 4 * 4 + 2 * 5);
  check(network_n_inputs(network) == 3 && network_n_outputs(network) == 2);

  double before[26], after[26];
  network_get_weights(network, before);
  Network other = new_network(2, sizes, "tanh", 0.1, 2);
  set_weights(other, before);
  network_get_weights(other, after);
  check(memcmp(before, after, sizeof(before)) == 0);

  network_free(network);
  network_free(other);
}


static void test_forward_by_hand(void) {
  int sizes[] = {2, 1};
  Network network = new_network(1, sizes, "lineal", 0.1, 1);
  double weights[] = {0.5, 2.0, -1.0}; // bias first
  set_weights(network, weights);
  double input[] = {1.0, 3.0}, output;
  network_predict(network, input, &output);
  check_close(output, 0.5 + 2.0 - 3.0, 1e-12);
  network_free(network);

  // 2-2-1 with tanh: hidden = tanh(w·x + b), output = tanh(...)
  int sizes2[] = {2, 2, 1};
  Network deep = new_network(2, sizes2, "tanh", 0.1, 1);
  double w2[] = {0.1, 0.2, 0.3, -0.1, 0.4, -0.2, 0.05, 0.6, -0.7};
  set_weights(deep, w2);
  double x[] = {1.0, -1.0};
  double h1 = tanh(0.1 + 0.2 - 0.3), h2 = tanh(-0.1 + 0.4 + 0.2);
  network_predict(deep, x, &output);
  check_close(output, tanh(0.05 + 0.6 * h1 - 0.7 * h2), 1e-12);
  network_free(deep);
}


static void test_single_neuron_update_by_hand(void) {
  int sizes[] = {2, 1};
  Network network = new_network(1, sizes, "lineal", 0.1, 1);
  double weights[] = {0.0, 0.0, 0.0};
  set_weights(network, weights);
  double input[] = {2.0, -1.0}, zeta[] = {1.0};
  network_train(network, input, zeta, 1, 1, 1, NULL, NULL);
  // O = 0, delta = 1, Δw = eta * delta * x
  double after[3];
  network_get_weights(network, after);
  check_close(after[0], 0.1, 1e-12);
  check_close(after[1], 0.2, 1e-12);
  check_close(after[2], -0.1, 1e-12);
  network_free(network);
}


static double energy(Network network, const double inputs[], const double zetas[], int n_samples) {
  return network_error(network, inputs, zetas, n_samples).energy;
}

// Full batch: one epoch changes the weights by -eta * dE/dw, with dE/dw taken numerically. This checks
// the whole backpropagation (hidden deltas included) against the definition of the gradient.
static void test_backpropagation_matches_numeric_gradient(void) {
  const char * activations[] = {"tanh", "logistic"};
  for (int a = 0; a < 2; a++) {
    int sizes[] = {2, 3, 2, 1};
    double eta = 0.01;
    Network network = new_network(3, sizes, activations[a], eta, 5);
    int n = network_n_weights(network);
    double weights[n], trained[n];
    network_get_weights(network, weights);
    double zetas[] = {0.1, 0.9, 0.8, 0.2};

    network_train(network, XOR_INPUTS, zetas, 4, 1, 4, NULL, NULL);
    network_get_weights(network, trained);

    for (int i = 0; i < n; i++) {
      double probe[n];
      memcpy(probe, weights, sizeof(probe));
      probe[i] = weights[i] + 1e-6;
      set_weights(network, probe);
      double up = energy(network, XOR_INPUTS, zetas, 4);
      probe[i] = weights[i] - 1e-6;
      set_weights(network, probe);
      double down = energy(network, XOR_INPUTS, zetas, 4);
      double gradient = (up - down) / 2e-6;
      check_close(trained[i] - weights[i], -eta * gradient, 1e-8);
    }
    network_free(network);
  }
}


// Full batch sums Δw over the epoch, so the order of the samples doesn't matter
static void test_full_batch_ignores_sample_order(void) {
  int sizes[] = {2, 2, 1};
  const double reversed_inputs[] = {1, 1, 1, -1, -1, 1, -1, -1};
  const double reversed_zetas[] = {-1, 1, 1, -1};
  Network a = new_network(2, sizes, "tanh", 0.1, 3), b = new_network(2, sizes, "tanh", 0.1, 3);
  network_train(a, XOR_INPUTS, XOR_ZETAS, 4, 5, 4, NULL, NULL);
  network_train(b, reversed_inputs, reversed_zetas, 4, 5, 4, NULL, NULL);
  double wa[9], wb[9];
  network_get_weights(a, wa);
  network_get_weights(b, wb);
  for (int i = 0; i < 9; i++) check_close(wa[i], wb[i], 1e-12);

  // online is order dependent: it doesn't give the same weights
  Network c = new_network(2, sizes, "tanh", 0.1, 3), d = new_network(2, sizes, "tanh", 0.1, 3);
  network_train(c, XOR_INPUTS, XOR_ZETAS, 4, 5, 1, NULL, NULL);
  network_train(d, reversed_inputs, reversed_zetas, 4, 5, 1, NULL, NULL);
  network_get_weights(c, wa);
  network_get_weights(d, wb);
  check(fabs(wa[0] - wb[0]) > 1e-9);

  network_free(a); network_free(b); network_free(c); network_free(d);
}


static void test_and_with_sign_converges(void) {
  int sizes[] = {2, 1};
  Network network = new_network(1, sizes, "sign", 0.1, 1);
  network_train(network, XOR_INPUTS, AND_ZETAS, 4, 100, 1, NULL, NULL);
  check(network_misclassified(network, XOR_INPUTS, AND_ZETAS, 4) == 0);

  Network untrained = new_network(1, sizes, "sign", 0.1, 1);
  double weights[] = {1.0, 0.0, 0.0}; // always +1: only (1, 1) is right
  set_weights(untrained, weights);
  check(network_misclassified(untrained, XOR_INPUTS, AND_ZETAS, 4) == 3);
  network_free(network);
  network_free(untrained);
}


static void test_line_with_lineal_converges(void) {
  int sizes[] = {1, 1};
  Network network = new_network(1, sizes, "lineal", 0.05, 1);
  double inputs[50], zetas[50];
  for (int i = 0; i < 50; i++) inputs[i] = zetas[i] = -1.0 + 2.0 * i / 49;
  network_train(network, inputs, zetas, 50, 200, 1, NULL, NULL);
  check(network_error(network, inputs, zetas, 50).mse < 1e-6);
  network_free(network);
}


static void test_xor_multilayer_converges(void) {
  int sizes[] = {2, 3, 2, 1};
  Network network = new_network(3, sizes, "tanh", 0.1, 1);
  network_train(network, XOR_INPUTS, XOR_ZETAS, 4, 3000, 1, NULL, NULL);
  check(network_error(network, XOR_INPUTS, XOR_ZETAS, 4).mse < 0.01);
  check(network_misclassified(network, XOR_INPUTS, XOR_ZETAS, 4) == 0);
  network_free(network);
}


static void test_same_seed_same_result(void) {
  int sizes[] = {2, 3, 1};
  Network a = new_network(2, sizes, "tanh", 0.1, 9), b = new_network(2, sizes, "tanh", 0.1, 9);
  Network c = new_network(2, sizes, "tanh", 0.1, 10);
  network_train(a, XOR_INPUTS, XOR_ZETAS, 4, 50, 1, NULL, NULL);
  network_train(b, XOR_INPUTS, XOR_ZETAS, 4, 50, 1, NULL, NULL);
  network_train(c, XOR_INPUTS, XOR_ZETAS, 4, 50, 1, NULL, NULL);
  double wa[13], wb[13], wc[13];
  network_get_weights(a, wa);
  network_get_weights(b, wb);
  network_get_weights(c, wc);
  check(memcmp(wa, wb, sizeof(wa)) == 0);
  check(memcmp(wa, wc, sizeof(wa)) != 0);
  network_free(a); network_free(b); network_free(c);
}


static int stop_at_three(int epoch, Network network, void * context) {
  (void) network;
  (*(int *) context)++;
  return epoch == 3;
}

static void test_training_stops_when_callback_asks(void) {
  int sizes[] = {2, 1};
  Network network = new_network(1, sizes, "sign", 0.1, 1);
  int calls = 0;
  int run = network_train(network, XOR_INPUTS, AND_ZETAS, 4, 100, 1, stop_at_three, &calls);
  check(run == 3);
  check(calls == 3);

  calls = 0;
  check(network_train(network, XOR_INPUTS, AND_ZETAS, 4, 2, 1, stop_at_three, &calls) == 2);
  network_free(network);
}


static void test_error_metrics_by_hand(void) {
  int sizes[] = {1, 1};
  Network network = network_new(1, sizes, activation_find("lineal"), 0.1, zero_weight, NULL); // O = 0 always
  double inputs[] = {0, 0, 0}, zetas[] = {1.0, -2.0, 0.0};
  ErrorMetrics error = network_error(network, inputs, zetas, 3);
  check_close(error.energy, 0.5 * 5.0, 1e-12);
  check_close(error.mse, 5.0 / 3, 1e-12);
  check_close(error.mae, 1.0, 1e-12);
  check_close(error.max_abs_error, 2.0, 1e-12);
  network_free(network);
}


// ---------- io ----------

static const char * TMP_FILE = "build/test_tmp";

static void write_tmp(const char * content) {
  FILE * file = fopen(TMP_FILE, "w");
  fputs(content, file);
  fclose(file);
}


static void test_dataset_loading(void) {
  write_tmp("x1,x2,zeta_0,zeta_1\n1,2,1,0\n\n3,4,0,1\n");
  Dataset dataset = dataset_load(TMP_FILE);
  check(dataset != NULL);
  if (dataset != NULL) {
    check(dataset_n_samples(dataset) == 2);
    check(dataset_n_inputs(dataset) == 2);
    check(dataset_n_outputs(dataset) == 2);
    check_close(dataset_inputs(dataset)[3], 4.0, 0);
    check_close(dataset_zetas(dataset)[1], 0.0, 0);
    dataset_free(dataset);
  }

  write_tmp("a,b,target\n1,2,3\n4,5,6\n"); // no zeta* names: the last column is the only zeta
  dataset = dataset_load(TMP_FILE);
  check(dataset != NULL && dataset_n_inputs(dataset) == 2 && dataset_n_outputs(dataset) == 1);
  if (dataset != NULL) dataset_free(dataset);

  write_tmp("1,2,3\n4,5\n"); // ragged rows
  fprintf(stderr, "  (expected error follows)\n");
  check(dataset_load(TMP_FILE) == NULL);
  check(dataset_load("build/does_not_exist.csv") == NULL);
}


static const char * CONFIG_BASE = "\"train_dataset\":\"a\",\"validation_dataset\":\"b\",\"activation\":\"tanh\","
                                  "\"eta\":0.1,\"epochs\":10,\"batch_size\":2,\"hidden_layers\":[3,2],\"seed\":4";

static int load_config_with(const char * extra, Config * config) {
  char text[1024];
  snprintf(text, sizeof(text), "{%s%s}", CONFIG_BASE, extra);
  write_tmp(text);
  return config_load(TMP_FILE, config);
}

static void test_config_loading(void) {
  Config config;
  check(load_config_with("", &config));
  check(strcmp(config.train_dataset, "a") == 0 && strcmp(config.activation, "tanh") == 0);
  check_close(config.eta, 0.1, 0);
  check(config.epochs == 10 && config.batch_size == 2 && config.seed == 4);
  check(config.n_hidden_layers == 2 && config.hidden_layers[0] == 3 && config.hidden_layers[1] == 2);
  check_close(config.tolerance, 0.0, 0); // optional keys default to zero / ""
  check(config.initial_weights[0] == '\0');

  check(load_config_with(",\"tolerance\":0.001,\"initial_weights\":\"results/x\"", &config));
  check_close(config.tolerance, 0.001, 0);
  check(strcmp(config.initial_weights, "results/x") == 0);

  fprintf(stderr, "  (expected errors follow)\n");
  check(!load_config_with(",\"tolerance\":-1", &config));
  check(!load_config_with(",\"nope\":1", &config));
  write_tmp("{\"eta\":0.1}");
  check(!config_load(TMP_FILE, &config)); // required keys missing
  write_tmp("{\"eta\":");
  check(!config_load(TMP_FILE, &config));
}


typedef void (*Test)(void);

int main(void) {
  struct { const char * name; Test run; } tests[] = {
    { "rng", test_rng },
    { "activations", test_activations },
    { "weights get/set roundtrip", test_weights_roundtrip },
    { "forward by hand", test_forward_by_hand },
    { "single neuron update by hand", test_single_neuron_update_by_hand },
    { "error metrics by hand", test_error_metrics_by_hand },
    { "backpropagation vs numeric gradient", test_backpropagation_matches_numeric_gradient },
    { "full batch ignores sample order", test_full_batch_ignores_sample_order },
    { "AND with sign converges", test_and_with_sign_converges },
    { "y = x with lineal converges", test_line_with_lineal_converges },
    { "XOR [2,3,2,1] converges", test_xor_multilayer_converges },
    { "same seed, same result", test_same_seed_same_result },
    { "callback stops training", test_training_stops_when_callback_asks },
    { "dataset loading", test_dataset_loading },
    { "config loading", test_config_loading },
  };
  int n_tests = (int) (sizeof(tests) / sizeof(tests[0]));

  for (int i = 0; i < n_tests; i++) {
    int failures_before = failures;
    tests[i].run();
    printf("%s %s\n", failures == failures_before ? "ok  " : "FAIL", tests[i].name);
  }
  remove(TMP_FILE);
  printf("%d checks, %d failed\n", checks, failures);
  return failures == 0 ? 0 : 1;
}
