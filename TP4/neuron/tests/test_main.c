#define _POSIX_C_SOURCE 200809L // mkdir, opendir, dup2

// Dependency-free tests: `make test-c`. Each test_* function reports through check(); the exit code is
// nonzero if any check failed. Run from neuron/ (the fixtures are read as tests/fixtures/...). Everything the
// tests write goes under TMP_DIR and is removed at the end.

#include "../io/config.h"
#include "../io/matrix.h"
#include "../io/results.h"
#include "../models/hopfield_core.h"
#include "../models/models.h"
#include "../rng.h"
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#define TMP_DIR "build/test_tmp"
#define PATH_MAX_TEST 512
#define FILE_MAX_TEST 65536

#define ZSCORE_FIXTURE "tests/fixtures/zscore_small.csv"
#define PATTERNS_FIXTURE "tests/fixtures/patterns_small.csv"
#define PATTERNS_MIX "tests/fixtures/patterns_mix.csv"

static int checks = 0;
static int failures = 0;

#define check(condition) check_at((condition), #condition, __FILE__, __LINE__)
#define check_close(actual, expected, tolerance) \
  check_close_at((actual), (expected), (tolerance), #actual, __FILE__, __LINE__)

static void check_at(int condition, const char * text, const char * file, int line) {
  checks++;
  if (!condition) {
    failures++;
    fprintf(stderr, "  FAIL %s:%d: %s\n", file, line, text);
  }
}

static void check_close_at(double actual, double expected, double tolerance, const char * text, const char * file,
                           int line) {
  checks++;
  if (!(fabs(actual - expected) <= tolerance)) {
    failures++;
    fprintf(stderr, "  FAIL %s:%d: %s = %.10g, expected %.10g (±%g)\n", file, line, text, actual, expected, tolerance);
  }
}


// ---- Temporary files -------------------------------------------------------------------------------------

static void make_dir(const char * path) {
  if (mkdir(path, 0755) != 0 && errno != EEXIST) {
    perror(path);
    exit(EXIT_FAILURE);
  }
}


// Removes everything inside path (not path itself): files, and run directories with their files
static void clear_dir(const char * path) {
  DIR * dir = opendir(path);
  if (dir == NULL) return;

  struct dirent * entry;
  while ((entry = readdir(dir)) != NULL) {
    if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) continue;
    char child[PATH_MAX_TEST];
    snprintf(child, sizeof(child), "%s/%s", path, entry->d_name);
    if (remove(child) != 0) { // a directory that is not empty yet
      clear_dir(child);
      remove(child);
    }
  }
  closedir(dir);
}


static void tmp_start(void) {
  make_dir("build");
  make_dir(TMP_DIR);
  clear_dir(TMP_DIR);
}


static void tmp_finish(void) {
  clear_dir(TMP_DIR);
}


// Writes text to TMP_DIR/name and returns the path in out
static void write_tmp(const char * name, const char * text, char out[PATH_MAX_TEST]) {
  snprintf(out, PATH_MAX_TEST, "%s/%s", TMP_DIR, name);
  FILE * file = fopen(out, "wb");
  if (file == NULL) {
    perror(out);
    exit(EXIT_FAILURE);
  }
  fputs(text, file);
  fclose(file);
}


// Whole file in buf; returns its length or -1
static long read_all(const char * path, char buf[FILE_MAX_TEST]) {
  FILE * file = fopen(path, "rb");
  if (file == NULL) return -1;
  size_t length = fread(buf, 1, FILE_MAX_TEST, file);
  int failed = ferror(file) || length >= FILE_MAX_TEST;
  fclose(file);
  return failed ? -1 : (long) length;
}


// Same name in both directories and the same bytes. Returns how many files dir_a holds, or -1 if any differ.
static int compare_dirs(const char * dir_a, const char * dir_b) {
  DIR * dir = opendir(dir_a);
  if (dir == NULL) return -1;

  static char bytes_a[FILE_MAX_TEST];
  static char bytes_b[FILE_MAX_TEST];
  int n_files = 0;
  int same = 1;
  struct dirent * entry;
  while ((entry = readdir(dir)) != NULL) {
    if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) continue;
    char path_a[PATH_MAX_TEST];
    char path_b[PATH_MAX_TEST];
    snprintf(path_a, sizeof(path_a), "%s/%s", dir_a, entry->d_name);
    snprintf(path_b, sizeof(path_b), "%s/%s", dir_b, entry->d_name);
    long length_a = read_all(path_a, bytes_a);
    long length_b = read_all(path_b, bytes_b);
    if (length_a < 0 || length_a != length_b || memcmp(bytes_a, bytes_b, (size_t) length_a) != 0) same = 0;
    n_files++;
  }
  closedir(dir);
  return same ? n_files : -1;
}


// Same name in both, any bytes: does the one file differ?
static int file_differs(const char * path_a, const char * path_b) {
  static char bytes_a[FILE_MAX_TEST];
  static char bytes_b[FILE_MAX_TEST];
  long length_a = read_all(path_a, bytes_a);
  long length_b = read_all(path_b, bytes_b);
  if (length_a < 0 || length_b < 0) return 0;
  return length_a != length_b || memcmp(bytes_a, bytes_b, (size_t) length_a) != 0;
}


// The bad configs below fail on purpose: their complaints go to /dev/null while silenced
static int silence(void) {
  fflush(stderr);
  int saved = dup(STDERR_FILENO);
  int null = open("/dev/null", O_WRONLY);
  if (saved >= 0 && null >= 0) dup2(null, STDERR_FILENO);
  if (null >= 0) close(null);
  return saved;
}


static void unsilence(int saved) {
  fflush(stderr);
  if (saved >= 0) {
    dup2(saved, STDERR_FILENO);
    close(saved);
  }
}


static int load_quiet(const char * path, Config * config) {
  int saved = silence();
  int ok = config_load(path, config);
  unsilence(saved);
  return ok;
}


static int validate_quiet(const cJSON * object, const KeySpec keys[]) {
  int saved = silence();
  int ok = config_validate_object("test.json", object, keys, "");
  unsilence(saved);
  return ok;
}


// ---- Test 1: strict config validation --------------------------------------------------------------------

static int loads(const char * text) {
  char path[PATH_MAX_TEST];
  write_tmp("config.json", text, path);
  Config config;
  int ok = load_quiet(path, &config);
  if (ok) config_free(&config);
  return ok;
}


static void test_config_strict_validation(void) {
  check(loads("{\"model\": \"oja\", \"seed\": 1, \"input\": \"" ZSCORE_FIXTURE "\"}"));
  check(loads("{\"model\": \"kohonen\", \"seed\": 1, \"input\": \"" ZSCORE_FIXTURE "\", "
              "\"grid_k\": 3, \"neighborhood\": \"step\", \"radius0\": 1.5, \"radius_final\": 1, "
              "\"eta0\": 0.5, \"eta_final\": 0.01, \"epochs\": 5}"));
  check(loads("{\"model\": \"hopfield\", \"seed\": 1, \"input\": \"" PATTERNS_MIX "\", "
              "\"task\": \"recall\", \"rule\": \"hebb\", \"update\": \"async\", \"max_sweeps\": 100, "
              "\"trials\": 2, \"noise_levels\": [0.0, 0.5], \"subset\": [0, 1, 2, 3], \"trace_trials\": 1}"));

  check(!loads("{\"model\": \"oja\", \"seed\": 1, \"input\": \"x.csv\", \"bogus\": 1}"));
  check(!loads("{\"model\": \"oja\", \"seed\": 1, \"seed\": 2, \"input\": \"x.csv\"}"));
  check(!loads("{\"model\": \"oja\", \"input\": \"x.csv\"}"));
  check(!loads("{\"model\": \"oja\", \"seed\": \"1\", \"input\": \"x.csv\"}"));
  check(!loads("{\"model\": \"oja\", \"seed\": -1, \"input\": \"x.csv\"}"));
  check(!loads("{\"model\": \"kohonen\", \"seed\": 1, \"input\": \"x.csv\", \"grid_k\": 2.5}"));
  check(!loads("{\"model\": \"oja\", \"seed\": 1, \"input\": \"x.csv\", \"grid_k\": 3}"));
  check(!loads("{\"model\": \"kohonen\", \"seed\": 1, \"input\": \"x.csv\"}"));
  check(!loads("{\"model\": \"som\", \"seed\": 1, \"input\": \"x.csv\"}"));
  check(!loads("{\"model\": \"hopfield\", \"seed\": 1, \"input\": \"x.csv\", \"noise_levels\": [\"a\"]}"));
  check(!loads("{\"model\": \"hopfield\", \"seed\": 1, \"input\": \"x.csv\", \"noise_levels\": []}"));
  // The valid Hopfield case with no task, with a fractional trials and with a key of another model
  check(!loads("{\"model\": \"hopfield\", \"seed\": 1, \"input\": \"" PATTERNS_MIX "\", "
               "\"rule\": \"hebb\", \"update\": \"async\", \"max_sweeps\": 100, "
               "\"trials\": 2, \"noise_levels\": [0.0, 0.5], \"subset\": [0, 1, 2, 3], \"trace_trials\": 1}"));
  check(!loads("{\"model\": \"hopfield\", \"seed\": 1, \"input\": \"" PATTERNS_MIX "\", "
               "\"task\": \"recall\", \"rule\": \"hebb\", \"update\": \"async\", \"max_sweeps\": 100, "
               "\"trials\": 2.5, \"noise_levels\": [0.0, 0.5], \"subset\": [0, 1, 2, 3], \"trace_trials\": 1}"));
  check(!loads("{\"model\": \"hopfield\", \"seed\": 1, \"input\": \"" PATTERNS_MIX "\", "
               "\"task\": \"recall\", \"rule\": \"hebb\", \"update\": \"async\", \"max_sweeps\": 100, "
               "\"trials\": 2, \"noise_levels\": [0.0, 0.5], \"subset\": [0, 1, 2, 3], \"trace_trials\": 1, "
               "\"grid_k\": 3}"));
  check(!loads("{\"model\": \"oja\", \"seed\": "));
  check(!loads("[1, 2]"));

  // Nested objects: a table with one KEY_OBJECT row whose children are { k KEY_INT required }
  static const KeySpec CHILDREN[] = {
    { "k", KEY_INT, 1, NULL },
    { NULL, KEY_INT, 0, NULL },
  };
  static const KeySpec TOP[] = {
    { "a", KEY_OBJECT, 1, CHILDREN },
    { NULL, KEY_INT, 0, NULL },
  };
  cJSON * unknown = cJSON_Parse("{\"a\": {\"k\": 3, \"z\": 1}}");
  cJSON * missing = cJSON_Parse("{\"a\": {}}");
  cJSON * valid = cJSON_Parse("{\"a\": {\"k\": 3}}");
  check(unknown != NULL && missing != NULL && valid != NULL);
  if (unknown != NULL) check(!validate_quiet(unknown, TOP));
  if (missing != NULL) check(!validate_quiet(missing, TOP));
  if (valid != NULL) check(validate_quiet(valid, TOP));
  cJSON_Delete(unknown);
  cJSON_Delete(missing);
  cJSON_Delete(valid);

  // A dotted key reaches into the nested object
  Config nested;
  memset(&nested, 0, sizeof(nested));
  strcpy(nested.path, "nested.json");
  nested.json = cJSON_Parse("{\"a\": {\"k\": 3}}");
  check(nested.json != NULL);
  int k = 0;
  check(config_get_int(&nested, "a.k", &k));
  check(k == 3);
  config_free(&nested);
}


// ---- Test 2: same seed, same bytes -----------------------------------------------------------------------

// Runs the model of the config at path into the directory TMP_DIR/name with a fresh Rng(seed)
static int run_into(const Config * config, unsigned int seed, const char * name, char dir[PATH_MAX_TEST]) {
  snprintf(dir, PATH_MAX_TEST, "%s/%s", TMP_DIR, name);
  make_dir(dir);

  Results results;
  snprintf(results.dir, sizeof(results.dir), "%s", dir);
  Rng rng = rng_new(seed);
  const Model * model = model_find(config->model);
  if (model == NULL) return 0;
  return model->run(config, &rng, &results);
}


// Two runs with the same seed give the same bytes in every file; seed + 1 changes seed_file (NULL: not checked)
static void same_seed_same_bytes(const char * name, const char * config_text, const char * seed_file) {
  char path[PATH_MAX_TEST];
  write_tmp("run.json", config_text, path);
  Config config;
  check(load_quiet(path, &config));

  char dir_a[PATH_MAX_TEST];
  char dir_b[PATH_MAX_TEST];
  char dir_c[PATH_MAX_TEST];
  char label[64];
  snprintf(label, sizeof(label), "%s_a", name);
  check(run_into(&config, config.seed, label, dir_a));
  snprintf(label, sizeof(label), "%s_b", name);
  check(run_into(&config, config.seed, label, dir_b));
  snprintf(label, sizeof(label), "%s_c", name);
  check(run_into(&config, config.seed + 1, label, dir_c));

  check(compare_dirs(dir_a, dir_b) >= 2); // at least one table and metrics.json
  if (seed_file != NULL) {
    char file_a[PATH_MAX_TEST];
    char file_c[PATH_MAX_TEST];
    snprintf(file_a, sizeof(file_a), "%s/%s", dir_a, seed_file);
    snprintf(file_c, sizeof(file_c), "%s/%s", dir_c, seed_file);
    check(file_differs(file_a, file_c));
  }
  config_free(&config);
}


static void test_same_seed_same_bytes(void) {
  same_seed_same_bytes("oja",
                       "{\"model\": \"oja\", \"seed\": 5, \"input\": \"" ZSCORE_FIXTURE "\"}", "weights.csv");
  // 9 neurons on 6 rows: the case also covers more neurons than samples
  same_seed_same_bytes("kohonen",
                       "{\"model\": \"kohonen\", \"seed\": 5, \"input\": \"" ZSCORE_FIXTURE "\", "
                       "\"grid_k\": 3, \"neighborhood\": \"step\", \"radius0\": 1.5, \"radius_final\": 1, "
                       "\"eta0\": 0.5, \"eta_final\": 0.01, \"epochs\": 5}",
                       "prototypes.csv");
  // The noisy queries and the async orders come from the seed, so trials.csv changes with it
  same_seed_same_bytes("hopfield",
                       "{\"model\": \"hopfield\", \"seed\": 5, \"input\": \"" PATTERNS_MIX "\", "
                       "\"task\": \"recall\", \"rule\": \"hebb\", \"update\": \"async\", \"max_sweeps\": 100, "
                       "\"trials\": 3, \"noise_levels\": [0.0, 0.24], \"subset\": [0, 1, 2, 3], "
                       "\"trace_trials\": 1}",
                       "trials.csv");

  Rng first = rng_new(7);
  Rng second = rng_new(7);
  int identical = 1;
  for (int i = 0; i < 100; i++) {
    if (rng_uniform(&first) != rng_uniform(&second)) identical = 0;
  }
  check(identical);

  // The fixture has no newline at the end of the last row
  Matrix matrix;
  check(matrix_load(ZSCORE_FIXTURE, &matrix));
  check(matrix.n_rows == 6);
  check(matrix.n_cols == 3);
  check_close(matrix.data[0], 0.5, 0);
  check_close(matrix.data[5 * 3 + 2], -0.72, 1e-12);
  matrix_free(&matrix);
}


// ---- Test 3: dispatch by model ---------------------------------------------------------------------------

static void test_dispatch_by_model(void) {
  static const struct {
    const char * name;
    ModelRun run;
  } EXPECTED[] = {
    { "kohonen", run_kohonen },
    { "oja", run_oja },
    { "hopfield", run_hopfield },
  };

  for (int i = 0; i < 3; i++) {
    const Model * model = model_find(EXPECTED[i].name);
    check(model != NULL);
    if (model != NULL) {
      check(strcmp(model->name, EXPECTED[i].name) == 0);
      check(model->run == EXPECTED[i].run);
    }
    check(strstr(model_names(), EXPECTED[i].name) != NULL);
    check(config_model_keys(EXPECTED[i].name) != NULL); // the config table and the dispatch table agree
  }
  check(model_find("som") == NULL);
  check(config_model_keys("som") == NULL);
}


// ---- Test 4: Kohonen training ----------------------------------------------------------------------------

// Data lines of a CSV (everything after the header); -1 if it can't be read
static int count_data_lines(const char * path) {
  static char bytes[FILE_MAX_TEST];
  long length = read_all(path, bytes);
  if (length < 0) return -1;
  int lines = 0;
  for (long i = 0; i < length; i++) {
    if (bytes[i] == '\n') lines++;
  }
  if (length > 0 && bytes[length - 1] != '\n') lines++;
  return lines - 1;
}


// Value in column (0-based) of data row (0-based, after the header) of a CSV with plain numeric fields
static int csv_value(const char * path, int data_row, int column, double * out) {
  static char bytes[FILE_MAX_TEST];
  long length = read_all(path, bytes);
  if (length < 0) return 0;
  bytes[length] = '\0';

  const char * line = bytes;
  for (int row = 0; row < data_row + 1; row++) { // skip the header and data_row lines
    line = strchr(line, '\n');
    if (line == NULL) return 0;
    line++;
  }
  const char * field = line;
  for (int col = 0; col < column; col++) {
    while (*field != ',' && *field != '\n' && *field != '\0') field++;
    if (*field != ',') return 0;
    field++;
  }
  char * end;
  *out = strtod(field, &end);
  return end != field;
}


// A step or gaussian run on the 6-row fixture with the given values; 1 if the model accepts the config
static int fixture_run_accepts(const char * neighborhood, double radius0, double radius_final, double eta0,
                               double eta_final, int grid_k, int epochs) {
  char text[1024];
  snprintf(text, sizeof(text),
           "{\"model\": \"kohonen\", \"seed\": 1, \"input\": \"" ZSCORE_FIXTURE "\", \"grid_k\": %d, "
           "\"neighborhood\": \"%s\", \"radius0\": %.17g, \"radius_final\": %.17g, \"eta0\": %.17g, "
           "\"eta_final\": %.17g, \"epochs\": %d}",
           grid_k, neighborhood, radius0, radius_final, eta0, eta_final, epochs);
  char path[PATH_MAX_TEST];
  write_tmp("bad.json", text, path);
  Config config;
  if (!load_quiet(path, &config)) return -1; // the types must be valid: only the values are wrong
  char dir[PATH_MAX_TEST];
  int saved = silence();
  int ok = run_into(&config, config.seed, "rejected", dir);
  unsilence(saved);
  config_free(&config);
  return ok;
}


static void test_kohonen_training(void) {
  // (a) the neighborhood: radius 1 reaches the four adjacent cells and not the diagonals
  check_close(kohonen_neighbor_weight(0, 1.0, 0), 1.0, 0);
  check_close(kohonen_neighbor_weight(1, 1.0, 0), 1.0, 0);
  check_close(kohonen_neighbor_weight(2, 1.0, 0), 0.0, 0);
  check_close(kohonen_neighbor_weight(4, 1.0, 0), 0.0, 0);
  double last_radius = kohonen_radius(3.0, 1.0, 1.0);
  check(last_radius >= 1.0);
  check_close(kohonen_neighbor_weight(1, last_radius, 0), 1.0, 0);
  check_close(kohonen_neighbor_weight(0, 1.0, 1), 1.0, 0);
  check_close(kohonen_neighbor_weight(1, 1.0, 1), exp(-0.5), 1e-15);
  check_close(kohonen_neighbor_weight(0, 0.001, 1), 1.0, 0);

  // (b) the decay starts at the start value and ends at the end value
  check_close(kohonen_decay(0.5, 0.01, 0.0), 0.5, 0);
  check_close(kohonen_decay(0.5, 0.01, 1.0), 0.01, 1e-15);

  // (c) more neurons (9) than samples (6): every sample is counted once and the trace follows the schedule
  char path[PATH_MAX_TEST];
  write_tmp("som.json",
            "{\"model\": \"kohonen\", \"seed\": 3, \"input\": \"" ZSCORE_FIXTURE "\", \"grid_k\": 3, "
            "\"neighborhood\": \"step\", \"radius0\": 1.5, \"radius_final\": 1, \"eta0\": 0.5, "
            "\"eta_final\": 0.01, \"epochs\": 4}",
            path);
  Config config;
  check(load_quiet(path, &config));
  char dir[PATH_MAX_TEST];
  check(run_into(&config, config.seed, "som", dir));
  config_free(&config);

  char file[PATH_MAX_TEST];
  snprintf(file, sizeof(file), "%s/prototypes.csv", dir);
  check(count_data_lines(file) == 9);

  snprintf(file, sizeof(file), "%s/occupancy.csv", dir);
  check(count_data_lines(file) == 9);
  double hits_sum = 0;
  for (int row = 0; row < 9; row++) {
    double hits = -1;
    check(csv_value(file, row, 3, &hits));
    hits_sum += hits;
  }
  check_close(hits_sum, 6, 0);

  snprintf(file, sizeof(file), "%s/trace.csv", dir);
  check(count_data_lines(file) == 5);
  double value;
  check(csv_value(file, 0, 0, &value));
  check_close(value, 0, 0);
  check(csv_value(file, 0, 1, &value));
  check_close(value, 0.5, 1e-12);
  check(csv_value(file, 0, 2, &value));
  check_close(value, 1.5, 1e-12);
  check(csv_value(file, 4, 0, &value));
  check_close(value, 4, 0);
  check(csv_value(file, 4, 1, &value));
  check_close(value, 0.01, 1e-12);
  check(csv_value(file, 4, 2, &value));
  check_close(value, 1.0, 1e-12);

  // (d) the gaussian neighborhood is reproducible and depends on the seed
  same_seed_same_bytes("kohonen_gaussian",
                       "{\"model\": \"kohonen\", \"seed\": 5, \"input\": \"" ZSCORE_FIXTURE "\", "
                       "\"grid_k\": 3, \"neighborhood\": \"gaussian\", \"radius0\": 1.5, \"radius_final\": 0.5, "
                       "\"eta0\": 0.5, \"eta_final\": 0.01, \"epochs\": 5}",
                       "prototypes.csv");

  // (e) configs of the right types whose values the model refuses
  check(fixture_run_accepts("step", 1.5, 1, 0.5, 0.01, 3, 5) == 1); // the baseline of the cases below
  check(fixture_run_accepts("hex", 1.5, 1, 0.5, 0.01, 3, 5) == 0);
  check(fixture_run_accepts("step", 1.5, 1, 1.0, 0.01, 3, 5) == 0);
  check(fixture_run_accepts("step", 1.5, 1, 0.5, 0.6, 3, 5) == 0);
  check(fixture_run_accepts("step", 1.5, 0.5, 0.5, 0.01, 3, 5) == 0);
  check(fixture_run_accepts("gaussian", 1.5, 0, 0.5, 0.01, 3, 5) == 0);
  check(fixture_run_accepts("step", 0.5, 0.5, 0.5, 0.01, 3, 5) == 0);
  check(fixture_run_accepts("step", 1.5, 2, 0.5, 0.01, 3, 5) == 0);
  check(fixture_run_accepts("step", 1.5, 1, 0.5, 0.01, 1, 5) == 0);
  check(fixture_run_accepts("step", 1.5, 1, 0.5, 0.01, 33, 5) == 0);
  check(fixture_run_accepts("step", 1.5, 1, 0.5, 0.01, 3, 0) == 0);
}


// ---- Test 5: Hopfield network ----------------------------------------------------------------------------

// Number under key in dir/metrics.json; 0 if the file or the key is missing
static int metrics_number(const char * dir, const char * key, double * out) {
  static char bytes[FILE_MAX_TEST];
  char path[PATH_MAX_TEST];
  snprintf(path, sizeof(path), "%s/metrics.json", dir);
  long length = read_all(path, bytes);
  if (length < 0) return 0;
  bytes[length] = '\0';
  cJSON * json = cJSON_Parse(bytes);
  if (json == NULL) return 0;
  const cJSON * item = cJSON_GetObjectItemCaseSensitive(json, key);
  int found = cJSON_IsNumber(item);
  if (found) *out = item->valuedouble;
  cJSON_Delete(json);
  return found;
}


// The config fragment of a Hopfield run on the synthetic fixture; every argument is a string literal
#define HOP_FRAGMENT(task, rule, update, sweeps, trials, noise, extra) \
  "\"input\": \"" PATTERNS_MIX "\", \"task\": \"" task "\", \"rule\": \"" rule "\", \"update\": \"" update "\", " \
  "\"max_sweeps\": " sweeps ", \"trials\": " trials ", \"noise_levels\": " noise extra
#define HOP_SUBSET ", \"subset\": [0, 1, 2, 3], \"trace_trials\": 1"

// 1 if the Hopfield model accepts the config, 0 if the run refuses it, -1 if the types are wrong
static int hopfield_run_accepts(const char * fragment) {
  char text[2048];
  snprintf(text, sizeof(text), "{\"model\": \"hopfield\", \"seed\": 1, %s}", fragment);
  char path[PATH_MAX_TEST];
  write_tmp("hop_bad.json", text, path);
  Config config;
  if (!load_quiet(path, &config)) return -1;
  char dir[PATH_MAX_TEST];
  int saved = silence();
  int ok = run_into(&config, config.seed, "hop_rejected", dir);
  unsilence(saved);
  config_free(&config);
  return ok;
}


static void test_hopfield_run(void) {
  char path[PATH_MAX_TEST];
  write_tmp("hop_run.json",
            "{\"model\": \"hopfield\", \"seed\": 3, " HOP_FRAGMENT("recall", "hebb", "async", "100", "4", "[0.0, 0.24]",
                                                                      HOP_SUBSET) "}",
            path);
  Config config;
  check(load_quiet(path, &config));
  char dir[PATH_MAX_TEST];
  check(run_into(&config, config.seed, "hop_run", dir));
  config_free(&config);

  char file[PATH_MAX_TEST + 32];
  snprintf(file, sizeof(file), "%s/trials.csv", dir);
  check(count_data_lines(file) == 32);
  for (int a = 0; a < 4; a++) {
    for (int t = 0; t < 4; t++) {
      int row = a * 8 + t; // noise 0 comes first for every pattern
      double v;
      check(csv_value(file, row, 3, &v) && v == 0);
      check(csv_value(file, row, 6, &v) && v == 1);  // converged
      check(csv_value(file, row, 7, &v) && v == 1);  // sweeps
      check(csv_value(file, row, 9, &v) && v == 0);  // flips
      check(csv_value(file, row, 11, &v) && v == 0); // class stored
      check(csv_value(file, row, 12, &v) && v == a); // match_a
      check(csv_value(file, row, 18, &v) && v == 1); // correct
      double e_start = 1;
      double e_final = 2;
      check(csv_value(file, row, 19, &e_start) && csv_value(file, row, 20, &e_final) && e_start == e_final);
    }
  }

  // Planning-time numpy values for rows 0-3 of the fixture
  static const double MARGIN[4] = { 10, 2, 12, 16 };
  static const double ENERGY[4] = { -304, -332, -288, -268 };
  snprintf(file, sizeof(file), "%s/stored.csv", dir);
  check(count_data_lines(file) == 4);
  for (int a = 0; a < 4; a++) {
    double v;
    check(csv_value(file, a, 2, &v) && v == 1);
    check(csv_value(file, a, 3, &v) && v == MARGIN[a]);
    check(csv_value(file, a, 5, &v) && v == ENERGY[a]);
  }

  snprintf(file, sizeof(file), "%s/overlaps.csv", dir);
  double overlap = 0;
  check(csv_value(file, 1, 1, &overlap));
  check_close(overlap, 0.36, 1e-15);

  snprintf(file, sizeof(file), "%s/states.csv", dir);
  check(count_data_lines(file) == 16);

  snprintf(file, sizeof(file), "%s/trace.csv", dir);
  double v;
  check(csv_value(file, 0, 0, &v) && v == 0);
  check(csv_value(file, 0, 1, &v) && v == 0);
  check(csv_value(file, 0, 2, &v) && v == 0);
  check(csv_value(file, 0, 3, &v) && v == -1);
  check(csv_value(file, 0, 4, &v) && v == 0);
  check(csv_value(file, 0, 5, &v) && v == -304);
  check(csv_value(file, 25, 0, &v) && v == 0);  // step 0 and one quiet sweep of 25 visits
  check(csv_value(file, 26, 0, &v) && v != 0);

  double metric = -1;
  check(metrics_number(dir, "energy_increases", &metric) && metric == 0);
  check(metrics_number(dir, "stored_fixed", &metric) && metric == 4);
  check(metrics_number(dir, "recall_rate", &metric) && metric >= 0.5);

  // The same config with the synchronous update
  write_tmp("hop_sync.json",
            "{\"model\": \"hopfield\", \"seed\": 3, " HOP_FRAGMENT("recall", "hebb", "sync", "100", "4", "[0.0, 0.24]",
                                                                      HOP_SUBSET) "}",
            path);
  check(load_quiet(path, &config));
  check(run_into(&config, config.seed, "hop_sync", dir));
  config_free(&config);
  snprintf(file, sizeof(file), "%s/trials.csv", dir);
  check(count_data_lines(file) == 32);
  for (int a = 0; a < 4; a++) {
    for (int t = 0; t < 4; t++) {
      int row = a * 8 + t;
      double sweeps = 0;
      double correct = 0;
      check(csv_value(file, row, 7, &sweeps) && sweeps == 1);
      check(csv_value(file, row, 18, &correct) && correct == 1);
    }
  }
  same_seed_same_bytes("hopfield_sync",
                       "{\"model\": \"hopfield\", \"seed\": 5, " HOP_FRAGMENT("recall", "hebb", "sync", "100", "3",
                                                                                 "[0.0, 0.24]", HOP_SUBSET) "}",
                       "trials.csv");

  // Refusals
  check(hopfield_run_accepts(HOP_FRAGMENT("recall", "hebb", "async", "100", "4", "[0.0]", HOP_SUBSET)) == 1);
  check(hopfield_run_accepts(HOP_FRAGMENT("recall", "hebb", "async", "100", "4", "[0.0]",
                                          ", \"subset\": [0, 6], \"trace_trials\": 1")) == 0);
  check(hopfield_run_accepts(HOP_FRAGMENT("recall", "hebb", "async", "100", "4", "[0.0]",
                                          ", \"subset\": [1, 1], \"trace_trials\": 1")) == 0);
  check(hopfield_run_accepts(HOP_FRAGMENT("recall", "hebb", "async", "100", "4", "[0.0]",
                                          ", \"subset\": [0.5], \"trace_trials\": 1")) == 0);
  check(hopfield_run_accepts(HOP_FRAGMENT("recall", "hebb", "async", "100", "4", "[0.0]",
                                          ", \"trace_trials\": 1")) == 0);
  check(hopfield_run_accepts(HOP_FRAGMENT("recall", "hebb", "async", "100", "4", "[0.0]",
                                          ", \"subset\": [0, 1, 2, 3]")) == 0);
  check(hopfield_run_accepts(HOP_FRAGMENT("recall", "hebb", "async", "100", "4", "[0.0]",
                                          ", \"subset\": [0, 1, 2, 3], \"trace_trials\": 5")) == 0);
  check(hopfield_run_accepts(HOP_FRAGMENT("recall", "hebb", "async", "100", "4", "[0.0]",
                                          ", \"subset\": [0, 1, 2, 3], \"trace_trials\": -1")) == 0);
  check(hopfield_run_accepts(HOP_FRAGMENT("recall", "hebb", "async", "0", "4", "[0.0]", HOP_SUBSET)) == 0);
  check(hopfield_run_accepts(HOP_FRAGMENT("recall", "hebb", "async", "10001", "4", "[0.0]", HOP_SUBSET)) == 0);
  check(hopfield_run_accepts(HOP_FRAGMENT("recall", "hebb", "async", "100", "0", "[0.0]", HOP_SUBSET)) == 0);
  check(hopfield_run_accepts(HOP_FRAGMENT("recall", "hebb", "hex", "100", "4", "[0.0]", HOP_SUBSET)) == 0);
  check(hopfield_run_accepts(HOP_FRAGMENT("recall", "pinv", "async", "100", "4", "[0.0]", HOP_SUBSET)) == 0);
  check(hopfield_run_accepts(HOP_FRAGMENT("bogus", "hebb", "async", "100", "4", "[0.0]", HOP_SUBSET)) == 0);
  check(hopfield_run_accepts(HOP_FRAGMENT("recall", "hebb", "async", "100", "4", "[0.0, 1.5]", HOP_SUBSET)) == 0);
  char zeros[PATH_MAX_TEST];
  write_tmp("hop_zeros.csv", "a,b\n1,0\n-1,1\n", zeros);
  char fragment[1024];
  snprintf(fragment, sizeof(fragment),
           "\"input\": \"%s\", \"task\": \"recall\", \"rule\": \"hebb\", \"update\": \"async\", "
           "\"max_sweeps\": 100, \"trials\": 4, \"noise_levels\": [0.0], \"subset\": [0, 1], \"trace_trials\": 1",
           zeros);
  check(hopfield_run_accepts(fragment) == 0);
}


// Config text of a capacity run on the synthetic fixture
#define CAP_CONFIG(seed, p, n_subsets, trials) \
  "{\"model\": \"hopfield\", \"seed\": " seed ", " \
  HOP_FRAGMENT("capacity", "hebb", "async", "100", trials, "[0.12]", ", \"p\": " p ", \"n_subsets\": " n_subsets) "}"

// Runs the config text and leaves the run directory in dir
static void capacity_run(const char * name, const char * text, char dir[]) {
  char path[PATH_MAX_TEST];
  write_tmp("hop_cap.json", text, path);
  Config config;
  check(load_quiet(path, &config));
  check(run_into(&config, config.seed, name, dir));
  config_free(&config);
}


static void test_hopfield_capacity(void) {
  // Planning-time numpy values for the 15 subsets of 4 rows of the fixture
  static const double N_STABLE[15] = { 4, 2, 4, 3, 4, 2, 4, 4, 3, 4, 4, 4, 4, 4, 4 };
  static const double MIN_MARGIN[15] = { 2, -2, 4, -2, 6, -6, 4, 10, -2, 2, 6, 10, 6, 10, 10 };
  char dir[PATH_MAX_TEST];
  char file[PATH_MAX_TEST + 32];
  double v;

  capacity_run("hop_cap4", CAP_CONFIG("2", "4", "0", "2"), dir);
  snprintf(file, sizeof(file), "%s/capacity.csv", dir);
  check(count_data_lines(file) == 15);
  for (int r = 0; r < 15; r++) {
    check(csv_value(file, r, 0, &v) && v == r);
    check(csv_value(file, r, 7, &v) && v == N_STABLE[r]);
    check(csv_value(file, r, 8, &v));
    check_close(v, N_STABLE[r] / 4, 1e-15);
    check(csv_value(file, r, 9, &v) && v == MIN_MARGIN[r]);
    check(csv_value(file, r, 10, &v) && v >= 0 && v <= 1);
  }
  static const double FIRST[4] = { 0, 1, 2, 3 };
  static const double LAST[4] = { 2, 3, 4, 5 };
  for (int c = 0; c < 4; c++) {
    check(csv_value(file, 0, 1 + c, &v) && v == FIRST[c]);
    check(csv_value(file, 14, 1 + c, &v) && v == LAST[c]);
  }
  check(csv_value(file, 0, 5, &v));
  check_close(v, 0.36, 1e-15);
  check(csv_value(file, 1, 5, &v));
  check_close(v, 0.52, 1e-15);
  check(csv_value(file, 0, 6, &v));
  check_close(v, 22.0 / 150, 1e-15);

  double metric = -1;
  check(metrics_number(dir, "n_subsets", &metric) && metric == 15);
  check(metrics_number(dir, "n_patterns", &metric) && metric == 4);
  check(metrics_number(dir, "n_rows", &metric) && metric == 6);
  check(metrics_number(dir, "mean_stable_fraction", &metric));
  check_close(metric, 0.9, 1e-12);
  check(metrics_number(dir, "all_stable_fraction", &metric));
  check_close(metric, 11.0 / 15, 1e-12);

  // The exhaustive list doesn't depend on the seed
  char other[PATH_MAX_TEST];
  char other_file[PATH_MAX_TEST + 32];
  capacity_run("hop_cap4_seed9", CAP_CONFIG("9", "4", "0", "2"), other);
  snprintf(other_file, sizeof(other_file), "%s/capacity.csv", other);
  for (int r = 0; r < 15; r++) {
    for (int c = 0; c < 5; c++) {
      double a = 0;
      double b = 1;
      check(csv_value(file, r, c, &a) && csv_value(other_file, r, c, &b) && a == b);
    }
  }
  same_seed_same_bytes("hopfield_capacity", CAP_CONFIG("2", "4", "0", "2"), "capacity.csv");

  // p = 3: every subset is stable, row 2 is (0, 1, 4) with a tie at margin 0
  capacity_run("hop_cap3", CAP_CONFIG("2", "3", "0", "2"), dir);
  snprintf(file, sizeof(file), "%s/capacity.csv", dir);
  check(count_data_lines(file) == 20);
  for (int r = 0; r < 20; r++) check(csv_value(file, r, 6, &v) && v == 3);
  check(csv_value(file, 2, 1, &v) && v == 0);
  check(csv_value(file, 2, 2, &v) && v == 1);
  check(csv_value(file, 2, 3, &v) && v == 4);
  check(csv_value(file, 2, 8, &v) && v == 0);

  // p = 1: margin N - 1 and no pair
  capacity_run("hop_cap1", CAP_CONFIG("2", "1", "0", "2"), dir);
  snprintf(file, sizeof(file), "%s/capacity.csv", dir);
  check(count_data_lines(file) == 6);
  for (int r = 0; r < 6; r++) {
    check(csv_value(file, r, 2, &v) && v == 0);
    check(csv_value(file, r, 6, &v) && v == 24);
  }

  // Sampled subsets: distinct, ascending, depend on the seed
  capacity_run("hop_cap_sampled", CAP_CONFIG("4", "3", "10", "2"), dir);
  snprintf(file, sizeof(file), "%s/capacity.csv", dir);
  check(count_data_lines(file) == 10);
  for (int r = 0; r < 10; r++) {
    double a[3];
    for (int c = 0; c < 3; c++) check(csv_value(file, r, 1 + c, &a[c]));
    check(a[0] < a[1] && a[1] < a[2] && a[2] <= 5);
    check(csv_value(file, r, 6, &v) && v == 3);
    for (int q = 0; q < r; q++) {
      int same = 1;
      for (int c = 0; c < 3; c++) {
        double b;
        check(csv_value(file, q, 1 + c, &b));
        if (b != a[c]) same = 0;
      }
      check(!same);
    }
  }
  same_seed_same_bytes("hopfield_capacity_sampled", CAP_CONFIG("4", "3", "10", "2"), "capacity.csv");

  // Refusals
  check(hopfield_run_accepts(HOP_FRAGMENT("capacity", "hebb", "async", "100", "2", "[0.12]",
                                          ", \"p\": 3, \"n_subsets\": 19")) == 1);
  check(hopfield_run_accepts(HOP_FRAGMENT("capacity", "hebb", "async", "100", "2", "[0.12]",
                                          ", \"p\": 3, \"n_subsets\": 20")) == 0);
  check(hopfield_run_accepts(HOP_FRAGMENT("capacity", "hebb", "async", "100", "2", "[0.12]",
                                          ", \"p\": 0, \"n_subsets\": 0")) == 0);
  check(hopfield_run_accepts(HOP_FRAGMENT("capacity", "hebb", "async", "100", "2", "[0.12]",
                                          ", \"p\": 7, \"n_subsets\": 0")) == 0);
  check(hopfield_run_accepts(HOP_FRAGMENT("capacity", "hebb", "async", "100", "2", "[0.12]",
                                          ", \"p\": 3, \"n_subsets\": -1")) == 0);
  check(hopfield_run_accepts(HOP_FRAGMENT("capacity", "hebb", "async", "100", "2", "[0.12]",
                                          ", \"p\": 3, \"n_subsets\": 10001")) == 0);
  check(hopfield_run_accepts(HOP_FRAGMENT("capacity", "hebb", "async", "100", "2", "[0.12, 0.2]",
                                          ", \"p\": 3, \"n_subsets\": 0")) == 0);
  check(hopfield_run_accepts(HOP_FRAGMENT("capacity", "hebb", "async", "100", "2", "[0.12]",
                                          ", \"p\": 3, \"n_subsets\": 0, \"subset\": [0, 1]")) == 0);
  check(hopfield_run_accepts(HOP_FRAGMENT("capacity", "hebb", "async", "100", "2", "[0.12]",
                                          ", \"p\": 3, \"n_subsets\": 0, \"trace_trials\": 0")) == 0);
  check(hopfield_run_accepts(HOP_FRAGMENT("capacity", "hebb", "async", "100", "2", "[0.12]",
                                          ", \"n_subsets\": 0")) == 0);
  check(hopfield_run_accepts(HOP_FRAGMENT("capacity", "hebb", "async", "100", "2", "[0.12]", ", \"p\": 3")) == 0);
  check(hopfield_run_accepts(HOP_FRAGMENT("recall", "hebb", "async", "100", "4", "[0.0]",
                                          HOP_SUBSET ", \"p\": 2")) == 0);
  check(hopfield_run_accepts(HOP_FRAGMENT("recall", "hebb", "async", "100", "4", "[0.0]",
                                          HOP_SUBSET ", \"n_subsets\": 0")) == 0);
}


// State sign(sa xi_a + sb xi_b + sc xi_c) into out
static void mixture_of(const double patterns[], int n, int a, int b, int c, double out[]) {
  for (int j = 0; j < n; j++) {
    double sum = patterns[a * n + j] + patterns[b * n + j] + patterns[c * n + j];
    out[j] = sum > 0 ? 1 : -1;
  }
}


static void test_hopfield_core(void) {
  // (a) the course example (slides 26-32)
  static const double COURSE[8] = { 1, 1, -1, -1, -1, -1, 1, 1 };
  double w4[16];
  hopfield_hebb(COURSE, 2, 4, w4);
  check(w4[0 * 4 + 1] == 2 && w4[0 * 4 + 2] == -2 && w4[0 * 4 + 3] == -2);
  check(w4[1 * 4 + 2] == -2 && w4[1 * 4 + 3] == -2 && w4[2 * 4 + 3] == 2);
  int symmetric = 1;
  for (int i = 0; i < 4; i++) {
    check(w4[i * 4 + i] == 0);
    for (int j = 0; j < 4; j++) symmetric = symmetric && w4[i * 4 + j] == w4[j * 4 + i];
  }
  check(symmetric);
  double zeta[4] = { 1, -1, -1, -1 };
  double h4[4];
  hopfield_fields(w4, 4, zeta, h4);
  check(h4[0] == 2 && h4[1] == 6 && h4[2] == -2 && h4[3] == -2);
  double next4[4];
  check(hopfield_sync_step(w4, 4, zeta, next4) == 1);
  check(next4[0] == 1 && next4[1] == 1 && next4[2] == -1 && next4[3] == -1);
  int match[3];
  int sign[3];
  check(hopfield_classify(COURSE, 2, 4, next4, match, sign) == HOPFIELD_STORED);
  check(match[0] == 0 && sign[0] == 1 && match[1] == -1 && sign[1] == 0);
  check(hopfield_energy(w4, 4, COURSE) == -12);
  check(hopfield_energy(w4, 4, zeta) == 0);

  // (b) Hebb on rows 0-3 of the fixture
  Matrix fixture;
  check(matrix_load(PATTERNS_MIX, &fixture));
  const double * rows = fixture.data;
  double w[25 * 25];
  hopfield_hebb(rows, 4, 25, w);
  int integral = 1;
  int sym = 1;
  double max_abs = 0;
  for (int i = 0; i < 25; i++) {
    check(w[i * 25 + i] == 0);
    for (int j = 0; j < 25; j++) {
      integral = integral && w[i * 25 + j] == floor(w[i * 25 + j]);
      sym = sym && w[i * 25 + j] == w[j * 25 + i];
      if (fabs(w[i * 25 + j]) > max_abs) max_abs = fabs(w[i * 25 + j]);
    }
  }
  check(integral && sym);
  check(max_abs == 4);
  check(w[0 * 25 + 1] == 0);

  // (c) a zero field keeps the state
  double wt[9] = { 0, 1, -1, 1, 0, 0, -1, 0, 0 };
  double tie[3] = { -1, 1, 1 };
  double tie_next[3];
  hopfield_sync_step(wt, 3, tie, tie_next);
  check(tie_next[0] == -1);
  {
    double s[3] = { -1, 1, 1 };
    double h[3];
    int order[3] = { 0, 1, 2 };
    Rng rng = rng_new(1);
    HopfieldTrace trace = { NULL, 0, 0, 1000, 0 };
    HopfieldOutcome out;
    check(hopfield_async_run(wt, 3, s, h, order, &rng, 10, &trace, &out));
    int found = 0;
    for (long long r = 0; r < trace.rows && !found; r++) {
      const double * line = trace.data + r * HOPFIELD_TRACE_WIDTH;
      if (line[3] == 0) {
        found = 1;
        check(line[4] == 0); // the first visit of neuron 0 changes nothing
      }
    }
    check(found);
    check(out.converged);
    hopfield_trace_free(&trace);
  }

  // (d) incremental energy against the energy from scratch, monotone in async
  {
    Rng rng = rng_new(11);
    HopfieldTrace trace = { NULL, 0, 0, 100000, 0 };
    int all_converged = 1;
    int all_monotone = 1;
    int all_replayed = 1;
    int all_fixed = 1;
    for (int run = 0; run < 200; run++) {
      double s[25];
      double start[25];
      double h[25];
      int order[25];
      for (int j = 0; j < 25; j++) {
        s[j] = rng_uniform(&rng) < 0.5 ? -1 : 1;
        start[j] = s[j];
        order[j] = j;
      }
      trace.rows = 0;
      HopfieldOutcome out;
      check(hopfield_async_run(w, 25, s, h, order, &rng, 100, &trace, &out));
      all_converged = all_converged && out.converged && out.cycle == 0 && out.energy_increases == 0;

      double replay[25];
      memcpy(replay, start, sizeof(replay));
      for (long long r = 0; r < trace.rows; r++) {
        const double * line = trace.data + r * HOPFIELD_TRACE_WIDTH;
        if (r > 0) {
          const double * before = line - HOPFIELD_TRACE_WIDTH;
          if (line[5] > before[5] + 1e-9) all_monotone = 0;
          if (line[4] == 1 && !(line[5] <= before[5] - 1)) all_monotone = 0;
          if (line[4] == 1) replay[(int) line[3]] = -replay[(int) line[3]];
        }
        if (fabs(hopfield_energy(w, 25, replay) - line[5]) > 1e-9) all_replayed = 0;
      }
      hopfield_fields(w, 25, s, h);
      for (int i = 0; i < 25; i++) all_fixed = all_fixed && (h[i] == 0 || (h[i] > 0) == (s[i] > 0));
    }
    check(all_converged);
    check(all_monotone);
    check(all_replayed);
    check(all_fixed);
    hopfield_trace_free(&trace);
  }

  // (e) the synchronous two-cycle against the asynchronous convergence
  {
    double w2[4] = { 0, -1, -1, 0 };
    double s[2] = { 1, 1 };
    double scratch[4];
    HopfieldOutcome out;
    check(hopfield_sync_run(w2, 2, s, scratch, 100, NULL, &out));
    check(out.cycle == 2 && out.converged == 0 && out.sweeps == 2);
    check(s[0] == 1 && s[1] == 1);

    double a[2] = { 1, 1 };
    double h[2];
    int order[2] = { 0, 1 };
    Rng rng = rng_new(2);
    check(hopfield_async_run(w2, 2, a, h, order, &rng, 100, NULL, &out));
    check(out.converged == 1 && out.cycle == 0);
    check(a[0] == -a[1]);
  }

  // (f) the classifier
  {
    double state[25];
    memcpy(state, rows + 2 * 25, sizeof(state));
    check(hopfield_classify(rows, 4, 25, state, match, sign) == HOPFIELD_STORED);
    check(match[0] == 2 && sign[0] == 1);

    for (int j = 0; j < 25; j++) state[j] = -rows[25 + j];
    check(hopfield_classify(rows, 4, 25, state, match, sign) == HOPFIELD_INVERSE);
    check(match[0] == 1 && sign[0] == -1);

    mixture_of(rows, 25, 0, 2, 3, state);
    check(hopfield_classify(rows, 4, 25, state, match, sign) == HOPFIELD_MIXTURE);
    check(match[0] == 0 && match[1] == 2 && match[2] == 3);
    check(sign[0] == 1 && sign[1] == 1 && sign[2] == 1);
    check(hopfield_classify(rows, 2, 25, state, match, sign) == HOPFIELD_OTHER);

    memcpy(state, rows, sizeof(state));
    for (int j = 0; j < 3; j++) state[j] = -state[j];
    check(hopfield_classify(rows, 4, 25, state, match, sign) == HOPFIELD_OTHER);
    check(match[0] == -1);
  }

  // (g) the stability margin and a synchronous run from a stored pattern
  {
    int wrong = -1;
    check(hopfield_min_margin(w, 25, rows + 25, &wrong) == 2);
    check(wrong == 0);
    double s[25];
    double scratch[50];
    memcpy(s, rows, sizeof(s));
    HopfieldOutcome out;
    check(hopfield_sync_run(w, 25, s, scratch, 100, NULL, &out));
    check(out.converged && out.sweeps == 1 && out.flips == 0);
  }
  matrix_free(&fixture);
}


int main(void) {

  tmp_start();

  struct {
    const char * name;
    void (*run)(void);
  } tests[] = {
    { "config strict validation", test_config_strict_validation },
    { "same seed, same bytes", test_same_seed_same_bytes },
    { "dispatch by model", test_dispatch_by_model },
    { "kohonen training", test_kohonen_training },
    { "hopfield run", test_hopfield_run },
    { "hopfield core", test_hopfield_core },
    { "hopfield capacity", test_hopfield_capacity },
  };
  int n_tests = (int) (sizeof(tests) / sizeof(tests[0]));

  for (int i = 0; i < n_tests; i++) {
    int failures_before = failures;
    tests[i].run();
    printf("%s %s\n", failures == failures_before ? "ok  " : "FAIL", tests[i].name);
  }

  tmp_finish();
  printf("%d checks, %d failed\n", checks, failures);
  return failures == 0 ? 0 : 1;

}
