#include "config.h"
#include <ctype.h>
#include <stddef.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CONFIG_FILE_MAX 4096

enum field_type { FIELD_STRING, FIELD_DOUBLE, FIELD_INT, FIELD_UINT, FIELD_BOOL, FIELD_INT_ARRAY };

typedef struct {
  const char * key;
  enum field_type type;
  size_t offset;
  size_t count_offset; // FIELD_INT_ARRAY only: where the element count goes
  int optional;        // may be left out, the field then keeps its zero value
} Field;

static const Field FIELDS[] = {
  { "train_dataset",      FIELD_STRING,    offsetof(Config, train_dataset), 0, 0 },
  { "validation_dataset", FIELD_STRING,    offsetof(Config, validation_dataset), 0, 1 },
  { "activation",         FIELD_STRING,    offsetof(Config, activation), 0, 0 },
  { "eta",                FIELD_DOUBLE,    offsetof(Config, eta), 0, 0 },
  { "epochs",             FIELD_INT,       offsetof(Config, epochs), 0, 0 },
  { "batch_size",         FIELD_INT,       offsetof(Config, batch_size), 0, 0 },
  { "hidden_layers",      FIELD_INT_ARRAY, offsetof(Config, hidden_layers), offsetof(Config, n_hidden_layers), 0 },
  { "tolerance",          FIELD_DOUBLE,    offsetof(Config, tolerance), 0, 1 },
  { "seed",               FIELD_UINT,      offsetof(Config, seed), 0, 0 },
  { "shuffle",            FIELD_BOOL,      offsetof(Config, shuffle), 0, 1 },
  { "validation_split",   FIELD_DOUBLE,    offsetof(Config, validation_split), 0, 1 },
  { "split_seed",         FIELD_UINT,      offsetof(Config, split_seed), 0, 1 },
  { "initial_weights",    FIELD_STRING,    offsetof(Config, initial_weights), 0, 1 },
  { "optimizer",          FIELD_STRING,    offsetof(Config, optimizer), 0, 1 },
  { "momentum",           FIELD_DOUBLE,    offsetof(Config, momentum), 0, 1 },
  { "rmsprop_decay",      FIELD_DOUBLE,    offsetof(Config, rmsprop_decay), 0, 1 },
  { "adam_beta1",         FIELD_DOUBLE,    offsetof(Config, adam_beta1), 0, 1 },
  { "adam_beta2",         FIELD_DOUBLE,    offsetof(Config, adam_beta2), 0, 1 },
  { "optimizer_epsilon",  FIELD_DOUBLE,    offsetof(Config, optimizer_epsilon), 0, 1 },
};

#define N_FIELDS ((int) (sizeof(FIELDS) / sizeof(FIELDS[0])))

// Optimizer hyperparameters. None has a default: the run's config.json shows every value it trained with.
typedef struct {
  const char * key;
  const char * typical; // suggested when it's missing (class 12.1 and the Adam paper)
  int fraction;         // 1: in [0, 1); 0: positive
} Hyperparameter;

static const Hyperparameter HYPERPARAMETERS[] = {
  { "momentum",          "0.9",   1 },
  { "rmsprop_decay",     "0.9",   1 },
  { "adam_beta1",        "0.9",   1 },
  { "adam_beta2",        "0.999", 1 },
  { "optimizer_epsilon", "1e-8",  0 },
};

#define N_HYPERPARAMETERS ((int) (sizeof(HYPERPARAMETERS) / sizeof(HYPERPARAMETERS[0])))
#define MAX_OPTIMIZER_KEYS 3

// Which hyperparameters each optimizer reads. The names must match the optimizer module's (a test checks it).
typedef struct {
  const char * name;
  const char * keys[MAX_OPTIMIZER_KEYS]; // NULL after the last one
} OptimizerKeys;

static const OptimizerKeys OPTIMIZERS[] = {
  { "gd",       { NULL } },
  { "momentum", { "momentum" } },
  { "rmsprop",  { "rmsprop_decay", "optimizer_epsilon" } },
  { "adam",     { "adam_beta1", "adam_beta2", "optimizer_epsilon" } },
};

#define N_OPTIMIZERS ((int) (sizeof(OPTIMIZERS) / sizeof(OPTIMIZERS[0])))

typedef struct {
  const char * path;
  const char * cursor;
} Parser;


static int parse_error(const Parser * parser, const char * message) {
  fprintf(stderr, "%s: %s\n", parser->path, message);
  return 0;
}


static void skip_whitespace(Parser * parser) {
  while (isspace((unsigned char) *parser->cursor)) parser->cursor++;
}


static int expect(Parser * parser, char c) {
  skip_whitespace(parser);
  if (*parser->cursor != c) {
    char message[64];
    snprintf(message, sizeof(message), "expected '%c'", c);
    return parse_error(parser, message);
  }
  parser->cursor++;
  return 1;
}


static int parse_string(Parser * parser, char out[CONFIG_STRING_MAX]) {
  if (!expect(parser, '"')) return 0;

  int length = 0;
  while (*parser->cursor != '"') {
    char c = *parser->cursor++;
    if (c == '\0') return parse_error(parser, "unterminated string");
    if (c == '\\') {
      c = *parser->cursor++;
      if (c != '"' && c != '\\' && c != '/') return parse_error(parser, "unsupported escape sequence");
    }
    if (length == CONFIG_STRING_MAX - 1) return parse_error(parser, "string too long");
    out[length++] = c;
  }
  parser->cursor++;
  out[length] = '\0';
  return 1;
}


static int parse_number(Parser * parser, double * out) {
  skip_whitespace(parser);
  char * end;
  *out = strtod(parser->cursor, &end);
  if (end == parser->cursor) return parse_error(parser, "expected a number");
  parser->cursor = end;
  return 1;
}


static int parse_integer(Parser * parser, int * out) {
  double value;
  if (!parse_number(parser, &value)) return 0;
  if (value != floor(value)) return parse_error(parser, "expected an integer");
  *out = (int) value;
  return 1;
}


static int parse_int_array(Parser * parser, int out[CONFIG_HIDDEN_LAYERS_MAX], int * count) {
  if (!expect(parser, '[')) return 0;

  *count = 0;
  skip_whitespace(parser);
  if (*parser->cursor == ']') {
    parser->cursor++;
    return 1;
  }

  while (1) {
    if (*count == CONFIG_HIDDEN_LAYERS_MAX) return parse_error(parser, "array too long");
    if (!parse_integer(parser, &out[(*count)++])) return 0;

    skip_whitespace(parser);
    if (*parser->cursor != ',') return expect(parser, ']');
    parser->cursor++;
  }
}


static const Field * find_field(const char * key) {
  for (int i = 0; i < N_FIELDS; i++) {
    if (strcmp(FIELDS[i].key, key) == 0) return &FIELDS[i];
  }
  return NULL;
}


static int parse_bool(Parser * parser, int * out) {
  skip_whitespace(parser);
  if (strncmp(parser->cursor, "true", 4) == 0) {
    *out = 1;
    parser->cursor += 4;
  } else if (strncmp(parser->cursor, "false", 5) == 0) {
    *out = 0;
    parser->cursor += 5;
  } else {
    return parse_error(parser, "expected true or false");
  }
  return 1;
}


static int parse_value(Parser * parser, const Field * field, Config * config) {
  void * target = (char *) config + field->offset;

  if (field->type == FIELD_STRING) return parse_string(parser, target);
  if (field->type == FIELD_BOOL) return parse_bool(parser, target);
  if (field->type == FIELD_INT_ARRAY) return parse_int_array(parser, target, (int *) ((char *) config + field->count_offset));

  double value;
  if (!parse_number(parser, &value)) return 0;

  switch (field->type) {
    case FIELD_DOUBLE:
      *(double *) target = value;
      return 1;
    case FIELD_INT:
      if (value != floor(value)) return parse_error(parser, "expected an integer");
      *(int *) target = (int) value;
      return 1;
    case FIELD_UINT:
      if (value != floor(value) || value < 0) return parse_error(parser, "expected a non-negative integer");
      *(unsigned int *) target = (unsigned int) value;
      return 1;
    default:
      return 0;
  }
}


static int was_given(const int seen[], const char * key) {
  return seen[find_field(key) - FIELDS];
}


// The validation set comes either from its own file or from a split of the train one, never both
static int check_validation_source(const Parser * parser, const int seen[]) {
  int has_dataset = was_given(seen, "validation_dataset");
  int has_split = was_given(seen, "validation_split");
  if (has_dataset == has_split) {
    return parse_error(parser, "give exactly one of \"validation_dataset\" and \"validation_split\"");
  }
  if (has_split && !was_given(seen, "split_seed")) return parse_error(parser, "missing key \"split_seed\"");
  if (!has_split && was_given(seen, "split_seed")) {
    return parse_error(parser, "\"split_seed\" only goes with \"validation_split\"");
  }
  return 1;
}


static const OptimizerKeys * find_optimizer(const char * name) {
  for (int i = 0; i < N_OPTIMIZERS; i++) {
    if (strcmp(OPTIMIZERS[i].name, name) == 0) return &OPTIMIZERS[i];
  }
  return NULL;
}


static int reads_key(const OptimizerKeys * optimizer, const char * key) {
  for (int i = 0; i < MAX_OPTIMIZER_KEYS && optimizer->keys[i] != NULL; i++) {
    if (strcmp(optimizer->keys[i], key) == 0) return 1;
  }
  return 0;
}


static int unknown_optimizer(const Parser * parser, const char * name) {
  fprintf(stderr, "%s: unknown optimizer \"%s\" (available:", parser->path, name);
  for (int i = 0; i < N_OPTIMIZERS; i++) {
    fprintf(stderr, "%s %s", i == 0 ? "" : ",", OPTIMIZERS[i].name);
  }
  fprintf(stderr, ")\n");
  return 0;
}


static int check_hyperparameter_range(const Parser * parser, const Config * config, const Hyperparameter * hyperparameter) {
  double value = *(const double *) ((const char *) config + find_field(hyperparameter->key)->offset);
  if (hyperparameter->fraction && !(value >= 0 && value < 1)) {
    fprintf(stderr, "%s: \"%s\" must be in [0, 1)\n", parser->path, hyperparameter->key);
    return 0;
  }
  if (!hyperparameter->fraction && !(value > 0)) {
    fprintf(stderr, "%s: \"%s\" must be positive\n", parser->path, hyperparameter->key);
    return 0;
  }
  return 1;
}


// Without "optimizer" it's gd. Every hyperparameter the optimizer reads is required, and any other refused.
static int check_optimizer(const Parser * parser, Config * config, const int seen[]) {
  if (!was_given(seen, "optimizer")) strcpy(config->optimizer, "gd");
  const OptimizerKeys * optimizer = find_optimizer(config->optimizer);
  if (optimizer == NULL) return unknown_optimizer(parser, config->optimizer);

  for (int i = 0; i < N_HYPERPARAMETERS; i++) {
    const Hyperparameter * hyperparameter = &HYPERPARAMETERS[i];
    int reads = reads_key(optimizer, hyperparameter->key);
    int given = was_given(seen, hyperparameter->key);
    if (reads && !given) {
      fprintf(stderr, "%s: missing key \"%s\" for optimizer \"%s\" (typical: %s)\n", parser->path,
              hyperparameter->key, optimizer->name, hyperparameter->typical);
      return 0;
    }
    if (!reads && given) {
      fprintf(stderr, "%s: \"%s\" doesn't go with optimizer \"%s\"\n", parser->path, hyperparameter->key,
              optimizer->name);
      return 0;
    }
    if (reads && !check_hyperparameter_range(parser, config, hyperparameter)) return 0;
  }
  return 1;
}


static int parse_object(Parser * parser, Config * config) {
  int seen[N_FIELDS] = {0};

  if (!expect(parser, '{')) return 0;

  skip_whitespace(parser);
  int done = (*parser->cursor == '}');
  if (done) parser->cursor++;

  while (!done) {
    char key[CONFIG_STRING_MAX];
    if (!parse_string(parser, key)) return 0;

    const Field * field = find_field(key);
    if (field == NULL) {
      fprintf(stderr, "%s: unknown key \"%s\"\n", parser->path, key);
      return 0;
    }

    if (!expect(parser, ':') || !parse_value(parser, field, config)) return 0;
    seen[field - FIELDS] = 1;

    skip_whitespace(parser);
    if (*parser->cursor == ',') {
      parser->cursor++;
    } else if (!expect(parser, '}')) {
      return 0;
    } else {
      done = 1;
    }
  }

  skip_whitespace(parser);
  if (*parser->cursor != '\0') return parse_error(parser, "unexpected content after the object");

  for (int i = 0; i < N_FIELDS; i++) {
    if (!seen[i] && !FIELDS[i].optional) {
      fprintf(stderr, "%s: missing key \"%s\"\n", parser->path, FIELDS[i].key);
      return 0;
    }
  }

  return check_validation_source(parser, seen) && check_optimizer(parser, config, seen);
}


static int read_file(const char * path, char buffer[CONFIG_FILE_MAX]) {
  FILE * file = fopen(path, "r");
  if (file == NULL) {
    perror(path);
    return 0;
  }

  size_t length = fread(buffer, 1, CONFIG_FILE_MAX - 1, file);
  int too_long = !feof(file);
  fclose(file);

  if (too_long) {
    fprintf(stderr, "%s: file too long\n", path);
    return 0;
  }

  buffer[length] = '\0';
  return 1;
}


static int validate(const char * path, const Config * config) {
  if (config->eta <= 0) {
    fprintf(stderr, "%s: \"eta\" must be positive\n", path);
    return 0;
  }
  if (config->epochs <= 0) {
    fprintf(stderr, "%s: \"epochs\" must be positive\n", path);
    return 0;
  }
  if (config->batch_size <= 0) {
    fprintf(stderr, "%s: \"batch_size\" must be positive\n", path);
    return 0;
  }
  if (config->validation_dataset[0] == '\0' && !(config->validation_split > 0 && config->validation_split < 1)) {
    fprintf(stderr, "%s: \"validation_split\" must be between 0 and 1, both excluded\n", path);
    return 0;
  }
  if (config->tolerance < 0) {
    fprintf(stderr, "%s: \"tolerance\" can't be negative\n", path);
    return 0;
  }
  for (int i = 0; i < config->n_hidden_layers; i++) {
    if (config->hidden_layers[i] <= 0) {
      fprintf(stderr, "%s: every entry of \"hidden_layers\" must be positive\n", path);
      return 0;
    }
  }
  return 1;
}


int config_load(const char * path, Config * config) {
  char buffer[CONFIG_FILE_MAX];
  if (!read_file(path, buffer)) return 0;

  *config = (Config) {0};
  Parser parser = { .path = path, .cursor = buffer };
  return parse_object(&parser, config) && validate(path, config);
}
