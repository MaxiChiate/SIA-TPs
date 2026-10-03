#include "config.h"
#include <ctype.h>
#include <stddef.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CONFIG_FILE_MAX 4096

enum field_type { FIELD_STRING, FIELD_DOUBLE, FIELD_INT, FIELD_UINT, FIELD_INT_ARRAY };

typedef struct {
  const char * key;
  enum field_type type;
  size_t offset;
  size_t count_offset; // FIELD_INT_ARRAY only: where the element count goes
  int optional;        // may be left out, the field then keeps its zero value
} Field;

static const Field FIELDS[] = {
  { "train_dataset",      FIELD_STRING,    offsetof(Config, train_dataset), 0, 0 },
  { "validation_dataset", FIELD_STRING,    offsetof(Config, validation_dataset), 0, 0 },
  { "activation",         FIELD_STRING,    offsetof(Config, activation), 0, 0 },
  { "eta",                FIELD_DOUBLE,    offsetof(Config, eta), 0, 0 },
  { "epochs",             FIELD_INT,       offsetof(Config, epochs), 0, 0 },
  { "batch_size",         FIELD_INT,       offsetof(Config, batch_size), 0, 0 },
  { "hidden_layers",      FIELD_INT_ARRAY, offsetof(Config, hidden_layers), offsetof(Config, n_hidden_layers), 0 },
  { "tolerance",          FIELD_DOUBLE,    offsetof(Config, tolerance), 0, 1 },
  { "seed",               FIELD_UINT,      offsetof(Config, seed), 0, 0 },
  { "initial_weights",    FIELD_STRING,    offsetof(Config, initial_weights), 0, 1 },
};

#define N_FIELDS ((int) (sizeof(FIELDS) / sizeof(FIELDS[0])))

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


static int parse_value(Parser * parser, const Field * field, Config * config) {
  void * target = (char *) config + field->offset;

  if (field->type == FIELD_STRING) return parse_string(parser, target);
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

  return 1;
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
