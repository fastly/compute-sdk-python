# Fastly Compute Integration Tests

Integration tests for Fastly Compute services using viceroy with automatic server management, dynamic port allocation, and comprehensive error handling.

## Quick Start

```python
import pytest
from fastly_compute.testing import ViceroyTestBase

@pytest.mark.integration
class TestMyService(ViceroyTestBase):
    def test_endpoint(self, viceroy_server):
        response = self.get("/test", viceroy_server)
        assert response.status_code == 200
```

**Prerequisites**: WASM file must exist (handled by your build system).

## Available Methods

- `self.get(path, viceroy_server, **kwargs)` - GET request
- `self.post(path, viceroy_server, **kwargs)` - POST request  
- `self.request(method, path, viceroy_server, **kwargs)` - Any HTTP method

## Configuration

```python
class TestMyService(ViceroyTestBase):
    REQUEST_TIMEOUT = 30        # Custom timeout (default: 10s)
    WASM_FILE = "my-service.wasm"  # Custom WASM file (default: "app.wasm")
```

## Advanced Usage

For custom fixtures:

```python
from fastly_compute.testing import create_viceroy_server_fixture

my_server = create_viceroy_server_fixture("custom.wasm")

class TestCustomService:
    def test_endpoint(self, my_server):
        response = requests.get(f"{my_server.base_url}/test")
        assert response.status_code == 200
```

## Running Tests

```bash
make test                    # Build and run tests
pytest -m integration       # Run integration tests only
pytest -m integration -v -s # Verbose output with viceroy logs
```

## Error Handling

The framework provides comprehensive error handling:

- **Missing WASM**: Clear error message if WASM file doesn't exist
- **Startup failures**: Viceroy output displayed automatically
- **Request failures**: Recent viceroy logs shown on HTTP errors
- **Test failures**: Automatic viceroy output display (requires plugin setup)

### Enabling Automatic Viceroy Output

To get viceroy logs automatically displayed on test failures, add this to your `conftest.py`:

```python
pytest_plugins = ["fastly_compute.pytest_plugin"]
```

This enables automatic display of recent viceroy server output whenever a test fails, making debugging much easier.

## Build Integration

Let your build system handle WASM building:

```makefile
test: app.wasm
	pytest -m integration

app.wasm: app.py
	componentize-py componentize app -o app.wasm
```

## Examples

- `test_app.py` - Tests for the Fastly Compute service functionality (app.wasm)
- `test_testing.py` - Tests for the viceroy testing framework itself