// Deterministic stand-in for Oja's rule (Phase 3 replaces the body): a random unit vector from the run's Rng,
// and every input row projected onto it. It exercises the config, the input loader, the Rng and the writers.

#include "../io/matrix.h"
#include "models.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#define METRICS_COUNT 7


static double norm(const double values[], int n) {
  double sum = 0;
  for (int j = 0; j < n; j++) sum += values[j] * values[j];
  return sqrt(sum);
}


// Uniform in [-0.5, 0.5) per component, scaled to length 1; a zero vector cannot be scaled
static int random_unit_vector(Rng * rng, double w[], int n) {
  for (int j = 0; j < n; j++) w[j] = rng_uniform(rng) - 0.5;
  double length = norm(w, n);
  if (length == 0) {
    fprintf(stderr, "oja: the random vector has zero length\n");
    return 0;
  }
  for (int j = 0; j < n; j++) w[j] /= length;
  return 1;
}


static void project(const Matrix * input, const double w[], double index[]) {
  for (int i = 0; i < input->n_rows; i++) {
    double dot = 0;
    for (int j = 0; j < input->n_cols; j++) dot += w[j] * input->data[(size_t) i * input->n_cols + j];
    index[i] = dot;
  }
}


// Population mean and standard deviation
static void mean_and_std(const double values[], int n, double * mean, double * std) {
  double sum = 0;
  for (int i = 0; i < n; i++) sum += values[i];
  *mean = sum / n;

  double squares = 0;
  for (int i = 0; i < n; i++) squares += (values[i] - *mean) * (values[i] - *mean);
  *std = sqrt(squares / n);
}


static int write_outputs(const Config * config, const Results * results, const Matrix * input, const double w[],
                         const double index[]) {
  int n = input->n_rows;
  double mean, std;
  mean_and_std(index, n, &mean, &std);

  double * samples = malloc((size_t) n * 2 * sizeof(double));
  if (samples == NULL) {
    fprintf(stderr, "oja: couldn't allocate the index table\n");
    return 0;
  }
  for (int i = 0; i < n; i++) {
    samples[2 * i] = i;
    samples[2 * i + 1] = index[i];
  }

  const char * index_header[] = { "sample", "index" };
  const Metric metrics[METRICS_COUNT] = {
    { "model", "oja", 0 },
    { "seed", NULL, config->seed },
    { "n_samples", NULL, n },
    { "n_features", NULL, input->n_cols },
    { "w_norm", NULL, norm(w, input->n_cols) },
    { "index_mean", NULL, mean },
    { "index_std", NULL, std },
  };

  int ok = results_write_table(results, "weights.csv", input->n_cols, (const char * const *) input->names, 1, w)
        && results_write_table(results, "index.csv", 2, index_header, n, samples)
        && results_write_metrics(results, metrics, METRICS_COUNT);
  free(samples);
  return ok;
}


int run_oja(const Config * config, Rng * rng, const Results * results) {
  Matrix input;
  if (!matrix_load(config->input, &input)) return 0;

  double * w = malloc((size_t) input.n_cols * sizeof(double));
  double * index = malloc((size_t) input.n_rows * sizeof(double));
  int ok = w != NULL && index != NULL;
  if (!ok) fprintf(stderr, "oja: couldn't allocate the weights\n");

  ok = ok && random_unit_vector(rng, w, input.n_cols);
  if (ok) project(&input, w, index);
  ok = ok && write_outputs(config, results, &input, w, index);

  free(w);
  free(index);
  matrix_free(&input);
  return ok;
}
