CC      := gcc
CFLAGS  := -std=c11 -Wall -Wextra -O2 -MMD -MP
LDLIBS  := -lm

BUILD_DIR := build
TARGET    := $(BUILD_DIR)/neuron

SOURCES := $(wildcard *.c io/*.c activation/*.c)
OBJECTS := $(SOURCES:%.c=$(BUILD_DIR)/%.o)
DEPS    := $(OBJECTS:.o=.d)

CONFIG ?= config.json

.PHONY: all run clean

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CC) $(CFLAGS) $^ -o $@ $(LDLIBS)

$(BUILD_DIR)/%.o: %.c
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) -c $< -o $@

run: $(TARGET)
	./$(TARGET) $(CONFIG)

clean:
	rm -rf $(BUILD_DIR)

-include $(DEPS)
