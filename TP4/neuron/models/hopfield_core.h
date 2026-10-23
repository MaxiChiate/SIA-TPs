#ifndef __HOPFIELD_CORE_H__
#define __HOPFIELD_CORE_H__

// Pure core of the discrete Hopfield network: neurons are +-1, W = sum over the stored patterns of xi xi^T with a
// zero diagonal and no 1/N, so every entry of W is an integer held exactly in a double. A neuron with field
// h_i = sum_j w_ij s_j takes +1 if h_i > 0, -1 if h_i < 0 and keeps its state if h_i == 0 (the course's rule). The
// energy is E = -1/2 s^T W s. Nothing here reads or writes files; models/hopfield.c does the I/O. The core takes a
// generic P x N matrix of +-1 and never assumes N = 25.

#include "../rng.h"

typedef enum {
  HOPFIELD_STORED = 0,
  HOPFIELD_INVERSE = 1,
  HOPFIELD_MIXTURE = 2,
  HOPFIELD_OTHER = 3,
} HopfieldClass;

#define HOPFIELD_TRACE_WIDTH 6 // trial, step, sweep, neuron, changed, energy

// Rows of (trial, step, sweep, neuron, changed, energy) in one growing buffer; zero it and set max_rows before use
typedef struct {
  double * data;
  long long rows;
  long long capacity;
  long long max_rows;
  double trial; // written in column 0 of every appended row
} HopfieldTrace;

typedef struct {
  int converged;         // 1 if the last step or sweep changed nothing
  int cycle;             // 2 if a synchronous two-cycle was detected, else 0
  int sweeps;            // sweeps (async) or steps (sync) taken, counting the confirming one
  long long updates;     // sweeps * n
  long long flips;       // neurons that changed their state
  int energy_increases;  // times the energy rose by more than 1e-9 between two consecutive logged values
  double e_start;
  double e_final;
} HopfieldOutcome;

// Appends one row (the trial comes from trace->trial); returns 0 and appends nothing if the row would pass
// max_rows or the allocation fails
int hopfield_trace_append(HopfieldTrace * trace, double step, double sweep, double neuron, double changed,
                          double energy);

void hopfield_trace_free(HopfieldTrace * trace);

// w (n x n) = sum over the p rows of patterns (p x n) of xi_i xi_j, with w_ii = 0
void hopfield_hebb(const double patterns[], int p, int n, double w[]);

// h = W s
void hopfield_fields(const double w[], int n, const double s[], double h[]);

// -1/2 s^T W s, computed from scratch
double hopfield_energy(const double w[], int n, const double s[]);

// Asynchronous dynamics, the reference: every sweep visits the neurons in a fresh random order (rng_shuffle of
// order, which holds 0..n-1 on entry), updating each one at once. Stops at the first sweep without a flip
// (converged) or after max_sweeps. s is the state (updated in place), h and order are scratch of n entries. The
// energy is kept incrementally (E += 2 s_i h_i on a flip) and a row per visit goes to trace if it is not NULL.
// Returns 0 only if a trace append fails.
int hopfield_async_run(const double w[], int n, double s[], double h[], int order[], Rng * rng, int max_sweeps,
                       HopfieldTrace * trace, HopfieldOutcome * out);

// One synchronous step s -> sign(W s), a zero field keeping the state; next must not alias s. Returns how many
// neurons changed.
int hopfield_sync_step(const double w[], int n, const double s[], double next[]);

// Synchronous dynamics, the course's comparison: repeated hopfield_sync_step, the energy recomputed from scratch at
// every step (it may rise). Stops when a step changes nothing (converged) or when the new state equals the state
// two steps back (a two-cycle: cycle 2, converged 0, the detection state is the final state), or after max_sweeps.
// Cycles longer than 2 are not searched for; the cap catches them as non-converged. scratch holds 2n doubles. s ends
// as the final state. Returns 0 only if a trace append fails.
int hopfield_sync_run(const double w[], int n, double s[], double scratch[], int max_sweeps, HopfieldTrace * trace,
                      HopfieldOutcome * out);

// Classifies a final state against the p stored patterns (p x n), in this order: stored (state == xi_a; wins over
// the inverse of another pattern), inverse (state == -xi_a), mixture (state == sign(sa xi_a + sb xi_b + sc xi_c)
// for some triple a < b < c and signs), other. match and sign are filled with the indices and signs involved (-1
// and 0 where unused): a stored or inverse state uses slot 0 only. With p < 3 no mixture is possible.
HopfieldClass hopfield_classify(const double patterns[], int p, int n, const double s[], int match[3], int sign[3]);

// min over i of xi_i h_i(xi) and, in wrong, the number of i with xi_i h_i < 0. The pattern is a fixed point iff
// wrong == 0, because a zero field keeps the state.
double hopfield_min_margin(const double w[], int n, const double pattern[], int * wrong);

#endif //__HOPFIELD_CORE_H__
