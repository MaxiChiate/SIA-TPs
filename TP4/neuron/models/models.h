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

// Kohonen map on a k x k grid: prototypes start as samples picked by the Rng, trained online for a number of
// shuffled epochs with a step or gaussian neighborhood and exponentially decaying radius and learning rate.
// Writes prototypes.csv, assignments.csv, occupancy.csv, trace.csv and metrics.json.
int run_kohonen(const Config * config, Rng * rng, const Results * results);

// Kohonen helpers, exported for tests/test_main.c
// start * (end / start)^fraction: exponential decay from start (fraction 0) to end (fraction 1)
double kohonen_decay(double start, double end, double fraction);
// kohonen_decay of the radius, never below radius_final
double kohonen_radius(double radius0, double radius_final, double fraction);
// Weight of a neuron at squared grid distance d2 from the winner: step (gaussian 0) 1 if d2 <= radius^2 else 0;
// gaussian exp(-d2 / (2 radius^2))
double kohonen_neighbor_weight(int d2, double radius, int gaussian);

// Oja's rule for one neuron: uniform start scaled to length 1, shuffled epochs, exponentially decaying eta, final
// renormalization to length 1 and the D-02 orientation (largest-|value| coefficient positive). Writes weights.csv,
// index.csv, trace.csv and metrics.json.
int run_oja(const Config * config, Rng * rng, const Results * results);

// Oja helpers, exported for tests/test_main.c
// Negates w when its largest-|value| coefficient is negative (lowest index on ties); returns 1 if it negated
int oja_orient(double w[], int n);

// Discrete Hopfield network: Hebb W with a zero diagonal, async (reference) or sync updates, energy per step, two-cycle
// detection in sync, final state classified as stored / inverse / mixture / other. Task "recall" writes stored.csv,
// overlaps.csv, trials.csv, trace.csv, states.csv and metrics.json; task "capacity" writes capacity.csv and
// metrics.json.
// The core API lives in hopfield_core.h.
int run_hopfield(const Config * config, Rng * rng, const Results * results);

#endif //__MODELS_H__
