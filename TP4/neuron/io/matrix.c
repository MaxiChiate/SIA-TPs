#define _POSIX_C_SOURCE 200809L // getline

#include "matrix.h"
#include <ctype.h>
#include <limits.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>


static int is_blank(const char * line) {
  for (; *line != '\0'; line++) {
    if (!isspace((unsigned char) *line)) return 0;
  }
  return 1;
}


// Strips trailing CR/LF in place
static void chomp(char * line) {
  size_t length = strlen(line);
  while (length > 0 && (line[length - 1] == '\n' || line[length - 1] == '\r')) line[--length] = '\0';
}


static int count_fields(const char * line) {
  int n = 1;
  for (; *line != '\0'; line++) {
    if (*line == ',') n++;
  }
  return n;
}


// Copy of text[0..length) without the surrounding spaces; NULL on allocation failure
static char * trimmed_copy(const char * text, size_t length) {
  while (length > 0 && isspace((unsigned char) *text)) {
    text++;
    length--;
  }
  while (length > 0 && isspace((unsigned char) text[length - 1])) length--;

  char * copy = malloc(length + 1);
  if (copy == NULL) return NULL;
  memcpy(copy, text, length);
  copy[length] = '\0';
  return copy;
}


static int parse_header(const char * path, int line_number, const char * line, Matrix * matrix) {
  matrix->n_cols = count_fields(line);
  matrix->names = calloc(matrix->n_cols, sizeof(char *));
  if (matrix->names == NULL) {
    fprintf(stderr, "%s:%d: couldn't allocate the header\n", path, line_number);
    return 0;
  }

  const char * start = line;
  for (int j = 0; j < matrix->n_cols; j++) {
    const char * end = strchr(start, ',');
    if (end == NULL) end = start + strlen(start);
    matrix->names[j] = trimmed_copy(start, (size_t) (end - start));
    if (matrix->names[j] == NULL) {
      fprintf(stderr, "%s:%d: couldn't allocate the header\n", path, line_number);
      return 0;
    }
    if (matrix->names[j][0] == '\0') {
      fprintf(stderr, "%s:%d: empty column name at position %d\n", path, line_number, j + 1);
      return 0;
    }
    start = end + 1;
  }
  return 1;
}


// Exactly n_cols finite numbers separated by commas
static int parse_row(const char * path, int line_number, const char * line, int n_cols, double row[]) {
  const char * cursor = line;
  for (int j = 0; j < n_cols; j++) {
    char * end;
    row[j] = strtod(cursor, &end);
    int separator_ok = j < n_cols - 1 ? *end == ',' : *end == '\0';
    if (end == cursor || !separator_ok || !isfinite(row[j])) {
      fprintf(stderr, "%s:%d: expected %d numeric columns\n", path, line_number, n_cols);
      return 0;
    }
    cursor = end + 1;
  }
  return 1;
}


// Room for one more row, doubling the capacity; 0 after printing the reason
static int grow(const char * path, Matrix * matrix, int * capacity) {
  if (matrix->n_rows < *capacity) return 1;

  if (*capacity > INT_MAX / 2) {
    fprintf(stderr, "%s: too many rows\n", path);
    return 0;
  }
  int new_capacity = *capacity == 0 ? 64 : *capacity * 2;
  if ((size_t) new_capacity > SIZE_MAX / sizeof(double) / (size_t) matrix->n_cols) {
    fprintf(stderr, "%s: the matrix is too large\n", path);
    return 0;
  }
  double * data = realloc(matrix->data, (size_t) new_capacity * matrix->n_cols * sizeof(double));
  if (data == NULL) {
    fprintf(stderr, "%s: couldn't allocate the matrix\n", path);
    return 0;
  }
  matrix->data = data;
  *capacity = new_capacity;
  return 1;
}


// The rows are counted by parsing them, so a last line without a newline still counts
static int read_rows(const char * path, FILE * file, Matrix * matrix) {
  char * line = NULL;
  size_t line_size = 0;
  int line_number = 0;
  int capacity = 0;
  int header_read = 0;
  int ok = 1;

  while (ok && getline(&line, &line_size, file) != -1) {
    line_number++;
    chomp(line);
    if (is_blank(line)) continue;

    if (!header_read) {
      ok = parse_header(path, line_number, line, matrix);
      header_read = 1;
    } else {
      ok = grow(path, matrix, &capacity)
        && parse_row(path, line_number, line, matrix->n_cols, &matrix->data[(size_t) matrix->n_rows * matrix->n_cols]);
      if (ok) matrix->n_rows++;
    }
  }
  free(line);

  if (ok && matrix->n_rows == 0) {
    fprintf(stderr, "%s: no data rows\n", path);
    ok = 0;
  }
  return ok;
}


int matrix_load(const char * path, Matrix * out) {
  *out = (Matrix) { 0 };
  FILE * file = fopen(path, "r");
  if (file == NULL) {
    perror(path);
    return 0;
  }

  int ok = read_rows(path, file, out);
  fclose(file);
  if (!ok) matrix_free(out);
  return ok;
}


void matrix_free(Matrix * matrix) {
  if (matrix->names != NULL) {
    for (int j = 0; j < matrix->n_cols; j++) free(matrix->names[j]);
  }
  free(matrix->names);
  free(matrix->data);
  *matrix = (Matrix) { 0 };
}
