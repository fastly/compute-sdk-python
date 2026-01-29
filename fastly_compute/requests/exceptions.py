"""Exceptions for fastly_compute.requests - compatible with requests library."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .response import FastlyResponse

# Runtime imports needed for error mappings at module level
from wit_world.imports import http_req
from wit_world.imports import types as wit_types
from wit_world.imports.http_req import SendErrorDetail

from fastly_compute.exceptions import FastlyError
from fastly_compute.exceptions.http_req import ErrorWithDetail
from fastly_compute.exceptions.types.error import (
    CannotRead,
    HttpHeadTooLarge,
    HttpIncomplete,
    HttpInvalid,
    HttpInvalidStatus,
    HttpUser,
)


def _map_error_to_exception(
    error: object,
    mapping: MappingProxyType,
    operation: str,
    fallback_cls: type[RequestException],
) -> RequestException:
    """Map WIT error to appropriate RequestException subclass.

    Args:
        error: The WIT error object to map
        mapping: Mapping from error types to exception classes
        operation: Description of operation that failed
        fallback_cls: Exception class to use if no mapping found

    Returns:
        Appropriate RequestException subclass instance
    """
    error_type = type(error)
    exc_cls = mapping.get(error_type, fallback_cls)
    return exc_cls(f"{operation}: {error_type.__name__}")


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
    def from_detailed_error(
        cls, err: ErrorWithDetail, operation: str
    ) -> RequestException:
        """Create a ``requests`` exception from an ErrorWithDetail.

        Args:
            err: The error to map from
            operation: Description of what operation failed

        Returns:
            Appropriate RequestException subclass instance
        """
        error_with_detail = err.args[0]

        # Try detailed error classification first; this is not guaranteed
        # to be present in all cases.
        if error_with_detail.detail is not None:
            return _map_error_to_exception(
                error_with_detail.detail,
                WIT_SEND_ERROR_DETAIL_MAPPING,
                operation,
                cls,
            )

        # No detailed error - classify based on base error type
        return _map_error_to_exception(
            error_with_detail.error,
            WIT_ERROR_MAPPINGS,
            operation,
            cls,
        )

    @classmethod
    def from_fastly_error(cls, err: FastlyError, operation: str) -> RequestException:
        """Create a ``requests`` exception from a FastlyError or subclass.

        Args:
            err: The error to map from
            operation: Description of what operation failed

        Returns:
            Appropriate RequestException subclass instance
        """
        return _map_error_to_exception(
            err,
            FASTLY_ERROR_MAPPINGS,
            f"Operation {operation} failed",
            cls,
        )


class ConnectionError(RequestException):
    """Exception for connection-related errors."""


class Timeout(RequestException):
    """Exception for timeout errors."""


class HTTPError(RequestException):
    """Exception for HTTP error responses (4xx, 5xx status codes)."""


class TooManyRedirects(RequestException):
    """Exception for too many redirects."""


class InvalidURL(RequestException, ValueError):
    """Exception for invalid URLs."""


class MissingSchema(RequestException, ValueError):
    """Exception for URLs missing a schema (http://, https://, etc.)."""


class InvalidHeader(RequestException, ValueError):
    """Exception for invalid headers."""


class ChunkedEncodingError(RequestException):
    """Exception for chunked encoding errors."""


class ContentDecodingError(RequestException):
    """Exception for content decoding errors."""


class StreamConsumedError(RequestException, TypeError):
    """Exception for attempting to read a consumed stream."""


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

# Map FastlyErrors to the errors `requests` returns.
FASTLY_ERROR_MAPPINGS: MappingProxyType[type[FastlyError], type[RequestException]] = (
    MappingProxyType(
        {
            HttpInvalid: HTTPError,
            HttpUser: HTTPError,
            HttpIncomplete: HTTPError,
            HttpHeadTooLarge: HTTPError,
            HttpInvalidStatus: HTTPError,
            CannotRead: ConnectionError,
        }
    )
)
