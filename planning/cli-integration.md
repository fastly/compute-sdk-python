# Fastly CLI Integration Design

## Overview

Design for integrating the Python SDK with the Fastly CLI (`fastly compute ...`).

## CLI Tool: `fastly-compute-py`

The Python SDK includes a CLI tool named `fastly-compute-py` that handles building Python applications into WebAssembly modules compatible with Fastly Compute.

The build tool is **bundled into the `fastly-compute` package** rather than distributed separately:
- **`fastly-compute`**: The Python SDK library with embedded Rust build tool
- **`fastly-compute-py`** (optional): Also available as a standalone binary via crates.io for Rust users

### Why Bundle the Build Tool?

1. **WIT Definition Alignment**: The build tool requires WIT definitions that exactly match the SDK version. Bundling ensures they stay in sync.
2. **Prevents Version Mismatches**: Users cannot accidentally use incompatible SDK/build-tool versions (e.g., SDK 0.7.0 with build tool 0.6.0).
3. **Simpler User Experience**: One `uv add fastly-compute` provides everything needed to build and run Fastly Compute applications.
4. **Shared Version Control**: SDK features and build tool capabilities are versioned together in lockstep.

This bundling strategy:
- Eliminates version mismatch footguns
- Ensures WIT definitions always match the SDK
- Simplifies dependency management
- Works seamlessly in virtual environments

### Installation & Usage

The build tool is automatically included when you install the SDK:

```bash
uv add fastly-compute
```

Projects invoke the tool via `uv run` scripts defined in `pyproject.toml`:

```bash
uv run build
```

### Commands

- `fastly-compute-py build` - Build the Python application into a WASM module
- `fastly-compute-py version` - Display version information

## `fastly.toml` Configuration

The `fastly.toml` file is the manifest for Compute services.

```toml
manifest_version = 4
service_id = "..."
name = "my-python-service"
language = "python"

[scripts]
build = "uv run build"
post_init = "uv sync"
```

## `pyproject.toml` Configuration

A typical Flask-based Fastly Compute project's `pyproject.toml`:

```toml
[project]
name = "my-python-service"
version = "0.1.0"
description = "A Fastly Compute service built with Python"
requires-python = ">=3.12"
dependencies = [
    "fastly-compute>=0.1.0",
    "flask>=3.0.0",
]

[dependency-groups]
dev = [
    "fastly-compute-py>=0.1.0",
]

[tool.uv.scripts]
build = "fastly-compute-py build"
```

Key elements:
- **requires-python**: We embed 3.14 currently but 3.12+ is more likely to be available on host systems.
- **dependencies**: Just `fastly-compute` - the build tool is included
- **tool.uv.scripts**: Simple script that invokes the bundled build tool
- **No [build-system]**: Not needed since we're building to WASM, not distributing as a Python package

### How It Works

The `fastly-compute` package includes:
- Python SDK runtime code (`fastly_compute/`)
- Rust-based build tool (via PyO3 extension module)
- WIT definitions (embedded in the build tool)
- CLI entry point (`fastly-compute-py` command)

When you run `uv run build`, it invokes the `fastly-compute-py` command which is provided by the `fastly-compute` package you've already installed.

### Developer Workflow

```bash
# Sync dependencies
uv sync

# Build the WASM module
uv run build
```

## Project Structure

A standard Python Compute project structure (using `uv`):

```text
.
├── fastly.toml
├── pyproject.toml
├── uv.lock
├── src/
│   └── main.py
└── README.md
```

## Starter Kits

Fastly provides [Starter Kits](https://www.fastly.com/documentation/solutions/starters/) to help developers get up and running quickly. For the Python SDK alpha, we will provide a limited set of high-quality starters.

### Proposed Alpha Starters

1.  **Python Default (WSGI/Flask)**
    - **Repo**: `fastly/compute-starter-kit-python-flask` (Proposed)
    - **Focus**: The "paved path" for most developers. Uses Flask to demonstrate compatibility with standard Python web frameworks.
    - **Features**: Routing, JSON handling, Middleware.

2.  **Python Raw (No Framework)**
    - **Repo**: `fastly/compute-starter-kit-python-raw` (Proposed)
    - **Focus**: Minimalist example using the SDK's `Request` and `Response` objects directly.
    - **Features**: Low-level control, maximum performance, zero dependencies (other than SDK).

### Template Structure

Each starter kit should follow the standard structure:

```text
.
├── fastly.toml
├── pyproject.toml
├── src/
│   └── main.py
└── README.md
```

## Dependency Management

The "paved path" for dependency management is **`uv`** with `pyproject.toml`.  Nothing would preclude customers from using other tooling (e.g. pip, etc.) but `uv` now has wide adoption and seems reasonable to have it be what is documented as the paved path.

### Option 1: Manual Initialization

```bash
# Initialize a new project
uv init my-python-service
cd my-python-service

# Add the Fastly Compute SDK (includes build tool)
uv add fastly-compute flask

# Add uv script to pyproject.toml (or do this manually)
cat >> pyproject.toml <<EOF

[tool.uv.scripts]
build = "fastly-compute-py build"
EOF

# Create your application in src/main.py
# ...

# Build using the convenient script
uv run build
```

### Option 2: Template-Based Initialization (Recommended)

Using a Fastly starter kit (e.g., WSGI/Flask template):

```bash
# Initialize from template
fastly compute init --from=https://github.com/fastly/compute-starter-kit-python-flask

# Dependencies are already configured in pyproject.toml
# Sync all dependencies
uv sync

# Build using the convenient script
uv run build
```

The template approach provides:
- Pre-configured `fastly.toml` and `pyproject.toml` with `[tool.uv.scripts]`
- Build tool included via `fastly-compute` dependency
- Working example application code
- Proper project structure
- Common patterns and best practices


## Implementation Notes

1.  **Bundled Build Tool**: The build tool is bundled into the `fastly-compute` package, ensuring WIT definitions and SDK are always version-aligned and preventing version mismatch bugs.
2.  **Single Package Installation**: Users install just `fastly-compute` and get both the SDK and build tool.
3.  **Script-Based Invocation**: Projects use `[tool.uv.scripts]` to define `build` commands, invoked via `uv run build`. This is referenced in `fastly.toml` for Fastly CLI integration.
4.  **Language Support**: Python support (`language = "python"`) will be added to the Fastly CLI before alpha release.
5.  **Viceroy Compatibility**: Viceroy (downloaded automatically by the Fastly CLI from the Viceroy releases repository) already supports components 0.0.0+, ensuring compatibility with our WASM output.
6.  **Build Output**: `fastly-compute-py build` should output to `bin/main.wasm` by default to match Fastly CLI conventions.
7.  **Dual Distribution**: The build tool is also available standalone via crates.io (`cargo install fastly-compute-py`) for Rust users or non-Python build environments.
