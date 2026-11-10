#include "activation.h"
#include <math.h>
#include <string.h>

static double sign(double x) {
  return x >= 0 ? 1.0 : -1.0;
}

// Not the derivative (it's 0 almost everywhere): 1 makes the generic delta rule
// eta * (zeta - O) * x exactly Rosenblatt's, so the step needs no special case.
static double sign_prime(double x) {
  (void) x;
  return 1.0;
}

static double lineal(double x) {
  return x;
}

static double lineal_prime(double x) {
  (void) x;
  return 1.0;
}

// Not differentiable at 0: the derivative there is taken as 0, so a neuron sitting exactly at 0 doesn't learn
static double relu(double x) {
  return x > 0 ? x : 0.0;
}

static double relu_prime(double x) {
  return x > 0 ? 1.0 : 0.0;
}

static double tanh_prime(double x) {
  return 1.0 - (tanh(x) * tanh(x));
}

// Split by sign so exp never overflows for large |x|
static double logistic(double x) {
  if (x >= 0) return 1.0 / (1.0 + exp(-x));
  double e = exp(x);
  return e / (1.0 + e);
}

static double logistic_prime(double x) {
  double theta = logistic(x);
  return theta * (1.0 - theta);
}

static const Activation ACTIVATIONS[] = {
  { "sign",     sign,     sign_prime,     1 },
  { "lineal",   lineal,   lineal_prime,   0 },
  { "tanh",     tanh,     tanh_prime,     0 },
  { "logistic", logistic, logistic_prime, 0 },
  { "relu",     relu,     relu_prime,     0 },
};

#define N_ACTIVATIONS ((int) (sizeof(ACTIVATIONS) / sizeof(ACTIVATIONS[0])))


const Activation * activation_find(const char * name) {
  for (int i = 0; i < N_ACTIVATIONS; i++) {
    if (strcmp(ACTIVATIONS[i].name, name) == 0) return &ACTIVATIONS[i];
  }
  return NULL;
}


const char * activation_names(void) {
  return "sign, lineal, tanh, logistic, relu";
}
