CC      := gcc
# -fassociative-math lets gcc vectorize the weighted sums (neuron_predict is ~90% of the time); it only
# reorders additions, so results match -O2 to ~1e-10
CFLAGS  := -std=c11 -Wall -Wextra -O3 -march=native -fassociative-math -fno-signed-zeros -fno-trapping-math -MMD -MP
LDLIBS  := -lm

BUILD_DIR := build
TARGET    := $(BUILD_DIR)/neuron

SOURCES := $(wildcard *.c io/*.c activation/*.c)
OBJECTS := $(SOURCES:%.c=$(BUILD_DIR)/%.o)
DEPS    := $(OBJECTS:.o=.d)

CONFIG ?= config.json
REPORT := ../scripts/run_report.py
PORT   ?= 8000

.PHONY: all run serve clean

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CC) $(CFLAGS) $^ -o $@ $(LDLIBS)

$(BUILD_DIR)/%.o: %.c
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) -c $< -o $@

# The binary prints "results -> <run dir>"; the report is written into that directory
run: $(TARGET)
	@output=$$(./$(TARGET) $(CONFIG)) && echo "$$output" && python3 $(REPORT) "$${output#results -> }"

# Serves the latest run's report on localhost:$(PORT); the page reloads by itself after each run
serve:
	python3 ../scripts/report_server.py --port $(PORT)

clean:
	rm -rf $(BUILD_DIR)

-include $(DEPS)
