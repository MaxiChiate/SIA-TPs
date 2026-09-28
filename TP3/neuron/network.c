#include "network.h"
#include "neuron.h"
#include <math.h>

struct network {
  int n_layers;     // layers with neurons, the input layer doesn't count
  int * sizes;      // sizes[0] = n_inputs, sizes[l] = neurons in layer l
  Neuron ** layers; // layers[l][j] for l = 1..n_layers, layers[0] is unused
  double ** v;      // v[0] = input, v[l][j] = output of neuron j in layer l
  double ** h;      // h[l][j] = excitation of neuron j in layer l
  double ** delta;  // delta[l][j] = error signal of neuron j in layer l, theta'(h) included
};


static void * checked_malloc(size_t size) {
  void * pointer = malloc(size);
  if (pointer == NULL) {
    fprintf(stderr, "FATAL: couldn't allocate network\n");
    abort();
  }
  return pointer;
}


static Neuron new_neuron(int n_inputs, const Activation * activation, double eta, double (*draw_weight)(void)) {
  double weights[n_inputs + 1];
  for (int i = 0; i <= n_inputs; i++) {
    weights[i] = draw_weight();
  }
  return neuron_new(n_inputs, activation->theta, activation->theta_prime, weights, eta);
}


Network network_new(int n_layers, const int sizes[], const Activation * activation, double eta,
                    double (*draw_weight)(void)) {

  Network network = checked_malloc(sizeof(struct network));
  network->n_layers = n_layers;
  network->sizes = checked_malloc((n_layers + 1) * sizeof(int));
  memcpy(network->sizes, sizes, (n_layers + 1) * sizeof(int));

  network->layers = checked_malloc((n_layers + 1) * sizeof(Neuron *));
  network->v = checked_malloc((n_layers + 1) * sizeof(double *));
  network->h = checked_malloc((n_layers + 1) * sizeof(double *));
  network->delta = checked_malloc((n_layers + 1) * sizeof(double *));

  network->layers[0] = NULL;
  network->v[0] = checked_malloc(sizes[0] * sizeof(double));
  network->h[0] = NULL;
  network->delta[0] = NULL;

  for (int l = 1; l <= n_layers; l++) {
    network->layers[l] = checked_malloc(sizes[l] * sizeof(Neuron));
    for (int j = 0; j < sizes[l]; j++) {
      network->layers[l][j] = new_neuron(sizes[l-1], activation, eta, draw_weight);
    }
    network->v[l] = checked_malloc(sizes[l] * sizeof(double));
    network->h[l] = checked_malloc(sizes[l] * sizeof(double));
    network->delta[l] = checked_malloc(sizes[l] * sizeof(double));
  }

  return network;

}


void network_free(Network network) {
  for (int l = 1; l <= network->n_layers; l++) {
    for (int j = 0; j < network->sizes[l]; j++) {
      neuron_free(network->layers[l][j]);
    }
    free(network->layers[l]);
    free(network->h[l]);
    free(network->delta[l]);
  }
  for (int l = 0; l <= network->n_layers; l++) {
    free(network->v[l]);
  }
  free(network->layers);
  free(network->v);
  free(network->h);
  free(network->delta);
  free(network->sizes);
  free(network);
}


int network_n_inputs(const Network network) {
  return network->sizes[0];
}


int network_n_outputs(const Network network) {
  return network->sizes[network->n_layers];
}


int network_n_weights(const Network network) {
  int total = 0;
  for (int l = 1; l <= network->n_layers; l++) {
    total += network->sizes[l] * (network->sizes[l-1] + 1);
  }
  return total;
}


void network_get_weights(const Network network, double out[]) {
  for (int l = 1; l <= network->n_layers; l++) {
    for (int j = 0; j < network->sizes[l]; j++) {
      neuron_get_weights(network->layers[l][j], out);
      out += network->sizes[l-1] + 1;
    }
  }
}


void network_set_weights(Network network, const double weights[]) {
  for (int l = 1; l <= network->n_layers; l++) {
    for (int j = 0; j < network->sizes[l]; j++) {
      neuron_set_weights(network->layers[l][j], weights);
      weights += network->sizes[l-1] + 1;
    }
  }
}


// Leaves every v[l] and h[l] filled in, backpropagation needs them
static void forward(Network network, const double input[]) {
  memcpy(network->v[0], input, network->sizes[0] * sizeof(double));
  for (int l = 1; l <= network->n_layers; l++) {
    for (int j = 0; j < network->sizes[l]; j++) {
      network->v[l][j] = neuron_predict(network->layers[l][j], network->v[l-1], &network->h[l][j]);
    }
  }
}


void network_predict(Network network, const double input[], double output[]) {
  forward(network, input);
  memcpy(output, network->v[network->n_layers], network_n_outputs(network) * sizeof(double));
}


// Computes every delta first and only then accumulates Δw. The weights don't change until
// apply_updates, so the hidden deltas always use the weights the forward pass used.
static void backpropagate(Network network, const double input[], const double zeta[]) {

  int last = network->n_layers;
  forward(network, input);

  for (int j = 0; j < network->sizes[last]; j++) {
    Neuron neuron = network->layers[last][j];
    network->delta[last][j] = (zeta[j] - network->v[last][j]) * neuron_theta_prime(neuron, network->h[last][j]);
  }

  for (int l = last - 1; l >= 1; l--) {
    for (int j = 0; j < network->sizes[l]; j++) {
      double sum = 0.0;
      for (int k = 0; k < network->sizes[l+1]; k++) {
        // j + 1 because weight 0 is the bias
        sum += neuron_get_weight(network->layers[l+1][k], j + 1) * network->delta[l+1][k];
      }
      network->delta[l][j] = sum * neuron_theta_prime(network->layers[l][j], network->h[l][j]);
    }
  }

  for (int l = 1; l <= last; l++) {
    for (int j = 0; j < network->sizes[l]; j++) {
      neuron_accumulate(network->layers[l][j], network->v[l-1], network->delta[l][j]);
    }
  }

}


static void apply_updates(Network network) {
  for (int l = 1; l <= network->n_layers; l++) {
    for (int j = 0; j < network->sizes[l]; j++) {
      neuron_apply(network->layers[l][j]);
    }
  }
}


ErrorMetrics network_error(Network network, const double inputs[], const double zetas[], int n_samples) {
  int n_inputs = network_n_inputs(network);
  int n_outputs = network_n_outputs(network);
  double * output = network->v[network->n_layers];

  double squared_sum = 0.0, abs_sum = 0.0, max_abs = 0.0;
  for (int i = 0; i < n_samples; i++) {
    forward(network, &inputs[i * n_inputs]);
    for (int j = 0; j < n_outputs; j++) {
      double error = zetas[i * n_outputs + j] - output[j];
      squared_sum += error * error;
      abs_sum += fabs(error);
      if (fabs(error) > max_abs) max_abs = fabs(error);
    }
  }

  int n = n_samples * n_outputs;
  return (ErrorMetrics) {
    .energy = squared_sum / 2,
    .mse = squared_sum / n,
    .mae = abs_sum / n,
    .max_abs_error = max_abs,
  };
}


void network_train(Network network, const double inputs[], const double zetas[], int n_samples,
                   int epochs, int batch_size, EpochCallback on_epoch, void * context) {

  int n_inputs = network_n_inputs(network);
  int n_outputs = network_n_outputs(network);

  for (int epoch = 1; epoch <= epochs; epoch++) {
    for (int i = 0; i < n_samples; i++) {
      backpropagate(network, &inputs[i * n_inputs], &zetas[i * n_outputs]);
      int batch_done = (i + 1) % batch_size == 0 || i + 1 == n_samples;
      if (batch_done) apply_updates(network);
    }
    if (on_epoch != NULL) on_epoch(epoch, network, context);
  }

}
