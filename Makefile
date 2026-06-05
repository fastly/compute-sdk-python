# Fastly Compute Python SDK

# Default Viceroy location. Set VICEROY env var to change.
VICEROY ?= viceroy

# Build tool configuration
# For development: Use cargo run (always up-to-date, no install needed)
# For production: Use installed binary via `uv run fastly-compute-py`
DEV_MODE ?= 1

# Rust crate path
FASTLY_COMPUTE_PY_MANIFEST := $(abspath crates/fastly-compute-py/Cargo.toml)

# Select build tool based on DEV_MODE
ifeq ($(DEV_MODE),1)
    # Development mode: use cargo run (always current)
    FASTLY_COMPUTE_PY := uv run cargo run --release --manifest-path $(FASTLY_COMPUTE_PY_MANIFEST) --no-default-features --features binary --
else
    # Production mode: use installed Python entry point
    FASTLY_COMPUTE_PY := uv run fastly-compute-py
endif

# Configuration
STUBS_DIR := fastly_compute/testing/stubs
BUILD_DIR := build
EXAMPLES_DIR := examples
COMPUTE_WIT := wit/deps/fastly/compute.wit

# Define all available examples (add new ones here)
EXAMPLES := bottle-app flask-app backend-requests game-of-life

# Default example for serve target
EXAMPLE ?= bottle-app
WASM_FILE := $(BUILD_DIR)/$(EXAMPLE).composed.wasm

TARGET_WORLD := fastly:compute/service@0.1.0

VICEROY ?= viceroy

# Generate WASM file paths for all examples
EXAMPLE_WASMS := $(foreach example,$(EXAMPLES),$(BUILD_DIR)/$(example).wasm)

# Composed wasm for each example
COMPOSED_WASMS := $(foreach example,$(EXAMPLES),$(BUILD_DIR)/$(example).composed.wasm)

# Default target builds all examples
all: $(COMPOSED_WASMS)

$(STUBS_DIR): $(COMPUTE_WIT)
	rm -rf $(STUBS_DIR)
	$(FASTLY_COMPUTE_PY) bindings -d wit -w $(TARGET_WORLD) --world-module wit_world $(STUBS_DIR)

# Build our composed wasm using fastly-compute-py build
$(BUILD_DIR)/%.composed.wasm: wit/viceroy.wit wit/deps/fastly/compute.wit fastly_compute/wsgi.py fastly_compute/runtime_patching/patches.py | $(BUILD_DIR) $(STUBS_DIR)
	@echo "Building $* example with fastly-compute-py..."
	@test -d $(EXAMPLES_DIR)/$* || (echo "Error: Example directory $(EXAMPLES_DIR)/$* not found" && exit 1)
	cd $(EXAMPLES_DIR)/$* && $(FASTLY_COMPUTE_PY) build --output ../../$@

# The script that writes the exceptions and the patches always rewrites
# everything, so we can depend on the mod date of only 1 file. We choose
# patches.py, because its name doesn't depend on the WIT contents.
fastly_compute/runtime_patching/patches.py: scripts/generate_patches/*.py $(shell find scripts/generate_patches/templates -name "*.jinja") $(COMPUTE_WIT)
	uv run python -m scripts.generate_patches

# Create build directory
$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

# Serve the specified example (default: bottle-app)
serve: $(WASM_FILE)
	@echo "Serving $(EXAMPLE) example on http://127.0.0.1:7676"
	$(VICEROY) serve $(WASM_FILE)

# Test all examples (requires all WASM files to be built)
test: $(COMPOSED_WASMS)
	VICEROY=$(VICEROY) FASTLY_COMPUTE_PY="$(FASTLY_COMPUTE_PY)" uv run --extra test pytest

# Update snapshots for snapshot tests
test-update-snapshots: $(COMPOSED_WASMS)
	VICEROY=$(VICEROY) FASTLY_COMPUTE_PY="$(FASTLY_COMPUTE_PY)" uv run --extra test pytest --snapshot-update

# List available examples
list-examples:
	@echo "Available examples:"
	@for example in $(EXAMPLES); do echo "  $$example"; done

# Clean build artifacts
clean:
	rm -rf $(BUILD_DIR) $(STUBS_DIR)
	rm -f fastly_compute/runtime_patching/patches.py
	cd fastly_compute/exceptions && rm -rf acl http_body http_req kv_store types
	cd crates/fastly-compute-py && cargo clean

# Development tools
lint: fastly_compute/runtime_patching/patches.py | $(STUBS_DIR)
	@echo "Checking version synchronization..."
	uv run python scripts/check_version_sync.py
	@echo "Linting Python code..."
	uv run --extra dev --extra test --extra examples ruff check .
	uv run --extra dev --extra test pyrefly check
	@echo "Linting Rust code..."
	cd crates/fastly-compute-py && cargo clippy --release --no-default-features --features binary -- -D warnings

lint-fix: fastly_compute/runtime_patching/patches.py
	@echo "Fixing Python code..."
	uv run --extra dev ruff check --fix .
	@echo "Fixing Rust code..."
	cd crates/fastly-compute-py && cargo clippy --release --no-default-features --features binary --fix --allow-dirty --allow-staged

format:
	@echo "Formatting Python code..."
	uv run --extra dev ruff format .
	@echo "Formatting Rust code..."
	cd crates/fastly-compute-py && cargo fmt

format-check:
	@echo "Checking Python formatting..."
	uv run --extra dev ruff format --check .
	@echo "Checking Rust formatting..."
	cd crates/fastly-compute-py && cargo fmt --check

# Bump version numbers across the project for a new release
bump-version:
	@test -n "$(VERSION)" || (echo "Error: VERSION is required. Example: make bump-version VERSION=0.2.0" && exit 1)
	uv run python scripts/bump_version.py $(VERSION)
	$(MAKE) lint

# Help target
help:
	@echo "Fastly Compute Python SDK"
	@echo ""
	@echo "Build Tool Mode:"
	@echo "  DEV_MODE=1 (default): Uses 'cargo run' - always current, no install needed"
	@echo "  DEV_MODE=0:           Uses installed 'fastly-compute-py' Python entry point"
	@echo ""
	@echo "Targets:"
	@echo "  all                     Build all examples"
	@echo "  serve [EXAMPLE=name]    Serve example (default: $(EXAMPLE))"
	@echo "  test                    Run integration tests (builds all examples)"
	@echo "  test-update-snapshots   Update snapshot test baselines"
	@echo "  bump-version VERSION=vX.Y.Z Bump version across pyproject.toml and Cargo.toml"
	@echo "  build-all               Build all examples (alias for 'all')"
	@echo "  list-examples           List available examples"
	@echo "  clean                   Clean all build artifacts (including Rust)"
	@echo "  lint                    Run linter (Python + Rust)"
	@echo "  lint-fix                Run linter with auto-fix (Python + Rust)"
	@echo "  format                  Format code (Python + Rust)"
	@echo "  format-check            Check code formatting (Python + Rust)"
	@echo ""
	@echo "Development Workflow:"
	@echo "  The build tool is invoked via 'cargo run' by default (DEV_MODE=1)."
	@echo "  Changes to Rust code are automatically picked up on next build."
	@echo "  No need to explicitly rebuild the tool!"
	@echo ""
	@echo "  To use the installed Python entry point instead:"
	@echo "    make DEV_MODE=0           # Build with installed fastly-compute-py"
	@echo ""
	@echo "Examples:"
	@echo "  make                          # Build all examples"
	@echo "  make serve                    # Serve bottle-app example"
	@echo "  make serve EXAMPLE=flask-app  # Serve flask-app example"
	@echo "  make build/flask-app.wasm     # Build specific example"
	@echo ""
	@echo "Available examples: $(EXAMPLES)"

.PHONY: all serve test test-update-snapshots list-examples build-all clean lint lint-fix format format-check help bump-version
