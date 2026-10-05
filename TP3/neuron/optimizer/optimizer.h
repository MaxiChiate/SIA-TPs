#ifndef __OPTIMIZER_H__
#define __OPTIMIZER_H__

// Turns the descent direction accumulated over a batch into the step the weights take. It knows nothing
// about neurons, networks or datasets: it works on a plain array of weights.

typedef struct {
  const char * name;   // "gd"
  double eta;          // learning rate
  double momentum;     // alpha, for momentum
  double decay;        // gamma, for rmsprop
  double beta1, beta2; // for adam
  double epsilon;      // for rmsprop and adam
} OptimizerConfig;

typedef struct optimizer * Optimizer;

// For n_weights weights, with its state at zero. Returns NULL if there's no optimizer called config->name.
Optimizer optimizer_new(const OptimizerConfig * config, int n_weights);

void optimizer_free(Optimizer optimizer);

// descent is -dE/dw accumulated over the batch, one value per weight; weights moves by the optimizer's step
void optimizer_step(Optimizer optimizer, double weights[], const double descent[]);

double optimizer_eta(const Optimizer optimizer);

void optimizer_set_eta(Optimizer optimizer, double eta);

// Comma-separated list of the available names, for error messages
const char * optimizer_names(void);

#endif //__OPTIMIZER_H__
