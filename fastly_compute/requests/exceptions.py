"""Exceptions for fastly_compute.requests - compatible with requests library."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wit_world.types import Err as WitErr

    from .response import FastlyResponse

# Runtime imports needed for error mappings at module level
from wit_world.imports import http_req
from wit_world.imports import types as wit_types
from wit_world.imports.http_req import SendErrorDetail


class RequestException(IOError):
    """Base exception for all requests-related errors."""

    def __init__(
        self,
        message: str,
        response: FastlyResponse | None = None,
        request: http_req.Request | None = None,
    ) -> None:
        """Initialize RequestException.

        Args:
            message: Error message
            response: Optional response object that caused the error
            request: Optional request object that caused the error
        """
        super().__init__(message)
        self.response: FastlyResponse | None = response
        self.request: http_req.Request | None = request

    @classmethod
    def from_http_req_error(
        cls, err: WitErr[http_req.ErrorWithDetail], operation: str
    ) -> RequestException:
        """Create appropriate exception from http_req WIT error.

        Args:
            err: WIT Err exception containing ErrorWithDetail
            operation: Description of what operation failed

        Returns:
            Appropriate RequestException subclass instance
        """
        error_with_detail = err.value

        # Try detailed error classification first; this is not guaranteed
        # to be present in all cases.
        if error_with_detail.detail is not None:
            send_error_type = type(error_with_detail.detail)
            requests_exc_type = WIT_SEND_ERROR_DETAIL_MAPPING.get(send_error_type, cls)
            return requests_exc_type(f"{operation}: {send_error_type.__name__}")

        # No detailed error - classify based on base error type
        base_error_type = type(error_with_detail.error)
        requests_exc_type: type[RequestException] = WIT_ERROR_MAPPINGS.get(
            base_error_type, cls
        )
        return requests_exc_type(f"{operation}: {base_error_type.__name__}")

    @classmethod
    def from_wit_error(
        cls, err: WitErr[wit_types.Error], operation: str
    ) -> RequestException:
        """Create appropriate exception from generic WIT error.

        Args:
            err: WIT Err exception containing generic Error
            operation: Description of what operation failed

        Returns:
            Appropriate RequestException subclass instance
        """
        error_type = type(err.value)
        exception_class = WIT_ERROR_MAPPINGS.get(error_type, cls)
        message = f"Operation {operation} failed: {error_type.__name__}"
        return exception_class(message)


class ConnectionError(RequestException):
    """Exception for connection-related errors."""


class Timeout(RequestException):
    """Exception for timeout errors."""


class HTTPError(RequestException):
    """Exception for HTTP error responses (4xx, 5xx status codes)."""

    def __init__(
        self,
        message: str,
        response: FastlyResponse | None = None,
        request: http_req.Request | None = None,
    ) -> None:
        """Initialize HTTPError.

        Args:
            message: Error message
            response: Response object that caused the error
            request: Request object that caused the error
        """
        super().__init__(message, response, request)


class TooManyRedirects(RequestException):
    """Exception for too many redirects."""


class InvalidURL(RequestException, ValueError):
    """Exception for invalid URLs."""

    def __init__(
        self,
        message: str,
        response: FastlyResponse | None = None,
        request: http_req.Request | None = None,
    ) -> None:
        """Initialize InvalidURL."""
        super().__init__(message, response, request)


class MissingSchema(RequestException, ValueError):
    """Exception for URLs missing a schema (http://, https://, etc.)."""

    def __init__(
        self,
        message: str,
        response: FastlyResponse | None = None,
        request: http_req.Request | None = None,
    ) -> None:
        """Initialize MissingSchema."""
        super().__init__(message, response, request)


class InvalidHeader(RequestException, ValueError):
    """Exception for invalid headers."""

    def __init__(
        self,
        message: str,
        response: FastlyResponse | None = None,
        request: http_req.Request | None = None,
    ) -> None:
        """Initialize InvalidHeader."""
        super().__init__(message, response, request)


class ChunkedEncodingError(RequestException):
    """Exception for chunked encoding errors."""


class ContentDecodingError(RequestException):
    """Exception for content decoding errors."""


class StreamConsumedError(RequestException, TypeError):
    """Exception for attempting to read a consumed stream."""

    def __init__(
        self,
        message: str,
        response: FastlyResponse | None = None,
        request: http_req.Request | None = None,
    ) -> None:
        """Initialize StreamConsumedError."""
        super().__init__(message, response, request)


# WIT error detail mappings for http_req errors
WIT_SEND_ERROR_DETAIL_MAPPING: MappingProxyType[
    type[SendErrorDetail], type[RequestException]
] = MappingProxyType(
    {
        # Timeout errors
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
)

# WIT base error type mappings for generic errors
WIT_ERROR_MAPPINGS: MappingProxyType[type[wit_types.Error], type[RequestException]] = (
    MappingProxyType(
        {
            wit_types.Error_HttpInvalid: HTTPError,
            wit_types.Error_HttpUser: HTTPError,
            wit_types.Error_HttpIncomplete: HTTPError,
            wit_types.Error_HttpHeadTooLarge: HTTPError,
            wit_types.Error_HttpInvalidStatus: HTTPError,
            wit_types.Error_CannotRead: ConnectionError,
        }
    )
)
