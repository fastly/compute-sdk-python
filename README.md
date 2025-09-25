# Fastly Compute Python SDK

Experimental Python SDK for [Fastly Compute](https://www.fastly.com/products/edge-compute) services.

## Features

- **Multiple Framework Support**: Examples with Bottle, Flask, and more
- **WIT Bindings**: Auto-generated Python bindings from Fastly's WIT files
- **WSGI Compatibility**: Host any WSGI-compatible web framework
- **Testing Framework**: Comprehensive viceroy-based integration testing
- **Type Safety**: Full type hints and IDE support

## Quick Start

### Build and Run
```bash
make serve                    # Serve default example (Bottle)
make serve EXAMPLE=flask-app  # Serve Flask example
```

Visit http://127.0.0.1:7676/hello/world or http://127.0.0.1:7676/info

### Available Examples

```bash
make list-examples           # List all examples
make build-all              # Build all examples
```

### Testing
```bash
make test                   # Run integration tests
```

## Development

### Code Quality
```bash
make format         # Format code
make lint           # Run linter
make lint-fix       # Auto-fix linting issues
```

### Building Examples
```bash
make build/my-app.wasm      # Build specific example
make clean                  # Clean build artifacts
```

## Status

Currently demonstrates:
- Building pure Python into WebAssembly components
- Creating Python bindings from Fastly's WIT files
- Hosting web frameworks by adapting Fastly's API to WSGI
- Comprehensive testing with viceroy integration

## Caveats

- Any native Python modules need to be compiled against WASI. Few are at the
  moment. However, [Joel has done
  some](https://github.com/dicej/wasi-wheels/releases/), and the changes needed
  aren't extensive.

## Prerequisites

1. [Install `uv`](https://docs.astral.sh/uv/getting-started/installation/)
2. Install [Viceroy](https://github.com/fastly/Viceroy) with component support
