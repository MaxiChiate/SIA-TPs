#ifndef __RNG_H__
#define __RNG_H__

// Seeded pseudo-random generator (splitmix64). One instance is created in main and passed down, so the
// same seed and config always give the same run.
typedef struct {
  unsigned long long state;
} Rng;

Rng rng_new(unsigned int seed);

// Uniform in [0, 1)
double rng_uniform(Rng * rng);

// Fisher-Yates: permutes values[0..n-1] in place, every order equally likely
void rng_shuffle(Rng * rng, int values[], int n);

#endif //__RNG_H__
