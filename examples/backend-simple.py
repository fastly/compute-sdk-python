"""Simple backend example.

This example demonstrates using Fastly backends to make HTTP requests to external services
using the raw WIT bindings. It shows both static and dynamic backend patterns.

Static backends are pre-configured in the viceroy configuration file.
Dynamic backends are created programmatically at runtime.
"""

import json
from dataclasses import dataclass

from bottle import Bottle
from wit_world.imports import backend, compute_runtime, http_body, http_req

from fastly_compute.utils import read_response_body
from fastly_compute.wsgi import WsgiHttpIncoming


@dataclass
class SimpleResponse:
    """Simple response container for backend requests."""

    status: int
    body: bytes


app = Bottle()


def _register_dynamic_backend(
    target_url: str, backend_prefix: str = "dynamic"
) -> tuple[str, str, str, str]:
    """
    Parse URL and register dynamic backend if needed.

    Args:
        target_url: Full URL to parse and register backend for
        backend_prefix: Prefix for the backend name

    Returns:
        Tuple of (scheme, host, path, backend_name)

    Raises:
        ValueError: If URL is invalid
        Exception: If backend registration fails
    """
    # Parse URL to get host for backend registration
    if not target_url.startswith(("http://", "https://")):
        raise ValueError("Dynamic backend requires full URL with scheme")

    # Extract scheme and host
    scheme = "https" if target_url.startswith("https://") else "http"
    url_without_scheme = target_url[len(scheme + "://") :]
    host_and_path = url_without_scheme.split("/", 1)
    host = host_and_path[0]
    path = "/" + (host_and_path[1] if len(host_and_path) > 1 else "")

    # Create backend name (replace dots and colons for valid backend names)
    backend_name = f"{backend_prefix}_{host.replace('.', '_').replace(':', '_')}"

    # Register dynamic backend if it doesn't exist
    if not backend.exists(backend_name):
        # Create backend options
        options = http_req.DynamicBackendOptions()

        # Configure TLS if HTTPS
        if scheme == "https":
            options.use_tls(True)

        # Set reasonable timeouts (in milliseconds)
        options.connect_timeout(30000)  # 30 seconds
        options.first_byte_timeout(60000)  # 60 seconds
        options.between_bytes_timeout(10000)  # 10 seconds

        # Register the backend
        http_req.register_dynamic_backend(
            prefix=backend_name, target=f"{scheme}://{host}", options=options
        )

    return scheme, host, path, backend_name


def make_static_backend_request(backend_name: str, path: str) -> SimpleResponse:
    """Make a request using a static backend (pre-configured in viceroy.toml).

    Args:
        backend_name: Name of the static backend from configuration
        path: Path to request (e.g., "/get", "/post")

    Returns:
        SimpleResponse with status and raw body bytes

    Raises:
        Exception if backend doesn't exist or request fails
    """
    # Check if backend exists
    if not backend.exists(backend_name):
        raise ValueError(f"Static backend '{backend_name}' does not exist")

    # Create a new request
    request = http_req.Request.new()

    # Set request details
    request.set_method("GET")
    request.set_uri(path)
    request.insert_header("User-Agent", b"FastlyCompute-BackendExample/1.0")

    # TODO: this shouldn't be required and is a bug in viceroy for component
    #       model interactions, most likely.
    request.insert_header("Host", b"localhost")

    # Create empty body for GET request
    body = http_body.new()

    # Send request to static backend
    response, response_body = http_req.send(request, body, backend_name)

    # Read response
    status = response.get_status()

    # Read response body
    response_data = read_response_body(response_body)

    return SimpleResponse(status=status, body=response_data)


def make_dynamic_backend_request(
    target_url: str, backend_prefix: str = "dynamic"
) -> SimpleResponse:
    """Make a request using a dynamic backend (created at runtime).

    Args:
        target_url: Full URL to request (e.g., "https://httpbin.org/get")
        backend_prefix: Prefix for the dynamic backend name

    Returns:
        SimpleResponse with status and raw body bytes

    Raises:
        ValueError: If URL is invalid
        Exception: If backend registration or request fails
    """
    # Parse URL and register backend
    scheme, host, path, backend_name = _register_dynamic_backend(
        target_url, backend_prefix
    )

    # Create request
    request = http_req.Request.new()
    request.set_method("GET")
    request.set_uri(path)
    request.insert_header("User-Agent", b"FastlyCompute-BackendExample/1.0")
    request.insert_header("Host", host.encode("utf-8"))

    # Create empty body
    body = http_body.new()

    # Send request
    response, response_body = http_req.send(request, body, backend_name)

    # Read response
    status = response.get_status()

    # Read response body
    response_data = read_response_body(response_body)

    return SimpleResponse(status=status, body=response_data)


def make_dynamic_post_request(target_url: str, post_data: dict) -> SimpleResponse:
    """Make a POST request using a dynamic backend with JSON data.

    Args:
        target_url: Full URL to POST to
        post_data: Data to send as JSON

    Returns:
        SimpleResponse with status and raw body bytes

    Raises:
        ValueError: If URL is invalid
        Exception: If backend registration or request fails
    """
    # Parse URL and register backend
    scheme, host, path, backend_name = _register_dynamic_backend(target_url)

    # Create POST request
    request = http_req.Request.new()
    request.set_method("POST")
    request.set_uri(path)
    request.insert_header("User-Agent", b"FastlyCompute-BackendExample/1.0")
    request.insert_header("Host", host.encode("utf-8"))
    request.insert_header("Content-Type", b"application/json")

    # Create body with JSON data
    json_str = json.dumps(post_data)
    json_bytes = json_str.encode("utf-8")

    body = http_body.new()
    http_body.write(body, json_bytes, http_body.WriteEnd.BACK)

    # Send request
    response, response_body = http_req.send(request, body, backend_name)

    # Read response
    status = response.get_status()

    # Read response body
    response_data = read_response_body(response_body)

    return SimpleResponse(status=status, body=response_data)


@app.route("/static")
def test_static_backend():
    """Test static backend (requires backend named 'test-be' in viceroy.toml)."""
    try:
        response = make_static_backend_request("test-be", "/get")

        # Try to parse response as JSON
        try:
            response_data = json.loads(response.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            response_data = {"text": response.body.decode("utf-8", errors="replace")}

        return {
            "backend_type": "static",
            "backend_name": "test-be",
            "status": response.status,
            "data": response_data,
        }
    except Exception as e:
        return {"backend_type": "static", "backend_name": "test-be", "error": str(e)}


@app.route("/dynamic")
def test_dynamic_backend():
    """Test dynamic backend to a public API."""
    from bottle import request

    # Get target from query parameter (required)
    target = request.query.get("target")
    if not target:
        return {
            "backend_type": "dynamic",
            "error": "target query parameter is required (e.g., ?target=https://httpbin.org/get)",
        }

    try:
        response = make_dynamic_backend_request(target)

        # Try to parse response as JSON
        try:
            response_data = json.loads(response.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            response_data = {"text": response.body.decode("utf-8", errors="replace")}

        return {
            "backend_type": "dynamic",
            "target": target,
            "status": response.status,
            "data": response_data,
        }
    except Exception as e:
        return {
            "backend_type": "dynamic",
            "target": target,
            "error": str(e),
        }


@app.route("/dynamic-post")
def test_dynamic_post():
    """Test dynamic backend POST."""
    from bottle import request

    # Get target from query parameter (required)
    target = request.query.get("target")
    if not target:
        return {
            "backend_type": "dynamic",
            "method": "POST",
            "error": "target query parameter is required (e.g., ?target=https://httpbin.org/post)",
        }

    vcpu_time = compute_runtime.get_vcpu_ms()
    test_data = {
        "message": "Hello from Fastly Compute!",
        "timestamp": vcpu_time,
        "test": True,
    }

    try:
        response = make_dynamic_post_request(target, test_data)

        # Try to parse response as JSON
        try:
            response_data = json.loads(response.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            response_data = {"text": response.body.decode("utf-8", errors="replace")}

        return {
            "backend_type": "dynamic",
            "method": "POST",
            "target": target,
            "status": response.status,
            "sent_data": test_data,
            "data": response_data,
        }
    except Exception as e:
        return {
            "backend_type": "dynamic",
            "method": "POST",
            "target": target,
            "error": str(e),
        }


# Create the HTTP handler using the shared WSGI infrastructure
# Use basic environ for Bottle (doesn't need enhanced WSGI variables like Flask)
HttpIncoming = WsgiHttpIncoming(app)
