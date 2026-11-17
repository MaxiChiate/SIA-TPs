#ifndef __CONFIG_H__
#define __CONFIG_H__

#define CONFIG_STRING_MAX 256
#define CONFIG_HIDDEN_LAYERS_MAX 16

typedef struct {
  char train_dataset[CONFIG_STRING_MAX];
  char validation_dataset[CONFIG_STRING_MAX]; // "" when validation_split is used instead
  char activation[CONFIG_STRING_MAX];
  double eta;
  int epochs;
  int batch_size;
  int hidden_layers[CONFIG_HIDDEN_LAYERS_MAX]; // neurons per hidden layer; empty = simple perceptron.
                                               // With the autoencoder keys it's filled in by config_load:
                                               // encoder_layers, latent_dim, encoder_layers reversed
  int n_hidden_layers;
  // Autoencoder, as an alternative to hidden_layers: the two go together. The decoder mirrors the encoder, so
  // the network is inputs - encoder_layers - latent_dim - encoder_layers reversed - outputs (the dataset's
  // zetas, as many as inputs).
  int encoder_layers[CONFIG_HIDDEN_LAYERS_MAX]; // neurons per layer between the inputs and the latent code
  int n_encoder_layers;
  int latent_dim;                               // neurons in the latent code layer; 0 = not an autoencoder
  // Variational autoencoder: "variational_beta" (>= 0, the weight of the KL term; 0 is allowed) turns the
  // autoencoder into a VAE. The layer in the middle then has 2 * latent_dim neurons (the means and the
  // log-variances of the latent code, see network_new_variational) and variational is 1.
  int variational;
  double variational_beta;
  double tolerance; // stop once the train MSE drops below it; 0 (the default) never stops early.
                    // Ignored with a discrete activation, which stops at zero misclassified samples
  unsigned int seed;
  int shuffle; // optional: reshuffle the train samples at the start of every epoch (with seed); 0 keeps the CSV order
  double validation_split; // optional: share of train_dataset held out as validation, in (0, 1), instead of a
                           // validation_dataset; 0 (the default) means there is a validation_dataset
  unsigned int split_seed; // seed of that split, independent of seed; required with validation_split
  char initial_weights[CONFIG_STRING_MAX]; // optional: an earlier run's directory or weights.csv to keep
                                           // training from; "" (the default) draws random weights
  char optimizer[CONFIG_STRING_MAX]; // optional: "gd" (the default), "momentum", "rmsprop", "adam" or "adaptive_eta"
  // The optimizer's hyperparameters: each one is required with the optimizers that read it and refused with
  // the rest, so they stay at 0 when unused
  double momentum;          // alpha, momentum
  double rmsprop_decay;     // gamma, rmsprop
  double adam_beta1;        // adam
  double adam_beta2;        // adam
  double optimizer_epsilon; // rmsprop and adam
  double eta_increase;      // adaptive_eta: a, added to eta after eta_patience_up epochs with the train E falling
  double eta_decrease;      // adaptive_eta: b, eta *= 1 - b after eta_patience_down epochs with it rising
  int eta_patience_up;      // adaptive_eta: k
  int eta_patience_down;    // adaptive_eta: k'
} Config;

// Reads a flat JSON object with the Config fields as keys. Every key is required except the optional
// ones, which default to zero / "". Exactly one of validation_dataset and validation_split must be given,
// and split_seed goes with validation_split. The architecture is either hidden_layers or the autoencoder
// keys (encoder_layers, latent_dim), never both. The optimizer comes with exactly the hyperparameters it reads.
// Returns 1 on success; on failure prints the reason to stderr and returns 0.
int config_load(const char * path, Config * config);

#endif //__CONFIG_H__
