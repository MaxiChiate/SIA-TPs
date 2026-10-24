#ifndef __HOPFIELD_CORE_H__
#define __HOPFIELD_CORE_H__

// Pure core of the discrete Hopfield network: neurons are +-1. Two learning rules build W (n x n): Hebb
// (hopfield_hebb) is W = sum over the stored patterns of xi xi^T with a zero diagonal and no 1/N, so every entry is
// an integer held exactly in a double; the pseudo-inverse / projection rule (hopfield_pinv) is
// W = X^T (X X^T)^-1 X with the diagonal left non-zero (D-07), a real-valued projection matrix whose entries are
// not integers in general. A neuron with field h_i = sum_j w_ij s_j takes +1 if h_i > 0, -1 if h_i < 0 and keeps its
// state if h_i == 0 (the course's rule). The energy is E = -1/2 s^T W s, kept incrementally in the dynamics with a
// correction term for a non-zero diagonal (see hopfield_async_run) so it matches the from-scratch energy for either
// rule. Nothing here reads or writes files; models/hopfield.c does the I/O. The core takes a generic P x N matrix
// of +-1 and never assumes N = 25.

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

// w (n x n) = sum over the p rows of patterns (p x n) of xi_i xi_j, with w_ii = 0; every entry is an exact integer
// held in a double (D-06: Hebb is the only rule with this property)
void hopfield_hebb(const double patterns[], int p, int n, double w[]);

// The pseudo-inverse / projection rule (D-06): w (n x n) = X^T (X X^T)^-1 X, where X is patterns (p x n). Builds the
// p x p Gram matrix G = X X^T and inverts it by Gauss-Jordan elimination with partial pivoting in scratch (work
// space of at least 2*p*p doubles, the augmented [G | I] matrix); returns 0 and leaves w unwritten if the largest
// available pivot magnitude falls below a fixed tolerance (G singular or too ill-conditioned - the stored patterns
// are not linearly independent), 1 otherwise. The diagonal of w is left non-zero (D-07): it is the projection
// property that makes every stored pattern an exact fixed point, the real-valued remedy for Hebb's failure on
// correlated patterns. Same flat row-major layout as hopfield_hebb; does no I/O.
int hopfield_pinv(const double patterns[], int p, int n, double w[], double scratch[]);

// h = W s
void hopfield_fields(const double w[], int n, const double s[], double h[]);

// -1/2 s^T W s, computed from scratch
double hopfield_energy(const double w[], int n, const double s[]);

// Asynchronous dynamics, the reference: every sweep visits the neurons in a fresh random order (rng_shuffle of
// order, which holds 0..n-1 on entry), updating each one at once. Stops at the first sweep without a flip
// (converged) or after max_sweeps. s is the state (updated in place), h and order are scratch of n entries. The
// energy is kept incrementally (E += 2 s_i h_i - 2 w_ii on a flip, which reduces to the zero-diagonal Hebb formula
// when w_ii == 0) and a row per visit goes to trace if it is not NULL. Returns 0 only if a trace append fails.
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

// min over i of xi_i h_i(xi) and, in wrong, the number of i with xi_i h_i < -ENERGY_TOLERANCE. The pattern is a
// fixed point iff wrong == 0, because a zero field keeps the state; the tolerance (rather than a strict < 0) lets a
// true pinv fixed point land a hair below 0 from floating-point rounding without being counted as wrong, while
// leaving Hebb's exact integer margins unchanged.
double hopfield_min_margin(const double w[], int n, const double pattern[], int * wrong);

#endif //__HOPFIELD_CORE_H__
