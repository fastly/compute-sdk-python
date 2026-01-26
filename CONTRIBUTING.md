# Contributing to Fastly Compute Python SDK

Thank you for your interest in contributing! This guide will help you get set up for development.

## Prerequisites

### Required Tools

The build process requires several tools to be installed:

1. **Python 3.12+**
   ```bash
   python --version  # Should be 3.12 or higher
   ```

2. **uv** - Python package manager
3. **Rust toolchain** (stable)
4. **wasm32-unknown-unknown target** (required by build.rs)
   ```bash
   rustup target add wasm32-unknown-unknown
   ```

5. **wasm-tools** (required by build.rs for WIT merging and componentization)
6. **Viceroy** - Fastly's local testing server

## Getting Started

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd compute-sdk-python/build-tool-impl
   ```

2. **Initialize submodules** (if applicable)
   ```bash
   git submodule update --init --recursive
   ```

3. **Install Python dependencies**
   ```bash
   uv sync --extra dev --extra test
   ```

4. **Verify setup**
   ```bash
   make help  # Should show available commands
   ```

## Development Workflow

### Building Examples

The default development workflow uses `cargo run` which automatically picks up Rust changes:

```bash
# Build an example
make build/bottle-app.composed.wasm

# Build all examples
make

# Serve an example for testing
make serve EXAMPLE=bottle-app
```

### Making Changes to the Build Tool

The build tool is in `crates/fastly-compute-py/`. When you make changes:

```bash
# The build system automatically rebuilds via `cargo run`
make build/bottle-app.composed.wasm

# Or test the installed entry point
make DEV_MODE=0 build/bottle-app.composed.wasm
```

### Code Quality

```bash
# Format code (Python + Rust)
make format

# Check formatting
make format-check

# Run linters (Python + Rust)
make lint

# Auto-fix linting issues
make lint-fix
```

### Testing

```bash
# Run all tests
make test

# Update snapshot tests
make test-update-snapshots
```

## Project Structure

```
.
├── crates/
│   ├── fastly-compute-py/   # Rust build tool
│   │   ├── build.rs         # Build script (requires wasm-tools)
│   │   └── src/
│   └── wasiless/            # WASM component for WASI removal
├── examples/                 # Example applications
│   ├── bottle-app/
│   ├── flask-app/
│   └── ...
├── fastly_compute/          # Python SDK
├── wit/                     # WIT (WebAssembly Interface Type) definitions
└── tests/                   # Integration tests
```

## Build Process

Understanding the build process helps when debugging issues:

1. **build.rs runs** (during Rust compilation):
   - Calls `wasm-tools component wit` to merge WIT files
   - Builds `wasiless` crate for wasm32-unknown-unknown
   - Calls `wasm-tools component new` to componentize wasiless

2. **fastly-compute-py runs**:
   - Resolves Python dependencies from virtualenv
   - Calls `componentize-py` to build Python WASM component
   - Composes with wasiless using WAC

## Continuous Integration

Our CI builds wheels for multiple platforms:
- Linux: x86_64, aarch64
- macOS: x86_64 (Intel), aarch64 (Apple Silicon)
- Windows: x86_64

The CI workflow (`.github/workflows/build-wheels.yml`) ensures all required tools are installed automatically.
