#ifndef __CONFIG_H__
#define __CONFIG_H__

#define CONFIG_STRING_MAX 256

typedef struct {
  char train_dataset[CONFIG_STRING_MAX];
  char validation_dataset[CONFIG_STRING_MAX];
  char activation[CONFIG_STRING_MAX];
  double eta;
  int epochs;
  unsigned int seed;
} Config;

// Reads a flat JSON object with every Config field as a key.
// Returns 1 on success; on failure prints the reason to stderr and returns 0.
int config_load(const char * path, Config * config);

#endif //__CONFIG_H__
