# Fastly CLI Integration Design

## Overview

Design for integrating the Python SDK with the Fastly CLI (`fastly compute ...`).

## `fastly.toml` Configuration

The `fastly.toml` file is the manifest for Compute services.

```toml
manifest_version = 4
service_id = "..."
name = "my-python-service"
language = "other"  # Currently no native "python" support in CLI, so "other" + scripts

[scripts]
  build = "fastly-py build"
  post_init = "uv sync"

[local_server]
  # Viceroy integration
  # The SDK build tool outputs to bin/main.wasm
  bin = "bin/main.wasm"
```

## Project Structure

A standard Python Compute project structure (using `uv`):

```text
.
├── fastly.toml
├── pyproject.toml
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

The "paved path" for dependency management is **`uv`** with `pyproject.toml`.

- **Initialization**: `uv init`
- **Adding Dependencies**: `uv add fastly-compute`
- **Build**: `fastly-py build` will detect `pyproject.toml` and use `uv sync` if needed to ensure the environment is ready.


## Implementation Notes

1.  **Language Support**: Ideally, we work with the Fastly CLI team to get `language = "python"` supported natively, which would set up these defaults automatically.
2.  **Viceroy**: The `fastly compute serve` command runs Viceroy. Our build tool must ensure the artifact is compatible with the Viceroy version bundled with the CLI.
