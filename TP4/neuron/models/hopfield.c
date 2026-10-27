// Discrete Hopfield network with +-1 neurons. rule "hebb": W = sum over the stored patterns of xi xi^T with a zero
// diagonal and no 1/N, so its entries are exact integers kept in doubles. rule "pinv": W = X^T (X X^T)^-1 X, the
// pseudo-inverse / projection rule (D-06), real-valued with a non-zero diagonal (D-07) - the remedy for Hebb's
// failure on correlated patterns, built by hopfield_pinv and reported as an error if the Gram matrix X X^T is
// singular. Either way h_i = 0 is an exact tie (the neuron keeps its state).
// Task "recall" stores the rows of the input named by "subset", then corrupts every stored pattern by flipping exactly
// k = lround(level * N) distinct pixels per trial and runs the dynamics: "async" (one neuron at a time in a fresh
// random order per sweep, the reference) or "sync" (every neuron at once, the course's comparison, with two-cycle
// detection). The final state of every trial is classified as stored, inverse, mixture of three or other.
// Writes stored.csv, overlaps.csv, trials.csv, trace.csv, states.csv and metrics.json.
// Task "capacity" stores p rows of the input at a time, either every p-subset in lexicographic order or n_subsets
// distinct subsets drawn with the seed, and writes per subset the overlaps, how many stored patterns are fixed
// points, the minimum stability margin and the exact-match recall rate at one noise level: capacity.csv and
// metrics.json. The dynamics live in hopfield_core.c; this file reads the config, runs the trials and writes the
// tables.

#include "../io/matrix.h"
#include "hopfield_core.h"
#include "models.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define NEURONS_MAX 2048
#define SWEEPS_MAX 10000
#define TRIALS_MAX 100000
#define TRIAL_ROWS_MAX 2000000       // p * levels * trials
#define TABLE_DOUBLES_MAX 50000000   // values of one table (400 MB)
#define TRACE_ROWS_MAX 1000000
#define RECALL_METRICS 20
#define CAPACITY_P_MAX 64
#define CAPACITY_SAMPLES_MAX 10000
#define CAPACITY_ROWS_MAX 200000
#define CAPACITY_WORK_MAX 50000000   // subsets * p * trials
#define CAPACITY_METRICS 14
#define CAPACITY_TAIL 7              // columns of capacity.csv after the indices
#define DRAWS_PER_SUBSET 1000
#define TRIAL_FIXED 22 // columns of trials.csv before m_0
#define STORED_WIDTH 6
#define NAME_MAX_LENGTH 24


// The keys of the config, already checked
typedef struct {
  int recall;       // task "recall"
  int pinv;         // 0: rule "hebb", 1: rule "pinv"
  int sync;         // 0: update "async", 1: update "sync"
  int max_sweeps;
  int trials;
  int trace_trials;
  int n_levels;
  double levels[CONFIG_ARRAY_MAX];
  int p;            // patterns stored
  int subset[CONFIG_ARRAY_MAX];
  int n_subsets;    // capacity: 0 = every p-subset, otherwise that many distinct random ones
  long long subsets; // capacity: rows of capacity.csv
} HopfieldParams;


static int is_pm_one(const Matrix * patterns) {
  for (size_t i = 0; i < (size_t) patterns->n_rows * patterns->n_cols; i++) {
    if (patterns->data[i] != -1 && patterns->data[i] != 1) return 0;
  }
  return 1;
}


static int has_key(const Config * config, const char * key) {
  return cJSON_GetObjectItemCaseSensitive(config->json, key) != NULL;
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


// subset: distinct integer row indices of the input, at least one
static int read_subset(const Config * config, int n_rows, HopfieldParams * params) {
  double values[CONFIG_ARRAY_MAX];
  if (!config_get_number_array(config, "subset", values, CONFIG_ARRAY_MAX, &params->p)) return 0;
  for (int a = 0; a < params->p; a++) {
    if (values[a] != floor(values[a]) || values[a] < 0 || values[a] >= n_rows) {
      fprintf(stderr, "%s: subset[%d] = %g must be an integer row of the input, between 0 and %d\n", config->path, a,
              values[a], n_rows - 1);
      return 0;
    }
    params->subset[a] = (int) values[a];
    for (int b = 0; b < a; b++) {
      if (params->subset[b] == params->subset[a]) {
        fprintf(stderr, "%s: subset[%d] repeats row %d of subset[%d]\n", config->path, a, params->subset[a], b);
        return 0;
      }
    }
  }
  return 1;
}


// The keys of task "recall": subset and trace_trials, and the sizes of its tables
static int read_recall_keys(const Config * config, const Matrix * input, HopfieldParams * params) {
  if (has_key(config, "p") || has_key(config, "n_subsets")) {
    fprintf(stderr, "%s: p and n_subsets are only for task \"capacity\"\n", config->path);
    return 0;
  }
  if (!has_key(config, "subset") || !has_key(config, "trace_trials")) {
    fprintf(stderr, "%s: task \"recall\" needs subset and trace_trials\n", config->path);
    return 0;
  }
  if (!read_subset(config, input->n_rows, params) || !config_get_int(config, "trace_trials", &params->trace_trials)) {
    return 0;
  }
  if (params->trace_trials < 0 || params->trace_trials > params->trials) {
    fprintf(stderr, "%s: trace_trials must be between 0 and trials (%d)\n", config->path, params->trials);
    return 0;
  }

  long long rows = (long long) params->p * params->n_levels * params->trials;
  if (rows > TRIAL_ROWS_MAX
      || rows * (TRIAL_FIXED + params->p) > TABLE_DOUBLES_MAX) {
    fprintf(stderr, "%s: %d patterns x %d levels x %d trials is too many trials; lower trials\n", config->path,
            params->p, params->n_levels, params->trials);
    return 0;
  }
  long long state_values = (long long) params->p * params->n_levels * params->trace_trials * 2
                           * (2 + input->n_cols);
  if (state_values > TABLE_DOUBLES_MAX) {
    fprintf(stderr, "%s: trace_trials is too large: states.csv would hold %lld values\n", config->path,
            state_values);
    return 0;
  }
  return 1;
}


// C(n, k) in long long, or limit + 1 as soon as it passes limit (the running value only grows up to k = n / 2)
static long long binomial_capped(int n, int k, long long limit) {
  if (k > n - k) k = n - k;
  long long value = 1;
  for (int i = 0; i < k; i++) {
    value = value * (n - i) / (i + 1);
    if (value > limit) return limit + 1;
  }
  return value;
}


// The keys of task "capacity": p and n_subsets, one noise level, and the sizes of capacity.csv and of the work
static int read_capacity_keys(const Config * config, const Matrix * input, HopfieldParams * params) {
  if (has_key(config, "subset") || has_key(config, "trace_trials")) {
    fprintf(stderr, "%s: subset and trace_trials are only for task \"recall\"\n", config->path);
    return 0;
  }
  if (!has_key(config, "p") || !has_key(config, "n_subsets")) {
    fprintf(stderr, "%s: task \"capacity\" needs p and n_subsets\n", config->path);
    return 0;
  }
  if (params->n_levels != 1) {
    fprintf(stderr, "%s: task \"capacity\" takes exactly one noise level, noise_levels has %d\n", config->path,
            params->n_levels);
    return 0;
  }
  if (!config_get_int(config, "p", &params->p) || !config_get_int(config, "n_subsets", &params->n_subsets)) return 0;
  int p_max = input->n_rows < CAPACITY_P_MAX ? input->n_rows : CAPACITY_P_MAX;
  if (params->p < 1 || params->p > p_max) {
    fprintf(stderr, "%s: p must be between 1 and %d (the rows of the input, at most %d)\n", config->path, p_max,
            CAPACITY_P_MAX);
    return 0;
  }
  if (params->n_subsets < 0 || params->n_subsets > CAPACITY_SAMPLES_MAX) {
    fprintf(stderr, "%s: n_subsets must be between 0 and %d\n", config->path, CAPACITY_SAMPLES_MAX);
    return 0;
  }

  long long all = binomial_capped(input->n_rows, params->p, CAPACITY_ROWS_MAX);
  if (params->n_subsets == 0) {
    if (all > CAPACITY_ROWS_MAX) {
      fprintf(stderr, "%s: n_subsets 0 needs C(n_rows, p) <= %d; give n_subsets > 0 to sample\n", config->path,
              CAPACITY_ROWS_MAX);
      return 0;
    }
    params->subsets = all;
  } else {
    if (params->n_subsets >= all) {
      fprintf(stderr, "%s: n_subsets must be below C(n_rows, p) = %lld; use 0 for every subset\n", config->path,
              all);
      return 0;
    }
    params->subsets = params->n_subsets;
  }

  if (params->subsets * params->p * params->trials > CAPACITY_WORK_MAX) {
    fprintf(stderr, "%s: %lld subsets x %d patterns x %d trials is too much work; lower trials\n", config->path,
            params->subsets, params->p, params->trials);
    return 0;
  }
  if (params->subsets * (1 + params->p + CAPACITY_TAIL) > TABLE_DOUBLES_MAX) {
    fprintf(stderr, "%s: capacity.csv would hold too many values; lower p or n_subsets\n", config->path);
    return 0;
  }
  return 1;
}


// The keys, checked before anything is allocated; prints "<config path>: <key> ..." and returns 0 on the first one
// that doesn't fit
static int read_params(const Config * config, const Matrix * input, HopfieldParams * params) {
  const char * task;
  const char * rule;
  const char * update;
  if (!config_get_string(config, "task", &task)
      || !config_get_string(config, "rule", &rule)
      || !config_get_string(config, "update", &update)
      || !config_get_int(config, "max_sweeps", &params->max_sweeps)
      || !config_get_int(config, "trials", &params->trials)) {
    return 0;
  }

  int is_capacity = strcmp(task, "capacity") == 0;
  if (!is_capacity && strcmp(task, "recall") != 0) {
    fprintf(stderr, "%s: task must be \"recall\" or \"capacity\"\n", config->path);
    return 0;
  }
  params->recall = !is_capacity;
  if (strcmp(rule, "hebb") == 0) {
    params->pinv = 0;
  } else if (strcmp(rule, "pinv") == 0) {
    params->pinv = 1;
  } else {
    fprintf(stderr, "%s: rule must be \"hebb\" or \"pinv\"\n", config->path);
    return 0;
  }
  if (strcmp(update, "async") == 0) {
    params->sync = 0;
  } else if (strcmp(update, "sync") == 0) {
    params->sync = 1;
  } else {
    fprintf(stderr, "%s: update must be \"async\" or \"sync\"\n", config->path);
    return 0;
  }
  if (params->max_sweeps < 1 || params->max_sweeps > SWEEPS_MAX) {
    fprintf(stderr, "%s: max_sweeps must be between 1 and %d\n", config->path, SWEEPS_MAX);
    return 0;
  }
  if (params->trials < 1 || params->trials > TRIALS_MAX) {
    fprintf(stderr, "%s: trials must be between 1 and %d\n", config->path, TRIALS_MAX);
    return 0;
  }
  if (!read_noise_levels(config, params->levels, &params->n_levels)) return 0;

  if (input->n_cols < 2 || input->n_cols > NEURONS_MAX) {
    fprintf(stderr, "%s: the input needs between 2 and %d columns, it has %d\n", config->input, NEURONS_MAX,
            input->n_cols);
    return 0;
  }
  if (!is_pm_one(input)) {
    fprintf(stderr, "%s: patterns must contain only -1 and 1\n", config->input);
    return 0;
  }
  return is_capacity ? read_capacity_keys(config, input, params) : read_recall_keys(config, input, params);
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


// A header of fixed names followed by prefix0..prefix{count-1}, all in memory that outlives results_write_table
typedef struct {
  const char ** names;
  char * storage;
} Header;


static int header_make(Header * header, const char * const fixed[], int n_fixed, const char * prefix, int count) {
  header->names = malloc((size_t) (n_fixed + count) * sizeof(char *));
  header->storage = malloc((size_t) (count > 0 ? count : 1) * NAME_MAX_LENGTH);
  if (header->names == NULL || header->storage == NULL) {
    fprintf(stderr, "hopfield: couldn't allocate a table header\n");
    return 0;
  }
  for (int c = 0; c < n_fixed; c++) header->names[c] = fixed[c];
  for (int c = 0; c < count; c++) {
    char * name = header->storage + (size_t) c * NAME_MAX_LENGTH;
    snprintf(name, NAME_MAX_LENGTH, "%s%d", prefix, c);
    header->names[n_fixed + c] = name;
  }
  return 1;
}


static void header_free(Header * header) {
  free(header->names);
  free(header->storage);
}


// stored.csv: pattern, source_row, fixed, min_margin, wrong_pixels, energy of every stored pattern; returns in
// fixed_count how many are fixed points of W
static int write_stored(const Results * results, const HopfieldParams * params, const double patterns[], int n,
                        const double w[], int * fixed_count) {
  int p = params->p;
  double * table = malloc((size_t) p * STORED_WIDTH * sizeof(double));
  if (table == NULL) {
    fprintf(stderr, "hopfield: couldn't allocate the stored table\n");
    return 0;
  }
  *fixed_count = 0;
  for (int a = 0; a < p; a++) {
    const double * xi = patterns + (size_t) a * n;
    int wrong;
    double margin = hopfield_min_margin(w, n, xi, &wrong);
    double * line = table + (size_t) a * STORED_WIDTH;
    line[0] = a;
    line[1] = params->subset[a];
    line[2] = wrong == 0;
    line[3] = margin;
    line[4] = wrong;
    line[5] = hopfield_energy(w, n, xi);
    if (wrong == 0) (*fixed_count)++;
  }
  const char * header[STORED_WIDTH] = { "pattern", "source_row", "fixed", "min_margin", "wrong_pixels", "energy" };
  int ok = results_write_table(results, "stored.csv", STORED_WIDTH, header, p, table);
  free(table);
  return ok;
}


// overlaps.csv: pattern, then m_b = xi_a . xi_b / N for every stored pattern b; max_abs gets the largest |m_ab|, a < b
static int write_overlaps(const Results * results, int p, int n, const double patterns[], double * max_abs) {
  int width = 1 + p;
  double * table = malloc((size_t) p * width * sizeof(double));
  Header header = { NULL, NULL };
  const char * const fixed[] = { "pattern" };
  int ok = table != NULL && header_make(&header, fixed, 1, "m_", p);
  if (table == NULL) fprintf(stderr, "hopfield: couldn't allocate the overlap table\n");

  if (ok) {
    *max_abs = 0;
    for (int a = 0; a < p; a++) {
      table[(size_t) a * width] = a;
      for (int b = 0; b < p; b++) {
        double dot = 0;
        for (int j = 0; j < n; j++) dot += patterns[(size_t) a * n + j] * patterns[(size_t) b * n + j];
        table[(size_t) a * width + 1 + b] = dot / n;
        if (a < b && fabs(dot) / n > *max_abs) *max_abs = fabs(dot) / n;
      }
    }
    ok = results_write_table(results, "overlaps.csv", width, header.names, p, table);
  }
  header_free(&header);
  free(table);
  return ok;
}


// Totals over every trial of the run
typedef struct {
  long long n_trials;
  long long correct;
  long long wrong_stored;
  long long inverse;
  long long mixture;
  long long other;
  long long cycles;
  double sweeps;
  double flips;
  long long energy_increases;
} Tally;


// The row of trials.csv: the fixed columns, then m_b = xi_b . s / N
static void trial_row(double line[], long long trial, int a, const HopfieldParams * params, int l, int k, int n,
                      const HopfieldOutcome * out, HopfieldClass klass, const int match[3], const int sign[3],
                      const double patterns[], const double s[], int correct) {
  const double * xi = patterns + (size_t) a * n;
  int hamming = 0;
  for (int j = 0; j < n; j++) {
    if (s[j] != xi[j]) hamming++;
  }
  line[0] = (double) trial;
  line[1] = a;
  line[2] = params->subset[a];
  line[3] = params->levels[l];
  line[4] = k;
  line[5] = (double) (n - 2 * k) / n;
  line[6] = out->converged;
  line[7] = out->sweeps;
  line[8] = (double) out->updates;
  line[9] = (double) out->flips;
  line[10] = out->cycle;
  line[11] = klass;
  for (int c = 0; c < 3; c++) {
    line[12 + c] = match[c];
    line[15 + c] = sign[c];
  }
  line[18] = correct;
  line[19] = out->e_start;
  line[20] = out->e_final;
  line[21] = hamming;
  for (int b = 0; b < params->p; b++) {
    double dot = 0;
    for (int j = 0; j < n; j++) dot += patterns[(size_t) b * n + j] * s[j];
    line[TRIAL_FIXED + b] = dot / n;
  }
}


static void tally_add(Tally * tally, int a, const HopfieldOutcome * out, HopfieldClass klass, const int match[3],
                      int correct) {
  tally->n_trials++;
  tally->correct += correct;
  if (klass == HOPFIELD_STORED && match[0] != a) tally->wrong_stored++;
  if (klass == HOPFIELD_INVERSE) tally->inverse++;
  if (klass == HOPFIELD_MIXTURE) tally->mixture++;
  if (klass == HOPFIELD_OTHER) tally->other++;
  if (out->cycle > 0) tally->cycles++;
  tally->sweeps += out->sweeps;
  tally->flips += (double) out->flips;
  tally->energy_increases += out->energy_increases;
}


// trace.csv: trial, step, sweep, neuron, changed, energy
static int write_trace(const Results * results, const HopfieldTrace * trace) {
  const char * header[HOPFIELD_TRACE_WIDTH] = { "trial", "step", "sweep", "neuron", "changed", "energy" };
  return results_write_table(results, "trace.csv", HOPFIELD_TRACE_WIDTH, header, (int) trace->rows, trace->data);
}


// The buffers of the trial loop; run_recall allocates them together and frees them in one place
typedef struct {
  double * patterns; // p x n, the stored rows in subset order
  double * w;
  double * s;
  double * query;
  double * h;
  double * scratch;  // 2n
  double * gram;     // 2*p*p, hopfield_pinv's Gram scratch (unused when rule is hebb)
  int * order;
  double * trials;
  double * states;
} RecallBuffers;


// Runs every trial in the order pattern, level, trial index with the run's single Rng
static int run_trials(const HopfieldParams * params, Rng * rng, int n, RecallBuffers * buf, HopfieldTrace * trace,
                      Tally * tally) {
  int p = params->p;
  int width = TRIAL_FIXED + p;
  long long trial = 0;
  long long state_row = 0;

  for (int a = 0; a < p; a++) {
    const double * xi = buf->patterns + (size_t) a * n;
    for (int l = 0; l < params->n_levels; l++) {
      for (int t = 0; t < params->trials; t++) {
        int k = (int) lround(params->levels[l] * n);
        corrupt(rng, xi, n, k, buf->order, buf->s);
        memcpy(buf->query, buf->s, (size_t) n * sizeof(double));
        for (int j = 0; j < n; j++) buf->order[j] = j;

        int traced = t < params->trace_trials;
        trace->trial = (double) trial;
        HopfieldOutcome out;
        int ok;
        if (params->sync) {
          ok = hopfield_sync_run(buf->w, n, buf->s, buf->scratch, params->max_sweeps, traced ? trace : NULL, &out);
        } else {
          ok = hopfield_async_run(buf->w, n, buf->s, buf->h, buf->order, rng, params->max_sweeps,
                                  traced ? trace : NULL, &out);
        }
        if (!ok) {
          fprintf(stderr, "hopfield: trace.csv would pass %d rows; lower trace_trials\n", TRACE_ROWS_MAX);
          return 0;
        }

        int match[3];
        int sign[3];
        HopfieldClass klass = hopfield_classify(buf->patterns, p, n, buf->s, match, sign);
        int correct = out.converged && klass == HOPFIELD_STORED && match[0] == a;
        trial_row(buf->trials + (size_t) trial * width, trial, a, params, l, k, n, &out, klass, match, sign,
                  buf->patterns, buf->s, correct);
        tally_add(tally, a, &out, klass, match, correct);

        if (traced) {
          double * query_line = buf->states + (size_t) state_row * (2 + n);
          double * final_line = query_line + (2 + n);
          query_line[0] = (double) trial;
          query_line[1] = 0;
          final_line[0] = (double) trial;
          final_line[1] = 1;
          memcpy(query_line + 2, buf->query, (size_t) n * sizeof(double));
          memcpy(final_line + 2, buf->s, (size_t) n * sizeof(double));
          state_row += 2;
        }
        trial++;
      }
    }
  }
  return 1;
}


static int write_trials(const Results * results, const HopfieldParams * params, const double table[]) {
  static const char * const fixed[TRIAL_FIXED] = {
    "trial", "pattern", "source_row", "noise", "flipped", "overlap", "converged", "sweeps", "updates", "flips",
    "cycle", "class", "match_a", "match_b", "match_c", "sign_a", "sign_b", "sign_c", "correct", "e_start", "e_final",
    "hamming_final",
  };
  Header header = { NULL, NULL };
  int ok = header_make(&header, fixed, TRIAL_FIXED, "m_", params->p);
  int rows = params->p * params->n_levels * params->trials;
  ok = ok && results_write_table(results, "trials.csv", TRIAL_FIXED + params->p, header.names, rows, table);
  header_free(&header);
  return ok;
}


static int write_states(const Results * results, const HopfieldParams * params, int n, const double table[]) {
  static const char * const fixed[2] = { "trial", "kind" };
  Header header = { NULL, NULL };
  int ok = header_make(&header, fixed, 2, "s_", n);
  int rows = params->p * params->n_levels * params->trace_trials * 2;
  ok = ok && results_write_table(results, "states.csv", 2 + n, header.names, rows, table);
  header_free(&header);
  return ok;
}


static int run_recall(const Config * config, const HopfieldParams * params, Rng * rng, const Results * results,
                      const Matrix * input) {
  int n = input->n_cols;
  int p = params->p;
  size_t trial_rows = (size_t) p * params->n_levels * params->trials;
  size_t state_rows = (size_t) p * params->n_levels * params->trace_trials * 2;

  RecallBuffers buf;
  buf.patterns = malloc((size_t) p * n * sizeof(double));
  buf.w = malloc((size_t) n * n * sizeof(double));
  buf.s = malloc((size_t) n * sizeof(double));
  buf.query = malloc((size_t) n * sizeof(double));
  buf.h = malloc((size_t) n * sizeof(double));
  buf.scratch = malloc((size_t) 2 * n * sizeof(double));
  buf.gram = malloc((size_t) 2 * p * p * sizeof(double));
  buf.order = malloc((size_t) n * sizeof(int));
  buf.trials = malloc(trial_rows * (TRIAL_FIXED + p) * sizeof(double));
  buf.states = malloc((state_rows > 0 ? state_rows : 1) * (2 + n) * sizeof(double));
  int ok = buf.patterns != NULL && buf.w != NULL && buf.s != NULL && buf.query != NULL && buf.h != NULL
           && buf.scratch != NULL && buf.gram != NULL && buf.order != NULL && buf.trials != NULL
           && buf.states != NULL;
  if (!ok) fprintf(stderr, "hopfield: couldn't allocate the weights and the trial tables\n");

  HopfieldTrace trace = { NULL, 0, 0, TRACE_ROWS_MAX, 0 };
  Tally tally;
  memset(&tally, 0, sizeof(tally));
  int fixed_count = 0;
  double max_abs_overlap = 0;

  if (ok) {
    for (int a = 0; a < p; a++) {
      memcpy(buf.patterns + (size_t) a * n, input->data + (size_t) params->subset[a] * n, (size_t) n * sizeof(double));
    }
    if (params->pinv) {
      if (!hopfield_pinv(buf.patterns, p, n, buf.w, buf.gram)) {
        fprintf(stderr, "%s: the Gram matrix of the stored patterns is singular; the pseudo-inverse rule needs "
                        "linearly independent patterns\n", config->path);
        ok = 0;
      }
    } else {
      hopfield_hebb(buf.patterns, p, n, buf.w);
    }
  }
  ok = ok && write_stored(results, params, buf.patterns, n, buf.w, &fixed_count);
  ok = ok && write_overlaps(results, p, n, buf.patterns, &max_abs_overlap);
  ok = ok && run_trials(params, rng, n, &buf, &trace, &tally);
  ok = ok && write_trials(results, params, buf.trials);
  ok = ok && write_trace(results, &trace);
  ok = ok && write_states(results, params, n, buf.states);

  if (ok) {
    double total = (double) tally.n_trials;
    const Metric metrics[RECALL_METRICS] = {
      { "model", "hopfield", 0 },
      { "seed", NULL, config->seed },
      { "task", "recall", 0 },
      { "update", params->sync ? "sync" : "async", 0 },
      { "rule", params->pinv ? "pinv" : "hebb", 0 },
      { "n_patterns", NULL, p },
      { "n_neurons", NULL, n },
      { "n_levels", NULL, params->n_levels },
      { "trials", NULL, params->trials },
      { "stored_fixed", NULL, fixed_count },
      { "max_abs_overlap", NULL, max_abs_overlap },
      { "recall_rate", NULL, (double) tally.correct / total },
      { "wrong_stored_rate", NULL, (double) tally.wrong_stored / total },
      { "inverse_rate", NULL, (double) tally.inverse / total },
      { "mixture_rate", NULL, (double) tally.mixture / total },
      { "other_rate", NULL, (double) tally.other / total },
      { "cycle_rate", NULL, (double) tally.cycles / total },
      { "mean_sweeps", NULL, tally.sweeps / total },
      { "mean_flips", NULL, tally.flips / total },
      { "energy_increases", NULL, (double) tally.energy_increases },
    };
    ok = results_write_metrics(results, metrics, RECALL_METRICS);
  }

  hopfield_trace_free(&trace);
  free(buf.patterns);
  free(buf.w);
  free(buf.s);
  free(buf.query);
  free(buf.h);
  free(buf.scratch);
  free(buf.gram);
  free(buf.order);
  free(buf.trials);
  free(buf.states);
  return ok;
}


// Advances idx (p ascending indices below n) to the next combination in lexicographic order; 0 after the last one
static int next_combination(int idx[], int p, int n) {
  int i = p - 1;
  while (i >= 0 && idx[i] == n - p + i) i--;
  if (i < 0) return 0;
  idx[i]++;
  for (int j = i + 1; j < p; j++) idx[j] = idx[j - 1] + 1;
  return 1;
}


// Fills idx (count x p) with distinct subsets: each draw shuffles order, keeps the first p sorted ascending and is
// accepted if no accepted subset equals it. Done before any trial, so the list depends only on the seed.
static int draw_subsets(Rng * rng, int n_rows, int p, int count, int order[], int idx[]) {
  int accepted = 0;
  for (long long draw = 0; accepted < count && draw < (long long) DRAWS_PER_SUBSET * count; draw++) {
    for (int j = 0; j < n_rows; j++) order[j] = j;
    rng_shuffle(rng, order, n_rows);
    int * candidate = idx + (size_t) accepted * p;
    for (int j = 0; j < p; j++) {
      int value = order[j];
      int k = j;
      while (k > 0 && candidate[k - 1] > value) {
        candidate[k] = candidate[k - 1];
        k--;
      }
      candidate[k] = value;
    }
    int repeated = 0;
    for (int b = 0; b < accepted && !repeated; b++) {
      repeated = memcmp(idx + (size_t) b * p, candidate, (size_t) p * sizeof(int)) == 0;
    }
    if (!repeated) accepted++;
  }
  if (accepted < count) {
    fprintf(stderr, "hopfield: could not draw %d distinct subsets\n", count);
    return 0;
  }
  return 1;
}


// The buffers of the capacity loop
typedef struct {
  int * idx;          // subsets x p, the input rows of every subset
  double * table;     // subsets x width
  double * patterns;  // p x n
  double * w;
  double * s;
  double * h;
  double * scratch;   // 2n
  double * gram;      // 2*p*p, hopfield_pinv's Gram scratch (unused when rule is hebb)
  int * order;        // n, and n_rows while drawing
} CapacityBuffers;


// capacity.csv: subset, idx_0..idx_{p-1}, max_abs_overlap, mean_abs_overlap, n_stable, stable_fraction, min_margin,
// recall_rate, mean_sweeps
static int write_capacity(const Results * results, int p, long long subsets, const double table[]) {
  static const char * const tail[CAPACITY_TAIL] = {
    "max_abs_overlap", "mean_abs_overlap", "n_stable", "stable_fraction", "min_margin", "recall_rate", "mean_sweeps",
  };
  int width = 1 + p + CAPACITY_TAIL;
  const char ** names = malloc((size_t) width * sizeof(char *));
  char * storage = malloc((size_t) p * NAME_MAX_LENGTH);
  if (names == NULL || storage == NULL) {
    fprintf(stderr, "hopfield: couldn't allocate a table header\n");
    free(names);
    free(storage);
    return 0;
  }
  names[0] = "subset";
  for (int c = 0; c < p; c++) {
    char * name = storage + (size_t) c * NAME_MAX_LENGTH;
    snprintf(name, NAME_MAX_LENGTH, "idx_%d", c);
    names[1 + c] = name;
  }
  for (int c = 0; c < CAPACITY_TAIL; c++) names[1 + p + c] = tail[c];
  int ok = results_write_table(results, "capacity.csv", width, names, (int) subsets, table);
  free(names);
  free(storage);
  return ok;
}


// Max and mean of |xi_a . xi_b| / n over the pairs a < b of the p stored rows; both 0 when p = 1
static void pair_overlaps(const double patterns[], int p, int n, double * max_abs, double * mean_abs) {
  double sum = 0;
  double biggest = 0;
  for (int a = 0; a < p; a++) {
    for (int b = a + 1; b < p; b++) {
      double dot = 0;
      for (int j = 0; j < n; j++) dot += patterns[(size_t) a * n + j] * patterns[(size_t) b * n + j];
      sum += fabs(dot);
      if (fabs(dot) / n > biggest) biggest = fabs(dot) / n;
    }
  }
  int pairs = p * (p - 1) / 2;
  *max_abs = biggest;
  *mean_abs = pairs > 0 ? sum / ((double) n * pairs) : 0;
}


// Stores every subset in turn, measures its stability and runs the noisy recall trials at the one noise level.
// Returns 0 (and stops) if a singular Gram is hit under rule "pinv".
static int run_subsets(const Config * config, const HopfieldParams * params, Rng * rng, const Matrix * input,
                       CapacityBuffers * buf) {
  int n = input->n_cols;
  int p = params->p;
  int width = 1 + p + CAPACITY_TAIL;
  int k = (int) lround(params->levels[0] * n);

  for (long long r = 0; r < params->subsets; r++) {
    const int * rows = buf->idx + (size_t) r * p;
    for (int a = 0; a < p; a++) {
      memcpy(buf->patterns + (size_t) a * n, input->data + (size_t) rows[a] * n, (size_t) n * sizeof(double));
    }
    if (params->pinv) {
      if (!hopfield_pinv(buf->patterns, p, n, buf->w, buf->gram)) {
        fprintf(stderr, "%s: the Gram matrix of the stored patterns is singular; the pseudo-inverse rule needs "
                        "linearly independent patterns\n", config->path);
        return 0;
      }
    } else {
      hopfield_hebb(buf->patterns, p, n, buf->w);
    }

    double * line = buf->table + (size_t) r * width;
    line[0] = (double) r;
    for (int a = 0; a < p; a++) line[1 + a] = rows[a];
    pair_overlaps(buf->patterns, p, n, &line[1 + p], &line[2 + p]);

    int n_stable = 0;
    double min_margin = 0;
    for (int a = 0; a < p; a++) {
      int wrong;
      double margin = hopfield_min_margin(buf->w, n, buf->patterns + (size_t) a * n, &wrong);
      if (wrong == 0) n_stable++;
      if (a == 0 || margin < min_margin) min_margin = margin;
    }

    long long correct = 0;
    double sweeps = 0;
    for (int a = 0; a < p; a++) {
      const double * xi = buf->patterns + (size_t) a * n;
      for (int t = 0; t < params->trials; t++) {
        corrupt(rng, xi, n, k, buf->order, buf->s);
        for (int j = 0; j < n; j++) buf->order[j] = j;
        HopfieldOutcome out;
        if (params->sync) {
          hopfield_sync_run(buf->w, n, buf->s, buf->scratch, params->max_sweeps, NULL, &out);
        } else {
          hopfield_async_run(buf->w, n, buf->s, buf->h, buf->order, rng, params->max_sweeps, NULL, &out);
        }
        int match[3];
        int sign[3];
        HopfieldClass klass = hopfield_classify(buf->patterns, p, n, buf->s, match, sign);
        correct += out.converged && klass == HOPFIELD_STORED && match[0] == a;
        sweeps += out.sweeps;
      }
    }
    double total = (double) p * params->trials;
    line[3 + p] = n_stable;
    line[4 + p] = (double) n_stable / p;
    line[5 + p] = min_margin;
    line[6 + p] = (double) correct / total;
    line[7 + p] = sweeps / total;
  }
  return 1;
}


static int run_capacity(const Config * config, const HopfieldParams * params, Rng * rng, const Results * results,
                        const Matrix * input) {
  int n = input->n_cols;
  int p = params->p;
  int width = 1 + p + CAPACITY_TAIL;
  int order_size = input->n_rows > n ? input->n_rows : n;

  CapacityBuffers buf;
  buf.idx = malloc((size_t) params->subsets * p * sizeof(int));
  buf.table = malloc((size_t) params->subsets * width * sizeof(double));
  buf.patterns = malloc((size_t) p * n * sizeof(double));
  buf.w = malloc((size_t) n * n * sizeof(double));
  buf.s = malloc((size_t) n * sizeof(double));
  buf.h = malloc((size_t) n * sizeof(double));
  buf.scratch = malloc((size_t) 2 * n * sizeof(double));
  buf.gram = malloc((size_t) 2 * p * p * sizeof(double));
  buf.order = malloc((size_t) order_size * sizeof(int));
  int ok = buf.idx != NULL && buf.table != NULL && buf.patterns != NULL && buf.w != NULL && buf.s != NULL
           && buf.h != NULL && buf.scratch != NULL && buf.gram != NULL && buf.order != NULL;
  if (!ok) fprintf(stderr, "hopfield: couldn't allocate the capacity tables\n");

  if (ok && params->n_subsets > 0) {
    ok = draw_subsets(rng, input->n_rows, p, params->n_subsets, buf.order, buf.idx);
  } else if (ok) {
    int * first = buf.idx;
    for (int a = 0; a < p; a++) first[a] = a;
    for (long long r = 1; r < params->subsets; r++) {
      memcpy(buf.idx + (size_t) r * p, buf.idx + (size_t) (r - 1) * p, (size_t) p * sizeof(int));
      next_combination(buf.idx + (size_t) r * p, p, input->n_rows);
    }
  }
  ok = ok && run_subsets(config, params, rng, input, &buf);
  ok = ok && write_capacity(results, p, params->subsets, buf.table);

  if (ok) {
    double rows = (double) params->subsets;
    double stable_sum = 0;
    double recall_sum = 0;
    long long all_stable = 0;
    for (long long r = 0; r < params->subsets; r++) {
      const double * line = buf.table + (size_t) r * width;
      stable_sum += line[4 + p];
      recall_sum += line[6 + p];
      if (line[3 + p] == p) all_stable++;
    }
    const Metric metrics[CAPACITY_METRICS] = {
      { "model", "hopfield", 0 },
      { "seed", NULL, config->seed },
      { "task", "capacity", 0 },
      { "update", params->sync ? "sync" : "async", 0 },
      { "rule", params->pinv ? "pinv" : "hebb", 0 },
      { "n_patterns", NULL, p },
      { "n_neurons", NULL, n },
      { "n_rows", NULL, input->n_rows },
      { "n_subsets", NULL, rows },
      { "noise", NULL, params->levels[0] },
      { "trials", NULL, params->trials },
      { "mean_stable_fraction", NULL, stable_sum / rows },
      { "all_stable_fraction", NULL, (double) all_stable / rows },
      { "mean_recall_rate", NULL, recall_sum / rows },
    };
    ok = results_write_metrics(results, metrics, CAPACITY_METRICS);
  }

  free(buf.idx);
  free(buf.table);
  free(buf.patterns);
  free(buf.w);
  free(buf.s);
  free(buf.h);
  free(buf.scratch);
  free(buf.gram);
  free(buf.order);
  return ok;
}


int run_hopfield(const Config * config, Rng * rng, const Results * results) {
  Matrix input;
  if (!matrix_load(config->input, &input)) return 0;

  HopfieldParams params;
  memset(&params, 0, sizeof(params));
  int ok = read_params(config, &input, &params);
  if (ok) {
    ok = params.recall ? run_recall(config, &params, rng, results, &input)
                       : run_capacity(config, &params, rng, results, &input);
  }

  matrix_free(&input);
  return ok;
}
