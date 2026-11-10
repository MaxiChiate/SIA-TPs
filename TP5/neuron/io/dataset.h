#ifndef __DATASET_H__
#define __DATASET_H__

#include "../rng.h"

// CSV format: one sample per line, inputs first and the zetas (expected outputs) last.
// An optional header line (any non-numeric field) is skipped, as are blank lines.
// The header's trailing columns named zeta* (zeta_0, zeta_1, ...) are the zetas, one per output
// neuron; without a header, or without zeta* names, only the last column is. n_inputs is the rest,
// and every row must have the same column count.

typedef struct dataset * Dataset;

// Returns NULL (after printing the reason to stderr) if the file can't be read or is malformed
Dataset dataset_load(const char * path);

void dataset_free(Dataset dataset);

// Splits source in two, at random: a validation_fraction share of the samples (rounded, at least one,
// leaving at least one for train) goes to validation, the rest to train. Which sample goes where depends
// only on rng; each side keeps the order the samples had in source. source is left untouched, the caller
// frees all three. Returns 1 on success; if source has fewer than 2 samples or validation_fraction is
// outside (0, 1), prints the reason to stderr and returns 0.
int dataset_split(const Dataset source, double validation_fraction, Rng * rng, Dataset * train, Dataset * validation);

int dataset_n_samples(const Dataset dataset);

int dataset_n_inputs(const Dataset dataset);

// Row-major n_samples x n_inputs matrix, castable to const double (*)[n_inputs]
const double * dataset_inputs(const Dataset dataset);

int dataset_n_outputs(const Dataset dataset);

// Row-major n_samples x n_outputs matrix
const double * dataset_zetas(const Dataset dataset);

#endif //__DATASET_H__
