#define _POSIX_C_SOURCE 200809L // mkdir, opendir, dup2

// Dependency-free tests: `make test-c`. Each test_* function reports through check(); the exit code is
// nonzero if any check failed. Run from neuron/ (the fixtures are read as tests/fixtures/...). Everything the
// tests write goes under TMP_DIR and is removed at the end.

#include "../io/config.h"
#include "../io/matrix.h"
#include "../io/results.h"
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
  check(loads("{\"model\": \"hopfield\", \"seed\": 1, \"input\": \"" PATTERNS_FIXTURE "\", "
              "\"noise_levels\": [0.0, 0.5]}"));

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
  // The stub flips a number of pixels fixed by the level, so its CSVs hold no trace of the seed: only the
  // identical-bytes check applies. The Hopfield phases add a file that does depend on it.
  same_seed_same_bytes("hopfield",
                       "{\"model\": \"hopfield\", \"seed\": 5, \"input\": \"" PATTERNS_FIXTURE "\", "
                       "\"noise_levels\": [0.0, 0.5]}",
                       NULL);

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
