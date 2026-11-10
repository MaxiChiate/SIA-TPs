#include "neuron.h"

struct neuron {
  int n_inputs;
  double (*theta)(double);
  double (*theta_prime)(double);
  Optimizer optimizer; // its own, so per-weight state (momentum, adam) belongs to this neuron's weights
  double * gradient; // descent direction delta * input accumulated since the last neuron_apply, points into storage
  double * weights;  // n_inputs + 1 elements, weights[0] = w0, points into storage
  double storage[];
};


Neuron neuron_new(int n_inputs, double (*func)(double), double (*func_prime)(double), const double weights[],
                  const OptimizerConfig * optimizer) {

  Neuron neuron = malloc(sizeof(struct neuron) + 2 * (n_inputs + 1) * sizeof(double));
  if (neuron == NULL) {
    fprintf(stderr, "FATAL: couldn't allocate neuron\n");
    abort();
  }
  neuron->optimizer = optimizer_new(optimizer, n_inputs + 1);
  if (neuron->optimizer == NULL) {
    fprintf(stderr, "FATAL: unknown optimizer \"%s\" (available: %s)\n", optimizer->name, optimizer_names());
    abort();
  }
  neuron->n_inputs = n_inputs;
  neuron->weights = neuron->storage;
  neuron->gradient = neuron->storage + n_inputs + 1;
  memset(neuron->gradient, 0, (n_inputs + 1) * sizeof(double));
  memcpy(neuron->weights, weights, (n_inputs + 1) * sizeof(double));
  neuron->theta = func;
  neuron->theta_prime = func_prime;

  return neuron;

}


void neuron_free(Neuron neuron) {
  optimizer_free(neuron->optimizer);
  free(neuron);
}


int neuron_get_n_inputs(const Neuron neuron) {
  return neuron->n_inputs;
}


double neuron_get_weight(const Neuron neuron, int i) {
  return neuron->weights[i];
}


double neuron_theta_prime(const Neuron neuron, double h) {
  return neuron->theta_prime(h);
}


void neuron_get_weights(const Neuron neuron, double out[]) {
  memcpy(out, neuron->weights, (neuron->n_inputs + 1) * sizeof(double));
}


void neuron_set_weights(Neuron neuron, const double weights[]) {
  memcpy(neuron->weights, weights, (neuron->n_inputs + 1) * sizeof(double));
  memset(neuron->gradient, 0, (neuron->n_inputs + 1) * sizeof(double));
}


double neuron_predict(const Neuron neuron, const double input[], double * h_out) {

  double aux = 0.0;

  for (int j = 0; j < neuron->n_inputs; j++) {
    aux += (neuron->weights[j+1] * input[j]);
  }
  aux += neuron->weights[0];

  if (h_out != NULL) {
    *h_out = aux;
  }

  return neuron->theta(aux);

}


void neuron_accumulate(Neuron neuron, const double input[], double delta) {

  neuron->gradient[0] += delta;
  for (int i = 1; i <= neuron->n_inputs; i++) {
    neuron->gradient[i] += (delta * input[i-1]);
  }

}


void neuron_apply(Neuron neuron) {

  optimizer_step(neuron->optimizer, neuron->weights, neuron->gradient);
  memset(neuron->gradient, 0, (neuron->n_inputs + 1) * sizeof(double));

}


double neuron_eta(const Neuron neuron) {
  return optimizer_eta(neuron->optimizer);
}


void neuron_set_eta(Neuron neuron, double eta) {
  optimizer_set_eta(neuron->optimizer, eta);
}
