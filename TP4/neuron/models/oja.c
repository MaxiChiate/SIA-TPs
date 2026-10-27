// Oja's rule for one neuron on the input matrix (centered by the z-score). The start vector is uniform in [0, 1) per
// component, scaled to length 1 (course slides p. 15-16). Every epoch visits all the samples once in a shuffled
// order and applies w += eta * y * (x - y * w) with y = x . w. The learning rate eta decays exponentially from eta0
// to eta_final over all the steps and the number of epochs is fixed (no tolerance stop). After training w is
// renormalized to length 1 and oriented so its largest-|value| coefficient is positive (the convention of the
// Phase 1 PCA, lowest index on a tie); the index of every sample is then x . w. It writes the weights, the index,
// a per-epoch trace with the weights and the metrics.

#include "../io/matrix.h"
#include "models.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#define EPOCHS_MAX 100000
#define METRICS_COUNT 16
#define TRACE_FIXED 4 // epoch, eta, w_norm, delta_w; then one column per variable
#define STABILITY_MAX 1.0


// The three Oja keys of the config, already checked, and two numbers of the input
typedef struct {
  double eta0;
  double eta_final;
  int epochs;
  long long steps;   // epochs * n_samples, the number of weight updates of the run
  double max_x2;     // largest squared norm of an input row
  double eta0_max_x2; // eta0 * max_x2, the stability product (Pitfall 8)
} OjaParams;


static double norm(const double values[], int n) {
  double sum = 0;
  for (int j = 0; j < n; j++) sum += values[j] * values[j];
  return sqrt(sum);
}


// The three keys, checked before anything is allocated; prints "<config path>: <key> must ..." and returns 0 on the
// first value that doesn't fit
static int read_params(const Config * config, const Matrix * input, OjaParams * params) {
  if (!config_get_number(config, "eta0", &params->eta0)
      || !config_get_number(config, "eta_final", &params->eta_final)
      || !config_get_int(config, "epochs", &params->epochs)) {
    return 0;
  }

  if (params->epochs < 1 || params->epochs > EPOCHS_MAX) {
    fprintf(stderr, "%s: epochs must be between 1 and %d\n", config->path, EPOCHS_MAX);
    return 0;
  }
  params->steps = (long long) params->epochs * input->n_rows;

  params->max_x2 = 0;
  for (int i = 0; i < input->n_rows; i++) {
    double sum = 0;
    for (int j = 0; j < input->n_cols; j++) {
      double x = input->data[(size_t) i * input->n_cols + j];
      sum += x * x;
    }
    if (sum > params->max_x2) params->max_x2 = sum;
  }
  params->eta0_max_x2 = params->eta0 * params->max_x2;

  if (!(params->eta0 > 0 && params->eta0 < 1)) {
    fprintf(stderr, "%s: eta0 must be > 0 and < 1\n", config->path);
    return 0;
  }
  if (!(params->eta_final > 0 && params->eta_final <= params->eta0)) {
    fprintf(stderr, "%s: eta_final must be > 0 and <= eta0\n", config->path);
    return 0;
  }
  if (!(params->eta0_max_x2 < STABILITY_MAX)) {
    fprintf(stderr, "%s: eta0 * max |x|^2 = %g must be < 1 (Pitfall 8)\n", config->path, params->eta0_max_x2);
    return 0;
  }
  return 1;
}


// Uniform in [0, 1) per component, scaled to length 1; a zero vector cannot be scaled
static int initial_weights(Rng * rng, double w[], int n) {
  for (int j = 0; j < n; j++) w[j] = rng_uniform(rng);
  double length = norm(w, n);
  if (length == 0) {
    fprintf(stderr, "oja: the random vector has zero length\n");
    return 0;
  }
  for (int j = 0; j < n; j++) w[j] /= length;
  return 1;
}


// One trace row: epoch, eta, |w| (before any renormalization), delta_w, then the weights
static void trace_row(double trace[], int epoch, double eta, const double w[], double delta_w, int n_cols) {
  double * line = trace + (size_t) epoch * (TRACE_FIXED + n_cols);
  line[0] = epoch;
  line[1] = eta;
  line[2] = norm(w, n_cols);
  line[3] = delta_w;
  for (int j = 0; j < n_cols; j++) line[TRACE_FIXED + j] = w[j];
}


// Online training: epochs passes over the samples in a fresh shuffled order each time, no renormalization. trace gets
// epochs + 1 rows: row 0 is the start vector with eta0 and delta_w 0, row e the weights at the end of epoch e with
// the eta of that epoch's last step and delta_w = ||w_e - w_(e-1)||.
static int train(const OjaParams * params, Rng * rng, const Matrix * input, double w[], double trace[]) {
  int n = input->n_rows;
  int n_cols = input->n_cols;

  int * order = malloc((size_t) n * sizeof(int));
  double * before = malloc((size_t) n_cols * sizeof(double));
  if (order == NULL || before == NULL) {
    fprintf(stderr, "oja: couldn't allocate the training buffers\n");
    free(order);
    free(before);
    return 0;
  }
  for (int i = 0; i < n; i++) order[i] = i;

  trace_row(trace, 0, params->eta0, w, 0, n_cols);
  long long step = 0;
  for (int epoch = 1; epoch <= params->epochs; epoch++) {
    for (int j = 0; j < n_cols; j++) before[j] = w[j];
    rng_shuffle(rng, order, n);
    double eta = params->eta0;
    for (int i = 0; i < n; i++, step++) {
      double fraction = params->steps > 1 ? (double) step / (double) (params->steps - 1) : 0;
      eta = kohonen_decay(params->eta0, params->eta_final, fraction);

      const double * sample = input->data + (size_t) order[i] * n_cols;
      double y = 0;
      for (int j = 0; j < n_cols; j++) y += w[j] * sample[j];
      for (int j = 0; j < n_cols; j++) w[j] += eta * y * (sample[j] - y * w[j]);
    }

    for (int j = 0; j < n_cols; j++) {
      if (!isfinite(w[j])) {
        fprintf(stderr, "oja: the weights diverged at epoch %d; lower eta0\n", epoch);
        free(order);
        free(before);
        return 0;
      }
    }
    double delta = 0;
    for (int j = 0; j < n_cols; j++) delta += (w[j] - before[j]) * (w[j] - before[j]);
    trace_row(trace, epoch, eta, w, sqrt(delta), n_cols);
  }
  free(order);
  free(before);
  return 1;
}


// Index of the largest |w_j|; a strictly larger value replaces the current one, so the lowest index wins a tie
static int largest_abs(const double w[], int n) {
  int pivot = 0;
  for (int j = 1; j < n; j++) {
    if (fabs(w[j]) > fabs(w[pivot])) pivot = j;
  }
  return pivot;
}


// Negates w when its largest-|value| coefficient is negative (lowest index on a tie); returns 1 if it negated
int oja_orient(double w[], int n) {
  if (w[largest_abs(w, n)] >= 0) return 0;
  for (int j = 0; j < n; j++) w[j] = -w[j];
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


// trace.csv: epoch, eta, w_norm, delta_w, then the weights under the variable names; one row per epoch plus the start
static int write_trace(const Results * results, const Matrix * input, int epochs, const double trace[]) {
  int width = TRACE_FIXED + input->n_cols;
  const char ** header = malloc((size_t) width * sizeof(char *));
  if (header == NULL) {
    fprintf(stderr, "oja: couldn't allocate the trace header\n");
    return 0;
  }
  header[0] = "epoch";
  header[1] = "eta";
  header[2] = "w_norm";
  header[3] = "delta_w";
  for (int j = 0; j < input->n_cols; j++) header[TRACE_FIXED + j] = input->names[j];
  int ok = results_write_table(results, "trace.csv", width, header, epochs + 1, trace);
  free(header);
  return ok;
}


// weights.csv, index.csv and metrics.json. w is the oriented unit vector; w_norm_final and delta_w_final describe the
// last epoch before the renormalization.
static int write_outputs(const Config * config, const OjaParams * params, const Results * results,
                         const Matrix * input, const double w[], const double index[], double w_norm_final,
                         double delta_w_final, int flipped) {
  int n = input->n_rows;
  double mean, std;
  mean_and_std(index, n, &mean, &std);
  int pivot = largest_abs(w, input->n_cols);

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
    { "epochs", NULL, params->epochs },
    { "eta0", NULL, params->eta0 },
    { "eta_final", NULL, params->eta_final },
    { "eta0_max_x2", NULL, params->eta0_max_x2 },
    { "w_norm_final", NULL, w_norm_final },
    { "delta_w_final", NULL, delta_w_final },
    { "w_norm", NULL, norm(w, input->n_cols) },
    { "sign_flipped", NULL, flipped },
    { "pivot", input->names[pivot], 0 },
    { "pivot_weight", NULL, w[pivot] },
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

  OjaParams params;
  int ok = read_params(config, &input, &params);

  double * w = NULL;
  double * index = NULL;
  double * trace = NULL;
  if (ok) {
    w = malloc((size_t) input.n_cols * sizeof(double));
    index = malloc((size_t) input.n_rows * sizeof(double));
    trace = malloc((size_t) (params.epochs + 1) * (TRACE_FIXED + input.n_cols) * sizeof(double));
    ok = w != NULL && index != NULL && trace != NULL;
    if (!ok) fprintf(stderr, "oja: couldn't allocate the weights and the trace\n");
  }

  ok = ok && initial_weights(rng, w, input.n_cols);
  ok = ok && train(&params, rng, &input, w, trace);

  if (ok) {
    const double * last = trace + (size_t) params.epochs * (TRACE_FIXED + input.n_cols);
    double w_norm_final = norm(w, input.n_cols);
    double delta_w_final = last[3];
    if (w_norm_final == 0) {
      fprintf(stderr, "oja: the trained weights have zero length\n");
      ok = 0;
    } else {
      for (int j = 0; j < input.n_cols; j++) w[j] /= w_norm_final;
      int flipped = oja_orient(w, input.n_cols);
      project(&input, w, index);
      ok = write_outputs(config, &params, results, &input, w, index, w_norm_final, delta_w_final, flipped)
        && write_trace(results, &input, params.epochs, trace);
    }
  }

  free(w);
  free(index);
  free(trace);
  matrix_free(&input);
  return ok;
}
