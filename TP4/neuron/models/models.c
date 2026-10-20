#include "models.h"
#include <string.h>

// Table order is the order model_names lists them in
static const Model MODELS[] = {
  { "kohonen", run_kohonen },
  { "oja", run_oja },
  { "hopfield", run_hopfield },
};

#define N_MODELS ((int) (sizeof(MODELS) / sizeof(MODELS[0])))


const Model * model_find(const char * name) {
  for (int i = 0; i < N_MODELS; i++) {
    if (strcmp(MODELS[i].name, name) == 0) return &MODELS[i];
  }
  return NULL;
}


const char * model_names(void) {
  static char names[256];
  names[0] = '\0';
  for (int i = 0; i < N_MODELS; i++) {
    if (i > 0) strncat(names, ", ", sizeof(names) - strlen(names) - 1);
    strncat(names, MODELS[i].name, sizeof(names) - strlen(names) - 1);
  }
  return names;
}
