"""A requests-compatible HTTP client for Fastly Compute.

This module provides a familiar requests-like API while leveraging Fastly's
backend architecture and WIT bindings for optimal performance.

Usage::
    import fastly_compute.requests as requests
    from fastly_compute.requests import TimeoutConfig

    # Static backend (pre-configured)
    response = requests.get("/api/users", fastly_backend="api-backend")
    # or, providing full URL (will still use backend configuration)
    response = requests.get("https://example.com/api/users", fastly_backend="api-backend")

    # Dynamic backend (looks like normal requests usage)
    response = requests.get("https://http-me.fastly.dev/get")

    # POST with JSON
    response = requests.post("https://http-me.fastly.dev/post",
                           json={"key": "value"})

    # Granular timeout control (Fastly-specific)
    timeout_config = TimeoutConfig(
        connect=5.0,          # 5s to establish connection
        first_byte=30.0,      # 30s to receive first byte
        between_bytes=2.0     # 2s max between bytes
    )
    response = requests.get(
        "https://api.example.com/data",
        fastly_timeout=timeout_config
    )

Compatibility Notes:
    Most parameters are compatible with the standard requests library.
    Fastly-specific parameters (fastly_timeout, fastly_backend) will cause TypeErrors
    if used with the standard requests library. Use the standard timeout
    parameter for cross-platform compatibility.
"""

import json as json_module
import urllib.parse
from typing import Any, TypedDict, Unpack

from componentize_py_types import Err
from wit_world.imports import http_body, http_req

from fastly_compute.requests.backend import resolve_backend

from .exceptions import (
    ConnectionError,
    HTTPError,
    MissingSchema,
    RequestException,
    Timeout,
)
from .response import FastlyResponse
from .timeout import TimeoutConfig


# TypedDict for common request parameters
class RequestKwargs(TypedDict, total=False):
    """Common keyword arguments for all request methods."""

    data: str | bytes | dict[str, Any] | None
    json: Any
    params: dict[str, Any]
    headers: dict[str, str]
    fastly_backend: str
    timeout: None | float | tuple[float, float]
    fastly_timeout: TimeoutConfig


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
    "MissingSchema",
]


def get(
    url: str,
    **kwargs: Unpack[RequestKwargs],
) -> FastlyResponse:
    """Send a GET request.

    Args:
        url: URL for the request. Can be a path (for static backends) or full URL (for dynamic)
        params: Query parameters to append to the URL
        headers: HTTP headers to send with the request
        fastly_backend: Static backend name (optional, will use dynamic backend if not provided)
        timeout: Request timeout in seconds (requests-compatible). Can be:
            - float: Single timeout for all phases
            - (connect, read): Tuple for connect and read timeouts
        fastly_timeout: **Fastly-only** Advanced timeout configuration with granular control
            over connect_timeout, first_byte_timeout, and between_bytes_timeout
        **kwargs: Additional arguments (for requests compatibility, ignored)

    Note:
        The fastly_timeout parameter is Fastly-specific and will cause a TypeError
        if used with the standard requests library. Use timeout for cross-platform compatibility.

    Raises:
        RequestException: For general request errors
        ConnectionError: For connection-related errors
        Timeout: For timeout errors
        ValueError: If both timeout and fastly_timeout are specified
    """
    return request("GET", url, **kwargs)


def post(
    url: str,
    **kwargs: Unpack[RequestKwargs],
) -> FastlyResponse:
    """Send a POST request.

    Args:
        url: URL for the request
        data: Form data to send in the body
        json: JSON data to send in the body (mutually exclusive with data)
        params: Query parameters to append to the URL
        headers: HTTP headers to send with the request
        fastly_backend: Static backend name (optional)
        timeout: Request timeout in seconds (requests-compatible)
        fastly_timeout: **Fastly-only** Advanced timeout configuration
        **kwargs: Additional arguments (for requests compatibility, ignored)
    """
    return request("POST", url, **kwargs)


def put(
    url: str,
    **kwargs: Unpack[RequestKwargs],
) -> FastlyResponse:
    """Send a PUT request."""
    return request("PUT", url, **kwargs)


def delete(
    url: str,
    **kwargs: Unpack[RequestKwargs],
) -> FastlyResponse:
    """Send a DELETE request."""
    return request("DELETE", url, **kwargs)


def patch(
    url: str,
    **kwargs: Unpack[RequestKwargs],
) -> FastlyResponse:
    """Send a PATCH request."""
    return request("PATCH", url, **kwargs)


def head(url: str, **kwargs: Unpack[RequestKwargs]) -> FastlyResponse:
    """Send a HEAD request."""
    return request("HEAD", url, **kwargs)


def options(url: str, **kwargs: Unpack[RequestKwargs]) -> FastlyResponse:
    """Send an OPTIONS request."""
    return request("OPTIONS", url, **kwargs)


def request(
    method: str,
    url: str,
    params: dict[str, Any] | None = None,
    data: str | bytes | dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    fastly_backend: str | None = None,
    timeout: None | float | tuple[float, float] = None,
    fastly_timeout: TimeoutConfig | None = None,
    **_kwargs: Any,
) -> FastlyResponse:
    """Send an HTTP request.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        url: URL for the request
        params: Query parameters
        data: Form data for the request body
        json: JSON data for the request body (mutually exclusive with data)
        headers: HTTP headers
        fastly_backend: Static backend name (if not provided, will use dynamic backend)
        timeout: Request timeout in seconds (requests-compatible)
        fastly_timeout: **Fastly-only** Advanced timeout configuration
        **kwargs: Additional arguments (for requests compatibility, ignored)

    Raises:
        RequestException: For general request errors
        ValueError: For invalid arguments
    """
    # Validate arguments
    if data is not None and json is not None:
        raise ValueError("Cannot specify both 'data' and 'json' parameters")

    if timeout is not None and fastly_timeout is not None:
        raise ValueError(
            "Cannot specify both 'timeout' and 'fastly_timeout' parameters"
        )

    # Resolve timeout configuration
    if fastly_timeout is None:
        fastly_timeout = TimeoutConfig.from_requests_timeout(timeout)

    resolution = resolve_backend(url, fastly_backend, fastly_timeout)
    url_parsed = resolution.url_parsed

    # Add query parameters if provided
    if params:
        query_params = urllib.parse.parse_qs(url_parsed.query)
        for key, value in params.items():
            if isinstance(value, list):
                query_params[key] = value
            else:
                query_params[key] = [str(value)]

        new_query = urllib.parse.urlencode(query_params, doseq=True)
        url_parsed = url_parsed._replace(query=new_query)

    # Create WIT request
    try:
        wit_request = http_req.Request.new()
        wit_request.set_method(method.upper())
        wit_request.set_uri(url_parsed.geturl())
    except Err as e:
        raise RequestException.from_wit_error(e, "create_req") from e

    # Set headers
    headers = headers if headers is not None else {}
    if fastly_backend is not None:
        host_header = headers.pop("Host", url_parsed.netloc)
        wit_request.insert_header("Host", host_header.encode("utf-8"))

    body: bytes | None = None
    if json is not None:
        # JSON data - use the json module, not the parameter
        json_str = json if isinstance(json, str) else json_module.dumps(json)
        body = json_str.encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    elif data is None:
        pass
    elif isinstance(data, dict):
        # Form data
        headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        body = urllib.parse.urlencode(data).encode("utf-8")
    else:
        # str | bytes
        body = data.encode("utf-8") if isinstance(data, str) else data

    # Add headers
    for name, value in headers.items():
        try:
            wit_request.insert_header(name, value.encode("utf-8"))
        except Err as e:
            raise RequestException.from_wit_error(e, "insert_header") from e

    # Prepare request body
    wit_body = http_body.new()
    if body:
        try:
            written = 0
            while written < len(body):
                written += http_body.write(wit_body, body)
        except Err as e:
            raise RequestException.from_wit_error(e, "http_body.write") from e

    # Send the request
    try:
        wit_response, response_body = http_req.send(
            wit_request, wit_body, resolution.backend
        )
    except Err as e:
        # WIT-level errors during request execution - use proper error classification
        raise RequestException.from_http_req_error(e, "http_req.send") from e

    # Wrap in FastlyResponse
    return FastlyResponse(wit_response, response_body, url_parsed.geturl())
