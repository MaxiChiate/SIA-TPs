// Dependency-free tests: `make test`. Each test_* function reports through check(); the exit code is
// nonzero if any check failed.

#include "../activation/activation.h"
#include "../io/config.h"
#include "../io/dataset.h"
#include "../network.h"
#include "../optimizer/optimizer.h"
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

static Network new_network_with(int n_layers, const int sizes[], const char * activation,
                                const OptimizerConfig * optimizer, unsigned int seed) {
  Rng rng = rng_new(seed);
  return network_new(n_layers, sizes, activation_find(activation), optimizer, random_weight, &rng);
}

// With plain gradient descent
static Network new_network(int n_layers, const int sizes[], const char * activation, double eta, unsigned int seed) {
  OptimizerConfig gd = { .name = "gd", .eta = eta };
  return new_network_with(n_layers, sizes, activation, &gd, seed);
}

// One of each, with the typical hyperparameters of class 12.1
static const OptimizerConfig TEST_OPTIMIZERS[] = {
  { .name = "gd",       .eta = 0.1 },
  { .name = "momentum", .eta = 0.01, .momentum = 0.9 },
  { .name = "rmsprop",  .eta = 0.01, .decay = 0.9, .epsilon = 1e-8 },
  { .name = "adam",     .eta = 0.01, .beta1 = 0.9, .beta2 = 0.999, .epsilon = 1e-8 },
};

#define N_TEST_OPTIMIZERS ((int) (sizeof(TEST_OPTIMIZERS) / sizeof(TEST_OPTIMIZERS[0])))

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


static void test_rng_shuffle(void) {
  int a[20], b[20], c[20];
  for (int i = 0; i < 20; i++) a[i] = b[i] = c[i] = i;
  Rng ra = rng_new(5), rb = rng_new(5), rc = rng_new(6);
  rng_shuffle(&ra, a, 20);
  rng_shuffle(&rb, b, 20);
  rng_shuffle(&rc, c, 20);
  check(memcmp(a, b, sizeof(a)) == 0); // same seed, same order
  check(memcmp(a, c, sizeof(a)) != 0);

  int seen[20] = {0}, moved = 0;
  for (int i = 0; i < 20; i++) {
    seen[a[i]]++;
    if (a[i] != i) moved = 1;
  }
  int is_permutation = 1;
  for (int i = 0; i < 20; i++) if (seen[i] != 1) is_permutation = 0;
  check(is_permutation);
  check(moved);

  // Each of the 3! orders of three values comes up about a sixth of the time
  int counts[3][3] = {{0}};
  Rng rng = rng_new(1);
  for (int t = 0; t < 6000; t++) {
    int values[] = {0, 1, 2};
    rng_shuffle(&rng, values, 3);
    for (int i = 0; i < 3; i++) counts[i][values[i]]++;
  }
  for (int i = 0; i < 3; i++) for (int v = 0; v < 3; v++) check(abs(counts[i][v] - 2000) < 200);

  int one[] = {7};
  rng_shuffle(&rng, one, 1);
  check(one[0] == 7);
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

  const Activation * relu = activation_find("relu");
  check(!relu->discrete);
  check_close(relu->theta(-3.0), 0.0, 0);
  check_close(relu->theta(0.0), 0.0, 0);
  check_close(relu->theta(2.5), 2.5, 0);
  check_close(relu->theta_prime(-3.0), 0.0, 0);
  check_close(relu->theta_prime(0.0), 0.0, 0); // the kink: taken as 0
  check_close(relu->theta_prime(2.5), 1.0, 0);
  for (double h = -2.0; h <= 2.0; h += 0.5) {
    if (h == 0.0) continue; // not differentiable there
    double numeric = (relu->theta(h + 1e-6) - relu->theta(h - 1e-6)) / 2e-6;
    check_close(relu->theta_prime(h), numeric, 1e-6);
  }

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
  network_train(network, input, zeta, 1, 1, 1, NULL, NULL, NULL);
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
  const char * activations[] = {"tanh", "logistic", "relu"};
  for (int a = 0; a < 3; a++) {
    int sizes[] = {2, 3, 2, 1};
    double eta = 0.01;
    Network network = new_network(3, sizes, activations[a], eta, 5);
    int n = network_n_weights(network);
    double weights[n], trained[n];
    network_get_weights(network, weights);
    double zetas[] = {0.1, 0.9, 0.8, 0.2};

    network_train(network, XOR_INPUTS, zetas, 4, 1, 4, NULL, NULL, NULL);
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
  network_train(a, XOR_INPUTS, XOR_ZETAS, 4, 5, 4, NULL, NULL, NULL);
  network_train(b, reversed_inputs, reversed_zetas, 4, 5, 4, NULL, NULL, NULL);
  double wa[9], wb[9];
  network_get_weights(a, wa);
  network_get_weights(b, wb);
  for (int i = 0; i < 9; i++) check_close(wa[i], wb[i], 1e-12);

  // online is order dependent: it doesn't give the same weights
  Network c = new_network(2, sizes, "tanh", 0.1, 3), d = new_network(2, sizes, "tanh", 0.1, 3);
  network_train(c, XOR_INPUTS, XOR_ZETAS, 4, 5, 1, NULL, NULL, NULL);
  network_train(d, reversed_inputs, reversed_zetas, 4, 5, 1, NULL, NULL, NULL);
  network_get_weights(c, wa);
  network_get_weights(d, wb);
  check(fabs(wa[0] - wb[0]) > 1e-9);

  network_free(a); network_free(b); network_free(c); network_free(d);
}


static void test_and_with_sign_converges(void) {
  int sizes[] = {2, 1};
  Network network = new_network(1, sizes, "sign", 0.1, 1);
  network_train(network, XOR_INPUTS, AND_ZETAS, 4, 100, 1, NULL, NULL, NULL);
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
  network_train(network, inputs, zetas, 50, 200, 1, NULL, NULL, NULL);
  check(network_error(network, inputs, zetas, 50).mse < 1e-6);
  network_free(network);
}


static void test_xor_multilayer_converges(void) {
  int sizes[] = {2, 3, 2, 1};
  Network network = new_network(3, sizes, "tanh", 0.1, 1);
  network_train(network, XOR_INPUTS, XOR_ZETAS, 4, 3000, 1, NULL, NULL, NULL);
  check(network_error(network, XOR_INPUTS, XOR_ZETAS, 4).mse < 0.01);
  check(network_misclassified(network, XOR_INPUTS, XOR_ZETAS, 4) == 0);
  network_free(network);
}


static void test_same_seed_same_result(void) {
  int sizes[] = {2, 3, 1};
  Network a = new_network(2, sizes, "tanh", 0.1, 9), b = new_network(2, sizes, "tanh", 0.1, 9);
  Network c = new_network(2, sizes, "tanh", 0.1, 10);
  network_train(a, XOR_INPUTS, XOR_ZETAS, 4, 50, 1, NULL, NULL, NULL);
  network_train(b, XOR_INPUTS, XOR_ZETAS, 4, 50, 1, NULL, NULL, NULL);
  network_train(c, XOR_INPUTS, XOR_ZETAS, 4, 50, 1, NULL, NULL, NULL);
  double wa[13], wb[13], wc[13];
  network_get_weights(a, wa);
  network_get_weights(b, wb);
  network_get_weights(c, wc);
  check(memcmp(wa, wb, sizeof(wa)) == 0);
  check(memcmp(wa, wc, sizeof(wa)) != 0);
  network_free(a); network_free(b); network_free(c);
}


static void test_shuffled_training(void) {
  int sizes[] = {2, 3, 1};
  double wa[13], wb[13], wc[13], wd[13];

  // Same shuffle seed, same result; another seed, or no shuffling, gives a different one
  Network a = new_network(2, sizes, "tanh", 0.1, 9), b = new_network(2, sizes, "tanh", 0.1, 9);
  Network c = new_network(2, sizes, "tanh", 0.1, 9), d = new_network(2, sizes, "tanh", 0.1, 9);
  Rng ra = rng_new(1), rb = rng_new(1), rc = rng_new(2);
  network_train(a, XOR_INPUTS, XOR_ZETAS, 4, 20, 1, &ra, NULL, NULL);
  network_train(b, XOR_INPUTS, XOR_ZETAS, 4, 20, 1, &rb, NULL, NULL);
  network_train(c, XOR_INPUTS, XOR_ZETAS, 4, 20, 1, &rc, NULL, NULL);
  network_train(d, XOR_INPUTS, XOR_ZETAS, 4, 20, 1, NULL, NULL, NULL);
  network_get_weights(a, wa);
  network_get_weights(b, wb);
  network_get_weights(c, wc);
  network_get_weights(d, wd);
  check(memcmp(wa, wb, sizeof(wa)) == 0);
  check(memcmp(wa, wc, sizeof(wa)) != 0);
  check(memcmp(wa, wd, sizeof(wa)) != 0);
  network_free(a); network_free(b); network_free(c); network_free(d);

  // Full batch sums Δw over every sample, so shuffling must change nothing: each sample is visited
  // exactly once per epoch
  a = new_network(2, sizes, "tanh", 0.1, 3);
  b = new_network(2, sizes, "tanh", 0.1, 3);
  Rng rng = rng_new(4);
  network_train(a, XOR_INPUTS, XOR_ZETAS, 4, 5, 4, &rng, NULL, NULL);
  network_train(b, XOR_INPUTS, XOR_ZETAS, 4, 5, 4, NULL, NULL, NULL);
  network_get_weights(a, wa);
  network_get_weights(b, wb);
  for (int i = 0; i < 13; i++) check_close(wa[i], wb[i], 1e-12);
  network_free(a); network_free(b);

  int xor_sizes[] = {2, 3, 2, 1};
  Network xor_network = new_network(3, xor_sizes, "tanh", 0.1, 1);
  Rng xor_rng = rng_new(1);
  network_train(xor_network, XOR_INPUTS, XOR_ZETAS, 4, 3000, 1, &xor_rng, NULL, NULL);
  check(network_misclassified(xor_network, XOR_INPUTS, XOR_ZETAS, 4) == 0);
  network_free(xor_network);
}


static void test_relu_network_learns(void) {
  int sizes[] = {2, 4, 1};
  Network network = new_network(2, sizes, "relu", 0.05, 2);
  const double inputs[] = {0, 0, 0, 1, 1, 0, 1, 1};
  const double zetas[] = {0, 1, 1, 0}; // XOR
  Rng rng = rng_new(1);
  double before = network_error(network, inputs, zetas, 4).mse;
  network_train(network, inputs, zetas, 4, 2000, 1, &rng, NULL, NULL);
  check(network_error(network, inputs, zetas, 4).mse < before);
  check(network_error(network, inputs, zetas, 4).mse < 0.05);
  network_free(network);
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
  int run = network_train(network, XOR_INPUTS, AND_ZETAS, 4, 100, 1, NULL, stop_at_three, &calls);
  check(run == 3);
  check(calls == 3);

  calls = 0;
  check(network_train(network, XOR_INPUTS, AND_ZETAS, 4, 2, 1, NULL, stop_at_three, &calls) == 2);
  network_free(network);
}


static void test_error_metrics_by_hand(void) {
  int sizes[] = {1, 1};
  OptimizerConfig gd = { .name = "gd", .eta = 0.1 };
  Network network = network_new(1, sizes, activation_find("lineal"), &gd, zero_weight, NULL); // O = 0 always
  double inputs[] = {0, 0, 0}, zetas[] = {1.0, -2.0, 0.0};
  ErrorMetrics error = network_error(network, inputs, zetas, 3);
  check_close(error.energy, 0.5 * 5.0, 1e-12);
  check_close(error.mse, 5.0 / 3, 1e-12);
  check_close(error.mae, 1.0, 1e-12);
  check_close(error.max_abs_error, 2.0, 1e-12);
  network_free(network);
}


// ---------- optimizer ----------


static void test_gd_step_by_hand(void) {
  OptimizerConfig config = { .name = "gd", .eta = 0.1 };
  Optimizer optimizer = optimizer_new(&config, 2);
  double weights[] = {1.0, 1.0}, descent[] = {1.0, -2.0};
  optimizer_step(optimizer, weights, descent); // Δw = eta * descent
  check_close(weights[0], 1.1, 1e-12);
  check_close(weights[1], 0.8, 1e-12);

  optimizer_set_eta(optimizer, 0.5);
  check_close(optimizer_eta(optimizer), 0.5, 1e-12);
  optimizer_step(optimizer, weights, descent);
  check_close(weights[0], 1.6, 1e-12);
  check_close(weights[1], -0.2, 1e-12);
  optimizer_free(optimizer);

  OptimizerConfig unknown = { .name = "nope", .eta = 0.1 };
  check(optimizer_new(&unknown, 2) == NULL);
}


// The optimizer on its own, no network: f(w) = 1/2 (w - 3)^2, whose descent direction is -f'(w) = 3 - w
static void test_gd_minimizes_a_quadratic(void) {
  OptimizerConfig config = { .name = "gd", .eta = 0.1 };
  Optimizer optimizer = optimizer_new(&config, 1);
  double w[] = {0.0};
  for (int t = 0; t < 300; t++) {
    double descent[] = {3.0 - w[0]};
    optimizer_step(optimizer, w, descent);
  }
  check_close(w[0], 3.0, 1e-9);
  optimizer_free(optimizer);
}


// One weight starting at 0: steps[t] gets the Δw of each update with the given descent directions
static void steps_on_one_weight(const OptimizerConfig * config, const double descents[], int n_steps, double steps[]) {
  Optimizer optimizer = optimizer_new(config, 1);
  double w[] = {0.0};
  for (int t = 0; t < n_steps; t++) {
    double before = w[0];
    optimizer_step(optimizer, w, &descents[t]);
    steps[t] = w[0] - before;
  }
  optimizer_free(optimizer);
}


// The numbers of the momentum example in class 12.1: eta = 0.1, alpha = 0.9
static void test_momentum_steps_by_hand(void) {
  OptimizerConfig config = { .name = "momentum", .eta = 0.1, .momentum = 0.9 };
  double steps[4];

  double constant[] = {1, 1, 1, 1}; // the steps add up, towards eta / (1 - alpha) = 1
  steps_on_one_weight(&config, constant, 4, steps);
  check_close(steps[0], 0.1, 1e-12);
  check_close(steps[1], 0.19, 1e-12);
  check_close(steps[2], 0.271, 1e-12);
  check_close(steps[3], 0.3439, 1e-12);

  double alternating[] = {1, -1, 1, -1}; // they cancel out, towards eta / (1 + alpha) in size
  steps_on_one_weight(&config, alternating, 4, steps);
  check_close(steps[0], 0.1, 1e-12);
  check_close(steps[1], -0.01, 1e-12);
  check_close(steps[2], 0.091, 1e-12);
  check_close(steps[3], -0.0181, 1e-12);
}


// With alpha = 0 nothing carries over: every step is plain gradient descent
static void test_momentum_without_alpha_is_gd(void) {
  OptimizerConfig momentum = { .name = "momentum", .eta = 0.05, .momentum = 0.0 };
  OptimizerConfig gd = { .name = "gd", .eta = 0.05 };
  Rng rng = rng_new(3);
  double descents[20], momentum_steps[20], gd_steps[20];
  for (int t = 0; t < 20; t++) descents[t] = rng_uniform(&rng) - 0.5;
  steps_on_one_weight(&momentum, descents, 20, momentum_steps);
  steps_on_one_weight(&gd, descents, 20, gd_steps);
  for (int t = 0; t < 20; t++) check_close(momentum_steps[t], gd_steps[t], 1e-15);
}


// S starts at 0, so after one step S = (1 - gamma) d^2 and the step is eta / sqrt(1 - gamma) = 3.16 eta
static void test_rmsprop_first_step(void) {
  OptimizerConfig config = { .name = "rmsprop", .eta = 0.001, .decay = 0.9, .epsilon = 1e-8 };
  double descent[] = {2.0}, step[1];
  steps_on_one_weight(&config, descent, 1, step);
  check_close(step[0], 0.001 / sqrt(0.1), 1e-9);
}


// With the bias correction the first step is eta whatever the size of the gradient, and it goes the way
// of the descent direction (the paper's minus sign is already in descent = -dE/dw)
static void test_adam_first_step(void) {
  OptimizerConfig config = { .name = "adam", .eta = 0.001, .beta1 = 0.9, .beta2 = 0.999, .epsilon = 1e-8 };
  Optimizer optimizer = optimizer_new(&config, 4);
  double weights[] = {0, 0, 0, 0}, descent[] = {100.0, 1.0, 0.01, -1.0};
  optimizer_step(optimizer, weights, descent);
  check_close(weights[0], 0.001, 1e-8);
  check_close(weights[1], 0.001, 1e-8);
  check_close(weights[2], 0.001, 1e-8);
  check_close(weights[3], -0.001, 1e-8);
  optimizer_free(optimizer);
}


static double minimize_quadratic(const OptimizerConfig * config, int n_steps) {
  Optimizer optimizer = optimizer_new(config, 1);
  double w[] = {0.0};
  for (int t = 0; t < n_steps; t++) {
    double descent[] = {3.0 - w[0]};
    optimizer_step(optimizer, w, descent);
  }
  optimizer_free(optimizer);
  return w[0];
}


// Every optimizer reaches the minimum of f(w) = 1/2 (w - 3)^2 with no network around. rmsprop and adam move
// each weight about eta per step even next to the minimum, so with a fixed eta they end up hovering around
// it within a few eta instead of settling on it.
static void test_optimizers_minimize_a_quadratic(void) {
  OptimizerConfig momentum = { .name = "momentum", .eta = 0.1, .momentum = 0.9 };
  OptimizerConfig rmsprop = { .name = "rmsprop", .eta = 0.01, .decay = 0.9, .epsilon = 1e-8 };
  OptimizerConfig adam = { .name = "adam", .eta = 0.01, .beta1 = 0.9, .beta2 = 0.999, .epsilon = 1e-8 };
  check_close(minimize_quadratic(&momentum, 1000), 3.0, 1e-6);
  check_close(minimize_quadratic(&rmsprop, 3000), 3.0, 0.05);
  check_close(minimize_quadratic(&adam, 3000), 3.0, 0.05);
}


// Inside a network, with every optimizer: the same seed gives the same weights, full batch doesn't depend on
// the order of the samples (the descent is summed before the optimizer sees it), and the weights do move
static void test_optimizers_in_a_network(void) {
  int sizes[] = {2, 2, 1};
  const double reversed_inputs[] = {1, 1, 1, -1, -1, 1, -1, -1};
  const double reversed_zetas[] = {-1, 1, 1, -1};
  for (int k = 0; k < N_TEST_OPTIMIZERS; k++) {
    const OptimizerConfig * optimizer = &TEST_OPTIMIZERS[k];
    Network a = new_network_with(2, sizes, "tanh", optimizer, 3);
    Network b = new_network_with(2, sizes, "tanh", optimizer, 3);
    Network reversed = new_network_with(2, sizes, "tanh", optimizer, 3);
    double initial[9], wa[9], wb[9], wr[9];
    network_get_weights(a, initial);

    network_train(a, XOR_INPUTS, XOR_ZETAS, 4, 20, 4, NULL, NULL, NULL);
    network_train(b, XOR_INPUTS, XOR_ZETAS, 4, 20, 4, NULL, NULL, NULL);
    network_train(reversed, reversed_inputs, reversed_zetas, 4, 20, 4, NULL, NULL, NULL);
    network_get_weights(a, wa);
    network_get_weights(b, wb);
    network_get_weights(reversed, wr);

    check(memcmp(wa, wb, sizeof(wa)) == 0);
    for (int i = 0; i < 9; i++) check_close(wa[i], wr[i], 1e-12);
    check(memcmp(wa, initial, sizeof(wa)) != 0);
    network_free(a); network_free(b); network_free(reversed);
  }
}


// Every optimizer lowers the error of a net that can solve XOR (the one GD solves in "XOR [2,3,2,1] converges").
// Only lower, not solved: any of them may stop at a local minimum, but a step with the wrong sign makes it grow.
static void test_optimizers_learn_xor(void) {
  int sizes[] = {2, 3, 2, 1};
  for (int k = 0; k < N_TEST_OPTIMIZERS; k++) {
    Network network = new_network_with(3, sizes, "tanh", &TEST_OPTIMIZERS[k], 1);
    double before = network_error(network, XOR_INPUTS, XOR_ZETAS, 4).mse;
    network_train(network, XOR_INPUTS, XOR_ZETAS, 4, 1000, 1, NULL, NULL, NULL);
    check(network_error(network, XOR_INPUTS, XOR_ZETAS, 4).mse < before);
    network_free(network);
  }
}


static void test_network_eta(void) {
  int sizes[] = {2, 3, 1};
  Network network = new_network(2, sizes, "tanh", 0.1, 1);
  check_close(network_eta(network), 0.1, 1e-12);
  network_set_eta(network, 0.02);
  check_close(network_eta(network), 0.02, 1e-12);
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


static void test_dataset_split(void) {
  char text[512] = "x1,zeta\n";
  for (int i = 0; i < 10; i++) {
    char row[32];
    snprintf(row, sizeof(row), "%d,%d\n", i, 100 + i); // the input says which sample it is
    strcat(text, row);
  }
  write_tmp(text);
  Dataset source = dataset_load(TMP_FILE);
  check(source != NULL);
  if (source == NULL) return;

  Dataset train, validation, again, other;
  Rng rng = rng_new(3), same = rng_new(3), different = rng_new(4);
  check(dataset_split(source, 0.3, &rng, &train, &validation));
  check(dataset_n_samples(train) == 7 && dataset_n_samples(validation) == 3);
  check(dataset_n_inputs(validation) == 1 && dataset_n_outputs(validation) == 1);

  // Every sample lands on exactly one side, with its own zeta, and each side keeps the source's order
  int seen[10] = {0}, ordered = 1, paired = 1;
  const Dataset sides[] = {train, validation};
  for (int s = 0; s < 2; s++) {
    for (int i = 0; i < dataset_n_samples(sides[s]); i++) {
      int id = (int) dataset_inputs(sides[s])[i];
      seen[id]++;
      if (dataset_zetas(sides[s])[i] != 100 + id) paired = 0;
      if (i > 0 && dataset_inputs(sides[s])[i] <= dataset_inputs(sides[s])[i - 1]) ordered = 0;
    }
  }
  int partition = 1;
  for (int i = 0; i < 10; i++) if (seen[i] != 1) partition = 0;
  check(partition && paired && ordered);

  check(dataset_split(source, 0.3, &same, &again, &other));
  check(memcmp(dataset_inputs(validation), dataset_inputs(other), 3 * sizeof(double)) == 0);
  dataset_free(again);
  dataset_free(other);
  check(dataset_split(source, 0.3, &different, &again, &other));
  check(memcmp(dataset_inputs(validation), dataset_inputs(other), 3 * sizeof(double)) != 0);
  dataset_free(again);
  dataset_free(other);
  dataset_free(train);
  dataset_free(validation);

  // Neither side is ever empty
  Rng edge = rng_new(1);
  check(dataset_split(source, 0.001, &edge, &train, &validation));
  check(dataset_n_samples(validation) == 1 && dataset_n_samples(train) == 9);
  dataset_free(train);
  dataset_free(validation);
  check(dataset_split(source, 0.999, &edge, &train, &validation));
  check(dataset_n_samples(train) == 1 && dataset_n_samples(validation) == 9);
  dataset_free(train);
  dataset_free(validation);

  fprintf(stderr, "  (expected errors follow)\n");
  check(!dataset_split(source, 0.0, &edge, &train, &validation));
  check(!dataset_split(source, 1.0, &edge, &train, &validation));
  dataset_free(source);

  write_tmp("1,2\n");
  source = dataset_load(TMP_FILE);
  check(source != NULL && !dataset_split(source, 0.5, &edge, &train, &validation));
  if (source != NULL) dataset_free(source);
}


static const char * CONFIG_BASE = "\"train_dataset\":\"a\",\"validation_dataset\":\"b\",\"activation\":\"tanh\","
                                  "\"eta\":0.1,\"epochs\":10,\"batch_size\":2,\"hidden_layers\":[3,2],\"seed\":4";

static int load_config_with(const char * extra, Config * config) {
  char text[1024];
  snprintf(text, sizeof(text), "{%s%s}", CONFIG_BASE, extra);
  write_tmp(text);
  return config_load(TMP_FILE, config);
}

// Same config, but without validation_dataset
static int load_config_without_validation_dataset(const char * extra, Config * config) {
  char text[1024];
  snprintf(text, sizeof(text), "{\"train_dataset\":\"a\",\"activation\":\"tanh\",\"eta\":0.1,\"epochs\":10,"
           "\"batch_size\":2,\"hidden_layers\":[3,2],\"seed\":4%s}", extra);
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

  check(!config.shuffle && config.validation_split == 0 && config.split_seed == 0);
  check(strcmp(config.validation_dataset, "b") == 0);

  check(load_config_with(",\"shuffle\":true", &config) && config.shuffle == 1);
  check(load_config_with(",\"shuffle\":false", &config) && config.shuffle == 0);

  check(load_config_without_validation_dataset(",\"validation_split\":0.25,\"split_seed\":7", &config));
  check_close(config.validation_split, 0.25, 0);
  check(config.split_seed == 7 && config.validation_dataset[0] == '\0');

  fprintf(stderr, "  (expected errors follow)\n");
  check(!load_config_with(",\"shuffle\":1", &config));
  check(!load_config_with(",\"validation_split\":0.25,\"split_seed\":7", &config)); // both sources
  check(!load_config_without_validation_dataset("", &config)); // neither
  check(!load_config_without_validation_dataset(",\"validation_split\":0.25", &config)); // no split_seed
  check(!load_config_with(",\"split_seed\":7", &config)); // split_seed without a split
  check(!load_config_without_validation_dataset(",\"validation_split\":0,\"split_seed\":7", &config));
  check(!load_config_without_validation_dataset(",\"validation_split\":1,\"split_seed\":7", &config));
  check(!load_config_without_validation_dataset(",\"validation_split\":1.5,\"split_seed\":7", &config));
  check(!load_config_with(",\"tolerance\":-1", &config));
  check(!load_config_with(",\"nope\":1", &config));
  write_tmp("{\"eta\":0.1}");
  check(!config_load(TMP_FILE, &config)); // required keys missing
  write_tmp("{\"eta\":");
  check(!config_load(TMP_FILE, &config));
}


// Each optimizer with exactly the hyperparameters it reads
static const char * OPTIMIZER_CONFIGS[][2] = {
  { "gd",       ",\"optimizer\":\"gd\"" },
  { "momentum", ",\"optimizer\":\"momentum\",\"momentum\":0.9" },
  { "rmsprop",  ",\"optimizer\":\"rmsprop\",\"rmsprop_decay\":0.9,\"optimizer_epsilon\":1e-8" },
  { "adam",     ",\"optimizer\":\"adam\",\"adam_beta1\":0.9,\"adam_beta2\":0.999,\"optimizer_epsilon\":1e-8" },
};

static void test_optimizer_config(void) {
  Config config;
  check(load_config_with("", &config) && strcmp(config.optimizer, "gd") == 0); // the default

  // Every optimizer the config accepts exists in the optimizer module
  for (int i = 0; i < 4; i++) {
    check(load_config_with(OPTIMIZER_CONFIGS[i][1], &config));
    check(strcmp(config.optimizer, OPTIMIZER_CONFIGS[i][0]) == 0);
    OptimizerConfig optimizer = { .name = config.optimizer, .eta = config.eta };
    Optimizer created = optimizer_new(&optimizer, 1);
    check(created != NULL);
    if (created != NULL) optimizer_free(created);
  }
  check(load_config_with(OPTIMIZER_CONFIGS[3][1], &config));
  check_close(config.adam_beta1, 0.9, 0);
  check_close(config.adam_beta2, 0.999, 0);
  check_close(config.optimizer_epsilon, 1e-8, 0);
  check(load_config_with(",\"optimizer\":\"momentum\",\"momentum\":0", &config)); // alpha = 0 is allowed

  fprintf(stderr, "  (expected errors follow)\n");
  check(!load_config_with(",\"optimizer\":\"nope\"", &config));
  check(!load_config_with(",\"optimizer\":\"\"", &config));
  check(!load_config_with(",\"optimizer\":\"momentum\"", &config)); // missing alpha, suggests 0.9
  check(!load_config_with(",\"optimizer\":\"adam\",\"adam_beta1\":0.9,\"optimizer_epsilon\":1e-8", &config));
  check(!load_config_with(",\"momentum\":0.9", &config)); // belongs to momentum, not to gd
  check(!load_config_with(",\"optimizer\":\"adam\",\"adam_beta1\":0.9,\"adam_beta2\":0.999,"
                          "\"optimizer_epsilon\":1e-8,\"momentum\":0.9", &config));
  check(!load_config_with(",\"optimizer\":\"momentum\",\"momentum\":1", &config));
  check(!load_config_with(",\"optimizer\":\"momentum\",\"momentum\":-0.1", &config));
  check(!load_config_with(",\"optimizer\":\"rmsprop\",\"rmsprop_decay\":0.9,\"optimizer_epsilon\":0", &config));
}


typedef void (*Test)(void);

int main(void) {
  struct { const char * name; Test run; } tests[] = {
    { "rng", test_rng },
    { "rng shuffle", test_rng_shuffle },
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
    { "shuffled training", test_shuffled_training },
    { "relu network learns", test_relu_network_learns },
    { "callback stops training", test_training_stops_when_callback_asks },
    { "gd step by hand", test_gd_step_by_hand },
    { "gd minimizes a quadratic", test_gd_minimizes_a_quadratic },
    { "momentum steps by hand", test_momentum_steps_by_hand },
    { "momentum without alpha is gd", test_momentum_without_alpha_is_gd },
    { "rmsprop first step", test_rmsprop_first_step },
    { "adam first step", test_adam_first_step },
    { "optimizers minimize a quadratic", test_optimizers_minimize_a_quadratic },
    { "optimizers in a network", test_optimizers_in_a_network },
    { "optimizers learn XOR", test_optimizers_learn_xor },
    { "network eta get/set", test_network_eta },
    { "dataset loading", test_dataset_loading },
    { "dataset split", test_dataset_split },
    { "config loading", test_config_loading },
    { "optimizer config", test_optimizer_config },
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
