// Kohonen self-organising map: a k x k grid of prototypes that starts as k * k training samples picked by the
// run's Rng and is trained online. Every epoch visits all the samples once in a shuffled order; for each one the
// winner (BMU) and its grid neighbors move toward the sample. The learning rate eta and the neighborhood radius
// both decay exponentially from their start value to their final value over the whole run. The neighborhood is
// either a step (every neuron within grid distance R of the winner) or a gaussian of sigma = R. After training
// it measures the quantization error, the topographic error and the occupancy of every neuron on the training
// samples, and writes them with the prototypes, the assignments and a per-epoch trace.

#include "../io/matrix.h"
#include "models.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define GRID_K_MAX 32
#define EPOCHS_MAX 100000
#define METRICS_COUNT 19
#define TRACE_WIDTH 5 // epoch, eta, radius, qe, te


// The seven Kohonen keys of the config, already checked
typedef struct {
  int grid_k;
  int gaussian; // 0: step neighborhood, 1: gaussian
  int epochs;
  double radius0;
  double radius_final;
  double eta0;
  double eta_final;
  long long steps; // epochs * n_samples, the number of weight updates of the run
} SomParams;


// The seven keys, checked before anything is allocated; prints "<config path>: <key> must ..." and returns 0 on the
// first value that doesn't fit
static int read_params(const Config * config, int n_rows, SomParams * params) {
  const char * neighborhood;
  if (!config_get_int(config, "grid_k", &params->grid_k)
      || !config_get_string(config, "neighborhood", &neighborhood)
      || !config_get_number(config, "radius0", &params->radius0)
      || !config_get_number(config, "radius_final", &params->radius_final)
      || !config_get_number(config, "eta0", &params->eta0)
      || !config_get_number(config, "eta_final", &params->eta_final)
      || !config_get_int(config, "epochs", &params->epochs)) {
    return 0;
  }

  if (params->grid_k < 2 || params->grid_k > GRID_K_MAX) {
    fprintf(stderr, "%s: grid_k must be between 2 and %d\n", config->path, GRID_K_MAX);
    return 0;
  }
  if (strcmp(neighborhood, "step") == 0) {
    params->gaussian = 0;
  } else if (strcmp(neighborhood, "gaussian") == 0) {
    params->gaussian = 1;
  } else {
    fprintf(stderr, "%s: neighborhood must be \"step\" or \"gaussian\"\n", config->path);
    return 0;
  }
  if (params->epochs < 1 || params->epochs > EPOCHS_MAX) {
    fprintf(stderr, "%s: epochs must be between 1 and %d\n", config->path, EPOCHS_MAX);
    return 0;
  }
  if (n_rows < 2) {
    fprintf(stderr, "%s: the input needs at least 2 samples\n", config->path);
    return 0;
  }
  if (params->radius0 < 1) {
    fprintf(stderr, "%s: radius0 must be >= 1\n", config->path);
    return 0;
  }
  double radius_low = params->gaussian ? 0 : 1; // the gaussian needs > 0, the step >= 1
  if (params->radius_final > params->radius0 || params->radius_final < radius_low
      || (params->gaussian && params->radius_final == 0)) {
    fprintf(stderr, "%s: radius_final must be %s and <= radius0\n", config->path,
            params->gaussian ? "> 0 for the gaussian neighborhood" : ">= 1 for the step neighborhood");
    return 0;
  }
  if (!(params->eta0 > 0 && params->eta0 < 1)) {
    fprintf(stderr, "%s: eta0 must be > 0 and < 1\n", config->path);
    return 0;
  }
  if (!(params->eta_final > 0 && params->eta_final <= params->eta0)) {
    fprintf(stderr, "%s: eta_final must be > 0 and <= eta0\n", config->path);
    return 0;
  }
  params->steps = (long long) params->epochs * n_rows;
  return 1;
}


// Neuron i starts as row order[i % n]; the order is shuffled at i = 0 and again each time i wraps past n, so a
// grid with more neurons than samples repeats samples and never reads past the array
static int pick_prototypes(Rng * rng, const Matrix * input, int n_neurons, double prototypes[]) {
  int n = input->n_rows;
  int * order = malloc((size_t) n * sizeof(int));
  if (order == NULL) {
    fprintf(stderr, "kohonen: couldn't allocate the sample order\n");
    return 0;
  }
  for (int i = 0; i < n; i++) order[i] = i;

  for (int neuron = 0; neuron < n_neurons; neuron++) {
    if (neuron % n == 0) rng_shuffle(rng, order, n);
    for (int j = 0; j < input->n_cols; j++) {
      prototypes[(size_t) neuron * input->n_cols + j] = input->data[(size_t) order[neuron % n] * input->n_cols + j];
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


// The winner and the runner-up (second-smallest distance); the lowest index wins a tie in both. The runner-up is
// never the winner, so it needs at least two neurons.
static int nearest_two(const double sample[], const double prototypes[], int n_neurons, int n_cols, double * best,
                       int * second) {
  int winner = 0;
  *second = -1;
  double second_distance = INFINITY;
  *best = distance(sample, prototypes, n_cols);
  for (int neuron = 1; neuron < n_neurons; neuron++) {
    double d = distance(sample, prototypes + (size_t) neuron * n_cols, n_cols);
    if (d < *best) {
      second_distance = *best;
      *second = winner;
      *best = d;
      winner = neuron;
    } else if (d < second_distance || *second < 0) {
      second_distance = d;
      *second = neuron;
    }
  }
  return winner;
}


// start * (end / start)^fraction: exponential decay from start (fraction 0) to end (fraction 1)
double kohonen_decay(double start, double end, double fraction) {
  return start * pow(end / start, fraction);
}


// The neighborhood radius at a point of the run. The clamp keeps the last steps at radius_final when pow lands
// one ulp below it.
double kohonen_radius(double radius0, double radius_final, double fraction) {
  return fmax(kohonen_decay(radius0, radius_final, fraction), radius_final);
}


// Weight of a neuron at squared grid distance d2 from the winner. Step: 1 within radius (<=, so radius 1 reaches the
// four adjacent cells and not the diagonals), else 0. Gaussian: exp(-d2 / 2 sigma^2) with sigma = radius.
double kohonen_neighbor_weight(int d2, double radius, int gaussian) {
  if (gaussian) return exp(-d2 / (2 * radius * radius));
  return d2 <= radius * radius + 1e-12 ? 1.0 : 0.0;
}


// Measures on the training samples. qe: mean distance to the winner. te: fraction of samples whose winner and
// runner-up are not 4-adjacent on the grid (a diagonal counts as an error). Each output array is optional.
typedef struct {
  double qe;
  double te;
  int occupied;
  int max_hits;
  int singletons;
} Measures;

static void measure(const Matrix * input, const double prototypes[], int k, Measures * out, int bmu[], int bmu2[],
                    double distances[], int hits[]) {
  int n = input->n_rows;
  int n_neurons = k * k;
  int n_cols = input->n_cols;
  double total = 0;
  int not_adjacent = 0;
  int * counts = hits;
  int * own = NULL;
  if (counts == NULL) {
    own = calloc((size_t) n_neurons, sizeof(int));
    counts = own;
  } else {
    memset(counts, 0, (size_t) n_neurons * sizeof(int));
  }

  for (int i = 0; i < n; i++) {
    double d;
    int second;
    int first = nearest_two(input->data + (size_t) i * n_cols, prototypes, n_neurons, n_cols, &d, &second);
    total += d;
    int dr = abs(first / k - second / k);
    int dc = abs(first % k - second % k);
    if (dr + dc != 1) not_adjacent++;
    if (counts != NULL) counts[first]++;
    if (bmu != NULL) bmu[i] = first;
    if (bmu2 != NULL) bmu2[i] = second;
    if (distances != NULL) distances[i] = d;
  }

  out->qe = total / n;
  out->te = (double) not_adjacent / n;
  out->occupied = 0;
  out->max_hits = 0;
  out->singletons = 0;
  if (counts != NULL) {
    for (int neuron = 0; neuron < n_neurons; neuron++) {
      if (counts[neuron] > 0) out->occupied++;
      if (counts[neuron] > out->max_hits) out->max_hits = counts[neuron];
      if (counts[neuron] == 1) out->singletons++;
    }
  }
  free(own);
}


// One trace row: epoch, eta, radius, then qe and te of the prototypes at that moment
static void trace_row(const Matrix * input, const double prototypes[], int k, int hits[], double trace[], int epoch,
                      double eta, double radius) {
  Measures m;
  measure(input, prototypes, k, &m, NULL, NULL, NULL, hits);
  double * line = trace + (size_t) epoch * TRACE_WIDTH;
  line[0] = epoch;
  line[1] = eta;
  line[2] = radius;
  line[3] = m.qe;
  line[4] = m.te;
}


// Online training: epochs passes over the samples in a fresh shuffled order each time. trace gets epochs + 1 rows:
// row 0 is the starting prototypes with eta0 and radius0, row e the state after epoch e with the eta and radius of
// that epoch's last step.
static int train(const SomParams * params, Rng * rng, const Matrix * input, double prototypes[], double trace[]) {
  int n = input->n_rows;
  int n_cols = input->n_cols;
  int k = params->grid_k;
  int n_neurons = k * k;

  int * order = malloc((size_t) n * sizeof(int));
  int * hits = malloc((size_t) n_neurons * sizeof(int));
  if (order == NULL || hits == NULL) {
    fprintf(stderr, "kohonen: couldn't allocate the training buffers\n");
    free(order);
    free(hits);
    return 0;
  }
  for (int i = 0; i < n; i++) order[i] = i;

  trace_row(input, prototypes, k, hits, trace, 0, params->eta0, params->radius0);
  long long step = 0;
  for (int epoch = 1; epoch <= params->epochs; epoch++) {
    rng_shuffle(rng, order, n);
    double eta = 0;
    double radius = 0;
    for (int i = 0; i < n; i++, step++) {
      double fraction = (double) step / (double) (params->steps - 1);
      eta = kohonen_decay(params->eta0, params->eta_final, fraction);
      radius = kohonen_radius(params->radius0, params->radius_final, fraction);

      const double * sample = input->data + (size_t) order[i] * n_cols;
      double best;
      int bmu = nearest(sample, prototypes, n_neurons, n_cols, &best);

      for (int neuron = 0; neuron < n_neurons; neuron++) {
        int dr = neuron / k - bmu / k;
        int dc = neuron % k - bmu % k;
        double h = kohonen_neighbor_weight(dr * dr + dc * dc, radius, params->gaussian);
        if (h == 0) continue;
        double * weights = prototypes + (size_t) neuron * n_cols;
        for (int j = 0; j < n_cols; j++) weights[j] += eta * h * (sample[j] - weights[j]);
      }
    }
    trace_row(input, prototypes, k, hits, trace, epoch, eta, radius);
  }
  free(order);
  free(hits);
  return 1;
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


// occupancy.csv: neuron, row, col, hits
static int write_occupancy(const Results * results, int grid_k, const int hits[]) {
  int n_neurons = grid_k * grid_k;
  double * table = malloc((size_t) n_neurons * 4 * sizeof(double));
  if (table == NULL) {
    fprintf(stderr, "kohonen: couldn't allocate the occupancy table\n");
    return 0;
  }
  for (int neuron = 0; neuron < n_neurons; neuron++) {
    double * line = table + (size_t) neuron * 4;
    line[0] = neuron;
    line[1] = neuron / grid_k;
    line[2] = neuron % grid_k;
    line[3] = hits[neuron];
  }
  const char * header[] = { "neuron", "row", "col", "hits" };
  int ok = results_write_table(results, "occupancy.csv", 4, header, n_neurons, table);
  free(table);
  return ok;
}


// assignments.csv (sample, bmu, row, col, distance, bmu2), occupancy.csv and metrics.json, measured on the trained
// prototypes over the training samples
static int write_outputs(const Config * config, const SomParams * params, const Results * results,
                         const Matrix * input, const double prototypes[]) {
  int n = input->n_rows;
  int k = params->grid_k;
  int n_neurons = k * k;
  double * table = malloc((size_t) n * 6 * sizeof(double));
  int * bmu = malloc((size_t) n * sizeof(int));
  int * bmu2 = malloc((size_t) n * sizeof(int));
  double * distances = malloc((size_t) n * sizeof(double));
  int * hits = malloc((size_t) n_neurons * sizeof(int));
  int ok = table != NULL && bmu != NULL && bmu2 != NULL && distances != NULL && hits != NULL;
  if (!ok) fprintf(stderr, "kohonen: couldn't allocate the assignment table\n");

  if (ok) {
    Measures m;
    measure(input, prototypes, k, &m, bmu, bmu2, distances, hits);
    for (int i = 0; i < n; i++) {
      double * line = table + (size_t) i * 6;
      line[0] = i;
      line[1] = bmu[i];
      line[2] = bmu[i] / k;
      line[3] = bmu[i] % k;
      line[4] = distances[i];
      line[5] = bmu2[i];
    }

    const char * header[] = { "sample", "bmu", "row", "col", "distance", "bmu2" };
    const Metric metrics[METRICS_COUNT] = {
      { "model", "kohonen", 0 },
      { "seed", NULL, config->seed },
      { "n_samples", NULL, n },
      { "n_features", NULL, input->n_cols },
      { "grid_k", NULL, k },
      { "n_neurons", NULL, n_neurons },
      { "neighborhood", params->gaussian ? "gaussian" : "step", 0 },
      { "epochs", NULL, params->epochs },
      { "radius0", NULL, params->radius0 },
      { "radius_final", NULL, params->radius_final },
      { "eta0", NULL, params->eta0 },
      { "eta_final", NULL, params->eta_final },
      { "qe", NULL, m.qe },
      { "te", NULL, m.te },
      { "occupied_neurons", NULL, m.occupied },
      { "empty_fraction", NULL, 1.0 - (double) m.occupied / n_neurons },
      { "mean_hits_occupied", NULL, m.occupied > 0 ? (double) n / m.occupied : 0 },
      { "max_hits", NULL, m.max_hits },
      { "singleton_neurons", NULL, m.singletons },
    };
    ok = results_write_table(results, "assignments.csv", 6, header, n, table)
      && write_occupancy(results, k, hits)
      && results_write_metrics(results, metrics, METRICS_COUNT);
  }
  free(table);
  free(bmu);
  free(bmu2);
  free(distances);
  free(hits);
  return ok;
}


// trace.csv: epoch, eta, radius, qe, te; one row per epoch plus the starting state
static int write_trace(const Results * results, int epochs, const double trace[]) {
  const char * header[] = { "epoch", "eta", "radius", "qe", "te" };
  return results_write_table(results, "trace.csv", TRACE_WIDTH, header, epochs + 1, trace);
}


int run_kohonen(const Config * config, Rng * rng, const Results * results) {
  Matrix input;
  if (!matrix_load(config->input, &input)) return 0;

  SomParams params;
  int ok = read_params(config, input.n_rows, &params);

  double * prototypes = NULL;
  double * trace = NULL;
  if (ok) {
    prototypes = malloc((size_t) params.grid_k * params.grid_k * input.n_cols * sizeof(double));
    trace = malloc((size_t) (params.epochs + 1) * TRACE_WIDTH * sizeof(double));
    ok = prototypes != NULL && trace != NULL;
    if (!ok) fprintf(stderr, "kohonen: couldn't allocate the prototypes and the trace\n");
  }

  ok = ok && pick_prototypes(rng, &input, params.grid_k * params.grid_k, prototypes);
  ok = ok && train(&params, rng, &input, prototypes, trace);
  ok = ok && write_prototypes(results, &input, params.grid_k, prototypes);
  ok = ok && write_outputs(config, &params, results, &input, prototypes);
  ok = ok && write_trace(results, params.epochs, trace);

  free(prototypes);
  free(trace);
  matrix_free(&input);
  return ok;
}
