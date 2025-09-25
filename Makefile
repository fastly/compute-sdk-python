# Fastly Compute Python SDK

# Configuration
STUBS_DIR := stubs
BUILD_DIR := build
EXAMPLES_DIR := examples

# Define all available examples (add new ones here)
EXAMPLES := wit-bottle flask-app backend-simple requests-simple datascience-compatibility datascience-wasi numpy-wasi-test

# Default example for serve target
EXAMPLE ?= wit-bottle
WASM_FILE := $(BUILD_DIR)/$(EXAMPLE).wasm

VICEROY ?= viceroy

# Generate WASM file paths for all examples
EXAMPLE_WASMS := $(foreach example,$(EXAMPLES),$(BUILD_DIR)/$(example).wasm)

# Default target builds all examples
all: $(EXAMPLE_WASMS)

# Pattern rule for building any example
$(BUILD_DIR)/%.wasm: $(EXAMPLES_DIR)/%.py wit/viceroy.wit wit/deps/fastly/compute.wit | $(BUILD_DIR)
	@echo "Building $* example..."
	rm -rf $(STUBS_DIR)
	uv run componentize-py -d wit -w viceroy bindings $(STUBS_DIR)
	uv run componentize-py -d wit -w viceroy componentize $* -p $(EXAMPLES_DIR) -p . -o $@

# Special target for datascience-compatibility with extra dependencies
$(BUILD_DIR)/datascience-compatibility.wasm: $(EXAMPLES_DIR)/datascience-compatibility.py wit/viceroy.wit wit/deps/fastly/compute.wit | $(BUILD_DIR)
	@echo "Building datascience-compatibility example with data science dependencies..."
	@echo "Note: This may take longer due to large dependencies that may not work in WASM"
	rm -rf $(STUBS_DIR)
	uv run --extra datascience componentize-py -d wit -w viceroy bindings $(STUBS_DIR)
	uv run --extra datascience componentize-py -d wit -w viceroy componentize datascience-compatibility -p $(EXAMPLES_DIR) -p . -o $@

# Create build directory
$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

# Serve the specified example (default: wit-bottle)
serve: $(WASM_FILE)
	@echo "Serving $(EXAMPLE) example on http://127.0.0.1:7676"
	$(VICEROY) serve $(WASM_FILE)

# Test all examples (requires all WASM files to be built)
test: $(EXAMPLE_WASMS)
	VICEROY=$(VICEROY) uv run --extra test pytest

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
lint:
	uv run --extra dev ruff check .

lint-fix:
	uv run --extra dev ruff check --fix .

format:
	uv run --extra dev ruff format .

format-check:
	uv run --extra dev ruff format --check .

# Data science tools
install-datascience:
	@echo "Installing data science dependencies..."
	@echo "Warning: Many of these libraries may not work in WASM environment"
	uv sync --extra datascience

serve-datascience: $(BUILD_DIR)/datascience-compatibility.wasm
	@echo "Serving datascience-compatibility example on http://127.0.0.1:7676"
	@echo "Try: curl http://127.0.0.1:7676/test-all"
	$(VICEROY) serve $(BUILD_DIR)/datascience-compatibility.wasm

# WASI wheels integration
setup-wasi-wheels:
	@echo "Setting up WASI wheels..."
	@if [ ! -d wasi-packages/numpy ]; then \
		./scripts/download-wasi-wheels.sh numpy; \
	else \
		echo "✅ NumPy already available"; \
	fi
	@echo "Downloading pandas manually (workaround for API issue)..."
	@mkdir -p wasi-packages
	@if [ ! -f wasi-packages/pandas-wasi.tar.gz ] && [ ! -d wasi-packages/pandas ]; then \
		curl -L -f -o wasi-packages/pandas-wasi.tar.gz https://github.com/dicej/wasi-wheels/releases/download/latest/pandas-wasi.tar.gz || true; \
	fi
	@if [ -f wasi-packages/pandas-wasi.tar.gz ] && [ ! -d wasi-packages/pandas ]; then \
		cd wasi-packages && tar -xzf pandas-wasi.tar.gz && rm pandas-wasi.tar.gz; \
	fi
	@if [ -d wasi-packages/pandas ]; then \
		echo "✅ Pandas already available"; \
	fi
	@rm -rf wasi-packages/pandas
	@echo "✅ WASI wheels ready: numpy, pandas"

# Special target for WASI-enabled datascience example
$(BUILD_DIR)/datascience-wasi.wasm: $(EXAMPLES_DIR)/datascience-wasi.py wit/viceroy.wit wit/deps/fastly/compute.wit setup-wasi-wheels | $(BUILD_DIR)
	@echo "Building WASI-enabled datascience example..."
	@echo "Using WASI wheels: numpy, pandas"
	rm -rf $(STUBS_DIR)
	PYTHONPATH="$(PWD)/wasi-packages:$$PYTHONPATH" uv run componentize-py -d wit -w viceroy bindings $(STUBS_DIR)
	PYTHONPATH="$(PWD)/wasi-packages:$$PYTHONPATH" uv run componentize-py -d wit -w viceroy componentize datascience-wasi -p $(EXAMPLES_DIR) -p . -p wasi-packages -o $@

serve-datascience-wasi: $(BUILD_DIR)/datascience-wasi.wasm
	@echo "Serving WASI-enabled datascience example on http://127.0.0.1:7676"
	@echo "This example uses real numpy and pandas from WASI wheels!"
	@echo "Try: curl http://127.0.0.1:7676/test-all"
	$(VICEROY) serve $(BUILD_DIR)/datascience-wasi.wasm

# NumPy-only WASI test
$(BUILD_DIR)/numpy-wasi-test.wasm: $(EXAMPLES_DIR)/numpy-wasi-test.py wit/viceroy.wit wit/deps/fastly/compute.wit setup-wasi-wheels | $(BUILD_DIR)
	@echo "Building NumPy-only WASI test..."
	@echo "Using WASI wheels: numpy only"
	@mkdir -p wasi-packages-numpy-only
	@cp -r wasi-packages/numpy wasi-packages-numpy-only/ 2>/dev/null || true
	rm -rf $(STUBS_DIR)
	PYTHONPATH="$(PWD)/wasi-packages-numpy-only:$$PYTHONPATH" uv run componentize-py -d wit -w viceroy bindings $(STUBS_DIR)
	PYTHONPATH="$(PWD)/wasi-packages-numpy-only:$$PYTHONPATH" uv run componentize-py -d wit -w viceroy componentize numpy-wasi-test -p $(EXAMPLES_DIR) -p . -p wasi-packages-numpy-only -o $@

serve-numpy-wasi: $(BUILD_DIR)/numpy-wasi-test.wasm
	@echo "Serving NumPy WASI test on http://127.0.0.1:7676"
	@echo "This tests just NumPy from WASI wheels!"
	@echo "Try: curl http://127.0.0.1:7676/test-all"
	$(VICEROY) serve $(BUILD_DIR)/numpy-wasi-test.wasm

# Help target
help:
	@echo "Fastly Compute Python SDK"
	@echo ""
	@echo "Targets:"
	@echo "  all                    Build all examples"
	@echo "  serve [EXAMPLE=name]   Serve example (default: $(EXAMPLE))"
	@echo "  test                   Run integration tests (builds all examples)"
	@echo "  build-all              Build all examples (alias for 'all')"
	@echo "  list-examples          List available examples"
	@echo "  clean                  Clean build artifacts"
	@echo "  lint                   Run linter"
	@echo "  lint-fix               Run linter with auto-fix"
	@echo "  format                 Format code"
	@echo "  format-check           Check code formatting"
	@echo ""
	@echo "Data Science Targets:"
	@echo "  install-datascience    Install data science dependencies"
	@echo "  serve-datascience      Build and serve datascience-compatibility example"
	@echo ""
	@echo "WASI Wheels Targets:"
	@echo "  setup-wasi-wheels      Download and setup WASI wheels (numpy, pandas)"
	@echo "  serve-datascience-wasi Build and serve WASI-enabled datascience example"
	@echo ""
	@echo "Examples:"
	@echo "  make                                    # Build all examples"
	@echo "  make serve                              # Serve wit-bottle example"
	@echo "  make serve EXAMPLE=flask-app            # Serve flask-app example"
	@echo "  make build/flask-app.wasm               # Build specific example"
	@echo "  make install-datascience                # Install data science libs"
	@echo "  make serve-datascience                  # Test data science compatibility"
	@echo "  make setup-wasi-wheels                  # Download WASI wheels"
	@echo "  make serve-datascience-wasi             # Test WASI data science"
	@echo ""
	@echo "Available examples: $(EXAMPLES)"
	@echo ""
	@echo "Note: datascience-compatibility requires 'make install-datascience' first"
	@echo "      datascience-wasi uses WASI wheels with 'make setup-wasi-wheels'"

.PHONY: all serve test list-examples build-all clean lint lint-fix format format-check install-datascience serve-datascience setup-wasi-wheels serve-datascience-wasi help

