#ifndef __CONFIG_H__
#define __CONFIG_H__

// A run is described by one JSON file. The three keys every model shares:
//   model   which runner to use (oja here; kohonen and hopfield come with plan 01-05)
//   seed    integer >= 0, seeds the run's single Rng
//   input   numeric CSV with a header row, relative to the directory the binary runs from
// Nothing falls back to a silent default: a missing key aborts the run.

#include "../vendor/cjson/cJSON.h"

#define CONFIG_STRING_MAX 512
#define CONFIG_MODEL_MAX 32
#define CONFIG_FILE_MAX 1048576 // a config larger than 1 MiB is not a config

typedef struct {
  char path[CONFIG_STRING_MAX];
  char model[CONFIG_MODEL_MAX];
  unsigned int seed;
  char input[CONFIG_STRING_MAX];
  cJSON * json; // the whole document, owned; config_free releases it
} Config;

// Returns 1 on success; on failure prints "<path>: <reason>" to stderr and returns 0.
int config_load(const char * path, Config * config);

void config_free(Config * config);

#endif //__CONFIG_H__
