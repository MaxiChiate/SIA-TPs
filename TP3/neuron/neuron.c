#include "neuron.h" 
#include <math.h>

struct neuron {
  double weights[WEIGHTS_AMOUNT];
  double (*theta)(double);
  double (*theta_prime)(double);
  double eta;
};


Neuron neuron_new(double (*func)(double), double (*func_prime)(double), double weights[], double eta) {

  Neuron neuron = malloc(sizeof(struct neuron));
  if (neuron == NULL) {
    fprintf(stderr, "FATAL: couldn't allocate neuron\n", stderr);
    abort();
  }
  memcpy(neuron->weights, weights, sizeof(neuron->weights)); 
  neuron->theta = func;
  neuron->theta_prime = func_prime;
  neuron->eta = eta;

  return neuron;

}


void neuron_get_weights(const Neuron neuron, double out[WEIGHTS_AMOUNT]) {
  memcpy(out, neuron->weights, sizeof(neuron->weights));
}


double neuron_predict(const Neuron neuron, const double input[N_INPUTS], double * h_out) {

  double aux = 0.0;

  for (int i = 1, j = 0; i < WEIGHTS_AMOUNT && j < N_INPUTS; i++, j++) {
    aux += (neuron->weights[i] * input[j]);
  }
  aux += neuron->weights[0];
  
  if (h_out != NULL) {
    *h_out = aux; 
  }

  return neuron->theta(aux);

}


int neuron_learn(Neuron neuron, const double input[N_INPUTS], double zeta) {
  
  double h;
  double prediction = neuron_predict(neuron, input, &h);

  double delta = neuron->eta * (zeta - prediction) * neuron->theta_prime(h);

  neuron->weights[0] += delta;
  for (int i = 1; i < WEIGHTS_AMOUNT; i++) {
    neuron->weights[i] += (delta * input[i-1]);
  }

  return !(((prediction - zeta)  < 0.1) && ((zeta - prediction) > -0.1));

}


int neuron_train(Neuron neuron, const double dataset[][N_INPUTS], const double zetas[], int n_samples, int max_epochs) {

  int convergence = 0;
  int epoch = 0;

  while (!convergence && epoch++ < max_epochs) {

    int errors_this_epoch = 0;
    for (int i = 0; i < n_samples; i++) {
      errors_this_epoch += neuron_learn(neuron, dataset[i], zetas[i]);
    }

    if (errors_this_epoch == 0) convergence = 1;
  }

  
  return convergence ? epoch : -1;

}
