# Fastly Compute Python Examples

This directory contains small examples of Fastly Compute services built with Python.

## Available Examples

### `bottle-app`
- **Framework**: Bottle (lightweight WSGI framework)
- **Demonstrates**: Basic routing, JSON responses, WIT API integration
- **Use Case**: Simple services, proof-of-concept applications

### `flask-app`
- **Framework**: Flask (popular Python web framework)
- **Demonstrates**: Flask routing, request handling, error handling
- **Use Case**: More complex applications, familiar Flask patterns

### `game-of-life`
- **Shows**: A server-side implementation of Conway’s Game of Life, with a server round trip per frame.
- **Demonstrates**: Raw requests-per-second performance; Fastly's session-reuse
feature, which saves spin-up time in busy services

### `backend-requests`
This is actually a piece of the test harness; please ignore it.

## Building and Running Examples

Before you use `make`, please [install the prerequisites](https://github.com/fastly/compute-sdk-python/blob/main/CONTRIBUTING.md#prerequisites).

### Hello World in Flask or Bottle
```bash
make serve                       # Serve default example (Bottle)
make serve EXAMPLE=flask-app     # Serve Flask example
```

Visit http://127.0.0.1:7676/hello/world or http://127.0.0.1:7676/info.

### Conway's Game of Life
```bash
make serve EXAMPLE=game-of-life  # Serve Conway's Game of Life example
```

Visit http://127.0.0.1:7676/.

### Other Invocations

```bash
make list-examples            # List all examples
make build-all                # Build all examples
```  
