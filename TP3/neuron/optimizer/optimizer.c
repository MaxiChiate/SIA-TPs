#include "optimizer.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef void (*StepFunction)(Optimizer optimizer, double weights[], const double descent[]);

struct optimizer {
  OptimizerConfig config;
  StepFunction step;
  int n_weights;
};


// Plain gradient descent: Δw = eta * descent
static void gd_step(Optimizer optimizer, double weights[], const double descent[]) {
  for (int i = 0; i < optimizer->n_weights; i++) {
    weights[i] += optimizer->config.eta * descent[i];
  }
}


typedef struct {
  const char * name;
  StepFunction step;
} OptimizerKind;

static const OptimizerKind OPTIMIZERS[] = {
  { "gd", gd_step },
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

  Optimizer optimizer = malloc(sizeof(struct optimizer));
  if (optimizer == NULL) {
    fprintf(stderr, "FATAL: couldn't allocate optimizer\n");
    abort();
  }
  optimizer->config = *config;
  optimizer->config.name = kind->name; // the caller's string may not outlive the optimizer
  optimizer->step = kind->step;
  optimizer->n_weights = n_weights;

  return optimizer;

}


void optimizer_free(Optimizer optimizer) {
  free(optimizer);
}


void optimizer_step(Optimizer optimizer, double weights[], const double descent[]) {
  optimizer->step(optimizer, weights, descent);
}


double optimizer_eta(const Optimizer optimizer) {
  return optimizer->config.eta;
}


void optimizer_set_eta(Optimizer optimizer, double eta) {
  optimizer->config.eta = eta;
}


const char * optimizer_names(void) {
  return "gd";
}
