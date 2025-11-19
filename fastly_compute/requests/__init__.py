"""A requests-compatible HTTP client for Fastly Compute.

This module provides a familiar requests-like API while leveraging Fastly's
backend architecture and WIT bindings for optimal performance.

Basic Usage:
    import fastly_compute.requests as requests

    # Static backend (pre-configured)
    response = requests.get("/api/users", backend="api-backend")

    # Dynamic backend (external URLs)
    response = requests.get("https://http-me.fastly.dev/get")

    # POST with JSON
    response = requests.post("https://http-me.fastly.dev/post",
                           json={"key": "value"})

Fastly-Specific Features:
    from fastly_compute.requests import TimeoutConfig

    # Granular timeout control (not available in standard requests)
    timeout_config = TimeoutConfig(
        connect=5.0,          # 5s to establish connection
        first_byte=30.0,      # 30s to receive first byte
        between_bytes=2.0     # 2s max between bytes
    )
    response = requests.get(
        "https://api.example.com/data",
        timeout_config=timeout_config
    )

    # Backend-specific features
    response = requests.get(
        "/api/endpoint",
        backend="my-backend"          # Use specific static backend
    )

Compatibility Notes:
    Most parameters are compatible with the standard requests library.
    Fastly-specific parameters (timeout_config, backend) will cause TypeErrors
    if used with the standard requests library. Use the standard timeout
    parameter for cross-platform compatibility.
"""

import json as json_module
import urllib.parse
from typing import Any

from wit_world.imports import http_body, http_req

from .backend import BackendResolver
from .exceptions import ConnectionError, HTTPError, RequestException, Timeout
from .response import FastlyResponse
from .timeout import TimeoutConfig

# Export main components for public API
__all__ = [
    # Core request functions
    "get",
    "post",
    "put",
    "delete",
    "head",
    "options",
    "request",
    # Response class
    "FastlyResponse",
    # Timeout configuration
    "TimeoutConfig",
    # Exceptions
    "RequestException",
    "ConnectionError",
    "HTTPError",
    "Timeout",
]


def get(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    backend: str | None = None,
    timeout: None | float | tuple = None,
    timeout_config: TimeoutConfig | None = None,
    **kwargs,
) -> FastlyResponse:
    """Send a GET request.

    Args:
        url: URL for the request. Can be a path (for static backends) or full URL (for dynamic)
        params: Query parameters to append to the URL
        headers: HTTP headers to send with the request
        backend: Static backend name (optional, will use dynamic backend if not provided)
        timeout: Request timeout in seconds (requests-compatible). Can be:
            - float: Single timeout for all phases
            - (connect, read): Tuple for connect and read timeouts
        timeout_config: **Fastly-only** Advanced timeout configuration with granular control
            over connect_timeout, first_byte_timeout, and between_bytes_timeout
        **kwargs: Additional arguments (for requests compatibility, ignored)

    Note:
        The timeout_config parameter is Fastly-specific and will cause a TypeError
        if used with the standard requests library. Use timeout for cross-platform compatibility.

    Raises:
        RequestException: For general request errors
        ConnectionError: For connection-related errors
        Timeout: For timeout errors
        ValueError: If both timeout and timeout_config are specified
    """
    return request(
        "GET",
        url,
        params=params,
        headers=headers,
        backend=backend,
        timeout=timeout,
        timeout_config=timeout_config,
        **kwargs,
    )


def post(
    url: str,
    data: str | bytes | dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    backend: str | None = None,
    timeout: None | float | tuple = None,
    timeout_config: TimeoutConfig | None = None,
    **kwargs,
) -> FastlyResponse:
    """Send a POST request.

    Args:
        url: URL for the request
        data: Form data to send in the body
        json: JSON data to send in the body (mutually exclusive with data)
        params: Query parameters to append to the URL
        headers: HTTP headers to send with the request
        backend: Static backend name (optional)
        timeout: Request timeout in seconds (requests-compatible)
        timeout_config: **Fastly-only** Advanced timeout configuration
        **kwargs: Additional arguments (for requests compatibility, ignored)
    """
    return request(
        "POST",
        url,
        data=data,
        json=json,
        params=params,
        headers=headers,
        backend=backend,
        timeout=timeout,
        timeout_config=timeout_config,
        **kwargs,
    )


def put(
    url: str,
    data: str | bytes | dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    **kwargs,
) -> FastlyResponse:
    """Send a PUT request."""
    return request("PUT", url, data=data, json=json, **kwargs)


def delete(url: str, **kwargs) -> FastlyResponse:
    """Send a DELETE request."""
    return request("DELETE", url, **kwargs)


def patch(
    url: str,
    data: str | bytes | dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    **kwargs,
) -> FastlyResponse:
    """Send a PATCH request."""
    return request("PATCH", url, data=data, json=json, **kwargs)


def head(url: str, **kwargs) -> FastlyResponse:
    """Send a HEAD request."""
    return request("HEAD", url, **kwargs)


def options(url: str, **kwargs) -> FastlyResponse:
    """Send an OPTIONS request."""
    return request("OPTIONS", url, **kwargs)


def request(
    method: str,
    url: str,
    params: dict[str, Any] | None = None,
    data: str | bytes | dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    backend: str | None = None,
    timeout: None | float | tuple = None,
    timeout_config: TimeoutConfig | None = None,
    **kwargs,
) -> FastlyResponse:
    """Send an HTTP request.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        url: URL for the request
        params: Query parameters
        data: Form data for the request body
        json: JSON data for the request body (mutually exclusive with data)
        headers: HTTP headers
        backend: Static backend name (if not provided, will use dynamic backend)
        timeout: Request timeout in seconds (requests-compatible)
        timeout_config: **Fastly-only** Advanced timeout configuration
        **kwargs: Additional arguments (for requests compatibility, ignored)

    Raises:
        RequestException: For general request errors
        ValueError: For invalid arguments
    """
    # Validate arguments
    if data is not None and json is not None:
        raise ValueError("Cannot specify both 'data' and 'json' parameters")

    if timeout is not None and timeout_config is not None:
        raise ValueError(
            "Cannot specify both 'timeout' and 'timeout_config' parameters"
        )

    # Resolve timeout configuration
    if timeout_config is not None:
        resolved_timeout = timeout_config
    else:
        resolved_timeout = TimeoutConfig.from_requests_timeout(timeout)

    # Initialize resolver
    resolver = BackendResolver()

    try:
        # Resolve backend and final URL
        final_url, backend_name = resolver.resolve(url, backend, resolved_timeout)

        # Add query parameters if provided
        if params:
            # Parse existing query parameters
            parsed_url = urllib.parse.urlparse(final_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)

            # Add new parameters
            for key, value in params.items():
                if isinstance(value, list):
                    query_params[key] = value
                else:
                    query_params[key] = [str(value)]

            # Rebuild URL with parameters
            new_query = urllib.parse.urlencode(query_params, doseq=True)
            final_url = urllib.parse.urlunparse(
                (
                    parsed_url.scheme,
                    parsed_url.netloc,
                    parsed_url.path,
                    parsed_url.params,
                    new_query,
                    parsed_url.fragment,
                )
            )

        # Create WIT request
        wit_request = http_req.Request.new()
        wit_request.set_method(method.upper())
        wit_request.set_uri(final_url)

        # Set Host header (may be required by viceroy, but let's test without it)
        # TODO: Investigate if Host header is actually required by the WIT spec
        # or if this is a viceroy-specific requirement
        if backend is not None:
            # Static backend - use localhost as host
            wit_request.insert_header("Host", b"localhost")
        else:
            # Dynamic backend - extract host from original URL
            parsed_url = urllib.parse.urlparse(url)
            host = parsed_url.netloc.encode("utf-8")
            wit_request.insert_header("Host", host)

        # Set default headers
        wit_request.insert_header("User-Agent", b"FastlyCompute-Requests/1.0")

        # Add custom headers
        if headers:
            for name, value in headers.items():
                wit_request.insert_header(name, value.encode("utf-8"))

        # Prepare request body
        request_body = http_body.new()

        if json is not None:
            # JSON data - use the json module, not the parameter
            json_str = json_module.dumps(json) if not isinstance(json, str) else json
            json_bytes = json_str.encode("utf-8")
            wit_request.insert_header("Content-Type", b"application/json")
            http_body.write(request_body, json_bytes, http_body.WriteEnd.BACK)

        elif data is not None:
            if isinstance(data, dict):
                # Form data
                form_data = urllib.parse.urlencode(data).encode("utf-8")
                wit_request.insert_header(
                    "Content-Type", b"application/x-www-form-urlencoded"
                )
                http_body.write(request_body, form_data, http_body.WriteEnd.BACK)
            elif isinstance(data, str | bytes):
                # Raw data
                data_bytes = data.encode("utf-8") if isinstance(data, str) else data
                http_body.write(request_body, data_bytes, http_body.WriteEnd.BACK)
            else:
                raise ValueError(f"Unsupported data type: {type(data)}")

        # Send request
        wit_response, response_body = http_req.send(
            wit_request, request_body, backend_name
        )

        # Wrap in FastlyResponse
        return FastlyResponse(wit_response, response_body, final_url)

    except Exception as e:
        # TODO: revisit finer-grained exception handling and top-level
        #       WIT exception mapping.

        # Map WIT errors to requests-compatible exceptions
        error_msg = str(e).lower()
        if "timeout" in error_msg:
            raise Timeout(str(e)) from e
        elif "connection" in error_msg or "network" in error_msg:
            raise ConnectionError(str(e)) from e
        else:
            raise RequestException(str(e)) from e


# Export main API
__all__ = [
    "get",
    "post",
    "put",
    "delete",
    "patch",
    "head",
    "options",
    "request",
    "FastlyResponse",
    "RequestException",
    "ConnectionError",
    "Timeout",
    "HTTPError",
]
