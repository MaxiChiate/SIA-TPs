#include "neuron.h" 
#include <math.h>

struct neuron {
  int n_inputs;
  double (*theta)(double);
  double (*theta_prime)(double);
  double eta;
  double * pending; // Δw accumulated since the last neuron_apply, points into storage
  double * weights; // n_inputs + 1 elements, weights[0] = w0, points into storage
  double storage[];
};


Neuron neuron_new(int n_inputs, double (*func)(double), double (*func_prime)(double), const double weights[], double eta) {

  Neuron neuron = malloc(sizeof(struct neuron) + 2 * (n_inputs + 1) * sizeof(double));
  if (neuron == NULL) {
    fprintf(stderr, "FATAL: couldn't allocate neuron\n");
    abort();
  }
  neuron->n_inputs = n_inputs;
  neuron->weights = neuron->storage;
  neuron->pending = neuron->storage + n_inputs + 1;
  memset(neuron->pending, 0, (n_inputs + 1) * sizeof(double));
  memcpy(neuron->weights, weights, (n_inputs + 1) * sizeof(double));
  neuron->theta = func;
  neuron->theta_prime = func_prime;
  neuron->eta = eta;

  return neuron;

}


void neuron_free(Neuron neuron) {
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
  memset(neuron->pending, 0, (neuron->n_inputs + 1) * sizeof(double));
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

  double step = neuron->eta * delta;

  neuron->pending[0] += step;
  for (int i = 1; i <= neuron->n_inputs; i++) {
    neuron->pending[i] += (step * input[i-1]);
  }

}


void neuron_apply(Neuron neuron) {

  for (int i = 0; i <= neuron->n_inputs; i++) {
    neuron->weights[i] += neuron->pending[i];
    neuron->pending[i] = 0.0;
  }

}


void neuron_learn(Neuron neuron, const double input[], double zeta) {

  double h;
  double prediction = neuron_predict(neuron, input, &h);

  neuron_accumulate(neuron, input, (zeta - prediction) * neuron->theta_prime(h));
  neuron_apply(neuron);

}


int neuron_learn_only(Neuron neuron, const double input[], double zeta) {
  
  double h;
  double prediction = neuron_predict(neuron, input, &h);

  double delta = neuron->eta * (zeta - prediction) * neuron->theta_prime(h);

  neuron->weights[0] += delta;
  for (int i = 1; i <= neuron->n_inputs; i++) {
    neuron->weights[i] += (delta * input[i-1]);
  }

  return !(fabs(prediction - zeta) < EPSILON);

}


/*int neuron_train(Neuron neuron, int n_inputs, const double dataset[][n_inputs], const double zetas[], int n_samples, int max_epochs) {

  int convergence = 0;
  int epoch = 0;

  while (!convergence && epoch++ < max_epochs) {

    int errors_this_epoch = 0;
    for (int i = 0; i < n_samples; i++) {
      neuron_learn(neuron, dataset[i], zetas[i]);
    }

    if (errors_this_epoch == 0) convergence = 1;
  }

  
  return convergence ? epoch : -1;
}*/

void neuron_train(Neuron neuron, int n_inputs, const double dataset[][n_inputs], const double zetas[], int n_samples, int epochs) {

  int epoch = 0;

  while ( epoch++ < epochs) {

    int errors_this_epoch = 0;
    for (int i = 0; i < n_samples; i++) {
      neuron_learn(neuron, dataset[i], zetas[i]);
    }
  }

}
