# Fastly Compute Python SDK

# Default Viceroy location. Set VICEROY env var to change.
VICEROY ?= viceroy

# Configuration
STUBS_DIR := stubs
BUILD_DIR := build
EXAMPLES_DIR := examples

# Define all available examples (add new ones here)
EXAMPLES := bottle-app flask-app game-of-life

# Default example for serve target
EXAMPLE ?= bottle-app
WASM_FILE := $(BUILD_DIR)/$(EXAMPLE).composed.wasm

TARGET_WORLD := fastly:compute/service

# Generate WASM file paths for all examples
EXAMPLE_WASMS := $(foreach example,$(EXAMPLES),$(BUILD_DIR)/$(example).wasm)

# Composed wasm for each example
COMPOSED_WASMS := $(foreach example,$(EXAMPLES),$(BUILD_DIR)/$(example).composed.wasm)

WASILESS_ROOT := vendor/wasiless
WASILESS_WASM := $(WASILESS_ROOT)/wasiless.wasm

# Default target builds all examples
all: $(COMPOSED_WASMS)

$(BUILD_DIR)/%.composed.wasm: $(BUILD_DIR)/%.wasm $(WASILESS_WASM)
	@echo "Composing $* example"
	wac compose --dep fastly:wasiless=$(WASILESS_WASM) --dep app:component=$< -o $@ wrap_app_in_wasiless.wac

# Pattern rule for building any example
$(BUILD_DIR)/%.wasm: $(EXAMPLES_DIR)/%.py wit/viceroy.wit wit/deps/fastly/compute.wit fastly_compute/wsgi.py | $(BUILD_DIR)
	@echo "Building $* example..."
	rm -rf $(STUBS_DIR)
	uv run componentize-py -d wit -w $(TARGET_WORLD) bindings $(STUBS_DIR)
	uv run componentize-py -d wit -w $(TARGET_WORLD) componentize $* -p $(EXAMPLES_DIR) -p . -o $@

$(WASILESS_WASM):
	 $(MAKE) -C $(WASILESS_ROOT) wasiless.wasm

# Create build directory
$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

# Serve the specified example (default: bottle-app)
serve: $(WASM_FILE)
	@echo "Serving $(EXAMPLE) example on http://127.0.0.1:7676"
	$(VICEROY) serve $(WASM_FILE)

# Test all examples (requires all WASM files to be built)
test: $(COMPOSED_WASMS)
	uv run --extra test pytest

# List available examples
list-examples:
	@echo "Available examples:"
	@for example in $(EXAMPLES); do echo "  $$example"; done

# Build all examples (alias for 'all')
build-all: all

# Clean build artifacts
clean:
	rm -rf $(BUILD_DIR) $(STUBS_DIR)

# Development tools
lint: $(EXAMPLE_WASMS)
	uv run --extra dev ruff check .
	uv run --extra dev --extra test pyrefly check .

lint-fix:
	uv run --extra dev ruff check --fix .

format:
	uv run --extra dev ruff format .

format-check:
	uv run --extra dev ruff format --check .

# Help target
help:
	@echo "Fastly Compute Python SDK"
	@echo ""
	@echo "Targets:"
	@echo "  all                 Build all examples"
	@echo "  serve [EXAMPLE=name] Serve example (default: $(EXAMPLE))"
	@echo "  test                Run integration tests (builds all examples)"
	@echo "  build-all           Build all examples (alias for 'all')"
	@echo "  list-examples       List available examples"
	@echo "  clean               Clean build artifacts"
	@echo "  lint                Run linter"
	@echo "  lint-fix            Run linter with auto-fix"
	@echo "  format              Format code"
	@echo "  format-check        Check code formatting"
	@echo ""
	@echo "Examples:"
	@echo "  make                          # Build all examples"
	@echo "  make serve                    # Serve bottle-app example"
	@echo "  make serve EXAMPLE=flask-app  # Serve flask-app example"
	@echo "  make build/flask-app.wasm     # Build specific example"
	@echo ""
	@echo "Available examples: $(EXAMPLES)"

.PHONY: all serve test list-examples build-all clean lint lint-fix format format-check help $(WASILESS_WASM)
