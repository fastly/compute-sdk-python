# Developer Tooling Design

## Overview

Design for the build chain and tooling required to convert Python applications into Fastly Compute WebAssembly components.

## Goals

1.  **Zero-Config Defaults**: Works out of the box for standard structures.
2.  **Fastly CLI Integration**: integrates seamlessly with `fastly compute build`.
3.  **Python-Native Distribution**: Published on PyPI for easy installation via standard Python tooling.
4.  **Performance**: Optimizes build time.
5.  **Dual Distribution**: Support both PyPI (Python users) and crates.io (Rust users) from the same codebase.

## Package Architecture

The build tool will be implemented as a Rust library with dual distribution:

- **`fastly-compute`** (PyPI): Python SDK with embedded Rust build tool
- **`fastly-compute-py`** (crates.io): Standalone Rust binary for non-Python users

### Rationale for Bundling

The build tool is bundled into the SDK package rather than distributed separately because:

1. **WIT Definition Alignment**: The build tool needs WIT definitions that exactly match the SDK version. Bundling ensures they stay in sync.
2. **Prevents Version Mismatches**: Users cannot accidentally use incompatible SDK/build-tool versions (e.g., SDK 0.7.0 with build tool 0.6.0).
3. **Simpler User Experience**: "Fewer Things" - one package provides everything needed to build and run Fastly Compute applications.
4. **Shared Version Control**: SDK features and build tool capabilities can be versioned together in lockstep.

## Project Structure

```
compute-sdk-python/
├── Cargo.toml                    # Rust workspace root
├── pyproject.toml                # Python package configuration (maturin)
├── fastly_compute/               # Python SDK source
│   ├── cli.py                    # NEW: CLI entry point
│   └── ...
├── crates/                       # Rust source
│   ├── fastly-compute-py/        # Build tool crate
│   └── wasiless/                 # MOVED from vendor/wasiless
└── wit/                          # WIT definitions
```

### Key Changes to Directory Structure

1. **New `Cargo.toml` at root**: Rust workspace configuration
2. **New `crates/` directory**: Contains all Rust crates
3. **`crates/fastly-compute-py/`**: Build tool implementation
4. **Move `vendor/wasiless` → `crates/wasiless`**: Treat as a workspace member
5. **New `fastly_compute/cli.py`**: Python entry point for the CLI

## The `fastly-compute-py` Tool

We will provide a Rust-based CLI tool named **`fastly-compute-py`**, bundled into the `fastly-compute` Python package.

### Package Structure

- **`fastly-compute`** (PyPI): The Python SDK library with embedded Rust build tool
  - Includes platform-specific wheels with pre-compiled Rust binaries
  - Provides `fastly-compute-py` command-line tool
  - Contains WIT definitions matching the SDK version

- **`fastly-compute-py`** (crates.io, optional): Standalone Rust binary
  - For Rust developers or non-Python build environments
  - Shares the same core implementation with the PyPI distribution

This bundling provides:
- WIT definitions always match the SDK version
- No version mismatch footguns
- Single `uv add fastly-compute` installs everything
- Clear distinction between runtime and build-time code

### Architecture

- **Language**: Rust (compiled to Python wheels with embedded binaries via PyO3)
- **Distribution**: Published on PyPI as part of `fastly-compute`, optionally on crates.io
- **Invocation**: Via `uv run build` (using `[tool.uv.scripts]` in `pyproject.toml`)
- **Core Responsibility**: Orchestrate the build process by embedding or managing necessary sub-tools like `componentize-py` and `wac`.

### Rust Crate Design

**crates/fastly-compute-py/Cargo.toml:**
```toml
[package]
name = "fastly-compute-py"

[lib]
crate-type = ["cdylib", "rlib"]

[[bin]]
name = "fastly-compute-py"
path = "src/main.rs"

[dependencies.pyo3]
version = "0.27.2"
features = ["extension-module"]
optional = true

[features]
python = ["pyo3"]
```

**src/lib.rs:**
```rust
pub fn build_component(entry: &str, output: &str) -> Result<(), Error> {
    // Build logic: componentize-py, wac composition, etc.
}

#[cfg(feature = "python")]
use pyo3::prelude::*;

#[cfg(feature = "python")]
#[pyfunction]
fn build(entry: String, output: String) -> PyResult<()> {
    build_component(&entry, &output)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
}

#[cfg(feature = "python")]
#[pymodule]
fn _fastly_compute_py(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(build, m)?)?;
    Ok(())
}
```

**src/main.rs:**
```rust
use clap::Parser;

#[derive(Parser)]
#[command(name = "fastly-compute-py")]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    Build {
        #[arg(short, long, default_value = "bin/main.wasm")]
        output: String,
        #[arg(short, long)]
        verbose: bool,
    },
}

fn main() {
    let cli = Cli::parse();
    match cli.command {
        Command::Build { output, verbose } => {
            fastly_compute_py::build_component("main.py", &output).unwrap();
        }
    }
}
```

### Python CLI Wrapper

**fastly_compute/cli.py:**
```python
"""Thin wrapper that delegates to Rust CLI."""
import sys
import subprocess

def main():
    # Just exec the Rust binary directly
    from fastly_compute._fastly_compute_py import __file__ as lib_path
    import os
    binary = os.path.join(os.path.dirname(lib_path), "fastly-compute-py")
    if sys.platform == "win32":
        binary += ".exe"
    
    result = subprocess.run([binary] + sys.argv[1:])
    sys.exit(result.returncode)
```

### Workspace Configuration

**Root Cargo.toml:**
```toml
[workspace]
members = ["crates/fastly-compute-py", "crates/wasiless"]
resolver = "2"
```

**Root pyproject.toml:**
```toml
[build-system]
requires = ["maturin>=1.0"]
build-backend = "maturin"

[project.scripts]
fastly-compute-py = "fastly_compute.cli:main"

[tool.maturin]
python-source = "."
manifest-path = "crates/fastly-compute-py/Cargo.toml"
features = ["python"]
module-name = "fastly_compute._fastly_compute_py"
```

### Build Process

1.  **Discovery**: Analyze `pyproject.toml`
2.  **Componentization**: Use `componentize-py` with embedded WIT
3.  **Composition**: Compose with embedded `wasiless.wasm` via `wac`
4.  **Output**: Write to `bin/main.wasm` (default)

### CLI Arguments

```
fastly-compute-py build [--output FILE] [--verbose]
```

## Distribution Strategy

**Usage:**
```bash
uv add fastly-compute  # Installs SDK + build tool
uv run build           # Invokes fastly-compute-py
```

**Building wheels:**
```bash
maturin develop --features python
maturin build --release --features python
```

**Publishing standalone binary:**
```bash
cd crates/fastly-compute-py
cargo publish
cargo install fastly-compute-py
```

## Implementation Plan

1.  **Move wasiless**: `vendor/wasiless` → `crates/wasiless`
2.  **Create `crates/fastly-compute-py/`** with Rust CLI
3.  **Embed assets**: WIT definitions, `wasiless.wasm` via `include_bytes!`
4.  **Maturin setup**: Configure for platform-specific wheels with PyO3
5.  **CI/CD**: GitHub Actions for multi-platform wheel builds

## Advantages of This Approach

- **Version Alignment**: Build tool and SDK WIT definitions are always in sync, preventing runtime errors from version mismatches.
- **Single Package**: Users install one package (`fastly-compute`) and get everything needed.
- **Dual Distribution**: Same codebase supports both PyPI (Python users) and crates.io (Rust users).
- **Simple Invocation**: `uv run build` is concise and integrates with `fastly.toml`.
- **Portability**: Platform-specific wheels ensure the tool works across different operating systems.
- **Robustness**: Static typing and better error handling for the build orchestration (via Rust).
- **Speed**: Native Rust performance for build orchestration.
- **Isolation**: Can shield the user from dependency conflicts by managing the build environment explicitly.
