#include "config.h"
#include <limits.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXCERPT_MAX 40


// Keys of every model
static const KeySpec COMMON_KEYS[] = {
  { "model", KEY_STRING, 1, NULL },
  { "seed",  KEY_INT,    1, NULL },
  { "input", KEY_STRING, 1, NULL },
  { NULL, KEY_INT, 0, NULL },
};

// grid_k: side of the k x k grid of neurons (D-07). neighborhood: "step" updates every neuron within grid distance R
// of the winner, "gaussian" weights them by exp(-d^2 / 2 sigma^2) (D-01). radius0, radius_final: R (or sigma) at the
// first and the last step, decaying exponentially. eta0, eta_final: learning rate at the first and the last step
// (D-02). epochs: passes over the shuffled samples (D-03). The ranges are checked in models/kohonen.c.
static const KeySpec KOHONEN_KEYS[] = {
  { "grid_k", KEY_INT, 1, NULL },
  { "neighborhood", KEY_STRING, 1, NULL },
  { "radius0", KEY_NUMBER, 1, NULL },
  { "radius_final", KEY_NUMBER, 1, NULL },
  { "eta0", KEY_NUMBER, 1, NULL },
  { "eta_final", KEY_NUMBER, 1, NULL },
  { "epochs", KEY_INT, 1, NULL },
  { NULL, KEY_INT, 0, NULL },
};

// The stub reads nothing else; Phase 3 appends the rows of the real Oja rule here
static const KeySpec OJA_KEYS[] = {
  { NULL, KEY_INT, 0, NULL },
};

// task: what the run does; "recall" runs noisy queries of the stored patterns. rule: the learning rule; "hebb". update:
// "async" = one neuron at a time in a fresh random order per sweep, the reference; "sync" = every neuron at once, the
// course's comparison. max_sweeps: cap on sweeps or sync steps. trials: queries per stored pattern and noise level.
// noise_levels: fractions of pixels flipped, each in [0, 1]. subset: recall, the rows of the input that are stored,
// distinct row indices. trace_trials: recall, trials per pattern and level whose per-step trace and states are
// written. p: capacity, patterns stored per subset. n_subsets: capacity, 0 = every p-subset of the input in
// lexicographic order, otherwise that many distinct random subsets. The ranges are checked in models/hopfield.c.
static const KeySpec HOPFIELD_KEYS[] = {
  { "task", KEY_STRING, 1, NULL },
  { "rule", KEY_STRING, 1, NULL },
  { "update", KEY_STRING, 1, NULL },
  { "max_sweeps", KEY_INT, 1, NULL },
  { "trials", KEY_INT, 1, NULL },
  { "noise_levels", KEY_NUMBER_ARRAY, 1, NULL },
  { "subset", KEY_NUMBER_ARRAY, 0, NULL },
  { "trace_trials", KEY_INT, 0, NULL },
  { "p", KEY_INT, 0, NULL },
  { "n_subsets", KEY_INT, 0, NULL },
  { NULL, KEY_INT, 0, NULL },
};

typedef struct {
  const char * name;
  const KeySpec * keys;
} ModelKeys;

// Same names, in the same order, as the runner table in models/models.c
static const ModelKeys MODEL_KEYS[] = {
  { "kohonen", KOHONEN_KEYS },
  { "oja", OJA_KEYS },
  { "hopfield", HOPFIELD_KEYS },
};

#define N_MODEL_KEYS ((int) (sizeof(MODEL_KEYS) / sizeof(MODEL_KEYS[0])))


const KeySpec * config_model_keys(const char * model) {
  for (int i = 0; i < N_MODEL_KEYS; i++) {
    if (strcmp(MODEL_KEYS[i].name, model) == 0) return MODEL_KEYS[i].keys;
  }
  return NULL;
}


static const char * type_description(KeyType type) {
  switch (type) {
    case KEY_INT: return "an integer";
    case KEY_NUMBER: return "a number";
    case KEY_BOOL: return "a boolean";
    case KEY_STRING: return "a string";
    case KEY_OBJECT: return "an object";
    case KEY_NUMBER_ARRAY: return "an array of numbers";
  }
  return "a value";
}


static int integer_in_int_range(double value) {
  return value >= INT_MIN && value <= INT_MAX && value == floor(value);
}


static int is_finite_number(const cJSON * item) {
  return cJSON_IsNumber(item) && isfinite(item->valuedouble);
}


static int number_array_fits(const cJSON * item) {
  if (!cJSON_IsArray(item)) return 0;
  int size = cJSON_GetArraySize(item);
  if (size < 1 || size > CONFIG_ARRAY_MAX) return 0;

  const cJSON * element;
  cJSON_ArrayForEach(element, item) {
    if (!is_finite_number(element)) return 0;
  }
  return 1;
}


// Does item have the shape type asks for? (KEY_OBJECT children are checked by the caller)
static int has_type(const cJSON * item, KeyType type) {
  switch (type) {
    case KEY_INT: return cJSON_IsNumber(item) && integer_in_int_range(item->valuedouble);
    case KEY_NUMBER: return is_finite_number(item);
    case KEY_BOOL: return cJSON_IsBool(item);
    case KEY_STRING: return cJSON_IsString(item);
    case KEY_OBJECT: return cJSON_IsObject(item);
    case KEY_NUMBER_ARRAY: return number_array_fits(item);
  }
  return 0;
}


static const KeySpec * find_spec(const KeySpec keys[], const char * name) {
  for (int i = 0; keys[i].name != NULL; i++) {
    if (strcmp(keys[i].name, name) == 0) return &keys[i];
  }
  return NULL;
}


// cJSON keeps repeated keys as separate items, so a repeat is any earlier sibling with the same name
static int seen_before(const cJSON * object, const cJSON * item) {
  for (const cJSON * other = object->child; other != item; other = other->next) {
    if (other->string != NULL && strcmp(other->string, item->string) == 0) return 1;
  }
  return 0;
}


static int validate_item(const char * path, const cJSON * item, const KeySpec * spec, const char * where) {
  if (!has_type(item, spec->type)) {
    fprintf(stderr, "%s: key \"%s%s\" must be %s\n", path, where, spec->name, type_description(spec->type));
    return 0;
  }
  if (spec->type != KEY_OBJECT) return 1;

  char nested[CONFIG_STRING_MAX];
  int length = snprintf(nested, sizeof(nested), "%s%s.", where, spec->name);
  if (length < 0 || (size_t) length >= sizeof(nested)) {
    fprintf(stderr, "%s: key \"%s%s\" is nested too deep\n", path, where, spec->name);
    return 0;
  }
  return config_validate_object(path, item, spec->children, nested);
}


int config_validate_object(const char * path, const cJSON * object, const KeySpec keys[], const char * where) {
  static const KeySpec NO_KEYS[] = { { NULL, KEY_INT, 0, NULL } };
  if (keys == NULL) keys = NO_KEYS;

  for (const cJSON * item = object->child; item != NULL; item = item->next) {
    const KeySpec * spec = item->string == NULL ? NULL : find_spec(keys, item->string);
    if (spec == NULL) {
      fprintf(stderr, "%s: unknown key \"%s%s\"\n", path, where, item->string == NULL ? "" : item->string);
      return 0;
    }
    if (seen_before(object, item)) {
      fprintf(stderr, "%s: duplicate key \"%s%s\"\n", path, where, item->string);
      return 0;
    }
    if (!validate_item(path, item, spec, where)) return 0;
  }

  for (int i = 0; keys[i].name != NULL; i++) {
    if (keys[i].required && cJSON_GetObjectItemCaseSensitive(object, keys[i].name) == NULL) {
      fprintf(stderr, "%s: missing key \"%s%s\"\n", path, where, keys[i].name);
      return 0;
    }
  }
  return 1;
}


// Whole file in a heap buffer (NUL-terminated); NULL after printing the reason
static char * read_file(const char * path) {
  FILE * file = fopen(path, "rb");
  if (file == NULL) {
    perror(path);
    return NULL;
  }

  char * text = malloc(CONFIG_FILE_MAX + 1);
  if (text == NULL) {
    fprintf(stderr, "%s: couldn't allocate the config buffer\n", path);
    fclose(file);
    return NULL;
  }

  size_t length = fread(text, 1, CONFIG_FILE_MAX + 1, file);
  int failed = ferror(file);
  fclose(file);
  if (failed) {
    fprintf(stderr, "%s: couldn't read the file\n", path);
    free(text);
    return NULL;
  }
  if (length > CONFIG_FILE_MAX) {
    fprintf(stderr, "%s: the file is larger than %d bytes\n", path, CONFIG_FILE_MAX);
    free(text);
    return NULL;
  }
  text[length] = '\0';
  return text;
}


static cJSON * parse_text(const char * path, const char * text) {
  cJSON * json = cJSON_Parse(text);
  if (json != NULL) return json;

  const char * where = cJSON_GetErrorPtr();
  if (where == NULL) where = text;
  fprintf(stderr, "%s: invalid JSON near \"%.*s\"\n", path, EXCERPT_MAX, where);
  return NULL;
}


// "oja" or "kohonen, oja, hopfield": every registered model, for the unknown-model message
static void model_list(char out[], size_t size) {
  out[0] = '\0';
  for (int i = 0; i < N_MODEL_KEYS; i++) {
    if (i > 0) strncat(out, ", ", size - strlen(out) - 1);
    strncat(out, MODEL_KEYS[i].name, size - strlen(out) - 1);
  }
}


// COMMON_KEYS followed by the model's own rows, in one table ending with a NULL row
static int merge_tables(const char * path, const KeySpec model_keys[], KeySpec merged[CONFIG_KEYS_MAX + 1]) {
  int n = 0;
  for (int i = 0; COMMON_KEYS[i].name != NULL; i++) {
    merged[n++] = COMMON_KEYS[i];
  }
  for (int i = 0; model_keys[i].name != NULL; i++) {
    if (n >= CONFIG_KEYS_MAX) {
      fprintf(stderr, "%s: the key table of the model has more than %d rows\n", path, CONFIG_KEYS_MAX);
      return 0;
    }
    merged[n++] = model_keys[i];
  }
  merged[n] = (KeySpec) { NULL, KEY_INT, 0, NULL };
  return 1;
}


static int copy_string(const char * path, const cJSON * item, const char * key, char out[], size_t size) {
  if (strlen(item->valuestring) >= size) {
    fprintf(stderr, "%s: key \"%s\" is longer than %d characters\n", path, key, (int) size - 1);
    return 0;
  }
  strcpy(out, item->valuestring);
  return 1;
}


// Validates the document against the common keys plus the model's table, then fills the struct
static int read_document(const char * path, Config * config) {
  const cJSON * root = config->json;
  if (!cJSON_IsObject(root)) {
    fprintf(stderr, "%s: the top level must be an object\n", path);
    return 0;
  }

  const cJSON * model = cJSON_GetObjectItemCaseSensitive(root, "model");
  if (model == NULL) {
    fprintf(stderr, "%s: missing key \"model\"\n", path);
    return 0;
  }
  if (!cJSON_IsString(model)) {
    fprintf(stderr, "%s: key \"model\" must be a string\n", path);
    return 0;
  }

  const KeySpec * model_keys = config_model_keys(model->valuestring);
  if (model_keys == NULL) {
    char available[CONFIG_STRING_MAX];
    model_list(available, sizeof(available));
    fprintf(stderr, "%s: unknown model \"%s\" (available: %s)\n", path, model->valuestring, available);
    return 0;
  }

  KeySpec merged[CONFIG_KEYS_MAX + 1];
  if (!merge_tables(path, model_keys, merged)) return 0;
  if (!config_validate_object(path, root, merged, "")) return 0;

  // Validated: all three exist with the right type
  const cJSON * seed = cJSON_GetObjectItemCaseSensitive(root, "seed");
  if (seed->valuedouble < 0) {
    fprintf(stderr, "%s: seed must be >= 0\n", path);
    return 0;
  }
  config->seed = (unsigned int) seed->valuedouble;

  return copy_string(path, model, "model", config->model, sizeof(config->model))
      && copy_string(path, cJSON_GetObjectItemCaseSensitive(root, "input"), "input", config->input,
                     sizeof(config->input));
}


int config_load(const char * path, Config * config) {
  memset(config, 0, sizeof(*config));
  if (strlen(path) >= sizeof(config->path)) {
    fprintf(stderr, "%s: the path is longer than %d characters\n", path, CONFIG_STRING_MAX - 1);
    return 0;
  }
  strcpy(config->path, path);

  char * text = read_file(path);
  if (text == NULL) return 0;
  config->json = parse_text(path, text);
  free(text);
  if (config->json == NULL) return 0;

  if (!read_document(path, config)) {
    config_free(config);
    return 0;
  }
  return 1;
}


void config_free(Config * config) {
  cJSON_Delete(config->json);
  config->json = NULL;
}


// Walks a dotted key through nested objects; NULL after printing the reason
static const cJSON * find_item(const Config * config, const char * key) {
  char remaining[CONFIG_STRING_MAX];
  if (strlen(key) >= sizeof(remaining)) {
    fprintf(stderr, "%s: key \"%s\" is too long\n", config->path, key);
    return NULL;
  }
  strcpy(remaining, key);

  const cJSON * item = config->json;
  char * part = remaining;
  while (part != NULL) {
    char * dot = strchr(part, '.');
    if (dot != NULL) *dot = '\0';

    item = cJSON_IsObject(item) ? cJSON_GetObjectItemCaseSensitive(item, part) : NULL;
    if (item == NULL) {
      fprintf(stderr, "%s: missing key \"%s\"\n", config->path, key);
      return NULL;
    }
    part = dot == NULL ? NULL : dot + 1;
  }
  return item;
}


int config_get_int(const Config * config, const char * key, int * out) {
  const cJSON * item = find_item(config, key);
  if (item == NULL) return 0;
  if (!has_type(item, KEY_INT)) {
    fprintf(stderr, "%s: key \"%s\" must be %s\n", config->path, key, type_description(KEY_INT));
    return 0;
  }
  *out = (int) item->valuedouble;
  return 1;
}


int config_get_number(const Config * config, const char * key, double * out) {
  const cJSON * item = find_item(config, key);
  if (item == NULL) return 0;
  if (!has_type(item, KEY_NUMBER)) {
    fprintf(stderr, "%s: key \"%s\" must be %s\n", config->path, key, type_description(KEY_NUMBER));
    return 0;
  }
  *out = item->valuedouble;
  return 1;
}


int config_get_string(const Config * config, const char * key, const char ** out) {
  const cJSON * item = find_item(config, key);
  if (item == NULL) return 0;
  if (!has_type(item, KEY_STRING)) {
    fprintf(stderr, "%s: key \"%s\" must be %s\n", config->path, key, type_description(KEY_STRING));
    return 0;
  }
  *out = item->valuestring;
  return 1;
}


int config_get_number_array(const Config * config, const char * key, double out[], int max, int * count) {
  const cJSON * item = find_item(config, key);
  if (item == NULL) return 0;
  if (!has_type(item, KEY_NUMBER_ARRAY)) {
    fprintf(stderr, "%s: key \"%s\" must be %s\n", config->path, key, type_description(KEY_NUMBER_ARRAY));
    return 0;
  }

  int size = cJSON_GetArraySize(item);
  if (size > max) {
    fprintf(stderr, "%s: key \"%s\" has %d items, at most %d fit\n", config->path, key, size, max);
    return 0;
  }
  int n = 0;
  const cJSON * element;
  cJSON_ArrayForEach(element, item) {
    out[n++] = element->valuedouble;
  }
  *count = n;
  return 1;
}
