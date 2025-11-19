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
from wit_world.imports import types as wit_types
from wit_world.types import Err as WitErr

from .backend import BackendResolver
from .exceptions import ConnectionError, HTTPError, RequestException, Timeout
from .response import FastlyResponse
from .timeout import TimeoutConfig

# WIT error type mappings for detailed errors; the keys here are derived
# from send-error-detail
_WIT_ERROR_CODE_TO_REQUESTS_EXC = {
    # Timeout errors
    http_req.SendErrorDetail_DnsTimeout: Timeout,
    http_req.SendErrorDetail_DnsTimeout: Timeout,
    http_req.SendErrorDetail_ConnectionTimeout: Timeout,
    http_req.SendErrorDetail_HttpResponseTimeout: Timeout,
    # Connection errors
    http_req.SendErrorDetail_ConnectionRefused: ConnectionError,
    http_req.SendErrorDetail_ConnectionTerminated: ConnectionError,
    http_req.SendErrorDetail_DestinationNotFound: ConnectionError,
    http_req.SendErrorDetail_DestinationUnavailable: ConnectionError,
    http_req.SendErrorDetail_DestinationIpUnroutable: ConnectionError,
    http_req.SendErrorDetail_DnsError: ConnectionError,
    http_req.SendErrorDetail_TlsCertificateError: ConnectionError,
    http_req.SendErrorDetail_TlsConfigurationError: ConnectionError,
    http_req.SendErrorDetail_TlsAlertReceived: ConnectionError,
    http_req.SendErrorDetail_TlsProtocolError: ConnectionError,
    http_req.SendErrorDetail_ConnectionLimitReached: ConnectionError,
    # HTTP protocol errors
    http_req.SendErrorDetail_HttpIncompleteResponse: HTTPError,
    http_req.SendErrorDetail_HttpResponseHeaderSectionTooLarge: HTTPError,
    http_req.SendErrorDetail_HttpResponseBodyTooLarge: HTTPError,
    http_req.SendErrorDetail_HttpUpgradeFailed: HTTPError,
    http_req.SendErrorDetail_HttpProtocolError: HTTPError,
    http_req.SendErrorDetail_HttpResponseStatusInvalid: HTTPError,
    # Request/backend errors (default to RequestException)
    http_req.SendErrorDetail_HttpRequestCacheKeyInvalid: RequestException,
    http_req.SendErrorDetail_HttpRequestUriInvalid: RequestException,
    http_req.SendErrorDetail_InternalError: RequestException,
}

# WIT base error type mappings for generic errors (current viceroy)
_BASE_ERROR_MAPPINGS = {
    wit_types.Error_HttpInvalid: HTTPError,
    wit_types.Error_HttpUser: HTTPError,
    wit_types.Error_HttpIncomplete: HTTPError,
    wit_types.Error_HttpHeadTooLarge: HTTPError,
    wit_types.Error_HttpInvalidStatus: HTTPError,
    wit_types.Error_CannotRead: ConnectionError,
    # All others (Error_GenericError, Error_InvalidArgument, etc.) default to RequestException
}


def _map_wit_error(err: WitErr, operation: str) -> None:
    """Map a WIT error to a requests exception.

    Args:
        err: WIT Err exception containing ErrorWithDetail
        operation: Description of what operation failed

    Raises:
        Appropriate exception (Timeout, ConnectionError, HTTPError, RequestException)
        with full exception chain preserved via 'from err'
    """
    # TODO: many of the requests exceptions allow for storage of the request/response
    # that lead to the error; plumb those through in the future depending on the type.

    # Create base error message
    message = f"{operation}: "

    # sanity check -- this isn't expected but map the base case to a
    # generic exception
    if not hasattr(err.value, "detail") and not hasattr(err.value, "error"):
        message += f"unexpected error structure: {err}"
        return RequestException(message)

        error_with_detail = err.value

    # Try detailed error classification first (future production case)
    if error_with_detail.detail is not None:
        send_error_type = type(error_with_detail.detail)
        message += send_error_type.__name__

        # Look up exception type from detailed error mapping
        # TODO - there's some additional info on some of these types that could
        # be extracted.  It may be enough that we just keep the underlying exception
        # but that is TBD.
        exception_class = _WIT_ERROR_CODE_TO_REQUESTS_EXC.get(
            send_error_type, RequestException
        )
        return exception_class(message)

    # No detailed error - classify based on base error type
    base_error_type = type(error_with_detail.error)
    message += base_error_type.__name__
    exception_class = _BASE_ERROR_MAPPINGS.get(base_error_type, RequestException)

    return exception_class(message)


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

    # Resolve backend and final URL
    try:
        final_url, backend_name = resolver.resolve(url, backend, resolved_timeout)
    except ValueError as e:
        # Backend resolution errors (invalid URLs, missing backends, etc.)
        raise RequestException(f"Backend resolution failed: {e}") from e

    # Add query parameters if provided
    if params:
        try:
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
        except (ValueError, TypeError) as e:
            raise RequestException(f"Invalid query parameters: {e}") from e

    # Create WIT request
    try:
        wit_request = http_req.Request.new()
        wit_request.set_method(method.upper())
        wit_request.set_uri(final_url)
    except Exception as e:
        raise RequestException(f"Failed to create WIT request: {e}") from e

    # Set headers
    try:
        # TODO: See https://github.com/fastly/Viceroy/pull/549; what is
        # present here is a temporary workaround for viceroy differing
        # in its handling than XQD.
        if backend is not None:
            wit_request.insert_header("Host", b"dummy")

        # TODO: verify against other Compute SDKs
        wit_request.insert_header("User-Agent", b"FastlyCompute-Requests/1.0")

        # Add custom headers
        if headers:
            for name, value in headers.items():
                wit_request.insert_header(name, value.encode("utf-8"))
    except (ValueError, UnicodeError) as e:
        raise RequestException(f"Invalid headers: {e}") from e
    except Exception as e:
        raise RequestException(f"Failed to set request headers: {e}") from e

    # Prepare request body
    try:
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
    except (TypeError, ValueError, UnicodeError) as e:
        raise RequestException(f"Invalid request body: {e}") from e
    except Exception as e:
        raise RequestException(f"Failed to prepare request body: {e}") from e

    # Send the request
    try:
        wit_response, response_body = http_req.send(
            wit_request, request_body, backend_name
        )
    except WitErr as e:
        # WIT-level errors during request execution - use proper error classification
        raise _map_wit_error(e, "Request execution failed") from e
    except Exception as e:
        # Unexpected non-WIT exception (should be rare)
        raise RequestException(f"Unexpected error during request execution: {e}") from e

    # Wrap in FastlyResponse
    try:
        return FastlyResponse(wit_response, response_body, final_url)
    except Exception as e:
        raise RequestException(f"Failed to create response object: {e}") from e


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
