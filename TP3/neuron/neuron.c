#include "neuron.h" 
#include <math.h>

struct neuron {
  int n_inputs;
  double (*theta)(double);
  double (*theta_prime)(double);
  double eta;
  double weights[]; // n_inputs + 1 elements, weights[0] = w0
};


Neuron neuron_new(int n_inputs, double (*func)(double), double (*func_prime)(double), const double weights[], double eta) {

  Neuron neuron = malloc(sizeof(struct neuron) + (n_inputs + 1) * sizeof(double));
  if (neuron == NULL) {
    fprintf(stderr, "FATAL: couldn't allocate neuron\n");
    abort();
  }
  neuron->n_inputs = n_inputs;
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


void neuron_get_weights(const Neuron neuron, double out[]) {
  memcpy(out, neuron->weights, (neuron->n_inputs + 1) * sizeof(double));
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


void neuron_learn(Neuron neuron, const double input[], double zeta) {
  
  double h;
  double prediction = neuron_predict(neuron, input, &h);

  double delta = neuron->eta * (zeta - prediction) * neuron->theta_prime(h);

  neuron->weights[0] += delta;
  for (int i = 1; i <= neuron->n_inputs; i++) {
    neuron->weights[i] += (delta * input[i-1]);
  }

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


void plot_neuron_validation(const Neuron neuron, int n_inputs, const double dataset[][n_inputs], const double zetas[], int n_samples) {

  int errors = 0;

  for (int i = 0; i < n_samples; i++) {
    double prediction = neuron_predict(neuron, dataset[i], NULL);

    printf("input: %f, prediction: %f, zeta: %f\n", dataset[i][0], prediction, zetas[i]);

    if (!(fabs(prediction - zetas[i]) < EPSILON)) {
      errors++;
    }
  }

  printf("errors: %d/%d\n", errors, n_samples);

}