#include "config.h"
#include <limits.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXCERPT_MAX 40


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


static int integer_in_int_range(double value) {
  return value >= INT_MIN && value <= INT_MAX && value == floor(value);
}


static int copy_string(const char * path, const cJSON * item, const char * key, char out[], size_t size) {
  if (!cJSON_IsString(item)) {
    fprintf(stderr, "%s: key \"%s\" must be a string\n", path, key);
    return 0;
  }
  if (strlen(item->valuestring) >= size) {
    fprintf(stderr, "%s: key \"%s\" is longer than %d characters\n", path, key, (int) size - 1);
    return 0;
  }
  strcpy(out, item->valuestring);
  return 1;
}


static int read_common_keys(const char * path, const cJSON * root, Config * config) {
  const cJSON * model = cJSON_GetObjectItemCaseSensitive(root, "model");
  const cJSON * seed = cJSON_GetObjectItemCaseSensitive(root, "seed");
  const cJSON * input = cJSON_GetObjectItemCaseSensitive(root, "input");

  if (model == NULL || seed == NULL || input == NULL) {
    fprintf(stderr, "%s: missing key \"%s\"\n", path, model == NULL ? "model" : seed == NULL ? "seed" : "input");
    return 0;
  }
  if (!copy_string(path, model, "model", config->model, sizeof(config->model))) return 0;
  if (!cJSON_IsNumber(seed) || !integer_in_int_range(seed->valuedouble)) {
    fprintf(stderr, "%s: key \"seed\" must be an integer\n", path);
    return 0;
  }
  if (seed->valuedouble < 0) {
    fprintf(stderr, "%s: seed must be >= 0\n", path);
    return 0;
  }
  config->seed = (unsigned int) seed->valuedouble;
  return copy_string(path, input, "input", config->input, sizeof(config->input));
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

  if (!cJSON_IsObject(config->json)) {
    fprintf(stderr, "%s: the top level must be an object\n", path);
    config_free(config);
    return 0;
  }
  if (!read_common_keys(path, config->json, config)) {
    config_free(config);
    return 0;
  }
  return 1;
}


void config_free(Config * config) {
  cJSON_Delete(config->json);
  config->json = NULL;
}
