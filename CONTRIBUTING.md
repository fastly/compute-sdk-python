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
4. **wasm32-unknown-unknown Rust target** (required by build.rs)
   ```bash
   rustup target add wasm32-unknown-unknown
   ```

5. **[wasm-tools](https://github.com/bytecodealliance/wasm-tools)** (required by build.rs for WIT merging and componentization)
6. **[Viceroy](https://github.com/fastly/Viceroy/releases)** - Fastly's local testing server

## Development Workflow

The `fastly-compute-py` build tool is written in Rust. By default, the Makefile uses `cargo run` (DEV_MODE=1), which means:
- **No installation needed** for testing or use against examples; the tool runs directly via cargo
- **Always up-to-date.** Changes to Rust code are automatically picked up.
- **Fast incremental builds.** Cargo handles recompilation efficiently.

To work on the build tool, edit the Rust code in `crates/fastly-compute-py/`, then run `make` to build it.

### Making Changes to the Build Tool

The build tool is written in Rust and lives in `crates/fastly-compute-py/`. After you make changes, the Makefile automatically rebuilds via `cargo run` when you build an example service, like this:

```bash
make build/bottle-app.composed.wasm
```

You can also test the installed entry point, which lets Python code call the build tool:

```bash
make DEV_MODE=0 build/bottle-app.composed.wasm
```

### Code Quality

These will spruce up spelling in both Python and Rust code:

```bash
make format          # Format code
make format-check    # Check formatting
make lint            # Run linters
make lint-fix        # Auto-fix linting issues
```

### Testing

The SDK has comprehensive tests, with integration tests running via Viceroy:

```bash
make test                     # Run all tests
make test-update-snapshots    # Update snapshot tests
```

## Project Structure

```
.
├── crates/
│   ├── fastly-compute-py/   # Rust build tool
│   │   ├── build.rs         # Build script (requires wasm-tools)
│   │   └── src/
│   └── wasiless/            # Wasm component for WASI stubbing
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

1. **build.rs** (during Rust compilation)...
   - Calls `wasm-tools component wit` to merge WIT files
   - Builds `wasiless` crate for wasm32-unknown-unknown
   - Calls `wasm-tools component new` to componentize wasiless

2. **fastly-compute-py**...
   - Resolves Python dependencies from virtualenv
   - Calls `componentize-py` to build Python Wasm component
   - Composes with wasiless using `wac`

## Continuous Integration

The CI workflow (`.github/workflows/python-ci.yml`) validates formatting,
linting, and tests on every push and pull request. The release workflow
(`.github/workflows/release.yml`) builds binary wheels for all supported
platforms (`Linux x86_64/aarch64`, `macOS x86_64/aarch64`) and attaches them
to a GitHub pre-release.

## Performing a Release

Releases are driven by a git tag. The release workflow builds binary wheels
and attaches them to a GitHub pre-release for validation before PyPI publishing.

The version must be kept in sync across two files:
- `pyproject.toml` — `[project] version`
- `crates/fastly-compute-py/Cargo.toml` — `[package] version`

`make lint` checks these are in sync.

### Steps

1. Bump `version` in both files above to the new version (e.g. `0.2.0`).

2. Verify locally:
   ```bash
   make lint
   ```

3. PR the changes and land into main.

4. Push tag (make sure you are on the right sha first)
   ```
   git tag v0.2.0
   git push origin v0.2.0
   ```
   
4. The release workflow runs automatically. Jobs: `check-version` (fails fast
   on any mismatch) → parallel wheel + sdist builds → `collect-artifacts` →
   `create-github-release`.

5. (Pending) If the release is built successfully, it will make its way to PyPI
   via trusted publishing.

