// Pure core of the discrete Hopfield network (see hopfield_core.h): Hebb training, fields, energy, the asynchronous
// and synchronous dynamics with an optional per-step trace, the classifier of a final state and the stability margin.

#include "hopfield_core.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>

#define ENERGY_TOLERANCE 1e-9


int hopfield_trace_append(HopfieldTrace * trace, double step, double sweep, double neuron, double changed,
                          double energy) {
  if (trace->rows >= trace->max_rows) return 0;
  if (trace->rows == trace->capacity) {
    long long capacity = trace->capacity == 0 ? 1024 : trace->capacity * 2;
    if (capacity > trace->max_rows) capacity = trace->max_rows;
    double * grown = realloc(trace->data, (size_t) capacity * HOPFIELD_TRACE_WIDTH * sizeof(double));
    if (grown == NULL) return 0;
    trace->data = grown;
    trace->capacity = capacity;
  }
  double * line = trace->data + (size_t) trace->rows * HOPFIELD_TRACE_WIDTH;
  line[0] = trace->trial;
  line[1] = step;
  line[2] = sweep;
  line[3] = neuron;
  line[4] = changed;
  line[5] = energy;
  trace->rows++;
  return 1;
}


void hopfield_trace_free(HopfieldTrace * trace) {
  free(trace->data);
  trace->data = NULL;
  trace->rows = 0;
  trace->capacity = 0;
}


void hopfield_hebb(const double patterns[], int p, int n, double w[]) {
  for (int i = 0; i < n; i++) {
    for (int j = 0; j < n; j++) {
      double sum = 0;
      if (i != j) {
        for (int a = 0; a < p; a++) sum += patterns[(size_t) a * n + i] * patterns[(size_t) a * n + j];
      }
      w[(size_t) i * n + j] = sum;
    }
  }
}


void hopfield_fields(const double w[], int n, const double s[], double h[]) {
  for (int i = 0; i < n; i++) {
    double sum = 0;
    for (int j = 0; j < n; j++) sum += w[(size_t) i * n + j] * s[j];
    h[i] = sum;
  }
}


double hopfield_energy(const double w[], int n, const double s[]) {
  double sum = 0;
  for (int i = 0; i < n; i++) {
    double row = 0;
    for (int j = 0; j < n; j++) row += w[(size_t) i * n + j] * s[j];
    sum += s[i] * row;
  }
  return -0.5 * sum;
}


// The state a neuron takes under field h: the sign of h, and its current value when h == 0
static double next_state(double h, double current) {
  if (h > 0) return 1;
  if (h < 0) return -1;
  return current;
}


int hopfield_async_run(const double w[], int n, double s[], double h[], int order[], Rng * rng, int max_sweeps,
                       HopfieldTrace * trace, HopfieldOutcome * out) {
  memset(out, 0, sizeof(*out));
  hopfield_fields(w, n, s, h);
  double energy = hopfield_energy(w, n, s);
  out->e_start = energy;
  long long step = 0;
  if (trace != NULL && !hopfield_trace_append(trace, 0, 0, -1, 0, energy)) return 0;

  for (int sweep = 1; sweep <= max_sweeps; sweep++) {
    rng_shuffle(rng, order, n);
    long long flips_before = out->flips;
    for (int v = 0; v < n; v++) {
      int i = order[v];
      double next = next_state(h[i], s[i]);
      int changed = next != s[i];
      double previous = energy;
      if (changed) {
        energy += 2 * s[i] * h[i]; // strictly negative: the flip follows the sign of h_i
        double delta = next - s[i];
        for (int j = 0; j < n; j++) h[j] += w[(size_t) j * n + i] * delta;
        s[i] = next;
        out->flips++;
      }
      if (energy > previous + ENERGY_TOLERANCE) out->energy_increases++;
      step++;
      if (trace != NULL && !hopfield_trace_append(trace, (double) step, sweep, i, changed, energy)) return 0;
    }
    out->sweeps = sweep;
    if (out->flips == flips_before) {
      out->converged = 1;
      break;
    }
  }
  out->updates = (long long) out->sweeps * n;
  out->e_final = energy;
  return 1;
}


int hopfield_sync_step(const double w[], int n, const double s[], double next[]) {
  int changed = 0;
  for (int i = 0; i < n; i++) {
    double h = 0;
    for (int j = 0; j < n; j++) h += w[(size_t) i * n + j] * s[j];
    next[i] = next_state(h, s[i]);
    if (next[i] != s[i]) changed++;
  }
  return changed;
}


int hopfield_sync_run(const double w[], int n, double s[], double scratch[], int max_sweeps, HopfieldTrace * trace,
                      HopfieldOutcome * out) {
  memset(out, 0, sizeof(*out));
  double * previous = scratch;    // the state two steps back, valid from the second step
  double * next = scratch + n;
  double energy = hopfield_energy(w, n, s);
  out->e_start = energy;
  if (trace != NULL && !hopfield_trace_append(trace, 0, 0, -1, 0, energy)) return 0;

  for (int t = 1; t <= max_sweeps; t++) {
    int changed = hopfield_sync_step(w, n, s, next);
    double after = hopfield_energy(w, n, next);
    if (after > energy + ENERGY_TOLERANCE) out->energy_increases++;
    energy = after;
    out->sweeps = t;
    out->flips += changed;
    if (trace != NULL && !hopfield_trace_append(trace, t, t, -1, changed, energy)) return 0;

    if (changed == 0) {
      out->converged = 1;
      break;
    }
    if (t >= 2 && memcmp(next, previous, (size_t) n * sizeof(double)) == 0) {
      memcpy(s, next, (size_t) n * sizeof(double)); // the detection state is the final state
      out->cycle = 2;
      break;
    }
    memcpy(previous, s, (size_t) n * sizeof(double));
    memcpy(s, next, (size_t) n * sizeof(double));
  }
  out->updates = (long long) out->sweeps * n;
  out->e_final = energy;
  return 1;
}


// The sign of sa xi_a + sb xi_b + sc xi_c at pixel j; three +-1 never sum to 0
static double mixture_pixel(const double patterns[], int n, int a, int b, int c, int sa, int sb, int sc, int j) {
  double sum = sa * patterns[(size_t) a * n + j] + sb * patterns[(size_t) b * n + j]
             + sc * patterns[(size_t) c * n + j];
  return sum > 0 ? 1 : -1;
}


HopfieldClass hopfield_classify(const double patterns[], int p, int n, const double s[], int match[3], int sign[3]) {
  for (int k = 0; k < 3; k++) {
    match[k] = -1;
    sign[k] = 0;
  }
  // d = xi_a . s is an integer, so == n and == -n are exact
  for (int a = 0; a < p; a++) {
    double d = 0;
    for (int j = 0; j < n; j++) d += patterns[(size_t) a * n + j] * s[j];
    if (d == n) {
      match[0] = a;
      sign[0] = 1;
      return HOPFIELD_STORED;
    }
  }
  for (int a = 0; a < p; a++) {
    double d = 0;
    for (int j = 0; j < n; j++) d += patterns[(size_t) a * n + j] * s[j];
    if (d == -n) {
      match[0] = a;
      sign[0] = -1;
      return HOPFIELD_INVERSE;
    }
  }
  for (int a = 0; a < p; a++) {
    for (int b = a + 1; b < p; b++) {
      for (int c = b + 1; c < p; c++) {
        for (int bits = 0; bits < 8; bits++) {
          int sa = (bits & 1) ? -1 : 1;
          int sb = (bits & 2) ? -1 : 1;
          int sc = (bits & 4) ? -1 : 1;
          int equal = 1;
          for (int j = 0; j < n && equal; j++) {
            equal = mixture_pixel(patterns, n, a, b, c, sa, sb, sc, j) == s[j];
          }
          if (equal) {
            match[0] = a;
            match[1] = b;
            match[2] = c;
            sign[0] = sa;
            sign[1] = sb;
            sign[2] = sc;
            return HOPFIELD_MIXTURE;
          }
        }
      }
    }
  }
  return HOPFIELD_OTHER;
}


double hopfield_min_margin(const double w[], int n, const double pattern[], int * wrong) {
  double margin = 0;
  *wrong = 0;
  for (int i = 0; i < n; i++) {
    double h = 0;
    for (int j = 0; j < n; j++) h += w[(size_t) i * n + j] * pattern[j];
    double m = pattern[i] * h;
    if (i == 0 || m < margin) margin = m;
    if (m < 0) (*wrong)++;
  }
  return margin;
}
