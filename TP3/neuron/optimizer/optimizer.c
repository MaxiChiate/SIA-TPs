#include "optimizer.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef void (*StepFunction)(Optimizer optimizer, double weights[], const double descent[]);

typedef struct {
  const char * name;
  StepFunction step;
  int n_states; // per-weight arrays it keeps between steps
} OptimizerKind;

struct optimizer {
  OptimizerConfig config;
  const OptimizerKind * kind;
  int n_weights;
  long t;          // steps taken so far, for adam's bias correction
  double state[];  // kind->n_states arrays of n_weights values each, zero at the start
};


// Plain gradient descent: Δw = eta * descent
static void gd_step(Optimizer optimizer, double weights[], const double descent[]) {
  for (int i = 0; i < optimizer->n_weights; i++) {
    weights[i] += optimizer->config.eta * descent[i];
  }
}


// Δw(t+1) = eta * descent + alpha * Δw(t). The steps add up while the descent keeps its sign and cancel
// out when it flips.
static void momentum_step(Optimizer optimizer, double weights[], const double descent[]) {
  double * velocity = optimizer->state; // the previous Δw
  for (int i = 0; i < optimizer->n_weights; i++) {
    velocity[i] = optimizer->config.momentum * velocity[i] + optimizer->config.eta * descent[i];
    weights[i] += velocity[i];
  }
}


// S = gamma * S + (1 - gamma) * descent^2, Δw = eta * descent / sqrt(S + epsilon): each weight's step is
// divided by the typical size of its recent gradients, so every weight moves about eta.
static void rmsprop_step(Optimizer optimizer, double weights[], const double descent[]) {
  double * mean_square = optimizer->state;
  double decay = optimizer->config.decay;
  for (int i = 0; i < optimizer->n_weights; i++) {
    mean_square[i] = decay * mean_square[i] + (1.0 - decay) * descent[i] * descent[i];
    weights[i] += optimizer->config.eta * descent[i] / sqrt(mean_square[i] + optimizer->config.epsilon);
  }
}


// m averages the descent (momentum) and v its square (rmsprop). Both start at 0, so they're divided by
// 1 - beta^t to undo that pull towards 0 in the first steps. descent is -dE/dw, so the step adds where the
// paper subtracts: m flips sign along with the gradient and v doesn't.
static void adam_step(Optimizer optimizer, double weights[], const double descent[]) {
  double * mean = optimizer->state;
  double * mean_square = optimizer->state + optimizer->n_weights;
  double beta1 = optimizer->config.beta1, beta2 = optimizer->config.beta2;

  optimizer->t++;
  double mean_correction = 1.0 - pow(beta1, (double) optimizer->t);
  double mean_square_correction = 1.0 - pow(beta2, (double) optimizer->t);

  for (int i = 0; i < optimizer->n_weights; i++) {
    mean[i] = beta1 * mean[i] + (1.0 - beta1) * descent[i];
    mean_square[i] = beta2 * mean_square[i] + (1.0 - beta2) * descent[i] * descent[i];
    double corrected_mean = mean[i] / mean_correction;
    double corrected_mean_square = mean_square[i] / mean_square_correction;
    weights[i] += optimizer->config.eta * corrected_mean / (sqrt(corrected_mean_square) + optimizer->config.epsilon);
  }
}


static const OptimizerKind OPTIMIZERS[] = {
  { "gd",       gd_step,       0 },
  { "momentum", momentum_step, 1 },
  { "rmsprop",  rmsprop_step,  1 },
  { "adam",     adam_step,     2 },
};

#define N_OPTIMIZERS ((int) (sizeof(OPTIMIZERS) / sizeof(OPTIMIZERS[0])))


static const OptimizerKind * find_kind(const char * name) {
  for (int i = 0; i < N_OPTIMIZERS; i++) {
    if (strcmp(OPTIMIZERS[i].name, name) == 0) return &OPTIMIZERS[i];
  }
  return NULL;
}


Optimizer optimizer_new(const OptimizerConfig * config, int n_weights) {

  const OptimizerKind * kind = find_kind(config->name);
  if (kind == NULL) return NULL;

  size_t state_size = (size_t) kind->n_states * n_weights * sizeof(double);
  Optimizer optimizer = malloc(sizeof(struct optimizer) + state_size);
  if (optimizer == NULL) {
    fprintf(stderr, "FATAL: couldn't allocate optimizer\n");
    abort();
  }
  optimizer->config = *config;
  optimizer->config.name = kind->name; // the caller's string may not outlive the optimizer
  optimizer->kind = kind;
  optimizer->n_weights = n_weights;
  optimizer->t = 0;
  memset(optimizer->state, 0, state_size);

  return optimizer;

}


void optimizer_free(Optimizer optimizer) {
  free(optimizer);
}


void optimizer_step(Optimizer optimizer, double weights[], const double descent[]) {
  optimizer->kind->step(optimizer, weights, descent);
}


double optimizer_eta(const Optimizer optimizer) {
  return optimizer->config.eta;
}


void optimizer_set_eta(Optimizer optimizer, double eta) {
  optimizer->config.eta = eta;
}


const char * optimizer_names(void) {
  return "gd, momentum, rmsprop, adam";
}
