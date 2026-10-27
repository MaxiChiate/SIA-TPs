#define _POSIX_C_SOURCE 200809L // mkdir, localtime_r

#include "results.h"
#include <ctype.h>
#include <errno.h>
#include <math.h>
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
  int length = snprintf(path, sizeof(path), "%s/%s", results->dir, name);
  if (length < 0 || (size_t) length >= sizeof(path)) {
    fprintf(stderr, "%s/%s: the path is too long\n", results->dir, name);
    return NULL;
  }
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
  int ok = 1;
  while (ok && (length = fread(buffer, 1, sizeof(buffer), source)) > 0) {
    ok = fwrite(buffer, 1, length, target) == length;
  }
  ok = ok && !ferror(source);

  fclose(source);
  return fclose(target) == 0 && ok;
}


// Letters, digits, '_', '.' and '-': nothing that needs JSON escaping or could climb out of a directory name
static int is_plain(const char * text) {
  if (text[0] == '\0') return 0;
  for (; *text != '\0'; text++) {
    unsigned char c = (unsigned char) *text;
    if (!isalnum(c) && c != '_' && c != '.' && c != '-') return 0;
  }
  return 1;
}


int results_create(const char * config_path, const char * model, unsigned int seed, Results * results) {
  if (!is_plain(model) || model[0] == '.') {
    fprintf(stderr, "%s: not a valid model name for a run directory\n", model);
    return 0;
  }
  if (!make_dir(RESULTS_ROOT)) return 0;

  time_t now = time(NULL);
  struct tm local;
  localtime_r(&now, &local);
  char timestamp[32];
  strftime(timestamp, sizeof(timestamp), "%Y-%m-%d_%H-%M-%S", &local);

  char base[RESULTS_PATH_MAX - SUFFIX_MAX];
  int length = snprintf(base, sizeof(base), "%s/%s_%s_seed%u", RESULTS_ROOT, timestamp, model, seed);
  if (length < 0 || (size_t) length >= sizeof(base)) {
    fprintf(stderr, "%s: the run directory name is too long\n", model);
    return 0;
  }

  return make_run_dir(base, results->dir) && copy_file(config_path, results, "config.json");
}


// %.17g reads back as the same double; a value that is not a number has no JSON form, so it becomes null
static void print_number(FILE * file, double value) {
  if (isfinite(value)) {
    fprintf(file, "%.17g", value);
  } else {
    fputs("null", file);
  }
}


int results_write_metrics(const Results * results, const Metric metrics[], int n) {
  for (int i = 0; i < n; i++) {
    if (!is_plain(metrics[i].key) || (metrics[i].text != NULL && !is_plain(metrics[i].text))) {
      fprintf(stderr, "metrics.json: key or value #%d holds characters outside letters, digits, _ . -\n", i);
      return 0;
    }
  }

  FILE * file = open_in_run_dir(results, "metrics.json");
  if (file == NULL) return 0;

  fputs("{\n", file);
  for (int i = 0; i < n; i++) {
    fprintf(file, "  \"%s\": ", metrics[i].key);
    if (metrics[i].text != NULL) {
      fprintf(file, "\"%s\"", metrics[i].text);
    } else {
      print_number(file, metrics[i].number);
    }
    fputs(i < n - 1 ? ",\n" : "\n", file);
  }
  fputs("}\n", file);

  return fclose(file) == 0;
}


int results_write_table(const Results * results, const char * name, int n_cols, const char * const header[],
                        int n_rows, const double data[]) {
  FILE * file = open_in_run_dir(results, name);
  if (file == NULL) return 0;

  for (int j = 0; j < n_cols; j++) {
    fprintf(file, j == 0 ? "%s" : ",%s", header[j]);
  }
  fputc('\n', file);

  for (int i = 0; i < n_rows; i++) {
    for (int j = 0; j < n_cols; j++) {
      if (j > 0) fputc(',', file);
      fprintf(file, "%.17g", data[(size_t) i * n_cols + j]);
    }
    fputc('\n', file);
  }

  return fclose(file) == 0;
}
