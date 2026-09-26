#include "neuron.h"

double sign(double x) {
  return x >= 0 ? 1.0 : -1.0;
}

double sign_prime() {
  return 1.0;
}


#define N_SAMPLES 20

static const double dataset[N_SAMPLES][N_INPUTS] = {
    {0.445, 0.669}, {0.349, 0.692}, {0.232, 0.585}, {0.125, 0.438},
    {0.224, 0.579}, {0.230, 0.529}, {0.392, 0.696}, {0.355, 0.641},
    {0.455, 0.660}, {0.289, 0.510}, {0.513, 0.255}, {0.755, 0.522},
    {0.626, 0.240}, {0.703, 0.342}, {0.863, 0.536}, {0.600, 0.225},
    {0.664, 0.303}, {0.802, 0.565}, {0.592, 0.213}, {0.531, 0.223},
};

static const double and_dataset[4][2] = {
  {0.0, 0.0}, {1.0, 0.0}, {0.0, 1.0}, {1.0, 1.0} 
};

static const double and_zetas[4] = {
  -1.0, -1.0, -1.0, 1.0
};


static const double zetas[N_SAMPLES] = {
    1,1,1,1,1,1,1,1,1,1, -1,-1,-1,-1,-1,-1,-1,-1,-1,-1
};


int main() {

  double weights_in[] = {1.0, 1.0, 1.0};
  double eta = 1;

  printf("weights before training:\n");
  printf("%f, %f, %f\n", weights_in[0], weights_in[1], weights_in[2]);

  Neuron neuron = neuron_new(sign, sign_prime, weights_in, eta);

  int converged = neuron_train(neuron, and_dataset, and_zetas, 4, 10000);

  printf("converged: %d\n", converged);

  double weights_out[WEIGHTS_AMOUNT];
  neuron_get_weights(neuron, weights_out);

  printf("weights after training:\n");
  printf("%f, %f, %f\n", weights_out[0], weights_out[1], weights_out[2]);

  return 0;

}
