#ifndef __MODELS_H__
#define __MODELS_H__

// The binary runs whichever model the config's "model" key names. Each model is one runner with the same
// signature; main creates the Rng and the run directory and hands both down.

#include "../io/config.h"
#include "../io/results.h"
#include "../rng.h"

// Returns 1 on success; on failure prints the reason to stderr and returns 0
typedef int (*ModelRun)(const Config * config, Rng * rng, const Results * results);

typedef struct {
  const char * name;
  ModelRun run;
} Model;

// NULL if no model has that name
const Model * model_find(const char * name);

// The registered names, comma-separated, in table order
const char * model_names(void);

// Phase 1 stub: sample-initialised k x k prototypes and the nearest prototype of every sample.
// Phase 2 replaces the body with Kohonen training.
int run_kohonen(const Config * config, Rng * rng, const Results * results);

// Phase 1 stub: projects the input onto a random unit vector. Phase 3 replaces the body with Oja's rule.
int run_oja(const Config * config, Rng * rng, const Results * results);

#endif //__MODELS_H__
