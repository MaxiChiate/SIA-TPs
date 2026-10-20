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
DEPS    := $(OBJECTS:.o=.d)

CONFIG ?= config.json

.PHONY: all run clean

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

clean:
	rm -rf $(BUILD_DIR)

-include $(DEPS)
