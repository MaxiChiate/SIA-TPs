#ifndef __CONFIG_H__
#define __CONFIG_H__

// A run is described by one JSON file. The three keys every model shares:
//   model   which runner to use (oja here; kohonen and hopfield come with plan 01-05)
//   seed    integer >= 0, seeds the run's single Rng
//   input   numeric CSV with a header row, relative to the directory the binary runs from
// Each model adds its own keys. Both sets are tables of KeySpec rows: a key that is not in the table, appears
// twice, is missing or has the wrong type aborts the run before anything runs. Nothing falls back to a
// silent default. A new key in a later phase is one more row in the model's table in config.c.

#include "../vendor/cjson/cJSON.h"

#define CONFIG_STRING_MAX 512
#define CONFIG_MODEL_MAX 32
#define CONFIG_FILE_MAX 1048576 // a config larger than 1 MiB is not a config
#define CONFIG_ARRAY_MAX 64     // most items of a number array
#define CONFIG_KEYS_MAX 32      // most rows of the table a config is validated against

typedef enum {
  KEY_INT,          // a JSON number with no fractional part, inside int range
  KEY_NUMBER,       // any finite JSON number
  KEY_BOOL,
  KEY_STRING,
  KEY_OBJECT,       // validated recursively against children
  KEY_NUMBER_ARRAY, // non-empty array of at most CONFIG_ARRAY_MAX finite numbers
} KeyType;

// A table is an array of rows ending with a row whose name is NULL
typedef struct KeySpec {
  const char * name;
  KeyType type;
  int required;
  const struct KeySpec * children; // KEY_OBJECT only
} KeySpec;

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

// Checks the keys of object against keys. where is the prefix of nested keys in messages ("" at the top,
// "grid." inside "grid"). Returns 1 if they all fit; otherwise prints the first problem and returns 0.
int config_validate_object(const char * path, const cJSON * object, const KeySpec keys[], const char * where);

// The table of a model's own keys (the common ones are separate); NULL for an unknown model
const KeySpec * config_model_keys(const char * model);

// Typed getters for the models. key may be dotted ("grid.rows") to reach nested objects. On a missing item
// or the wrong type they print "<path>: ..." and return 0.
int config_get_int(const Config * config, const char * key, int * out);
int config_get_number(const Config * config, const char * key, double * out);
int config_get_string(const Config * config, const char * key, const char ** out); // valid until config_free
int config_get_number_array(const Config * config, const char * key, double out[], int max, int * count);

#endif //__CONFIG_H__
