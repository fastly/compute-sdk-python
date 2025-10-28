# Fastly Compute Python Examples

This directory contains example applications demonstrating different approaches to building Fastly Compute services with Python.

## Available Examples

### `bottle-app.py`
- **Framework**: Bottle (lightweight WSGI framework)
- **Features**: Basic routing, JSON responses, WIT API integration
- **Use Case**: Simple services, proof-of-concept applications

### `flask-app.py`
- **Framework**: Flask (popular Python web framework)
- **Features**: Flask routing, request handling, error handling
- **Use Case**: More complex applications, familiar Flask patterns

### `game-of-life.py`
A server-side implementation of Conway’s Game of Life, with a server round trip per frame. This demonstrates raw requests-per-second performance.

## Building and Running Examples

### Build a Specific Example
```bash
make build/flask-app.wasm     # Build Flask example
make build/bottle-app.wasm    # Build Bottle example
make build/game-of-life.wasm  # Build Conway's Game of Life example
```

### Serve an Example
```bash
make serve                    # Serve default (bottle-app)
make serve EXAMPLE=flask-app  # Serve Flask example
```

### Build All Examples
```bash
make build-all
```

### List Available Examples
```bash
make list-examples
```

## Testing Examples

The integration tests use the default example (bottle-app). To test other examples:

```bash
# Update the test to use a different example
EXAMPLE=flask-app make test
```

## Creating New Examples

1. Create a new `.py` file in this directory
2. Implement your WSGI application
3. Include the `serve_wsgi_request` function and `HttpIncoming` class
4. Build with `make build/your-example.wasm`
5. Test with `make serve EXAMPLE=your-example`

## Framework Requirements

All examples must:
- Be WSGI-compatible applications
- Include the WIT integration boilerplate (`serve_wsgi_request`, `HttpIncoming`)
- Handle the standard test endpoints for integration tests:
  - `/hello/<name>` - Returns "Hello {name}!"
  - `/info` - Returns JSON with service info and WIT data
  - `/error` - Raises an exception for error testing

## Dependencies

Examples may use different web frameworks, but they all rely on:
- `wit_world` - Generated WIT bindings
- `componentize-py` - Python to WebAssembly compilation
- Framework-specific dependencies (bottle, flask, etc.)