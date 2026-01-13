# Developer Tooling Design

## Overview

Design for the build chain and tooling required to convert Python applications into Fastly Compute WebAssembly components.

## Goals

1.  **Zero-Config Defaults**: Works out of the box for standard structures.
2.  **Fastly CLI Integration**: integrates seamlessly with `fastly compute build`.
3.  **Single Binary**: Distributed as a standalone tool to minimize environment dependency issues.
4.  **Performance**: Optimizes build time.

## The `fastly-py` Tool

We will provide a Rust-based CLI tool named **`fastly-py`**.

### Architecture

- **Language**: Rust
- **Distribution**: Standalone binary (via cargo install or downloadable releases).
- **Core Responsibility**: Orchestrate the build process by embedding or managing necessary sub-tools like `componentize-py` and `wac`.

### Build Process (`fastly-py build`)

1.  **Discovery**: Analyze the project structure (`pyproject.toml`).
2.  **Environment Prep**: Ensure a suitable Python environment is available. The tool will check for `uv` managed environments as the preferred path.
3.  **Componentization**: 
    - Executes the componentization logic (wrapping `componentize-py`).
    - Uses the `fastly:compute/service` WIT world.
    - bundles necessary WIT files automatically.
4.  **Composition**: 
    - Automatically composes the result with the `wasiless.wasm` adapter (embedded in the binary).
5.  **Output**: Generates the final Wasm artifact (default: `bin/main.wasm`).

### CLI Arguments

```text
usage: fastly-py build [options] [entrypoint]

positional arguments:
  entrypoint            Entry point module/file (default: main.py or app.py)

options:
  -o, --output FILE     Output Wasm file (default: bin/main.wasm)
  -v, --verbose         Verbose output
```

## Moving Parts Strategy

1.  **`componentize-py`**: The Rust binary will manage the execution of componentization. It may bundle the python parts or manage a dedicated venv to ensure the correct version is used.
2.  **`wasiless.wasm`**: This adapter will be embedded directly into the `fastly-py` Rust binary (using `include_bytes!`), eliminating the need for external file dependencies.
3.  **WIT Definitions**: The authoritative `compute.wit` will also be embedded in the binary.

## Implementation Plan

1.  **Project Location**: `src/fastly-py` (or similar) in the repo.
2.  **Dependencies**:
    - `clap`: For CLI argument parsing.
    - `anyhow`: For error handling.
    - `wac` (library): Use the `wac` crate directly if available, or bundle the binary.
3.  **Embedding**: Use Rust's `include_bytes!` macro to compile static assets (adapter, WITs) into the binary.

## Advantages of Rust-based Tool

- **Portability**: Single binary, easier to distribute via Fastly CLI or CI/CD.
- **Robustness**: Static typing and better error handling for the build orchestration.
- **Speed**: Startup time is negligible; heavy lifting is still done by the Wasm engine but the driver is fast.
- **Isolation**: Can shield the user from dependency conflicts by managing the build environment explicitly.
