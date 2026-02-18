# Fastly Compute SDK Tests

Tests for Fastly Compute SDK using viceroy with automatic
server management, dynamic port allocation, and comprehensive error handling.

## Quick Start

```python
import pytest
from fastly_compute.testing import ViceroyTestBase

class TestMyService(ViceroyTestBase):
    def test_endpoint(self):
        response = self.get("/test")
        assert response.status_code == 200
```

**Prerequisites**: WASM file must exist (handled by your build system).

## Available Methods

- `self.get(path, **kwargs)` - GET request
- `self.post(path, **kwargs)` - POST request  
- `self.request(method, path, **kwargs)` - Any HTTP method

## Configuration

```python
class TestMyService(ViceroyTestBase):
    REQUEST_TIMEOUT = 30        # Custom timeout (default: 10s)
    WASM_FILE = "my-service.wasm"  # Custom WASM file (default: "app.wasm")
```

## Running Tests

```bash
make test           # Build and run tests
uv run pytest -v -s # Verbose output with viceroy logs
```

### Enabling Automatic Viceroy Output

To get viceroy logs automatically displayed on test failures, add this to your `conftest.py`:

```python
pytest_plugins = ["fastly_compute.pytest_plugin"]
```

This enables automatic display of recent viceroy server output whenever a test fails, making debugging much easier.
