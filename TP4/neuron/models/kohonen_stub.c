// Deterministic stand-in for the Kohonen map (Phase 2 replaces the body): a k x k grid whose prototypes are
// samples picked by the run's Rng, and every sample assigned to its nearest prototype. It exercises the config,
// the input loader, the Rng and the writers.

#include "../io/matrix.h"
#include "models.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#define METRICS_COUNT 8


// Largest k with k * k <= n
static int integer_sqrt(int n) {
  int k = 0;
  while ((k + 1) <= n / (k + 1)) k++;
  return k;
}


// grid_k from the config, checked against the number of samples before anything is allocated
static int read_grid_k(const Config * config, int n_samples, int * grid_k) {
  if (!config_get_int(config, "grid_k", grid_k)) return 0;
  int max = integer_sqrt(n_samples);
  if (*grid_k < 1 || *grid_k > max) {
    fprintf(stderr, "%s: grid_k must be between 1 and %d\n", config->path, max);
    return 0;
  }
  return 1;
}


// The first grid_k * grid_k entries of a shuffled 0..n-1 pick the rows that start as prototypes
static int pick_prototypes(Rng * rng, const Matrix * input, int n_neurons, double prototypes[]) {
  int * order = malloc((size_t) input->n_rows * sizeof(int));
  if (order == NULL) {
    fprintf(stderr, "kohonen: couldn't allocate the sample order\n");
    return 0;
  }
  for (int i = 0; i < input->n_rows; i++) order[i] = i;
  rng_shuffle(rng, order, input->n_rows);

  for (int neuron = 0; neuron < n_neurons; neuron++) {
    for (int j = 0; j < input->n_cols; j++) {
      prototypes[(size_t) neuron * input->n_cols + j] = input->data[(size_t) order[neuron] * input->n_cols + j];
    }
  }
  free(order);
  return 1;
}


static double distance(const double a[], const double b[], int n) {
  double sum = 0;
  for (int j = 0; j < n; j++) sum += (a[j] - b[j]) * (a[j] - b[j]);
  return sqrt(sum);
}


// Index of the prototype closest to sample; the lowest index wins a tie
static int nearest(const double sample[], const double prototypes[], int n_neurons, int n_cols, double * best) {
  int winner = 0;
  *best = distance(sample, prototypes, n_cols);
  for (int neuron = 1; neuron < n_neurons; neuron++) {
    double d = distance(sample, prototypes + (size_t) neuron * n_cols, n_cols);
    if (d < *best) {
      *best = d;
      winner = neuron;
    }
  }
  return winner;
}


// prototypes.csv: neuron, row, col, then the prototype's features
static int write_prototypes(const Results * results, const Matrix * input, int grid_k, const double prototypes[]) {
  int n_neurons = grid_k * grid_k;
  int width = input->n_cols + 3;
  double * table = malloc((size_t) n_neurons * width * sizeof(double));
  const char ** header = malloc((size_t) width * sizeof(char *));
  int ok = table != NULL && header != NULL;
  if (!ok) fprintf(stderr, "kohonen: couldn't allocate the prototype table\n");

  if (ok) {
    header[0] = "neuron";
    header[1] = "row";
    header[2] = "col";
    for (int j = 0; j < input->n_cols; j++) header[3 + j] = input->names[j];
    for (int neuron = 0; neuron < n_neurons; neuron++) {
      double * line = table + (size_t) neuron * width;
      line[0] = neuron;
      line[1] = neuron / grid_k;
      line[2] = neuron % grid_k;
      for (int j = 0; j < input->n_cols; j++) line[3 + j] = prototypes[(size_t) neuron * input->n_cols + j];
    }
    ok = results_write_table(results, "prototypes.csv", width, header, n_neurons, table);
  }
  free(table);
  free(header);
  return ok;
}


// assignments.csv: sample, bmu, row, col, distance; also counts the neurons that won at least one sample
static int write_assignments(const Config * config, const Results * results, const Matrix * input, int grid_k,
                             const double prototypes[]) {
  int n = input->n_rows;
  int n_neurons = grid_k * grid_k;
  double * table = malloc((size_t) n * 5 * sizeof(double));
  int * wins = calloc((size_t) n_neurons, sizeof(int));
  int ok = table != NULL && wins != NULL;
  if (!ok) fprintf(stderr, "kohonen: couldn't allocate the assignment table\n");

  double total = 0;
  if (ok) {
    for (int i = 0; i < n; i++) {
      double d;
      int bmu = nearest(input->data + (size_t) i * input->n_cols, prototypes, n_neurons, input->n_cols, &d);
      wins[bmu]++;
      total += d;
      double * line = table + (size_t) i * 5;
      line[0] = i;
      line[1] = bmu;
      line[2] = bmu / grid_k;
      line[3] = bmu % grid_k;
      line[4] = d;
    }

    int occupied = 0;
    for (int neuron = 0; neuron < n_neurons; neuron++) {
      if (wins[neuron] > 0) occupied++;
    }

    const char * header[] = { "sample", "bmu", "row", "col", "distance" };
    const Metric metrics[METRICS_COUNT] = {
      { "model", "kohonen", 0 },
      { "seed", NULL, config->seed },
      { "n_samples", NULL, n },
      { "n_features", NULL, input->n_cols },
      { "grid_k", NULL, grid_k },
      { "n_neurons", NULL, n_neurons },
      { "occupied_neurons", NULL, occupied },
      { "mean_bmu_distance", NULL, total / n },
    };
    ok = results_write_table(results, "assignments.csv", 5, header, n, table)
      && results_write_metrics(results, metrics, METRICS_COUNT);
  }
  free(table);
  free(wins);
  return ok;
}


int run_kohonen(const Config * config, Rng * rng, const Results * results) {
  Matrix input;
  if (!matrix_load(config->input, &input)) return 0;

  int grid_k;
  int ok = read_grid_k(config, input.n_rows, &grid_k);

  double * prototypes = NULL;
  if (ok) {
    prototypes = malloc((size_t) grid_k * grid_k * input.n_cols * sizeof(double));
    ok = prototypes != NULL;
    if (!ok) fprintf(stderr, "kohonen: couldn't allocate the prototypes\n");
  }

  ok = ok && pick_prototypes(rng, &input, grid_k * grid_k, prototypes);
  ok = ok && write_prototypes(results, &input, grid_k, prototypes);
  ok = ok && write_assignments(config, results, &input, grid_k, prototypes);

  free(prototypes);
  matrix_free(&input);
  return ok;
}
