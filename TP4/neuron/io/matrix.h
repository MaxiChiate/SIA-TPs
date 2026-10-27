#ifndef __MATRIX_H__
#define __MATRIX_H__

// A numeric CSV with a header row: the z-scored creators and the +-1 Hopfield patterns alike.
// Python prepares it; C only reads it, it never selects, scales or drops columns.

typedef struct {
  int n_rows;
  int n_cols;
  char ** names;  // n_cols column names from the header
  double * data;  // n_rows x n_cols, row-major
} Matrix;

// Returns 1 on success. On failure prints "<path>:<line>: <reason>" to stderr and returns 0; out is left
// empty (safe to pass to matrix_free).
int matrix_load(const char * path, Matrix * out);

void matrix_free(Matrix * matrix);

#endif //__MATRIX_H__
