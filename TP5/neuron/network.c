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

  // Variational autoencoder (variational_layer = 0 when the network is a plain multilayer): layer
  // variational_layer has 2L neurons, the L means then the L log-variances, and the layer after it takes the
  // L-vector z = mean + exp(log_variance / 2) * epsilon as its input, not the 2L outputs.
  int variational_layer;
  double beta;  // weight of the KL term in the loss
  Rng * noise;  // epsilon ~ N(0, 1) comes from here in training; NULL means no noise (z = mean)
  double * z;   // L values
  double * epsilon;
};


static void * checked_malloc(size_t size) {
  void * pointer = malloc(size);
  if (pointer == NULL) {
    fprintf(stderr, "FATAL: couldn't allocate network\n");
    abort();
  }
  return pointer;
}


// Inputs of layer l: the previous layer's outputs, except right after the variational layer (z has half as many)
static int n_inputs_of(const struct network * network, int l) {
  int after_variational = network->variational_layer != 0 && l == network->variational_layer + 1;
  return after_variational ? network->sizes[l-1] / 2 : network->sizes[l-1];
}


static const double * inputs_of(const struct network * network, int l) {
  int after_variational = network->variational_layer != 0 && l == network->variational_layer + 1;
  return after_variational ? network->z : network->v[l-1];
}


static Neuron new_neuron(int n_inputs, const Activation * activation, const OptimizerConfig * optimizer,
                         double (*draw_weight)(void *), void * context) {
  double weights[n_inputs + 1];
  for (int i = 0; i <= n_inputs; i++) {
    weights[i] = draw_weight(context);
  }
  return neuron_new(n_inputs, activation->theta, activation->theta_prime, weights, optimizer);
}


static Network create(int n_layers, const int sizes[], int variational_layer, double beta, Rng * noise,
                      const Activation * activation, const OptimizerConfig * optimizer,
                      double (*draw_weight)(void *), void * context) {

  Network network = checked_malloc(sizeof(struct network));
  network->n_layers = n_layers;
  network->variational_layer = variational_layer;
  network->beta = beta;
  network->noise = noise;
  int latent = variational_layer != 0 ? sizes[variational_layer] / 2 : 0;
  network->z = checked_malloc((latent > 0 ? latent : 1) * sizeof(double));
  network->epsilon = checked_malloc((latent > 0 ? latent : 1) * sizeof(double));
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
      // the variational layer outputs means and log-variances, which are unbounded: it's linear
      const Activation * layer_activation = l == variational_layer ? activation_find("lineal") : activation;
      network->layers[l][j] = new_neuron(n_inputs_of(network, l), layer_activation, optimizer, draw_weight, context);
    }
    network->v[l] = checked_malloc(sizes[l] * sizeof(double));
    network->h[l] = checked_malloc(sizes[l] * sizeof(double));
    network->delta[l] = checked_malloc(sizes[l] * sizeof(double));
  }

  return network;

}


Network network_new(int n_layers, const int sizes[], const Activation * activation, const OptimizerConfig * optimizer,
                    double (*draw_weight)(void *), void * context) {
  return create(n_layers, sizes, 0, 0.0, NULL, activation, optimizer, draw_weight, context);
}


Network network_new_variational(int n_layers, const int sizes[], int variational_layer, double beta, Rng * noise,
                                const Activation * activation, const OptimizerConfig * optimizer,
                                double (*draw_weight)(void *), void * context) {
  return create(n_layers, sizes, variational_layer, beta, noise, activation, optimizer, draw_weight, context);
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
  free(network->z);
  free(network->epsilon);
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
    total += network->sizes[l] * (n_inputs_of(network, l) + 1);
  }
  return total;
}


void network_get_weights(const Network network, double out[]) {
  for (int l = 1; l <= network->n_layers; l++) {
    for (int j = 0; j < network->sizes[l]; j++) {
      neuron_get_weights(network->layers[l][j], out);
      out += n_inputs_of(network, l) + 1;
    }
  }
}


void network_set_weights(Network network, const double weights[]) {
  for (int l = 1; l <= network->n_layers; l++) {
    for (int j = 0; j < network->sizes[l]; j++) {
      neuron_set_weights(network->layers[l][j], weights);
      weights += n_inputs_of(network, l) + 1;
    }
  }
}


// Every neuron's optimizer has the same eta, so any of them answers for the network
double network_eta(const Network network) {
  return neuron_eta(network->layers[1][0]);
}


void network_set_eta(Network network, double eta) {
  for (int l = 1; l <= network->n_layers; l++) {
    for (int j = 0; j < network->sizes[l]; j++) {
      neuron_set_eta(network->layers[l][j], eta);
    }
  }
}


// z = mean + exp(log_variance / 2) * epsilon from the outputs of the variational layer. epsilon is drawn only
// when sample is set and the network has noise; otherwise it's 0 and z is the mean.
static void sample_z(Network network, int sample) {
  int latent = network->sizes[network->variational_layer] / 2;
  const double * outputs = network->v[network->variational_layer];
  for (int j = 0; j < latent; j++) {
    network->epsilon[j] = sample && network->noise != NULL ? rng_normal(network->noise) : 0.0;
    network->z[j] = outputs[j] + exp(0.5 * outputs[latent + j]) * network->epsilon[j];
  }
}


// Leaves every v[l] and h[l] filled in, backpropagation needs them
static void forward(Network network, const double input[], int sample) {
  memcpy(network->v[0], input, network->sizes[0] * sizeof(double));
  for (int l = 1; l <= network->n_layers; l++) {
    for (int j = 0; j < network->sizes[l]; j++) {
      network->v[l][j] = neuron_predict(network->layers[l][j], inputs_of(network, l), &network->h[l][j]);
    }
    if (l == network->variational_layer) sample_z(network, sample);
  }
}


void network_predict(Network network, const double input[], double output[]) {
  forward(network, input, 0);
  memcpy(output, network->v[network->n_layers], network_n_outputs(network) * sizeof(double));
}


int network_n_layers(const Network network) {
  return network->n_layers;
}


int network_layer_size(const Network network, int layer) {
  return network->sizes[layer];
}


int network_latent_layer(const Network network) {
  return network->variational_layer != 0 ? network->variational_layer : network->n_layers / 2;
}


int network_latent_size(const Network network) {
  int size = network->sizes[network_latent_layer(network)];
  return network->variational_layer != 0 ? size / 2 : size;
}


void network_encode(Network network, const double input[], int layer, double out[]) {
  forward(network, input, 0);
  memcpy(out, network->v[layer], network->sizes[layer] * sizeof(double));
}


void network_decode(Network network, int from_layer, const double code[], double output[]) {
  if (from_layer == network->variational_layer) {
    // the decoder starts from z, which has half the neurons of the layer that produces it
    memcpy(network->z, code, network->sizes[from_layer] / 2 * sizeof(double));
  } else {
    memcpy(network->v[from_layer], code, network->sizes[from_layer] * sizeof(double));
  }
  for (int l = from_layer + 1; l <= network->n_layers; l++) {
    for (int j = 0; j < network->sizes[l]; j++) {
      network->v[l][j] = neuron_predict(network->layers[l][j], inputs_of(network, l), &network->h[l][j]);
    }
    if (l == network->variational_layer) sample_z(network, 0);
  }
  memcpy(output, network->v[network->n_layers], network_n_outputs(network) * sizeof(double));
}


// Deltas of the variational layer: -d(E + beta * KL)/dh, with E the reconstruction energy and
//   KL = -1/2 * sum(1 + log_variance - mean^2 - exp(log_variance)) over the L latent values.
// g = -dE/dz comes from the layer after, whose delta is already computed; z = mean + exp(log_variance / 2) * epsilon:
//   -dE/dmean = g                              -d(beta KL)/dmean = -beta * mean
//   -dE/dlog_variance = g * epsilon * exp(log_variance / 2) / 2    -d(beta KL)/dlog_variance = -beta * (exp(log_variance) - 1) / 2
static void variational_delta(Network network) {
  int l = network->variational_layer;
  int latent = network->sizes[l] / 2;
  const double * outputs = network->v[l];
  for (int j = 0; j < latent; j++) {
    double g = 0.0;
    for (int k = 0; k < network->sizes[l+1]; k++) {
      g += neuron_get_weight(network->layers[l+1][k], j + 1) * network->delta[l+1][k];
    }
    double mean = outputs[j], log_variance = outputs[latent + j];
    double d_mean = g - network->beta * mean;
    double d_log_variance = g * network->epsilon[j] * exp(0.5 * log_variance) / 2
                            - network->beta * (exp(log_variance) - 1) / 2;
    network->delta[l][j] = d_mean * neuron_theta_prime(network->layers[l][j], network->h[l][j]);
    network->delta[l][latent + j] =
      d_log_variance * neuron_theta_prime(network->layers[l][latent + j], network->h[l][latent + j]);
  }
}


// Computes every delta first and only then accumulates Δw. The weights don't change until
// apply_updates, so the hidden deltas always use the weights the forward pass used.
static void backpropagate(Network network, const double input[], const double zeta[]) {

  int last = network->n_layers;
  forward(network, input, 1);

  for (int j = 0; j < network->sizes[last]; j++) {
    Neuron neuron = network->layers[last][j];
    network->delta[last][j] = (zeta[j] - network->v[last][j]) * neuron_theta_prime(neuron, network->h[last][j]);
  }

  for (int l = last - 1; l >= 1; l--) {
    if (l == network->variational_layer) {
      variational_delta(network);
      continue;
    }
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
      neuron_accumulate(network->layers[l][j], inputs_of(network, l), network->delta[l][j]);
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
    forward(network, &inputs[i * n_inputs], 0);
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


double network_variational_loss(Network network, const double inputs[], const double zetas[], int n_samples) {
  int n_inputs = network_n_inputs(network);
  int n_outputs = network_n_outputs(network);
  double * output = network->v[network->n_layers];
  int latent = network->sizes[network->variational_layer] / 2;
  const double * means = network->v[network->variational_layer];
  const double * log_variances = means + latent;

  double loss = 0.0;
  for (int i = 0; i < n_samples; i++) {
    forward(network, &inputs[i * n_inputs], 1);
    double energy = 0.0, kl = 0.0;
    for (int j = 0; j < n_outputs; j++) {
      double error = zetas[i * n_outputs + j] - output[j];
      energy += error * error / 2;
    }
    for (int j = 0; j < latent; j++) {
      kl += -0.5 * (1 + log_variances[j] - means[j] * means[j] - exp(log_variances[j]));
    }
    loss += energy + network->beta * kl;
  }
  return loss;
}


int network_misclassified(Network network, const double inputs[], const double zetas[], int n_samples) {
  int n_inputs = network_n_inputs(network);
  int n_outputs = network_n_outputs(network);
  double * output = network->v[network->n_layers];

  int wrong = 0;
  for (int i = 0; i < n_samples; i++) {
    forward(network, &inputs[i * n_inputs], 0);
    for (int j = 0; j < n_outputs; j++) {
      if (fabs(zetas[i * n_outputs + j] - output[j]) > 0.5) {
        wrong++;
        break;
      }
    }
  }
  return wrong;
}


int network_train(Network network, const double inputs[], const double zetas[], int n_samples,
                  int epochs, int batch_size, Rng * shuffle_rng, EpochCallback on_epoch, void * context) {

  int n_inputs = network_n_inputs(network);
  int n_outputs = network_n_outputs(network);

  // The samples are visited through order, so shuffling never touches the dataset itself
  int * order = checked_malloc(n_samples * sizeof(int));
  for (int i = 0; i < n_samples; i++) order[i] = i;

  int epochs_run = epochs;
  for (int epoch = 1; epoch <= epochs; epoch++) {
    if (shuffle_rng != NULL) rng_shuffle(shuffle_rng, order, n_samples);
    for (int i = 0; i < n_samples; i++) {
      int sample = order[i];
      backpropagate(network, &inputs[sample * n_inputs], &zetas[sample * n_outputs]);
      int batch_done = (i + 1) % batch_size == 0 || i + 1 == n_samples;
      if (batch_done) apply_updates(network);
    }
    if (on_epoch != NULL && on_epoch(epoch, network, context)) {
      epochs_run = epoch;
      break;
    }
  }

  free(order);
  return epochs_run;

}
