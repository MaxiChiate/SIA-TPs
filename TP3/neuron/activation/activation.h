#ifndef __ACTIVATION_H__
#define __ACTIVATION_H__

typedef struct {
  const char * name;
  double (*theta)(double);
  double (*theta_prime)(double);
} Activation;

// Returns NULL if there's no activation with that name
const Activation * activation_find(const char * name);

// Comma-separated list of the available names, for error messages
const char * activation_names(void);

#endif //__ACTIVATION_H__
