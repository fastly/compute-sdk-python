"""A requests-compatible HTTP client for Fastly Compute.

This module provides a familiar requests-like API while leveraging Fastly's
backend architecture and WIT bindings for optimal performance.

Usage:
    import fastly_compute.requests as requests

    # Static backend (pre-configured)
    response = requests.get("/api/users", backend="api-backend")

    # Dynamic backend (external URLs)
    response = requests.get("https://http-me.fastly.dev/get")

    # POST with JSON
    response = requests.post("https://http-me.fastly.dev/post",
                           json={"key": "value"})
"""

import json as json_module
import urllib.parse
from typing import Any

from .backend import BackendResolver
from .exceptions import ConnectionError, HTTPError, RequestException, Timeout
from .response import FastlyResponse


def get(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    backend: str | None = None,
    timeout: int | None = None,
    **kwargs,
) -> FastlyResponse:
    """Send a GET request.

    Args:
        url: URL for the request. Can be a path (for static backends) or full URL (for dynamic)
        params: Query parameters to append to the URL
        headers: HTTP headers to send with the request
        backend: Static backend name (optional, will use dynamic backend if not provided)
        timeout: Request timeout in seconds
        **kwargs: Additional arguments (for requests compatibility)

    Returns:
        FastlyResponse object

    Raises:
        RequestException: For general request errors
        ConnectionError: For connection-related errors
        Timeout: For timeout errors
    """
    return request(
        "GET",
        url,
        params=params,
        headers=headers,
        backend=backend,
        timeout=timeout,
        **kwargs,
    )


def post(
    url: str,
    data: str | bytes | dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    backend: str | None = None,
    timeout: int | None = None,
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
        timeout: Request timeout in seconds
        **kwargs: Additional arguments

    Returns:
        FastlyResponse object
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
    timeout: int | None = None,
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
        timeout: Request timeout in seconds
        **kwargs: Additional arguments

    Returns:
        FastlyResponse object

    Raises:
        RequestException: For general request errors
        ValueError: For invalid arguments
    """
    # Import WIT modules
    from wit_world.imports import http_body, http_req

    # Validate arguments
    if data is not None and json is not None:
        raise ValueError("Cannot specify both 'data' and 'json' parameters")

    # Initialize resolver
    resolver = BackendResolver()

    try:
        # Resolve backend and final URL
        backend_name, final_url = resolver.resolve(url, backend)

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
