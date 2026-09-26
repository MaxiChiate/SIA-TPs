#include "neuron.h"
#include "config.h"
#include <math.h>

double sign(double x) {
  return x >= 0 ? 1.0 : -1.0;
}

double sign_prime() {
  return 1.0;
}

// Ejemplo voters

#define N_SAMPLES 20

static const double dataset[N_SAMPLES][2] = {
    {0.445, 0.669}, {0.349, 0.692}, {0.232, 0.585}, {0.125, 0.438},
    {0.224, 0.579}, {0.230, 0.529}, {0.392, 0.696}, {0.355, 0.641},
    {0.455, 0.660}, {0.289, 0.510}, {0.513, 0.255}, {0.755, 0.522},
    {0.626, 0.240}, {0.703, 0.342}, {0.863, 0.536}, {0.600, 0.225},
    {0.664, 0.303}, {0.802, 0.565}, {0.592, 0.213}, {0.531, 0.223},
};

static const double zetas[N_SAMPLES] = {
    1,1,1,1,1,1,1,1,1,1, -1,-1,-1,-1,-1,-1,-1,-1,-1,-1
};

// AND


static const double and_dataset[4][2] = {
  {0.0, 0.0}, {1.0, 0.0}, {0.0, 1.0}, {1.0, 1.0} 
};


static const double and_zetas[4] = {
  -1.0, -1.0, -1.0, 1.0
};

// Lineal

double lineal(double x) {
  return x;
}

double lineal_prime() {
  return 1.0;
}

#define N_SAMPLES_LINEAL 50
#define M_VALIDATION_LINEAL 10

static const double lineal_dataset[N_SAMPLES_LINEAL][1] = {
  {0.0}, {0.1}, {0.2}, {0.3}, {0.4}, {0.5}, {0.6}, {0.7}, {0.8}, {0.9},
  {1.0}, {1.1}, {1.2}, {1.3}, {1.4}, {1.5}, {1.6}, {1.7}, {1.8}, {1.9},
  {2.0}, {2.1}, {2.2}, {2.3}, {2.4}, {2.5}, {2.6}, {2.7}, {2.8}, {2.9},
  {3.0}, {3.1}, {3.2}, {3.3}, {3.4}, {3.5}, {3.6}, {3.7}, {3.8}, {3.9},
  {4.0}, {4.1}, {4.2}, {4.3}, {4.4}, {4.5}, {4.6}, {4.7}, {4.8}, {4.9}
};

static const double lineal_zetas[N_SAMPLES_LINEAL] = {
  0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9,
  1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9,
  2.0, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9,
  3.0, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7 , 3.8 , 3.9 ,
  4.0 , 4.1 , 4.2 , 4.3 , 4.4 , 4.5 , 4.6 , 4.7 , 4.8 , 4.9
};

static const double lineal_validation_dataset[M_VALIDATION_LINEAL][1] = {
  {0.05}, {0.15}, {0.25}, {0.35}, {0.45}, {0.55}, {0.65}, {0.75}, {0.85}, {0.95}
};

static const double lineal_validation_zetas[M_VALIDATION_LINEAL] = {
  0.05, 0.15, 0.25,0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95
};

// No Lineal (tanh)

#define N_SAMPLES_TANH 50
#define M_VALIDATION_TANH 10

double tanh_prime(double x) {
  return 1.0 - (tanh(x) * tanh(x));
}

static const double tanh_dataset[N_SAMPLES_TANH][1] = {
  {-2.5}, {-2.4}, {-2.3}, {-2.2}, {-2.1}, {-2.0}, {-1.9}, {-1.8}, {-1.7}, {-1.6},
  {-1.5}, {-1.4}, {-1.3}, {-1.2}, {-1.1}, {-1.0}, {-0.9}, {-0.8}, {-0.7}, {-0.6},
  {-0.5}, {-0.4}, {-0.3}, {-0.2}, {-0.1}, {0.0}, {0.1}, {0.2}, {0.3}, {0.4},
  {0.5}, {0.6}, {0.7}, {0.8}, {0.9}, {1.0}, {1.1}, {1.2}, {1.3}, {1.4},
  {1.5}, {1.6}, {1.7}, {1.8}, {1.9}, {2.0}, {2.1}, {2.2}, {2.3}, {2.4}
};

static const double tanh_zetas[N_SAMPLES_TANH] = {
  -0.986614, -0.983675, -0.980096, -0.975743, -0.970452,
  -0.964028, -0.956237, -0.946806, -0.935409, -0.921669,
  -0.905148, -0.885352, -0.861723, -0.833655, -0.800499,
  -0.761594, -0.716298, -0.664037, -0.604368, -0.537050,
  -0.462117, -0.379949, -0.291313, -0.197375, -0.099668,
  0.000000, 0.099668, 0.197375, 0.291313, 0.379949,
  0.462117, 0.537050, 0.604368, 0.664037, 0.716298,
  0.761594, 0.800499, 0.833655, 0.861723, 0.885352,
  0.905148, 0.921669, 0.935409, 0.946806, 0.956237,
  0.964028, 0.970452, 0.975743, 0.980096, 0.983675
};

static const double tanh_validation_dataset[M_VALIDATION_TANH][1] = {
  {-2.25}, {-1.75}, {-1.25}, {-0.75}, {-0.25}, {0.25}, {0.75}, {1.25}, {1.75}, {2.25}
};

static const double tanh_validation_zetas[M_VALIDATION_TANH] = {
  -0.978026, -0.941376, -0.848284, -0.635149, -0.244919,
  0.244919, 0.635149, 0.848284, 0.941376, 0.978026
};


// Main

int main() {

  const int n_inputs = 1;
  double weights_in[] = {1.0, 0.3};

  printf("weights before training:\n");
  printf("%f, %f\n", weights_in[0], weights_in[1]);

  //Neuron neuron = neuron_new(sign, sign_prime, weights_in, eta);
  //Neuron neuron = neuron_new(lineal, lineal_prime, weights_in, eta);
  Neuron neuron = neuron_new(n_inputs, tanh, tanh_prime, weights_in, ETA);

  //int converged = neuron_train(neuron, lineal_dataset, lineal_zetas, N_SAMPLES_LINEAL, 10000);

  int converged = neuron_train_by_epoch(neuron, n_inputs, tanh_dataset, tanh_zetas, N_SAMPLES_TANH);
  printf("converged: %d\n", converged);

  double weights_out[n_inputs + 1];
  neuron_get_weights(neuron, weights_out);

  printf("weights after training:\n");
  printf("%f, %f\n", weights_out[0], weights_out[1]);


  plot_neuron_validation(neuron, n_inputs, tanh_validation_dataset, tanh_validation_zetas, M_VALIDATION_TANH);


// Agregar validate

  neuron_free(neuron);

  return 0;

}
