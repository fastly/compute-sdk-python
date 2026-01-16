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

### Build Tool Development

The `fastly-compute-py` build tool is written in Rust. By default, the Makefile uses `cargo run` (DEV_MODE=1), which means:
- **No installation needed** - the tool runs directly via cargo
- **Always up-to-date** - changes to Rust code are automatically picked up
- **Fast incremental builds** - cargo handles recompilation efficiently

Simply edit the Rust code in `crates/fastly-compute-py/` and run `make` - that's it!

**Alternative: Using the Python Entry Point**

To test the installed `fastly-compute-py` command (how end users will invoke it):
```bash
make DEV_MODE=0   # Uses `uv run fastly-compute-py` instead of `cargo run`
```

### Code Quality
```bash
make format         # Format code (Python + Rust)
make lint           # Run linter (Python + Rust)
make lint-fix       # Auto-fix linting issues (Python + Rust)
```

### Building Examples
```bash
make build/my-app.wasm      # Build specific example
make clean                  # Clean all build artifacts
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

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
