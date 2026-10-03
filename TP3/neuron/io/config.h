#ifndef __CONFIG_H__
#define __CONFIG_H__

#define CONFIG_STRING_MAX 256
#define CONFIG_HIDDEN_LAYERS_MAX 16

typedef struct {
  char train_dataset[CONFIG_STRING_MAX];
  char validation_dataset[CONFIG_STRING_MAX];
  char activation[CONFIG_STRING_MAX];
  double eta;
  int epochs;
  int batch_size;
  int hidden_layers[CONFIG_HIDDEN_LAYERS_MAX]; // neurons per hidden layer; empty = simple perceptron
  int n_hidden_layers;
  double tolerance; // stop once the train MSE drops below it; 0 (the default) never stops early.
                    // Ignored with a discrete activation, which stops at zero misclassified samples
  unsigned int seed;
  char initial_weights[CONFIG_STRING_MAX]; // optional: an earlier run's directory or weights.csv to keep
                                           // training from; "" (the default) draws random weights
} Config;

// Reads a flat JSON object with the Config fields as keys. Every key is required except the optional
// ones, which default to zero / "".
// Returns 1 on success; on failure prints the reason to stderr and returns 0.
int config_load(const char * path, Config * config);

#endif //__CONFIG_H__
