#include "rng.h"
#include <math.h>

Rng rng_new(unsigned int seed) {
  return (Rng) { .state = seed };
}


double rng_uniform(Rng * rng) {
  rng->state += 0x9E3779B97F4A7C15ULL;
  unsigned long long z = rng->state;
  z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
  z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
  z ^= z >> 31;
  return (z >> 11) * (1.0 / 9007199254740992.0); // top 53 bits
}


double rng_normal(Rng * rng) {
  double u1 = 1.0 - rng_uniform(rng); // in (0, 1], so the log is finite
  double u2 = rng_uniform(rng);
  return sqrt(-2.0 * log(u1)) * cos(6.283185307179586 * u2);
}


void rng_shuffle(Rng * rng, int values[], int n) {
  for (int i = n - 1; i > 0; i--) {
    int j = (int) (rng_uniform(rng) * (i + 1)); // uniform in [0, i]
    int swapped = values[i];
    values[i] = values[j];
    values[j] = swapped;
  }
}
