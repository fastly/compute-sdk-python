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

The CI workflow (`.github/workflows/python-ci.yml`) validates formatting,
linting, and tests on every push and pull request. The release workflow
(`.github/workflows/release.yml`) builds binary wheels for all supported
platforms (Linux x86_64/aarch64, macOS x86_64/aarch64, Windows x86_64)
and attaches them to a GitHub pre-release.

## Performing a Release

Releases are driven by a git tag. The release workflow builds binary wheels
and attaches them to a GitHub pre-release for validation before PyPI publishing.

The version must be kept in sync across two files:
- `pyproject.toml` — `[project] version`
- `crates/fastly-compute-py/Cargo.toml` — `[package] version`

`make lint` checks these are in sync. To also validate against a specific tag:

```bash
make check-version-tag TAG=v0.2.0
```

### Steps

1. Bump `version` in both files above to the new version (e.g. `0.2.0`).

2. Verify locally:
   ```bash
   make check-version-tag TAG=v0.2.0
   ```

3. Commit and tag:
   ```bash
   git add pyproject.toml crates/fastly-compute-py/Cargo.toml
   git commit -m "Bump version to 0.2.0"
   git tag v0.2.0
   git push origin v0.2.0
   ```

4. The release workflow runs automatically. Jobs: `check-version` (fails fast
   on any mismatch) → parallel wheel builds → `collect-wheels` →
   `create-github-release`.

5. Install a wheel from the GitHub Release to validate before promoting to PyPI:
   ```bash
   pip install https://github.com/fastly/compute-sdk-python/releases/download/v0.2.0/<wheel-filename>.whl
   ```

6. Promote to PyPI once validated (via trusted publishing, configured separately).

### Ad-hoc test builds

To build wheels without tagging, trigger the workflow manually from
**Actions → Release → Run workflow** with a version label (e.g. `v0.2.0-rc1`).
Wheels are uploaded as Actions artifacts; no release is created. The in-tree
versions must still match the label you provide.

### If the version check fails

Fix the mismatch, then retag:
```bash
git tag -f v0.2.0
git push --force origin v0.2.0
```


