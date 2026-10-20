#define _POSIX_C_SOURCE 200809L // clock_gettime

#include "io/config.h"
#include "io/results.h"
#include "models/models.h"
#include "rng.h"
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define DEFAULT_CONFIG_PATH "config.json"


static void die(const char * format, ...) {
  va_list args;
  va_start(args, format);
  vfprintf(stderr, format, args);
  va_end(args);
  fputc('\n', stderr);
  exit(EXIT_FAILURE);
}


static const char * config_path(int argc, char * argv[]) {
  if (argc > 2) die("usage: %s [config.json]", argv[0]);
  return argc == 2 ? argv[1] : DEFAULT_CONFIG_PATH;
}


static double now_seconds(void) {
  struct timespec now;
  clock_gettime(CLOCK_MONOTONIC, &now);
  return now.tv_sec + now.tv_nsec * 1e-9;
}


int main(int argc, char * argv[]) {

  const char * path = config_path(argc, argv);
  Config config;
  if (!config_load(path, &config)) return EXIT_FAILURE;

  const Model * model = model_find(config.model);
  if (model == NULL) {
    fprintf(stderr, "%s: unknown model \"%s\" (available: %s)\n", path, config.model, model_names());
    config_free(&config);
    return EXIT_FAILURE;
  }

  Rng rng = rng_new(config.seed);
  Results results;
  if (!results_create(path, config.model, config.seed, &results)) {
    config_free(&config);
    return EXIT_FAILURE;
  }

  double started_at = now_seconds();
  if (!model->run(&config, &rng, &results)) {
    fprintf(stderr, "%s: the %s run failed\n", path, config.model);
    config_free(&config);
    return EXIT_FAILURE;
  }

  // The duration goes to stderr only: a file holding it would make two same-seed runs differ
  fprintf(stderr, "%s finished in %.3fs\n", config.model, now_seconds() - started_at);
  printf("results -> %s\n", results.dir);

  config_free(&config);
  return 0;

}
