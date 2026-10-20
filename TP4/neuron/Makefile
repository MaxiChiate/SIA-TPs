CC      := gcc
# No -O3, -march=native or float-reordering flags: plain -O2 keeps the C sums comparable with numpy
CFLAGS  := -std=c11 -Wall -Wextra -Wpedantic -O2 -MMD -MP
# The vendored cJSON is compiled with its own, laxer flags (never edited, so never warned about)
VENDOR_CFLAGS := -std=c11 -O2 -MMD -MP
LDLIBS  := -lm

BUILD_DIR := build
TARGET    := $(BUILD_DIR)/neuron

SOURCES := $(wildcard *.c io/*.c models/*.c vendor/cjson/*.c)
OBJECTS := $(SOURCES:%.c=$(BUILD_DIR)/%.o)

# Tests: everything but main.c, linked with tests/test_main.c
TEST_TARGET  := $(BUILD_DIR)/tests/test_main
TEST_OBJECTS := $(filter-out $(BUILD_DIR)/main.o,$(OBJECTS)) $(BUILD_DIR)/tests/test_main.o
DEPS         := $(OBJECTS:.o=.d) $(BUILD_DIR)/tests/test_main.d

CONFIG ?= config.json

# Python of the root .venv; the root Makefile passes it down as an absolute path
PY ?= $(abspath ../.venv/bin/python)

# Generated, not versioned. If it is missing (fresh clone) the root Makefile makes it
PREPARED := ../datos/prepared/creadores_zscore.csv

.PHONY: all run clean test test-c debug

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CC) $(CFLAGS) $^ -o $@ $(LDLIBS)

$(BUILD_DIR)/vendor/cjson/cJSON.o: vendor/cjson/cJSON.c
	@mkdir -p $(@D)
	$(CC) $(VENDOR_CFLAGS) -c $< -o $@

$(BUILD_DIR)/%.o: %.c
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) -c $< -o $@

# The binary prints "results -> <run dir>"
run: $(TARGET)
	./$(TARGET) $(CONFIG)

$(PREPARED):
	$(MAKE) -C .. prepare

# The C tests read only tests/fixtures
test-c: $(TEST_TARGET)
	./$(TEST_TARGET)

# C tests, then the Python ones (they read datos/prepared/)
test: test-c $(PREPARED)
	$(PY) -m pytest ../analysis/tests -q

$(TEST_TARGET): $(TEST_OBJECTS)
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) $^ -o $@ $(LDLIBS)

# The C tests under AddressSanitizer and UndefinedBehaviorSanitizer, in their own build directory.
# The flags also reach the link line, which uses CFLAGS.
debug:
	$(MAKE) BUILD_DIR=build/debug \
	  CFLAGS="-std=c11 -Wall -Wextra -Wpedantic -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer -MMD -MP" \
	  VENDOR_CFLAGS="-std=c11 -Wno-deprecated-declarations -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer -MMD -MP" \
	  test-c

clean:
	rm -rf $(BUILD_DIR)

-include $(DEPS)
