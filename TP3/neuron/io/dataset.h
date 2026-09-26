#ifndef __DATASET_H__
#define __DATASET_H__

// CSV format: one sample per line, inputs first and zeta as the last column.
// An optional header line (non-numeric first field) is skipped, as are blank lines.
// n_inputs is inferred from the column count and must be the same on every row.

typedef struct dataset * Dataset;

// Returns NULL (after printing the reason to stderr) if the file can't be read or is malformed
Dataset dataset_load(const char * path);

void dataset_free(Dataset dataset);

int dataset_n_samples(const Dataset dataset);

int dataset_n_inputs(const Dataset dataset);

// Row-major n_samples x n_inputs matrix, castable to const double (*)[n_inputs]
const double * dataset_inputs(const Dataset dataset);

const double * dataset_zetas(const Dataset dataset);

#endif //__DATASET_H__
