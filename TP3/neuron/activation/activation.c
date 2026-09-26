#include "activation.h"
#include <math.h>
#include <string.h>

static double sign(double x) {
  return x >= 0 ? 1.0 : -1.0;
}

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

static double tanh_prime(double x) {
  return 1.0 - (tanh(x) * tanh(x));
}

static const Activation ACTIVATIONS[] = {
  { "sign",   sign,   sign_prime },
  { "lineal", lineal, lineal_prime },
  { "tanh",   tanh,   tanh_prime },
};

#define N_ACTIVATIONS ((int) (sizeof(ACTIVATIONS) / sizeof(ACTIVATIONS[0])))


const Activation * activation_find(const char * name) {
  for (int i = 0; i < N_ACTIVATIONS; i++) {
    if (strcmp(ACTIVATIONS[i].name, name) == 0) return &ACTIVATIONS[i];
  }
  return NULL;
}


const char * activation_names(void) {
  return "sign, lineal, tanh";
}
