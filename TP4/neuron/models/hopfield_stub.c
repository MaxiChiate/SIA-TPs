// Deterministic stand-in for the Hopfield network (Phases 4 and 5 replace the body): every stored pattern is
// corrupted by flipping a seeded set of pixels per noise level, and the overlap with the original is measured.
// There is no recall yet. It exercises the config, the input loader, the Rng and the writers.

#include "../io/matrix.h"
#include "models.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#define METRICS_COUNT 6
#define QUERY_COLUMNS 4


static int is_pm_one(const Matrix * patterns) {
  for (size_t i = 0; i < (size_t) patterns->n_rows * patterns->n_cols; i++) {
    if (patterns->data[i] != -1 && patterns->data[i] != 1) return 0;
  }
  return 1;
}


// noise_levels from the config; every level must be a fraction in [0, 1]
static int read_noise_levels(const Config * config, double levels[], int * n_levels) {
  if (!config_get_number_array(config, "noise_levels", levels, CONFIG_ARRAY_MAX, n_levels)) return 0;
  for (int l = 0; l < *n_levels; l++) {
    if (levels[l] < 0 || levels[l] > 1) {
      fprintf(stderr, "%s: noise_levels[%d] = %g is outside [0, 1]\n", config->path, l, levels[l]);
      return 0;
    }
  }
  return 1;
}


// Flips the sign of the first k entries of a shuffled 0..n-1 in noisy, a copy of pattern
static void corrupt(Rng * rng, const double pattern[], int n, int k, int order[], double noisy[]) {
  for (int j = 0; j < n; j++) {
    order[j] = j;
    noisy[j] = pattern[j];
  }
  rng_shuffle(rng, order, n);
  for (int f = 0; f < k; f++) noisy[order[f]] = -noisy[order[f]];
}


static double overlap(const double a[], const double b[], int n) {
  double dot = 0;
  for (int j = 0; j < n; j++) dot += a[j] * b[j];
  return dot / n;
}


// queries.csv: pattern, noise, flipped, overlap for every pattern and level; returns the mean overlap in mean
static int write_queries(const Results * results, Rng * rng, const Matrix * patterns, const double levels[],
                         int n_levels, double * mean) {
  int n = patterns->n_cols;
  int n_rows = patterns->n_rows * n_levels;
  double * table = malloc((size_t) n_rows * QUERY_COLUMNS * sizeof(double));
  int * order = malloc((size_t) n * sizeof(int));
  double * noisy = malloc((size_t) n * sizeof(double));
  int ok = table != NULL && order != NULL && noisy != NULL;
  if (!ok) fprintf(stderr, "hopfield: couldn't allocate the query table\n");

  if (ok) {
    double total = 0;
    for (int p = 0; p < patterns->n_rows; p++) {
      const double * pattern = patterns->data + (size_t) p * n;
      for (int l = 0; l < n_levels; l++) {
        int k = (int) lround(levels[l] * n);
        corrupt(rng, pattern, n, k, order, noisy);
        double o = overlap(pattern, noisy, n);
        total += o;

        double * line = table + (size_t) (p * n_levels + l) * QUERY_COLUMNS;
        line[0] = p;
        line[1] = levels[l];
        line[2] = k;
        line[3] = o;
      }
    }
    *mean = total / n_rows;

    const char * header[QUERY_COLUMNS] = { "pattern", "noise", "flipped", "overlap" };
    ok = results_write_table(results, "queries.csv", QUERY_COLUMNS, header, n_rows, table);
  }
  free(table);
  free(order);
  free(noisy);
  return ok;
}


int run_hopfield(const Config * config, Rng * rng, const Results * results) {
  Matrix patterns;
  if (!matrix_load(config->input, &patterns)) return 0;

  int ok = is_pm_one(&patterns);
  if (!ok) fprintf(stderr, "%s: patterns must contain only -1 and 1\n", config->input);

  double levels[CONFIG_ARRAY_MAX];
  int n_levels = 0;
  ok = ok && read_noise_levels(config, levels, &n_levels);

  double mean = 0;
  ok = ok && write_queries(results, rng, &patterns, levels, n_levels, &mean);

  if (ok) {
    const Metric metrics[METRICS_COUNT] = {
      { "model", "hopfield", 0 },
      { "seed", NULL, config->seed },
      { "n_patterns", NULL, patterns.n_rows },
      { "n_neurons", NULL, patterns.n_cols },
      { "n_levels", NULL, n_levels },
      { "mean_overlap", NULL, mean },
    };
    ok = results_write_metrics(results, metrics, METRICS_COUNT);
  }

  matrix_free(&patterns);
  return ok;
}
