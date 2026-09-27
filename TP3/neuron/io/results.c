#define _POSIX_C_SOURCE 200809L // mkdir, localtime_r

#include "results.h"
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>

#define MAX_DIR_ATTEMPTS 100
#define SUFFIX_MAX 8 // room for "_<attempt>"


static int make_dir(const char * path) {
  if (mkdir(path, 0755) == 0 || errno == EEXIST) return 1;
  perror(path);
  return 0;
}


// Two runs within the same second get a numeric suffix instead of sharing a directory
static int make_run_dir(const char base[RESULTS_PATH_MAX - SUFFIX_MAX], char out[RESULTS_PATH_MAX]) {
  for (int attempt = 1; attempt <= MAX_DIR_ATTEMPTS; attempt++) {
    if (attempt == 1) {
      snprintf(out, RESULTS_PATH_MAX, "%s", base);
    } else {
      snprintf(out, RESULTS_PATH_MAX, "%s_%d", base, attempt);
    }
    if (mkdir(out, 0755) == 0) return 1;
    if (errno != EEXIST) {
      perror(out);
      return 0;
    }
  }
  fprintf(stderr, "%s: too many runs with the same name\n", base);
  return 0;
}


static FILE * open_in_run_dir(const Results * results, const char * name) {
  char path[RESULTS_PATH_MAX + 64];
  snprintf(path, sizeof(path), "%s/%s", results->dir, name);
  FILE * file = fopen(path, "w");
  if (file == NULL) perror(path);
  return file;
}


static int copy_file(const char * source_path, const Results * results, const char * name) {
  FILE * source = fopen(source_path, "r");
  if (source == NULL) {
    perror(source_path);
    return 0;
  }

  FILE * target = open_in_run_dir(results, name);
  if (target == NULL) {
    fclose(source);
    return 0;
  }

  char buffer[4096];
  size_t length;
  while ((length = fread(buffer, 1, sizeof(buffer), source)) > 0) {
    fwrite(buffer, 1, length, target);
  }

  fclose(source);
  return fclose(target) == 0;
}


int results_create(const char * config_path, const char * activation, Results * results) {
  if (!make_dir(RESULTS_ROOT)) return 0;

  time_t now = time(NULL);
  struct tm local;
  localtime_r(&now, &local);
  char timestamp[32];
  strftime(timestamp, sizeof(timestamp), "%Y-%m-%d_%H-%M-%S", &local);

  char base[RESULTS_PATH_MAX - SUFFIX_MAX];
  snprintf(base, sizeof(base), "%s/%s_%s", RESULTS_ROOT, timestamp, activation);

  return make_run_dir(base, results->dir) && copy_file(config_path, results, "config.json");
}


static void write_weight_row(FILE * file, const char * stage, int n_weights, const double weights[]) {
  fprintf(file, "%s", stage);
  for (int i = 0; i < n_weights; i++) {
    fprintf(file, ",%.10g", weights[i]);
  }
  fputc('\n', file);
}


int results_write_weights(const Results * results, int n_weights, const double initial[], const double final[]) {
  FILE * file = open_in_run_dir(results, "weights.csv");
  if (file == NULL) return 0;

  fprintf(file, "stage");
  for (int i = 0; i < n_weights; i++) {
    fprintf(file, ",w%d", i);
  }
  fputc('\n', file);

  write_weight_row(file, "initial", n_weights, initial);
  write_weight_row(file, "final", n_weights, final);

  return fclose(file) == 0;
}


int results_write_predictions(const Results * results, int n_inputs, const double inputs[][n_inputs],
                              const double zetas[], const double predictions[], int n_samples) {
  FILE * file = open_in_run_dir(results, "predictions.csv");
  if (file == NULL) return 0;

  for (int j = 0; j < n_inputs; j++) {
    fprintf(file, "x%d,", j + 1);
  }
  fprintf(file, "zeta,prediction\n");

  for (int i = 0; i < n_samples; i++) {
    for (int j = 0; j < n_inputs; j++) {
      fprintf(file, "%.10g,", inputs[i][j]);
    }
    fprintf(file, "%.10g,%.10g\n", zetas[i], predictions[i]);
  }

  return fclose(file) == 0;
}
