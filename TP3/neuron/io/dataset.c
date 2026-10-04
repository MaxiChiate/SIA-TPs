#define _POSIX_C_SOURCE 200809L // getline

#include "dataset.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define INITIAL_CAPACITY 64
#define ZETA_PREFIX "zeta"

struct dataset {
  int n_samples;
  int n_inputs;
  int n_outputs;
  double * inputs; // n_samples * n_inputs, row-major
  double * zetas;  // n_samples * n_outputs, row-major
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


static int is_zeta_name(const char * name) {
  name += strspn(name, " \t\"");
  return strncmp(name, ZETA_PREFIX, strlen(ZETA_PREFIX)) == 0;
}


// Trailing header columns named zeta*: one per output neuron
static int count_zeta_columns(const char * header, int columns) {
  const char * names[columns];
  names[0] = header;
  for (int i = 1; i < columns; i++) {
    names[i] = strchr(names[i-1], ',') + 1;
  }
  int count = 0;
  while (count < columns && is_zeta_name(names[columns - 1 - count])) count++;
  return count;
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
  dataset->n_outputs = 1;
  dataset->inputs = NULL;
  dataset->zetas = NULL;

  int capacity = 0;
  double * row = NULL;
  int columns = 0;
  char * line = NULL;
  size_t line_size = 0;
  int line_number = 0;
  int ok = 1;

  while (ok && getline(&line, &line_size, file) != -1) {
    line_number++;
    if (is_blank(line)) continue;

    if (dataset->n_inputs == -1) {
      columns = count_columns(line);
      row = checked_realloc(NULL, columns * sizeof(double));
      int is_header = !parse_row(line, row, columns);
      if (is_header) {
        int zeta_columns = count_zeta_columns(line, columns);
        if (zeta_columns > 0) dataset->n_outputs = zeta_columns;
      }
      dataset->n_inputs = columns - dataset->n_outputs;
      if (dataset->n_inputs < 1) {
        fprintf(stderr, "%s:%d: expected at least one input column before the zeta columns\n", path, line_number);
        ok = 0;
        break;
      }
      if (is_header) continue;
    } else if (count_columns(line) != columns || !parse_row(line, row, columns)) {
      fprintf(stderr, "%s:%d: expected %d numeric columns\n", path, line_number, columns);
      ok = 0;
      break;
    }

    if (dataset->n_samples == capacity) {
      capacity = capacity == 0 ? INITIAL_CAPACITY : capacity * 2;
      dataset->inputs = checked_realloc(dataset->inputs, (size_t) capacity * dataset->n_inputs * sizeof(double));
      dataset->zetas = checked_realloc(dataset->zetas, (size_t) capacity * dataset->n_outputs * sizeof(double));
    }

    memcpy(&dataset->inputs[dataset->n_samples * dataset->n_inputs], row, dataset->n_inputs * sizeof(double));
    memcpy(&dataset->zetas[dataset->n_samples * dataset->n_outputs], &row[dataset->n_inputs],
           dataset->n_outputs * sizeof(double));
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


static Dataset new_dataset(int n_samples, int n_inputs, int n_outputs) {
  Dataset dataset = checked_realloc(NULL, sizeof(struct dataset));
  dataset->n_samples = n_samples;
  dataset->n_inputs = n_inputs;
  dataset->n_outputs = n_outputs;
  dataset->inputs = checked_realloc(NULL, (size_t) n_samples * n_inputs * sizeof(double));
  dataset->zetas = checked_realloc(NULL, (size_t) n_samples * n_outputs * sizeof(double));
  return dataset;
}


static void copy_sample(Dataset to, int to_index, const Dataset from, int from_index) {
  memcpy(&to->inputs[to_index * to->n_inputs], &from->inputs[from_index * from->n_inputs],
         from->n_inputs * sizeof(double));
  memcpy(&to->zetas[to_index * to->n_outputs], &from->zetas[from_index * from->n_outputs],
         from->n_outputs * sizeof(double));
}


int dataset_split(const Dataset source, double validation_fraction, Rng * rng, Dataset * train, Dataset * validation) {
  int n = source->n_samples;
  if (n < 2) {
    fprintf(stderr, "can't split a dataset of %d sample(s)\n", n);
    return 0;
  }
  if (!(validation_fraction > 0 && validation_fraction < 1)) {
    fprintf(stderr, "validation fraction %g must be in (0, 1)\n", validation_fraction);
    return 0;
  }

  int n_validation = (int) (validation_fraction * n + 0.5);
  if (n_validation < 1) n_validation = 1;
  if (n_validation > n - 1) n_validation = n - 1;

  // The first n_validation entries of a shuffled 0..n-1 are the validation samples
  int * order = checked_realloc(NULL, n * sizeof(int));
  char * is_validation = checked_realloc(NULL, n);
  for (int i = 0; i < n; i++) {
    order[i] = i;
    is_validation[i] = 0;
  }
  rng_shuffle(rng, order, n);
  for (int i = 0; i < n_validation; i++) is_validation[order[i]] = 1;

  *train = new_dataset(n - n_validation, source->n_inputs, source->n_outputs);
  *validation = new_dataset(n_validation, source->n_inputs, source->n_outputs);
  int next_train = 0, next_validation = 0;
  for (int i = 0; i < n; i++) {
    if (is_validation[i]) copy_sample(*validation, next_validation++, source, i);
    else copy_sample(*train, next_train++, source, i);
  }

  free(order);
  free(is_validation);
  return 1;
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


int dataset_n_outputs(const Dataset dataset) {
  return dataset->n_outputs;
}


const double * dataset_inputs(const Dataset dataset) {
  return dataset->inputs;
}


const double * dataset_zetas(const Dataset dataset) {
  return dataset->zetas;
}
