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


int results_write_weights(const Results * results, int n_layers, const int sizes[], const double initial[],
                          const double final[]) {
  FILE * file = open_in_run_dir(results, "weights.csv");
  if (file == NULL) return 0;

  fprintf(file, "layer,neuron,weight,initial,final\n");

  int index = 0;
  for (int l = 1; l <= n_layers; l++) {
    for (int j = 0; j < sizes[l]; j++) {
      for (int w = 0; w <= sizes[l-1]; w++, index++) {
        // 17 significant digits: reading them back gives the same doubles, so epochs 0 evaluates the same network
        fprintf(file, "%d,%d,%d,%.17g,%.17g\n", l, j + 1, w, initial[index], final[index]);
      }
    }
  }

  return fclose(file) == 0;
}


#define WEIGHTS_HEADER "layer,neuron,weight,initial,final"
#define WEIGHTS_LINE_MAX 256


static FILE * open_weights(const char * path, char resolved[RESULTS_PATH_MAX + 64]) {
  struct stat info;
  if (stat(path, &info) == 0 && S_ISDIR(info.st_mode)) {
    snprintf(resolved, RESULTS_PATH_MAX + 64, "%s/weights.csv", path);
  } else {
    snprintf(resolved, RESULTS_PATH_MAX + 64, "%s", path);
  }
  FILE * file = fopen(resolved, "r");
  if (file == NULL) perror(resolved);
  return file;
}


static int read_weight_rows(FILE * file, const char * path, int n_layers, const int sizes[], double out[]) {
  char line[WEIGHTS_LINE_MAX];
  if (fgets(line, sizeof(line), file) == NULL || strncmp(line, WEIGHTS_HEADER, strlen(WEIGHTS_HEADER)) != 0) {
    fprintf(stderr, "%s: expected the header \"%s\"\n", path, WEIGHTS_HEADER);
    return 0;
  }

  int index = 0;
  for (int l = 1; l <= n_layers; l++) {
    for (int j = 1; j <= sizes[l]; j++) {
      for (int w = 0; w <= sizes[l-1]; w++, index++) {
        int layer, neuron, weight;
        double initial;
        if (fgets(line, sizeof(line), file) == NULL
            || sscanf(line, "%d,%d,%d,%lf,%lf", &layer, &neuron, &weight, &initial, &out[index]) != 5) {
          fprintf(stderr, "%s: row %d isn't layer %d, neuron %d, weight %d; does the architecture match?\n",
                  path, index + 2, l, j, w);
          return 0;
        }
        if (layer != l || neuron != j || weight != w) {
          fprintf(stderr, "%s: row %d is layer %d, neuron %d, weight %d, expected %d, %d, %d; "
                          "does the architecture match?\n", path, index + 2, layer, neuron, weight, l, j, w);
          return 0;
        }
      }
    }
  }

  if (fgets(line, sizeof(line), file) != NULL) {
    fprintf(stderr, "%s: more weights than the network has; does the architecture match?\n", path);
    return 0;
  }
  return 1;
}


int results_read_weights(const char * path, int n_layers, const int sizes[], double out[]) {
  char resolved[RESULTS_PATH_MAX + 64];
  FILE * file = open_weights(path, resolved);
  if (file == NULL) return 0;
  int ok = read_weight_rows(file, resolved, n_layers, sizes, out);
  fclose(file);
  return ok;
}


// "name" with a single output, "name_0", "name_1", ... with several (0-based, like the dataset's zeta_k)
static void write_output_names(FILE * file, const char * name, int n_outputs) {
  for (int j = 0; j < n_outputs; j++) {
    if (n_outputs == 1) {
      fprintf(file, "%s", name);
    } else {
      fprintf(file, "%s_%d", name, j);
    }
    if (j < n_outputs - 1) fputc(',', file);
  }
}


static void write_values(FILE * file, const double values[], int n_values) {
  for (int j = 0; j < n_values; j++) {
    fprintf(file, ",%.10g", values[j]);
  }
}


int results_write_predictions(const Results * results, int n_inputs, int n_outputs, const double inputs[][n_inputs],
                              const double zetas[], const double predictions[], int n_samples) {
  FILE * file = open_in_run_dir(results, "predictions.csv");
  if (file == NULL) return 0;

  for (int j = 0; j < n_inputs; j++) {
    fprintf(file, "x%d,", j + 1);
  }
  write_output_names(file, "zeta", n_outputs);
  fputc(',', file);
  write_output_names(file, "prediction", n_outputs);
  fputc('\n', file);

  for (int i = 0; i < n_samples; i++) {
    fprintf(file, "%.10g", inputs[i][0]);
    write_values(file, &inputs[i][1], n_inputs - 1);
    write_values(file, &zetas[i * n_outputs], n_outputs);
    write_values(file, &predictions[i * n_outputs], n_outputs);
    fputc('\n', file);
  }

  return fclose(file) == 0;
}


static void write_metrics(FILE * file, const ErrorMetrics * metrics) {
  fprintf(file, ",%.10g,%.10g,%.10g,%.10g", metrics->energy, metrics->mse, metrics->mae, metrics->max_abs_error);
}


int results_write_epochs(const Results * results, int n_epochs, const ErrorMetrics train[],
                         const ErrorMetrics validation[], const double elapsed[], const double eta[]) {
  FILE * file = open_in_run_dir(results, "epochs.csv");
  if (file == NULL) return 0;

  fprintf(file, "epoch,train_error,train_mse,train_mae,train_max_error,"
                "validation_error,validation_mse,validation_mae,validation_max_error,elapsed_s,eta\n");
  for (int epoch = 0; epoch <= n_epochs; epoch++) {
    fprintf(file, "%d", epoch);
    write_metrics(file, &train[epoch]);
    write_metrics(file, &validation[epoch]);
    fprintf(file, ",%.6f,%.10g\n", elapsed[epoch], eta[epoch]);
  }

  return fclose(file) == 0;
}


int results_write_snapshots(const Results * results, int n_snapshots, const int epochs[], int n_samples,
                            int n_outputs, const double zetas[], const double predictions[]) {
  FILE * file = open_in_run_dir(results, "predictions_by_epoch.csv");
  if (file == NULL) return 0;

  write_output_names(file, "zeta", n_outputs);
  for (int k = 0; k < n_snapshots; k++) {
    char name[32];
    snprintf(name, sizeof(name), "epoch_%d", epochs[k]);
    fputc(',', file);
    write_output_names(file, name, n_outputs);
  }
  fputc('\n', file);

  for (int i = 0; i < n_samples; i++) {
    fprintf(file, "%.10g", zetas[i * n_outputs]);
    write_values(file, &zetas[i * n_outputs + 1], n_outputs - 1);
    for (int k = 0; k < n_snapshots; k++) {
      write_values(file, &predictions[(k * n_samples + i) * n_outputs], n_outputs);
    }
    fputc('\n', file);
  }

  return fclose(file) == 0;
}
