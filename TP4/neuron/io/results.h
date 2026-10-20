#ifndef __RESULTS_H__
#define __RESULTS_H__

// Every run writes into its own directory, results/<date>_<time>_<model>_seed<N>/:
//   config.json   the config file, byte for byte
//   metrics.json  flat object, one "key": value line per metric, numbers with 17 significant digits
//   <name>.csv    the model's tables: a header line, then %.17g values
// The timestamp lives only in the directory name. No file holds a time value, a duration or an absolute
// path, so two runs with the same config and seed give directories that `diff -r` calls identical.

#define RESULTS_ROOT "results"
#define RESULTS_PATH_MAX 512

typedef struct {
  char dir[RESULTS_PATH_MAX];
} Results;

// One entry of metrics.json: text != NULL means a string value, otherwise number is written
typedef struct {
  const char * key;
  const char * text;
  double number;
} Metric;

// Creates the run directory and copies the config into it.
// Returns 1 on success; on failure prints the reason to stderr and returns 0.
int results_create(const char * config_path, const char * model, unsigned int seed, Results * results);

// Keys and text values may only hold letters, digits, '_', '.' and '-'; a non-finite number is written as null
int results_write_metrics(const Results * results, const Metric metrics[], int n);

// name is the file name (e.g. "weights.csv"); data is n_rows x n_cols, row-major
int results_write_table(const Results * results, const char * name, int n_cols, const char * const header[],
                        int n_rows, const double data[]);

#endif //__RESULTS_H__
