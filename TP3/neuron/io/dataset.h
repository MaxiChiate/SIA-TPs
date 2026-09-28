#ifndef __DATASET_H__
#define __DATASET_H__

// CSV format: one sample per line, inputs first and the zetas (expected outputs) last.
// An optional header line (any non-numeric field) is skipped, as are blank lines.
// The header's trailing columns named zeta* (zeta_0, zeta_1, ...) are the zetas, one per output
// neuron; without a header, or without zeta* names, only the last column is. n_inputs is the rest,
// and every row must have the same column count.

typedef struct dataset * Dataset;

// Returns NULL (after printing the reason to stderr) if the file can't be read or is malformed
Dataset dataset_load(const char * path);

void dataset_free(Dataset dataset);

int dataset_n_samples(const Dataset dataset);

int dataset_n_inputs(const Dataset dataset);

// Row-major n_samples x n_inputs matrix, castable to const double (*)[n_inputs]
const double * dataset_inputs(const Dataset dataset);

int dataset_n_outputs(const Dataset dataset);

// Row-major n_samples x n_outputs matrix
const double * dataset_zetas(const Dataset dataset);

#endif //__DATASET_H__
