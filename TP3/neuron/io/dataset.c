#define _POSIX_C_SOURCE 200809L // getline

#include "dataset.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define INITIAL_CAPACITY 64

struct dataset {
  int n_samples;
  int n_inputs;
  double * inputs; // n_samples * n_inputs, row-major
  double * zetas;  // n_samples
};


static void * checked_realloc(void * ptr, size_t size) {
  void * new_ptr = realloc(ptr, size);
  if (new_ptr == NULL) {
    fprintf(stderr, "FATAL: couldn't allocate dataset\n");
    abort();
  }
  return new_ptr;
}


static int count_columns(const char * line) {
  int columns = 1;
  for (const char * c = line; *c != '\0'; c++) {
    if (*c == ',') columns++;
  }
  return columns;
}


static int is_blank(const char * line) {
  return line[strspn(line, " \t\r\n")] == '\0';
}


// Parses exactly n_values comma-separated numbers into out. Returns 1 on success, 0 otherwise.
static int parse_row(const char * line, double out[], int n_values) {
  const char * cursor = line;
  for (int i = 0; i < n_values; i++) {
    char * end;
    out[i] = strtod(cursor, &end);
    if (end == cursor) return 0;
    end += strspn(end, " \t");
    if (i < n_values - 1) {
      if (*end != ',') return 0;
      cursor = end + 1;
    } else if (!is_blank(end)) {
      return 0;
    }
  }
  return 1;
}


Dataset dataset_load(const char * path) {

  FILE * file = fopen(path, "r");
  if (file == NULL) {
    perror(path);
    return NULL;
  }

  Dataset dataset = checked_realloc(NULL, sizeof(struct dataset));
  dataset->n_samples = 0;
  dataset->n_inputs = -1;
  dataset->inputs = NULL;
  dataset->zetas = NULL;

  int capacity = 0;
  double * row = NULL;
  char * line = NULL;
  size_t line_size = 0;
  int line_number = 0;
  int ok = 1;

  while (ok && getline(&line, &line_size, file) != -1) {
    line_number++;
    if (is_blank(line)) continue;

    int columns = count_columns(line);

    if (dataset->n_inputs == -1) {
      if (columns < 2) {
        fprintf(stderr, "%s:%d: expected at least 2 columns (inputs and zeta)\n", path, line_number);
        ok = 0;
        break;
      }
      dataset->n_inputs = columns - 1;
      row = checked_realloc(NULL, columns * sizeof(double));
      if (!parse_row(line, row, columns)) continue; // header
    } else if (columns != dataset->n_inputs + 1 || !parse_row(line, row, columns)) {
      fprintf(stderr, "%s:%d: expected %d numeric columns\n", path, line_number, dataset->n_inputs + 1);
      ok = 0;
      break;
    }

    if (dataset->n_samples == capacity) {
      capacity = capacity == 0 ? INITIAL_CAPACITY : capacity * 2;
      dataset->inputs = checked_realloc(dataset->inputs, (size_t) capacity * dataset->n_inputs * sizeof(double));
      dataset->zetas = checked_realloc(dataset->zetas, capacity * sizeof(double));
    }

    memcpy(&dataset->inputs[dataset->n_samples * dataset->n_inputs], row, dataset->n_inputs * sizeof(double));
    dataset->zetas[dataset->n_samples] = row[dataset->n_inputs];
    dataset->n_samples++;
  }

  free(line);
  free(row);
  fclose(file);

  if (ok && dataset->n_samples == 0) {
    fprintf(stderr, "%s: no samples found\n", path);
    ok = 0;
  }

  if (!ok) {
    dataset_free(dataset);
    return NULL;
  }

  return dataset;
}


void dataset_free(Dataset dataset) {
  if (dataset == NULL) return;
  free(dataset->inputs);
  free(dataset->zetas);
  free(dataset);
}


int dataset_n_samples(const Dataset dataset) {
  return dataset->n_samples;
}


int dataset_n_inputs(const Dataset dataset) {
  return dataset->n_inputs;
}


const double * dataset_inputs(const Dataset dataset) {
  return dataset->inputs;
}


const double * dataset_zetas(const Dataset dataset) {
  return dataset->zetas;
}
